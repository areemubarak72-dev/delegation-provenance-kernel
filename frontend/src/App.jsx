import { useState } from "react";
import axios from "axios";

const API = "http://localhost:5000";

export default function App() {
  const [text, setText] = useState("Send 0.1 ETH to Alice");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/api/process`, { text });
      setResult(res.data);
    } catch (e) {
      setResult({ status: "error", reason: e.message });
    }
    setLoading(false);
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#e2e8f0", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, fontFamily: "system-ui" }}>
      <div style={{ width: "100%", maxWidth: 640 }}>
        <h1 style={{ fontSize: 36, fontWeight: "bold", textAlign: "center", marginBottom: 8, color: "#60a5fa" }}>
          Delegation Provenance Kernel
        </h1>
        <p style={{ textAlign: "center", color: "#94a3b8", marginBottom: 32 }}>
          Bind every AI-agent transaction to a verifiable EIP-7702 delegation epoch.
        </p>

        <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
          <label style={{ display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 8 }}>
            Transaction request
          </label>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{ width: "100%", background: "#0f172a", border: "1px solid #475569", borderRadius: 8, padding: "12px 16px", fontSize: 16, color: "#e2e8f0", boxSizing: "border-box" }}
          />
          <button
            onClick={submit}
            disabled={loading}
            style={{ marginTop: 16, width: "100%", background: loading ? "#334155" : "#2563eb", color: "white", border: "none", borderRadius: 8, padding: "14px 0", fontSize: 16, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "Processing…" : "Submit"}
          </button>
        </div>

        {result && (
          <div style={{ marginTop: 24, borderRadius: 12, padding: 24, background: result.status === "approved" ? "rgba(22,101,52,0.3)" : "rgba(127,29,29,0.3)", border: `1px solid ${result.status === "approved" ? "#166534" : "#991b1b"}` }}>
            <div style={{ fontSize: 20, fontWeight: "bold", marginBottom: 16, color: result.status === "approved" ? "#4ade80" : "#f87171" }}>
              {result.status === "approved" ? "✓ APPROVED" : "✗ BLOCKED"}
            </div>

            {result.reason && <div style={{ color: "#cbd5e1", marginBottom: 12 }}>Reason: {result.reason}</div>}

            {result.epoch_commitment && (
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                <div style={{ color: "#94a3b8" }}>Epoch commitment:</div>
                <div style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all", color: "#e2e8f0" }}>{result.epoch_commitment}</div>
              </div>
            )}

            {result.intent_hash && (
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                <div style={{ color: "#94a3b8" }}>Intent hash:</div>
                <div style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all", color: "#e2e8f0" }}>{result.intent_hash}</div>
              </div>
            )}

            {result.etherscan && (
              <a href={result.etherscan} target="_blank" rel="noreferrer" style={{ display: "inline-block", marginTop: 16, color: "#60a5fa" }}>
                View on Sepolia Etherscan →
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
