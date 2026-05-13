"""Tests for offline-safe token encoding helpers."""

from unittest.mock import patch

from core.anthropic.tokenizer import ApproximateTokenEncoder, get_cl100k_encoder


def test_approximate_token_encoder_counts_empty_text_as_zero() -> None:
    encoder = ApproximateTokenEncoder()

    assert len(encoder.encode("")) == 0


def test_approximate_token_encoder_counts_non_empty_text_at_least_one() -> None:
    encoder = ApproximateTokenEncoder()

    assert len(encoder.encode("abc")) == 1
    assert len(encoder.encode("a" * 100)) == 25


def test_get_cl100k_encoder_falls_back_when_tiktoken_encoding_cannot_load() -> None:
    with patch(
        "core.anthropic.tokenizer.tiktoken.get_encoding",
        side_effect=RuntimeError("offline"),
    ):
        encoder = get_cl100k_encoder()

    assert isinstance(encoder, ApproximateTokenEncoder)
    assert len(encoder.encode("a" * 100)) == 25
