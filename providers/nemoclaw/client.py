"""Nemoclaw provider implementation."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
from loguru import logger

from core.anthropic import (
    SSEBuilder,
    append_request_id,
    extract_text_from_content,
    iter_provider_stream_error_sse_events,
)
from providers.base import BaseProvider, ProviderConfig
from providers.defaults import NEMOCLAW_DEFAULT_BASE
from providers.error_mapping import (
    map_error,
    user_visible_message_for_mapped_provider_error,
)
from providers.rate_limit import GlobalRateLimiter


class NemoclawProvider(BaseProvider):
    """Nemoclaw provider using ``POST /v1/chat``."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._provider_name = "NEMOCLAW"
        self._api_key = config.api_key
        self._base_url = (config.base_url or NEMOCLAW_DEFAULT_BASE).rstrip("/")
        self._global_rate_limiter = GlobalRateLimiter.get_scoped_instance(
            "nemoclaw",
            rate_limit=config.rate_limit,
            rate_window=config.rate_window,
            max_concurrency=config.max_concurrency,
        )
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            proxy=config.proxy or None,
            timeout=httpx.Timeout(
                config.http_read_timeout,
                connect=config.http_connect_timeout,
                read=config.http_read_timeout,
                write=config.http_write_timeout,
            ),
        )

    async def cleanup(self) -> None:
        await self._client.aclose()

    def _build_input(self, request: Any) -> str:
        parts: list[str] = []
        system = getattr(request, "system", None)
        if system:
            system_text = extract_text_from_content(system)
            if system_text.strip():
                parts.append(f"system: {system_text.strip()}")

        for message in getattr(request, "messages", []):
            role = str(getattr(message, "role", "user"))
            content = extract_text_from_content(getattr(message, "content", ""))
            if content.strip():
                parts.append(f"{role}: {content.strip()}")
        return "\n\n".join(parts).strip()

    async def _request_chat(self, request: Any) -> str:
        body = {"input": self._build_input(request)}
        response = await self._global_rate_limiter.execute_with_retry(
            self._client.post,
            "/v1/chat",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return str(payload)

        output = payload.get("output")
        if isinstance(output, str):
            return output

        message = payload.get("message")
        if isinstance(message, str):
            return message

        content = payload.get("content")
        if isinstance(content, str):
            return content

        return str(payload)

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        del thinking_enabled
        tag = self._provider_name
        req_tag = f" request_id={request_id}" if request_id else ""
        logger.info("{}_STREAM:{} model={}", tag, req_tag, request.model)
        sse = SSEBuilder(
            f"msg_{uuid.uuid4()}",
            request.model,
            input_tokens,
            log_raw_events=self._config.log_raw_sse_events,
        )

        try:
            async with self._global_rate_limiter.concurrency_slot():
                output = await self._request_chat(request)
        except Exception as error:
            self._log_stream_transport_error(tag, req_tag, error)
            mapped = map_error(error, rate_limiter=self._global_rate_limiter)
            base = user_visible_message_for_mapped_provider_error(
                mapped,
                provider_name=tag,
                read_timeout_s=self._config.http_read_timeout,
            )
            message = append_request_id(base, request_id)
            for event in iter_provider_stream_error_sse_events(
                request=request,
                input_tokens=input_tokens,
                error_message=message,
                sent_any_event=False,
                log_raw_sse_events=self._config.log_raw_sse_events,
            ):
                yield event
            return

        yield sse.message_start()
        for event in sse.ensure_text_block():
            yield event
        yield sse.emit_text_delta(output or " ")
        yield sse.stop_text_block()
        yield sse.message_delta("end_turn", sse.estimate_output_tokens())
        yield sse.message_stop()
