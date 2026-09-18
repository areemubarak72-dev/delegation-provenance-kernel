"""
Generate and verify a ZK proof that a prime is in the RSA accumulator.
"""
import json
import subprocess
from sympy import nextprime
import hashlib

MODULUS = 81598984465834894719238489185134176473463311005410189916608708884165415347481
ACCUMULATOR = 4763431264087935463085844812055273909151356266015522156934993338323737679218

AUTH = "0x1451A02b54F5ba82220185156803C1959a8407c2"
DELEG = "0x0d19f7a92BB0cd49958210E16c255e64f6AdF3FB"
BLOCK = 11723203

payload = f"{AUTH.lower()}|{DELEG.lower()}|{BLOCK}"
PRIME = nextprime(int.from_bytes(hashlib.sha256(payload.encode()).digest(), "big"))
WITNESS = 3


def main():
    print("=== ZK Membership Proof ===")
    print(f"Public:  accumulator = {ACCUMULATOR}")
    print(f"Public:  modulus     = {MODULUS}")
    print(f"Private: witness     = {WITNESS}")
    print(f"Private: prime       = {PRIME}")
    print()

    # Write circuit input
    input_data = {
        "witness": str(WITNESS),
        "prime": str(PRIME),
        "accumulator": str(ACCUMULATOR),
        "modulus": str(MODULUS),
    }
    with open("input.json", "w") as f:
        json.dump(input_data, f)
    print("[1] Input written: input.json")

    # Generate witness
    print("[2] Generating witness...")
    subprocess.run([
        "node", "membership_js/generate_witness.js",
        "membership_js/membership.wasm",
        "input.json",
        "witness.wtns"
    ], check=True)
    print("    Witness: witness.wtns")

    # Generate proof
    print("[3] Generating Groth16 proof...")
    subprocess.run([
        "snarkjs", "groth16", "prove",
        "membership_0001.zkey",
        "witness.wtns",
        "proof.json",
        "public.json"
    ], check=True)
    print("    Proof: proof.json")

    # Read proof
    with open("proof.json") as f:
        proof = json.load(f)
    with open("public.json") as f:
        public = json.load(f)

    print()
    print("=== PROOF ===")
    print(f"pi_a: {proof['pi_a'][:2]}")
    print(f"pi_b: {proof['pi_b'][0]}")
    print(f"pi_c: {proof['pi_c'][:2]}")
    print(f"public signals: {public}")
    print()

    # Verify proof
    print("[4] Verifying proof...")
    result = subprocess.run([
        "snarkjs", "groth16", "verify",
        "verification_key.json",
        "public.json",
        "proof.json"
    ], capture_output=True, text=True)
    print(result.stdout)
    print()


if __name__ == "__main__":
    main()
