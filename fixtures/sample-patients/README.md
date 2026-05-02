# Sample patient fixtures (CSV)

**Purpose:** Offline **synthetic cohort** data for future evals, golden retrieves, and OpenEMR import experiments—**not** wired into the FastAPI agent at runtime.

## Provenance and PHI

These files follow the **Synthea**-style CSV export shape (column names such as `PATIENT`, `ENCOUNTER`, SNOMED/LOINC codes, synthetic `999-xx-xxxx` SSN patterns). Treat them as **synthetic research data**, not a guarantee of de-identification for every cell. **Do not** add real patient exports here without legal approval; use `local/` (gitignored) for sensitive experiments.

## Layout

| File | Role |
| --- | --- |
| `patients.csv` | Root person records (`Id` = patient UUID used elsewhere) |
| `organizations.csv`, `providers.csv`, `payers.csv` | Reference entities |
| `encounters.csv` | Visits / encounters; links `PATIENT` → `patients.Id` |
| `observations.csv` | Labs, vitals, social history rows (`CATEGORY` matches FHIR Observation bands) |
| `medications.csv`, `conditions.csv`, `allergies.csv`, … | Clinical facts keyed by `PATIENT` (+ `ENCOUNTER` where present) |
| `claims.csv`, `claims_transactions.csv` | Billing-shaped rows; use `PATIENTID` → patient |

## Nondisruptive use (today)

1. **Fixtures only** — tests and scripts **read** these files; nothing in `agent/` auto-loads them on `uvicorn` startup.
2. **Validate referential shape** (recommended before demos):

   ```bash
   python scripts/validate_sample_patient_fixtures.py
   # or: make validate-fixtures
   ```

3. **Optional quick check** (patients file + directory sanity only):

   ```bash
   python scripts/validate_sample_patient_fixtures.py --quick
   ```

## Promoting to OpenEMR (later / disruptive phase)

The agent does **not** import CSV into MariaDB. When you are ready:

1. Use **OpenEMR-supported** import paths (native modules, FHIR bulk import, or a controlled ETL you own)—match your fork’s schema.
2. Keep **the same CSV column shapes** here so **eval expectations** and **EMR content** stay aligned.
3. After import, re-run **integration / live** tests against that stack (`RUN_LIVE_OPENEMR_E2E`, etc.).

## Local overrides (gitignored)

Drop machine-specific or sensitive CSV copies under `fixtures/sample-patients/local/` — see root `.gitignore`.
