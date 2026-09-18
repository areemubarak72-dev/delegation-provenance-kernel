"""
Incremental Product Tree for RSA Accumulators
Week 1, Day 3: O(log n) insertion for EIP-7702 delegation epochs

Improvement over Day 2:
- Day 2: O(n) insertion (rebuild entire tree)
- Day 3: O(log n) insertion (update only root-to-leaf path)

Core idea:
- Leaves are always at level 0
- Each internal node = product of its two children
- On insert, only the parent chain of the new leaf is recomputed
"""

import hashlib
import time
from sympy import nextprime, isprime
import secrets


# =========================================================
# 1. RSA Modulus (fast version using known-safe primes)
# =========================================================

def generate_rsa_modulus(bits=512):
    """Generate RSA modulus N = p * q with 512-bit primes (fast)."""
    half = bits // 2
    p = _generate_prime(half)
    q = _generate_prime(half)
    while p == q:
        q = _generate_prime(half)
    return p * q, p, q


def _generate_prime(bits):
    """Generate a large prime. Not necessarily safe, but sufficient for research."""
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
    """Encode EIP-7702 delegation state as a large prime."""
    payload = f"{authority.lower()}|{delegate.lower()}|{block}"
    digest = hashlib.sha256(payload.encode()).digest()
    seed = int.from_bytes(digest, "big")
    return nextprime(seed)


# =========================================================
# 3. Incremental Product Tree
# =========================================================

class IncrementalProductTree:
    """
    Product tree with O(log n) insertion.

    Structure:
        levels[0] = leaves (individual primes)
        levels[1] = pairwise products of leaves
        levels[2] = pairwise products of level-1 nodes
        ...
        levels[-1] = [root product]

    Insertion:
        1. Append new prime to leaves
        2. Recompute only the parent chain of this new leaf
        3. Other nodes stay unchanged

    Witness generation for leaf at index i:
        1. Walk up from i to root
        2. At each level, multiply the sibling node
        3. O(log n) multiplications
    """

    def __init__(self):
        self.levels = [[]]
        self.leaf_index = {}

    def add(self, prime):
        """
        Insert a prime in O(log n) time.
        Returns the new root product.
        """
        if prime in self.leaf_index:
            raise ValueError("Prime already in tree")

        # Step 1: Append to leaf level
        index = len(self.levels[0])
        self.levels[0].append(prime)
        self.leaf_index[prime] = index

        # Step 2: Walk up, recompute only affected parents
        current_index = index
        level = 0

        while current_index > 0 or level == 0:
            # Compute parent index in next level
            parent_index = current_index // 2

            # Sibling in current level
            if current_index % 2 == 0:
                sibling_index = current_index + 1
            else:
                sibling_index = current_index - 1

            # Get or compute parent value
            if sibling_index < len(self.levels[level]):
                parent_value = self.levels[level][current_index] * self.levels[level][sibling_index]
            else:
                # No sibling yet; parent is just the child
                parent_value = self.levels[level][current_index]

            # Ensure next level exists
            if level + 1 >= len(self.levels):
                self.levels.append([])

            # Place parent at parent_index in next level
            next_level = self.levels[level + 1]
            while len(next_level) <= parent_index:
                next_level.append(1)

            next_level[parent_index] = parent_value

            # Move up
            current_index = parent_index
            level += 1

            # If we've reached a level with only one node, stop
            if current_index == 0 and len(self.levels[level]) == 1:
                # Trim trailing empty levels
                while len(self.levels) > 1 and len(self.levels[-1]) == 0:
                    self.levels.pop()
                break

        return self.get_root()

    def get_root(self):
        """Return product of all leaves."""
        if not self.levels or not self.levels[-1]:
            return 1
        return self.levels[-1][0]

    def get_witness_exponent(self, prime):
        """
        Return product of all OTHER primes (the witness exponent).
        O(log n) multiplications by walking up the tree.
        """
        if prime not in self.leaf_index:
            raise ValueError("Prime not in tree")

        index = self.leaf_index[prime]
        witness = 1
        level = 0

        while level < len(self.levels) - 1:
            if index % 2 == 0:
                sibling = index + 1
            else:
                sibling = index - 1

            if sibling < len(self.levels[level]):
                witness *= self.levels[level][sibling]

            index = index // 2
            level += 1

        return witness

    def size(self):
        return len(self.levels[0])


# =========================================================
# 4. Incremental Accumulator
# =========================================================

class IncrementalAccumulator:
    def __init__(self, N, generator=3):
        self.N = N
        self.g = generator
        self.tree = IncrementalProductTree()
        self.value = 1

    def add(self, prime):
        """Add delegation prime and update accumulator value in O(log n)."""
        exponent = self.tree.add(prime)
        self.value = pow(self.g, exponent, self.N)
        return self.value

    def get_value(self):
        return self.value

    def prove_membership(self, prime):
        """Generate membership witness."""
        exponent = self.tree.get_witness_exponent(prime)
        witness = pow(self.g, exponent, self.N)
        return witness, prime

    @staticmethod
    def verify_membership(witness, prime, accumulator_value, N):
        """O(1) verification."""
        return pow(witness, prime, N) == accumulator_value

    def size(self):
        return self.tree.size()


# =========================================================
# 5. Demo & Benchmarks
# =========================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Incremental Product Tree: Week 1, Day 3")
    print("=" * 60)

    print("\n[1] Generating 512-bit RSA modulus...")
    t0 = time.time()
    N, p, q = generate_rsa_modulus(bits=512)
    print(f"    Done in {time.time() - t0:.3f}s")
    print(f"    Modulus bit length: {N.bit_length()}")

    print("\n[2] Correctness test: 20 delegations, all proofs must verify")
    acc = IncrementalAccumulator(N)
    authority = "0x1451A02b54F5ba82220185156803C1959a8407c2"
    delegate = "0x0d19f7a92BB0cd49958210E16c255e64f6AdF3FB"

    primes = []
    for i in range(20):
        block = 11723203 + i * 100
        prime = encode_delegation(authority, delegate, block)
        primes.append(prime)
        acc.add(prime)

    all_valid = True
    for prime in primes:
        witness, _ = acc.prove_membership(prime)
        if not acc.verify_membership(witness, prime, acc.get_value(), N):
            all_valid = False
    print(f"    All 20 proofs valid: {all_valid}")

    print("\n[3] Negative test: fake delegation must NOT verify")
    fake = encode_delegation(authority, delegate, 999999999)
    try:
        w, _ = acc.prove_membership(fake)
        fake_valid = acc.verify_membership(w, fake, acc.get_value(), N)
    except ValueError:
        fake_valid = False
    print(f"    Fake delegation verified: {fake_valid} (should be False)")

    print("\n[4] Scaling benchmark: insert time vs N")
    print(f"    {'N':>6} | {'Insert total (s)':>18} | {'Per insert (ms)':>16}")
    print(f"    {'-'*6} | {'-'*18} | {'-'*16}")

    results = []
    for size in [10, 50, 100, 500, 1000, 5000]:
        acc2 = IncrementalAccumulator(N)
        primes2 = [encode_delegation(authority, delegate, 30000000 + i) for i in range(size)]

        t0 = time.time()
        for prime in primes2:
            acc2.add(prime)
        total = time.time() - t0
        per = total / size * 1000

        print(f"    {size:>6} | {total:>18.6f} | {per:>16.4f}")
        results.append((size, total, per))

    print("\n[5] Witness generation benchmark: N=1000")
    acc3 = IncrementalAccumulator(N)
    primes3 = [encode_delegation(authority, delegate, 40000000 + i) for i in range(1000)]
    for prime in primes3:
        acc3.add(prime)

    t0 = time.time()
    for prime in primes3:
        acc3.prove_membership(prime)
    total = time.time() - t0
    print(f"    Total for 1000 witnesses: {total:.3f}s")
    print(f"    Per witness: {total / 1000 * 1000:.4f}ms")

    print("\n[6] Scaling comparison (expected)")
    print("    Naive O(n): insert time grows quadratically")
    print("    Incremental O(log n): insert time grows logarithmically")
    print()
    print("    From the results above:")
    for size, total, per in results:
        print(f"      N={size:>5}: {per:.4f} ms per insert")

    print("\n" + "=" * 60)
    print("Week 1 Day 3 complete.")
    print("=" * 60)
