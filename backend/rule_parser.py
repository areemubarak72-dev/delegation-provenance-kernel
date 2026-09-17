import re

ADDRESS_BOOK = {
    "alice": "0x4be9323dfad59dbac2f0e870067cd29e5bac41cd",
    "bob":   "0x000000000000000000000000000000000000dead",
}

def parse_intent(text):
    text_lower = text.lower()

    amount_match = re.search(r"(\d+(?:\.\d+)?)\s*eth", text_lower)
    if not amount_match:
        raise ValueError("No amount found in request")
    amount_eth = float(amount_match.group(1))
    amount_wei = int(amount_eth * 10**18)

    recipient = None
    for name, addr in ADDRESS_BOOK.items():
        if name in text_lower:
            recipient = addr
            break
    if not recipient:
        raise ValueError("Recipient not recognized")

    return {
        "action": "transfer",
        "to": recipient,
        "amount_wei": amount_wei,
        "asset": "ETH",
    }
