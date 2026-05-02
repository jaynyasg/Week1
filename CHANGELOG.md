# Changelog

All notable changes to this repository are documented here. The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Synthetic **Synthea-style** patient CSV fixtures under `fixtures/sample-patients/` with README and optional FK validation (`scripts/validate_sample_patient_fixtures.py`, PowerShell wrapper, `make validate-fixtures`).
- **GitHub Actions** manual workflow [`.github/workflows/validate-sample-fixtures.yml`](.github/workflows/validate-sample-fixtures.yml) for full fixture scans on demand.
- **GitLab CI** manual job `validate-sample-fixtures` (stdlib-only script, no extra pip install).
- **pytest** header checks for key fixture CSVs (`agent/tests/unit/test_sample_patient_fixtures_headers.py`).
- **`SECURITY.md`** for responsible vulnerability reporting.
- **`.editorconfig`** for consistent encoding and indentation across common file types.
- **`PROJECT-SHOWCASE.md`** living narrative (architecture, users, eval, cost, observability, interview Q&A, tool stack).
- **Pre-commit** local hook to run quick fixture validation (alongside Ruff).
- **Unit tests** for fixture headers and quick validation subprocess.

### Documentation

- Expanded **`USERS.md`** Part 1 (Stage 4 user, workflow, use cases, “why conversational agent”).
- **`USER.md`** as a short alias to `USERS.md` Part 1.
- **`AI-COST-ANALYSIS.md`**, **`.planning/observability-gap-analysis.md`**, eval snapshot under `.planning/eval-artifacts/`.
- **`CONTRIBUTING`** notes on synthetic data and Makefile targets.

### Changed

- README troubleshooting, submission links, pytest count snapshots (re-run `pytest` to refresh numbers).
