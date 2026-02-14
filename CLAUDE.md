# Autonomous Document Intel Engine — Developer Guide for Claude Code

## Project Summary
Document intelligence platform. Python keyword search is the PRIMARY classifier.
LLM (Ollama / IBM Watsonx) is FALLBACK ONLY, invoked when confidence < threshold.
Pipeline: parse → classify → validate → audit → output (LangGraph StateGraph).

## Current Sprint Status
| Sprint | What | Status |
|--------|------|--------|
| S0 | Foundation — schemas, config loader, YAML dicts, folder scaffold | ✅ DONE |
| S1 | Docling parse node | ⬜ NEXT |
| S2 | Python keyword classifier engine | ⬜ |
| S3 | LangGraph pipeline wiring | ⬜ |
| S4 | Pydantic validation + audit log nodes | ⬜ |
| S5 | FastAPI REST API | ⬜ |
| S6 | LLM fallback (Ollama → Watsonx) | ⬜ |
| S7 | Chainlit UI | ⬜ |
| S8 | Gradio QE UI + feedback loop | ⬜ |

## Environment
- Python 3.12.8, .venv at project root
- Windows — use `.venv/Scripts/` not `.venv/bin/`
- Run tests: `PYTHONPATH=. .venv/Scripts/pytest tests/ -v`
- No binary installations allowed (OCR = RapidOCR, pure Python)

## Installed in .venv
pydantic, pyyaml, python-dotenv, pytest
NOT YET: docling, langgraph, langchain-core, fastapi, chainlit, gradio, sqlalchemy

## Sprint 1 — Next Steps
1. `pip install "docling[rapidocr]"` (large install, ~500 MB)
2. Implement `src/pipeline/nodes/parse.py` → `parse_node(state) -> dict`
   - Input:  `state["file_bytes"]`, `state["source_filename"]`
   - Output: `state["parsed_markdown"]` (success) or `state["parse_error"]` (failure)
3. Write `tests/test_parse.py` with a real PDF in `tests/fixtures/documents/`

## Key Architecture Rules
- parse_node: Docling converts bytes → Markdown string (in-memory, not persisted unless DEBUG_PERSIST_MARKDOWN=true)
- classify_node: runs KeywordClassifier; if confidence < threshold sets llm_escalation_reason
- llm_fallback_node: Ollama first, Watsonx second, 2 retries with backoff; sets llm_unavailable on failure
- validate_node: checks mandatory_fields presence + Pydantic validation; never silently passes invalid
- audit_node: append-only JSONL write (logs/audit.jsonl); every document gets exactly one entry

## File Map
- src/models/schemas.py       — ExtractedDocument, AuditEntry, ClassificationResult, FeedbackRecord
- src/config/loader.py        — KeywordConfigLoader (hot-reload), load_categories()
- src/pipeline/state.py       — PipelineState TypedDict
- config/keywords/            — 7 YAML keyword dicts + categories.yaml index
- tests/test_config.py        — 72 passing Sprint 0 tests
