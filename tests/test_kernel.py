import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from rule_parser import parse_intent
import app as api


class ParserTests(unittest.TestCase):
    def test_exact_wei(self):
        self.assertEqual(parse_intent("Send 0.000000000000000001 ETH to Alice")["amount_wei"], 1)
        self.assertEqual(parse_intent("Transfer 0.100000000000000001 ETH to Bob")["amount_wei"], 100000000000000001)

    def test_ambiguous_or_invalid_commands(self):
        for text in [None, 5, "Send -1 ETH to Alice", "Don't send 1 ETH to Alice", "Send 1 ETH to Alice and Bob", "Send 0 ETH to Bob", "Send 0.0000000000000000001 ETH to Alice", "Send 1e3 ETH to Bob"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_intent(text)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = api.app.test_client()
        self.enforcer = Mock()
        self.enforcer.enforce.return_value = {"status": "approved", "record": {"epoch_commitment": "aa"*32, "provenance_hash": "bb"*32}}

    def test_zk_is_explicitly_not_integrated(self):
        data = self.client.get("/api/zk-status").get_json()
        self.assertFalse(data["verified_locally"])
        self.assertFalse(data["verified_onchain"])

    def test_bad_json_does_not_reach_enforcer(self):
        with patch.object(api, "ENFORCER", self.enforcer):
            for data in [None, [], {"text": 7}, {}]:
                self.assertEqual(self.client.post("/api/process", json=data).status_code, 400)
        self.enforcer.enforce.assert_not_called()

    def test_recording_disabled_does_not_sign(self):
        with patch.object(api, "ENFORCER", self.enforcer), patch.object(api, "RECORD_ONCHAIN", False), patch.object(api, "emit_provenance") as emit:
            data = self.client.post("/api/process", json={"text": "Send 0.1 ETH to Alice"}).get_json()
        emit.assert_not_called()
        self.assertEqual(data["stages"], {"intent": "done", "policy": "done", "proof": "not_integrated", "onchain": "not_attempted"})
        self.assertFalse(data["executed"])

    def test_receipt_status_controls_recording_result(self):
        for receipt_status, stage in [(0, "error"), (1, "done")]:
            with self.subTest(receipt_status=receipt_status), patch.object(api, "ENFORCER", self.enforcer), patch.object(api, "RECORD_ONCHAIN", True), patch.object(api, "PRIVATE_KEY", "test-only"), patch.object(api, "emit_provenance", return_value={"tx_hash": "cc"*32, "status": receipt_status}):
                data = self.client.post("/api/process", json={"text": "Send 0.1 ETH to Alice"}).get_json()
                self.assertEqual(data["stages"]["onchain"], stage)
                self.assertEqual(data["stages"]["proof"], "not_integrated")

    def test_rpc_error_does_not_leak_provider_credentials(self):
        self.enforcer.enforce.side_effect = RuntimeError("secret-provider-url")
        with patch.object(api, "ENFORCER", self.enforcer):
            res = self.client.post("/api/process", json={"text": "Send 1 ETH to Alice"})
        self.assertEqual(res.status_code, 502)
        self.assertNotIn("secret-provider", res.get_data(as_text=True))

    def test_blocked_policy_remains_blocked_when_recording_fails(self):
        self.enforcer.enforce.return_value = {"status": "blocked", "reason": "amount exceeds policy max"}
        with patch.object(api, "ENFORCER", self.enforcer), patch.object(api, "RECORD_ONCHAIN", True), patch.object(api, "PRIVATE_KEY", "test-only"), patch.object(api, "emit_blocked", side_effect=RuntimeError()):
            data = self.client.post("/api/process", json={"text": "Send 5 ETH to Alice"}).get_json()
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["stages"]["onchain"], "error")


if __name__ == "__main__":
    unittest.main()
