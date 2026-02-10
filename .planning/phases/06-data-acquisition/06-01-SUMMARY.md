# Phase 6 Plan 01: Tribal Award Matching Pipeline Summary

**One-liner:** Two-tier award matching (3751-entry alias table + token_sort_ratio >= 85 with state validation) against USASpending batch API, with per-Tribe JSON cache for 592 Tribes.

## Metadata

| Field | Value |
|-------|-------|
| Phase | 06-data-acquisition |
| Plan | 01 |
| Subsystem | packets/awards |
| Tags | usaspending, award-matching, fuzzy-matching, caching, tribal |
| Duration | ~7 minutes |
| Completed | 2026-02-10 |

## What Was Built

### 1. USASpendingScraper Batch Methods (`src/scrapers/usaspending.py`)

Added two new async methods to the existing scraper (existing `scan()` and `_fetch_obligations()` unchanged):

- **`fetch_tribal_awards_for_cfda(session, cfda)`**: POSTs to USASpending spending_by_award endpoint filtered to `indian_native_american_tribal_government` recipients. Full pagination via `page_metadata.hasNext`. Returns raw award dicts (not normalized).
- **`fetch_all_tribal_awards()`**: Iterates all 12 tracked CFDAs from `CFDA_TO_PROGRAM`, calls per-CFDA fetch with 0.5s rate limiting between requests. Per-CFDA exception handling (logs error, continues with empty list).

### 2. Curated Alias Table (`data/tribal_aliases.json`)

3,751 lowercased name -> tribe_id mappings bootstrapped from `data/tribal_registry.json` via `scripts/build_tribal_aliases.py`:

- Official names (592) + alternate names (624)
- "THE {name}" variants
- State-suffix stripped variants (single and multi-state: "Navajo Nation, Arizona, New Mexico, & Utah" -> "Navajo Nation")
- Parenthetical variants ("Muscogee (Creek) Nation" -> "Muscogee Creek Nation" and "Muscogee Nation")
- Leading "The" stripped variants
- "of the" / "of" prefix truncations (only when prefix is substantive)

### 3. TribalAwardMatcher (`src/packets/awards.py`)

Core class with four methods:

- **`match_recipient_to_tribe(name, state)`**: Two-tier matching:
  - Tier 1: Alias table O(1) lookup (3,751 entries)
  - Tier 2: rapidfuzz `token_sort_ratio` >= 85 with state-overlap validation
- **`match_all_awards(awards_by_cfda)`**: Processes batch results, normalizes awards with float obligations, logs unmatched for alias table refinement
- **`write_cache(matched_awards)`**: Writes 592 JSON files (one per Tribe), zero-award Tribes get `no_awards_context` advocacy framing
- **`run(scraper)` / `run_async(scraper)`**: Sync and async orchestration

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| token_sort_ratio (not WRatio) for award matching | WRatio is for interactive registry resolve() (Phase 5); award matching needs strict, word-order-invariant scoring |
| 85 threshold (not lower) | Prevents false positives; alias table handles known names at Tier 1 |
| State-overlap validation in Tier 2 only | Tier 1 alias matches are curated and trusted; Tier 2 fuzzy needs guardrails |
| Per-Tribe cache files (not single file) | O(1) per-Tribe lookup during DOCX generation, avoids loading all 592 Tribes' data |
| Zero-award Tribes get advocacy framing | First-time applicant status is a competitive grant advantage, not a data gap |
| No time_period filter in batch queries | Fetch all historical awards for comprehensive funding track record |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `328c8f3` | Batch Tribal query methods + alias table bootstrap |
| 2 | `08485c5` | TribalAwardMatcher class with matching + cache |

## Files Created/Modified

### Created
- `src/packets/awards.py` -- TribalAwardMatcher class (414 lines)
- `data/tribal_aliases.json` -- 3,751 alias entries
- `scripts/build_tribal_aliases.py` -- Alias table generator

### Modified
- `src/scrapers/usaspending.py` -- Added batch methods (111 lines added)

## Verification Results

| Check | Result |
|-------|--------|
| USASpendingScraper imports | PASS |
| Existing 83 tests pass | PASS (0 regressions) |
| Alias table > 500 entries | PASS (3,751) |
| Navajo Nation matches correctly | PASS (epa_100000171) |
| Muscogee (Creek) Nation matches | PASS (epa_100000169) |
| Unrecognizable names return None | PASS |
| Obligations stored as float | PASS |
| write_cache produces 592 files | PASS |
| Zero-award Tribes get no_awards_context | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Multi-state suffix stripping in alias table**
- **Found during:** Task 1
- **Issue:** Initial state-stripping regex only handled single trailing states (", California"). Names like "Navajo Nation, Arizona, New Mexico, & Utah" were not stripped to "Navajo Nation".
- **Fix:** Added `_strip_multi_state_suffix()` helper that detects multi-state patterns after the first comma and validates all tokens are US state names.
- **Files modified:** `scripts/build_tribal_aliases.py`

**2. [Rule 2 - Missing Critical] Leading "The" stripping for aliases**
- **Found during:** Task 1
- **Issue:** Names starting with "The" (e.g., "The Muscogee (Creek) Nation") only generated aliases with "the" prefix. The bare form "muscogee (creek) nation" was missing.
- **Fix:** Added leading "the " stripping and applied parenthetical variants to both the-prefixed and bare forms.
- **Files modified:** `scripts/build_tribal_aliases.py`

## Next Phase Readiness

This plan provides `TribalAwardMatcher` which Phase 7 (economic impact calculations) needs for obligation totals and CFDA summaries. The per-Tribe cache files at `data/award_cache/{tribe_id}.json` provide zero-API-call access to each Tribe's funding history.

Dependencies satisfied:
- `src/packets/awards.py` exports `TribalAwardMatcher`
- `data/tribal_aliases.json` has curated alias mappings
- `src/scrapers/usaspending.py` has batch fetch methods
