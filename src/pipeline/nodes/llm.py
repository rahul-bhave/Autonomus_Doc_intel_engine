"""
Stage 2b — LLM Fallback Node
Sprint: S6

Invoked ONLY when keyword engine confidence < threshold.
Primary target: Ollama (llama3.1 or granite3-dense:8b) — local, no API cost.
Secondary target: IBM Watsonx (Granite-3.0-8b-Instruct) — cloud, API key required.

Retry policy: up to 2 retries with exponential backoff before marking llm_unavailable.
All LLM invocations are logged with the escalation reason (NFR-O1, FR3).

Implemented in Sprint 6.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def llm_fallback_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: semantic inference when keyword engine is insufficient.

    Input state keys:  parsed_markdown, llm_escalation_reason
    Output state keys: document_category, classification_method ('llm_fallback'),
                       classification_confidence, extracted_fields,
                       llm_unavailable
    """
    # TODO (Sprint 6): implement Ollama → Watsonx fallback chain
    raise NotImplementedError("llm_fallback_node — implement in Sprint 6")
