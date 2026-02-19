"""
LLM Fallback Node Tests — Anthropic Claude API
Pre-Sprint 6 (implemented early per client request)

All tests mock the Anthropic API — no real API calls are made.

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_llm_fallback.py -v
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.nodes.llm import (
    _build_prompt,
    _parse_llm_response,
    llm_fallback_node,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_CATEGORIES = ["bank_statement", "contract", "invoice", "purchase_order", "receipt", "report", "resume"]

SAMPLE_STATE = {
    "parsed_markdown": "Invoice Number: INV-001\nTotal Amount: $1,250.00\nDue Date: 2024-03-15",
    "llm_escalation_reason": "Best match 'invoice' scored 0.4500 but threshold is 0.60",
    "document_category": "unclassified",
    "classification_confidence": 0.45,
}


def _make_mock_response(text: str) -> MagicMock:
    """Create a mock Anthropic message response with given text content."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


# ---------------------------------------------------------------------------
# _parse_llm_response tests
# ---------------------------------------------------------------------------


class TestParseLlmResponse:
    """Tests for response parsing and validation."""

    def test_valid_response(self):
        text = '{"category": "invoice", "confidence": 0.85}'
        result = _parse_llm_response(text, VALID_CATEGORIES)
        assert result == {"category": "invoice", "confidence": 0.85}

    def test_invalid_json(self):
        result = _parse_llm_response("not json at all", VALID_CATEGORIES)
        assert result is None

    def test_unknown_category(self):
        text = '{"category": "unknown_type", "confidence": 0.9}'
        result = _parse_llm_response(text, VALID_CATEGORIES)
        assert result is None

    def test_confidence_clamped_above_1(self):
        text = '{"category": "invoice", "confidence": 1.5}'
        result = _parse_llm_response(text, VALID_CATEGORIES)
        assert result["confidence"] == 1.0

    def test_confidence_clamped_below_0(self):
        text = '{"category": "invoice", "confidence": -0.5}'
        result = _parse_llm_response(text, VALID_CATEGORIES)
        assert result["confidence"] == 0.0

    def test_confidence_rounded(self):
        text = '{"category": "invoice", "confidence": 0.85678}'
        result = _parse_llm_response(text, VALID_CATEGORIES)
        assert result["confidence"] == 0.8568

    def test_invalid_confidence_type(self):
        text = '{"category": "invoice", "confidence": "high"}'
        result = _parse_llm_response(text, VALID_CATEGORIES)
        assert result is None

    def test_whitespace_stripped(self):
        text = '  {"category": "contract", "confidence": 0.72}  \n'
        result = _parse_llm_response(text, VALID_CATEGORIES)
        assert result == {"category": "contract", "confidence": 0.72}


# ---------------------------------------------------------------------------
# _build_prompt tests
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """Tests for prompt construction."""

    def test_prompt_includes_categories(self):
        prompt = _build_prompt(SAMPLE_STATE, VALID_CATEGORIES)
        for cat in VALID_CATEGORIES:
            assert cat in prompt

    def test_prompt_includes_escalation_reason(self):
        prompt = _build_prompt(SAMPLE_STATE, VALID_CATEGORIES)
        assert "scored 0.4500" in prompt

    def test_prompt_includes_document_text(self):
        prompt = _build_prompt(SAMPLE_STATE, VALID_CATEGORIES)
        assert "INV-001" in prompt

    def test_prompt_truncates_long_text(self):
        long_state = {**SAMPLE_STATE, "parsed_markdown": "x" * 10000}
        prompt = _build_prompt(long_state, VALID_CATEGORIES)
        # The document text portion should be truncated to 4000 chars
        assert len(prompt) < 10000


# ---------------------------------------------------------------------------
# llm_fallback_node tests
# ---------------------------------------------------------------------------


class TestLlmFallbackNode:
    """Tests for the full llm_fallback_node function."""

    def test_no_api_key_returns_unavailable(self, monkeypatch):
        """Missing ANTHROPIC_API_KEY → llm_unavailable=True."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = llm_fallback_node(SAMPLE_STATE)
        assert result["llm_unavailable"] is True

    def test_empty_api_key_returns_unavailable(self, monkeypatch):
        """Empty ANTHROPIC_API_KEY → llm_unavailable=True."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        result = llm_fallback_node(SAMPLE_STATE)
        assert result["llm_unavailable"] is True

    @patch("src.pipeline.nodes.llm.load_categories")
    def test_no_categories_returns_unavailable(self, mock_load, monkeypatch):
        """If categories can't be loaded → llm_unavailable=True."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        mock_load.side_effect = RuntimeError("config error")
        result = llm_fallback_node(SAMPLE_STATE)
        assert result["llm_unavailable"] is True

    @patch("src.pipeline.nodes.llm.anthropic.Anthropic")
    @patch("src.pipeline.nodes.llm.load_categories")
    def test_successful_classification(self, mock_load, mock_client_cls, monkeypatch):
        """Valid API response → sets category, method, confidence."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("LLM_MAX_RETRIES", "0")

        mock_load.return_value = {
            "invoice": MagicMock(), "contract": MagicMock(), "resume": MagicMock(),
        }

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(
            '{"category": "invoice", "confidence": 0.88}'
        )

        result = llm_fallback_node(SAMPLE_STATE)

        assert result["document_category"] == "invoice"
        assert result["classification_method"] == "llm_fallback"
        assert result["classification_confidence"] == 0.88
        assert result["llm_unavailable"] is False

    @patch("src.pipeline.nodes.llm.anthropic.Anthropic")
    @patch("src.pipeline.nodes.llm.load_categories")
    def test_retry_on_api_error(self, mock_load, mock_client_cls, monkeypatch):
        """First call fails, second succeeds → retries work."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("LLM_MAX_RETRIES", "1")
        monkeypatch.setenv("LLM_RETRY_BASE_DELAY", "0")  # no sleep in tests

        mock_load.return_value = {"invoice": MagicMock(), "contract": MagicMock()}

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        import anthropic as anthropic_mod
        mock_client.messages.create.side_effect = [
            anthropic_mod.APIConnectionError(request=MagicMock()),
            _make_mock_response('{"category": "invoice", "confidence": 0.75}'),
        ]

        result = llm_fallback_node(SAMPLE_STATE)

        assert result["document_category"] == "invoice"
        assert result["classification_method"] == "llm_fallback"
        assert mock_client.messages.create.call_count == 2

    @patch("src.pipeline.nodes.llm.anthropic.Anthropic")
    @patch("src.pipeline.nodes.llm.load_categories")
    def test_all_retries_exhausted(self, mock_load, mock_client_cls, monkeypatch):
        """All retries fail → llm_unavailable=True."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("LLM_MAX_RETRIES", "1")
        monkeypatch.setenv("LLM_RETRY_BASE_DELAY", "0")

        mock_load.return_value = {"invoice": MagicMock()}

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        import anthropic as anthropic_mod
        mock_client.messages.create.side_effect = anthropic_mod.APIConnectionError(
            request=MagicMock()
        )

        result = llm_fallback_node(SAMPLE_STATE)

        assert result["llm_unavailable"] is True
        assert mock_client.messages.create.call_count == 2  # initial + 1 retry

    @patch("src.pipeline.nodes.llm.anthropic.Anthropic")
    @patch("src.pipeline.nodes.llm.load_categories")
    def test_invalid_json_response(self, mock_load, mock_client_cls, monkeypatch):
        """LLM returns non-JSON → llm_unavailable after retries."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("LLM_MAX_RETRIES", "0")

        mock_load.return_value = {"invoice": MagicMock()}

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(
            "I think this is an invoice document."
        )

        result = llm_fallback_node(SAMPLE_STATE)
        assert result["llm_unavailable"] is True

    @patch("src.pipeline.nodes.llm.anthropic.Anthropic")
    @patch("src.pipeline.nodes.llm.load_categories")
    def test_unknown_category_in_response(self, mock_load, mock_client_cls, monkeypatch):
        """LLM returns category not in valid list → llm_unavailable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("LLM_MAX_RETRIES", "0")

        mock_load.return_value = {"invoice": MagicMock(), "contract": MagicMock()}

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(
            '{"category": "memo", "confidence": 0.90}'
        )

        result = llm_fallback_node(SAMPLE_STATE)
        assert result["llm_unavailable"] is True

    @patch("src.pipeline.nodes.llm.anthropic.Anthropic")
    @patch("src.pipeline.nodes.llm.load_categories")
    def test_model_from_env(self, mock_load, mock_client_cls, monkeypatch):
        """ANTHROPIC_MODEL env var is passed to the API call."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        monkeypatch.setenv("LLM_MAX_RETRIES", "0")

        mock_load.return_value = {"invoice": MagicMock()}

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(
            '{"category": "invoice", "confidence": 0.80}'
        )

        llm_fallback_node(SAMPLE_STATE)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
