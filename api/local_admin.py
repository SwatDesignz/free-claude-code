"""Local AI admin web shell."""

from html import escape

from config.settings import Settings


def _card(title: str, body: str) -> str:
    return (
        f'<section class="card"><h2>{escape(title)}</h2><p>{escape(body)}</p></section>'
    )


def build_local_admin_html(settings: Settings) -> str:
    """Render a lightweight local-first admin shell."""
    provider = escape(settings.provider_type)
    model = escape(settings.model)
    cards = "".join(
        [
            _card(
                "Chat",
                "Use the OpenAI-compatible or Anthropic-compatible APIs from any local chat UI.",
            ),
            _card(
                "Models",
                "Load CPU-friendly models from the built-in gallery, Hugging Face GGUF files, Ollama sources, URLs, or config files.",
            ),
            _card(
                "Agents",
                "Experiment with tool-using agents while keeping execution policy and workspace access explicit.",
            ),
            _card(
                "Usage",
                "Track requests, token estimates, quotas, and per-user activity in local storage.",
            ),
            _card(
                "Voice and media",
                "Expose ElevenLabs-style speech APIs and leave room for image, video, and music backends as they become available.",
            ),
            _card(
                "Private by default",
                "Data, logs, model files, usage records, and admin settings stay on this machine unless you configure a remote provider.",
            ),
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local AI Admin</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; background: #0f172a; color: #e5e7eb; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 48px 24px; }}
    .hero {{ border: 1px solid #334155; border-radius: 24px; padding: 32px; background: linear-gradient(135deg, #111827, #1e293b); }}
    h1 {{ margin: 0 0 12px; font-size: clamp(2rem, 5vw, 4rem); }}
    .subtitle {{ color: #cbd5e1; max-width: 760px; line-height: 1.6; }}
    .pillrow {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px; }}
    .pill {{ border: 1px solid #475569; border-radius: 999px; padding: 8px 12px; color: #bfdbfe; background: #0f172a; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 24px; }}
    .card {{ border: 1px solid #334155; border-radius: 18px; padding: 20px; background: #111827; }}
    .card h2 {{ margin-top: 0; color: #93c5fd; }}
    .card p {{ color: #cbd5e1; line-height: 1.5; }}
    code {{ color: #fde68a; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Private Local AI Gateway</h1>
      <p class="subtitle">A CPU-first control surface for running local and self-hosted AI backends with OpenAI, Anthropic, and ElevenLabs-style compatibility. This shell is intentionally local-first: keep model files, user records, and usage data on your own computer or server.</p>
      <div class="pillrow">
        <span class="pill">Provider: <code>{provider}</code></span>
        <span class="pill">Model route: <code>{model}</code></span>
        <span class="pill">CPU-only default</span>
        <span class="pill">API-key auth</span>
        <span class="pill">Local data</span>
      </div>
    </section>
    <section class="grid">{cards}</section>
  </main>
</body>
</html>
"""
