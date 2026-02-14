"""
Sprint 0 — Config loader tests.

These tests verify that all 7 keyword YAML dictionaries load cleanly
and that the Pydantic schemas are importable and instantiable.

Run:  .venv/Scripts/pytest tests/test_config.py -v
"""

import pytest
from pathlib import Path

from src.config.loader import KeywordConfigLoader, CategoryConfig, load_categories
from src.models.schemas import ExtractedDocument, AuditEntry, ClassificationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXPECTED_CATEGORIES = {
    "invoice",
    "purchase_order",
    "contract",
    "bank_statement",
    "resume",
    "report",
    "receipt",
}


@pytest.fixture(scope="module")
def loader() -> KeywordConfigLoader:
    return KeywordConfigLoader()


@pytest.fixture(scope="module")
def categories(loader: KeywordConfigLoader) -> dict[str, CategoryConfig]:
    return loader.get_categories()


# ---------------------------------------------------------------------------
# categories.yaml — master index
# ---------------------------------------------------------------------------

class TestCategoriesIndex:
    def test_all_expected_categories_loaded(self, categories):
        loaded = set(categories.keys())
        assert loaded == EXPECTED_CATEGORIES, (
            f"Missing: {EXPECTED_CATEGORIES - loaded}  |  Unexpected: {loaded - EXPECTED_CATEGORIES}"
        )

    def test_no_disabled_categories_leaked(self, categories):
        """categories.yaml marks all as enabled=true — all 7 should appear."""
        assert len(categories) == len(EXPECTED_CATEGORIES)


# ---------------------------------------------------------------------------
# Per-category YAML validation
# ---------------------------------------------------------------------------

class TestCategoryConfigs:
    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_category_loads_as_pydantic_model(self, categories, slug):
        cfg = categories[slug]
        assert isinstance(cfg, CategoryConfig), f"{slug} did not load as CategoryConfig"

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_has_primary_keywords(self, categories, slug):
        cfg = categories[slug]
        assert len(cfg.primary_keywords) >= 5, (
            f"{slug}: expected >= 5 primary keywords, got {len(cfg.primary_keywords)}"
        )

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_has_secondary_keywords(self, categories, slug):
        cfg = categories[slug]
        assert len(cfg.secondary_keywords) >= 5, (
            f"{slug}: expected >= 5 secondary keywords, got {len(cfg.secondary_keywords)}"
        )

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_confidence_threshold_in_valid_range(self, categories, slug):
        cfg = categories[slug]
        assert 0.0 < cfg.confidence_threshold < 1.0, (
            f"{slug}: confidence_threshold must be in (0, 1), got {cfg.confidence_threshold}"
        )

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_has_mandatory_fields(self, categories, slug):
        cfg = categories[slug]
        assert len(cfg.mandatory_fields) >= 1, (
            f"{slug}: must define at least 1 mandatory_field"
        )

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_has_regex_patterns(self, categories, slug):
        cfg = categories[slug]
        assert len(cfg.regex_patterns) >= 1, (
            f"{slug}: must define at least 1 regex_pattern"
        )

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_mandatory_fields_have_regex_patterns(self, categories, slug):
        """Every mandatory_field should have a corresponding regex_pattern to extract it."""
        cfg = categories[slug]
        missing = [f for f in cfg.mandatory_fields if f not in cfg.regex_patterns]
        assert not missing, (
            f"{slug}: mandatory fields lack regex patterns: {missing}"
        )

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_keywords_are_lowercase(self, categories, slug):
        """Loader normalises all keywords to lowercase."""
        cfg = categories[slug]
        for kw in cfg.primary_keywords + cfg.secondary_keywords:
            assert kw == kw.lower(), f"{slug}: keyword not lowercased: '{kw}'"

    @pytest.mark.parametrize("slug", sorted(EXPECTED_CATEGORIES))
    def test_min_primary_matches_lte_primary_count(self, categories, slug):
        cfg = categories[slug]
        assert cfg.scoring.min_primary_matches <= len(cfg.primary_keywords), (
            f"{slug}: min_primary_matches ({cfg.scoring.min_primary_matches}) "
            f"> total primary keywords ({len(cfg.primary_keywords)})"
        )


# ---------------------------------------------------------------------------
# Hot-reload: force reload returns same data
# ---------------------------------------------------------------------------

class TestHotReload:
    def test_reload_all_returns_same_categories(self, loader):
        first = set(loader.get_categories().keys())
        second = set(loader.reload_all().keys())
        assert first == second

    def test_get_category_by_slug(self, loader):
        cfg = loader.get_category("invoice")
        assert cfg is not None
        assert cfg.category == "invoice"

    def test_get_nonexistent_category_returns_none(self, loader):
        assert loader.get_category("nonexistent_xyz") is None


# ---------------------------------------------------------------------------
# Pydantic schema imports and basic instantiation
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_classification_result_instantiates(self):
        result = ClassificationResult(
            category="invoice",
            confidence=0.82,
            method="deterministic",
            matched_keywords=["invoice", "invoice number", "total amount"],
        )
        assert result.confidence == 0.82
        assert result.method == "deterministic"

    def test_extracted_document_instantiates(self):
        doc = ExtractedDocument(
            source_filename="test_invoice.pdf",
            document_category="invoice",
            classification_method="deterministic",
            classification_confidence=0.82,
            matched_keywords=["invoice", "total amount"],
            extracted_fields={"invoice_number": "INV-001", "total_amount": "500.00"},
            validation_status="valid",
        )
        assert doc.document_category == "invoice"
        assert doc.validation_status == "valid"
        assert doc.document_id  # UUID auto-generated

    def test_audit_entry_from_extracted(self):
        doc = ExtractedDocument(
            source_filename="test.pdf",
            document_category="contract",
            classification_method="llm_fallback",
            classification_confidence=0.61,
            llm_escalation_reason="Keyword confidence 0.41 below threshold 0.55",
            extracted_fields={},
            validation_status="partial",
            validation_errors=["effective_date: field not found"],
            processing_duration_ms=4200,
        )
        audit = AuditEntry.from_extracted(doc)
        assert audit.document_id == doc.document_id
        assert audit.extraction_method == "llm_fallback"
        assert audit.validation_outcome == "partial"
        assert audit.processing_duration_ms == 4200

    def test_confidence_rounded_to_4dp(self):
        doc = ExtractedDocument(
            source_filename="x.pdf",
            document_category="receipt",
            classification_method="deterministic",
            classification_confidence=0.7777777,
            validation_status="valid",
        )
        assert doc.classification_confidence == 0.7778
