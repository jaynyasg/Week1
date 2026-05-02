"""RBAC + argument validation for CSV-backed OpenAI tool functions (no network)."""

from __future__ import annotations

import json

import pytest

from agent.access.rbac import ToolRefusal
from agent.tools.csv_cohort import CsvCohortStore, fixture_csv_root, reset_cohort_store_for_tests
from agent.tools.dispatch import execute_tool_function, openai_tool_schemas

PID = "f1aa52b9-aded-3188-9386-012244805ebf"
FUNCTIONS = [
    "get_patient_demographics",
    "list_active_medications",
    "list_recent_laboratory_results",
    "list_recent_vital_signs",
    "list_allergies",
]


def _cases() -> list[tuple[str, str, bool]]:
    """(role, function_name, expect_rbac_refusal)."""
    rows: list[tuple[str, str, bool]] = []
    for fn in FUNCTIONS:
        rows.append(("PHYSICIAN", fn, False))
    nurse_ok = {
        "get_patient_demographics",
        "list_active_medications",
        "list_recent_vital_signs",
        "list_allergies",
    }
    for fn in FUNCTIONS:
        rows.append(("NURSE", fn, fn not in nurse_ok))
    admin_ok = {"get_patient_demographics"}
    for fn in FUNCTIONS:
        rows.append(("ADMIN", fn, fn not in admin_ok))
    return rows


@pytest.fixture(autouse=True)
def _reset_store():
    reset_cohort_store_for_tests()
    yield
    reset_cohort_store_for_tests()


@pytest.mark.llm_eval
@pytest.mark.parametrize("role,fn,expect_refusal", _cases())
def test_execute_matrix_rbac(
    role: str, fn: str, expect_refusal: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIXTURE_PATIENT_CSV_DIR", str(fixture_csv_root()))
    reset_cohort_store_for_tests()
    store = CsvCohortStore.load(fixture_csv_root())
    args = json.dumps({"patient_id": PID})
    if expect_refusal:
        with pytest.raises(ToolRefusal):
            execute_tool_function(
                function_name=fn,
                arguments_json=args,
                user_role=role,
                session_patient_id=PID,
                store=store,
            )
    else:
        out = execute_tool_function(
            function_name=fn,
            arguments_json=args,
            user_role=role,
            session_patient_id=PID,
            store=store,
        )
        assert "error" not in out
        assert out.get("rbac_tool")


def test_unknown_function_returns_error() -> None:
    out = execute_tool_function(
        function_name="not_a_real_tool",
        arguments_json=json.dumps({"patient_id": PID}),
        user_role="PHYSICIAN",
        session_patient_id=PID,
    )
    assert out["error"] == "unknown_function"


def test_invalid_json_arguments() -> None:
    out = execute_tool_function(
        function_name="get_patient_demographics",
        arguments_json="{not json",
        user_role="PHYSICIAN",
        session_patient_id=PID,
    )
    assert out["error"] == "invalid_arguments_json"


@pytest.mark.parametrize(
    "wrong_pid",
    [
        "00000000-0000-0000-0000-000000000000",
        PID[:-1] + "x",
        "",
    ],
)
def test_patient_scope_mismatch(wrong_pid: str) -> None:
    out = execute_tool_function(
        function_name="get_patient_demographics",
        arguments_json=json.dumps({"patient_id": wrong_pid or "x"}),
        user_role="PHYSICIAN",
        session_patient_id=PID,
    )
    assert out["error"] == "patient_scope_violation"


def test_demographics_missing_patient_returns_not_found() -> None:
    out = execute_tool_function(
        function_name="get_patient_demographics",
        arguments_json=json.dumps({"patient_id": "00000000-0000-4000-8000-000000000001"}),
        user_role="PHYSICIAN",
        session_patient_id="00000000-0000-4000-8000-000000000001",
    )
    assert out.get("error") == "patient_not_found"


def test_openai_tool_schema_count() -> None:
    schemas = openai_tool_schemas()
    assert len(schemas) == 5
    names = {s["function"]["name"] for s in schemas}
    assert names == set(FUNCTIONS)


@pytest.mark.parametrize("fn", FUNCTIONS)
def test_each_schema_has_patient_id_required(fn: str) -> None:
    schemas = openai_tool_schemas()
    match = next(s for s in schemas if s["function"]["name"] == fn)
    req = match["function"]["parameters"].get("required", [])
    assert "patient_id" in req


@pytest.mark.parametrize("role", ["UNKNOWN", "GUEST", ""])
def test_unknown_roles_cannot_call_demographics(role: str) -> None:
    with pytest.raises(ToolRefusal):
        execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=json.dumps({"patient_id": PID}),
            user_role=role,
            session_patient_id=PID,
        )


def test_lowercase_physician_role_denied_by_canonical_matrix() -> None:
    """RBAC expects ``PHYSICIAN``; lowercase is treated as unknown (no tools)."""
    with pytest.raises(ToolRefusal):
        execute_tool_function(
            function_name="get_patient_demographics",
            arguments_json=json.dumps({"patient_id": PID}),
            user_role="physician",
            session_patient_id=PID,
        )


# --- Additional matrix rows (explicit) for eval coverage beyond param block ---


@pytest.mark.llm_eval
@pytest.mark.parametrize(
    ("role", "fn"),
    [
        ("PHYSICIAN", "get_patient_demographics"),
        ("PHYSICIAN", "list_active_medications"),
        ("PHYSICIAN", "list_recent_laboratory_results"),
        ("PHYSICIAN", "list_recent_vital_signs"),
        ("PHYSICIAN", "list_allergies"),
    ],
)
def test_physician_double_call_idempotent_shape(role: str, fn: str) -> None:
    store = CsvCohortStore.load(fixture_csv_root())
    args = json.dumps({"patient_id": PID})
    a = execute_tool_function(
        function_name=fn,
        arguments_json=args,
        user_role=role,
        session_patient_id=PID,
        store=store,
    )
    b = execute_tool_function(
        function_name=fn,
        arguments_json=args,
        user_role=role,
        session_patient_id=PID,
        store=store,
    )
    assert a == b
