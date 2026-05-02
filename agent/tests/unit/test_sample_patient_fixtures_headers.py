"""Lightweight checks on fixtures/sample-patients CSV headers (no full FK scan)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "sample-patients"


def _header_row(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader)


@pytest.mark.parametrize(
    ("filename", "required"),
    [
        ("patients.csv", ["Id", "FIRST", "LAST", "BIRTHDATE"]),
        ("encounters.csv", ["Id", "PATIENT", "ENCOUNTERCLASS"]),
        ("observations.csv", ["PATIENT", "ENCOUNTER", "CATEGORY", "CODE"]),
        ("medications.csv", ["PATIENT", "ENCOUNTER", "CODE"]),
        ("conditions.csv", ["PATIENT", "ENCOUNTER", "CODE"]),
    ],
)
def test_sample_patient_csv_has_expected_columns(filename: str, required: list[str]) -> None:
    path = _FIXTURES / filename
    assert path.is_file(), f"missing {path}"
    headers = _header_row(path)
    missing = [c for c in required if c not in headers]
    assert not missing, f"{filename} missing columns {missing}; got {headers}"


def test_patients_csv_has_at_least_one_data_row() -> None:
    path = _FIXTURES / "patients.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = sum(1 for _ in reader)
    assert rows >= 1
