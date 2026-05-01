import { useCallback, useId, useMemo, useRef, useState } from "react";
import "./App.css";

type ChatRow = { role: string; content: string };

type ChatResponse = {
  assistant_message: string;
  verified: boolean;
  verification_notes: string[];
  verify_retry_count: number;
  tool_result_keys: string[];
  messages: ChatRow[];
};

const ROLES = ["PHYSICIAN", "NURSE", "ADMIN"] as const;

function chatEndpoint(): string {
  const raw = (import.meta.env.VITE_AGENT_BASE_URL || "").trim().replace(/\/$/, "");
  return raw ? `${raw}/agent/chat` : "/agent/chat";
}

function randomSession(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `sess-${Date.now()}`;
}

export default function App() {
  const idPrefix = useId();
  const [agentBaseDisplay] = useState(() => import.meta.env.VITE_AGENT_BASE_URL || "(same origin — dev proxy)");
  const [patientId, setPatientId] = useState("demo-patient");
  const [role, setRole] = useState<(typeof ROLES)[number]>("PHYSICIAN");
  const [authMode, setAuthMode] = useState<"demo" | "bearer">("demo");
  const [bearerToken, setBearerToken] = useState("");
  const [draft, setDraft] = useState("");
  const [rows, setRows] = useState<ChatRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMeta, setLastMeta] = useState<string | null>(null);
  const sessionRef = useRef(randomSession());

  const endpoint = useMemo(() => chatEndpoint(), []);

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || loading) return;
    setError(null);
    setLoading(true);
    setLastMeta(null);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Clinical-Session-Id": sessionRef.current,
    };
    if (authMode === "demo") {
      headers["X-Agent-Demo-Role"] = role;
    } else {
      const tok = bearerToken.trim();
      if (!tok) {
        setError("Bearer mode requires a non-empty Authorization value.");
        setLoading(false);
        return;
      }
      headers.Authorization = tok.startsWith("Bearer ") ? tok : `Bearer ${tok}`;
    }

    const prior = rows;
    const optimistic: ChatRow[] = [...prior, { role: "user", content: text }];
    setRows(optimistic);
    setDraft("");

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({
          patient_id: patientId.trim() || "demo-patient",
          user_message: text,
          messages: prior,
        }),
      });
      const rawText = await res.text();
      let data: ChatResponse | null = null;
      try {
        data = JSON.parse(rawText) as ChatResponse;
      } catch {
        /* not json */
      }
      if (!res.ok) {
        let detail = rawText.slice(0, 480);
        try {
          const errJson = JSON.parse(rawText) as { detail?: unknown };
          if (errJson?.detail !== undefined) {
            detail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
          }
        } catch {
          /* keep slice */
        }
        throw new Error(`${res.status} ${res.statusText} — ${detail}`);
      }
      if (!data || !Array.isArray(data.messages)) {
        throw new Error("Unexpected response shape from agent.");
      }
      setRows(data.messages);
      setLastMeta(
        `verified=${String(data.verified)} retries=${String(data.verify_retry_count)} tools=[${data.tool_result_keys.join(", ")}]`,
      );
    } catch (e) {
      setRows(prior);
      setDraft(text);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [authMode, bearerToken, draft, endpoint, loading, patientId, role, rows]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Clinical Co-Pilot</h1>
        <p>
          Minimal chat against <code style={{ color: "var(--accent)" }}>/agent/chat</code> —{" "}
          <span style={{ color: "var(--muted)" }}>API: {agentBaseDisplay}</span>
        </p>
      </header>

      {error ? (
        <div className="alert" role="alert">
          <strong>Error</strong> — {error}
        </div>
      ) : null}

      <section className="panel">
        <h2 className="panel-title">Connection</h2>
        <div className="grid grid-2">
          <label className="field">
            Patient ID
            <input value={patientId} onChange={(e) => setPatientId(e.target.value)} autoComplete="off" />
          </label>
          <label className="field">
            <span className="key">Role</span>
            <select value={role} onChange={(e) => setRole(e.target.value as (typeof ROLES)[number])}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div style={{ marginTop: "1rem" }}>
          <p className="panel-title" style={{ marginBottom: "0.5rem" }}>
            Auth
          </p>
          <div className="chip-group">
            <label className="chip">
              <input
                type="radio"
                name={`${idPrefix}-auth`}
                checked={authMode === "demo"}
                onChange={() => setAuthMode("demo")}
              />
              Demo bypass
            </label>
            <label className="chip">
              <input
                type="radio"
                name={`${idPrefix}-auth`}
                checked={authMode === "bearer"}
                onChange={() => setAuthMode("bearer")}
              />
              Bearer token
            </label>
          </div>
          {authMode === "bearer" ? (
            <label className="field" style={{ marginTop: "0.85rem" }}>
              Authorization (paste raw token or full <span className="key">Bearer …</span>)
              <textarea value={bearerToken} onChange={(e) => setBearerToken(e.target.value)} rows={3} />
            </label>
          ) : (
            <p className="meta" style={{ marginTop: "0.65rem", marginBottom: 0 }}>
              Sends <span className="key">X-Agent-Demo-Role</span>. Requires{" "}
              <span className="key">AGENT_DEMO_BYPASS=1</span> on the agent.
            </p>
          )}
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title">Conversation</h2>
        <div className="messages">
          {rows.length === 0 ? (
            <div className="empty-hint">Send a message to start. Session id is fixed until you refresh.</div>
          ) : (
            rows.map((m, i) => (
              <div key={`${i}-${m.role}`} className={`msg ${m.role === "user" ? "user" : "assistant"}`}>
                <div className="role">{m.role}</div>
                <div className="body">{m.content}</div>
              </div>
            ))
          )}
        </div>
        {lastMeta ? <div className="meta">{lastMeta}</div> : null}
        <div className="grid" style={{ marginTop: "1rem" }}>
          <label className="field">
            Message
            <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={3} disabled={loading} />
          </label>
        </div>
        <div className="row" style={{ marginTop: "0.85rem" }}>
          <button type="button" className="btn" disabled={loading || !draft.trim()} onClick={() => void send()}>
            {loading ? "Sending…" : "Send"}
          </button>
        </div>
      </section>
    </div>
  );
}
