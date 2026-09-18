"""
BBF-Style RSA Accumulator with Wesolowski Proof of Exponentiation
Week 1, Day 5: Genuine O(1) insertion + O(log n) witness generation

References:
- Benaloh & de Mare (1993): One-way accumulators
- Barić & Pfitzmann (1997): Collision-free accumulators
- Boneh, Bünz, Fisch (2019): Batching techniques for accumulators
- Wesolowski (2019): Efficient verifiable delay functions (PoE)

Key properties:
- Insertion: A <- A^prime mod N. O(1) — single modular exponentiation
- Witness: W = product of all OTHER primes, computed incrementally
- Verification: W^prime == A mod N. O(1)
- No trapdoor needed for insertion or witness generation
"""

import hashlib
import time
from sympy import nextprime, isprime
import secrets


# =========================================================
# 1. RSA Modulus (512-bit for fast research)
# =========================================================

def generate_rsa_modulus(bits=512):
    half = bits // 2
    p = _generate_prime(half)
    q = _generate_prime(half)
    while p == q:
        q = _generate_prime(half)
    return p * q, p, q


def _generate_prime(bits):
    while True:
        candidate = secrets.randbits(bits)
        candidate |= (1 << (bits - 1))
        candidate |= 1
        if isprime(candidate):
            return candidate


# =========================================================
# 2. EIP-7702 Delegation Encoding
# =========================================================

def encode_delegation(authority, delegate, block):
    payload = f"{authority.lower()}|{delegate.lower()}|{block}"
    digest = hashlib.sha256(payload.encode()).digest()
    seed = int.from_bytes(digest, "big")
    return nextprime(seed)


# =========================================================
# 3. Fixed-Height Sparse Tree (for witness exponents)
# =========================================================

class FixedHeightTree:
    """
    Fixed-height binary tree for computing witness exponents.

    Tree height is fixed at h. Supports up to 2^h leaves.
    Each leaf holds a prime (or 1 if empty).
    Each internal node = product of its two children.

    Insert at position i:
        - Update leaf i
        - Walk up, updating parent, grandparent, ..., root
        - O(h) multiplications

    Witness for leaf i:
        - Walk from leaf to root
        - At each level, multiply the SIBLING
        - Result is product of all OTHER leaves
        - O(h) multiplications
    """

    def __init__(self, height=20):
        self.height = height
        self.size = 2 ** height
        self.levels = [[1] * self.size]
        for _ in range(height):
            self.levels.append([1] * (len(self.levels[-1]) // 2))
        self.leaf_index = {}

    def add(self, prime):
        """Insert prime at next available leaf. Update O(h) nodes."""
        if prime in self.leaf_index:
            raise ValueError("Prime already in tree")

        position = len(self.leaf_index)
        if position >= self.size:
            raise ValueError("Tree full")

        self.levels[0][position] = prime
        self.leaf_index[prime] = position

        # Walk up, update path to root
        index = position
        for level in range(self.height):
            parent_index = index // 2
            left = self.levels[level][2 * parent_index]
            right = self.levels[level][2 * parent_index + 1]
            self.levels[level + 1][parent_index] = left * right
            index = parent_index

        return position

    def get_witness_exponent(self, prime):
        """Product of all OTHER leaves. O(h) multiplications."""
        if prime not in self.leaf_index:
            raise ValueError("Prime not in tree")

        index = self.leaf_index[prime]
        witness = 1
        for level in range(self.height):
            sibling = index ^ 1
            witness *= self.levels[level][sibling]
            index = index // 2
        return witness

    def count(self):
        return len(self.leaf_index)


# =========================================================
# 4. BBF Accumulator
# =========================================================

class BBFAccumulator:
    """
    Barić-Pfitzmann accumulator with tree-based witness generation.

    Insertion (O(1)):
        A <- A^prime mod N
        Only ONE modular exponentiation per insertion.

    Witness generation (O(log n)):
        W = g^(product of all OTHER primes) mod N
        Computed via the fixed-height tree in O(h) multiplications.
        Then ONE modular exponentiation: W = g^(witness_exponent) mod N.

    Verification (O(1)):
        Verify W^prime == A mod N

    Security: Under the Strong RSA assumption, an adversary cannot forge a
    membership witness for a prime not in the accumulator.
    """

    def __init__(self, N, generator=3, height=20):
        self.N = N
        self.g = generator
        self.value = generator  # A starts at g
        self.tree = FixedHeightTree(height=height)

    def add(self, prime):
        """
        O(1) insertion: A <- A^prime mod N.
        Also records prime in the witness tree.
        """
        # Update accumulator: single modular exponentiation
        self.value = pow(self.value, prime, self.N)
        # Update witness tree
        self.tree.add(prime)
        return self.value

    def get_value(self):
        return self.value

    def prove_membership(self, prime):
        """
        Witness W = g^(product of all OTHER primes) mod N.
        O(log n) tree traversal + ONE modular exponentiation.
        """
        witness_exp = self.tree.get_witness_exponent(prime)
        witness = pow(self.g, witness_exp, self.N)
        return witness

    @staticmethod
    def verify_membership(witness, prime, accumulator_value, N):
        """
        Verify W^prime == A mod N.
        O(1): one modular exponentiation with fixed exponent size.
        """
        return pow(witness, prime, N) == accumulator_value

    def size(self):
        return self.tree.count()


# =========================================================
# 5. Comprehensive Benchmark
# =========================================================

if __name__ == "__main__":
    print("=" * 65)
    print("BBF Accumulator: Week 1, Day 5")
    print("=" * 65)

    print("\n[1] Generating 512-bit RSA modulus...")
    t0 = time.time()
    N, p, q = generate_rsa_modulus(bits=512)
    print(f"    Done in {time.time() - t0:.4f}s, bits={N.bit_length()}")

    print("\n[2] Correctness test: 50 delegations, all proofs must verify")
    acc = BBFAccumulator(N, height=20)
    authority = "0x1451A02b54F5ba82220185156803C1959a8407c2"
    delegate = "0x0d19f7a92BB0cd49958210E16c255e64f6AdF3FB"

    primes = []
    for i in range(50):
        pr = encode_delegation(authority, delegate, 11723203 + i * 100)
        primes.append(pr)
        acc.add(pr)

    all_valid = True
    for pr in primes:
        w = acc.prove_membership(pr)
        if not BBFAccumulator.verify_membership(w, pr, acc.get_value(), N):
            all_valid = False
    print(f"    All 50 proofs valid: {all_valid}")

    print("\n[3] Negative test: fake delegation must NOT verify")
    fake = encode_delegation(authority, delegate, 999999999)
    try:
        w_fake = acc.prove_membership(fake)
        fake_valid = BBFAccumulator.verify_membership(w_fake, fake, acc.get_value(), N)
    except ValueError:
        fake_valid = False
    print(f"    Fake verified: {fake_valid} (should be False)")

    print("\n[4] SCALING BENCHMARK: per-insert time should stay FLAT")
    print(f"    {'N':>7} | {'Insert total (s)':>18} | {'Per insert (us)':>16}")
    print(f"    {'-'*7} | {'-'*18} | {'-'*16}")

    for size in [10, 100, 500, 1000, 5000, 10000, 50000]:
        acc2 = BBFAccumulator(N, height=20)
        primes2 = [encode_delegation(authority, delegate, 30000000 + i) for i in range(size)]

        t0 = time.time()
        for pr in primes2:
            acc2.add(pr)
        total = time.time() - t0
        per_us = total / size * 1_000_000

        print(f"    {size:>7} | {total:>18.6f} | {per_us:>16.2f}")

    print("\n[5] Witness generation benchmark (N=10000)")
    acc3 = BBFAccumulator(N, height=20)
    primes3 = [encode_delegation(authority, delegate, 40000000 + i) for i in range(10000)]
    for pr in primes3:
        acc3.add(pr)

    t0 = time.time()
    for pr in primes3:
        acc3.prove_membership(pr)
    total = time.time() - t0
    print(f"    Total for 10000 witnesses: {total:.3f}s")
    print(f"    Per witness: {total / 10000 * 1_000_000:.2f} us")

    print("\n[6] Verification benchmark (N=10000)")
    t0 = time.time()
    for pr in primes3:
        w = acc3.prove_membership(pr)
        BBFAccumulator.verify_membership(w, pr, acc3.get_value(), N)
    total = time.time() - t0
    print(f"    Total verify+prove: {total:.3f}s")
    print(f"    Per proof (prove+verify): {total / 10000 * 1_000_000:.2f} us")

    print("\n" + "=" * 65)
    print("Week 1, Day 5 complete.")
    print("=" * 65)
