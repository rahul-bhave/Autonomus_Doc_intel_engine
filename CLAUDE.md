# Autonomous Document Intel Engine — Developer Guide for Claude Code

## Project Summary
Document intelligence platform. Python keyword search is the PRIMARY classifier.
LLM (Ollama / IBM Watsonx) is FALLBACK ONLY, invoked when confidence < threshold.
Pipeline: parse → classify → validate → audit → output (LangGraph StateGraph).

## Current Sprint Status
| Sprint | What | Status |
|--------|------|--------|
| S0 | Foundation — schemas, config loader, YAML dicts, folder scaffold | ✅ DONE |
| S1 | Docling parse node | ✅ DONE |
| S2 | Python keyword classifier engine | ⬜ NEXT |
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
pydantic, pyyaml, python-dotenv, pytest, docling[rapidocr], fpdf2
NOT YET: langgraph, langchain-core, fastapi, chainlit, gradio, sqlalchemy

## Windows Workaround
- `parse.py` patches `huggingface_hub.file_download.are_symlinks_supported` → `False` on Windows
- Avoids `OSError: [WinError 1314]` symlink error without needing Developer Mode

## Sprint 2 — Next Steps
1. Implement `src/classifiers/engine.py` → `KeywordClassifier.classify(markdown, categories) -> ClassificationResult`
2. Use scoring formula: `confidence = (primary * primary_weight + secondary * secondary_weight) / (total_primary * primary_weight + total_secondary * secondary_weight)`
3. Write `tests/test_classifier.py`

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
- src/pipeline/nodes/parse.py  — parse_node() (Docling PDF→Markdown, 13 tests)
- tests/test_config.py        — 72 passing Sprint 0 tests
- tests/test_parse.py         — 13 passing Sprint 1 tests
- tests/fixtures/documents/   — 3 test PDFs (invoice, resume, contract)
