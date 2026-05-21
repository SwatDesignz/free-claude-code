"""Contracts for the local AI app foundation assets."""

from pathlib import Path

from api.local_admin import build_local_admin_html
from config.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_local_admin_shell_advertises_private_cpu_first_gateway() -> None:
    settings = Settings()
    settings.model = "ollama/llama3.2"

    html = build_local_admin_html(settings)

    assert "Private Local AI Gateway" in html
    assert "CPU-only default" in html
    assert "OpenAI" in html
    assert "Anthropic" in html
    assert "ElevenLabs" in html
    assert "Local data" in html
    assert "ollama" in html


def test_local_ai_blueprint_covers_required_product_surfaces() -> None:
    blueprint = (REPO_ROOT / "docs" / "local_ai_app.md").read_text()

    for required in (
        "CPU-only by default",
        "Optional GPU acceleration",
        "Private by default",
        "OpenAI",
        "Anthropic",
        "ElevenLabs",
        "Hugging Face GGUF",
        "Ollama",
        "roles",
        "quotas",
        "usage",
    ):
        assert required in blueprint


def test_local_ai_docker_compose_uses_cpu_default_and_local_volumes() -> None:
    compose = (REPO_ROOT / "deploy" / "local-ai" / "docker-compose.cpu.yml").read_text()

    assert "ollama/ollama:latest" in compose
    assert "MODEL: ${MODEL:-ollama/llama3.2}" in compose
    assert "ANTHROPIC_AUTH_TOKEN" in compose
    assert "local_ai_data" in compose
    assert "ollama_models" in compose


def test_local_ai_dockerfile_pins_uv_and_runs_gateway() -> None:
    dockerfile = (REPO_ROOT / "deploy" / "local-ai" / "Dockerfile").read_text()

    assert "FROM python:3.14-slim" in dockerfile
    assert "ghcr.io/astral-sh/uv:0.10.4" in dockerfile
    assert 'CMD ["uv", "run", "free-claude-code"]' in dockerfile
