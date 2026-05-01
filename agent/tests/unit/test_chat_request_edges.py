"""ChatRequest validation edge cases for required string fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.http.schemas import ChatRequest


@pytest.mark.parametrize(
    ("patient_id", "user_message"),
    [
        ("", "hi"),
        ("p1", ""),
    ],
    ids=["empty_patient_id", "empty_user_message"],
)
def test_chat_request_rejects_empty_required_strings(
    patient_id: str, user_message: str
) -> None:
    with pytest.raises(ValidationError):
        ChatRequest(patient_id=patient_id, user_message=user_message)


def test_chat_request_accepts_whitespace_only_strings() -> None:
    """min_length=1 counts all characters; strip is not applied."""
    req = ChatRequest(patient_id="   ", user_message="\t\n")
    assert req.patient_id == "   "
    assert req.user_message == "\t\n"
