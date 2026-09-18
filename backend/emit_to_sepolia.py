from web3 import Web3

ABI = [
    {"anonymous": False, "inputs": [
        {"indexed": True,  "name": "authority",       "type": "address"},
        {"indexed": True,  "name": "epochCommitment", "type": "bytes32"},
        {"indexed": False, "name": "intentHash",      "type": "bytes32"},
        {"indexed": False, "name": "accumulatorValue","type": "uint256"},
        {"indexed": False, "name": "blockNumber",     "type": "uint256"},
    ], "name": "ExecutionBound", "type": "event"},
    {"anonymous": False, "inputs": [
        {"indexed": True,  "name": "authority",   "type": "address"},
        {"indexed": True,  "name": "intentHash",  "type": "bytes32"},
        {"indexed": False, "name": "reasonHash",  "type": "bytes32"},
        {"indexed": False, "name": "blockNumber", "type": "uint256"},
    ], "name": "ExecutionBlocked", "type": "event"},
    {"anonymous": False, "inputs": [
        {"indexed": False, "name": "newAccumulator", "type": "uint256"},
        {"indexed": False, "name": "prime",          "type": "uint256"},
        {"indexed": False, "name": "blockNumber",    "type": "uint256"},
    ], "name": "PrimeAdded", "type": "event"},
    {"inputs": [
        {"name": "epochCommitment", "type": "bytes32"},
        {"name": "intentHash",      "type": "bytes32"},
    ], "name": "approveExecution", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [
        {"name": "intentHash", "type": "bytes32"},
        {"name": "reasonHash", "type": "bytes32"},
    ], "name": "recordBlocked", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [
        {"name": "prime", "type": "uint256"},
    ], "name": "addDelegation", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]

def _send(rpc_url, contract_address, private_key, fn_name, *args):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = w3.eth.account.from_key(private_key)
    contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=ABI)

    fn = getattr(contract.functions, fn_name)(*args)
    nonce = w3.eth.get_transaction_count(account.address)

    tx = fn.build_transaction({
        "chainId": 11155111,
        "gas": 500000,
        "maxFeePerGas": w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "nonce": nonce,
    })

    signed = w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return {"tx_hash": tx_hash.hex(), "block": receipt.blockNumber, "status": receipt.status}

def emit_provenance(rpc_url, contract_address, private_key, epoch_commitment_hex, intent_hash_hex):
    epoch_bytes = bytes.fromhex(epoch_commitment_hex.replace("0x", ""))
    intent_bytes = bytes.fromhex(intent_hash_hex.replace("0x", ""))
    return _send(rpc_url, contract_address, private_key, "approveExecution", epoch_bytes, intent_bytes)

def emit_blocked(rpc_url, contract_address, private_key, intent_hash_hex, reason_hash_hex):
    intent_bytes = bytes.fromhex(intent_hash_hex.replace("0x", ""))
    reason_bytes = bytes.fromhex(reason_hash_hex.replace("0x", ""))
    return _send(rpc_url, contract_address, private_key, "recordBlocked", intent_bytes, reason_bytes)
