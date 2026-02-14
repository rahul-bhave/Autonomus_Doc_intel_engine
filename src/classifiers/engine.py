"""
Python Keyword Classifier Engine
Sprint: S2

Implements the "Deterministic First" classification strategy.

Scoring algorithm:
    raw_score  = (primary_matches * primary_weight) + (secondary_matches * secondary_weight)
    max_score  = (total_primary * primary_weight) + (total_secondary * secondary_weight)
    confidence = raw_score / max_score

    Exclusion penalty:
        If any exclusion_keyword found in document text → confidence *= 0.30

    Minimum primary guard:
        If primary_matches < min_primary_matches → confidence = 0.0 (hard disqualification)

The category with the highest confidence above its threshold wins.
If no category exceeds its threshold → escalation_reason is set and LLM is invoked.

Implemented in Sprint 2.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.config.loader import CategoryConfig, KeywordConfigLoader, get_loader
from src.models.schemas import ClassificationResult

logger = logging.getLogger(__name__)


class KeywordClassifier:
    """
    Deterministic document classifier using keyword scoring.

    Usage:
        classifier = KeywordClassifier()
        result = classifier.classify(markdown_text)
        if result.confidence >= threshold:
            # use result
        else:
            # escalate to LLM
    """

    def __init__(self, loader: Optional[KeywordConfigLoader] = None) -> None:
        self._loader = loader or get_loader()

    def classify(self, text: str) -> ClassificationResult:
        """
        Score the document text against all enabled keyword dictionaries.
        Returns the best match (highest confidence above threshold), or
        an 'unclassified' result with an escalation reason if no category wins.

        Implemented in Sprint 2.
        """
        # TODO (Sprint 2): implement scoring loop across all categories
        raise NotImplementedError("KeywordClassifier.classify — implement in Sprint 2")

    def extract_fields(self, text: str, category_cfg: CategoryConfig) -> dict[str, str]:
        """
        Run regex patterns for the winning category against the document text.
        Returns {field_name: extracted_value} for all matched patterns.

        Implemented in Sprint 2.
        """
        # TODO (Sprint 2): implement regex extraction loop
        raise NotImplementedError("KeywordClassifier.extract_fields — implement in Sprint 2")

    def _score_category(
        self,
        text_lower: str,
        cfg: CategoryConfig,
    ) -> tuple[float, list[str]]:
        """
        Compute confidence score for one category.
        Returns (confidence, matched_keywords).

        Implemented in Sprint 2.
        """
        # TODO (Sprint 2): implement weighted scoring
        raise NotImplementedError("KeywordClassifier._score_category — implement in Sprint 2")
