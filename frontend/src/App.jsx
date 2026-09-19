import { useState, useEffect } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

export default function App() {
  const [text, setText] = useState("Send 0.1 ETH to Alice");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState(null);
  const [zk, setZk] = useState(null);
  const [steps, setSteps] = useState([]);
  const [copied, setCopied] = useState(null);
  const [uptime, setUptime] = useState(0);

  async function loadState() {
    const [s, z] = await Promise.allSettled([
      axios.get(`${API}/api/state`, { timeout: 15000 }),
      axios.get(`${API}/api/zk-status`, { timeout: 15000 }),
    ]);
    setState(s.status === "fulfilled" ? s.value.data : null);
    setZk(z.status === "fulfilled" ? z.value.data : null);
  }

  useEffect(() => {
    const initialLoad = setTimeout(loadState, 0);
    const i = setInterval(loadState, 10000);
    const t = setInterval(() => setUptime((u) => u + 1), 1000);
    return () => {
      clearTimeout(initialLoad);
      clearInterval(i);
      clearInterval(t);
    };
  }, []);

  async function copyToClipboard(value, key) {
    await navigator.clipboard.writeText(value);
    setCopied(key);
    setTimeout(() => setCopied(null), 1500);
  }

  async function submit() {
    setLoading(true);
    setResult(null);
    setSteps([]);

    const stageLabels = [["intent", "Intent"], ["policy", "Policy"], ["proof", "Proof"], ["onchain", "On-chain record"]];
    const applyStages = (data) => setSteps(stageLabels.map(([key, label]) => ({
      label, status: data.stages?.[key] || "not_attempted",
    })));
    setSteps(stageLabels.map(([, label]) => ({ label, status: "pending" })));
    try {
      const res = await axios.post(`${API}/api/process`, { text });
      applyStages(res.data);
      setResult(res.data);
      loadState();
    } catch (e) {
      const data = e.response?.data || { status: "error", reason: "Request failed; processing outcome is unknown" };
      applyStages(data);
      setResult(data);
    }

    setLoading(false);
  }

  const fmtUptime = () => {
    const h = Math.floor(uptime / 3600);
    const m = Math.floor((uptime % 3600) / 60);
    const s = uptime % 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div style={S.root}>
      {/* Top status bar */}
      <div style={S.topbar}>
        <div style={S.topbarLeft}>
          <span style={S.logo}>◆</span>
          <span style={S.logoText}>DPK</span>
          <span style={S.logoSub}>Delegation Provenance Kernel</span>
        </div>
        <div style={S.topbarRight}>
          <span style={{ ...S.statusDot, background: state ? "#4ade80" : "#64748b", boxShadow: "none" }} />
          <span style={S.statusText}>SEPOLIA</span>
          <span style={S.topbarDivider}>|</span>
          <span style={S.statusText}>{fmtUptime()}</span>
        </div>
      </div>

      <div style={S.container}>
        {/* Metrics strip - Blockstream style */}
        <div style={S.metricsStrip}>
          <MetricCell
            label="Constraints"
            value={zk?.circuit_constraints != null ? zk.circuit_constraints.toLocaleString() : "—"}
            accent="#a78bfa"
          />
          <MetricCell
            label="Proof Size"
            value={zk?.proof_size_bytes != null ? `${zk.proof_size_bytes} B` : "—"}
            accent="#a78bfa"
          />
          <MetricCell
            label="Local ZK proof"
            value={zk?.verified_locally ? "VERIFIED" : "NOT INTEGRATED"}
            accent={zk?.verified_locally ? "#4ade80" : "#64748b"}
          />
          <MetricCell
            label="On-chain ZK proof"
            value={zk?.verified_onchain ? "VERIFIED" : "NOT INTEGRATED"}
            accent={zk?.verified_onchain ? "#4ade80" : "#64748b"}
          />
          <MetricCell
            label="Delegations"
            value={state ? state.delegationCount : "—"}
            accent="#60a5fa"
          />
          <MetricCell
            label="Approved"
            value={state ? state.approvedCount : "—"}
            accent="#4ade80"
          />
          <MetricCell
            label="Blocked"
            value={state ? state.blockedCount : "—"}
            accent="#f87171"
          />
        </div>

        {/* Main grid - two columns */}
        <div style={S.grid}>
          {/* Left: Proof Pipeline */}
          <div style={S.panel}>
            <div style={S.panelHeader}>
              <span style={S.panelTitle}>PROCESSING RESULTS</span>
              <span style={S.panelMeta}>reported by backend</span>
            </div>

            <div style={S.pipelineTiles}>
              {(steps.length > 0
                ? steps
                : [
                    { label: "Intent", status: "idle" },
                    { label: "Policy", status: "idle" },
                    { label: "Proof", status: "idle" },
                    { label: "On-chain record", status: "idle" },
                  ]
              ).map((s, i) => (
                <div
                  key={i}
                  style={{
                    ...S.tile,
                    background:
                      s.status === "done"
                        ? "rgba(74,222,128,0.15)"
                        : s.status === "blocked"
                        ? "rgba(248,113,113,0.15)"
                        : s.status === "running"
                        ? "rgba(96,165,250,0.15)"
                        : "rgba(71,85,105,0.1)",
                    borderColor:
                      s.status === "done"
                        ? "#4ade80"
                        : s.status === "blocked"
                        ? "#f87171"
                        : s.status === "running"
                        ? "#60a5fa"
                        : "#334155",
                  }}
                >
                  <div style={S.tileIndex}>0{i + 1}</div>
                  <div style={S.tileLabel}>{s.label}</div>
                  <div
                    style={{
                      ...S.tileStatus,
                      color:
                        s.status === "done"
                          ? "#4ade80"
                          : s.status === "blocked"
                          ? "#f87171"
                          : s.status === "running"
                          ? "#60a5fa"
                          : "#64748b",
                    }}
                  >
                    {s.status === "done" && "✓"}
                    {s.status === "blocked" && "✗"}
                    {s.status === "running" && "●"}
                    {s.status === "idle" && "—"}
                    {s.status === "pending" && "·"}
                    {s.status === "not_integrated" && "Not integrated"}
                    {s.status === "not_attempted" && "Not attempted"}
                    {s.status === "error" && "Error"}
                  </div>
                </div>
              ))}
            </div>

            <div style={S.panelDivider} />

            <div style={S.hashBlock}>
              <div style={S.hashRow}>
                <span style={S.hashLabel}>PROOF HASH</span>
                {zk?.proof_hash ? (
                  <button
                    style={S.copyBtn}
                    onClick={() => copyToClipboard(zk.proof_hash, "proof")}
                  >
                    {copied === "proof" ? "COPIED" : "COPY"}
                  </button>
                ) : null}
              </div>
              <code style={S.hashValue}>
                {zk?.proof_hash || "—"}
              </code>
            </div>

            <div style={S.hashBlock}>
              <div style={S.hashRow}>
                <span style={S.hashLabel}>VERIFIER CONTRACT</span>
                <a
                  href={zk?.verifier_contract ? `https://sepolia.etherscan.io/address/${zk.verifier_contract}` : undefined}
                  target="_blank"
                  rel="noreferrer"
                  style={S.externalLink}
                >
                  ETHERSCAN ↗
                </a>
              </div>
              <code style={S.hashValue}>{zk?.verifier_contract || "—"}</code>
            </div>
          </div>

          {/* Right: Network State */}
          <div style={S.panel}>
            <div style={S.panelHeader}>
              <span style={S.panelTitle}>NETWORK STATE</span>
              <span style={S.panelMeta}>Sepolia</span>
            </div>

            <div style={S.stateRow}>
              <span style={S.stateKey}>RSA Modulus</span>
              <span style={S.stateVal}>{state?.modulus?.slice(0, 24)}…</span>
            </div>

            <div style={S.stateRow}>
              <span style={S.stateKey}>Accumulator</span>
              <span style={S.stateVal}>{state?.accumulator?.slice(0, 24)}…</span>
            </div>

            <div style={S.stateRow}>
              <span style={S.stateKey}>Contract</span>
              <a
                href={state?.contract ? `https://sepolia.etherscan.io/address/${state.contract}` : undefined}
                target="_blank"
                rel="noreferrer"
                style={S.externalLink}
              >
                {state?.contract?.slice(0, 14)}… ↗
              </a>
            </div>

            <div style={S.panelDivider} />

            <div style={S.circuitBlock}>
              <div style={S.circuitLabel}>CIRCUIT</div>
              <div style={S.circuitTags}>
                <span style={S.tag}>CIRCOM 2.0</span>
                <span style={S.tag}>GROTH16</span>
                <span style={S.tag}>BN128</span>
              </div>
            </div>

            <div style={S.circuitBlock}>
              <div style={S.circuitLabel}>ACCUMULATOR</div>
              <div style={S.circuitTags}>
                <span style={S.tag}>RSA ACCUMULATOR</span>
                <span style={S.tag}>EXPERIMENTAL</span>
              </div>
            </div>
          </div>
        </div>

        {/* Command bar */}
        <div style={S.panel}>
          <div style={S.panelHeader}>
            <span style={S.panelTitle}>POLICY CHECK</span>
            <span style={S.panelMeta}>Send &lt;amount&gt; ETH to Alice or Bob</span>
          </div>

          <div style={S.commandRow}>
            <span style={S.prompt}>$</span>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !loading && submit()}
              style={S.input}
              disabled={loading}
            />
            <button
              onClick={submit}
              disabled={loading}
              style={loading ? S.btnDisabled : S.btn}
            >
              {loading ? "CHECKING" : "CHECK POLICY"}
            </button>
          </div>
        </div>

        {/* Result */}
        {result && (
          <div
            style={{
              ...S.result,
              borderColor:
                result.status === "approved" ? "#166534" : "#991b1b",
            }}
          >
            <div style={S.resultHeader}>
              <span
                style={{
                  ...S.resultStatus,
                  color: result.status === "approved" ? "#4ade80" : "#f87171",
                }}
              >
                {result.status === "approved" ? "✓ POLICY APPROVED" : result.status === "blocked" ? "✗ POLICY BLOCKED" : "REQUEST ERROR"}
              </span>
              {result.reason && <span style={S.resultReason}>{result.reason}</span>}
            </div>

            <p>No ETH transfer is executed. ZK verification is not integrated.</p>
            {result.recording_message && <p>{result.recording_message}</p>}

            {result.epoch_commitment && (
              <div style={S.resultRow}>
                <span style={S.resultKey}>EPOCH</span>
                <code style={S.resultVal}>{result.epoch_commitment}</code>
              </div>
            )}

            {result.intent_hash && (
              <div style={S.resultRow}>
                <span style={S.resultKey}>INTENT</span>
                <code style={S.resultVal}>{result.intent_hash}</code>
              </div>
            )}

            {result.etherscan && (
              <a
                href={result.etherscan}
                target="_blank"
                rel="noreferrer"
                style={S.resultLink}
              >
                VIEW TRANSACTION ON ETHERSCAN ↗
              </a>
            )}
          </div>
        )}

        {/* Footer */}
        <div style={S.footer}>
          <span>RSA ACCUMULATOR</span>
          <span style={S.footerSep}>·</span>
          <span>GROTH16 PROOFS</span>
          <span style={S.footerSep}>·</span>
          <span>EIP-7702</span>
          <span style={S.footerSep}>·</span>
          <span>SEPOLIA TESTNET</span>
        </div>
      </div>
    </div>
  );
}

function MetricCell({ label, value, accent }) {
  return (
    <div style={S.metricCell}>
      <div style={S.metricLabel}>{label}</div>
      <div style={{ ...S.metricValue, color: accent }}>{value}</div>
    </div>
  );
}

const S = {
  root: {
    minHeight: "100vh",
    background: "#0a0e1a",
    color: "#cbd5e1",
    fontFamily:
      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 13,
  },
  topbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 24px",
    borderBottom: "1px solid #1e2537",
    background: "#0d1220",
  },
  topbarLeft: { display: "flex", alignItems: "center", gap: 12 },
  logo: { color: "#a78bfa", fontSize: 18 },
  logoText: {
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 700,
    letterSpacing: 2,
    fontSize: 13,
    color: "#f1f5f9",
  },
  logoSub: {
    fontSize: 11,
    color: "#64748b",
    letterSpacing: 1,
    textTransform: "uppercase",
    paddingLeft: 12,
    borderLeft: "1px solid #1e2537",
  },
  topbarRight: { display: "flex", alignItems: "center", gap: 10 },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    background: "#4ade80",
    boxShadow: "0 0 8px #4ade80",
  },
  statusText: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    color: "#64748b",
    letterSpacing: 1,
  },
  topbarDivider: { color: "#1e2537" },
  container: { maxWidth: 1200, margin: "0 auto", padding: "24px" },
  metricsStrip: {
    display: "grid",
    gridTemplateColumns: "repeat(7, 1fr)",
    background: "#0d1220",
    border: "1px solid #1e2537",
    borderRadius: 6,
    overflow: "hidden",
    marginBottom: 20,
  },
  metricCell: {
    padding: "14px 16px",
    borderRight: "1px solid #1e2537",
  },
  metricLabel: {
    fontSize: 10,
    color: "#64748b",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: 6,
  },
  metricValue: {
    fontSize: 16,
    fontWeight: 600,
    fontVariantNumeric: "tabular-nums",
    fontFamily: "'JetBrains Mono', monospace",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1.2fr 1fr",
    gap: 20,
    marginBottom: 20,
  },
  panel: {
    background: "#0d1220",
    border: "1px solid #1e2537",
    borderRadius: 6,
    padding: 20,
    marginBottom: 20,
  },
  panelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
    paddingBottom: 12,
    borderBottom: "1px solid #1e2537",
  },
  panelTitle: {
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 2,
    color: "#94a3b8",
    fontFamily: "'JetBrains Mono', monospace",
  },
  panelMeta: {
    fontSize: 10,
    color: "#475569",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  pipelineTiles: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr 1fr",
    gap: 8,
    marginBottom: 16,
  },
  tile: {
    padding: "12px 10px",
    border: "1px solid",
    borderRadius: 4,
    textAlign: "center",
    transition: "all 0.3s",
  },
  tileIndex: {
    fontSize: 9,
    color: "#475569",
    fontFamily: "'JetBrains Mono', monospace",
    marginBottom: 4,
  },
  tileLabel: {
    fontSize: 11,
    color: "#cbd5e1",
    fontWeight: 500,
    marginBottom: 6,
  },
  tileStatus: {
    fontSize: 14,
    fontFamily: "'JetBrains Mono', monospace",
  },
  panelDivider: { height: 1, background: "#1e2537", margin: "16px 0" },
  hashBlock: { marginBottom: 14 },
  hashRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  hashLabel: {
    fontSize: 10,
    color: "#475569",
    letterSpacing: 1,
    textTransform: "uppercase",
    fontFamily: "'JetBrains Mono', monospace",
  },
  copyBtn: {
    padding: "2px 8px",
    background: "transparent",
    border: "1px solid #334155",
    color: "#94a3b8",
    borderRadius: 3,
    fontSize: 9,
    letterSpacing: 1,
    fontWeight: 600,
    cursor: "pointer",
    fontFamily: "'JetBrains Mono', monospace",
  },
  hashValue: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    color: "#94a3b8",
    wordBreak: "break-all",
    lineHeight: 1.5,
    display: "block",
  },
  externalLink: {
    fontSize: 10,
    color: "#a78bfa",
    textDecoration: "none",
    letterSpacing: 1,
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 600,
  },
  stateRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 0",
    borderBottom: "1px solid #131a2c",
  },
  stateKey: {
    fontSize: 11,
    color: "#475569",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  stateVal: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    color: "#94a3b8",
  },
  circuitBlock: { marginBottom: 12 },
  circuitLabel: {
    fontSize: 10,
    color: "#475569",
    letterSpacing: 1,
    marginBottom: 8,
    textTransform: "uppercase",
    fontFamily: "'JetBrains Mono', monospace",
  },
  circuitTags: { display: "flex", gap: 6, flexWrap: "wrap" },
  tag: {
    padding: "3px 8px",
    background: "rgba(167,139,250,0.08)",
    border: "1px solid rgba(167,139,250,0.2)",
    color: "#a78bfa",
    borderRadius: 3,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: 0.8,
    fontFamily: "'JetBrains Mono', monospace",
  },
  commandRow: {
    display: "flex",
    alignItems: "center",
    background: "#0a0e1a",
    border: "1px solid #1e2537",
    borderRadius: 4,
    padding: "4px 4px 4px 16px",
  },
  prompt: {
    color: "#a78bfa",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 14,
    marginRight: 10,
    fontWeight: 700,
  },
  input: {
    flex: 1,
    background: "transparent",
    border: "none",
    outline: "none",
    color: "#f1f5f9",
    fontSize: 14,
    fontFamily: "'JetBrains Mono', monospace",
    padding: "12px 0",
  },
  btn: {
    padding: "12px 24px",
    background: "#7c3aed",
    color: "white",
    border: "none",
    borderRadius: 3,
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 1.5,
    cursor: "pointer",
    fontFamily: "'JetBrains Mono', monospace",
  },
  btnDisabled: {
    padding: "12px 24px",
    background: "#1e2537",
    color: "#475569",
    border: "none",
    borderRadius: 3,
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 1.5,
    cursor: "not-allowed",
    fontFamily: "'JetBrains Mono', monospace",
  },
  result: {
    padding: 20,
    border: "1px solid",
    borderRadius: 6,
    background: "#0d1220",
    marginBottom: 20,
  },
  resultHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  resultStatus: {
    fontSize: 14,
    fontWeight: 700,
    letterSpacing: 1.5,
    fontFamily: "'JetBrains Mono', monospace",
  },
  resultReason: { fontSize: 12, color: "#94a3b8" },
  resultRow: {
    display: "flex",
    gap: 16,
    padding: "8px 0",
    borderBottom: "1px solid #131a2c",
  },
  resultKey: {
    fontSize: 10,
    color: "#475569",
    letterSpacing: 1,
    width: 80,
    flexShrink: 0,
    paddingTop: 2,
    fontFamily: "'JetBrains Mono', monospace",
  },
  resultVal: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    color: "#94a3b8",
    wordBreak: "break-all",
  },
  resultLink: {
    display: "inline-block",
    marginTop: 12,
    fontSize: 11,
    color: "#a78bfa",
    textDecoration: "none",
    letterSpacing: 1,
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
  },
  footer: {
    textAlign: "center",
    fontSize: 10,
    color: "#334155",
    letterSpacing: 2,
    fontFamily: "'JetBrains Mono', monospace",
    paddingTop: 20,
    borderTop: "1px solid #1e2537",
  },
  footerSep: { margin: "0 12px", color: "#1e2537" },
};
