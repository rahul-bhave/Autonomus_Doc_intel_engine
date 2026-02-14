# Business Requirement Document (BRD): Autonomous Document Intel Engine

**Version:** 1.0
**Date:** 2026-02-14
**Status:** Draft

---

## Related Documents

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture diagram with layer summary and key design decisions |
| [docs/architecture.png](docs/architecture.png) | Architecture diagram — raster image (150 dpi) |
| [docs/architecture.svg](docs/architecture.svg) | Architecture diagram — vector image (scalable) |
| [docs/generate_architecture.py](docs/generate_architecture.py) | Python script to regenerate the architecture diagram (`pip install matplotlib`) |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Business Objectives](#2-business-objectives)
3. [Functional Requirements](#3-functional-requirements)
4. [UI & Presentation Requirements](#4-ui--presentation-requirements)
5. [Technical Stack](#5-technical-stack)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Data Architecture](#7-data-architecture)
8. [Integration Requirements](#8-integration-requirements)
9. [Acceptance Criteria](#9-acceptance-criteria)
10. [Out of Scope (Phase 1)](#10-out-of-scope-phase-1)

---

## 1. Project Overview

The objective is to architect a high-reliability document processing platform that bridges the gap between unstructured data and enterprise intelligence. The system uses **Docling** for layout-aware parsing, combined with a **Python-first hybrid extraction architecture**.

### Core Design Principle — Deterministic Priority

Document classification and metadata extraction rely **primarily on Python-based keyword search and rule logic**. Large Language Models (LLMs) serve exclusively as a **fallback mechanism**, invoked only when deterministic logic is insufficient. This design ensures:

- **Predictability** — classification outcomes are reproducible and inspectable
- **Auditability** — every decision traces back to a keyword match or an explicit LLM escalation reason
- **Cost control** — LLM inference is minimized, not the default path

---

## 2. Business Objectives

| # | Objective | Metric |
|---|-----------|--------|
| BO1 | Operational Efficiency | Automate ≥ 80% of document metadata extraction and categorization tasks |
| BO2 | Risk Mitigation | Minimize hallucination risk in critical fields (dates, IDs) through Python-based verification |
| BO3 | Consultancy Value | Provide a "Transparent AI" framework where stakeholders can audit the reasoning behind every automated decision |
| BO4 | Cost Control | Limit LLM invocations to < 20% of total document processing operations |

---

## 3. Functional Requirements

### 3.1 Core Requirements

| ID | Requirement | Description | Priority |
|----|-------------|-------------|----------|
| FR1 | Structural Parsing | Use Docling to convert documents into structured Markdown, preserving hierarchical relationships (tables, headers, lists). Supported input formats: PDF, DOCX, PPTX, images. For digital PDFs, text is extracted directly (no OCR). For scanned PDFs and image files, Docling's selective OCR mode is used via a configured OCR engine (RapidOCR recommended). | High |
| FR2 | Python Keyword Classification | Implement a "Deterministic First" node in LangGraph using Python keyword search, regex, and domain-specific rule sets as the **primary** mechanism for document classification and metadata extraction. | High |
| FR3 | LLM Semantic Fallback | Deploy Granite-3.0-8b-Instruct (via Watsonx/Ollama) or Llama 3.1 (via Ollama) **only** when deterministic logic fails to produce a classification at or above the configured confidence threshold. LLM invocation must be logged with an explicit escalation reason. | High |
| FR4 | Schema Validation | Use Pydantic models to validate all extracted JSON objects against defined domain schemas. Invalid extractions must be flagged with a structured error report and must never be silently passed downstream. | High |
| FR5 | Audit Trail | Maintain an append-only audit log recording: document ID, processing timestamp, extraction method (deterministic / llm_fallback), classification result, confidence score, escalation reason (if applicable), and validation outcome. | High |
| FR6 | Agentic Workflow | Manage the end-to-end process using LangGraph to ensure stateful transitions between the five pipeline stages: parse → classify → validate → log → output. | High |

### 3.2 Classification Pipeline (Strict Precedence)

```
Step 1:  Docling parses document → structured Markdown

Step 2:  Python keyword engine scans for domain keywords and patterns
          ├─ confidence ≥ threshold  →  classify + extract → Step 3
          └─ confidence < threshold  →  escalate to LLM  → Step 2b

Step 2b: LLM (Granite-3.0 / Llama 3.1) performs semantic inference
          └─ result tagged as "llm_fallback" in audit log → Step 3

Step 3:  Pydantic schema validation on all outputs (deterministic or LLM)
          ├─ valid    →  Step 4
          └─ invalid  →  flag error, write to audit log, surface in UI

Step 4:  Append-only audit log entry written

Step 5:  Output delivered to Chainlit UI / REST API response
```

> **Prerequisite:** Domain keyword dictionaries and confidence thresholds must be defined per document category before implementation of FR2 begins. See [Section 7.4](#74-document-taxonomy-prerequisites) for the required inputs.

---

## 4. UI & Presentation Requirements

Two complementary interfaces serve distinct audiences. **Both are in scope.**

### 4.1 Chainlit — Business & Stakeholder Interface

Target audience: consultants, business analysts, product stakeholders.

| Feature | Description |
|---------|-------------|
| Workflow Visualization | Real-time display of LangGraph stage execution (parse → classify → validate → log → output) |
| Reasoning Logs | Per-field extraction method label (e.g., "Date extracted via regex", "Category inferred by Granite-3.0 — no keyword match found") |
| Document Inspector | Side-by-side view of Docling-parsed Markdown and the final extracted JSON |
| Classification Transparency | Display matched keywords that triggered classification, or the LLM prompt used as fallback |
| Error Surface | Failed extractions and validation errors highlighted in real time |

### 4.2 Gradio — QE & Technical Validation Interface

Target audience: quality engineering, security, and technical review teams.

| Feature | Description |
|---------|-------------|
| Edge Case Testing | Upload arbitrary documents and observe extraction results with field-level confidence indicators |
| Keyword Rule Inspector | View active keyword dictionaries per category and per-document match scores |
| Feedback Loop | "Flag for Review" button to store problematic documents with labels for future keyword rule refinement |
| Adversarial Testing | Test system resilience against malformed, adversarial, and PII-injected document inputs (VAPT) |
| Feedback Data Export | Flagged documents and reviewer-supplied correct labels exported as JSONL for keyword dictionary review and update |

---

## 5. Technical Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Document Parsing | Docling | Layout-aware conversion of PDF/DOCX/PPTX/images to structured Markdown. Supports selective OCR (default) and full-page OCR for scanned documents. |
| OCR Engine | RapidOCR | Pluggable OCR backend used by Docling for scanned PDFs and image-only documents. Pure Python, ONNX Runtime-based — **no system binary installation required, works on Windows**. Digital PDFs with embedded text bypass OCR entirely. |
| Workflow Orchestration | LangGraph | Stateful multi-step agentic pipeline with explicit state transitions |
| Primary Classification | Python — keyword search, regex, rule engine | Deterministic document classification and metadata extraction |
| LLM Fallback | Granite-3.0-8b (IBM Watsonx) / Llama 3.1 (Ollama) | Semantic inference when Python logic is insufficient |
| Schema Validation | Pydantic | Validate extracted JSON against domain models |
| Business UI | Chainlit | Stakeholder-facing demo and reasoning transparency dashboard |
| QE UI | Gradio | Technical validation, adversarial testing, and feedback collection harness |
| Debug / Diff | DeepDiff | Development-time comparison of extraction outputs against expected fixtures |

> **OCR setup (Windows):** RapidOCR is the selected engine — pure Python, no system binaries required.
> ```bash
> pip install "docling[rapidocr]"
> ```
> This pulls in `rapidocr-onnxruntime` and `onnxruntime` only. No `.exe` installer or C compiler needed.

---

## 6. Non-Functional Requirements

### 6.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-P1 | Deterministic path processing latency | ≤ 5 seconds per page |
| NFR-P2 | LLM fallback path processing latency | ≤ 30 seconds per document |
| NFR-P3 | Batch throughput | ≥ 10 documents/minute |
| NFR-P4 | LLM invocation rate | < 20% of all processed documents |

### 6.2 Scalability

| ID | Requirement |
|----|-------------|
| NFR-S1 | Pipeline must support concurrent processing of at least 5 documents simultaneously |
| NFR-S2 | Keyword rule dictionaries must be updatable without system restart (hot-reload from YAML config) |
| NFR-S3 | New document categories must be addable by updating configuration files, not application code |

### 6.3 Reliability & Availability

| ID | Requirement |
|----|-------------|
| NFR-R1 | If the LLM service (Watsonx/Ollama) is unavailable, the system must degrade gracefully — returning deterministic-only results with an explicit "llm_unavailable" flag in the output |
| NFR-R2 | LLM calls must retry up to 2 times with exponential backoff before marking as failed |
| NFR-R3 | No document may be silently dropped — all failures must produce a structured error record in the audit log |

### 6.4 Security

| ID | Requirement |
|----|-------------|
| NFR-SEC1 | Document content must be processed in-memory and must not be written to disk beyond the defined storage layer |
| NFR-SEC2 | PII fields (names, account numbers, national IDs) detected in documents must be flagged and optionally redacted before any LLM processing |
| NFR-SEC3 | Chainlit and Gradio interfaces must require authenticated access (minimum: username/password) |
| NFR-SEC4 | LLM API credentials (Watsonx API key, etc.) must be stored in environment variables or a secrets manager — never in source code or version control |
| NFR-SEC5 | VAPT testing must be completed and sign-off obtained before production deployment |

### 6.5 Observability

| ID | Requirement |
|----|-------------|
| NFR-O1 | All LangGraph state transitions must emit structured log events with stage name, document ID, and timestamp |
| NFR-O2 | Metrics collected: documents processed (total), LLM invocation rate, validation failure rate, average processing time per stage |
| NFR-O3 | Failed extractions must be surfaced in the Chainlit dashboard in real time |

---

## 7. Data Architecture

### 7.1 Core Document Schema (Pydantic — to be extended per domain)

```python
from pydantic import BaseModel
from typing import Any, Literal, Optional
from datetime import datetime

class ExtractedDocument(BaseModel):
    document_id: str
    source_filename: str
    document_category: str                              # e.g. "Invoice", "Contract", "Report"
    classification_method: Literal["deterministic", "llm_fallback"]
    classification_confidence: float                   # 0.0 – 1.0
    matched_keywords: list[str]                        # Keywords that triggered classification
    llm_escalation_reason: Optional[str]               # Populated only when method == "llm_fallback"
    extracted_fields: dict[str, Any]                   # Domain-specific fields (defined per category)
    validation_status: Literal["valid", "invalid", "partial"]
    validation_errors: list[str]
    processed_at: datetime
```

### 7.2 Audit Log Schema

```python
class AuditEntry(BaseModel):
    audit_id: str
    document_id: str
    timestamp: datetime
    extraction_method: Literal["deterministic", "llm_fallback"]
    llm_escalation_reason: Optional[str]
    classification_result: str
    confidence_score: float
    validation_outcome: Literal["passed", "failed"]
    validation_errors: list[str]
    processing_duration_ms: int
```

> Audit log entries are **append-only and immutable** post-creation.

### 7.3 Storage Layer

| Data | Storage | Notes |
|------|---------|-------|
| Raw documents (input) | Local filesystem or S3-compatible object store | Path configured via environment variable |
| Parsed Markdown | In-memory (LangGraph state) | Not persisted unless debug mode is enabled |
| Extracted JSON | SQLite (Phase 1) / PostgreSQL (Phase 2) | Append-only; no updates to historical records |
| Audit logs | JSONL append-only log file | Must not be modifiable post-write |
| Keyword dictionaries | YAML configuration files | Version-controlled alongside source code |
| QE Feedback / Flagged documents | Local directory (JSONL + original file) | Reviewed by team to identify missing keywords; used to update YAML keyword dictionaries |

### 7.4 Document Taxonomy (Prerequisites)

The following inputs **must be delivered by the project team before Sprint 1 begins**. Implementation of FR2 is blocked until these are defined.

- [ ] Complete list of document categories in scope
- [ ] Keyword dictionary per category (primary and secondary keywords)
- [ ] Confidence threshold per category (minimum match score to classify deterministically)
- [ ] List of mandatory metadata fields per document category
- [ ] Pydantic schema per document category

---

## 8. Integration Requirements

| ID | Requirement |
|----|-------------|
| INT1 | The system must expose a REST API endpoint (`POST /process`) accepting a document file upload and returning extracted JSON |
| INT2 | Batch processing must support a local directory watch mode as the minimum; S3 event trigger is a Phase 2 enhancement |
| INT3 | The audit log must be exportable to CSV for reporting and compliance purposes |
| INT4 | Flagged documents from the Gradio feedback loop must be stored with their filename, classification result, and reviewer-supplied correct label in a structured JSONL file to support keyword dictionary updates |

---

## 9. Acceptance Criteria

| FR | Acceptance Criteria |
|----|---------------------|
| FR1 | Docling successfully parses ≥ 95% of test documents. Tables and header hierarchy are preserved in output Markdown. |
| FR2 | Python keyword engine correctly classifies ≥ 80% of documents in the defined test set without LLM invocation. All matched keywords are present in the output. |
| FR3 | LLM fallback is triggered **only** when keyword confidence is below the configured threshold. All LLM invocations include a logged escalation reason. LLM invocation rate is < 20% across the test set. |
| FR4 | All extraction outputs pass Pydantic schema validation. Invalid outputs are flagged with specific field-level errors and are never delivered to the caller as valid results. |
| FR5 | Every processed document produces exactly one audit log entry. Log entries cannot be modified or deleted after creation. |
| FR6 | LangGraph workflow completes all five pipeline stages without unhandled exceptions on 100% of test documents, including documents that trigger the error path. |

---

## 10. Out of Scope (Phase 1)

- LLM fine-tuning of any kind (Granite, Llama, or otherwise)
- Multi-language document support
- Documents exceeding 100 pages
- Integration with enterprise DMS platforms (SharePoint, Documentum, Confluence)
- Role-based access control beyond basic authentication
- Cloud deployment or Kubernetes orchestration (local / single-server only in Phase 1)
- Real-time streaming ingestion (webhook, Kafka)
