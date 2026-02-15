"""
Sprint 1 — Parse node tests.

Verifies that parse_node() converts PDF fixtures to Markdown correctly
and handles edge cases (empty bytes, missing filename).

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_parse.py -v
"""

import pytest
from pathlib import Path

from src.pipeline.nodes.parse import parse_node

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "documents"


def _load_fixture(name: str) -> bytes:
    """Read a test PDF fixture as raw bytes."""
    path = FIXTURES_DIR / name
    assert path.exists(), f"Fixture not found: {path}"
    return path.read_bytes()


@pytest.fixture
def invoice_bytes():
    return _load_fixture("invoice_digital.pdf")


@pytest.fixture
def resume_bytes():
    return _load_fixture("resume_standard.pdf")


@pytest.fixture
def contract_bytes():
    return _load_fixture("contract_service.pdf")


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestParseNodeSuccess:
    """Tests that parse_node returns parsed_markdown for valid PDFs."""

    def test_invoice_returns_markdown(self, invoice_bytes):
        result = parse_node({"file_bytes": invoice_bytes, "source_filename": "invoice_digital.pdf"})
        assert "parsed_markdown" in result
        assert "parse_error" not in result
        assert len(result["parsed_markdown"]) > 100

    def test_invoice_contains_key_content(self, invoice_bytes):
        result = parse_node({"file_bytes": invoice_bytes, "source_filename": "invoice_digital.pdf"})
        md = result["parsed_markdown"]
        assert "INV-2025-0042" in md
        assert "Acme Corp" in md

    def test_resume_returns_markdown(self, resume_bytes):
        result = parse_node({"file_bytes": resume_bytes, "source_filename": "resume_standard.pdf"})
        assert "parsed_markdown" in result
        assert len(result["parsed_markdown"]) > 100

    def test_resume_contains_key_content(self, resume_bytes):
        result = parse_node({"file_bytes": resume_bytes, "source_filename": "resume_standard.pdf"})
        md = result["parsed_markdown"]
        assert "Jane Smith" in md
        assert "Software Engineer" in md

    def test_contract_returns_markdown(self, contract_bytes):
        result = parse_node({"file_bytes": contract_bytes, "source_filename": "contract_service.pdf"})
        assert "parsed_markdown" in result
        assert len(result["parsed_markdown"]) > 100

    def test_contract_contains_key_content(self, contract_bytes):
        result = parse_node({"file_bytes": contract_bytes, "source_filename": "contract_service.pdf"})
        md = result["parsed_markdown"]
        assert "SERVICE AGREEMENT" in md or "Agreement" in md
        assert "TechStar Solutions" in md


# ---------------------------------------------------------------------------
# Error / edge-case tests
# ---------------------------------------------------------------------------


class TestParseNodeErrors:
    """Tests that parse_node handles invalid inputs gracefully."""

    def test_empty_bytes_returns_error(self):
        result = parse_node({"file_bytes": b"", "source_filename": "empty.pdf"})
        assert "parse_error" in result
        assert "parsed_markdown" not in result

    def test_no_file_bytes_returns_error(self):
        result = parse_node({"source_filename": "missing.pdf"})
        assert "parse_error" in result
        assert "No file bytes" in result["parse_error"]

    def test_corrupt_bytes_returns_error(self):
        result = parse_node({"file_bytes": b"not a real pdf", "source_filename": "corrupt.pdf"})
        assert "parse_error" in result

    def test_missing_filename_uses_default(self, invoice_bytes):
        result = parse_node({"file_bytes": invoice_bytes})
        # Should still parse successfully with default "unknown" filename
        assert "parsed_markdown" in result


# ---------------------------------------------------------------------------
# Markdown quality checks
# ---------------------------------------------------------------------------


class TestMarkdownQuality:
    """Validates that the Markdown output has reasonable structure."""

    def test_invoice_has_table(self, invoice_bytes):
        result = parse_node({"file_bytes": invoice_bytes, "source_filename": "invoice_digital.pdf"})
        md = result["parsed_markdown"]
        # Docling should produce pipe-delimited table rows
        assert "|" in md

    def test_resume_has_sections(self, resume_bytes):
        result = parse_node({"file_bytes": resume_bytes, "source_filename": "resume_standard.pdf"})
        md = result["parsed_markdown"]
        # Docling should produce markdown headings for resume sections
        assert "Experience" in md or "Education" in md or "Skills" in md

    def test_output_is_string(self, invoice_bytes):
        result = parse_node({"file_bytes": invoice_bytes, "source_filename": "invoice_digital.pdf"})
        assert isinstance(result["parsed_markdown"], str)
