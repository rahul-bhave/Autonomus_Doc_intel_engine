"""
Sprint 4 — audit_node Tests

Tests the full S4 implementation of audit_node:
  - Produces a valid AuditEntry with correct fields from pipeline state
  - Appends JSONL line to audit log file
  - Creates parent directory if missing
  - Sets audit_written=True on success, False on IO failure
  - Every call produces a unique audit_id
  - Handles missing / defaulted state fields gracefully

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_audit.py -v
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.pipeline.nodes.audit import audit_node
from src.models.schemas import AuditEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_STATE = {
    "document_id": "doc-abc-123",
    "source_filename": "invoice.pdf",
    "classification_method": "deterministic",
    "document_category": "invoice",
    "classification_confidence": 0.85,
    "llm_escalation_reason": None,
    "llm_unavailable": False,
    "validation_status": "valid",
    "validation_errors": [],
    "processing_duration_ms": 250,
}


# ---------------------------------------------------------------------------
# Return values
# ---------------------------------------------------------------------------


class TestReturnValues:
    """audit_node must return audit_id and audit_written keys."""

    def test_returns_audit_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
        result = audit_node(_FULL_STATE)
        assert "audit_id" in result
        assert isinstance(result["audit_id"], str)
        assert len(result["audit_id"]) > 0

    def test_returns_audit_written_true_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
        result = audit_node(_FULL_STATE)
        assert result["audit_written"] is True

    def test_each_call_produces_unique_audit_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
        r1 = audit_node(_FULL_STATE)
        r2 = audit_node(_FULL_STATE)
        assert r1["audit_id"] != r2["audit_id"]


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------


class TestFileWriting:
    """audit_node must write valid JSONL to the configured log file."""

    def test_creates_log_file(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        audit_node(_FULL_STATE)
        assert log_file.exists()

    def test_creates_parent_directory(self, tmp_path, monkeypatch):
        log_file = tmp_path / "nested" / "logs" / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        audit_node(_FULL_STATE)
        assert log_file.exists()

    def test_written_line_is_valid_json(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        audit_node(_FULL_STATE)
        line = log_file.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert isinstance(data, dict)

    def test_written_entry_fields_match_state(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        result = audit_node(_FULL_STATE)
        data = json.loads(log_file.read_text(encoding="utf-8").strip())

        assert data["audit_id"] == result["audit_id"]
        assert data["document_id"] == _FULL_STATE["document_id"]
        assert data["source_filename"] == _FULL_STATE["source_filename"]
        assert data["extraction_method"] == _FULL_STATE["classification_method"]
        assert data["classification_result"] == _FULL_STATE["document_category"]
        assert data["confidence_score"] == pytest.approx(_FULL_STATE["classification_confidence"])
        assert data["validation_outcome"] == "passed"
        assert data["validation_errors"] == []
        assert data["processing_duration_ms"] == _FULL_STATE["processing_duration_ms"]

    def test_appends_multiple_entries(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        audit_node(_FULL_STATE)
        audit_node(_FULL_STATE)
        audit_node(_FULL_STATE)
        lines = [l for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3
        # Every line must be independently valid JSON
        for line in lines:
            assert isinstance(json.loads(line), dict)

    def test_entries_have_distinct_audit_ids(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        audit_node(_FULL_STATE)
        audit_node(_FULL_STATE)
        lines = log_file.read_text(encoding="utf-8").splitlines()
        ids = [json.loads(l)["audit_id"] for l in lines if l.strip()]
        assert ids[0] != ids[1]

    def test_audit_id_in_file_matches_returned_id(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        result = audit_node(_FULL_STATE)
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["audit_id"] == result["audit_id"]


# ---------------------------------------------------------------------------
# Validation outcome mapping
# ---------------------------------------------------------------------------


class TestValidationOutcomeMapping:
    """validation_status in state must map correctly to validation_outcome in JSONL."""

    @pytest.mark.parametrize("status,expected_outcome", [
        ("valid", "passed"),
        ("partial", "partial"),
        ("invalid", "failed"),
    ])
    def test_outcome_mapping(self, tmp_path, monkeypatch, status, expected_outcome):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        state = {**_FULL_STATE, "validation_status": status}
        audit_node(state)
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["validation_outcome"] == expected_outcome

    def test_missing_validation_status_defaults_to_passed(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        state = {k: v for k, v in _FULL_STATE.items() if k != "validation_status"}
        audit_node(state)
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["validation_outcome"] == "passed"


# ---------------------------------------------------------------------------
# LLM fields
# ---------------------------------------------------------------------------


class TestLlmFields:
    """LLM-related state fields must be reflected in the audit entry."""

    def test_llm_escalation_reason_written(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        state = {
            **_FULL_STATE,
            "classification_method": "llm_fallback",
            "llm_escalation_reason": "Score 0.40 below threshold 0.60",
        }
        audit_node(state)
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["llm_escalation_reason"] == "Score 0.40 below threshold 0.60"
        assert data["extraction_method"] == "llm_fallback"

    def test_llm_unavailable_written(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        state = {**_FULL_STATE, "llm_unavailable": True}
        audit_node(state)
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["llm_unavailable"] is True

    def test_validation_errors_written(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        errors = ["Missing mandatory field: 'invoice_number'"]
        state = {**_FULL_STATE, "validation_status": "partial", "validation_errors": errors}
        audit_node(state)
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["validation_errors"] == errors


# ---------------------------------------------------------------------------
# Default / missing state fields
# ---------------------------------------------------------------------------


class TestDefaultFields:
    """audit_node must handle empty or sparse state gracefully without crashing."""

    def test_empty_state_does_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
        result = audit_node({})
        assert "audit_id" in result

    def test_empty_state_produces_valid_jsonl(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        audit_node({})
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["source_filename"] == "unknown"
        assert data["classification_result"] == "unclassified"
        assert data["extraction_method"] == "unclassified"

    def test_written_entry_is_valid_audit_entry_schema(self, tmp_path, monkeypatch):
        """The written JSON must deserialise into a valid AuditEntry Pydantic model."""
        log_file = tmp_path / "audit.jsonl"
        monkeypatch.setenv("AUDIT_LOG_PATH", str(log_file))
        audit_node(_FULL_STATE)
        raw = json.loads(log_file.read_text(encoding="utf-8").strip())
        # Should not raise
        entry = AuditEntry(**raw)
        assert entry.audit_id is not None


# ---------------------------------------------------------------------------
# IO failure — graceful degradation
# ---------------------------------------------------------------------------


class TestIOFailure:
    """audit_node must not crash the pipeline if the file write fails."""

    def test_returns_audit_written_false_on_io_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
        with patch("builtins.open", side_effect=PermissionError("access denied")):
            result = audit_node(_FULL_STATE)
        # audit_id is still generated
        assert "audit_id" in result
        assert isinstance(result["audit_id"], str)
        # audit_written signals failure
        assert result["audit_written"] is False

    def test_does_not_raise_on_io_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
        with patch("builtins.open", side_effect=OSError("disk full")):
            # Must not raise — pipeline must continue
            try:
                audit_node(_FULL_STATE)
            except Exception as exc:
                pytest.fail(f"audit_node raised unexpectedly: {exc}")

    def test_audit_id_present_even_on_failure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
        with patch("builtins.open", side_effect=IOError("write error")):
            result = audit_node(_FULL_STATE)
        assert len(result["audit_id"]) == 36  # UUID4 format
