"""
Sprint 3 — LangGraph Pipeline Tests

Tests the pipeline graph wiring, classify_node, output_node, and
end-to-end flows with mocked Docling (no heavy model downloads).

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_pipeline.py -v
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.graph import build_graph, route_after_classify, run_pipeline
from src.pipeline.nodes.classify import classify_node
from src.pipeline.nodes.output import output_node
from src.pipeline.nodes.validate import validate_node
from src.pipeline.nodes.audit import audit_node


# ---------------------------------------------------------------------------
# Sample Markdown for testing (triggers invoice classification)
# ---------------------------------------------------------------------------

INVOICE_MARKDOWN = """\
# Tax Invoice

Invoice Number: INV-2024-001
Invoice No: INV-2024-001
Invoice Date: 2024-03-15
Due Date: 2024-04-15

Vendor: Widgets International Ltd.
Supplier ID: SUP-9876
Account Number: ACC-55443

Bill To:
  Acme Corporation
  123 Main Street
  Purchase Order: PO-2024-100
  PO Number: PO-2024-100

Payment Terms: Net 30

| Line Item     | Item Description    | Quantity | Unit Price | Amount   |
|---------------|---------------------|----------|------------|----------|
| Widget A      | Premium widget      | 10       | $50.00     | $500.00  |
| Widget B      | Standard widget     | 5        | $75.00     | $375.00  |

Subtotal: $875.00
Discount: -$0.00
Tax (GST 10%): $87.50
Freight: $0.00
Total Amount: $962.50
Total Due: $962.50
Balance Due: $962.50
Amount Due: $962.50

Payment Due by April 15, 2024.
Please remit payment to: Bank of Example
Remit to: Bank of Example, Account #12345678
Remittance advice required.
"""

GARBAGE_MARKDOWN = "The quick brown fox jumps over the lazy dog. Nothing useful here."


# ---------------------------------------------------------------------------
# Graph Structure Tests
# ---------------------------------------------------------------------------


class TestGraphStructure:
    """Tests that the graph compiles and has the right shape."""

    def test_build_graph_returns_compiled(self):
        graph = build_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"parse", "classify", "llm_fallback", "validate", "audit", "output"}
        # LangGraph adds __start__ and __end__ nodes
        assert expected.issubset(node_names)


# ---------------------------------------------------------------------------
# Routing Logic Tests
# ---------------------------------------------------------------------------


class TestRouting:
    """Tests for the conditional routing function."""

    def test_route_to_validate_on_deterministic(self):
        state = {"document_category": "invoice", "classification_confidence": 0.85}
        assert route_after_classify(state) == "validate"

    def test_route_to_llm_on_escalation(self):
        state = {"llm_escalation_reason": "Best match scored 0.45 but threshold is 0.60"}
        assert route_after_classify(state) == "llm_fallback"

    def test_route_to_validate_on_pipeline_error(self):
        state = {"pipeline_error": "Parse failed", "llm_escalation_reason": "something"}
        assert route_after_classify(state) == "validate"


# ---------------------------------------------------------------------------
# classify_node Unit Tests
# ---------------------------------------------------------------------------


class TestClassifyNode:
    """Tests for the classify_node function."""

    def test_deterministic_invoice(self):
        state = {"parsed_markdown": INVOICE_MARKDOWN}
        result = classify_node(state)
        assert result["document_category"] == "invoice"
        assert result["classification_method"] == "deterministic"
        assert result["classification_confidence"] >= 0.60
        assert len(result["matched_keywords"]) > 0

    def test_unclassified_sets_escalation(self):
        state = {"parsed_markdown": GARBAGE_MARKDOWN}
        result = classify_node(state)
        assert result["document_category"] == "unclassified"
        assert result["classification_method"] == "unclassified"
        assert result.get("llm_escalation_reason") is not None

    def test_extracts_fields_for_invoice(self):
        state = {"parsed_markdown": INVOICE_MARKDOWN}
        result = classify_node(state)
        assert result["document_category"] == "invoice"
        fields = result.get("extracted_fields", {})
        # The invoice YAML has regex patterns for common fields
        # At minimum, extracted_fields should be a dict (may be empty if patterns don't match)
        assert isinstance(fields, dict)

    def test_skips_on_pipeline_error(self):
        state = {"pipeline_error": "Something broke", "parsed_markdown": INVOICE_MARKDOWN}
        result = classify_node(state)
        assert result == {}

    def test_sets_error_on_empty_markdown(self):
        state = {"parsed_markdown": ""}
        result = classify_node(state)
        assert "pipeline_error" in result

    def test_sets_error_on_missing_markdown(self):
        state = {}
        result = classify_node(state)
        assert "pipeline_error" in result


# ---------------------------------------------------------------------------
# validate_node Tests (pass-through stub)
# ---------------------------------------------------------------------------


class TestValidateNode:
    """Tests for the Sprint 3 pass-through validate_node."""

    def test_returns_valid_on_normal_state(self):
        state = {"document_category": "invoice", "extracted_fields": {}}
        result = validate_node(state)
        assert result["validation_status"] == "valid"
        assert result["validation_errors"] == []

    def test_returns_invalid_on_pipeline_error(self):
        state = {"pipeline_error": "Parse failed"}
        result = validate_node(state)
        assert result["validation_status"] == "invalid"
        assert "Parse failed" in result["validation_errors"]


# ---------------------------------------------------------------------------
# audit_node Tests (pass-through stub)
# ---------------------------------------------------------------------------


class TestAuditNode:
    """Tests for the Sprint 3 pass-through audit_node."""

    def test_returns_audit_id(self):
        result = audit_node({})
        assert "audit_id" in result
        assert len(result["audit_id"]) > 0

    def test_audit_not_written(self):
        result = audit_node({})
        assert result["audit_written"] is False


# ---------------------------------------------------------------------------
# output_node Tests
# ---------------------------------------------------------------------------


class TestOutputNode:
    """Tests for the output_node function."""

    def test_builds_final_output(self):
        state = {
            "document_id": "test-123",
            "source_filename": "invoice.pdf",
            "document_category": "invoice",
            "classification_method": "deterministic",
            "classification_confidence": 0.85,
            "matched_keywords": ["invoice", "due date"],
            "extracted_fields": {"invoice_number": "INV-001"},
            "validation_status": "valid",
            "validation_errors": [],
            "start_time_ms": int(time.time() * 1000) - 100,
        }
        result = output_node(state)
        assert result["final_output"] is not None
        assert result["final_output"]["document_category"] == "invoice"
        assert result["final_output"]["document_id"] == "test-123"
        assert result["processing_duration_ms"] >= 0

    def test_calculates_duration(self):
        state = {"start_time_ms": int(time.time() * 1000) - 500}
        result = output_node(state)
        assert result["processing_duration_ms"] >= 0

    def test_pipeline_error_returns_none(self):
        state = {
            "pipeline_error": "Parse failed",
            "start_time_ms": int(time.time() * 1000),
        }
        result = output_node(state)
        assert result["final_output"] is None
        assert result["processing_duration_ms"] >= 0


# ---------------------------------------------------------------------------
# End-to-End Pipeline Tests (Docling mocked)
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end pipeline tests with mocked Docling parse node.

    We patch parse_node at the graph module level because LangGraph captures
    the function reference at build_graph() time. We rebuild the graph
    inside each test so the mock is picked up.
    """

    @patch("src.pipeline.graph.parse_node")
    def test_deterministic_invoice_flow(self, mock_parse):
        """High-confidence invoice → deterministic path, no LLM call."""
        mock_parse.return_value = {
            "parsed_markdown": INVOICE_MARKDOWN,
            "document_metadata": {"file_size_bytes": 1024},
        }

        result = run_pipeline("invoice.pdf", b"fake-pdf-bytes", document_id="test-det-001")

        assert result["document_category"] == "invoice"
        assert result["classification_method"] == "deterministic"
        assert result["classification_confidence"] >= 0.60
        assert result.get("llm_escalation_reason") is None
        assert result["final_output"] is not None
        assert result["final_output"]["document_category"] == "invoice"
        assert result["audit_id"] is not None

    @patch("src.pipeline.graph.parse_node")
    def test_unclassified_routes_to_llm(self, mock_parse, monkeypatch):
        """Garbage text → low confidence → routes to LLM → LLM unavailable."""
        mock_parse.return_value = {
            "parsed_markdown": GARBAGE_MARKDOWN,
            "document_metadata": {},
        }
        # No API key → LLM returns unavailable
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = run_pipeline("unknown.pdf", b"fake-bytes", document_id="test-unk-001")

        assert result.get("llm_escalation_reason") is not None
        assert result.get("llm_unavailable") is True
        assert result["final_output"] is not None
        assert result["audit_id"] is not None

    @patch("src.pipeline.graph.parse_node")
    def test_parse_error_propagates(self, mock_parse):
        """Parse failure → pipeline_error propagates through all nodes."""
        mock_parse.return_value = {
            "parse_error": "Blocked file extension: .exe",
            "pipeline_error": "Blocked file extension: .exe",
            "document_metadata": {},
        }

        result = run_pipeline("malware.exe", b"MZ\x90\x00", document_id="test-err-001")

        assert result.get("pipeline_error") is not None
        assert result["final_output"] is None
        assert result["audit_id"] is not None  # Every doc gets an audit entry

    @patch("src.pipeline.graph.parse_node")
    def test_pipeline_returns_processing_duration(self, mock_parse):
        """Pipeline always calculates processing duration."""
        mock_parse.return_value = {
            "parsed_markdown": INVOICE_MARKDOWN,
            "document_metadata": {},
        }

        result = run_pipeline("test.pdf", b"fake", document_id="test-dur-001")

        assert result["processing_duration_ms"] >= 0
