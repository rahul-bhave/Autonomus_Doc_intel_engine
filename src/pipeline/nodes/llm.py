"""
Stage 2b — LLM Fallback Node (Anthropic Claude API)
Sprint: S6 (implemented early per client request)

Invoked ONLY when keyword engine confidence < threshold.
Uses the Anthropic Claude API (default: claude-haiku-4-5-20251001).

Retry policy: up to LLM_MAX_RETRIES (default 2) with exponential backoff.
Graceful degradation: if API key missing or all retries fail, sets llm_unavailable=True.
All LLM invocations are logged with the escalation reason (NFR-O1, FR3).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import anthropic

from src.config.loader import load_categories

logger = logging.getLogger(__name__)

# Defaults (overridable via .env)
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_RETRY_BASE_DELAY = 1.0
_MAX_DOC_CHARS = 4000

# Prompt template
_SYSTEM_PROMPT = (
    "You are a document classifier for an enterprise document intelligence system. "
    "You will be given document text and must classify it into exactly one category. "
    "Respond with valid JSON only — no markdown, no explanation."
)

_USER_PROMPT_TEMPLATE = """\
Classify this document into exactly one of these categories: {categories}

Respond with JSON only: {{"category": "<category_slug>", "confidence": <0.0-1.0>}}

Escalation context: {escalation_reason}
Keyword engine's best guess: {best_guess} (confidence: {best_confidence:.4f})

Document text:
{document_text}"""


def _get_valid_categories() -> list[str]:
    """Load all enabled category slugs from the keyword config."""
    try:
        categories = load_categories()
        return sorted(categories.keys())
    except Exception as exc:
        logger.warning("Could not load categories for LLM prompt: %s", exc)
        return []


def _build_prompt(state: dict[str, Any], valid_categories: list[str]) -> str:
    """Build the user prompt from pipeline state."""
    return _USER_PROMPT_TEMPLATE.format(
        categories=", ".join(valid_categories),
        escalation_reason=state.get("llm_escalation_reason", "Unknown"),
        best_guess=state.get("document_category", "unclassified"),
        best_confidence=state.get("classification_confidence", 0.0),
        document_text=state.get("parsed_markdown", "")[:_MAX_DOC_CHARS],
    )


def _parse_llm_response(text: str, valid_categories: list[str]) -> dict[str, Any] | None:
    """
    Parse the LLM's JSON response and validate the category.
    Returns {"category": str, "confidence": float} or None on failure.
    """
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON: %s", text[:200])
        return None

    category = data.get("category")
    confidence = data.get("confidence")

    if category not in valid_categories:
        logger.warning("LLM returned unknown category '%s' (valid: %s)", category, valid_categories)
        return None

    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        logger.warning("LLM returned invalid confidence: %s", confidence)
        return None

    return {"category": category, "confidence": round(confidence, 4)}


def llm_fallback_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: semantic inference when keyword engine is insufficient.

    Input state keys:  parsed_markdown, llm_escalation_reason,
                       document_category, classification_confidence
    Output state keys: document_category, classification_method ('llm_fallback'),
                       classification_confidence, llm_unavailable
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — LLM fallback unavailable")
        return {"llm_unavailable": True}

    model = os.environ.get("ANTHROPIC_MODEL", _DEFAULT_MODEL)
    max_retries = int(os.environ.get("LLM_MAX_RETRIES", _DEFAULT_MAX_RETRIES))
    base_delay = float(os.environ.get("LLM_RETRY_BASE_DELAY", _DEFAULT_RETRY_BASE_DELAY))

    valid_categories = _get_valid_categories()
    if not valid_categories:
        logger.warning("No valid categories loaded — LLM fallback unavailable")
        return {"llm_unavailable": True}

    user_prompt = _build_prompt(state, valid_categories)
    client = anthropic.Anthropic(api_key=api_key)

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=150,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            response_text = response.content[0].text
            parsed = _parse_llm_response(response_text, valid_categories)

            if parsed is not None:
                logger.info(
                    "LLM classified as '%s' (confidence=%.4f) on attempt %d",
                    parsed["category"], parsed["confidence"], attempt + 1,
                )
                return {
                    "document_category": parsed["category"],
                    "classification_method": "llm_fallback",
                    "classification_confidence": parsed["confidence"],
                    "llm_unavailable": False,
                }

            # Invalid response — treat as failure, retry
            logger.warning("LLM response could not be parsed (attempt %d)", attempt + 1)
            last_error = ValueError(f"Unparseable LLM response: {response_text[:200]}")

        except (
            anthropic.APIError,
            anthropic.APIConnectionError,
            anthropic.RateLimitError,
        ) as exc:
            last_error = exc
            logger.warning(
                "LLM API error on attempt %d/%d: %s",
                attempt + 1, max_retries + 1, exc,
            )

        # Exponential backoff before retry (skip on last attempt)
        if attempt < max_retries:
            delay = base_delay * (2 ** attempt)
            logger.debug("Retrying in %.1f seconds...", delay)
            time.sleep(delay)

    # All retries exhausted
    logger.error("LLM fallback failed after %d attempts: %s", max_retries + 1, last_error)
    return {"llm_unavailable": True}
