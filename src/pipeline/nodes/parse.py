"""
Stage 1 — Parse Node
Sprint: S1

Converts raw document bytes to structured Markdown using Docling.
Supports: PDF (digital + scanned), DOCX, PPTX, images.
OCR engine: RapidOCR (pure Python, no system binaries required).

Implemented in Sprint 1.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: parse document bytes → Markdown string.

    Input state keys:  source_filename, file_bytes
    Output state keys: parsed_markdown | parse_error
    """
    # TODO (Sprint 1): implement Docling conversion
    raise NotImplementedError("parse_node — implement in Sprint 1")
