"""
Trapdoor-Free RSA Accumulator with Product Tree
Week 1, Day 2: Production-grade accumulator for EIP-7702 delegation epochs

Key properties:
- Insert: O(log n) tree updates
- Witness generation: O(log n) multiplications
- Witness size: O(1) — single group element
- Verification: O(1) — one modular exponentiation
- No trapdoor needed for witness computation
"""

import hashlib
import time
from sympy import nextprime, isprime
import secrets


# =========================================================
# 1. RSA Modulus Generation (one-time trusted setup)
# =========================================================

def generate_rsa_modulus(bits=2048):
    """
    Generate RSA modulus N = p * q with safe primes.
    In production, this would be an MPC ceremony.
    For research, local generation is fine.
    """
    half = bits // 2
    p = _generate_safe_prime(half)
    q = _generate_safe_prime(half)
    while p == q:
        q = _generate_safe_prime(half)
    return p * q, p, q


def _generate_safe_prime(bits):
    while True:
        q = secrets.randbits(bits)
        q |= (1 << (bits - 1))
        q |= 1
        if not isprime(q):
            continue
        p = 2 * q + 1
        if isprime(p):
            return p


# =========================================================
# 2. EIP-7702 Delegation State Encoding
# =========================================================

def encode_delegation(authority, delegate, block):
    """
    Encode an EIP-7702 delegation state as a large prime.
    Deterministic: same inputs always produce same prime.
    Collision-resistant: SHA-256 based.
    """
    payload = f"{authority.lower()}|{delegate.lower()}|{block}"
    digest = hashlib.sha256(payload.encode()).digest()
    seed = int.from_bytes(digest, "big")
    return nextprime(seed)


def encode_revocation(authority, block):
    """Encode a delegation revocation (zero-address delegate)."""
    return encode_delegation(
        authority,
        "0x0000000000000000000000000000000000000000",
        block,
    )


# =========================================================
# 3. Product Tree
# =========================================================

class ProductTree:
    """
    Balanced binary tree of prime products.

    Level 0 (leaves):      [p1, p2, p3, ..., pn]
    Level 1:               [p1*p2, p3*p4, ...]
    Level k (root):        [p1*p2*...*pn]

    The root is the accumulator exponent.
    For any leaf pi, the witness exponent is the product of all OTHER leaves,
    computed by multiplying sibling nodes along the path to the root.
    """

    def __init__(self, primes=None):
        self.levels = []          # levels[0] = leaves, levels[-1] = root
        self.leaf_index = {}      # prime -> index in level 0
        if primes:
            self._build(primes)

    def _build(self, primes):
        self.levels = [list(primes)]
        self.leaf_index = {p: i for i, p in enumerate(primes)}

        current = list(primes)
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                if i + 1 < len(current):
                    next_level.append(current[i] * current[i + 1])
                else:
                    next_level.append(current[i])
            self.levels.append(next_level)
            current = next_level

    def add(self, prime):
        """
        Insert a new prime (delegation) into the tree.
        Returns the new root exponent.
        """
        if not self.levels:
            self._build([prime])
            return self.get_root()

        # Append to leaf level and recompute tree
        # (A production version would do incremental insertion in O(log n);
        #  this prototype rebuilds for simplicity and correctness.)
        self._build(self.levels[0] + [prime])
        return self.get_root()

    def get_root(self):
        """Return the root exponent (product of all primes)."""
        if not self.levels:
            return 1
        return self.levels[-1][0]

    def get_witness_exponent(self, prime):
        """
        Return the product of all OTHER primes.
        This is the witness exponent for `prime`'s membership proof.
        Runs in O(log n) by multiplying siblings along the path to root.
        """
        if prime not in self.leaf_index:
            raise ValueError("Prime not in tree")

        index = self.leaf_index[prime]
        witness = 1

        for level in self.levels:
            # Sibling is at index +/- 1 in the same level
            if index % 2 == 0:
                sibling = index + 1
            else:
                sibling = index - 1

            if sibling < len(level):
                witness *= level[sibling]

            # Move up: parent index in next level
            index = index // 2

        return witness

    def size(self):
        return len(self.levels[0]) if self.levels else 0


# =========================================================
# 4. Accumulator (combines tree + RSA group)
# =========================================================

class TrapdoorFreeAccumulator:
    """
    RSA accumulator using a product tree for O(log n) witness generation.
    No trapdoor is needed for adding elements or generating witnesses.
    The trapdoor (p, q) is only needed for deletion, which we don't support.
    """

    def __init__(self, N, generator=3):
        self.N = N
        self.g = generator
        self.tree = ProductTree()

    def add(self, prime):
        """
        Add a delegation prime to the accumulator.
        Updates the tree and recomputes the accumulator value: A = g^(product) mod N
        """
        self.tree.add(prime)
        exponent = self.tree.get_root()
        self.value = pow(self.g, exponent, self.N)
        return self.value

    def get_value(self):
        return self.value

    def prove_membership(self, prime):
        """
        Generate a witness for `prime` being in the accumulator.
        Returns (witness_value, prime).
        Verification: witness_value^prime == accumulator_value (mod N)
        """
        exponent = self.tree.get_witness_exponent(prime)
        witness = pow(self.g, exponent, self.N)
        return witness, prime

    @staticmethod
    def verify_membership(witness, prime, accumulator_value, N):
        """
        Verify that `prime` is in the accumulator.
        Runs in O(1): one modular exponentiation.
        """
        return pow(witness, prime, N) == accumulator_value

    def size(self):
        return self.tree.size()


# =========================================================
# 5. Demo & Benchmarks
# =========================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Trapdoor-Free RSA Accumulator: Week 1 Day 2")
    print("=" * 60)

    print("\n[1] Generating RSA modulus (2048-bit)...")
    t0 = time.time()
    N, p, q = generate_rsa_modulus(bits=2048)
    print(f"    Done in {time.time() - t0:.2f}s")
    print(f"    Modulus bit length: {N.bit_length()}")

    print("\n[2] Building accumulator with 100 real delegation states...")
    acc = TrapdoorFreeAccumulator(N)

    authority = "0x1451A02b54F5ba82220185156803C1959a8407c2"
    delegate = "0x0d19f7a92BB0cd49958210E16c255e64f6AdF3FB"

    primes = []
    for i in range(100):
        block = 11723203 + i * 100
        prime = encode_delegation(authority, delegate, block)
        primes.append(prime)
        acc.add(prime)

    print(f"    Accumulator size: {acc.size()} elements")
    print(f"    Accumulator value: {str(acc.get_value())[:60]}...")

    print("\n[3] Generating and verifying 100 membership proofs...")
    t0 = time.time()
    all_valid = True
    for prime in primes:
        witness, _ = acc.prove_membership(prime)
        if not acc.verify_membership(witness, prime, acc.get_value(), N):
            all_valid = False
    print(f"    All proofs valid: {all_valid}")
    print(f"    Total time for 100 proofs: {time.time() - t0:.3f}s")

    print("\n[4] Single proof size (bytes)...")
    witness, _ = acc.prove_membership(primes[0])
    witness_bytes = witness.to_bytes((witness.bit_length() + 7) // 8, "big")
    print(f"    Witness size: {len(witness_bytes)} bytes")

    print("\n[5] Negative test: fake delegation should NOT verify...")
    fake_prime = encode_delegation(authority, delegate, 999999999)
    try:
        fake_witness, _ = acc.prove_membership(fake_prime)
        fake_valid = acc.verify_membership(fake_witness, fake_prime, acc.get_value(), N)
    except ValueError:
        fake_valid = False
    print(f"    Fake delegation verified: {fake_valid} (should be False)")

    print("\n[6] Scaling test: proof generation time vs number of delegations")
    print(f"    {'N':>6} | {'Insert (s)':>12} | {'Witness avg (ms)':>18}")
    print(f"    {'-'*6} | {'-'*12} | {'-'*18}")

    for size in [10, 50, 100, 200]:
        acc2 = TrapdoorFreeAccumulator(N)
        primes2 = [encode_delegation(authority, delegate, 20000000 + i) for i in range(size)]

        t0 = time.time()
        for prime in primes2:
            acc2.add(prime)
        insert_time = time.time() - t0

        t0 = time.time()
        for prime in primes2:
            acc2.prove_membership(prime)
        witness_time = (time.time() - t0) / size * 1000  # ms per proof

        print(f"    {size:>6} | {insert_time:>12.4f} | {witness_time:>18.4f}")

    print("\n" + "=" * 60)
    print("Week 1 Day 2 complete.")
    print("=" * 60)
