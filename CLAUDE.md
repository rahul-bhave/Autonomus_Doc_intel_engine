# Autonomous Document Intel Engine — Developer Guide for Claude Code

## Project Summary
Document intelligence platform. Python keyword search is the PRIMARY classifier.
LLM (Anthropic Claude API) is FALLBACK ONLY, invoked when confidence < threshold.
Pipeline: parse → classify → validate → audit → output (LangGraph StateGraph).

## Current Sprint Status
| Sprint | What | Status |
|--------|------|--------|
| S0 | Foundation — schemas, config loader, YAML dicts, folder scaffold | ✅ DONE |
| S1 | Docling parse node | ✅ DONE |
| S2 | Python keyword classifier engine | ✅ DONE |
| S3 | LangGraph pipeline wiring | ✅ DONE |
| S4 | Pydantic validation + audit log nodes | ⬜ NEXT |
| S5 | FastAPI REST API | ⬜ |
| S6 | LLM fallback (Anthropic Claude API) | ✅ DONE |
| S7 | Chainlit UI (doc upload + API key input + pipeline visualization) | ⬜ |
| S8 | Gradio QE UI (doc upload + API key input + feedback loop) | ⬜ |

## Environment
- Python 3.12.8, .venv at project root
- Windows — use `.venv/Scripts/` not `.venv/bin/`
- Run tests: `PYTHONPATH=. .venv/Scripts/pytest tests/ -v`
- No binary installations allowed (OCR = RapidOCR, pure Python)

## Installed in .venv
pydantic, pyyaml, python-dotenv, pytest, docling[rapidocr], fpdf2, filetype, watchdog, anthropic, langgraph, langchain-core
NOT YET: fastapi, chainlit, gradio, sqlalchemy

## Windows Workaround
- `parse.py` patches `huggingface_hub.file_download.are_symlinks_supported` → `False` on Windows
- Avoids `OSError: [WinError 1314]` symlink error without needing Developer Mode

## Sprint 4 — Next Steps
1. Implement `validate_node` — mandatory_fields check + Pydantic validation per category
2. Implement `audit_node` — append-only JSONL writer using AuditEntry schema
3. Write `tests/test_validate.py` and `tests/test_audit.py`

## Key Architecture Rules
- parse_node: 3-layer file validation (blocked extensions → known-good → magic-byte MIME detection via `filetype`) then Docling converts bytes → Markdown string (in-memory, not persisted unless DEBUG_PERSIST_MARKDOWN=true)
- classify_node: runs KeywordClassifier; if confidence < threshold sets llm_escalation_reason
- llm_fallback_node: Anthropic Claude API (Haiku), 2 retries with exponential backoff; sets llm_unavailable on failure. API key from state["api_key"] (UI) or env fallback (Sprint 7 will refactor)
- validate_node: checks mandatory_fields presence + Pydantic validation; never silently passes invalid
- audit_node: append-only JSONL write (logs/audit.jsonl); every document gets exactly one entry

## UI Design Decisions (Sprint 7/8)
- **No secrets in .env**: API keys and auth credentials are NEVER stored in .env or on disk. All entered via UI at runtime (session-only).
- **Anthropic API Key**: Input field in both Chainlit and Gradio UIs. Session-only, passed to pipeline at invocation time.
- **Authentication**: Login form in both UIs. Credentials managed via UI, not environment variables.
- **Document Upload**: Both UIs allow direct file upload (drag-and-drop). Feeds into the same pipeline as REST API and directory watcher.
- **Chainlit (S7)**: Stakeholder dashboard — login, enter API key, upload doc, real-time pipeline stages, classification transparency, reasoning logs
- **Gradio (S8)**: QE harness — login, enter API key, upload doc, edge-case testing, keyword rule inspector, "Flag for Review" feedback loop

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
- src/pipeline/nodes/parse.py  — parse_node() (Docling PDF→Markdown + file validation + metadata extraction)
- src/pipeline/nodes/classify.py — classify_node() (KeywordClassifier wiring + field extraction)
- src/pipeline/nodes/llm.py   — llm_fallback_node() (Anthropic Claude API, retry + graceful degradation)
- src/pipeline/nodes/validate.py — validate_node() (pass-through stub, full in S4)
- src/pipeline/nodes/audit.py — audit_node() (pass-through stub, full in S4)
- src/pipeline/nodes/output.py — output_node() (assembles final ExtractedDocument dict)
- src/pipeline/graph.py       — build_graph(), run_pipeline(), route_after_classify()
- src/metadata/extractor.py   — extract_metadata() (filesystem + PDF/DOCX/PPTX internal metadata)
- src/watcher.py              — DirectoryWatcher (watchdog, monitors data/input/)
- src/classifiers/engine.py   — KeywordClassifier (deterministic scoring, 27 tests)
- tests/test_config.py        — 72 passing Sprint 0 tests
- tests/test_parse.py         — 31 passing tests (13 parse + 18 file validation)
- tests/test_classifier.py    — 27 passing Sprint 2 tests
- tests/test_pipeline.py      — 22 passing Sprint 3 tests (graph, routing, classify, e2e)
- tests/fixtures/documents/   — 3 test PDFs (invoice, resume, contract)
- .github/workflows/ci.yml    — GitHub Actions CI pipeline
- .claude/commands/            — 4 custom slash commands
