FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY api ./api
COPY cli ./cli
COPY config ./config
COPY core ./core
COPY messaging ./messaging
COPY providers ./providers
COPY server.py ./.env.example ./

RUN uv sync --frozen --no-dev

EXPOSE 8082
CMD ["uv", "run", "free-claude-code"]
