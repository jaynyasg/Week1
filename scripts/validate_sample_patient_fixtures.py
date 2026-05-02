#!/usr/bin/env python3
"""
Validate Synthea-style CSV fixtures under fixtures/sample-patients/.

Default: load patient + encounter IDs, then scan all configured tables for
broken PATIENT / PATIENTID / ENCOUNTER foreign keys.

Does not connect to any database. Exit 1 if errors exceed --max-errors.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

# (filename, [(fk_column, "patient" | "encounter"), ...])
FK_CONFIG: list[tuple[str, list[tuple[str, str]]]] = [
    ("encounters.csv", [("PATIENT", "patient")]),
    ("medications.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("observations.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("conditions.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("allergies.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("immunizations.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("procedures.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("devices.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("careplans.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("imaging_studies.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("supplies.csv", [("PATIENT", "patient"), ("ENCOUNTER", "encounter")]),
    ("payer_transitions.csv", [("PATIENT", "patient")]),
    ("claims.csv", [("PATIENTID", "patient")]),
    ("claims_transactions.csv", [("PATIENTID", "patient")]),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_ids(path: Path, column: str) -> set[str]:
    out: set[str] = set()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if column not in (reader.fieldnames or []):
            raise SystemExit(f"{path.name}: missing column {column!r}")
        for row in reader:
            v = (row.get(column) or "").strip()
            if v:
                out.add(v)
    return out


def _scan_fks(
    path: Path,
    checks: list[tuple[str, str]],
    *,
    patients: set[str],
    encounters: set[str],
    max_errors: int,
    errors: list[str],
) -> int:
    """Return number of rows read."""
    rows = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for col, _ in checks:
            if col not in fieldnames:
                errors.append(f"{path.name}: missing FK column {col!r}")
                return rows
        for row in reader:
            rows += 1
            for col, ref in checks:
                v = (row.get(col) or "").strip()
                if not v:
                    continue
                if ref == "patient" and v not in patients:
                    errors.append(f"{path.name}: row {rows}: {col}={v!r} not in patients.csv")
                elif ref == "encounter" and v not in encounters:
                    errors.append(f"{path.name}: row {rows}: {col}={v!r} not in encounters.csv")
                if len(errors) >= max_errors:
                    return rows
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=_repo_root() / "fixtures" / "sample-patients",
        help="Directory containing CSV exports",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Only check patients.csv exists and has rows (skip FK scans)",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=200,
        help="Stop collecting errors after this many (still exits non-zero)",
    )
    args = parser.parse_args()
    root: Path = args.root
    errors: list[str] = []

    if not root.is_dir():
        print(f"ERROR: fixture root not found: {root}", file=sys.stderr)
        return 1

    patients_path = root / "patients.csv"
    if not patients_path.is_file():
        print(f"ERROR: missing {patients_path}", file=sys.stderr)
        return 1

    patient_ids = _load_ids(patients_path, "Id")
    print(f"patients.csv: {len(patient_ids)} patient Id values")

    if args.quick:
        print("--quick: skipping FK scans")
        return 0

    enc_path = root / "encounters.csv"
    if not enc_path.is_file():
        errors.append(f"missing {enc_path.name} (needed for ENCOUNTER FK checks)")
    else:
        encounter_ids = _load_ids(enc_path, "Id")
        print(f"encounters.csv: {len(encounter_ids)} encounter Id values")
        counts: Counter[str] = Counter()
        for fname, checks in FK_CONFIG:
            path = root / fname
            if not path.is_file():
                errors.append(f"missing expected file {fname}")
                continue
            n = _scan_fks(
                path,
                checks,
                patients=patient_ids,
                encounters=encounter_ids,
                max_errors=args.max_errors,
                errors=errors,
            )
            counts[fname] = n
        for k, v in sorted(counts.items()):
            print(f"  scanned {k}: {v} rows")

    if errors:
        print(f"\n{len(errors)} issue(s):", file=sys.stderr)
        for e in errors[:50]:
            print(f"  - {e}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more", file=sys.stderr)
        return 1

    print("OK: no orphan PATIENT / PATIENTID / ENCOUNTER references detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
