"""Load Synthea-style CSV exports from ``fixtures/sample-patients`` for offline tools."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

_LOCK = Lock()
_STORE: CsvCohortStore | None = None


def fixture_csv_root() -> Path:
    raw = (os.environ.get("FIXTURE_PATIENT_CSV_DIR") or "").strip()
    if raw:
        return Path(raw)
    # agent/tools/csv_cohort.py -> parents[2] == repo root
    return Path(__file__).resolve().parents[2] / "fixtures" / "sample-patients"


@dataclass
class CsvCohortStore:
    """In-memory indexes keyed by patient UUID."""

    root: Path
    patients: dict[str, dict[str, str]] = field(default_factory=dict)
    medications: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    observations: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    allergies: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path) -> CsvCohortStore:
        self = cls(root=root)
        patients_path = root / "patients.csv"
        if not patients_path.is_file():
            raise FileNotFoundError(f"missing patients.csv under {root}")
        with patients_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pid = (row.get("Id") or "").strip()
                if pid:
                    self.patients[pid] = row
        self._index_by_patient(root / "medications.csv", "PATIENT", self.medications)
        self._index_by_patient(root / "observations.csv", "PATIENT", self.observations)
        self._index_by_patient(root / "allergies.csv", "PATIENT", self.allergies)
        return self

    def _index_by_patient(
        self,
        path: Path,
        col: str,
        bucket: dict[str, list[dict[str, str]]],
    ) -> None:
        if not path.is_file():
            return
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pid = (row.get(col) or "").strip()
                if not pid:
                    continue
                bucket.setdefault(pid, []).append(row)

    def demographics_payload(self, patient_id: str) -> dict[str, Any]:
        row = self.patients.get(patient_id)
        if not row:
            return {"error": "patient_not_found", "patient_id": patient_id}
        return {
            "patient_id": patient_id,
            "first": row.get("FIRST", ""),
            "last": row.get("LAST", ""),
            "birthdate": row.get("BIRTHDATE", ""),
            "gender": row.get("GENDER", ""),
            "race": row.get("RACE", ""),
            "ethnicity": row.get("ETHNICITY", ""),
            "city": row.get("CITY", ""),
            "state": row.get("STATE", ""),
        }

    def medications_payload(self, patient_id: str, *, limit: int = 50) -> dict[str, Any]:
        rows = self.medications.get(patient_id, [])
        slim = [
            {
                "description": r.get("DESCRIPTION", ""),
                "start": r.get("START", ""),
                "stop": r.get("STOP", ""),
                "code": r.get("CODE", ""),
            }
            for r in rows[:limit]
        ]
        return {"patient_id": patient_id, "count": len(rows), "medications": slim}

    def _obs_by_category(self, patient_id: str, category: str, *, limit: int) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for r in self.observations.get(patient_id, []):
            if (r.get("CATEGORY") or "").strip() != category:
                continue
            out.append(
                {
                    "date": r.get("DATE", ""),
                    "code": r.get("CODE", ""),
                    "description": r.get("DESCRIPTION", ""),
                    "value": r.get("VALUE", ""),
                    "units": r.get("UNITS", ""),
                }
            )
            if len(out) >= limit:
                break
        return out

    def labs_payload(self, patient_id: str, *, limit: int = 40) -> dict[str, Any]:
        rows = self._obs_by_category(patient_id, "laboratory", limit=limit)
        return {"patient_id": patient_id, "count": len(rows), "labs": rows}

    def vitals_payload(self, patient_id: str, *, limit: int = 40) -> dict[str, Any]:
        rows = self._obs_by_category(patient_id, "vital-signs", limit=limit)
        return {"patient_id": patient_id, "count": len(rows), "vitals": rows}

    def allergies_payload(self, patient_id: str, *, limit: int = 40) -> dict[str, Any]:
        rows = self.allergies.get(patient_id, [])[:limit]
        slim = [
            {
                "start": r.get("START", ""),
                "code": r.get("CODE", ""),
                "description": r.get("DESCRIPTION", ""),
                "type": r.get("TYPE", ""),
            }
            for r in rows
        ]
        return {"patient_id": patient_id, "count": len(rows), "allergies": slim}


def get_cohort_store() -> CsvCohortStore:
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = CsvCohortStore.load(fixture_csv_root())
        return _STORE


def reset_cohort_store_for_tests() -> None:
    """Test helper: clear singleton."""
    global _STORE
    with _LOCK:
        _STORE = None
