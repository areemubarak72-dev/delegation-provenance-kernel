"""
ZK proof of modular multiplication: a * b ≡ c (mod N)
"""
import json
import subprocess

MODULUS = 81598984465834894719238489185134176473463311005410189916608708884165415347481
C = 4763431264087935463085844812055273909151356266015522156934993338323737679218

A = 12345678901234567890123456789012345678901234567890  # 50-digit number
B = (C * pow(A, -1, MODULUS)) % MODULUS
assert (A * B) % MODULUS == C, "Sanity check failed"
Q = (A * B - C) // MODULUS

print("=== ZK Modular Multiplication Proof ===")
print(f"Public:  modulus = {MODULUS}")
print(f"Public:  c       = {C}")
print(f"Private: a       = {A}")
print(f"Private: b       = {B}")
print(f"Private: q       = {Q}")
print()

input_data = {
    "a": str(A),
    "b": str(B),
    "q": str(Q),
    "modulus": str(MODULUS),
    "c": str(C),
}
with open("modmul_input.json", "w") as f:
    json.dump(input_data, f)
print("[1] Input written: modmul_input.json")

print("[2] Generating witness...")
subprocess.run([
    "node", "modmul_js/generate_witness.js",
    "modmul_js/modmul.wasm",
    "modmul_input.json",
    "modmul_witness.wtns"
], check=True)
print("    witness.wtns")

print("[3] Generating Groth16 proof...")
subprocess.run([
    "snarkjs", "groth16", "prove",
    "modmul_0001.zkey",
    "modmul_witness.wtns",
    "modmul_proof.json",
    "modmul_public.json"
], check=True)

with open("modmul_proof.json") as f:
    proof = json.load(f)
with open("modmul_public.json") as f:
    public = json.load(f)

print()
print("=== PROOF ===")
print(f"pi_a: {proof['pi_a'][:2]}")
print(f"public: {public}")
print()

print("[4] Verifying proof...")
result = subprocess.run([
    "snarkjs", "groth16", "verify",
    "modmul_vk.json",
    "modmul_public.json",
    "modmul_proof.json"
], capture_output=True, text=True)
print(result.stdout)
