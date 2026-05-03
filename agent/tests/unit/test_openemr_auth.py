"""OpenEMR session validation (mocked HTTP): session probe vs Standard API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agent.access.openemr_auth import (
    OpenEMRAuthError,
    fetch_openemr_user_json,
    map_openemr_payload_to_agent_role,
    normalize_openemr_user_payload,
    validate_session_and_resolve_role,
)


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"agent_role": "physician"}, "PHYSICIAN"),
        ({"copilot_role": "NURSE"}, "NURSE"),
        ({"groups": ["Admin"]}, "ADMIN"),
        ({"groups": ["Registered Nurse"]}, "NURSE"),
        ({"groups": ["Physician"]}, "PHYSICIAN"),
        ({}, None),
    ],
)
def test_map_role(payload: dict, expected: str | None) -> None:
    assert map_openemr_payload_to_agent_role(payload) == expected


def test_normalize_openemr_user_payload_unwraps_single_data_row() -> None:
    out = normalize_openemr_user_payload(
        {"data": [{"username": "a", "acl": ["Physicians"]}]}
    )
    assert out["username"] == "a"
    assert out["groups"] == ["Physicians"]


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_respects_openemr_http_timeout_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_HTTP_TIMEOUT_SECONDS", "7")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_role": "PHYSICIAN"}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    await fetch_openemr_user_json(
        "https://example.com/",
        authorization_header_value="Bearer t",
        client=client,
    )
    _args, kwargs = client.get.await_args
    assert kwargs["timeout"] == 7.0


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_forwards_request_id() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_role": "NURSE"}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    await fetch_openemr_user_json(
        "https://example.com/openemr",
        authorization_header_value="Bearer token",
        client=client,
        request_id="upstream-trace-7",
    )
    _args, kwargs = client.get.await_args
    assert kwargs["headers"]["X-Request-ID"] == "upstream-trace-7"


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_success() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_role": "NURSE"}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    data = await fetch_openemr_user_json(
        "https://example.com/openemr",
        authorization_header_value="Bearer token",
        client=client,
    )
    assert data["agent_role"] == "NURSE"
    client.get.assert_awaited_once()
    args, kwargs = client.get.await_args
    assert args[0].endswith("/apis/default/api/user")
    assert kwargs["headers"]["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_rejects_non_200() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 401
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(OpenEMRAuthError):
        await fetch_openemr_user_json(
            "https://example.com/",
            authorization_header_value="Bearer x",
            client=client,
        )


@pytest.mark.asyncio
async def test_validate_session_and_resolve_role() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_role": "ADMIN"}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    role = await validate_session_and_resolve_role(
        "https://e/",
        authorization_header_value="Bearer t",
        client=client,
    )
    assert role == "ADMIN"


@pytest.mark.asyncio
async def test_validate_session_unknown_role() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(OpenEMRAuthError):
        await validate_session_and_resolve_role(
            "https://e/",
            authorization_header_value="Bearer t",
            client=client,
        )


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_cookie_only_sends_cookie_no_authorization() -> (
    None
):
    """Cookie-only auth path: outbound request has Cookie header but NOT Authorization."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_role": "PHYSICIAN"}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    data = await fetch_openemr_user_json(
        "https://example.com/openemr",
        cookie_header_value="OpenEMR=abc; PHPSESSID=xyz; token_main=tok",
        client=client,
    )
    assert data["agent_role"] == "PHYSICIAN"
    client.get.assert_awaited_once()
    _args, kwargs = client.get.await_args
    headers = kwargs["headers"]
    assert headers["Cookie"] == "OpenEMR=abc; PHPSESSID=xyz; token_main=tok"
    assert "Authorization" not in headers
    assert _args[0].endswith("/interface/copilot_session_probe.php")


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_authorization_only_unchanged() -> None:
    """Authorization-only path: existing Bearer behavior is unchanged (no Cookie sent)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_role": "ADMIN"}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    await fetch_openemr_user_json(
        "https://example.com/openemr",
        authorization_header_value="Bearer token-only",
        client=client,
    )
    _args, kwargs = client.get.await_args
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer token-only"
    assert "Cookie" not in headers
    assert _args[0] == "https://example.com/openemr/apis/default/api/user"


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_both_headers_present() -> None:
    """Both Authorization and Cookie are forwarded when both are provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_role": "NURSE"}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    await fetch_openemr_user_json(
        "https://example.com/openemr",
        authorization_header_value="Bearer t",
        cookie_header_value="OpenEMR=abc; PHPSESSID=xyz",
        client=client,
    )
    _args, kwargs = client.get.await_args
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer t"
    assert headers["Cookie"] == "OpenEMR=abc; PHPSESSID=xyz"
    assert _args[0].endswith("/interface/copilot_session_probe.php")


@pytest.mark.asyncio
async def test_fetch_openemr_user_json_blank_both_raises_before_http() -> None:
    """Blank/None for both Authorization and Cookie raises before any HTTP call."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()

    with pytest.raises(OpenEMRAuthError):
        await fetch_openemr_user_json(
            "https://example.com/openemr",
            authorization_header_value="",
            cookie_header_value="   ",
            client=client,
        )
    client.get.assert_not_awaited()

    with pytest.raises(OpenEMRAuthError):
        await fetch_openemr_user_json(
            "https://example.com/openemr",
            client=client,
        )
    client.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_session_and_resolve_role_cookie_only() -> None:
    """Cookie-only path hits session probe and resolves role from JSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"groups": ["Admin"]}

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)

    role = await validate_session_and_resolve_role(
        "https://e/",
        cookie_header_value="OpenEMR=cookie-value",
        client=client,
    )
    assert role == "ADMIN"
    _args, kwargs = client.get.await_args
    headers = kwargs["headers"]
    assert "Cookie" in headers
    assert "Authorization" not in headers
    assert _args[0].endswith("/interface/copilot_session_probe.php")


@pytest.mark.asyncio
async def test_validate_session_blank_both_raises() -> None:
    """validate_session_and_resolve_role rejects blank-only inputs without HTTP call."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()

    with pytest.raises(OpenEMRAuthError):
        await validate_session_and_resolve_role(
            "https://e/",
            authorization_header_value=None,
            cookie_header_value=None,
            client=client,
        )
    client.get.assert_not_awaited()
