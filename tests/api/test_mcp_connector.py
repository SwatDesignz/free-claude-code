from unittest.mock import AsyncMock, patch

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from free_claude_code.api.dependencies import get_settings
from free_claude_code.config.settings import Settings
from tests.api.support import create_test_app

PATCH_TARGET = "free_claude_code.api.mcp_routes._create_messages_response"


@pytest.fixture
def app():
    return create_test_app(Settings())


@pytest.fixture
def client(app):
    return TestClient(app)


def _rpc(id_, method, params=None):
    msg = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def _ask(prompt, **extra):
    return _rpc(
        1, "tools/call", {"name": "ask", "arguments": {"prompt": prompt, **extra}}
    )


def test_initialize_and_list_tools(client):
    r = client.post("/mcp", json=_rpc(1, "initialize"))
    assert r.json()["result"]["serverInfo"]["name"] == "free-claude-code"
    r = client.post("/mcp", json=_rpc(2, "tools/list"))
    assert r.json()["result"]["tools"][0]["name"] == "ask"
    assert client.post("/mcp", json=_rpc(3, "ping")).json()["result"] == {}


def test_notification_accepted_and_unknown_method(client):
    r = client.post(
        "/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    assert r.status_code == 202
    r = client.post("/mcp", json=_rpc(3, "nope"))
    assert r.json()["error"]["code"] == -32601


def test_get_not_supported(client):
    assert client.get("/mcp").status_code == 405


def test_parse_error_and_invalid_request(client):
    r = client.post(
        "/mcp", content=b"{nope", headers={"content-type": "application/json"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == -32700
    r = client.post("/mcp", json=5)
    assert r.json()["error"]["code"] == -32600


def test_ask_returns_text_from_dict_response(client):
    payload = {
        "content": [{"type": "text", "text": "hel"}, {"type": "text", "text": "lo"}]
    }
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=payload) as mock:
        r = client.post("/mcp", json=_ask("hi", model="my-model"))
    result = r.json()["result"]
    assert result == {"content": [{"type": "text", "text": "hello"}], "isError": False}
    body = mock.call_args.args[1]
    assert body["model"] == "my-model"
    assert body["stream"] is False
    assert body["messages"] == [{"role": "user", "content": "hi"}]


def test_ask_defaults_to_configured_model(client):
    with patch(
        PATCH_TARGET, new_callable=AsyncMock, return_value={"content": []}
    ) as mock:
        client.post("/mcp", json=_ask("hi"))
    assert mock.call_args.args[1]["model"] == Settings().model


def test_ask_handles_json_response_and_errors(client):
    ok = JSONResponse({"content": [{"type": "text", "text": "fine"}]})
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=ok):
        r = client.post("/mcp", json=_ask("hi"))
    assert r.json()["result"]["content"][0]["text"] == "fine"

    bad = JSONResponse({"error": {"message": "boom"}}, status_code=500)
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=bad):
        r = client.post("/mcp", json=_ask("hi"))
    assert r.json()["result"] == {
        "content": [{"type": "text", "text": "boom"}],
        "isError": True,
    }

    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=object()):
        r = client.post("/mcp", json=_ask("hi"))
    assert r.json()["result"]["isError"] is True


@pytest.mark.parametrize("prompt", ["", "   ", None, 5])
def test_ask_rejects_invalid_prompt(client, prompt):
    with patch(PATCH_TARGET, new_callable=AsyncMock) as mock:
        r = client.post("/mcp", json=_ask(prompt))
    assert r.json()["result"]["isError"] is True
    mock.assert_not_called()


def test_unknown_tool(client):
    r = client.post("/mcp", json=_rpc(1, "tools/call", {"name": "x"}))
    assert r.json()["error"]["code"] == -32602


def test_batch(client):
    batch = [
        _rpc(1, "ping"),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _rpc(2, "tools/list"),
    ]
    r = client.post("/mcp", json=batch)
    assert [m["id"] for m in r.json()] == [1, 2]
    r = client.post("/mcp", json=[{"jsonrpc": "2.0", "method": "notifications/x"}])
    assert r.status_code == 202


def test_auth_enforced(app, client):
    settings = Settings(proxy_auth_enabled=True, proxy_auth_token="s3cr3t")
    app.dependency_overrides[get_settings] = lambda: settings
    assert client.post("/mcp", json=_rpc(1, "ping")).status_code == 401
    r = client.post(
        "/mcp", json=_rpc(1, "ping"), headers={"Authorization": "Bearer wrong"}
    )
    assert r.status_code == 401
    r = client.post(
        "/mcp", json=_rpc(1, "ping"), headers={"Authorization": "Bearer s3cr3t"}
    )
    assert r.status_code == 200
    app.dependency_overrides.clear()
