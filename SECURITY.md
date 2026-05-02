# Security policy

## Supported versions

Security fixes are applied to the **default branch** of this repository (`main` or the active development branch). Tags/releases may trail the branch briefly; use the latest commit for patch verification.

## Reporting a vulnerability

**Please do not** open a public GitHub/GitLab issue for undisclosed security vulnerabilities.

1. Contact the maintainers using the process described in [`MAINTAINERS.md`](MAINTAINERS.md) (or your organization’s private security channel if this repo is forked under org policy).
2. Include: affected component (agent HTTP API, OpenEMR deploy, chat UI, CI), reproduction steps, and impact assessment if known.

We aim to acknowledge reports within a few business days; resolution time depends on severity and release process.

## Scope notes

- **Secrets:** Never commit `.env` files or live tokens. Use `fly secrets` / environment variables per [`deploy/README-fly-agent.md`](deploy/README-fly-agent.md).
- **Synthetic data:** Patient CSV fixtures under [`fixtures/sample-patients/`](fixtures/sample-patients/README.md) are intended as **synthetic** research data; do not replace them with real PHI without governance approval.

## Updates

Revise this file when the project adopts a formal disclosure program (e.g. platform security advisories) or a dedicated security contact email.
