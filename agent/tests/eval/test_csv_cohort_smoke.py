"""Smoke tests on CSV fixture loading (no OpenAI)."""

from __future__ import annotations

import pytest

from agent.tools.csv_cohort import fixture_csv_root, reset_cohort_store_for_tests
from agent.tools.csv_cohort import CsvCohortStore


@pytest.fixture(autouse=True)
def _reset_store():
    reset_cohort_store_for_tests()
    yield
    reset_cohort_store_for_tests()


def test_fixture_root_contains_patients_csv() -> None:
    root = fixture_csv_root()
    assert (root / "patients.csv").is_file()


def test_cohort_loads_known_patient_row() -> None:
    root = fixture_csv_root()
    store = CsvCohortStore.load(root)
    pid = "f1aa52b9-aded-3188-9386-012244805ebf"
    assert pid in store.patients
    demo = store.demographics_payload(pid)
    assert demo.get("last") == "Brekke496"


def test_medications_non_empty_for_seed_patient() -> None:
    store = CsvCohortStore.load(fixture_csv_root())
    pid = "f1aa52b9-aded-3188-9386-012244805ebf"
    meds = store.medications_payload(pid)
    assert meds.get("count", 0) >= 1
