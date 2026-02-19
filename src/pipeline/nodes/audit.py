"""
Stage 4 — Audit Node
Sprint: S4 (full implementation), S3 (pass-through stub)

Writes an append-only AuditEntry to the JSONL audit log file.
Entries are immutable post-write (file is opened in append mode only).
Every processed document produces exactly one audit entry, including failures (FR5).

Log location: configured via AUDIT_LOG_PATH environment variable.
Default: logs/audit.jsonl

Currently a pass-through stub — generates audit_id but does not write to disk.
Full implementation in Sprint 4.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def audit_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: write append-only audit log entry.

    Input state keys:  all classification + validation fields
    Output state keys: audit_id, audit_written
    """
    # Every document gets an audit entry — even failures
    audit_id = str(uuid4())

    # TODO (Sprint 4): implement JSONL append writer using AuditEntry schema
    logger.debug("audit_node: pass-through stub — audit_id=%s (not written to disk)", audit_id)
    return {"audit_id": audit_id, "audit_written": False}
