"""
Stage 3 — Validate Node
Sprint: S4 (full implementation), S3 (pass-through stub)

Validates extracted_fields against the Pydantic schema for the classified
document category. Checks mandatory fields are present.

On failure: sets validation_status='invalid' and populates validation_errors.
On partial: mandatory fields missing but no schema error → validation_status='partial'.
Invalid outputs are NEVER silently passed downstream (FR4).

Currently a pass-through stub — always returns validation_status='valid'.
Full implementation in Sprint 4.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: validate extracted fields against category schema.

    Input state keys:  document_category, extracted_fields, pipeline_error
    Output state keys: validation_status, validation_errors
    """
    if state.get("pipeline_error"):
        return {"validation_status": "invalid", "validation_errors": [state["pipeline_error"]]}

    # TODO (Sprint 4): implement Pydantic schema validation per category
    logger.debug("validate_node: pass-through stub — returning 'valid'")
    return {"validation_status": "valid", "validation_errors": []}
