"""Integration: missing OPENEMR_BASE_URL fails in get_openemr_base_url before OpenEMR HTTP."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "patch_openemr_base_url",
    [
        pytest.param("delenv", id="unset"),
        pytest.param("empty", id="empty"),
    ],
)
def test_tools_demographics_returns_500_when_openemr_base_url_misconfigured(
    app,
    monkeypatch: pytest.MonkeyPatch,
    patch_openemr_base_url: str,
) -> None:
    with TestClient(app) as client:
        if patch_openemr_base_url == "delenv":
            monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
        else:
            monkeypatch.setenv("OPENEMR_BASE_URL", "")
        r = client.post(
            "/agent/tools/demographics",
            headers={"Authorization": "Bearer x"},
        )
    assert r.status_code == 500
    detail = r.json().get("detail", "")
    assert "OPENEMR_BASE_URL" in str(detail) and "not configured" in str(detail)


@pytest.mark.parametrize(
    "patch_openemr_base_url",
    [
        pytest.param("delenv", id="unset"),
        pytest.param("empty", id="empty"),
    ],
)
def test_chat_returns_500_when_openemr_base_url_misconfigured(
    app,
    monkeypatch: pytest.MonkeyPatch,
    patch_openemr_base_url: str,
) -> None:
    with TestClient(app) as client:
        if patch_openemr_base_url == "delenv":
            monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
        else:
            monkeypatch.setenv("OPENEMR_BASE_URL", "")
        r = client.post(
            "/agent/chat",
            json={
                "patient_id": "pat-1",
                "user_message": "hello",
                "messages": [],
            },
            headers={"Authorization": "Bearer x"},
        )
    assert r.status_code == 500
    detail = r.json().get("detail", "")
    assert "OPENEMR_BASE_URL" in str(detail) and "not configured" in str(detail)
