"""
Stage 3 — Validate Node
Sprint: S4

Validates extracted_fields against the Pydantic schema for the classified
document category. Checks mandatory fields are present.

On failure: sets validation_status='invalid' and populates validation_errors.
On partial: mandatory fields missing but no schema error → validation_status='partial'.
Invalid outputs are NEVER silently passed downstream (FR4).

Implemented in Sprint 4.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: validate extracted fields against category schema.

    Input state keys:  document_category, extracted_fields
    Output state keys: validation_status, validation_errors
    """
    # TODO (Sprint 4): implement Pydantic schema validation per category
    raise NotImplementedError("validate_node — implement in Sprint 4")
