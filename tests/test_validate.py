"""
Sprint 4 — validate_node Tests

Tests the full S4 implementation of validate_node:
  - valid   → all mandatory_fields present and non-empty
  - partial → one or more mandatory_fields missing or empty
  - invalid → pipeline_error propagated from upstream

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_validate.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.nodes.validate import validate_node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_category_cfg(mandatory_fields: list[str]):
    """Return a mock CategoryConfig with the given mandatory_fields."""
    cfg = MagicMock()
    cfg.mandatory_fields = mandatory_fields
    return cfg


# ---------------------------------------------------------------------------
# Pipeline error propagation
# ---------------------------------------------------------------------------


class TestPipelineErrorPropagation:
    """validate_node must short-circuit to 'invalid' when pipeline_error is set."""

    def test_invalid_on_pipeline_error(self):
        state = {"pipeline_error": "Parse failed: corrupt PDF"}
        result = validate_node(state)
        assert result["validation_status"] == "invalid"

    def test_error_message_propagated(self):
        state = {"pipeline_error": "Blocked file extension: .exe"}
        result = validate_node(state)
        assert "Blocked file extension: .exe" in result["validation_errors"]

    def test_no_category_lookup_on_pipeline_error(self):
        """Loader must NOT be called when pipeline_error is present."""
        state = {"pipeline_error": "boom", "document_category": "invoice"}
        with patch("src.pipeline.nodes.validate.get_loader") as mock_loader:
            validate_node(state)
            mock_loader.assert_not_called()


# ---------------------------------------------------------------------------
# Unclassified documents
# ---------------------------------------------------------------------------


class TestUnclassifiedDocuments:
    """Unclassified docs have no schema → always valid, no loader call."""

    def test_unclassified_returns_valid(self):
        state = {"document_category": "unclassified", "extracted_fields": {}}
        result = validate_node(state)
        assert result["validation_status"] == "valid"
        assert result["validation_errors"] == []

    def test_unclassified_no_loader_call(self):
        state = {"document_category": "unclassified", "extracted_fields": {}}
        with patch("src.pipeline.nodes.validate.get_loader") as mock_loader:
            validate_node(state)
            mock_loader.assert_not_called()

    def test_missing_category_defaults_to_unclassified(self):
        """State without document_category key should behave like unclassified."""
        state = {"extracted_fields": {}}
        result = validate_node(state)
        assert result["validation_status"] == "valid"


# ---------------------------------------------------------------------------
# Valid documents — all mandatory fields present
# ---------------------------------------------------------------------------


class TestValidDocuments:
    """validate_node returns 'valid' when all mandatory_fields are present."""

    def test_invoice_all_mandatory_fields_present(self):
        state = {
            "document_category": "invoice",
            "extracted_fields": {
                "invoice_number": "INV-001",
                "invoice_date": "2024-03-15",
                "total_amount": "962.50",
            },
        }
        result = validate_node(state)
        assert result["validation_status"] == "valid"
        assert result["validation_errors"] == []

    def test_extra_optional_fields_do_not_affect_validity(self):
        state = {
            "document_category": "invoice",
            "extracted_fields": {
                "invoice_number": "INV-001",
                "invoice_date": "2024-03-15",
                "total_amount": "962.50",
                "due_date": "2024-04-15",      # optional
                "vendor_name": "Acme Corp",    # optional
            },
        }
        result = validate_node(state)
        assert result["validation_status"] == "valid"

    def test_category_with_no_mandatory_fields_is_valid(self):
        """A category with an empty mandatory_fields list → always valid."""
        mock_cfg = _make_category_cfg([])
        with patch("src.pipeline.nodes.validate.get_loader") as mock_loader:
            mock_loader.return_value.get_categories.return_value = {"report": mock_cfg}
            state = {
                "document_category": "report",
                "extracted_fields": {},
            }
            result = validate_node(state)
        assert result["validation_status"] == "valid"
        assert result["validation_errors"] == []

    def test_unknown_category_slug_treated_as_valid(self):
        """If a category slug isn't in the loaded YAML, skip and return valid."""
        with patch("src.pipeline.nodes.validate.get_loader") as mock_loader:
            mock_loader.return_value.get_categories.return_value = {}  # empty registry
            state = {
                "document_category": "nonexistent_category",
                "extracted_fields": {},
            }
            result = validate_node(state)
        assert result["validation_status"] == "valid"


# ---------------------------------------------------------------------------
# Partial documents — some mandatory fields missing
# ---------------------------------------------------------------------------


class TestPartialDocuments:
    """validate_node returns 'partial' when mandatory_fields are absent or empty."""

    def test_all_mandatory_fields_missing(self):
        state = {
            "document_category": "invoice",
            "extracted_fields": {},
        }
        result = validate_node(state)
        assert result["validation_status"] == "partial"
        assert len(result["validation_errors"]) == 3  # invoice has 3 mandatory fields

    def test_one_mandatory_field_missing(self):
        state = {
            "document_category": "invoice",
            "extracted_fields": {
                "invoice_number": "INV-001",
                "invoice_date": "2024-03-15",
                # total_amount is missing
            },
        }
        result = validate_node(state)
        assert result["validation_status"] == "partial"
        assert any("total_amount" in e for e in result["validation_errors"])

    def test_empty_string_field_treated_as_missing(self):
        """An extracted field with an empty string is treated as absent."""
        state = {
            "document_category": "invoice",
            "extracted_fields": {
                "invoice_number": "",           # empty → treated as missing
                "invoice_date": "2024-03-15",
                "total_amount": "962.50",
            },
        }
        result = validate_node(state)
        assert result["validation_status"] == "partial"
        assert any("invoice_number" in e for e in result["validation_errors"])

    def test_whitespace_only_field_treated_as_missing(self):
        """A field with only whitespace is treated as absent."""
        state = {
            "document_category": "invoice",
            "extracted_fields": {
                "invoice_number": "   ",        # whitespace only → missing
                "invoice_date": "2024-03-15",
                "total_amount": "962.50",
            },
        }
        result = validate_node(state)
        assert result["validation_status"] == "partial"
        assert any("invoice_number" in e for e in result["validation_errors"])

    def test_none_value_field_treated_as_missing(self):
        """A field explicitly set to None is treated as absent."""
        state = {
            "document_category": "invoice",
            "extracted_fields": {
                "invoice_number": None,
                "invoice_date": "2024-03-15",
                "total_amount": "962.50",
            },
        }
        result = validate_node(state)
        assert result["validation_status"] == "partial"

    def test_error_messages_name_missing_fields(self):
        """Each missing field should be named in the validation_errors list."""
        state = {
            "document_category": "invoice",
            "extracted_fields": {"invoice_number": "INV-001"},
        }
        result = validate_node(state)
        assert result["validation_status"] == "partial"
        error_text = " ".join(result["validation_errors"])
        assert "invoice_date" in error_text
        assert "total_amount" in error_text

    def test_partial_with_mock_category(self):
        """Verify partial logic works with a custom mandatory_fields list."""
        mock_cfg = _make_category_cfg(["field_a", "field_b", "field_c"])
        with patch("src.pipeline.nodes.validate.get_loader") as mock_loader:
            mock_loader.return_value.get_categories.return_value = {"custom": mock_cfg}
            state = {
                "document_category": "custom",
                "extracted_fields": {"field_a": "present"},
            }
            result = validate_node(state)
        assert result["validation_status"] == "partial"
        error_text = " ".join(result["validation_errors"])
        assert "field_b" in error_text
        assert "field_c" in error_text


# ---------------------------------------------------------------------------
# All supported real categories — smoke tests
# ---------------------------------------------------------------------------


class TestRealCategories:
    """Smoke tests against the real YAML keyword configs loaded from disk."""

    @pytest.mark.parametrize("category", [
        "invoice", "contract", "resume", "purchase_order",
        "bank_statement", "receipt", "report",
    ])
    def test_category_loads_without_error(self, category):
        """Each real category should be loadable and validate without crashing."""
        state = {
            "document_category": category,
            "extracted_fields": {},  # all mandatory fields will be missing → partial or valid
        }
        result = validate_node(state)
        assert result["validation_status"] in ("valid", "partial")
        assert isinstance(result["validation_errors"], list)

    @pytest.mark.parametrize("category", [
        "invoice", "contract", "resume", "purchase_order",
        "bank_statement", "receipt", "report",
    ])
    def test_empty_fields_never_silently_valid_when_mandatory_exist(self, category):
        """Categories with mandatory_fields must return partial, not valid, for empty fields."""
        from src.config.loader import load_categories
        categories = load_categories()
        cfg = categories.get(category)
        if cfg is None or not cfg.mandatory_fields:
            pytest.skip(f"Category '{category}' has no mandatory_fields — nothing to test")

        state = {
            "document_category": category,
            "extracted_fields": {},
        }
        result = validate_node(state)
        assert result["validation_status"] == "partial", (
            f"Expected 'partial' for {category} with empty fields, got {result['validation_status']}"
        )


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------


class TestErrorResilience:
    """validate_node must not crash the pipeline on unexpected errors."""

    def test_loader_exception_returns_invalid(self):
        """If the config loader raises, validate_node returns 'invalid'."""
        with patch("src.pipeline.nodes.validate.get_loader") as mock_loader:
            mock_loader.side_effect = RuntimeError("disk read error")
            state = {
                "document_category": "invoice",
                "extracted_fields": {},
            }
            result = validate_node(state)
        assert result["validation_status"] == "invalid"
        assert len(result["validation_errors"]) > 0

    def test_invalid_errors_are_strings(self):
        """validation_errors must always be a list of strings."""
        state = {"pipeline_error": "Something bad"}
        result = validate_node(state)
        assert all(isinstance(e, str) for e in result["validation_errors"])
