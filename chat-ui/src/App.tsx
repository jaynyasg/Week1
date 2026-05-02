import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import "./App.css";
import { strings } from "./strings/en";
import { CLINICIAN_WORKFLOWS, DEMO_SEED_PATIENT_ID } from "./workflows";

type ChatRow = { role: string; content: string };

type ChatResponse = {
  assistant_message: string;
  verified: boolean;
  verification_notes: string[];
  verify_retry_count: number;
  tool_result_keys: string[];
  tool_execution_summary?: Array<Record<string, unknown>> | null;
  messages: ChatRow[];
};

const ROLES = ["PHYSICIAN", "NURSE", "ADMIN"] as const;

type AuthMode = "openemr" | "demo" | "bearer";

const isEmbedded =
  import.meta.env.VITE_EMBEDDED === "true" || import.meta.env.VITE_EMBEDDED === "1";

function chatEndpoint(): string {
  const raw = (import.meta.env.VITE_AGENT_BASE_URL || "").trim().replace(/\/$/, "");
  return raw ? `${raw}/agent/chat` : "/agent/chat";
}

function randomSession(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `sess-${Date.now()}`;
}

function LoadingSkeleton() {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      <div className="skeleton-line w-80" />
      <div className="skeleton-line w-60" />
      <div className="skeleton-line w-70" />
    </div>
  );
}

export default function App() {
  const idPrefix = useId();
  const titleId = `${idPrefix}-title`;
  const agentBaseDisplay = useMemo(() => {
    if (isEmbedded) return strings.agentBaseEmbedded;
    return import.meta.env.VITE_AGENT_BASE_URL || strings.agentBaseDevProxy;
  }, []);
  const [patientId, setPatientId] = useState("demo-patient");
  const [role, setRole] = useState<(typeof ROLES)[number]>("PHYSICIAN");
  const [authMode, setAuthMode] = useState<AuthMode>(() => (isEmbedded ? "openemr" : "demo"));
  const [bearerToken, setBearerToken] = useState("");
  const [sessionCookie, setSessionCookie] = useState("");
  const [draft, setDraft] = useState("");
  const [rows, setRows] = useState<ChatRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMeta, setLastMeta] = useState<string | null>(null);
  const [toolSummary, setToolSummary] = useState<string | null>(null);
  const [online, setOnline] = useState(() =>
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const [liveStatus, setLiveStatus] = useState<string>("");
  const sessionRef = useRef(randomSession());

  const endpoint = useMemo(() => chatEndpoint(), []);

  useEffect(() => {
    const on = () => {
      setOnline(true);
      setLiveStatus(strings.onlineBanner);
    };
    const off = () => {
      setOnline(false);
      setLiveStatus(strings.offlineBanner);
    };
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || loading) return;
    if (!online) {
      setError(strings.offlineBanner);
      return;
    }
    setError(null);
    setLoading(true);
    setLastMeta(null);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Clinical-Session-Id": sessionRef.current,
    };
    if (authMode === "demo") {
      headers["X-Agent-Demo-Role"] = role;
    } else if (authMode === "bearer") {
      const tok = bearerToken.trim();
      if (!tok) {
        setError("Bearer mode requires a non-empty Authorization value.");
        setLoading(false);
        return;
      }
      headers.Authorization = tok.startsWith("Bearer ") ? tok : `Bearer ${tok}`;
    } else if (authMode === "openemr" && !isEmbedded) {
      const ck = sessionCookie.trim();
      if (!ck) {
        setError("OpenEMR session mode requires a Cookie header value. Paste it from browser DevTools.");
        setLoading(false);
        return;
      }
      headers.Cookie = ck;
    }

    const prior = rows;
    const optimistic: ChatRow[] = [...prior, { role: "user", content: text }];
    setRows(optimistic);
    setDraft("");

    try {
      const init: RequestInit = {
        method: "POST",
        headers,
        body: JSON.stringify({
          patient_id: patientId.trim() || "demo-patient",
          user_message: text,
          messages: prior,
        }),
      };
      if (authMode === "bearer") {
        init.credentials = "include";
      }
      const res = await fetch(endpoint, init);
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
      if (data.tool_execution_summary && data.tool_execution_summary.length > 0) {
        setToolSummary(JSON.stringify(data.tool_execution_summary, null, 2));
      } else {
        setToolSummary(null);
      }
    } catch (e) {
      setRows(prior);
      setDraft(text);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [authMode, bearerToken, draft, endpoint, loading, online, patientId, role, rows]);

  const applyWorkflow = useCallback(
    (preset: (typeof CLINICIAN_WORKFLOWS)[number]) => {
      setPatientId(DEMO_SEED_PATIENT_ID);
      setRole(preset.role);
      setAuthMode(isEmbedded ? "openemr" : "demo");
      setDraft(preset.prompt);
      setError(null);
    },
    [isEmbedded],
  );

  const onKeyDownMessage = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void send();
      }
    },
    [send],
  );

  return (
    <div className="app" role="application" aria-labelledby={titleId}>
      <div className="visually-hidden" aria-live="polite">
        {liveStatus}
      </div>
      {!online ? (
        <div className="offline-banner" role="status">
          {strings.offlineBanner}
        </div>
      ) : null}

      <header className="app-header">
        <h1 id={titleId}>{strings.title}</h1>
        <p>
          {strings.chatEndpointHint}{" "}
          <code style={{ color: "var(--accent)" }}>/agent/chat</code> —{" "}
          <span style={{ color: "var(--muted)" }}>
            {strings.subtitleApi}: {agentBaseDisplay}
          </span>
        </p>
      </header>

      {error ? (
        <div className="alert" role="alert" aria-live="assertive">
          <strong>{strings.errorPrefix}</strong> — {error}
        </div>
      ) : null}

      <section className="panel" aria-label={strings.connection}>
        <h2 className="panel-title">{strings.connection}</h2>
        <div className="grid grid-2">
          <label className="field">
            {strings.patientId}
            <input
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              autoComplete="off"
              aria-label={strings.patientId}
            />
          </label>
          {authMode === "openemr" ? (
            <div className="field" style={{ justifyContent: "flex-end", margin: 0 }}>
              <span className="key">{strings.roleFromSession}</span>
              <span style={{ color: "var(--muted)", fontSize: "0.9rem", lineHeight: 1.4 }}>
                {strings.roleFromSessionHelp}
              </span>
            </div>
          ) : (
            <label className="field">
              <span className="key">{strings.role}</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as (typeof ROLES)[number])}
                aria-label={strings.role}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div style={{ marginTop: "1rem" }}>
          <p className="panel-title" style={{ marginBottom: "0.5rem" }}>
            {strings.auth}
          </p>
          <div className="chip-group" role="radiogroup" aria-label={strings.auth}>
            <label className="chip">
              <input
                type="radio"
                name={`${idPrefix}-auth`}
                checked={authMode === "openemr"}
                onChange={() => setAuthMode("openemr")}
              />
              {strings.authOpenEmr}
            </label>
            <label className="chip">
              <input
                type="radio"
                name={`${idPrefix}-auth`}
                checked={authMode === "demo"}
                onChange={() => setAuthMode("demo")}
              />
              {strings.authDemo}
            </label>
            <label className="chip">
              <input
                type="radio"
                name={`${idPrefix}-auth`}
                checked={authMode === "bearer"}
                onChange={() => setAuthMode("bearer")}
              />
              {strings.authBearer}
            </label>
          </div>
          {authMode === "bearer" ? (
            <label className="field" style={{ marginTop: "0.85rem" }}>
              {strings.authBearerLabel}
              <textarea
                value={bearerToken}
                onChange={(e) => setBearerToken(e.target.value)}
                rows={3}
                aria-label={strings.authBearerLabel}
              />
            </label>
          ) : authMode === "openemr" && !isEmbedded ? (
            <label className="field" style={{ marginTop: "0.85rem" }}>
              {strings.authOpenEmrCookieLabel}
              <textarea
                value={sessionCookie}
                onChange={(e) => setSessionCookie(e.target.value)}
                rows={3}
                placeholder="OpenEMR=…; PHPSESSID=…; token_main=…"
                aria-label={strings.authOpenEmrCookieLabel}
              />
              <span className="meta" style={{ marginTop: "0.4rem" }}>
                {strings.authOpenEmrHelp}
              </span>
            </label>
          ) : authMode === "openemr" && isEmbedded ? (
            <p className="meta" style={{ marginTop: "0.65rem", marginBottom: 0 }}>
              Session cookies are forwarded automatically — no extra setup needed.
            </p>
          ) : (
            <p className="meta" style={{ marginTop: "0.65rem", marginBottom: 0 }}>
              {strings.authDemoHelp}
            </p>
          )}
        </div>
      </section>

      <section className="panel" aria-label={strings.workflows}>
        <h2 className="panel-title">{strings.workflows}</h2>
        <p className="meta" style={{ marginTop: 0, marginBottom: "0.85rem" }}>
          {strings.workflowsHelp}
        </p>
        <div className="workflow-grid" role="list">
          {CLINICIAN_WORKFLOWS.map((w) => (
            <button
              key={w.id}
              type="button"
              className="btn btn-workflow"
              onClick={() => applyWorkflow(w)}
              aria-label={`${strings.workflowApply}: ${w.title}`}
            >
              <span className="workflow-title">{w.title}</span>
              <span className="workflow-role">{w.role}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel" aria-label={strings.conversation}>
        <h2 className="panel-title">{strings.conversation}</h2>
        <div
          className="messages"
          role="log"
          aria-label={strings.conversation}
          aria-busy={loading}
        >
          {rows.length === 0 && !loading ? (
            <div className="empty-hint">{strings.emptyHint}</div>
          ) : (
            <>
              {rows.map((m, i) => (
                <div
                  key={`${i}-${m.role}`}
                  className={`msg ${m.role === "user" ? "user" : "assistant"}`}
                  role="article"
                  aria-label={`${m.role} message`}
                >
                  <div className="role">{m.role}</div>
                  <div className="body">{m.content}</div>
                </div>
              ))}
              {loading ? (
                <div className="loading-inline" aria-label={strings.loadingConversation}>
                  <LoadingSkeleton />
                </div>
              ) : null}
            </>
          )}
        </div>
        {lastMeta ? <div className="meta">{lastMeta}</div> : null}
        {toolSummary ? (
          <details className="tool-trace">
            <summary>{strings.toolSummary}</summary>
            <pre className="tool-trace-pre">{toolSummary}</pre>
          </details>
        ) : null}
        <div className="grid" style={{ marginTop: "1rem" }}>
          <label className="field">
            {strings.messageLabel}
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDownMessage}
              rows={3}
              disabled={loading}
              aria-label={strings.messageLabel}
            />
          </label>
        </div>
        <div className="row" style={{ marginTop: "0.85rem" }}>
          <button
            type="button"
            className="btn"
            disabled={loading || !draft.trim() || !online}
            onClick={() => void send()}
            aria-busy={loading}
            aria-label={loading ? strings.sending : strings.send}
          >
            {loading ? strings.sending : strings.send}
          </button>
        </div>
      </section>
    </div>
  );
}
