"""Deliberately narrow command grammar; this is not an LLM parser."""
import re

ADDRESS_BOOK = {
    "alice": "0x4be9323dfad59dbac2f0e870067cd29e5bac41cd",
    "bob": "0x000000000000000000000000000000000000dead",
}
COMMAND = re.compile(r"\s*(?:send|transfer)\s+(\d+)(?:\.(\d{1,18}))?\s+eth\s+to\s+(alice|bob)\s*", re.I)


def parse_intent(text):
    if not isinstance(text, str) or len(text) > 500:
        raise ValueError("Provide a command of at most 500 characters")
    match = COMMAND.fullmatch(text)
    if not match:
        raise ValueError("Use: Send <positive amount> ETH to Alice or Bob (up to 18 decimal places)")
    whole, fraction, name = match.groups()
    amount = int(whole) * 10**18 + int((fraction or "").ljust(18, "0"))
    if not 0 < amount < 2**256:
        raise ValueError("Amount must be positive and fit uint256")
    return {"action": "transfer", "to": ADDRESS_BOOK[name.lower()], "amount_wei": amount, "asset": "ETH"}
