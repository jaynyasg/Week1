## Conflict Detection Report

### BLOCKERS (0)

No unresolved blockers detected.
Source set:
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/PRD-AgentForge-Clinical-CoPilot-Requirements.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/deploy-docs-deployment.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/ARCHITECTURE.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/USERS.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/AUDIT.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/AUDIT_V2.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/deploy-INSTALL.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/deploy-README_section.classification.json`
- `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/README.classification.json`

### WARNINGS (0)

No competing requirement variants detected (single PRD source in this ingest set).

### INFO (2)

[INFO] Auto-resolved: ADR > SPEC on deployment platform target
  Found: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/ARCHITECTURE.md` describes runtime target as "Railway / Fly.io"
  Winner: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/deploy/docs/deployment.md` declares Fly.io as the chosen platform decision
  Source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/ARCHITECTURE.classification.json`, `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/deploy-docs-deployment.classification.json`
  Rationale: precedence ADR > SPEC

[INFO] Auto-resolved: ADR > DOC on deployment guidance
  Found: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/README.md` contains generic CI/CD deployment options
  Winner: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/deploy/docs/deployment.md` provides explicit Fly.io deployment decision and runbook
  Source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/README.classification.json`, `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/.planning/ingest/classifications/deploy-docs-deployment.classification.json`
  Rationale: precedence ADR > DOC
