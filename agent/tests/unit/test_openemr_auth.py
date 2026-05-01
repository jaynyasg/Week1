"""OpenEMR /api/user session validation (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agent.access.openemr_auth import (
    OpenEMRAuthError,
    fetch_openemr_user_json,
    map_openemr_payload_to_agent_role,
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
    assert args[0].endswith("/api/user")
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
