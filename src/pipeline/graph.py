"""
LangGraph pipeline graph definition.
Sprint: S3

Wires the five pipeline stages into a stateful StateGraph:
    parse → classify → [llm_fallback if confidence < threshold] → validate → audit → output

The conditional edge between classify and llm_fallback is the core
"deterministic-first" routing logic that implements the BRD's strict precedence.

Implemented in Sprint 3.
"""

from __future__ import annotations

# TODO (Sprint 3): implement StateGraph with conditional LLM routing
# from langgraph.graph import StateGraph, END
# from src.pipeline.state import PipelineState
# from src.pipeline.nodes.parse import parse_node
# from src.pipeline.nodes.classify import classify_node
# from src.pipeline.nodes.llm import llm_fallback_node
# from src.pipeline.nodes.validate import validate_node
# from src.pipeline.nodes.audit import audit_node


def build_graph():
    """Build and compile the LangGraph pipeline. Implemented in Sprint 3."""
    raise NotImplementedError("build_graph — implement in Sprint 3")
