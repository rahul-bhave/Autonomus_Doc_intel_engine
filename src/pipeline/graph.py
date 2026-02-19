"""
LangGraph pipeline graph definition.
Sprint: S3

Wires the pipeline stages into a stateful StateGraph:
    parse → classify → [llm_fallback if confidence < threshold] → validate → audit → output

The conditional edge between classify and llm_fallback is the core
"deterministic-first" routing logic that implements the BRD's strict precedence.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from langgraph.graph import END, StateGraph

from src.pipeline.nodes.audit import audit_node
from src.pipeline.nodes.classify import classify_node
from src.pipeline.nodes.llm import llm_fallback_node
from src.pipeline.nodes.output import output_node
from src.pipeline.nodes.parse import parse_node
from src.pipeline.nodes.validate import validate_node
from src.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def route_after_classify(state: dict[str, Any]) -> str:
    """
    Conditional routing after classification.

    Routes to llm_fallback if the keyword engine couldn't classify with
    sufficient confidence (indicated by llm_escalation_reason being set).
    Otherwise skips LLM and goes straight to validate.

    Pipeline errors also skip LLM — no point sending broken state to the API.
    """
    if state.get("pipeline_error"):
        return "validate"
    if state.get("llm_escalation_reason"):
        return "llm_fallback"
    return "validate"


def build_graph():
    """Build and compile the LangGraph pipeline."""
    sg = StateGraph(PipelineState)

    sg.add_node("parse", parse_node)
    sg.add_node("classify", classify_node)
    sg.add_node("llm_fallback", llm_fallback_node)
    sg.add_node("validate", validate_node)
    sg.add_node("audit", audit_node)
    sg.add_node("output", output_node)

    sg.set_entry_point("parse")
    sg.add_edge("parse", "classify")

    sg.add_conditional_edges(
        "classify",
        route_after_classify,
        {"llm_fallback": "llm_fallback", "validate": "validate"},
    )

    sg.add_edge("llm_fallback", "validate")
    sg.add_edge("validate", "audit")
    sg.add_edge("audit", "output")
    sg.add_edge("output", END)

    return sg.compile()


def run_pipeline(
    source_filename: str,
    file_bytes: bytes,
    document_id: str | None = None,
    source_path: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function: run the full pipeline on a document.

    Args:
        source_filename: Original filename (used for format detection).
        file_bytes: Raw document bytes.
        document_id: Optional UUID. Auto-generated if not provided.
        source_path: Optional absolute path on disk.

    Returns:
        Final pipeline state dict (includes final_output, audit_id, etc.).
    """
    graph = build_graph()
    initial_state: dict[str, Any] = {
        "source_filename": source_filename,
        "file_bytes": file_bytes,
        "document_id": document_id or str(uuid4()),
        "start_time_ms": int(time.time() * 1000),
    }
    if source_path:
        initial_state["source_path"] = source_path

    return graph.invoke(initial_state)
