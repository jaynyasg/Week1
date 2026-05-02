"""Behavioral tests for the OpenAI tool loop using a stub client (no network)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from agent.runtime.rgv_pipeline import ClinicalTurnState
from agent.services import openai_tool_loop as otl
from agent.tools.csv_cohort import fixture_csv_root, reset_cohort_store_for_tests


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-stub")
    monkeypatch.setenv("FIXTURE_PATIENT_CSV_DIR", str(fixture_csv_root()))
    reset_cohort_store_for_tests()
    yield
    reset_cohort_store_for_tests()


def _assistant(content: str | None = None, *, tool_calls: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        role="assistant",
        content=content,
        tool_calls=tool_calls or [],
    )


def _tool_call(name: str, arguments: dict[str, Any], call_id: str = "tc1") -> Any:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


def _completion(message: Any) -> Any:
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _StubCompletions:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []
        self._i = 0

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._i >= len(self._responses):
            raise AssertionError(f"unexpected extra API call (had {len(self._responses)})")
        r = self._responses[self._i]
        self._i += 1
        return r


class _StubChat:
    def __init__(self, responses: list[Any]) -> None:
        self.completions = _StubCompletions(responses)


class _StubOpenAI:
    def __init__(self, responses: list[Any], **_kwargs: Any) -> None:
        self.chat = _StubChat(responses)


PID = "f1aa52b9-aded-3188-9386-012244805ebf"


def _state(**kwargs: Any) -> ClinicalTurnState:
    defaults = {
        "patient_id": PID,
        "user_role": "PHYSICIAN",
        "session_id": "sess-1",
        "messages": [{"role": "user", "content": "Summarize this patient."}],
    }
    defaults.update(kwargs)
    return ClinicalTurnState(**defaults)


@pytest.mark.llm_eval
def test_tool_loop_no_tools_returns_model_text(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubOpenAI([_completion(_assistant("Done without tools."))])
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    text = otl.complete_chat_openai_with_csv_tools(state)
    assert text == "Done without tools."
    assert state.tool_results.get("patient_id") == PID
    assert stub.chat.completions.calls[0].get("tool_choice") == "auto"


@pytest.mark.llm_eval
def test_tool_loop_single_demographics_then_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubOpenAI(
        [
            _completion(
                _assistant(
                    tool_calls=[
                        _tool_call(
                            "get_patient_demographics",
                            {"patient_id": PID},
                            "c1",
                        )
                    ],
                )
            ),
            _completion(_assistant("Patient Brekke496 reviewed.")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    text = otl.complete_chat_openai_with_csv_tools(state)
    assert "Brekke496" in text or "reviewed" in text
    ex = state.tool_results.get("executions") or []
    assert len(ex) == 1
    assert ex[0]["function"] == "get_patient_demographics"
    assert ex[0]["result"].get("last") == "Brekke496"


@pytest.mark.llm_eval
def test_tool_loop_parallel_two_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubOpenAI(
        [
            _completion(
                _assistant(
                    tool_calls=[
                        _tool_call("list_active_medications", {"patient_id": PID}, "m1"),
                        _tool_call("list_allergies", {"patient_id": PID}, "a1"),
                    ],
                )
            ),
            _completion(_assistant("Medications and allergies summarized.")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    text = otl.complete_chat_openai_with_csv_tools(state)
    assert "summarized" in text.lower()
    names = {e["function"] for e in (state.tool_results.get("executions") or [])}
    assert names == {"list_active_medications", "list_allergies"}


@pytest.mark.llm_eval
def test_tool_loop_nurse_labs_rbac_then_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubOpenAI(
        [
            _completion(
                _assistant(
                    tool_calls=[
                        _tool_call("list_recent_laboratory_results", {"patient_id": PID}, "l1"),
                    ],
                )
            ),
            _completion(_assistant("I cannot access labs; vitals only if needed.")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state(user_role="NURSE")
    text = otl.complete_chat_openai_with_csv_tools(state)
    assert "cannot" in text.lower() or "vitals" in text.lower()
    ex = state.tool_results.get("executions") or []
    assert ex[0]["result"].get("error") == "rbac_refusal"


@pytest.mark.llm_eval
def test_tool_loop_exhausts_max_rounds(monkeypatch: pytest.MonkeyPatch) -> None:
    always_tools = _completion(
        _assistant(
            tool_calls=[
                _tool_call("get_patient_demographics", {"patient_id": PID}, "x"),
            ],
        ),
    )
    stub = _StubOpenAI([always_tools] * 10)
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    with pytest.raises(RuntimeError, match="Exceeded"):
        otl.complete_chat_openai_with_csv_tools(state)


@pytest.mark.llm_eval
def test_tool_loop_empty_final_content_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubOpenAI(
        [
            _completion(_assistant("")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    with pytest.raises(RuntimeError, match="empty content"):
        otl.complete_chat_openai_with_csv_tools(state)


@pytest.mark.llm_eval
def test_tool_loop_second_round_after_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model retries with an allowed tool after RBAC refusal."""
    stub = _StubOpenAI(
        [
            _completion(
                _assistant(
                    tool_calls=[_tool_call("list_recent_laboratory_results", {"patient_id": PID}, "l1")],
                )
            ),
            _completion(
                _assistant(
                    tool_calls=[_tool_call("list_recent_vital_signs", {"patient_id": PID}, "v1")],
                )
            ),
            _completion(_assistant("Used vitals instead.")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state(user_role="NURSE")
    text = otl.complete_chat_openai_with_csv_tools(state)
    assert "vitals" in text.lower()
    ex = state.tool_results.get("executions") or []
    assert ex[0]["result"]["error"] == "rbac_refusal"
    assert ex[1]["function"] == "list_recent_vital_signs"
    assert "error" not in ex[1]["result"]


@pytest.mark.llm_eval
def test_messages_include_tools_in_second_request(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubOpenAI(
        [
            _completion(
                _assistant(
                    tool_calls=[_tool_call("get_patient_demographics", {"patient_id": PID}, "c1")],
                )
            ),
            _completion(_assistant("ok")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    otl.complete_chat_openai_with_csv_tools(state)
    second = stub.chat.completions.calls[1]["messages"]
    roles = [m["role"] for m in second]
    assert roles.count("tool") == 1
    tool_msg = next(m for m in second if m["role"] == "tool")
    assert tool_msg.get("tool_call_id") == "c1"
    body = json.loads(tool_msg["content"])
    assert body.get("last") == "Brekke496"


@pytest.mark.llm_eval
@pytest.mark.parametrize(
    ("fn", "key"),
    [
        ("list_active_medications", "medications"),
        ("list_recent_laboratory_results", "labs"),
        ("list_recent_vital_signs", "vitals"),
    ],
)
def test_tool_loop_each_payload_shape(
    monkeypatch: pytest.MonkeyPatch, fn: str, key: str
) -> None:
    stub = _StubOpenAI(
        [
            _completion(_assistant(tool_calls=[_tool_call(fn, {"patient_id": PID}, "t1")])),
            _completion(_assistant("done")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    otl.complete_chat_openai_with_csv_tools(state)
    res = (state.tool_results.get("executions") or [])[0]["result"]
    assert key in res
    assert res.get("patient_id") == PID


@pytest.mark.llm_eval
def test_tool_loop_wrong_patient_id_in_args(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubOpenAI(
        [
            _completion(
                _assistant(
                    tool_calls=[
                        _tool_call(
                            "get_patient_demographics",
                            {"patient_id": "00000000-0000-0000-0000-000000000099"},
                            "bad",
                        ),
                    ],
                )
            ),
            _completion(_assistant("Acknowledged scope error in tool output.")),
        ]
    )
    monkeypatch.setattr("openai.OpenAI", lambda **kw: stub)
    state = _state()
    otl.complete_chat_openai_with_csv_tools(state)
    res = (state.tool_results.get("executions") or [])[0]["result"]
    assert res.get("error") == "patient_scope_violation"


@pytest.mark.llm_eval
def test_transcript_skips_non_user_assistant_messages() -> None:
    state = _state(
        messages=[
            {"role": "user", "content": "Hi"},
            {"role": "system", "content": "ignored"},
            {"role": "tool", "content": "{}"},
            {"role": "assistant", "content": "prior"},
            {"role": "user", "content": "Next"},
        ],
    )
    transcript = otl._transcript_without_retrieve_blob(state)
    roles = [m["role"] for m in transcript]
    assert roles[0] == "system"
    user_contents = [m["content"] for m in transcript if m["role"] == "user"]
    assert user_contents == ["Hi", "Next"]


@pytest.mark.llm_eval
def test_message_to_dict_serializes_tool_calls() -> None:
    msg = _assistant(
        tool_calls=[_tool_call("list_allergies", {"patient_id": PID}, "z")],
    )
    d = otl._message_to_dict(msg)
    assert d["role"] == "assistant"
    assert len(d["tool_calls"]) == 1
    assert d["tool_calls"][0]["function"]["name"] == "list_allergies"
