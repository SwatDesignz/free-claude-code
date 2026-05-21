"""Token encoding helpers with an offline-safe fallback."""

from typing import Protocol

import tiktoken
from loguru import logger


class TokenEncoder(Protocol):
    """Minimal encoder interface used by token estimation code."""

    def encode(self, text: str) -> list[int]:
        """Encode text into token identifiers."""


class ApproximateTokenEncoder:
    """Character-count based fallback for environments without tiktoken cache access."""

    def encode(self, text: str) -> list[int]:
        """Approximate token IDs without requiring network-backed encoding data."""
        if not text:
            return []
        return [0] * max(1, len(text) // 4)


def get_cl100k_encoder() -> TokenEncoder:
    """Return the cl100k encoder, or an approximate fallback if it cannot load."""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception as exc:
        logger.warning(
            "Failed to load tiktoken cl100k_base encoding; using approximate "
            "token estimation fallback: {}",
            exc,
        )
        return ApproximateTokenEncoder()
