"""
Stage 4 — Audit Node
Sprint: S4 (full implementation)

Writes an append-only AuditEntry to the JSONL audit log file.
Entries are immutable post-write (file is opened in append mode only).
Every processed document produces exactly one audit entry, including failures (FR5).

Log location: configured via AUDIT_LOG_PATH environment variable.
Default: logs/audit.jsonl

Graceful degradation: if the write fails (e.g. disk full, permissions error),
audit_written is set to False and the error is logged — the pipeline continues.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.models.schemas import AuditEntry

logger = logging.getLogger(__name__)

_DEFAULT_AUDIT_LOG = "logs/audit.jsonl"

# Mapping from validation_status (pipeline state) → validation_outcome (AuditEntry)
_OUTCOME_MAP = {"valid": "passed", "invalid": "failed", "partial": "partial"}


def audit_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: write append-only audit log entry.

    Input state keys:  document_id, source_filename, classification_method,
                       document_category, classification_confidence,
                       llm_escalation_reason, llm_unavailable,
                       validation_status, validation_errors,
                       processing_duration_ms
    Output state keys: audit_id, audit_written
    """
    audit_id = str(uuid4())
    log_path = Path(os.environ.get("AUDIT_LOG_PATH", _DEFAULT_AUDIT_LOG))

    validation_status = state.get("validation_status", "valid")
    validation_outcome = _OUTCOME_MAP.get(validation_status, "passed")

    entry = AuditEntry(
        audit_id=audit_id,
        document_id=state.get("document_id", str(uuid4())),
        source_filename=state.get("source_filename", "unknown"),
        extraction_method=state.get("classification_method", "unclassified"),
        llm_escalation_reason=state.get("llm_escalation_reason"),
        llm_unavailable=state.get("llm_unavailable", False),
        classification_result=state.get("document_category", "unclassified"),
        confidence_score=state.get("classification_confidence", 0.0),
        validation_outcome=validation_outcome,
        validation_errors=state.get("validation_errors", []),
        processing_duration_ms=state.get("processing_duration_ms", 0),
    )

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
        logger.debug(
            "audit_node: wrote entry audit_id=%s doc='%s' outcome=%s",
            audit_id,
            entry.source_filename,
            validation_outcome,
        )
        return {"audit_id": audit_id, "audit_written": True}

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "audit_node: failed to write audit log '%s': %s", log_path, exc
        )
        return {"audit_id": audit_id, "audit_written": False}
