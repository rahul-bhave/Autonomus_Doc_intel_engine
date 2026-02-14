"""
YAML keyword dictionary loader with hot-reload support.

Loads the master categories.yaml index and each individual category
keyword dictionary. Re-reads files from disk when they change (mtime-based),
enabling keyword updates without restarting the service (NFR-S2).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Default path to keyword dictionaries — relative to project root
_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "keywords"


# ---------------------------------------------------------------------------
# Pydantic models for YAML config structure
# ---------------------------------------------------------------------------

class ScoringConfig(BaseModel):
    primary_weight: int = 2
    secondary_weight: int = 1
    min_primary_matches: int = 2


class RegexPattern(BaseModel):
    description: str = ""
    pattern: str
    group: int = 1


class CategoryConfig(BaseModel):
    """Parsed and validated content of one category YAML file."""

    category: str
    display_name: str
    description: str = ""
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    primary_keywords: list[str] = Field(default_factory=list)
    secondary_keywords: list[str] = Field(default_factory=list)
    exclusion_keywords: list[str] = Field(default_factory=list)
    regex_patterns: dict[str, RegexPattern] = Field(default_factory=dict)
    mandatory_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)

    @property
    def all_keywords(self) -> list[str]:
        """Combined list of primary + secondary keywords (lowercased)."""
        return [kw.lower() for kw in self.primary_keywords + self.secondary_keywords]


class CategoryIndex(BaseModel):
    """Parsed content of categories.yaml master index."""

    version: str = "1.0"
    scoring_strategy: str = "weighted_ratio"
    categories: list[dict] = Field(default_factory=list)

    def enabled_entries(self) -> list[dict]:
        return [c for c in self.categories if c.get("enabled", True)]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class KeywordConfigLoader:
    """
    Loads and caches keyword dictionaries from YAML files.

    Hot-reload: call get_categories() on each request — it re-reads
    any files whose mtime has changed since the last load.

    Usage:
        loader = KeywordConfigLoader()
        categories = loader.get_categories()
        invoice_cfg = categories["invoice"]
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = config_dir or _DEFAULT_CONFIG_DIR
        self._cache: dict[str, CategoryConfig] = {}
        self._mtimes: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_categories(self) -> dict[str, CategoryConfig]:
        """
        Return all enabled categories as {category_slug: CategoryConfig}.
        Re-reads any files changed on disk since last call.
        """
        index = self._load_index()
        result: dict[str, CategoryConfig] = {}

        for entry in index.enabled_entries():
            slug = entry["category"]
            filename = entry["file"]
            path = self._config_dir / filename

            if not path.exists():
                logger.warning("Keyword file not found, skipping: %s", path)
                continue

            if self._is_stale(path):
                cfg = self._load_category(path)
                if cfg is not None:
                    self._cache[slug] = cfg
                    self._mtimes[str(path)] = path.stat().st_mtime
                    logger.debug("Loaded keyword config: %s (%.0f keywords)",
                                 slug, len(cfg.primary_keywords) + len(cfg.secondary_keywords))

            if slug in self._cache:
                result[slug] = self._cache[slug]

        return result

    def get_category(self, slug: str) -> Optional[CategoryConfig]:
        """Return a single category config by slug, or None if not found."""
        return self.get_categories().get(slug)

    def reload_all(self) -> dict[str, CategoryConfig]:
        """Force a full reload from disk, bypassing the mtime cache."""
        self._cache.clear()
        self._mtimes.clear()
        return self.get_categories()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> CategoryIndex:
        index_path = self._config_dir / "categories.yaml"
        if not index_path.exists():
            raise FileNotFoundError(
                f"Master categories index not found: {index_path}\n"
                "Expected at config/keywords/categories.yaml"
            )
        with open(index_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return CategoryIndex(**raw)

    def _load_category(self, path: Path) -> Optional[CategoryConfig]:
        try:
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)

            # Normalise regex_patterns: YAML may store as plain dicts
            if "regex_patterns" in raw and raw["regex_patterns"]:
                raw["regex_patterns"] = {
                    k: (v if isinstance(v, dict) else {"pattern": v})
                    for k, v in raw["regex_patterns"].items()
                }

            # Normalise keyword lists to lowercase
            for key in ("primary_keywords", "secondary_keywords", "exclusion_keywords"):
                if key in raw:
                    raw[key] = [str(kw).lower() for kw in raw[key]]

            return CategoryConfig(**raw)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load keyword config %s: %s", path.name, exc)
            return None

    def _is_stale(self, path: Path) -> bool:
        """Return True if the file has changed since last load (or was never loaded)."""
        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            return False
        return self._mtimes.get(str(path), -1) != current_mtime


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly in pipeline nodes
# ---------------------------------------------------------------------------

_loader: Optional[KeywordConfigLoader] = None


def get_loader() -> KeywordConfigLoader:
    """Return the module-level singleton loader (lazy-initialised)."""
    global _loader
    if _loader is None:
        _loader = KeywordConfigLoader()
    return _loader


def load_categories() -> dict[str, CategoryConfig]:
    """Convenience function: load all enabled keyword categories."""
    return get_loader().get_categories()
