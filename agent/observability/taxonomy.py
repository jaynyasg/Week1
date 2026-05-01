"""
Stable ``event_type`` values for structured logs (Phase 4 / NFR-observability).

Minimum operator questions (what, why, duration, fallback, cost envelope) should be
satisfied per event via ``log_agent_event`` fields — see each constant's docstring.
"""

from __future__ import annotations

# RBAC / tool gate
TOOL_REFUSAL = "tool_refusal"

# Successful chat turn (happy path summary)
CHAT_TURN_COMPLETE = "chat_turn_complete"

# RGV pipeline
VERIFY_FAILURE = "verify_failure"
RGV_VERIFY_RETRY = "rgv_verify_retry"
RGV_DEGRADED_UNVERIFIED = "rgv_degraded_unverified"

# Configuration / upstream
OPENEMR_MISCONFIGURATION = "openemr_misconfiguration"

# Demo / non-production auth bypass — only emitted when AGENT_DEMO_BYPASS=1 AND a
# valid X-Agent-Demo-Role header short-circuits OpenEMR /api/user validation.
# Operators MUST treat occurrences in production as a misconfiguration (PHI risk).
DEMO_BYPASS_ACTIVE = "auth_demo_bypass"

# Clinical safety review signal (labs vs vitals boundary, etc.)
CATEGORY_BOUNDARY_REVIEW = "category_boundary_review"
