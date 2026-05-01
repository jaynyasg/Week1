"""Unit tests for ``agent.http.deps`` helpers."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from agent.http.deps import get_openemr_base_url


def test_get_openemr_base_url_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


def test_get_openemr_base_url_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "")
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


@pytest.mark.parametrize(
    "value",
    ["   ", "\t\n  ", "///"],
)
def test_get_openemr_base_url_raises_when_whitespace_or_slash_only(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", value)
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


def test_get_openemr_base_url_strips_trailing_slashes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.com/")
    assert get_openemr_base_url() == "https://openemr.example.com"


def test_get_openemr_base_url_strips_multiple_trailing_slashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.com///")
    assert get_openemr_base_url() == "https://openemr.example.com"


def test_get_openemr_base_url_strips_outer_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "  https://host/openemr/  ")
    assert get_openemr_base_url() == "https://host/openemr"


def test_get_openemr_base_url_unchanged_without_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://host/path")
    assert get_openemr_base_url() == "https://host/path"
