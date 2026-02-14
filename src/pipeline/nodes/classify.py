"""
Stage 2 — Classify Node
Sprint: S2

Runs the Python keyword engine against parsed_markdown.
If confidence >= threshold  → deterministic classification.
If confidence <  threshold  → sets escalation_reason, defers to llm.py.

Implemented in Sprint 2.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def classify_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: Markdown → classification result + extracted fields.

    Input state keys:  parsed_markdown
    Output state keys: document_category, classification_method,
                       classification_confidence, matched_keywords,
                       extracted_fields, llm_escalation_reason
    """
    # TODO (Sprint 2): wire in KeywordClassifier
    raise NotImplementedError("classify_node — implement in Sprint 2")
