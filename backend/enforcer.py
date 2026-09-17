from web3 import Web3
import hashlib
import json
import time

class Enforcer:
    def __init__(self, rpc_url, policy):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.policy = policy
        # policy = {
        #   "max_amount_wei": int,
        #   "allowed_recipients": [list of addresses],
        # }

    def _commit(self, authority, delegate, block):
        payload = f"{authority}|{delegate}|{block}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def current_epoch(self, authority):
        block = self.w3.eth.block_number
        code = self.w3.eth.get_code(authority, block_identifier=block)
        code_hex = code.hex()
        delegate = "0x" + code_hex[6:46] if code_hex.startswith("ef0100") else None
        return {
            "authority": authority,
            "delegate": delegate,
            "block": block,
            "commitment": self._commit(authority, delegate, block),
        }

    def check_intent(self, intent):
        errors = []
        if intent["amount_wei"] > self.policy["max_amount_wei"]:
            errors.append("amount exceeds policy max")
        if intent["to"].lower() not in [a.lower() for a in self.policy["allowed_recipients"]]:
            errors.append("recipient not in allowed list")
        return errors

    def enforce(self, authority, intent):
        # Step 1: read current epoch
        epoch = self.current_epoch(authority)

        # Step 2: refuse if not delegated
        if epoch["delegate"] is None:
            return {"status": "blocked", "reason": "no active delegation"}

        # Step 3: policy check
        errors = self.check_intent(intent)
        if errors:
            return {"status": "blocked", "reason": "; ".join(errors)}

        # Step 4: bind intent to epoch
        record = {
            "authority": authority,
            "epoch_commitment": epoch["commitment"],
            "epoch_block": epoch["block"],
            "delegate_at_binding": epoch["delegate"],
            "tx_intent": intent,
            "bound_at": int(time.time()),
        }
        payload = json.dumps(record, sort_keys=True)
        record["provenance_hash"] = hashlib.sha256(payload.encode()).hexdigest()

        return {"status": "approved", "record": record}
