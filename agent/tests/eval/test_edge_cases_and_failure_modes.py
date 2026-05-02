"""Edge-case and failure-mode behavioral evals (no network, no OpenAI calls)."""

from __future__ import annotations

import json
import threading
from typing import Any

import pytest

from agent.access.rbac import ToolRefusal
from agent.tools.csv_cohort import CsvCohortStore, fixture_csv_root, reset_cohort_store_for_tests
from agent.tools.dispatch import execute_tool_function
from agent.tools.openemr_fhir import OpenEMRNotConfigured

SEED_PID = "f1aa52b9-aded-3188-9386-012244805ebf"
# A UUID that looks valid but is not present in the CSV fixture data
UNKNOWN_PID = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaaa"
# A phantom UUID injected manually into a store instance (but not loaded from CSV)
PHANTOM_PID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


@pytest.fixture(autouse=True)
def _reset_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXTURE_PATIENT_CSV_DIR", str(fixture_csv_root()))
    reset_cohort_store_for_tests()
    yield
    reset_cohort_store_for_tests()


def _load_store() -> CsvCohortStore:
    return CsvCohortStore.load(fixture_csv_root())


def _phantom_store() -> CsvCohortStore:
    """A store that has one patient record but no medications, labs, vitals, or allergies."""
    store = CsvCohortStore(root=fixture_csv_root())
    store.patients[PHANTOM_PID] = {
        "Id": PHANTOM_PID,
        "FIRST": "Ghost",
        "LAST": "Patient",
        "BIRTHDATE": "1980-01-01",
        "GENDER": "M",
        "RACE": "unknown",
        "ETHNICITY": "unknown",
        "CITY": "Nowhere",
        "STATE": "TX",
    }
    # medications, observations, allergies dicts remain empty (default_factory=dict)
    return store


# ---------------------------------------------------------------------------
# Multi-tool sequential dispatch
# ---------------------------------------------------------------------------


class TestMultiToolSequence:
    """Calling multiple tools for the same patient in a single process."""

    def test_demographics_then_allergies_both_succeed(self) -> None:
        store = _load_store()
        args = json.dumps({"patient_id": SEED_PID})

        demo = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=args,
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
            store=store,
        )
        allergy = execute_tool_function(
            function_name="list_allergies",
            arguments_json=args,
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
            store=store,
        )

        assert "error" not in demo
        assert "error" not in allergy
        assert demo.get("last") == "Brekke496"
        assert "allergies" in allergy

    def test_multi_tool_source_key_is_csv_without_fhir_credentials(self) -> None:
        """Without FHIR env vars every successful CSV tool reports source='csv'."""
        store = _load_store()
        args = json.dumps({"patient_id": SEED_PID})
        for fn in ("get_patient_demographics", "list_allergies"):
            result = execute_tool_function(
                function_name=fn,
                arguments_json=args,
                user_role="PHYSICIAN",
                session_patient_id=SEED_PID,
                store=store,
            )
            assert result.get("source") == "csv", f"Expected source='csv' for {fn}"

    def test_sequential_calls_return_correct_rbac_tool_keys(self) -> None:
        store = _load_store()
        args = json.dumps({"patient_id": SEED_PID})
        expected = {
            "get_patient_demographics": "demographics",
            "list_allergies": "allergies",
        }
        for fn, rbac_key in expected.items():
            result = execute_tool_function(
                function_name=fn,
                arguments_json=args,
                user_role="PHYSICIAN",
                session_patient_id=SEED_PID,
                store=store,
            )
            assert result.get("rbac_tool") == rbac_key, (
                f"Wrong rbac_tool for {fn}: got {result.get('rbac_tool')!r}"
            )


# ---------------------------------------------------------------------------
# RBAC permissions — roles that should PASS
# ---------------------------------------------------------------------------


class TestRBACPermissionsPass:
    """Roles that the matrix permits must not raise ToolRefusal."""

    def test_nurse_can_call_get_patient_demographics(self) -> None:
        store = _load_store()
        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=json.dumps({"patient_id": SEED_PID}),
            user_role="NURSE",
            session_patient_id=SEED_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("last") == "Brekke496"

    def test_admin_can_call_get_patient_demographics(self) -> None:
        store = _load_store()
        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=json.dumps({"patient_id": SEED_PID}),
            user_role="ADMIN",
            session_patient_id=SEED_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("rbac_tool") == "demographics"

    def test_rbac_tool_key_present_on_all_physician_tools(self) -> None:
        """Every tool that succeeds must include the rbac_tool key in its payload."""
        store = _load_store()
        args = json.dumps({"patient_id": SEED_PID})
        expected_rbac_values = {
            "get_patient_demographics": "demographics",
            "list_active_medications": "medications",
            "list_recent_laboratory_results": "labs",
            "list_recent_vital_signs": "vitals",
            "list_allergies": "allergies",
        }
        for fn, expected_val in expected_rbac_values.items():
            result = execute_tool_function(
                function_name=fn,
                arguments_json=args,
                user_role="PHYSICIAN",
                session_patient_id=SEED_PID,
                store=store,
            )
            assert result.get("rbac_tool") == expected_val, (
                f"rbac_tool mismatch for {fn}: {result.get('rbac_tool')!r}"
            )


# ---------------------------------------------------------------------------
# Empty / whitespace patient_id inputs
# ---------------------------------------------------------------------------


class TestEmptyAndWhitespaceInputs:
    """Whitespace and empty patient_id must trigger scope violation, not a crash."""

    @pytest.mark.parametrize("pid_value", ["", "   ", "\t\n"])
    def test_whitespace_patient_id_triggers_scope_violation(self, pid_value: str) -> None:
        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=json.dumps({"patient_id": pid_value}),
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
        )
        assert result.get("error") == "patient_scope_violation"

    def test_empty_arguments_json_triggers_scope_violation(self) -> None:
        """Empty string arguments_json is treated as '{}', missing patient_id → scope violation."""
        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json="",
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
        )
        assert result.get("error") == "patient_scope_violation"


# ---------------------------------------------------------------------------
# Patients with no clinical data — count=0 is not an error
# ---------------------------------------------------------------------------


class TestMissingPatientData:
    """Tools for patients with no clinical data rows return count=0, not an error."""

    def test_no_medications_returns_count_zero_not_error(self) -> None:
        store = _phantom_store()
        result = execute_tool_function(
            function_name="list_active_medications",
            arguments_json=json.dumps({"patient_id": PHANTOM_PID}),
            user_role="PHYSICIAN",
            session_patient_id=PHANTOM_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("count") == 0
        assert result.get("medications") == []

    def test_no_allergies_returns_count_zero_not_error(self) -> None:
        store = _phantom_store()
        result = execute_tool_function(
            function_name="list_allergies",
            arguments_json=json.dumps({"patient_id": PHANTOM_PID}),
            user_role="PHYSICIAN",
            session_patient_id=PHANTOM_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("count") == 0
        assert result.get("allergies") == []

    def test_demographics_for_unknown_patient_returns_patient_not_found(self) -> None:
        """Patient UUID not in CSV → demographics returns patient_not_found, not a crash."""
        store = _load_store()
        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=json.dumps({"patient_id": UNKNOWN_PID}),
            user_role="PHYSICIAN",
            session_patient_id=UNKNOWN_PID,
            store=store,
        )
        assert result.get("error") == "patient_not_found"

    def test_medications_for_unknown_patient_returns_empty_not_error(self) -> None:
        """medications_payload does not require patient to exist in patients dict."""
        store = _load_store()
        result = execute_tool_function(
            function_name="list_active_medications",
            arguments_json=json.dumps({"patient_id": UNKNOWN_PID}),
            user_role="PHYSICIAN",
            session_patient_id=UNKNOWN_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("count") == 0


# ---------------------------------------------------------------------------
# Extra / unexpected keys in arguments JSON
# ---------------------------------------------------------------------------


class TestArgumentsHandling:
    """Extra or deeply nested keys in arguments JSON are handled gracefully."""

    def test_extra_unknown_keys_in_arguments_are_ignored(self) -> None:
        store = _load_store()
        args = json.dumps({
            "patient_id": SEED_PID,
            "extra_key": "should be ignored",
            "another_field": 42,
            "nested": {"x": 1},
        })
        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=args,
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("last") == "Brekke496"

    def test_deeply_nested_junk_in_arguments_doesnt_crash(self) -> None:
        store = _load_store()
        # Build 50-level deep nested structure
        nested: Any = {"leaf": "junk"}
        for _ in range(50):
            nested = {"child": nested, "data": "x" * 100}
        big_args = json.dumps({"patient_id": SEED_PID, "nested_junk": nested})

        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=big_args,
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("last") == "Brekke496"


# ---------------------------------------------------------------------------
# Unhandled function path (in FUNCTION_TO_RBAC map but no if/elif branch)
# ---------------------------------------------------------------------------


class TestUnhandledFunctionPath:
    """An RBAC-approved function with no dispatch branch returns unhandled_function, not rbac_refusal."""

    def test_unhandled_function_error_not_rbac_refusal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import agent.tools.dispatch as dispatch_mod

        # Inject a fake function into the RBAC map without adding an if/elif handler
        patched_map = dict(dispatch_mod.FUNCTION_TO_RBAC)
        patched_map["fake_unmapped_function"] = "demographics"  # valid rbac tool
        monkeypatch.setattr(dispatch_mod, "FUNCTION_TO_RBAC", patched_map)

        store = _load_store()
        result = execute_tool_function(
            function_name="fake_unmapped_function",
            arguments_json=json.dumps({"patient_id": SEED_PID}),
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
            store=store,
        )
        assert result.get("error") == "unhandled_function"
        assert result.get("error") != "rbac_refusal"


# ---------------------------------------------------------------------------
# OpenEMR FHIR module raises OpenEMRNotConfigured when env vars absent
# ---------------------------------------------------------------------------


class TestOpenEMRNotConfigured:
    """Direct unit tests of the openemr_fhir._cfg() sentinel."""

    def test_cfg_raises_when_no_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
        monkeypatch.delenv("OPENEMR_FHIR_CLIENT_ID", raising=False)
        monkeypatch.delenv("OPENEMR_FHIR_CLIENT_SECRET", raising=False)

        from agent.tools.openemr_fhir import _cfg  # noqa: PLC0415

        with pytest.raises(OpenEMRNotConfigured):
            _cfg()

    def test_cfg_raises_when_only_base_url_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENEMR_BASE_URL", "https://example.com")
        monkeypatch.delenv("OPENEMR_FHIR_CLIENT_ID", raising=False)
        monkeypatch.delenv("OPENEMR_FHIR_CLIENT_SECRET", raising=False)

        from agent.tools.openemr_fhir import _cfg  # noqa: PLC0415

        with pytest.raises(OpenEMRNotConfigured):
            _cfg()

    def test_fhir_functions_fall_through_to_csv_when_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Integration: FHIR not configured → dispatch falls back to CSV, no exception bubbles up."""
        monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
        monkeypatch.delenv("OPENEMR_FHIR_CLIENT_ID", raising=False)
        monkeypatch.delenv("OPENEMR_FHIR_CLIENT_SECRET", raising=False)
        store = _load_store()

        result = execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=json.dumps({"patient_id": SEED_PID}),
            user_role="PHYSICIAN",
            session_patient_id=SEED_PID,
            store=store,
        )
        assert "error" not in result
        assert result.get("source") == "csv"


# ---------------------------------------------------------------------------
# Thread safety of get_cohort_store singleton
# ---------------------------------------------------------------------------


class TestConcurrentRBAC:
    """Two different roles concurrently calling the same tool must not corrupt state."""

    def test_concurrent_physician_and_admin_calls_no_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FIXTURE_PATIENT_CSV_DIR", str(fixture_csv_root()))
        reset_cohort_store_for_tests()

        results: list[dict[str, Any]] = []
        errors: list[Exception] = []

        def call_as(role: str) -> None:
            try:
                r = execute_tool_function(
                    function_name="get_patient_demographics",
                    arguments_json=json.dumps({"patient_id": SEED_PID}),
                    user_role=role,
                    session_patient_id=SEED_PID,
                )
                results.append(r)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = (
            [threading.Thread(target=call_as, args=("PHYSICIAN",)) for _ in range(5)]
            + [threading.Thread(target=call_as, args=("ADMIN",)) for _ in range(5)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Concurrent calls raised exceptions: {errors}"
        assert len(results) == 10
        for r in results:
            assert "error" not in r, f"Unexpected error in concurrent result: {r}"
            assert r.get("last") == "Brekke496"
