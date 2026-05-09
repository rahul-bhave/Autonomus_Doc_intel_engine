"""
REST API — Sprint 5
Exposes the LangGraph pipeline as a HTTP service.

Endpoints:
    POST /process   — multipart file upload → ExtractedDocument JSON
    GET  /health    — liveness probe

API key (for LLM fallback) is accepted via X-API-Key header.
It is held only for the duration of the request and never logged.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Autonomous Document Intel Engine",
    description="Document classification and metadata extraction pipeline.",
    version="0.5.0",
)


def _run_pipeline(source_filename: str, file_bytes: bytes) -> dict:
    # Lazy import keeps huggingface_hub/docling out of the import-time path,
    # so tests that mock this function don't need the full ML stack installed.
    from src.pipeline.graph import run_pipeline
    return run_pipeline(source_filename=source_filename, file_bytes=file_bytes)


@app.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process", summary="Process a document through the pipeline")
async def process_document(
    file: UploadFile = File(..., description="Document file to process (PDF, DOCX, PPTX, TXT)"),
    x_api_key: Optional[str] = Header(None, description="Anthropic API key for LLM fallback"),
) -> Any:
    """
    Upload a document and run it through the full parse → classify → validate → audit pipeline.

    Returns an ExtractedDocument JSON object on success.
    Returns HTTP 500 with a detail message if the pipeline fails.
    """
    file_bytes = await file.read()
    source_filename = file.filename or "upload"

    # Temporarily surface the API key to the LLM fallback node via env.
    # Sprint 7 will refactor this to thread it through PipelineState instead.
    prev_key: Optional[str] = None
    if x_api_key:
        prev_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = x_api_key

    try:
        state = _run_pipeline(
            source_filename=source_filename,
            file_bytes=file_bytes,
        )
    except Exception as exc:
        logger.exception("Unhandled exception in pipeline for '%s'", source_filename)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        # Restore previous key (or remove if it wasn't set before)
        if x_api_key:
            if prev_key is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = prev_key

    final_output = state.get("final_output")
    if final_output is None:
        error_msg = state.get("pipeline_error", "Pipeline failed without a specific error")
        logger.error("Pipeline returned no output for '%s': %s", source_filename, error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    return JSONResponse(content=final_output)
