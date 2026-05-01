# Decisions Intel

## ADR-DEPLOYMENT-CLINICAL-COPILOT-ON-FLY-IO

- title: Deployment - Clinical Co-Pilot on Fly.io
- source: `C:/Users/jayny/OneDrive/Documents/GitLab/Week1/deploy/docs/deployment.md`
- status: proposed
- scope: deployment platform and topology
- decision_statement: Use Fly.io for MVP deployment, with OpenEMR and MariaDB as separate apps connected over private `.internal` networking.
- supporting_decisions:
  - Keep MariaDB private-only (no public service exposure).
  - Store operational secrets in Fly secret storage, not repository files.
  - Require seven deployment smoke tests to pass post-deploy.
  - Keep environment demo-only; no real PHI due to no HIPAA BAA.
