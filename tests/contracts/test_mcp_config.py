"""Contract tests for repository MCP server configuration."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_puppeteer_mcp_server_is_configured() -> None:
    config = json.loads((REPO_ROOT / ".mcp.json").read_text())

    puppeteer = config["mcpServers"]["puppeteer"]

    assert puppeteer == {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
    }
