# Local AI App Blueprint

This project can grow into a private, local-first replacement for cloud AI services by
keeping the existing provider proxy as the API gateway and adding local model runtime,
admin, auth, quota, and media capabilities around it.

## Product goals

- **CPU-only by default**: run on a laptop, mini PC, or cheap server without a GPU.
- **Optional GPU acceleration**: enable CUDA/Metal/ROCm only when the host supports it.
- **Private by default**: model files, prompts, usage records, users, keys, and logs stay
  on the local machine unless an administrator configures a remote provider.
- **Drop-in APIs**: expose OpenAI-style chat, Anthropic Messages, and ElevenLabs-style
  speech endpoints so existing clients need minimal configuration changes.
- **Model sources**: support a built-in gallery, Hugging Face GGUF downloads, Ollama-style
  model names, direct URLs, and declarative config files.
- **Admin controls**: API keys, users, roles, quotas, model lifecycle, and usage reports.

## Current foundation in this repository

- FastAPI app and Anthropic-compatible routes under `api/`.
- Provider adapters for hosted, local, and OpenAI-compatible transports under `providers/`.
- Local-friendly providers for LM Studio, llama.cpp, and Ollama.
- Telegram and Discord gateway abstractions under `messaging/`.
- Repository MCP discovery through `.mcp.json`.

## Target architecture

```text
Browser UI / Existing SDKs / Messaging gateways
        ↓
FastAPI gateway
        ├── OpenAI-compatible API surface
        ├── Anthropic-compatible API surface
        ├── ElevenLabs-compatible speech API surface
        ├── Admin UI and API-key auth
        ├── Role, quota, and usage services
        └── Model registry and runtime manager
                ├── llama.cpp / GGUF CPU runtime
                ├── Ollama-compatible runtime
                ├── Whisper-compatible STT runtime
                ├── Piper/Coqui/other TTS runtime
                └── optional GPU backends
```

## API compatibility targets

| Surface | Minimum endpoints | Notes |
| --- | --- | --- |
| OpenAI | `/v1/models`, `/v1/chat/completions`, `/v1/embeddings`, `/v1/audio/transcriptions`, `/v1/images/generations` | Chat completions should remain the broadest compatibility target for existing apps. |
| Anthropic | `/v1/messages`, `/v1/messages/count_tokens` | Existing routes already provide the core Messages shape. |
| ElevenLabs | `/v1/text-to-speech/{voice_id}`, `/v1/speech-to-text` | Implement as compatibility wrappers over local TTS/STT engines. |
| Admin | `/admin/local`, `/admin/api/*` | Protect with API-key auth and eventually role-aware sessions. |

## Model registry

Each model entry should be represented as local metadata:

```yaml
id: qwen2.5-0.5b-instruct-q4
source:
  type: huggingface_gguf
  repo: Qwen/Qwen2.5-0.5B-Instruct-GGUF
  file: qwen2.5-0.5b-instruct-q4_k_m.gguf
runtime:
  type: llamacpp
  device: cpu
capabilities: [chat, tools]
limits:
  context_tokens: 32768
```

Supported source types should include:

- `gallery`: curated local metadata shipped with the app.
- `huggingface_gguf`: GGUF files from Hugging Face Hub.
- `ollama`: Ollama-style model names and Modelfile-compatible creation.
- `url`: direct model artifact URLs with checksum verification.
- `config`: administrator-provided YAML/JSON model definitions.

## Security and tenancy

- Store API keys as hashed secrets in local SQLite.
- Default roles: `admin`, `developer`, `user`, `read_only`.
- Quotas should support requests/day, tokens/day, audio minutes/day, and image jobs/day.
- Keep an append-only local usage table for auditability.
- Never expose model-management endpoints without auth.
- Make any remote-provider route visibly labeled as non-local in the UI.

## Phased implementation

1. **MVP shell**: admin UI route, CPU Docker profile, local-data messaging, and docs.
2. **Auth and quotas**: local users, API keys, roles, quota checks, usage records.
3. **Model registry**: gallery metadata, local import from Hugging Face/Ollama/URL/config.
4. **OpenAI compatibility**: generic OpenAI-compatible provider and chat completions route.
5. **Media APIs**: local STT/TTS wrappers and ElevenLabs-compatible routes.
6. **Agents**: tool registry, MCP opt-in, workspace policy, and usage attribution.
7. **Image/video/music**: capability-gated backends as CPU/GPU support allows.
