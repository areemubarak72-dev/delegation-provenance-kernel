from flask import Flask, request, jsonify
from flask_cors import CORS
import os, hashlib

from enforcer import Enforcer
from rule_parser import parse_intent
from emit_to_sepolia import emit_provenance, emit_blocked

app = Flask(__name__)
CORS(app, origins=os.environ.get("CORS_ORIGIN", "http://localhost:5173"))
app.config["MAX_CONTENT_LENGTH"] = 4096

POLICY = {
    "max_amount_wei": 10**18,
    "allowed_recipients": [
        "0x4be9323dfad59dbac2f0e870067cd29e5bac41cd",
        "0x000000000000000000000000000000000000dead",
    ],
}

RPC_URL = os.environ.get("RPC_URL")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
CONTRACT_ADDRESS = os.environ.get("CONTRACT_ADDRESS", "0xBA97b15362196d21e138426eb7770D1DBbBc536B")
AUTHORITY = os.environ.get("AUTHORITY", "0x1451A02b54F5ba82220185156803C1959a8407c2")
# Recording is opt-in: the local API is not an authenticated public service.
RECORD_ONCHAIN = os.environ.get("RECORD_ONCHAIN", "false").lower() == "true"
ENFORCER = Enforcer(RPC_URL, POLICY) if RPC_URL else None

STATE_ABI = [
    {"inputs": [], "name": "accumulator", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "modulus", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "approvedCount", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "blockedCount", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "delegationCount", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
]


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/api/state", methods=["GET"])
def state():
    """Return current on-chain state from the unified contract."""
    if not RPC_URL:
        return jsonify({"error": "RPC_URL is not configured"}), 503
    from web3 import Web3
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 10}))
        contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=STATE_ABI)
        return jsonify({
            "accumulator": str(contract.functions.accumulator().call()),
            "modulus": str(contract.functions.modulus().call()),
            "approvedCount": contract.functions.approvedCount().call(),
            "blockedCount": contract.functions.blockedCount().call(),
            "delegationCount": contract.functions.delegationCount().call(),
            "contract": CONTRACT_ADDRESS,
        })
    except Exception:
        return jsonify({"error": "Unable to read Sepolia state"}), 502


@app.route("/api/zk-status")
def zk_status():
    return jsonify({
        "status": "not_integrated", "verified_locally": False,
        "verified_onchain": False, "circuit_constraints": None,
        "proof_size_bytes": None, "proof_hash": None, "verifier_contract": None,
        "reason": "Standalone experimental circuits are not connected to this request pipeline",
    })


@app.route("/api/process", methods=["POST"])
def process():
    stages = {"intent": "pending", "policy": "pending", "proof": "not_integrated", "onchain": "not_attempted"}
    data = request.get_json(silent=True)
    try:
        if not isinstance(data, dict):
            raise ValueError("Send a JSON object with a text field")
        intent = parse_intent(data.get("text"))
    except ValueError as exc:
        stages["intent"] = "error"
        return jsonify(status="error", reason=str(exc), stages=stages), 400
    stages["intent"] = "done"
    if ENFORCER is None:
        stages["policy"] = "error"
        return jsonify(status="error", reason="RPC_URL is not configured", stages=stages), 503
    try:
        result = ENFORCER.enforce(AUTHORITY, intent)
    except Exception:
        stages["policy"] = "error"
        return jsonify(status="error", reason="Unable to read delegation state", stages=stages), 502

    blocked = result["status"] == "blocked"
    stages["policy"] = "blocked" if blocked else "done"
    response = {"status": result["status"], "stages": stages, "executed": False,
                "tx_hash": None, "etherscan": None}
    if blocked:
        intent_hash = hashlib.sha256(data["text"].encode()).hexdigest()
        reason_hash = hashlib.sha256(result["reason"].encode()).hexdigest()
        response.update(reason=result["reason"], intent_hash=intent_hash)
        emit, args = emit_blocked, (intent_hash, reason_hash)
    else:
        record = result["record"]
        response.update(epoch_commitment=record["epoch_commitment"], intent_hash=record["provenance_hash"])
        emit, args = emit_provenance, (record["epoch_commitment"], record["provenance_hash"])

    if not RECORD_ONCHAIN:
        response["recording_message"] = "On-chain recording is disabled"
    elif not PRIVATE_KEY:
        stages["onchain"] = "error"
        response["recording_message"] = "PRIVATE_KEY is not configured"
    else:
        try:
            receipt = emit(RPC_URL, CONTRACT_ADDRESS, PRIVATE_KEY, *args)
            tx_hash = receipt["tx_hash"]
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
            response.update(tx_hash=tx_hash, etherscan=f"https://sepolia.etherscan.io/tx/{tx_hash}")
            stages["onchain"] = "done" if receipt["status"] == 1 else "error"
            response["recording_message"] = "Provenance recorded" if receipt["status"] == 1 else "Recording transaction reverted"
        except Exception:
            stages["onchain"] = "error"
            response["recording_message"] = "Recording failed or confirmation is unknown; check the signer history before retrying"
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
