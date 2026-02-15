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
import re
from typing import Optional

from src.config.loader import CategoryConfig, KeywordConfigLoader, get_loader
from src.models.schemas import ClassificationResult

logger = logging.getLogger(__name__)

_EXCLUSION_PENALTY = 0.30


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
        """
        categories = self._loader.get_categories()
        text_lower = text.lower()

        best_slug: str | None = None
        best_confidence = 0.0
        best_matched: list[str] = []
        best_threshold = 0.0

        for slug, cfg in categories.items():
            confidence, matched = self._score_category(text_lower, cfg)
            logger.debug(
                "Category %s: confidence=%.4f threshold=%.2f matched=%d keywords",
                slug, confidence, cfg.confidence_threshold, len(matched),
            )
            if confidence > best_confidence:
                best_slug = slug
                best_confidence = confidence
                best_matched = matched
                best_threshold = cfg.confidence_threshold

        if best_slug is not None and best_confidence >= best_threshold:
            return ClassificationResult(
                category=best_slug,
                confidence=best_confidence,
                method="deterministic",
                matched_keywords=best_matched,
            )

        # No category exceeded its threshold → escalate
        if best_slug is not None:
            reason = (
                f"Best match '{best_slug}' scored {best_confidence:.4f} "
                f"but threshold is {best_threshold:.2f}"
            )
        else:
            reason = "No categories available for scoring"

        return ClassificationResult(
            category="unclassified",
            confidence=best_confidence,
            method="unclassified",
            matched_keywords=best_matched,
            escalation_reason=reason,
        )

    def extract_fields(self, text: str, category_cfg: CategoryConfig) -> dict[str, str]:
        """
        Run regex patterns for the winning category against the document text.
        Returns {field_name: extracted_value} for all matched patterns.
        """
        extracted: dict[str, str] = {}
        for field_name, rp in category_cfg.regex_patterns.items():
            match = re.search(rp.pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = match.group(rp.group).strip()
                except (IndexError, AttributeError):
                    continue
                if value:
                    extracted[field_name] = value
        return extracted

    def _score_category(
        self,
        text_lower: str,
        cfg: CategoryConfig,
    ) -> tuple[float, list[str]]:
        """
        Compute confidence score for one category.
        Returns (confidence, matched_keywords).
        """
        matched: list[str] = []

        # Count primary keyword matches
        primary_count = 0
        for kw in cfg.primary_keywords:
            if kw in text_lower:
                primary_count += 1
                matched.append(kw)

        # Hard guard: minimum primary matches
        if primary_count < cfg.scoring.min_primary_matches:
            return 0.0, []

        # Count secondary keyword matches
        secondary_count = 0
        for kw in cfg.secondary_keywords:
            if kw in text_lower:
                secondary_count += 1
                matched.append(kw)

        # Weighted score
        pw = cfg.scoring.primary_weight
        sw = cfg.scoring.secondary_weight
        raw_score = (primary_count * pw) + (secondary_count * sw)
        max_score = (len(cfg.primary_keywords) * pw) + (len(cfg.secondary_keywords) * sw)

        if max_score == 0:
            return 0.0, matched

        confidence = raw_score / max_score

        # Exclusion penalty
        for kw in cfg.exclusion_keywords:
            if kw in text_lower:
                logger.debug("Exclusion keyword '%s' found for category '%s'", kw, cfg.category)
                confidence *= _EXCLUSION_PENALTY
                break

        return confidence, matched
