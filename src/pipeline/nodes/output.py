"""
Stage 5 — Output Node
Sprint: S3

Assembles the final ExtractedDocument-shaped dict from pipeline state.
Calculates processing_duration_ms and builds final_output.

On pipeline_error: final_output = None (but processing_duration_ms is still set).
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def output_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: assemble final output payload.

    Input state keys:  all upstream fields + start_time_ms
    Output state keys: final_output, processing_duration_ms
    """
    start_time_ms = state.get("start_time_ms", 0)
    now_ms = int(time.time() * 1000)
    duration_ms = max(0, now_ms - start_time_ms) if start_time_ms else 0

    if state.get("pipeline_error"):
        logger.warning("Pipeline failed: %s", state["pipeline_error"])
        return {"final_output": None, "processing_duration_ms": duration_ms}

    final_output: dict[str, Any] = {
        "document_id": state.get("document_id", ""),
        "source_filename": state.get("source_filename", ""),
        "document_category": state.get("document_category", "unclassified"),
        "classification_method": state.get("classification_method", "unclassified"),
        "classification_confidence": state.get("classification_confidence", 0.0),
        "matched_keywords": state.get("matched_keywords", []),
        "llm_escalation_reason": state.get("llm_escalation_reason"),
        "llm_unavailable": state.get("llm_unavailable", False),
        "extracted_fields": state.get("extracted_fields", {}),
        "validation_status": state.get("validation_status", "valid"),
        "validation_errors": state.get("validation_errors", []),
        "processing_duration_ms": duration_ms,
    }

    logger.info(
        "Pipeline complete: category='%s' method='%s' confidence=%.4f duration=%dms",
        final_output["document_category"],
        final_output["classification_method"],
        final_output["classification_confidence"],
        duration_ms,
    )

    return {"final_output": final_output, "processing_duration_ms": duration_ms}
