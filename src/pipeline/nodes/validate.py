"""
Stage 3 — Validate Node
Sprint: S4 (full implementation)

Validates extracted_fields against mandatory_fields defined in the category
YAML config. Uses the KeywordConfigLoader to look up mandatory_fields per
category at runtime (hot-reload safe).

Validation outcomes:
  valid   — all mandatory_fields are present and non-empty
  partial — one or more mandatory_fields are absent or empty
  invalid — pipeline_error propagated from upstream, or exception during validation

Invalid outputs are NEVER silently passed downstream (FR4).
"""

from __future__ import annotations

import logging
from typing import Any

from src.config.loader import get_loader

logger = logging.getLogger(__name__)


def validate_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: validate extracted fields against category mandatory_fields.

    Input state keys:  document_category, extracted_fields, pipeline_error
    Output state keys: validation_status, validation_errors
    """
    # Propagate upstream errors immediately
    if state.get("pipeline_error"):
        return {
            "validation_status": "invalid",
            "validation_errors": [state["pipeline_error"]],
        }

    category = state.get("document_category", "unclassified")
    extracted_fields = state.get("extracted_fields", {})

    # Unclassified documents have no schema to validate against
    if category == "unclassified":
        logger.debug("validate_node: category=unclassified — skipping field validation")
        return {"validation_status": "valid", "validation_errors": []}

    try:
        loader = get_loader()
        categories = loader.get_categories()
        category_cfg = categories.get(category)

        if category_cfg is None:
            # Category slug not found in YAML config — treat as valid (no rules to check)
            logger.warning(
                "validate_node: no config found for category '%s' — skipping", category
            )
            return {"validation_status": "valid", "validation_errors": []}

        mandatory_fields = category_cfg.mandatory_fields
        if not mandatory_fields:
            logger.debug(
                "validate_node: category='%s' has no mandatory_fields — valid", category
            )
            return {"validation_status": "valid", "validation_errors": []}

        # Check each mandatory field is present and non-empty
        missing: list[str] = []
        for field in mandatory_fields:
            value = extracted_fields.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)

        if missing:
            errors = [f"Missing mandatory field: '{f}'" for f in missing]
            logger.info(
                "validate_node: category='%s' partial — missing fields: %s",
                category,
                missing,
            )
            return {"validation_status": "partial", "validation_errors": errors}

        logger.debug(
            "validate_node: category='%s' valid — all %d mandatory fields present",
            category,
            len(mandatory_fields),
        )
        return {"validation_status": "valid", "validation_errors": []}

    except Exception as exc:  # noqa: BLE001
        logger.error("validate_node: unexpected error: %s", exc)
        return {
            "validation_status": "invalid",
            "validation_errors": [f"Validation error: {exc}"],
        }
