import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000";

export default function App() {
  const [text, setText] = useState("Send 0.1 ETH to Alice");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState(null);

  async function loadState() {
    try {
      const res = await axios.get(`${API}/api/state`);
      setState(res.data);
    } catch (e) {
      setState(null);
    }
  }

  useEffect(() => {
    loadState();
    const interval = setInterval(loadState, 15000);
    return () => clearInterval(interval);
  }, []);

  async function submit() {
    setLoading(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/api/process`, { text });
      setResult(res.data);
      loadState();
    } catch (e) {
      setResult({ status: "error", reason: e.message });
    }
    setLoading(false);
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#e2e8f0", padding: 24, fontFamily: "system-ui" }}>
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        <h1 style={{ fontSize: 36, fontWeight: "bold", textAlign: "center", marginBottom: 8, color: "#60a5fa" }}>
          Delegation Provenance Kernel
        </h1>
        <p style={{ textAlign: "center", color: "#94a3b8", marginBottom: 32 }}>
          Bind every AI-agent transaction to a verifiable EIP-7702 delegation epoch.
        </p>

        {state && (
          <div style={{ marginBottom: 24, padding: 20, background: "#1e293b", border: "1px solid #334155", borderRadius: 12 }}>
            <h2 style={{ fontSize: 14, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1, marginBottom: 16 }}>
              On-Chain State
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 16 }}>
              <Stat label="Approved" value={state.approvedCount} color="#4ade80" />
              <Stat label="Blocked" value={state.blockedCount} color="#f87171" />
              <Stat label="Delegations" value={state.delegationCount} color="#60a5fa" />
              <Stat label="Modulus bits" value="256" color="#c084fc" />
            </div>
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #334155" }}>
              <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 4 }}>RSA Accumulator</div>
              <div style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all", color: "#cbd5e1" }}>
                {state.accumulator}
              </div>
            </div>
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <a
                href={`https://sepolia.etherscan.io/address/${state.contract}`}
                target="_blank"
                rel="noreferrer"
                style={{ color: "#60a5fa", textDecoration: "none" }}
              >
                View contract on Sepolia Etherscan →
              </a>
            </div>
          </div>
        )}

        <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
          <label style={{ display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 8 }}>
            AI Agent Transaction Request
          </label>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{
              width: "100%", background: "#0f172a", border: "1px solid #475569",
              borderRadius: 8, padding: "12px 16px", fontSize: 16, color: "#e2e8f0", boxSizing: "border-box"
            }}
          />
          <button
            onClick={submit}
            disabled={loading}
            style={{
              marginTop: 16, width: "100%",
              background: loading ? "#334155" : "#2563eb",
              color: "white", border: "none", borderRadius: 8, padding: "14px 0",
              fontSize: 16, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer"
            }}
          >
            {loading ? "Processing…" : "Submit"}
          </button>
        </div>

        {result && (
          <div style={{
            marginTop: 24, borderRadius: 12, padding: 24,
            background: result.status === "approved" ? "rgba(22,101,52,0.3)" : "rgba(127,29,29,0.3)",
            border: `1px solid ${result.status === "approved" ? "#166534" : "#991b1b"}`
          }}>
            <div style={{
              fontSize: 20, fontWeight: "bold", marginBottom: 16,
              color: result.status === "approved" ? "#4ade80" : "#f87171"
            }}>
              {result.status === "approved" ? "✓ APPROVED" : "✗ BLOCKED"}
            </div>

            {result.reason && <div style={{ color: "#cbd5e1", marginBottom: 12 }}>Reason: {result.reason}</div>}

            {result.epoch_commitment && (
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                <div style={{ color: "#94a3b8" }}>Epoch commitment:</div>
                <div style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all", color: "#e2e8f0" }}>
                  {result.epoch_commitment}
                </div>
              </div>
            )}

            {result.intent_hash && (
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                <div style={{ color: "#94a3b8" }}>Intent hash:</div>
                <div style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all", color: "#e2e8f0" }}>
                  {result.intent_hash}
                </div>
              </div>
            )}

            {result.etherscan && (
              <a href={result.etherscan} target="_blank" rel="noreferrer"
                 style={{ display: "inline-block", marginTop: 16, color: "#60a5fa" }}>
                View on Sepolia Etherscan →
              </a>
            )}
          </div>
        )}

        <div style={{ marginTop: 32, paddingTop: 24, borderTop: "1px solid #334155", fontSize: 12, color: "#64748b", textAlign: "center" }}>
          RSA accumulator + zero-knowledge proofs · EIP-7702 delegation provenance
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 28, fontWeight: "bold", color }}>{value}</div>
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1, marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
}
