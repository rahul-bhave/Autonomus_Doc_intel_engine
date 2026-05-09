"""
Sprint 5 — FastAPI REST API tests.

All tests mock src.api.server._run_pipeline so docling is NOT required.
The TestClient exercises real FastAPI routing, request parsing, and error handling.
"""

from __future__ import annotations

import io
import os
from typing import Any
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from src.api.server import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

client = TestClient(app, raise_server_exceptions=False)

_MOCK_TARGET = "src.api.server._run_pipeline"

_MINIMAL_OUTPUT: dict[str, Any] = {
    "document_id": "doc-001",
    "source_filename": "invoice.pdf",
    "document_category": "invoice",
    "classification_method": "deterministic",
    "classification_confidence": 0.92,
    "matched_keywords": ["invoice", "total"],
    "llm_escalation_reason": None,
    "llm_unavailable": False,
    "extracted_fields": {"invoice_number": "INV-001"},
    "validation_status": "valid",
    "validation_errors": [],
    "processing_duration_ms": 120,
}

_SUCCESS_STATE: dict[str, Any] = {
    "final_output": _MINIMAL_OUTPUT,
    "pipeline_error": None,
}

_FAILURE_STATE: dict[str, Any] = {
    "final_output": None,
    "pipeline_error": "Unsupported file type: .exe",
}


def _upload(filename: str = "invoice.pdf", content: bytes = b"%PDF-fake") -> Any:
    """POST /process with an in-memory file."""
    return client.post(
        "/process",
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
    )


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_ok_body(self):
        resp = client.get("/health")
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /process — happy path
# ---------------------------------------------------------------------------

class TestProcessSuccess:
    @patch(_MOCK_TARGET, return_value=_SUCCESS_STATE)
    def test_returns_200(self, mock_pipeline):
        resp = _upload()
        assert resp.status_code == 200

    @patch(_MOCK_TARGET, return_value=_SUCCESS_STATE)
    def test_response_has_document_id(self, mock_pipeline):
        resp = _upload()
        assert resp.json()["document_id"] == "doc-001"

    @patch(_MOCK_TARGET, return_value=_SUCCESS_STATE)
    def test_response_has_category(self, mock_pipeline):
        resp = _upload()
        assert resp.json()["document_category"] == "invoice"

    @patch(_MOCK_TARGET, return_value=_SUCCESS_STATE)
    def test_response_has_validation_status(self, mock_pipeline):
        resp = _upload()
        assert resp.json()["validation_status"] == "valid"

    @patch(_MOCK_TARGET, return_value=_SUCCESS_STATE)
    def test_filename_forwarded_to_pipeline(self, mock_pipeline):
        _upload(filename="contract.pdf")
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args
        passed_name = call_kwargs[1].get("source_filename") or call_kwargs[0][0]
        assert passed_name == "contract.pdf"

    @patch(_MOCK_TARGET, return_value=_SUCCESS_STATE)
    def test_file_bytes_forwarded_to_pipeline(self, mock_pipeline):
        content = b"%PDF-test-content"
        _upload(content=content)
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args
        passed_bytes = call_kwargs[1].get("file_bytes") or call_kwargs[0][1]
        assert passed_bytes == content


# ---------------------------------------------------------------------------
# POST /process — pipeline failure → 500
# ---------------------------------------------------------------------------

class TestProcessPipelineError:
    @patch(_MOCK_TARGET, return_value=_FAILURE_STATE)
    def test_returns_500(self, mock_pipeline):
        resp = _upload()
        assert resp.status_code == 500

    @patch(_MOCK_TARGET, return_value=_FAILURE_STATE)
    def test_error_detail_in_body(self, mock_pipeline):
        resp = _upload()
        assert "Unsupported file type" in resp.json()["detail"]

    @patch(_MOCK_TARGET, side_effect=RuntimeError("docling exploded"))
    def test_unhandled_exception_returns_500(self, mock_pipeline):
        resp = _upload()
        assert resp.status_code == 500

    @patch(_MOCK_TARGET, side_effect=RuntimeError("docling exploded"))
    def test_unhandled_exception_detail_in_body(self, mock_pipeline):
        resp = _upload()
        assert "docling exploded" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /process — missing file → 422
# ---------------------------------------------------------------------------

class TestProcessMissingFile:
    def test_no_file_returns_422(self):
        resp = client.post("/process")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# X-API-Key header handling
# ---------------------------------------------------------------------------

class TestApiKeyHeader:
    @patch(_MOCK_TARGET, return_value=_SUCCESS_STATE)
    def test_api_key_header_accepted(self, mock_pipeline):
        resp = client.post(
            "/process",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            headers={"X-API-Key": "sk-test-key"},
        )
        assert resp.status_code == 200

    def test_api_key_sets_env_during_request(self):
        """API key from header must be in ANTHROPIC_API_KEY when _run_pipeline is called."""
        captured: list[str] = []

        def capture_key(source_filename, file_bytes):
            captured.append(os.environ.get("ANTHROPIC_API_KEY", ""))
            return _SUCCESS_STATE

        with patch(_MOCK_TARGET, side_effect=capture_key):
            client.post(
                "/process",
                files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
                headers={"X-API-Key": "sk-captured"},
            )

        assert captured == ["sk-captured"]

    def test_api_key_restored_after_request(self):
        """ANTHROPIC_API_KEY must be restored to its prior value after the request."""
        original = os.environ.get("ANTHROPIC_API_KEY", "__not_set__")

        with patch(_MOCK_TARGET, return_value=_SUCCESS_STATE):
            client.post(
                "/process",
                files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
                headers={"X-API-Key": "sk-temp"},
            )

        after = os.environ.get("ANTHROPIC_API_KEY", "__not_set__")
        assert after == original


# ---------------------------------------------------------------------------
# OpenAPI docs endpoint
# ---------------------------------------------------------------------------

class TestDocs:
    def test_openapi_docs_available(self):
        resp = client.get("/docs")
        assert resp.status_code == 200
