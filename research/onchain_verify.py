"""
Unified Provenance + RSA Accumulator: end-to-end integration
"""

from web3 import Web3
from sympy import nextprime
import hashlib
import os
RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/alch_9lH5y1pKeuJX-pgNsdrcI"
CONTRACT_ADDRESS = "0xBA97b15362196d21e138426eb7770D1DBbBc536B"
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

ABI = [
    {"inputs": [{"name": "_modulus","type":"uint256"},{"name": "_initialAccumulator","type":"uint256"}],"stateMutability": "nonpayable","type": "constructor"},
    {"anonymous": False,"inputs":[{"indexed": True,"name":"authority","type":"address"},{"indexed": True,"name":"epochCommitment","type":"bytes32"},{"indexed": False,"name":"intentHash","type":"bytes32"},{"indexed": False,"name":"accumulatorValue","type":"uint256"},{"indexed": False,"name":"blockNumber","type":"uint256"}],"name": "ExecutionBound","type": "event"},
    {"anonymous": False,"inputs":[{"indexed": True,"name":"authority","type":"address"},{"indexed": True,"name":"intentHash","type":"bytes32"},{"indexed": False,"name":"reasonHash","type":"bytes32"},{"indexed": False,"name":"blockNumber","type":"uint256"}],"name": "ExecutionBlocked","type": "event"},
    {"anonymous": False,"inputs":[{"indexed": False,"name":"newAccumulator","type":"uint256"},{"indexed": False,"name":"prime","type":"uint256"},{"indexed": False,"name":"blockNumber","type":"uint256"}],"name": "PrimeAdded","type": "event"},
    {"anonymous": False,"inputs":[{"indexed": False,"name":"witness","type":"uint256"},{"indexed": False,"name":"prime","type":"uint256"},{"indexed": False,"name":"valid","type":"bool"},{"indexed": False,"name":"blockNumber","type":"uint256"}],"name": "MembershipVerified","type": "event"},
    {"inputs":[{"name": "epochCommitment","type":"bytes32"},{"name": "intentHash","type":"bytes32"}],"name": "approveExecution","outputs": [],"stateMutability": "nonpayable","type": "function"},
    {"inputs":[{"name": "intentHash","type":"bytes32"},{"name": "reasonHash","type":"bytes32"}],"name": "recordBlocked","outputs": [],"stateMutability": "nonpayable","type": "function"},
    {"inputs":[{"name": "prime","type": "uint256"}],"name": "addDelegation","outputs": [],"stateMutability": "nonpayable","type": "function"},
    {"inputs":[{"name": "witness","type": "uint256"},{"name": "prime","type":"uint256"}],"name": "verifyMembership","outputs": [{"type": "bool"}],"stateMutability": "nonpayable","type": "function"},
    {"inputs":[{"name": "witness","type": "uint256"},{"name": "prime","type":"uint256"}],"name": "verifyMembershipView","outputs": [{"type": "bool"}],"stateMutability": "view","type": "function"},
    {"inputs": [],"name": "accumulator","outputs": [{"type": "uint256"}],"stateMutability": "view","type": "function"},
    {"inputs": [],"name": "modulus","outputs": [{"type": "uint256"}],"stateMutability": "view","type": "function"},
    {"inputs": [],"name": "approvedCount","outputs": [{"type": "uint256"}],"stateMutability": "view","type": "function"},
    {"inputs": [],"name": "delegationCount","outputs": [{"type": "uint256"}],"stateMutability": "view","type": "function"},
]


def encode_delegation(authority, delegate, block):
    payload = f"{authority.lower()}|{delegate.lower()}|{block}"
    seed = int.from_bytes(hashlib.sha256(payload.encode()).digest(), "big")
    return nextprime(seed)


def send(w3, contract, fn, account, *args):
    nonce = w3.eth.get_transaction_count(account.address)
    tx = fn(*args).build_transaction({
        "chainId": 11155111,
        "gas": 500000,
        "maxFeePerGas": w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "nonce": nonce,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), receipt.gasUsed, receipt.status


def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    print("Wallet:", account.address)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=ABI,
    )

    mod = contract.functions.modulus().call()
    acc = contract.functions.accumulator().call()
    print("Modulus:", mod)
    print("Current accumulator:", acc)
    print()

    # Reference delegation (already added in previous run)
    auth = "0x1451A02b54F5ba82220185156803C1959a8407c2"
    deleg = "0x0d19f7a92BB0cd49958210E16c255e64f6AdF3FB"
    block_ref = 11723203
    prime = encode_delegation(auth, deleg, block_ref)
    print("Reference delegation prime:", prime)
    print()

    # ---- Step 1: Verify membership (read-only) ----
    print("Testing on-chain membership verification (read-only)...")
    witness = 3  # because only ONE delegation exists in the accumulator
    result_view = contract.functions.verifyMembershipView(witness, prime).call()
    print(f"  verifyMembershipView(witness=3, prime) -> {result_view}")
    print()

    # ---- Step 2: Verify membership (transaction, to measure gas) ----
    print("Submitting verifyMembership() as a transaction...")
    tx, gas, status = send(w3, contract, contract.functions.verifyMembership, account, witness, prime)
    print(f"  tx: {tx}")
    print(f"  gas: {gas}, status: {status}")
    print()

    # ---- Step 3: Negative test - fake prime should fail ----
    print("Negative test: fake prime should return False")
    fake_prime = encode_delegation(auth, deleg, 999999999)
    fake_result = contract.functions.verifyMembershipView(witness, fake_prime).call()
    print(f"  verifyMembershipView(witness=3, fake_prime) -> {fake_result} (should be False)")
    print()

    # ---- Step 4: Read counters ----
    print("Final state:")
    print("  approvedCount:", contract.functions.approvedCount().call())
    print("  delegationCount:", contract.functions.delegationCount().call())


if __name__ == "__main__":
    main()
