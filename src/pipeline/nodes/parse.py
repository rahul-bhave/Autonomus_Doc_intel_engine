"""
Stage 1 — Parse Node
Sprint: S1

Converts raw document bytes to structured Markdown using Docling.
Supports: PDF (digital + scanned), DOCX, PPTX, images.
OCR engine: RapidOCR (pure Python, no system binaries required).

The DocumentConverter is instantiated once at module level (expensive —
loads ONNX models). All subsequent calls reuse the same converter instance.
"""

from __future__ import annotations

import logging
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Windows symlink workaround (must run BEFORE importing huggingface_hub)
# WinError 1314 is an OSError that huggingface_hub doesn't catch properly.
# Force it to copy files instead of creating symlinks.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import huggingface_hub.file_download as _hf_dl
    _hf_dl.are_symlinks_supported = lambda *_args, **_kwargs: False

from docling.datamodel.base_models import ConversionStatus, DocumentStream, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

import filetype

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File validation constants
# ---------------------------------------------------------------------------

BLOCKED_EXTENSIONS: frozenset[str] = frozenset({
    ".exe", ".dll", ".bat", ".cmd", ".com", ".msi",
    ".scr", ".ps1", ".sh", ".vbs", ".js",
})

KNOWN_GOOD_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".tiff", ".tif",
})

SUPPORTED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
    "image/png",
    "image/jpeg",
    "image/tiff",
})


def _validate_file(filename: str, file_bytes: bytes) -> Optional[str]:
    """
    Validate file extension and content type before parsing.

    Returns None if the file is acceptable, or an error message string
    if the file should be rejected.
    """
    ext = Path(filename).suffix.lower()

    # Layer 1: Block dangerous extensions immediately
    if ext in BLOCKED_EXTENSIONS:
        logger.warning("Blocked dangerous file extension: '%s' (%s)", filename, ext)
        return f"File rejected: dangerous extension '{ext}' is not allowed"

    # Layer 2: Known good extensions — proceed directly to Docling
    if ext in KNOWN_GOOD_EXTENSIONS:
        return None

    # Layer 3: Unknown extension — inspect content via magic bytes
    kind = filetype.guess(file_bytes)
    if kind is None:
        logger.warning(
            "Unknown file type for '%s': no MIME type detected from content", filename,
        )
        return (
            f"File rejected: unknown extension '{ext}' "
            f"and content type could not be determined"
        )

    detected_mime = kind.mime
    if detected_mime in SUPPORTED_MIME_TYPES:
        logger.info(
            "Unknown extension '%s' for '%s', but detected supported MIME type: %s",
            ext, filename, detected_mime,
        )
        return None

    logger.warning(
        "File rejected: '%s' has unknown extension '%s' and unsupported MIME type '%s'",
        filename, ext, detected_mime,
    )
    return f"File rejected: unsupported content type '{detected_mime}' (extension: '{ext}')"


# ---------------------------------------------------------------------------
# Module-level converter singleton (expensive init — do once)
# ---------------------------------------------------------------------------

_converter: Optional[DocumentConverter] = None


def _get_converter() -> DocumentConverter:
    """Return the module-level DocumentConverter, building it on first call."""
    global _converter
    if _converter is None:
        ocr_options = RapidOcrOptions()
        pipeline_options = PdfPipelineOptions(
            do_ocr=True,
            ocr_options=ocr_options,
        )
        _converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )
        logger.info("Docling DocumentConverter initialised (OCR=RapidOCR)")
    return _converter


# ---------------------------------------------------------------------------
# Pipeline node
# ---------------------------------------------------------------------------

def parse_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: parse document bytes → Markdown string.

    Input state keys:
        source_filename  — original filename (used for format detection)
        file_bytes       — raw document bytes

    Output state keys:
        parsed_markdown  — Markdown string (on success / partial success)
        parse_error      — error message string (on failure)

    Both keys may be set on partial success (markdown + warnings logged).
    On hard failure, only parse_error is set.
    """
    file_bytes: bytes = state.get("file_bytes", b"")
    filename: str = state.get("source_filename", "unknown")

    if not file_bytes:
        return {"parse_error": f"No file bytes provided for '{filename}'"}

    # File validation guard — block dangerous extensions and unknown types
    validation_error = _validate_file(filename, file_bytes)
    if validation_error:
        return {"parse_error": validation_error}

    try:
        converter = _get_converter()

        source = DocumentStream(name=filename, stream=BytesIO(file_bytes))

        result = converter.convert(source, raises_on_error=False)

        if result.status == ConversionStatus.SUCCESS:
            markdown = result.document.export_to_markdown()
            logger.info("Parsed '%s' successfully (%d chars)", filename, len(markdown))
            output: dict[str, Any] = {"parsed_markdown": markdown}

            # Optionally persist Markdown to disk for debugging
            if os.environ.get("DEBUG_PERSIST_MARKDOWN", "").lower() == "true":
                _persist_markdown(state.get("document_id", "unknown"), markdown)

            return output

        elif result.status == ConversionStatus.PARTIAL_SUCCESS:
            markdown = result.document.export_to_markdown()
            warnings = [e.error_message for e in result.errors]
            logger.warning(
                "Partial conversion for '%s' (%d chars, %d warnings): %s",
                filename, len(markdown), len(warnings), warnings,
            )
            output = {"parsed_markdown": markdown}

            if os.environ.get("DEBUG_PERSIST_MARKDOWN", "").lower() == "true":
                _persist_markdown(state.get("document_id", "unknown"), markdown)

            return output

        else:
            # FAILURE or SKIPPED
            error_msgs = "; ".join(e.error_message for e in result.errors) or "Unknown conversion error"
            logger.error("Conversion failed for '%s': %s", filename, error_msgs)
            return {"parse_error": f"Docling conversion failed: {error_msgs}"}

    except Exception as exc:
        logger.exception("Unexpected error parsing '%s'", filename)
        return {"parse_error": f"Unexpected parse error: {exc}"}


# ---------------------------------------------------------------------------
# Debug helper
# ---------------------------------------------------------------------------

def _persist_markdown(document_id: str, markdown: str) -> None:
    """Write parsed Markdown to data/output/<document_id>.md when DEBUG_PERSIST_MARKDOWN=true."""
    try:
        output_dir = Path("data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{document_id}.md"
        out_path.write_text(markdown, encoding="utf-8")
        logger.debug("Persisted Markdown to %s", out_path)
    except Exception as exc:
        logger.warning("Failed to persist debug Markdown: %s", exc)
