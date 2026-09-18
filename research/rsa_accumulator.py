"""
RSA Accumulator for EIP-7702 Delegation Epochs
Week 1, Day 1: Minimal working prototype
"""

import hashlib
from sympy import nextprime, isprime
import secrets

# ---------------------------------------------------------
# 1. RSA Modulus Generation (trusted setup, done once)
# ---------------------------------------------------------

def generate_rsa_modulus(bits=2048):
    """
    Generate an RSA modulus N = p * q where p, q are safe primes.
    In a real system, this would be generated via MPC ceremony.
    For research prototype, we generate locally.
    """
    half = bits // 2

    p = _generate_safe_prime(half)
    q = _generate_safe_prime(half)

    while p == q:
        q = _generate_safe_prime(half)

    N = p * q
    return N, p, q


def _generate_safe_prime(bits):
    """Generate a safe prime: p = 2q + 1 where q is also prime."""
    while True:
        q = secrets.randbits(bits)
        q |= (1 << (bits - 1))  # ensure top bit set
        q |= 1                   # ensure odd
        if not isprime(q):
            continue
        p = 2 * q + 1
        if isprime(p):
            return p


# ---------------------------------------------------------
# 2. Encode Delegation State as Prime
# ---------------------------------------------------------

def encode_delegation(authority, delegate, block):
    """
    Encode an EIP-7702 delegation state as a prime number.

    authority: EOA address that signed the delegation (hex string)
    delegate:  contract address it delegated to (hex string)
    block:     block number where this delegation was active

    Returns a large prime uniquely derived from this state.
    """
    payload = f"{authority.lower()}|{delegate.lower()}|{block}"
    digest = hashlib.sha256(payload.encode()).digest()

    # Convert digest to integer, then find next prime
    seed = int.from_bytes(digest, "big")
    prime = nextprime(seed)

    return prime


def encode_revocation(authority, block):
    """
    Encode a delegation revocation (delegate = zero address).
    """
    return encode_delegation(
        authority,
        "0x0000000000000000000000000000000000000000",
        block,
    )


# ---------------------------------------------------------
# 3. RSA Accumulator
# ---------------------------------------------------------

class RSAAccumulator:
    def __init__(self, N):
        """
        N: RSA modulus (product of two secret safe primes).
        The accumulator starts at g = 3 (any generator of QR_N).
        """
        self.N = N
        self.value = 3
        self.elements = []  # for debugging only; not used in proofs

    def add(self, prime):
        """Add an element (prime) to the accumulator: A <- A^prime mod N."""
        self.value = pow(self.value, prime, self.N)
        self.elements.append(prime)

    def remove(self, prime):
        """
        Remove an element. Requires knowing the trapdoor (p, q).
        For prototype, we skip this — Week 2 will implement it.
        """
        raise NotImplementedError("Removal requires trapdoor. Week 2.")

    def get_value(self):
        return self.value


# ---------------------------------------------------------
# 4. Membership Proof (Witness)
# ---------------------------------------------------------

def compute_membership_witness(accumulator, prime, N):
    """
    Compute witness W = A^(product of all other primes) mod N.
    Given W and the prime, a verifier can check:
        W^prime == A (mod N)

    For prototype, this recomputes the product directly.
    Week 2 will use trapdoor-free witness computation.
    """
    product = 1
    for p in accumulator.elements:
        if p != prime:
            product *= p
    witness = pow(3, product, N)
    return witness


def verify_membership(witness, prime, accumulator_value, N):
    """
    Verify that `prime` is in the accumulator:
        witness^prime == accumulator_value (mod N)
    """
    return pow(witness, prime, N) == accumulator_value


# ---------------------------------------------------------
# 5. Demo: Encode EIP-7702 Delegations and Prove Membership
# ---------------------------------------------------------

if __name__ == "__main__":
    print("Generating RSA modulus (this takes a few seconds)...")
    N, p, q = generate_rsa_modulus(bits=512)  # small for speed; 2048 for real
    print(f"Modulus N = {N}")
    print(f"Prime p   = {p}")
    print(f"Prime q   = {q}")
    print()

    # Real delegation from Sepolia
    authority = "0x1451A02b54F5ba82220185156803C1959a8407c2"
    delegate  = "0x0d19f7a92BB0cd49958210E16c255e64f6AdF3FB"
    block     = 11723203

    prime1 = encode_delegation(authority, delegate, block)
    print(f"Delegation 1 prime: {prime1}")

    # Second delegation (different block, same authority)
    prime2 = encode_delegation(authority, delegate, 11724000)
    print(f"Delegation 2 prime: {prime2}")
    print()

    # Build accumulator
    acc = RSAAccumulator(N)
    acc.add(prime1)
    acc.add(prime2)
    print(f"Accumulator value: {acc.get_value()}")
    print()

    # Generate and verify membership proof for prime1
    witness1 = compute_membership_witness(acc, prime1, N)
    valid1 = verify_membership(witness1, prime1, acc.get_value(), N)
    print(f"Membership proof for delegation 1: {valid1}")

    # Generate and verify membership proof for prime2
    witness2 = compute_membership_witness(acc, prime2, N)
    valid2 = verify_membership(witness2, prime2, acc.get_value(), N)
    print(f"Membership proof for delegation 2: {valid2}")
    print()

    # Test negative case: a fake prime should NOT verify
    fake = encode_delegation(authority, delegate, 99999999)
    witness_fake = compute_membership_witness(acc, fake, N)
    valid_fake = verify_membership(witness_fake, fake, acc.get_value(), N)
    print(f"Fake delegation proof (should be False): {valid_fake}")
