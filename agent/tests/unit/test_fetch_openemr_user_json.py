"""Unit tests for ``fetch_openemr_user_json`` (httpx paths, no live network)."""

from __future__ import annotations

import httpx
import pytest

from agent.access.openemr_auth import OpenEMRAuthError, fetch_openemr_user_json


def _req(url: str = "https://openemr.example/apis/default/api/user") -> httpx.Request:
    return httpx.Request("GET", url)


@pytest.mark.asyncio
async def test_fetch_missing_credentials_raises() -> None:
    def _must_not_request(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP must not be called when credentials are missing")

    transport = httpx.MockTransport(_must_not_request)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(OpenEMRAuthError) as ei:
            await fetch_openemr_user_json(
                "https://openemr.example",
                authorization_header_value=None,
                cookie_header_value="   ",
                client=client,
            )
    assert ei.value.reason_code == "missing_credentials"


@pytest.mark.asyncio
async def test_fetch_request_error_maps_to_upstream_unreachable() -> None:
    class BoomClient:
        async def get(self, *_a, **_kw):  # noqa: ANN002,ANN003
            raise httpx.ConnectError("simulated failure", request=_req())

    with pytest.raises(OpenEMRAuthError) as ei:
        await fetch_openemr_user_json(
            "https://openemr.example",
            authorization_header_value="Bearer tok",
            cookie_header_value=None,
            client=BoomClient(),
        )
    assert ei.value.reason_code == "upstream_unreachable"


@pytest.mark.asyncio
async def test_fetch_non_200_maps_reason_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/apis/default/api/user")
        return httpx.Response(401, text="no")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(OpenEMRAuthError) as ei:
            await fetch_openemr_user_json(
                "https://openemr.example",
                authorization_header_value="Bearer x",
                cookie_header_value=None,
                client=client,
            )
    assert ei.value.reason_code == "openemr_http_401"


@pytest.mark.asyncio
async def test_fetch_invalid_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"not-json-at-all",
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(OpenEMRAuthError) as ei:
            await fetch_openemr_user_json(
                "https://openemr.example",
                authorization_header_value="Bearer x",
                cookie_header_value=None,
                client=client,
            )
    assert ei.value.reason_code == "invalid_json"


@pytest.mark.asyncio
async def test_fetch_non_object_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an", "object"])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(OpenEMRAuthError) as ei:
            await fetch_openemr_user_json(
                "https://openemr.example",
                authorization_header_value="Bearer x",
                cookie_header_value=None,
                client=client,
            )
    assert ei.value.reason_code == "invalid_payload_shape"


@pytest.mark.asyncio
async def test_fetch_success_returns_dict() -> None:
    payload = {"data": {"agent_role": "PHYSICIAN"}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        out = await fetch_openemr_user_json(
            "https://openemr.example",
            authorization_header_value="Bearer x",
            cookie_header_value=None,
            client=client,
        )
    assert out == {"agent_role": "PHYSICIAN"}


@pytest.mark.asyncio
async def test_fetch_cookie_only_sends_cookie_header() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["cookie"] = request.headers.get("cookie", "")
        seen["authorization"] = request.headers.get("authorization", "")
        assert str(request.url).endswith("/interface/copilot_session_probe.php")
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        out = await fetch_openemr_user_json(
            "https://openemr.example",
            authorization_header_value=None,
            cookie_header_value="OpenEMR=a; PHPSESSID=b",
            client=client,
        )
    assert out == {"ok": True}
    assert "OpenEMR=a" in seen["cookie"]
    assert seen["authorization"] == ""
