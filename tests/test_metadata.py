"""
Pre-Sprint 3 — Metadata extractor tests.

Tests for src/metadata/extractor.py covering:
- Filesystem metadata (size, extension, MIME type)
- PDF internal metadata (page count, author, title, producer)
- Edge cases (empty bytes, unknown format, missing source_path)
- Integration with parse_node (metadata_dict in output)

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_metadata.py -v
"""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.metadata.extractor import extract_metadata
from src.models.schemas import DocumentMetadata

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "documents"


def _load_fixture(name: str) -> bytes:
    """Read a test fixture as raw bytes."""
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
# DocumentMetadata model tests
# ---------------------------------------------------------------------------


class TestDocumentMetadataModel:
    """Tests for the DocumentMetadata Pydantic model."""

    def test_default_values(self):
        meta = DocumentMetadata()
        assert meta.file_size_bytes == 0
        assert meta.file_extension == ""
        assert meta.mime_type is None
        assert meta.created_at is None
        assert meta.modified_at is None
        assert meta.page_count is None
        assert meta.author is None
        assert meta.title is None
        assert meta.producer is None
        assert meta.creation_date is None

    def test_all_fields_populated(self):
        now = datetime.now(timezone.utc)
        meta = DocumentMetadata(
            file_size_bytes=1024,
            file_extension=".pdf",
            mime_type="application/pdf",
            created_at=now,
            modified_at=now,
            page_count=5,
            author="Test Author",
            title="Test Title",
            producer="Test Producer",
            creation_date="2024-01-01",
        )
        assert meta.file_size_bytes == 1024
        assert meta.file_extension == ".pdf"
        assert meta.page_count == 5
        assert meta.author == "Test Author"

    def test_serialization_roundtrip(self):
        meta = DocumentMetadata(
            file_size_bytes=512,
            file_extension=".docx",
            mime_type="application/zip",
        )
        data = meta.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["file_size_bytes"] == 512
        assert data["file_extension"] == ".docx"
        restored = DocumentMetadata.model_validate(data)
        assert restored == meta


# ---------------------------------------------------------------------------
# Filesystem metadata tests
# ---------------------------------------------------------------------------


class TestFilesystemMetadata:
    """Tests for filesystem-level metadata extraction."""

    def test_file_size(self, invoice_bytes):
        meta = extract_metadata(invoice_bytes, "invoice.pdf")
        assert meta.file_size_bytes == len(invoice_bytes)

    def test_file_extension_pdf(self, invoice_bytes):
        meta = extract_metadata(invoice_bytes, "test.pdf")
        assert meta.file_extension == ".pdf"

    def test_file_extension_case_insensitive(self, invoice_bytes):
        meta = extract_metadata(invoice_bytes, "test.PDF")
        assert meta.file_extension == ".pdf"

    def test_mime_type_pdf(self, invoice_bytes):
        meta = extract_metadata(invoice_bytes, "invoice.pdf")
        assert meta.mime_type == "application/pdf"

    def test_no_source_path_no_timestamps(self, invoice_bytes):
        meta = extract_metadata(invoice_bytes, "invoice.pdf")
        assert meta.created_at is None
        assert meta.modified_at is None

    def test_source_path_populates_timestamps(self, invoice_bytes):
        """When source_path points to a real file, timestamps are populated."""
        fixture_path = str(FIXTURES_DIR / "invoice_digital.pdf")
        meta = extract_metadata(invoice_bytes, "invoice_digital.pdf", source_path=fixture_path)
        assert meta.created_at is not None
        assert meta.modified_at is not None
        assert isinstance(meta.created_at, datetime)
        assert isinstance(meta.modified_at, datetime)

    def test_invalid_source_path_graceful(self, invoice_bytes):
        """Non-existent source_path doesn't crash — timestamps remain None."""
        meta = extract_metadata(invoice_bytes, "invoice.pdf", source_path="/no/such/file.pdf")
        assert meta.created_at is None
        assert meta.modified_at is None

    def test_empty_bytes(self):
        meta = extract_metadata(b"", "empty.pdf")
        assert meta.file_size_bytes == 0
        assert meta.mime_type is None

    def test_unknown_extension(self, invoice_bytes):
        """Unknown extension still detects MIME from content."""
        meta = extract_metadata(invoice_bytes, "document.xyz")
        assert meta.file_extension == ".xyz"
        assert meta.mime_type == "application/pdf"


# ---------------------------------------------------------------------------
# PDF internal metadata tests
# ---------------------------------------------------------------------------


class TestPdfMetadata:
    """Tests for PDF-internal metadata extraction via pypdfium2."""

    def test_page_count(self, invoice_bytes):
        meta = extract_metadata(invoice_bytes, "invoice.pdf")
        assert meta.page_count is not None
        assert meta.page_count >= 1

    def test_page_count_resume(self, resume_bytes):
        meta = extract_metadata(resume_bytes, "resume.pdf")
        assert meta.page_count is not None
        assert meta.page_count >= 1

    def test_page_count_contract(self, contract_bytes):
        meta = extract_metadata(contract_bytes, "contract.pdf")
        assert meta.page_count is not None
        assert meta.page_count >= 1

    def test_metadata_fields_are_strings_or_none(self, invoice_bytes):
        """Author/title/producer should be str or None, never other types."""
        meta = extract_metadata(invoice_bytes, "invoice.pdf")
        for field in ("author", "title", "producer", "creation_date"):
            val = getattr(meta, field)
            assert val is None or isinstance(val, str), f"{field} is {type(val)}"

    def test_non_pdf_bytes_no_crash(self):
        """Random bytes shouldn't crash the PDF extractor."""
        meta = extract_metadata(b"not a pdf", "test.pdf")
        # page_count won't be set since pypdfium2 will fail
        # but it should not raise
        assert meta.file_size_bytes == 9


# ---------------------------------------------------------------------------
# Integration: metadata in parse_node output
# ---------------------------------------------------------------------------


class TestParseNodeMetadataIntegration:
    """Verify parse_node includes document_metadata in its output."""

    def test_parse_node_includes_metadata(self, invoice_bytes):
        from src.pipeline.nodes.parse import parse_node

        state = {
            "source_filename": "invoice_digital.pdf",
            "file_bytes": invoice_bytes,
        }
        result = parse_node(state)
        assert "document_metadata" in result
        meta = result["document_metadata"]
        assert isinstance(meta, dict)
        assert meta["file_size_bytes"] == len(invoice_bytes)
        assert meta["file_extension"] == ".pdf"
        assert meta["mime_type"] == "application/pdf"
        assert meta["page_count"] is not None
        assert meta["page_count"] >= 1

    def test_parse_node_metadata_on_validation_failure(self):
        """Even when file validation fails, no metadata is returned (rejected before extraction)."""
        from src.pipeline.nodes.parse import parse_node

        state = {
            "source_filename": "malware.exe",
            "file_bytes": b"MZ\x90\x00",
        }
        result = parse_node(state)
        assert "parse_error" in result
        # Validation rejects before metadata extraction
        assert "document_metadata" not in result
