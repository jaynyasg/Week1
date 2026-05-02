"""
Unit tests for the OpenEMR FHIR → CSV fallback path in dispatch.py.

These tests verify:
- When FHIR credentials are absent, dispatch falls through to CSV cohort.
- When FHIR credentials are present, dispatch calls the FHIR helpers.
- The "source" key is always present in the payload.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

SEED_PID = "f1aa52b9-aded-3188-9386-012244805ebf"


def _call(function_name: str, patient_id: str = SEED_PID, role: str = "PHYSICIAN") -> dict[str, Any]:
    from agent.tools.dispatch import execute_tool_function

    return execute_tool_function(
        function_name=function_name,
        arguments_json=f'{{"patient_id": "{patient_id}"}}',
        user_role=role,
        session_patient_id=patient_id,
    )


# ── Without FHIR credentials (default test env) ─────────────────────────────

class TestCsvFallback:
    """All five tools fall back to CSV when FHIR env vars are absent."""

    def test_demographics_source_is_csv(self):
        out = _call("get_patient_demographics")
        assert out.get("source") == "csv"
        assert "last" in out or "error" in out  # patient found or not-found, no crash

    def test_medications_source_is_csv(self):
        out = _call("list_active_medications")
        assert out.get("source") == "csv"

    def test_labs_source_is_csv(self):
        out = _call("list_recent_laboratory_results")
        assert out.get("source") == "csv"

    def test_vitals_source_is_csv(self):
        out = _call("list_recent_vital_signs")
        assert out.get("source") == "csv"

    def test_allergies_source_is_csv(self):
        out = _call("list_allergies")
        assert out.get("source") == "csv"


# ── With FHIR credentials mocked ────────────────────────────────────────────

class TestFhirPreferred:
    """When FHIR credentials are set, the FHIR helpers are called."""

    @pytest.fixture(autouse=True)
    def _set_fhir_env(self, monkeypatch):
        monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example")
        monkeypatch.setenv("OPENEMR_FHIR_CLIENT_ID", "test_client")
        monkeypatch.setenv("OPENEMR_FHIR_CLIENT_SECRET", "test_secret")

    def test_demographics_calls_fhir(self, monkeypatch):
        fake = {"source": "openemr_fhir", "last": "Smith", "first": "Jane", "fhir_id": "42"}
        monkeypatch.setattr("agent.tools.dispatch.fhir_patient_by_identifier", lambda _: fake)
        out = _call("get_patient_demographics")
        assert out["source"] == "openemr_fhir"
        assert out["last"] == "Smith"

    def test_medications_calls_fhir(self, monkeypatch):
        fake = {"source": "openemr_fhir", "count": 2, "medications": [{"description": "Metformin"}]}
        monkeypatch.setattr("agent.tools.dispatch.fhir_medications", lambda _: fake)
        out = _call("list_active_medications")
        assert out["source"] == "openemr_fhir"
        assert out["count"] == 2

    def test_labs_calls_fhir(self, monkeypatch):
        fake = {"source": "openemr_fhir", "count": 3, "labs": []}
        monkeypatch.setattr(
            "agent.tools.dispatch.fhir_observations", lambda _pid, cat: fake
        )
        out = _call("list_recent_laboratory_results")
        assert out["source"] == "openemr_fhir"

    def test_vitals_calls_fhir(self, monkeypatch):
        fake = {"source": "openemr_fhir", "count": 1, "vitals": []}
        monkeypatch.setattr(
            "agent.tools.dispatch.fhir_observations", lambda _pid, cat: fake
        )
        out = _call("list_recent_vital_signs")
        assert out["source"] == "openemr_fhir"

    def test_allergies_calls_fhir(self, monkeypatch):
        fake = {"source": "openemr_fhir", "count": 0, "allergies": []}
        monkeypatch.setattr("agent.tools.dispatch.fhir_allergies", lambda _: fake)
        out = _call("list_allergies")
        assert out["source"] == "openemr_fhir"


# ── Source key is always present ─────────────────────────────────────────────

class TestSourceKeyContract:
    """Regardless of backend, every successful payload has a 'source' key."""

    @pytest.mark.parametrize("fn", [
        "get_patient_demographics",
        "list_active_medications",
        "list_recent_laboratory_results",
        "list_recent_vital_signs",
        "list_allergies",
    ])
    def test_source_key_present(self, fn):
        out = _call(fn)
        assert "source" in out, f"{fn} payload missing 'source' key: {out}"
