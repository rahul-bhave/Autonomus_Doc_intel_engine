"""
Stage 2 — Classify Node
Sprint: S2 (stub), S3 (implemented)

Runs the Python keyword engine against parsed_markdown.
If confidence >= threshold  → deterministic classification.
If confidence <  threshold  → sets escalation_reason, defers to llm.py.
"""

from __future__ import annotations

import logging
from typing import Any

from src.classifiers.engine import KeywordClassifier
from src.config.loader import get_loader

logger = logging.getLogger(__name__)


def classify_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: Markdown → classification result + extracted fields.

    Input state keys:  parsed_markdown, pipeline_error
    Output state keys: document_category, classification_method,
                       classification_confidence, matched_keywords,
                       extracted_fields, llm_escalation_reason
    """
    # Skip if upstream error
    if state.get("pipeline_error"):
        return {}

    parsed_markdown = state.get("parsed_markdown", "")
    if not parsed_markdown:
        logger.error("classify_node: no parsed_markdown in state")
        return {"pipeline_error": "No parsed Markdown available for classification"}

    classifier = KeywordClassifier()
    result = classifier.classify(parsed_markdown)

    output: dict[str, Any] = {
        "document_category": result.category,
        "classification_method": result.method,
        "classification_confidence": result.confidence,
        "matched_keywords": result.matched_keywords,
    }

    if result.method == "deterministic":
        # Extract fields using regex patterns for the winning category
        loader = get_loader()
        categories = loader.get_categories()
        category_cfg = categories.get(result.category)
        if category_cfg:
            output["extracted_fields"] = classifier.extract_fields(
                parsed_markdown, category_cfg
            )
        else:
            output["extracted_fields"] = {}
        logger.info(
            "Deterministic classification: '%s' (confidence=%.4f, %d keywords)",
            result.category, result.confidence, len(result.matched_keywords),
        )
    else:
        # Below threshold → escalate to LLM
        output["llm_escalation_reason"] = result.escalation_reason
        output["extracted_fields"] = {}
        logger.info(
            "Classification below threshold — escalating to LLM: %s",
            result.escalation_reason,
        )

    return output
