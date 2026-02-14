# Test Fixtures

Place sample documents and expected extraction outputs here.

## Structure

```
tests/fixtures/
├── documents/          # Sample input files (PDF, DOCX, PPTX, images)
│   ├── invoice_digital.pdf
│   ├── invoice_scanned.pdf
│   ├── purchase_order.pdf
│   ├── contract_nda.pdf
│   ├── bank_statement.pdf
│   ├── resume_standard.pdf
│   └── report_quarterly.pdf
│
└── expected/           # Expected JSON extraction outputs (one per document)
    ├── invoice_digital.json
    ├── invoice_scanned.json
    └── ...
```

## Usage

Expected JSON files are used by `deepdiff` in the test suite to compare
actual extraction output against known-good results.

Format of each expected JSON file:
```json
{
  "document_category": "invoice",
  "classification_method": "deterministic",
  "extracted_fields": {
    "invoice_number": "INV-2025-001",
    "invoice_date": "2025-01-15",
    "total_amount": "1250.00"
  },
  "validation_status": "valid"
}
```

## Notes

- Do NOT commit documents containing real PII or confidential data.
- Use synthetic / anonymised test documents only.
- Scanned PDFs are needed to validate RapidOCR integration (Sprint 1).
