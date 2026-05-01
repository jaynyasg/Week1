/**
 * UI copy (English). Swap this module later for a real i18n loader if needed.
 */
export const strings = {
  title: "Clinical Co-Pilot",
  subtitleApi: "API",
  chatEndpointHint: "Minimal chat against",
  connection: "Connection",
  patientId: "Patient ID",
  role: "Role",
  roleFromSession: "Role",
  roleFromSessionHelp:
    "Taken from your OpenEMR session (cookie) when the agent calls /api/user.",
  auth: "Auth",
  authOpenEmr: "OpenEMR session",
  authDemo: "Demo bypass",
  authBearer: "Bearer token",
  authDemoHelp: "Sends X-Agent-Demo-Role. Requires AGENT_DEMO_BYPASS=1 on the agent.",
  authBearerLabel: "Authorization (paste raw token or full Bearer …)",
  authOpenEmrHelp:
    "Sends cookies with credentials: include. Log into OpenEMR on this same site first. The agent must have OPENEMR_BASE_URL set to this OpenEMR origin.",
  conversation: "Conversation",
  emptyHint: "Send a message to start. Session id is fixed until you refresh.",
  messageLabel: "Message",
  send: "Send",
  sending: "Sending…",
  errorPrefix: "Error",
  offlineBanner: "You appear to be offline — messages cannot reach the agent until connectivity returns.",
  onlineBanner: "Back online.",
  loadingConversation: "Loading response…",
  agentBaseEmbedded: "same origin → Apache /agent → Fly agent (6PN)",
  agentBaseDevProxy: "(same origin — Vite dev proxy)",
} as const;
