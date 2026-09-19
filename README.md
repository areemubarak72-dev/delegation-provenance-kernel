# Delegation Provenance Kernel → ProofMesh

Early research prototype. The HTTP path parses a narrow command, checks delegation bytecode and a Python policy, and optionally records a Sepolia event. **It does not transfer ETH, generate a ZK proof, or verify one.** The standalone circuits under `research/zk` are experimental: `membership.circom` does not enforce RSA membership and `modmul.circom` is not a complete non-native RSA arithmetic implementation.

## Run locally

Python 3.12 and Node 22 are the CI targets. From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env with your Sepolia RPC URL, then export it:
set -a
source backend/.env
set +a
python backend/app.py
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open the Vite URL. Commands: `Send 0.1 ETH to Alice`, `Send 5 ETH to Alice`.
Without RPC_URL the API starts, but state/policy requests return a configuration error. No fabricated chain state is substituted. Recording defaults to off. Explicitly enabling RECORD_ONCHAIN with a funded Sepolia PRIVATE_KEY submits event transactions; it does not execute the transfer. Keep this unauthenticated prototype on localhost. Debug mode is disabled. Rotate the previously committed provider token; deleting it from current code does not remove it from history.

## Result semantics

`status` is the policy decision, `executed` is always false, and `stages` reports intent parsing, policy checks, proof integration, and event recording separately. A reverted receipt never reports successful recording. Timeout/failure may leave confirmation unknown; inspect the signer history before retrying. `/api/zk-status` explicitly returns `not_integrated`. State and ZK status load independently in the dashboard.

## Verification

```sh
python -m unittest discover -s tests -v
cd frontend
npm ci
npm run build
```

Tests mock the chain and signer; they never submit transactions. These checks cover parsing precision, ambiguous input rejection, malformed API requests, receipt handling, and truthful proof status. They do not establish cryptographic soundness or deployed-contract correctness.

## Remaining Milestone 0 work

- Recover the actual Solidity contracts and deployment configuration; current ABI/address alone cannot reproduce or audit a deployment.
- Recover the newer local circuit/backend if the screenshots came from uncommitted work. Do not infer 128,519 constraints or successful ZK verification from UI screenshots.
- Define canonical action/policy commitments, durable records, replay protection, authenticated ownership and concurrent signer coordination.
- Implement and negatively test a sound proof statement before connecting it to authorization.

Then implement signed parent/child delegation with attenuation and revocation for ProofMesh. A research-only agent must not delegate purchase authority: child permissions must be a subset of its parent's. The coordinator should delegate research and purchase to separate branches when appropriate.
