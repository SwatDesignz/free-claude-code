"""Minimal remote MCP server (Streamable HTTP) so FCC can be added as a connector.

Add ``https://<your-public-fcc-url>/mcp`` as a custom connector on claude.ai; it
then syncs to the Claude apps on iOS and Android. The server exposes one tool,
``ask``, which sends a prompt through FCC's configured model routing.
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from .dependencies import get_services, require_proxy_auth
from .ports import ApiServices
from .request_ids import get_request_id
from .routes import _create_messages_response

router = APIRouter()

_PROTOCOL_VERSION = "2025-03-26"
_ASK_TOOL = {
    "name": "ask",
    "description": "Send a prompt to the model configured in Free Claude Code.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The prompt to send."},
            "model": {
                "type": "string",
                "description": "Optional model id; defaults to FCC's configured model.",
            },
        },
        "required": ["prompt"],
    },
}


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _text_result(text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


async def _call_ask(
    services: ApiServices, arguments: dict[str, Any], request: Request
) -> dict[str, Any]:
    prompt = arguments.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return _text_result("'prompt' must be a non-empty string.", is_error=True)
    model = arguments.get("model")
    body: dict[str, Any] = {
        "model": model if isinstance(model, str) and model.strip() else "default",
        "max_tokens": 4096,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
    }
    if body["model"] == "default":
        body["model"] = services.requests.current_settings().model
    response = await _create_messages_response(
        services, body, request_id=get_request_id(request)
    )
    payload: Any = response
    if isinstance(response, Response):
        try:
            payload = json.loads(bytes(response.body))
        except AttributeError, ValueError:
            return _text_result("Unexpected response from model.", is_error=True)
        if response.status_code >= 400:
            detail = (
                payload.get("error", {}).get("message")
                if isinstance(payload, dict)
                else None
            )
            return _text_result(detail or "Model request failed.", is_error=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict):
        return _text_result("Unexpected response from model.", is_error=True)
    parts = [
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return _text_result("".join(parts))


async def _dispatch(
    message: Any, services: ApiServices, request: Request
) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid request")
    msg_id = message.get("id")
    method = message.get("method")
    if msg_id is None:  # notification
        return None
    if method == "initialize":
        return _result(
            msg_id,
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "free-claude-code", "version": "1"},
            },
        )
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": [_ASK_TOOL]})
    if method == "tools/call":
        params = message.get("params") or {}
        if params.get("name") != "ask":
            return _error(msg_id, -32602, "Unknown tool")
        arguments = params.get("arguments")
        return _result(
            msg_id,
            await _call_ask(
                services, arguments if isinstance(arguments, dict) else {}, request
            ),
        )
    return _error(msg_id, -32601, "Method not found")


@router.post("/mcp")
async def mcp_endpoint(
    request: Request,
    services: ApiServices = Depends(get_services),
    _auth=Depends(require_proxy_auth),
):
    """Handle MCP JSON-RPC requests (single or batched)."""
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse(_error(None, -32700, "Parse error"), status_code=400)
    if isinstance(body, list):
        replies = [r for m in body if (r := await _dispatch(m, services, request))]
        if not replies:
            return Response(status_code=202)
        return JSONResponse(replies)
    reply = await _dispatch(body, services, request)
    if reply is None:
        return Response(status_code=202)
    return JSONResponse(reply)


@router.get("/mcp")
async def mcp_stream_unsupported() -> Response:
    return Response(status_code=405, headers={"Allow": "POST"})
