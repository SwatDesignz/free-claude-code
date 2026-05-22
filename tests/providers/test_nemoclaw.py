"""Tests for Nemoclaw provider."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.anthropic.stream_contracts import (
    assert_anthropic_stream_contract,
    parse_sse_text,
    text_content,
)
from providers.base import ProviderConfig
from providers.nemoclaw import NEMOCLAW_DEFAULT_BASE, NemoclawProvider


class MockMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content


class MockRequest:
    def __init__(self, **kwargs):
        self.model = "nemoclaw/default"
        self.messages = [MockMessage("user", "Hello")]
        self.system = "System prompt"
        self.thinking = None
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = httpx.Response(
                self.status_code,
                request=httpx.Request("POST", "https://api.nemoclaw.com/v1/chat"),
            )
            raise httpx.HTTPStatusError(
                "error",
                request=response.request,
                response=response,
            )

    def json(self) -> dict:
        return self._payload


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    @asynccontextmanager
    async def _slot():
        yield

    with patch("providers.nemoclaw.client.GlobalRateLimiter") as mock:
        instance = mock.get_scoped_instance.return_value

        async def _passthrough(fn, *args, **kwargs):
            return await fn(*args, **kwargs)

        instance.execute_with_retry = AsyncMock(side_effect=_passthrough)
        instance.concurrency_slot.side_effect = _slot
        yield instance


def test_init_uses_default_base_url() -> None:
    with patch("httpx.AsyncClient"):
        provider = NemoclawProvider(ProviderConfig(api_key="key", base_url=None))
    assert provider._base_url == NEMOCLAW_DEFAULT_BASE


@pytest.mark.asyncio
async def test_stream_response_maps_messages_and_emits_text() -> None:
    provider = NemoclawProvider(
        ProviderConfig(api_key="key", base_url="https://api.nemoclaw.com")
    )
    req = MockRequest(
        messages=[
            MockMessage("assistant", [{"type": "text", "text": "Prior"}]),
            MockMessage("user", [{"type": "text", "text": "Next"}]),
        ]
    )
    with patch.object(
        provider._client,
        "post",
        new_callable=AsyncMock,
        return_value=MockResponse({"output": "Nemoclaw says hi"}),
    ) as mock_post:
        events = [
            event async for event in provider.stream_response(req, input_tokens=5)
        ]

    kwargs = mock_post.call_args.kwargs
    assert (
        kwargs["json"]["input"]
        == "system: System prompt\n\nassistant: Prior\n\nuser: Next"
    )
    parsed = parse_sse_text("".join(events))
    assert_anthropic_stream_contract(parsed)
    assert text_content(parsed) == "Nemoclaw says hi"


@pytest.mark.asyncio
async def test_stream_response_emits_error_envelope() -> None:
    provider = NemoclawProvider(
        ProviderConfig(api_key="key", base_url="https://api.nemoclaw.com")
    )
    req = MockRequest()

    with patch.object(
        provider._client,
        "post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("down"),
    ):
        events = [
            event async for event in provider.stream_response(req, request_id="REQ")
        ]

    parsed = parse_sse_text("".join(events))
    assert parsed[0].event == "message_start"
    assert parsed[-1].event == "message_stop"
    assert "REQ" in text_content(parsed)
