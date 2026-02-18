"""Tribal award matching pipeline with two-tier name resolution and per-Tribe caching.

Provides the TribalAwardMatcher class that:
  1. Fetches all Tribal government awards from USASpending via batch queries
  2. Matches awards to specific Tribes using a two-tier approach:
     - Tier 1: Curated alias table lookup (O(1), exact match)
     - Tier 2: rapidfuzz token_sort_ratio >= 85 with state-overlap validation
  3. Deduplicates awards by Award ID (multi-year awards span FY queries)
  4. Detects consortium/inter-Tribal awards (logged, not attributed)
  5. Writes per-Tribe JSON cache files with year-by-year obligation breakdowns

Usage:
    matcher = TribalAwardMatcher(config)
    # With live API:
    result = asyncio.run(matcher.run(scraper))
    # Or match pre-fetched data:
    matched = matcher.match_all_awards(awards_by_cfda)
    count = matcher.write_cache(matched)
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from src.config import FISCAL_YEAR_INT
from src.packets.registry import TribalRegistry
from src.paths import AWARD_CACHE_DIR, PROJECT_ROOT, TRIBAL_ALIASES_PATH
from src.scrapers.usaspending import CFDA_TO_PROGRAM

logger = logging.getLogger(__name__)


# Patterns that indicate a consortium or inter-Tribal organization
# (not attributable to a single Tribe).
_CONSORTIUM_PATTERNS = [
    "inter tribal", "intertribal", "inter-tribal",
    "consortium", "council of", "united tribes",
    "indian health board", "tribal council inc",
    "association of", "united south and eastern",
]


def _is_consortium(recipient_name: str) -> bool:
    """Check if a recipient name matches a consortium/inter-Tribal pattern.

    Consortium awards are logged separately and not attributed to individual
    Tribes, per the Phase 12 CONTEXT decision.

    Args:
        recipient_name: Raw recipient name from USASpending.

    Returns:
        True if the name matches a known consortium pattern.
    """
    lowered = recipient_name.lower()
    return any(pattern in lowered for pattern in _CONSORTIUM_PATTERNS)


def _determine_award_fy(award: dict) -> int | None:
    """Determine the federal fiscal year for an award.

    Uses the ``_fiscal_year`` field if present (set by the scraper), otherwise
    parses ``start_date`` (format "YYYY-MM-DD") using the October 1 boundary:
    month >= 10 means the next calendar year's FY.

    Args:
        award: Normalized award dict.

    Returns:
        Fiscal year as 4-digit int, or None if undeterminable.
    """
    if "_fiscal_year" in award:
        return award["_fiscal_year"]

    start_date = award.get("start_date", "")
    if not start_date or not isinstance(start_date, str):
        return None

    try:
        parts = start_date.split("-")
        year = int(parts[0])
        month = int(parts[1])
        return year + 1 if month >= 10 else year
    except (IndexError, ValueError):
        return None


class TribalAwardMatcher:
    """Two-tier award-to-Tribe matching with per-Tribe cache writes.

    Tier 1: Curated alias table (O(1) dict lookup)
    Tier 2: rapidfuzz token_sort_ratio >= 85 + state-overlap validation

    Attributes:
        registry: TribalRegistry instance for Tribe lookup.
        alias_table: Dict mapping lowercased recipient name -> tribe_id.
        cache_dir: Path to per-Tribe award cache directory.
        fuzzy_threshold: Minimum token_sort_ratio score for Tier 2 (default 85).
    """

    def __init__(self, config: dict) -> None:
        """Initialize the matcher.

        Args:
            config: Application configuration dict. Reads:
                - config["packets"]["awards"]["alias_path"] (default: data/tribal_aliases.json)
                - config["packets"]["awards"]["cache_dir"] (default: data/award_cache)
                - config["packets"]["awards"]["fuzzy_threshold"] (default: 85)
                - config["packets"]["tribal_registry"]["data_path"] (passed to TribalRegistry)
        """
        self.registry = TribalRegistry(config)

        packets_cfg = config.get("packets", {})
        awards_cfg = packets_cfg.get("awards", {})

        raw_alias = awards_cfg.get("alias_path")
        alias_path = Path(raw_alias) if raw_alias else TRIBAL_ALIASES_PATH
        if not alias_path.is_absolute():
            alias_path = PROJECT_ROOT / alias_path

        raw_cache = awards_cfg.get("cache_dir")
        self.cache_dir = Path(raw_cache) if raw_cache else AWARD_CACHE_DIR
        if not self.cache_dir.is_absolute():
            self.cache_dir = PROJECT_ROOT / self.cache_dir
        self.fuzzy_threshold = awards_cfg.get("fuzzy_threshold", 85)

        # Load alias table
        self.alias_table: dict[str, str] = {}
        try:
            with open(alias_path, "r", encoding="utf-8") as f:
                alias_data = json.load(f)
            self.alias_table = alias_data.get("aliases", {})
            logger.info(
                "Loaded %d aliases from %s", len(self.alias_table), alias_path,
            )
        except FileNotFoundError:
            logger.warning(
                "Alias table not found at %s. Tier 1 matching disabled. "
                "Run 'python scripts/build_tribal_aliases.py' to generate it.",
                alias_path,
            )
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON in alias table %s: %s", alias_path, exc,
            )

        # Build reverse lookup: lowercased name -> tribe dict
        self._name_to_tribe: dict[str, dict] = {}
        for tribe in self.registry.get_all():
            key = tribe["name"].lower().strip()
            self._name_to_tribe[key] = tribe
            for alt in tribe.get("alternate_names", []):
                alt_key = alt.lower().strip()
                if alt_key not in self._name_to_tribe:
                    self._name_to_tribe[alt_key] = tribe

    @staticmethod
    def deduplicate_awards(
        awards_by_cfda: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        """Remove duplicate awards across CFDA batches.

        Multi-year awards often appear in multiple fiscal year queries.
        Deduplication uses Award ID as the primary key. For awards with
        empty/missing Award IDs, a composite key of
        ``{recipient_name}|{cfda}|{obligation}|{start_date}`` is used.

        Keeps the FIRST occurrence (earliest fiscal year appearance).

        Args:
            awards_by_cfda: Dict keyed by CFDA number -> list of raw award dicts.

        Returns:
            New dict with same structure but deduplicated award lists.
        """
        seen_keys: set[str] = set()
        deduped: dict[str, list[dict]] = {}
        original_count = 0
        deduped_count = 0

        for cfda, awards in awards_by_cfda.items():
            deduped_list: list[dict] = []
            for award in awards:
                original_count += 1
                award_id = award.get("Award ID", "").strip()

                if award_id:
                    key = award_id
                else:
                    # Composite fallback for empty Award IDs
                    recipient = award.get("Recipient Name", "")
                    obligation = award.get(
                        "Total Obligation",
                        award.get("Award Amount", ""),
                    )
                    start_date = award.get("Start Date", "")
                    key = f"{recipient}|{cfda}|{obligation}|{start_date}"

                if key not in seen_keys:
                    seen_keys.add(key)
                    deduped_list.append(award)
                    deduped_count += 1

            deduped[cfda] = deduped_list

        removed = original_count - deduped_count
        logger.info(
            "Deduplicated %d -> %d awards (removed %d duplicates)",
            original_count, deduped_count, removed,
        )
        return deduped

    def match_recipient_to_tribe(
        self,
        recipient_name: str,
        recipient_state: str | None = None,
    ) -> dict | None:
        """Match a USASpending recipient name to a Tribe using two-tier matching.

        Tier 1: Curated alias table lookup (O(1)).
        Tier 2: rapidfuzz token_sort_ratio >= 85 with state-overlap validation.

        Args:
            recipient_name: Raw recipient name from USASpending.
            recipient_state: Two-letter state code (e.g., "AZ") for
                state-overlap validation. None to skip state check.

        Returns:
            Tribe dict if matched, None if no match found.
        """
        if not recipient_name or not recipient_name.strip():
            return None

        normalized = recipient_name.strip().lower()

        # Tier 1: Alias table lookup
        tribe_id = self.alias_table.get(normalized)
        if tribe_id:
            tribe = self.registry.get_by_id(tribe_id)
            if tribe:
                logger.debug(
                    "Tier 1 alias match: %r -> %s (%s)",
                    recipient_name, tribe_id, tribe["name"],
                )
                return tribe

        # Tier 2: Fuzzy matching with token_sort_ratio
        try:
            from rapidfuzz import fuzz
        except ImportError:
            logger.warning(
                "rapidfuzz not installed -- Tier 2 fuzzy matching unavailable."
            )
            return None

        best_match: dict | None = None
        best_score: float = 0.0

        for tribe in self.registry.get_all():
            # Check official name + alternate names
            searchable_names = [tribe["name"]] + tribe.get("alternate_names", [])

            for name in searchable_names:
                score = fuzz.token_sort_ratio(normalized, name.lower())

                if score < self.fuzzy_threshold:
                    continue

                # State-overlap validation (critical anti-false-positive guard)
                if recipient_state and tribe.get("states"):
                    if recipient_state.upper() not in tribe["states"]:
                        logger.debug(
                            "Tier 2 state mismatch: %r scored %.0f against %s "
                            "but state %s not in %s",
                            recipient_name, score, tribe["name"],
                            recipient_state, tribe["states"],
                        )
                        continue

                if score > best_score:
                    best_score = score
                    best_match = tribe

        if best_match:
            logger.debug(
                "Tier 2 fuzzy match: %r -> %s (score=%.0f)",
                recipient_name, best_match["name"], best_score,
            )

        return best_match

    def match_all_awards(
        self, awards_by_cfda: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        """Match all awards to Tribes, returning per-tribe_id award lists.

        Consortium/inter-Tribal awards are detected and logged separately
        (not attributed to individual Tribes). Access them via
        ``self._last_consortium_awards`` after calling this method.

        Args:
            awards_by_cfda: Dict keyed by CFDA number -> list of raw award dicts
                (output of USASpendingScraper.fetch_all_tribal_awards()).

        Returns:
            Dict keyed by tribe_id -> list of normalized award dicts.
        """
        matched_by_tribe: dict[str, list[dict]] = {}
        consortium_awards: list[dict] = []
        unmatched_awards: list[dict] = []
        total_awards = 0
        matched_count = 0
        unmatched_count = 0

        for cfda, awards in awards_by_cfda.items():
            for award in awards:
                total_awards += 1
                recipient_name = award.get("Recipient Name", "")

                # Detect consortium/inter-Tribal awards before matching
                if _is_consortium(recipient_name):
                    obligation = _safe_float(
                        award.get("Total Obligation")
                        or award.get("Award Amount"),
                    )
                    consortium_awards.append({
                        "recipient_name": recipient_name,
                        "cfda": cfda,
                        "obligation": obligation,
                        "award_id": award.get("Award ID", ""),
                    })
                    continue

                # Try to extract state from recipient name (trailing ", XX" pattern)
                state = _extract_state_from_name(recipient_name)

                tribe = self.match_recipient_to_tribe(recipient_name, state)

                if tribe is None:
                    unmatched_count += 1
                    obligation = _safe_float(
                        award.get("Total Obligation")
                        or award.get("Award Amount"),
                    )
                    unmatched_awards.append({
                        "recipient_name": recipient_name,
                        "cfda": cfda,
                        "obligation": obligation,
                        "award_id": award.get("Award ID", ""),
                    })
                    logger.debug(
                        "Unmatched award: %r (CFDA %s, %s)",
                        recipient_name, cfda,
                        award.get("Award ID", "unknown"),
                    )
                    continue

                matched_count += 1
                tribe_id = tribe["tribe_id"]

                # Normalize obligation to float
                obligation = _safe_float(
                    award.get("Total Obligation") or award.get("Award Amount")
                )

                normalized_award = {
                    "award_id": award.get("Award ID", ""),
                    "cfda": cfda,
                    "program_id": CFDA_TO_PROGRAM.get(cfda, ""),
                    "recipient_name_raw": recipient_name,
                    "obligation": obligation,
                    "start_date": award.get("Start Date", ""),
                    "end_date": award.get("End Date", ""),
                    "description": award.get("Description", ""),
                    "awarding_agency": award.get("Awarding Agency", ""),
                }

                if tribe_id not in matched_by_tribe:
                    matched_by_tribe[tribe_id] = []
                matched_by_tribe[tribe_id].append(normalized_award)

        # Store unmatched and consortium for downstream reporting
        self._last_unmatched_awards = unmatched_awards
        self._last_consortium_awards = consortium_awards
        if consortium_awards:
            consortium_total = sum(a["obligation"] for a in consortium_awards)
            logger.info(
                "Found %d consortium/inter-Tribal awards totaling $%s "
                "(not attributed to individual Tribes)",
                len(consortium_awards),
                f"{consortium_total:,.0f}",
            )

        matched_tribes = len(matched_by_tribe)
        logger.info(
            "Award matching complete: %d total awards, %d matched to %d Tribes, "
            "%d unmatched, %d consortium",
            total_awards, matched_count, matched_tribes, unmatched_count,
            len(consortium_awards),
        )

        return matched_by_tribe

    def write_cache(
        self,
        matched_awards: dict[str, list[dict]],
        fy_start: int | None = None,
        fy_end: int | None = None,
    ) -> int:
        """Write per-Tribe JSON cache files with enhanced schema.

        Creates a cache file for EVERY Tribe (592), not just those with
        awards. Zero-award Tribes get a ``no_awards_context`` field with
        advocacy framing. Each file includes year-by-year obligation
        breakdowns and a funding trend indicator.

        Args:
            matched_awards: Dict keyed by tribe_id -> list of award dicts.
            fy_start: First fiscal year in range (default: FISCAL_YEAR_INT - 4).
            fy_end: Last fiscal year in range (default: FISCAL_YEAR_INT).

        Returns:
            Number of cache files written.
        """
        if fy_end is None:
            fy_end = FISCAL_YEAR_INT
        if fy_start is None:
            fy_start = FISCAL_YEAR_INT - 4

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        files_written = 0

        for tribe in self.registry.get_all():
            tribe_id = tribe["tribe_id"]
            awards = matched_awards.get(tribe_id, [])
            total_obligation = sum(a.get("obligation", 0.0) for a in awards)

            # Build CFDA summary
            cfda_summary: dict[str, dict] = {}
            for award in awards:
                cfda = award.get("cfda", "")
                if cfda not in cfda_summary:
                    cfda_summary[cfda] = {"count": 0, "total": 0.0}
                cfda_summary[cfda]["count"] += 1
                cfda_summary[cfda]["total"] += award.get("obligation", 0.0)

            # Build yearly obligations breakdown
            yearly_obligations: dict[str, float] = {}
            for fy in range(fy_start, fy_end + 1):
                yearly_obligations[str(fy)] = 0.0
            for award in awards:
                award_fy = _determine_award_fy(award)
                if award_fy is not None and fy_start <= award_fy <= fy_end:
                    yearly_obligations[str(award_fy)] += award.get(
                        "obligation", 0.0,
                    )

            # Compute funding trend
            trend = _compute_trend(yearly_obligations, fy_start, fy_end)

            cache_data: dict = {
                "tribe_id": tribe_id,
                "tribe_name": tribe["name"],
                "fiscal_year_range": {"start": fy_start, "end": fy_end},
                "awards": awards,
                "total_obligation": total_obligation,
                "award_count": len(awards),
                "cfda_summary": cfda_summary,
                "yearly_obligations": yearly_obligations,
                "trend": trend,
            }

            if not awards:
                cache_data["no_awards_context"] = (
                    "No federal climate resilience awards found in tracked programs. "
                    "This represents a first-time applicant opportunity -- the Tribe "
                    "can leverage this status to demonstrate unmet need in competitive "
                    "grant applications."
                )

            cache_path = self.cache_dir / f"{tribe_id}.json"
            tmp_path = cache_path.with_suffix(".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                os.replace(str(tmp_path), str(cache_path))
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink()
                raise

            files_written += 1

        logger.info(
            "Wrote %d cache files to %s (FY%d-FY%d)",
            files_written, self.cache_dir, fy_start, fy_end,
        )
        return files_written

    def run(self, scraper) -> dict:
        """High-level orchestration: fetch, match, cache.

        Calls scraper.fetch_all_tribal_awards() (async), matches all
        awards to Tribes, and writes per-Tribe cache files.

        Args:
            scraper: USASpendingScraper instance.

        Returns:
            Summary dict with execution stats.
        """
        # fetch_all_tribal_awards is async -- run it in event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in an async context -- caller should await directly
            raise RuntimeError(
                "TribalAwardMatcher.run() cannot be called from within a "
                "running event loop. Use 'await run_async(scraper)' instead."
            )

        awards_by_cfda = asyncio.run(scraper.fetch_all_tribal_awards())
        matched = self.match_all_awards(awards_by_cfda)
        cache_count = self.write_cache(matched)

        total_awards = sum(len(v) for v in awards_by_cfda.values())
        matched_awards = sum(len(v) for v in matched.values())

        summary = {
            "total_awards_fetched": total_awards,
            "matched_awards": matched_awards,
            "unmatched_awards": total_awards - matched_awards,
            "matched_tribes": len(matched),
            "cache_files_written": cache_count,
        }
        logger.info("Award pipeline complete: %s", summary)
        return summary

    async def run_async(self, scraper) -> dict:
        """Async version of run() for use within existing event loops.

        Args:
            scraper: USASpendingScraper instance.

        Returns:
            Summary dict with execution stats.
        """
        awards_by_cfda = await scraper.fetch_all_tribal_awards()
        matched = self.match_all_awards(awards_by_cfda)
        cache_count = self.write_cache(matched)

        total_awards = sum(len(v) for v in awards_by_cfda.values())
        matched_awards = sum(len(v) for v in matched.values())

        return {
            "total_awards_fetched": total_awards,
            "matched_awards": matched_awards,
            "unmatched_awards": total_awards - matched_awards,
            "matched_tribes": len(matched),
            "cache_files_written": cache_count,
        }


def _compute_trend(
    yearly_obligations: dict[str, float],
    fy_start: int,
    fy_end: int,
) -> str:
    """Compute a funding trend indicator from yearly obligation data.

    Compares the first half of the fiscal year range to the second half:
      - "none": No awards at all
      - "new": Awards only in the last 2 fiscal years
      - "increasing": Second half > first half * 1.2
      - "decreasing": Second half < first half * 0.8
      - "stable": Otherwise

    Args:
        yearly_obligations: Dict of FY (str) -> obligation amount.
        fy_start: First fiscal year in range.
        fy_end: Last fiscal year in range.

    Returns:
        Trend string: "none", "new", "increasing", "decreasing", or "stable".
    """
    total = sum(yearly_obligations.values())
    if total == 0:
        return "none"

    # Check if awards only exist in the last 2 years
    fy_range = list(range(fy_start, fy_end + 1))
    if len(fy_range) <= 2:
        # With 2 or fewer years there is no meaningful "earlier" window.
        # Return "new" only when the first year has no activity; otherwise
        # use a simple comparison between the two years.
        if len(fy_range) == 1:
            return "new"
        first_fy, last_fy = str(fy_range[0]), str(fy_range[-1])
        first_val = yearly_obligations.get(first_fy, 0.0)
        last_val = yearly_obligations.get(last_fy, 0.0)
        if first_val == 0:
            return "new"
        if last_val > first_val * 1.2:
            return "increasing"
        if last_val < first_val * 0.8:
            return "decreasing"
        return "stable"
    earlier = set(str(fy) for fy in fy_range[:-2])
    has_earlier = any(yearly_obligations.get(fy, 0.0) > 0 for fy in earlier)
    if not has_earlier:
        return "new"

    # Split into first half and second half
    mid = len(fy_range) // 2
    first_half_fys = [str(fy) for fy in fy_range[:mid]]
    second_half_fys = [str(fy) for fy in fy_range[mid:]]

    first_half_sum = sum(yearly_obligations.get(fy, 0.0) for fy in first_half_fys)
    second_half_sum = sum(
        yearly_obligations.get(fy, 0.0) for fy in second_half_fys
    )

    if first_half_sum > 0 and second_half_sum > first_half_sum * 1.2:
        return "increasing"
    if first_half_sum > 0 and second_half_sum < first_half_sum * 0.8:
        return "decreasing"

    return "stable"


def _extract_state_from_name(name: str) -> str | None:
    """Extract a trailing two-letter state code from a recipient name.

    Looks for patterns like "Tribe Name, AZ" or "TRIBE NAME, OK".

    Args:
        name: Raw recipient name string.

    Returns:
        Two-letter state code (uppercase) or None.
    """
    import re
    match = re.search(r',\s*([A-Za-z]{2})\s*$', name)
    if match:
        candidate = match.group(1).upper()
        # Validate it's a real US state abbreviation
        if candidate in _US_STATE_ABBRS:
            return candidate
    return None


def _safe_float(value) -> float:
    """Safely convert a value to float, returning 0.0 on failure.

    Args:
        value: Any value (string, int, float, None).

    Returns:
        Float value, or 0.0 if conversion fails.
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


# US state abbreviations for state extraction validation
_US_STATE_ABBRS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI",
}
