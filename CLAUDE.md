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
| S2 | Python keyword classifier engine | ✅ DONE |
| S3 | LangGraph pipeline wiring | ⬜ NEXT |
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
pydantic, pyyaml, python-dotenv, pytest, docling[rapidocr], fpdf2, filetype
NOT YET: langgraph, langchain-core, fastapi, chainlit, gradio, sqlalchemy

## Windows Workaround
- `parse.py` patches `huggingface_hub.file_download.are_symlinks_supported` → `False` on Windows
- Avoids `OSError: [WinError 1314]` symlink error without needing Developer Mode

## Sprint 3 — Next Steps
1. Install `langgraph` and `langchain-core` into .venv
2. Wire LangGraph StateGraph: parse → classify → (conditional) llm_fallback → validate → audit
3. Implement `src/pipeline/nodes/classify.py` — classify_node wrapping KeywordClassifier
4. Write `tests/test_pipeline.py` — end-to-end pipeline tests

## Key Architecture Rules
- parse_node: 3-layer file validation (blocked extensions → known-good → magic-byte MIME detection via `filetype`) then Docling converts bytes → Markdown string (in-memory, not persisted unless DEBUG_PERSIST_MARKDOWN=true)
- classify_node: runs KeywordClassifier; if confidence < threshold sets llm_escalation_reason
- llm_fallback_node: Ollama first, Watsonx second, 2 retries with backoff; sets llm_unavailable on failure
- validate_node: checks mandatory_fields presence + Pydantic validation; never silently passes invalid
- audit_node: append-only JSONL write (logs/audit.jsonl); every document gets exactly one entry

## CI/CD
- GitHub Actions: `.github/workflows/ci.yml`
- Triggers on push to `main` + PRs to `main`
- Runs on `ubuntu-latest`, Python 3.12, caches pip + HuggingFace models
- Command: `PYTHONPATH=. pytest tests/ -v`

## Custom Commands (`.claude/commands/`)
| Command | File | Purpose |
|---------|------|---------|
| `/project:run-tests` | `run-tests.md` | Run pytest locally, report pass/fail |
| `/project:update-deps` | `update-deps.md` | Sync requirements files after new installs |
| `/project:sprint-finish` | `sprint-finish.md` | End-of-sprint checklist (tests, docs, deps) |
| `/project:ci-check` | `ci-check.md` | Check GitHub Actions CI status |

## File Map
- src/models/schemas.py       — ExtractedDocument, AuditEntry, ClassificationResult, FeedbackRecord
- src/config/loader.py        — KeywordConfigLoader (hot-reload), load_categories()
- src/pipeline/state.py       — PipelineState TypedDict
- config/keywords/            — 7 YAML keyword dicts + categories.yaml index
- src/pipeline/nodes/parse.py  — parse_node() (Docling PDF→Markdown + file validation, 31 tests)
- src/classifiers/engine.py   — KeywordClassifier (deterministic scoring, 27 tests)
- tests/test_config.py        — 72 passing Sprint 0 tests
- tests/test_parse.py         — 31 passing tests (13 parse + 18 file validation)
- tests/test_classifier.py    — 27 passing Sprint 2 tests
- tests/fixtures/documents/   — 3 test PDFs (invoice, resume, contract)
- .github/workflows/ci.yml    — GitHub Actions CI pipeline
- .claude/commands/            — 4 custom slash commands
