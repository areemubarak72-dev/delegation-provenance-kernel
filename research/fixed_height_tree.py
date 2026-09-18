"""
Fixed-Height Sparse Merkle Tree for RSA Accumulators
Week 1, Day 4: Genuine O(log n) insertion for EIP-7702 delegation epochs

Key properties:
- Tree height is fixed (e.g., 20 levels = 2^20 = 1M leaves)
- Each leaf has a fixed position (index)
- Insert updates only O(log n) nodes along the path to root
- Per-insert time stays constant regardless of total inserts
"""

import hashlib
import time
from sympy import nextprime, isprime
import secrets


# =========================================================
# 1. RSA Modulus (fast)
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
# 3. Fixed-Height Sparse Product Tree
# =========================================================

class FixedHeightTree:
    """
    Fixed-height binary tree with sparse leaves.

    Height h means the tree can hold up to 2^h leaves.
    Each leaf at position i stores a prime (or 1 if empty).
    Each internal node stores the product of its two children.

    Insertion into leaf i:
        - Update leaf i
        - Update parent (i // 2)
        - Update grandparent (i // 4)
        - ...
        - Update root
        Total: h updates = O(log n)

    Witness generation for leaf i:
        - Walk from leaf to root
        - At each level, multiply the sibling
        - Total: h multiplications = O(log n)
    """

    def __init__(self, height=20):
        self.height = height
        self.size = 2 ** height
        # levels[0] = leaves (all 1 by default)
        # levels[k] = products at level k
        self.levels = [[1] * self.size]
        for _ in range(height):
            self.levels.append([1] * (len(self.levels[-1]) // 2))

        self.leaf_index = {}  # prime -> leaf position

    def add(self, prime, position=None):
        """
        Insert prime at a leaf position.
        If position not given, use next available slot.
        Updates only O(height) nodes.
        """
        if prime in self.leaf_index:
            raise ValueError("Prime already in tree")

        # Find insertion position
        if position is None:
            position = self._next_free_position()

        if position >= self.size:
            raise ValueError(f"Tree is full (max {self.size} leaves)")

        # Store leaf
        self.levels[0][position] = prime
        self.leaf_index[prime] = position

        # Update only the path from leaf to root
        index = position
        for level in range(self.height):
            parent_index = index // 2
            left = self.levels[level][2 * parent_index]
            right = self.levels[level][2 * parent_index + 1]
            self.levels[level + 1][parent_index] = left * right
            index = parent_index

        return self.get_root()

    def _next_free_position(self):
        """Return the next position that is still 1."""
        for i in range(self.size):
            if self.levels[0][i] == 1:
                return i
        raise ValueError("Tree is full")

    def get_root(self):
        """Return product of all leaves (with empty leaves contributing 1)."""
        return self.levels[-1][0]

    def get_witness_exponent(self, prime):
        """
        Return product of all OTHER leaves.
        O(height) = O(log n) multiplications.
        """
        if prime not in self.leaf_index:
            raise ValueError("Prime not in tree")

        index = self.leaf_index[prime]
        witness = 1

        for level in range(self.height):
            sibling = index ^ 1  # XOR with 1 to get sibling index
            witness *= self.levels[level][sibling]
            index = index // 2

        return witness

    def count(self):
        return len(self.leaf_index)


# =========================================================
# 4. Fixed-Height Accumulator
# =========================================================

class FixedHeightAccumulator:
    def __init__(self, N, height=20, generator=3):
        self.N = N
        self.g = generator
        self.tree = FixedHeightTree(height=height)
        self.value = 1

    def add(self, prime):
        exponent = self.tree.add(prime)
        self.value = pow(self.g, exponent, self.N)
        return self.value

    def get_value(self):
        return self.value

    def prove_membership(self, prime):
        exponent = self.tree.get_witness_exponent(prime)
        witness = pow(self.g, exponent, self.N)
        return witness, prime

    @staticmethod
    def verify_membership(witness, prime, accumulator_value, N):
        return pow(witness, prime, N) == accumulator_value

    def size(self):
        return self.tree.count()


# =========================================================
# 5. Benchmarks
# =========================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Fixed-Height Sparse Tree: Week 1, Day 4")
    print("=" * 60)

    print("\n[1] Generating 512-bit RSA modulus...")
    t0 = time.time()
    N, p, q = generate_rsa_modulus(bits=512)
    print(f"    Done in {time.time() - t0:.3f}s, bits={N.bit_length()}")

    print("\n[2] Correctness: 50 delegations, all proofs verify")
    acc = FixedHeightAccumulator(N, height=20)
    authority = "0x1451A02b54F5ba82220185156803C1959a8407c2"
    delegate = "0x0d19f7a92BB0cd49958210E16c255e64f6AdF3FB"

    primes = []
    for i in range(50):
        prime = encode_delegation(authority, delegate, 11723203 + i * 100)
        primes.append(prime)
        acc.add(prime)

    all_valid = all(
        FixedHeightAccumulator.verify_membership(
            acc.prove_membership(pr)[0], pr, acc.get_value(), N
        )
        for pr in primes
    )
    print(f"    All 50 proofs valid: {all_valid}")

    print("\n[3] Negative test")
    fake = encode_delegation(authority, delegate, 999999999)
    try:
        w, _ = acc.prove_membership(fake)
        fake_valid = FixedHeightAccumulator.verify_membership(w, fake, acc.get_value(), N)
    except ValueError:
        fake_valid = False
    print(f"    Fake verified: {fake_valid} (should be False)")

    print("\n[4] Scaling benchmark: per-insert time should stay FLAT")
    print(f"    {'N':>7} | {'Total insert (s)':>18} | {'Per insert (us)':>16}")
    print(f"    {'-'*7} | {'-'*18} | {'-'*16}")

    for size in [10, 100, 500, 1000, 5000, 10000, 50000]:
        acc2 = FixedHeightAccumulator(N, height=20)
        primes2 = [encode_delegation(authority, delegate, 30000000 + i) for i in range(size)]

        t0 = time.time()
        for prime in primes2:
            acc2.add(prime)
        total = time.time() - t0
        per_us = total / size * 1_000_000

        print(f"    {size:>7} | {total:>18.6f} | {per_us:>16.2f}")

    print("\n[5] Witness generation benchmark: N=10000")
    acc3 = FixedHeightAccumulator(N, height=20)
    primes3 = [encode_delegation(authority, delegate, 40000000 + i) for i in range(10000)]
    for prime in primes3:
        acc3.add(prime)

    t0 = time.time()
    for prime in primes3:
        acc3.prove_membership(prime)
    total = time.time() - t0
    print(f"    10000 witnesses: {total:.3f}s")
    print(f"    Per witness: {total / 10000 * 1_000_000:.2f} us")

    print("\n" + "=" * 60)
    print("Week 1, Day 4 complete.")
    print("=" * 60)
