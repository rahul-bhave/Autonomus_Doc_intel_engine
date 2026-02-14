"""
Stage 4 — Audit Node
Sprint: S4

Writes an append-only AuditEntry to the JSONL audit log file.
Entries are immutable post-write (file is opened in append mode only).
Every processed document produces exactly one audit entry, including failures (FR5).

Log location: configured via AUDIT_LOG_PATH environment variable.
Default: logs/audit.jsonl

Implemented in Sprint 4.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def audit_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: write append-only audit log entry.

    Input state keys:  all classification + validation fields
    Output state keys: audit_id, audit_written
    """
    # TODO (Sprint 4): implement JSONL append writer using AuditEntry schema
    raise NotImplementedError("audit_node — implement in Sprint 4")
