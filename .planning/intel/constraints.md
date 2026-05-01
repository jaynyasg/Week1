# Constraints Intel

## CONSTRAINT-AGENT-MICROSERVICE-BOUNDARY
- title: Agent runs as separate FastAPI service
- source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/ARCHITECTURE.md`
- type: protocol
- content: Deploy the AI agent as an independent FastAPI microservice in the same network as OpenEMR, not embedded in PHP runtime.

## CONSTRAINT-AUTH-VALIDATION
- title: Validate OpenEMR session token via `/api/user`
- source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/ARCHITECTURE.md`
- type: api-contract
- content: Agent auth must validate incoming OpenEMR token against OpenEMR user endpoint instead of introducing a separate auth system.

## CONSTRAINT-RAG-WORKFLOW
- title: Bounded retrieve-generate-verify loop
- source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/ARCHITECTURE.md`
- type: nfr
- content: LangGraph flow must perform retrieve -> generate -> verify with bounded retry and graceful degradation when agent is unavailable.

## CONSTRAINT-RBAC-ENFORCEMENT-LAYER
- title: Enforce RBAC in agent retrieve layer
- source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/USERS.md`
- type: protocol
- content: Role boundaries are enforced in agent tool dispatch (`rbac.py`), not by UI gating alone.

## CONSTRAINT-RBAC-TOOL-MATRIX
- title: Eight-tool role matrix is normative
- source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/USERS.md`
- type: api-contract
- content: PHYSICIAN has eight tools; NURSE has demographics, medications, vitals, allergies, schedule; ADMIN has demographics and schedule only.

## CONSTRAINT-REFUSAL-BEHAVIOR
- title: Explicit deny response and logging
- source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/USERS.md`
- type: nfr
- content: Denied tool usage must return explicit role + tool refusal and policy-safe denial logs, without side-channel data leakage.
