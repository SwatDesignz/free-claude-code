from fastapi import FastAPI
from fastapi.testclient import TestClient

from free_claude_code.api.mcp_routes import router


def _client():
    from free_claude_code.api.dependencies import get_services, require_proxy_auth

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_proxy_auth] = lambda: None
    app.dependency_overrides[get_services] = lambda: None
    return TestClient(app)


def test_initialize_and_list_tools():
    c = _client()
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert r.json()["result"]["serverInfo"]["name"] == "free-claude-code"
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert r.json()["result"]["tools"][0]["name"] == "ask"


def test_notification_accepted_and_unknown_method():
    c = _client()
    r = c.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert r.status_code == 202
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "nope"})
    assert r.json()["error"]["code"] == -32601
