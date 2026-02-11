"""Tribal registry with lazy loading and 3-tier name resolution.

Provides the canonical list of all federally recognized Tribes loaded from
data/tribal_registry.json (built by scripts/build_registry.py). Name
resolution uses a 3-tier approach:

  Tier 1: Exact match on official name
  Tier 2: Substring match across name + alternate_names
  Tier 3: Fuzzy fallback using rapidfuzz WRatio (weighted ratio)

Usage:
    registry = TribalRegistry({})
    tribe = registry.resolve("Navajo Nation")           # Exact -> dict
    tribes = registry.resolve("Choctaw")                # Ambiguous -> list
    fuzzy = registry.resolve("Navaho")                  # Fuzzy -> list with scores
    none = registry.resolve("nonexistent xyz")           # No match -> None
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default path relative to project root
_DEFAULT_DATA_PATH = "data/tribal_registry.json"


class TribalRegistry:
    """Lazy-loaded tribal registry with 3-tier name resolution.

    Loads tribal_registry.json on first access (not at construction time)
    to avoid unnecessary I/O when the registry is not needed.

    Attributes:
        data_path: Path to the tribal_registry.json file.
    """

    def __init__(self, config: dict) -> None:
        """Initialize the registry.

        Args:
            config: Application configuration dict. Reads the data path from
                config["packets"]["tribal_registry"]["data_path"], falling
                back to "data/tribal_registry.json".
        """
        packets_cfg = config.get("packets", {})
        registry_cfg = packets_cfg.get("tribal_registry", {})
        raw_path = registry_cfg.get("data_path", _DEFAULT_DATA_PATH)
        self.data_path = Path(raw_path)

        self._tribes: list[dict] = []
        self._loaded: bool = False
        self._search_corpus: list[tuple[str, int]] | None = None

    def _load(self) -> None:
        """Lazy-load tribe data from JSON file.

        Called automatically before any data access. Subsequent calls
        are no-ops.
        """
        if self._loaded:
            return

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(
                "Tribal registry not found at %s. "
                "Run 'python scripts/build_registry.py' to generate it.",
                self.data_path,
            )
            raise
        except json.JSONDecodeError as exc:
            logger.error(
                "Tribal registry at %s contains invalid JSON: %s",
                self.data_path, exc,
            )
            raise

        self._tribes = data.get("tribes", [])
        self._loaded = True

        metadata = data.get("metadata", {})
        is_placeholder = metadata.get("placeholder", False)
        logger.info(
            "Loaded %d tribes from %s%s",
            len(self._tribes),
            self.data_path,
            " (PLACEHOLDER - run build_registry.py for full data)" if is_placeholder else "",
        )

    def resolve(self, query: str) -> dict | list[dict] | None:
        """Resolve a tribe name using 3-tier matching.

        Tier 1: Exact match on official name (case-insensitive).
        Tier 2: Substring match across name and alternate_names.
                 Returns single dict if unambiguous, list if multiple matches.
        Tier 3: Fuzzy matching via rapidfuzz WRatio with score_cutoff=60.
                 Returns list of dicts with _match_score and _matched_name.

        Args:
            query: The tribe name or partial name to search for.

        Returns:
            - dict: Single exact or unambiguous match.
            - list[dict]: Multiple matches (ambiguous substring or fuzzy results).
            - None: No matches found at any tier.
        """
        self._load()
        q = query.strip().lower()

        if not q:
            return None

        # Tier 1: Exact match on official name
        for tribe in self._tribes:
            if tribe["name"].lower() == q:
                logger.debug("Tier 1 exact match: %s", tribe["name"])
                return dict(tribe)

        # Tier 2: Substring match across name + alternate_names
        candidates: list[dict] = []
        for tribe in self._tribes:
            searchable = [tribe["name"]] + tribe.get("alternate_names", [])
            for name in searchable:
                if q in name.lower():
                    candidates.append(dict(tribe))
                    break  # Only add each tribe once

        if len(candidates) == 1:
            logger.debug("Tier 2 unambiguous substring: %s", candidates[0]["name"])
            return candidates[0]
        if candidates:
            logger.debug(
                "Tier 2 ambiguous substring: %d matches for '%s'",
                len(candidates), query,
            )
            return candidates

        # Tier 3: Fuzzy fallback (rapidfuzz)
        # Uses WRatio which automatically selects the best matching strategy
        # (partial, token set, etc.) based on input lengths. This handles
        # short queries like "Navaho" against long names like
        # "Navajo Nation, Arizona, New Mexico, & Utah" much better than
        # token_sort_ratio alone.
        try:
            from rapidfuzz import fuzz, process  # noqa: F811
        except ImportError:
            logger.warning(
                "rapidfuzz not installed -- fuzzy matching (Tier 3) unavailable. "
                "Install with: pip install rapidfuzz"
            )
            return None

        corpus = self._build_search_corpus()
        corpus_names = [entry[0] for entry in corpus]

        results = process.extract(
            q,
            corpus_names,
            scorer=fuzz.WRatio,
            limit=5,
            score_cutoff=60,
        )

        if results:
            matched: list[dict] = []
            seen_ids: set[str] = set()
            for name, score, idx in results:
                tribe_idx = corpus[idx][1]
                tribe = self._tribes[tribe_idx]
                # Deduplicate: a tribe may appear multiple times via alternate names
                if tribe["tribe_id"] not in seen_ids:
                    seen_ids.add(tribe["tribe_id"])
                    matched.append({
                        **tribe,
                        "_match_score": score,
                        "_matched_name": name,
                    })
            logger.debug(
                "Tier 3 fuzzy: %d matches for '%s' (top: %s @ %.0f%%)",
                len(matched), query,
                matched[0]["name"] if matched else "none",
                matched[0]["_match_score"] if matched else 0,
            )
            return matched

        logger.debug("No matches found for '%s' at any tier", query)
        return None

    def fuzzy_search(self, query: str, limit: int = 5) -> list[dict]:
        """Direct fuzzy search for suggestion/autocomplete purposes.

        Always uses rapidfuzz regardless of exact/substring match availability.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of tribe dicts with _match_score and _matched_name fields.
            Empty list if rapidfuzz is not installed or no matches found.
        """
        self._load()
        q = query.strip().lower()

        if not q:
            return []

        try:
            from rapidfuzz import fuzz, process  # noqa: F811
        except ImportError:
            logger.warning(
                "rapidfuzz not installed -- fuzzy search unavailable."
            )
            return []

        corpus = self._build_search_corpus()
        corpus_names = [entry[0] for entry in corpus]

        results = process.extract(
            q,
            corpus_names,
            scorer=fuzz.WRatio,
            limit=limit * 2,  # Over-fetch to account for deduplication
            score_cutoff=40,
        )

        matched: list[dict] = []
        seen_ids: set[str] = set()
        for name, score, idx in results:
            tribe_idx = corpus[idx][1]
            tribe = self._tribes[tribe_idx]
            if tribe["tribe_id"] not in seen_ids:
                seen_ids.add(tribe["tribe_id"])
                matched.append({
                    **tribe,
                    "_match_score": score,
                    "_matched_name": name,
                })
            if len(matched) >= limit:
                break

        return matched

    def get_all(self) -> list[dict]:
        """Return all tribes in the registry.

        Returns:
            List of all tribe dicts.
        """
        self._load()
        return list(self._tribes)

    def get_by_id(self, tribe_id: str) -> dict | None:
        """Look up a tribe by its tribe_id.

        Args:
            tribe_id: The tribe_id to look up (e.g., "epa_100000171").

        Returns:
            The tribe dict, or None if not found.
        """
        self._load()
        for tribe in self._tribes:
            if tribe["tribe_id"] == tribe_id:
                return dict(tribe)
        return None

    def _build_search_corpus(self) -> list[tuple[str, int]]:
        """Build the search corpus for fuzzy matching.

        Creates a list of (searchable_name, tribe_index) tuples from all
        tribe names and their alternates. Result is cached after first build.

        Returns:
            List of (name, tribe_index) tuples.
        """
        if self._search_corpus is not None:
            return self._search_corpus

        corpus: list[tuple[str, int]] = []
        for idx, tribe in enumerate(self._tribes):
            # Add current name
            corpus.append((tribe["name"], idx))
            # Add alternate names
            for alt in tribe.get("alternate_names", []):
                corpus.append((alt, idx))

        self._search_corpus = corpus
        logger.debug(
            "Built search corpus: %d entries from %d tribes",
            len(corpus), len(self._tribes),
        )
        return corpus
