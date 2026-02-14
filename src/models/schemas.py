"""
Pydantic v2 schemas for the Autonomous Document Intel Engine.

These are the canonical data contracts used across the entire pipeline.
Every node in the LangGraph graph reads/writes these types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Intermediate: output of the keyword classifier node
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    """Intermediate output produced by the keyword engine (or LLM fallback)."""

    category: str
    """Matched document category slug, e.g. 'invoice', 'contract'."""

    confidence: float = Field(ge=0.0, le=1.0)
    """Confidence score in [0.0, 1.0]."""

    method: Literal["deterministic", "llm_fallback", "unclassified"]
    """Whether classification was done by the keyword engine or LLM."""

    matched_keywords: list[str] = Field(default_factory=list)
    """Primary and secondary keywords that contributed to the score."""

    escalation_reason: Optional[str] = None
    """Populated only when method == 'llm_fallback'. Explains why LLM was invoked."""

    llm_unavailable: bool = False
    """Set to True when LLM was needed but unreachable. Graceful degradation flag."""


# ---------------------------------------------------------------------------
# Core output schema: one record per processed document
# ---------------------------------------------------------------------------

class ExtractedDocument(BaseModel):
    """
    Final output record for a processed document.
    Stored in SQLite and returned by the REST API.
    """

    document_id: str = Field(default_factory=lambda: str(uuid4()))
    """Unique identifier for this processing run."""

    source_filename: str
    """Original filename of the uploaded document."""

    document_category: str
    """Classified document category, e.g. 'invoice', 'contract', 'resume'."""

    classification_method: Literal["deterministic", "llm_fallback", "unclassified"]
    """Traceability: which path made the classification decision."""

    classification_confidence: float = Field(ge=0.0, le=1.0)
    """Confidence score produced by the classifier."""

    matched_keywords: list[str] = Field(default_factory=list)
    """Keywords that triggered the deterministic classification."""

    llm_escalation_reason: Optional[str] = None
    """Reason the document was escalated to LLM. None for deterministic path."""

    llm_unavailable: bool = False
    """True if LLM was needed but unreachable during this run."""

    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    """
    Domain-specific fields extracted by regex patterns.
    Keys match the regex_patterns entries in the category YAML.
    Example: {'invoice_number': 'INV-001', 'total_amount': '1250.00'}
    """

    validation_status: Literal["valid", "invalid", "partial"]
    """
    'valid'   — all mandatory_fields present and schema passes
    'partial' — one or more mandatory_fields missing but no schema errors
    'invalid' — Pydantic schema validation failed
    """

    validation_errors: list[str] = Field(default_factory=list)
    """Field-level error messages from Pydantic validation. Empty when valid."""

    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """UTC timestamp when this document completed the pipeline."""

    processing_duration_ms: int = 0
    """Total wall-clock time in milliseconds from parse start to output."""

    @field_validator("classification_confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 4)


# ---------------------------------------------------------------------------
# Audit log entry: one record per document, append-only
# ---------------------------------------------------------------------------

class AuditEntry(BaseModel):
    """
    Immutable audit record written after every pipeline run.
    Persisted to an append-only JSONL file.
    """

    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    """Unique identifier for this audit entry."""

    document_id: str
    """Matches ExtractedDocument.document_id for cross-referencing."""

    source_filename: str
    """Original filename — duplicated here so the audit log is self-contained."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """UTC timestamp when this audit entry was written."""

    extraction_method: Literal["deterministic", "llm_fallback", "unclassified"]
    """Classification method used for this document."""

    llm_escalation_reason: Optional[str] = None
    """Why the document was escalated to LLM, if applicable."""

    llm_unavailable: bool = False
    """Whether the LLM was unavailable during this run."""

    classification_result: str
    """Final category assigned (or 'unclassified')."""

    confidence_score: float = Field(ge=0.0, le=1.0)
    """Confidence score at time of classification."""

    validation_outcome: Literal["passed", "failed", "partial"]
    """Whether schema validation passed, failed, or was partial."""

    validation_errors: list[str] = Field(default_factory=list)
    """Validation error messages, if any."""

    processing_duration_ms: int
    """End-to-end pipeline duration in milliseconds."""

    @classmethod
    def from_extracted(cls, doc: ExtractedDocument) -> "AuditEntry":
        """Convenience constructor: build an AuditEntry from an ExtractedDocument."""
        outcome_map = {"valid": "passed", "invalid": "failed", "partial": "partial"}
        return cls(
            document_id=doc.document_id,
            source_filename=doc.source_filename,
            timestamp=doc.processed_at,
            extraction_method=doc.classification_method,
            llm_escalation_reason=doc.llm_escalation_reason,
            llm_unavailable=doc.llm_unavailable,
            classification_result=doc.document_category,
            confidence_score=doc.classification_confidence,
            validation_outcome=outcome_map[doc.validation_status],
            validation_errors=doc.validation_errors,
            processing_duration_ms=doc.processing_duration_ms,
        )


# ---------------------------------------------------------------------------
# QE feedback record: written when a reviewer flags a document
# ---------------------------------------------------------------------------

class FeedbackRecord(BaseModel):
    """
    Stored by the Gradio 'Flag for Review' action.
    Written to the feedback JSONL file for keyword dictionary review.
    """

    feedback_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    source_filename: str
    flagged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    predicted_category: str
    reviewer_correct_category: str
    reviewer_notes: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    matched_keywords: list[str] = Field(default_factory=list)
