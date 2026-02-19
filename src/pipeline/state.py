"""
LangGraph pipeline state definition.

PipelineState is the single TypedDict that flows through all five
pipeline stages:  parse → classify → validate → audit → output

Every node receives the full state and returns a partial dict with
only the keys it modified — LangGraph merges these automatically.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from typing_extensions import TypedDict


class PipelineState(TypedDict, total=False):
    """
    Shared state object passed between LangGraph nodes.

    All fields are Optional (total=False) because each node only
    populates the fields it is responsible for. Use .get() with
    a default when reading upstream fields in a node.
    """

    # ------------------------------------------------------------------
    # Input (set by the caller before graph.invoke())
    # ------------------------------------------------------------------
    source_filename: str
    """Original filename of the document being processed."""

    file_bytes: bytes
    """Raw document bytes. Passed to the Docling parse node."""

    document_id: str
    """Unique ID assigned at pipeline entry. Propagated to all outputs."""

    start_time_ms: int
    """Unix timestamp in ms when the pipeline was invoked. Used for duration calc."""

    # ------------------------------------------------------------------
    # Pre-parse: document metadata
    # ------------------------------------------------------------------
    document_metadata: dict[str, Any]
    """
    Serialised DocumentMetadata dict — filesystem + document-internal properties.
    Populated by the metadata extractor before or during parse.
    """

    source_path: Optional[str]
    """Absolute path to the source file on disk (set by watcher or API)."""

    # ------------------------------------------------------------------
    # Stage 1: parse node output
    # ------------------------------------------------------------------
    parsed_markdown: str
    """
    Full document content as Markdown string produced by Docling.
    This is the primary input to the keyword classifier.
    """

    parse_error: Optional[str]
    """Non-None if Docling failed to parse the document."""

    # ------------------------------------------------------------------
    # Stage 2: classify node output
    # ------------------------------------------------------------------
    document_category: str
    """Winning category slug (e.g. 'invoice', 'contract') or 'unclassified'."""

    classification_method: Literal["deterministic", "llm_fallback", "unclassified"]
    """Whether the keyword engine or LLM made the decision."""

    classification_confidence: float
    """Confidence score in [0.0, 1.0]."""

    matched_keywords: list[str]
    """Keywords that contributed to the deterministic classification."""

    llm_escalation_reason: Optional[str]
    """Why the document was passed to the LLM. None for deterministic path."""

    llm_unavailable: bool
    """True if LLM was needed but unreachable (graceful degradation)."""

    extracted_fields: dict[str, Any]
    """
    Regex-extracted metadata fields keyed by pattern name.
    Example: {'invoice_number': 'INV-001', 'total_amount': '1250.00'}
    """

    # ------------------------------------------------------------------
    # Stage 3: validate node output
    # ------------------------------------------------------------------
    validation_status: Literal["valid", "invalid", "partial"]
    """
    'valid'   — all mandatory_fields present and schema validates
    'partial' — one or more mandatory_fields missing
    'invalid' — Pydantic schema validation failure
    """

    validation_errors: list[str]
    """Field-level error messages. Empty list when validation_status == 'valid'."""

    # ------------------------------------------------------------------
    # Stage 4: audit node output
    # ------------------------------------------------------------------
    audit_id: str
    """ID of the AuditEntry written to the JSONL log."""

    audit_written: bool
    """True if the audit entry was successfully appended to the log file."""

    # ------------------------------------------------------------------
    # Stage 5: output node output
    # ------------------------------------------------------------------
    final_output: Optional[dict[str, Any]]
    """
    Serialised ExtractedDocument dict — the final API/UI response payload.
    None if the pipeline failed before reaching the output stage.
    """

    # ------------------------------------------------------------------
    # Cross-cutting: error handling
    # ------------------------------------------------------------------
    pipeline_error: Optional[str]
    """
    Set by any node that encounters an unrecoverable error.
    When non-None, subsequent nodes must skip their work and propagate this.
    No document is silently dropped — every failure produces an audit entry.
    """

    processing_duration_ms: int
    """Total pipeline duration in ms. Set by the output node."""
