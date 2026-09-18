from flask import Flask, request, jsonify
from flask_cors import CORS
import os, hashlib

from enforcer import Enforcer
from rule_parser import parse_intent
from emit_to_sepolia import emit_provenance, emit_blocked

app = Flask(__name__)
CORS(app)

POLICY = {
    "max_amount_wei": 10**18,
    "allowed_recipients": [
        "0x4be9323dfad59dbac2f0e870067cd29e5bac41cd",
        "0x000000000000000000000000000000000000dead",
    ],
}

RPC_URL = os.environ.get("RPC_URL", "https://eth-sepolia.g.alchemy.com/v2/alch_9lH5y1pKeuJX-pgNsdrcI")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
CONTRACT_ADDRESS = "0xBA97b15362196d21e138426eb7770D1DBbBc536B"
AUTHORITY = "0x1451A02b54F5ba82220185156803C1959a8407c2"

ENFORCER = Enforcer(RPC_URL, POLICY)

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
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=STATE_ABI,
    )
    try:
        return jsonify({
            "accumulator": str(contract.functions.accumulator().call()),
            "modulus": str(contract.functions.modulus().call()),
            "approvedCount": contract.functions.approvedCount().call(),
            "blockedCount": contract.functions.blockedCount().call(),
            "delegationCount": contract.functions.delegationCount().call(),
            "contract": CONTRACT_ADDRESS,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/process", methods=["POST"])
def process():
    data = request.get_json()
    user_text = data.get("text", "")

    try:
        intent = parse_intent(user_text)
    except Exception as e:
        return jsonify({"status": "error", "reason": str(e)}), 400

    result = ENFORCER.enforce(AUTHORITY, intent)

    if result["status"] == "blocked":
        intent_hash = hashlib.sha256(user_text.encode()).hexdigest()
        reason_hash = hashlib.sha256(result["reason"].encode()).hexdigest()

        try:
            onchain = emit_blocked(RPC_URL, CONTRACT_ADDRESS, PRIVATE_KEY, intent_hash, reason_hash)
            etherscan = f"https://sepolia.etherscan.io/tx/{onchain['tx_hash']}"
            tx_hash = onchain["tx_hash"]
        except Exception:
            etherscan = None
            tx_hash = None

        return jsonify({
            "status": "blocked",
            "reason": result["reason"],
            "intent_hash": intent_hash,
            "tx_hash": tx_hash,
            "etherscan": etherscan,
        })

    record = result["record"]
    onchain = emit_provenance(
        RPC_URL,
        CONTRACT_ADDRESS,
        PRIVATE_KEY,
        record["epoch_commitment"],
        record["provenance_hash"],
    )

    return jsonify({
        "status": "approved",
        "epoch_commitment": record["epoch_commitment"],
        "intent_hash": record["provenance_hash"],
        "tx_hash": onchain["tx_hash"],
        "etherscan": f"https://sepolia.etherscan.io/tx/{onchain['tx_hash']}",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
