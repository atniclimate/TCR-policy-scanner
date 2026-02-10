# Phase 6 Plan 03: Award + Hazard Orchestrator Integration and Test Suite Summary

**One-liner:** Wired award cache and hazard profile JSON into PacketOrchestrator context building + display, with 23 new tests covering awards, hazards, and orchestrator integration (106 total).

## Metadata

| Field | Value |
|-------|-------|
| Phase | 06-data-acquisition |
| Plan | 03 |
| Subsystem | packets/orchestrator, packets/awards, packets/hazards |
| Tags | orchestrator, awards, hazards, testing, caching, display |
| Duration | ~5 minutes |
| Completed | 2026-02-10 |

## What Was Built

### 1. Orchestrator Award + Hazard Integration (`src/packets/orchestrator.py`)

Updated PacketOrchestrator to load pre-cached award and hazard data into TribePacketContext:

- **`_load_tribe_cache(cache_dir, tribe_id)`**: Generic JSON cache loader with graceful error handling (FileNotFoundError, JSONDecodeError, OSError all return empty dict).
- **`_build_context()`**: Now populates `awards` (from award_cache) and `hazard_profile` (from hazard_profiles) fields on every TribePacketContext.
- **`_display_award_summary(context)`**: Prints total obligation, award count, and per-program breakdowns. Zero-award Tribes get "First-time applicant opportunity" messaging.
- **`_display_hazard_summary(context)`**: Prints NRI composite risk, social vulnerability, top 3 hazards with scores and EAL, and USFS wildfire risk-to-homes and likelihood.

Cache loading is read-only -- no API calls, no data generation. The orchestrator reads pre-built JSON files from `data/award_cache/` and `data/hazard_profiles/`.

### 2. Config Updates (`config/scanner_config.json`)

Added two new subsections to the `packets` config block:

```json
"awards": {
    "alias_path": "data/tribal_aliases.json",
    "cache_dir": "data/award_cache",
    "fuzzy_threshold": 85
},
"hazards": {
    "nri_dir": "data/nri",
    "usfs_dir": "data/usfs",
    "cache_dir": "data/hazard_profiles",
    "crosswalk_path": "data/aiannh_tribe_crosswalk.json"
}
```

Existing config sections (sources, scoring, monitors, packets core) untouched.

### 3. Comprehensive Phase 6 Test Suite (`tests/test_packets.py`)

Added 23 new tests across three test classes:

**TestTribalAwardMatcher (10 tests):**
- Alias table loading and entry count
- Tier 1 exact alias match
- Tier 2 fuzzy match (token_sort_ratio >= 85)
- Below-threshold rejection (prevents false positives)
- State overlap rejection (Choctaw in OK vs MS)
- State overlap pass (correct state allows match)
- No-match returns None
- Award grouping by tribe_id
- Zero-award cache with advocacy framing
- Numeric obligation amounts (float, not string)

**TestHazardProfileBuilder (8 tests):**
- NRI_HAZARD_CODES count (exactly 18)
- _safe_float edge cases (empty, None, N/A, numeric strings, ints)
- NRI county CSV parsing (correct values extracted)
- Multi-county aggregation (MAX risk, SUM EAL)
- Top 3 hazards ranked by descending risk score
- Empty profile for unmatched Tribes (no crash)
- UTF-8 cache file encoding
- Cache directory auto-creation

**TestOrchestratorPhase6Integration (5 tests):**
- Context includes awards from cache
- Context includes hazard_profile from cache
- Missing cache files produce empty defaults (graceful)
- Display outputs award summary with dollar amounts
- Display outputs hazard summary with top hazards

## Test Results

| Metric | Count |
|--------|-------|
| Previous tests | 83 |
| New tests added | 23 |
| Total tests | 106 |
| Tests passing | 106/106 |
| Regressions | 0 |

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `src/packets/orchestrator.py` | Modified | Added cache loading, award/hazard display methods |
| `config/scanner_config.json` | Modified | Added awards + hazards config sections |
| `tests/test_packets.py` | Modified | Added 23 tests in 3 new test classes |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `3fe390b` | feat | Wire award + hazard cache into orchestrator and config |
| `2d1dcb6` | test | Comprehensive Phase 6 test suite (23 tests) |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Read-only cache loading in orchestrator | Orchestrator displays pre-built data, never generates it; keeps --prep-packets fast |
| Separate display methods for awards/hazards | Clean separation; each method handles its own empty-data messaging |
| Generic _load_tribe_cache helper | Reused for both award and hazard cache directories; DRY principle |
| Awards grouped by program_id in display | Shows which specific programs funded the Tribe (BIA TCR, FEMA BRIC, etc.) |

## Deviations from Plan

None -- plan executed exactly as written.

## Phase 6 Completion Status

All 3 plans in Phase 6 (Data Acquisition) are now complete:

| Plan | Name | Status |
|------|------|--------|
| 06-01 | Tribal Award Matching Pipeline | Complete |
| 06-02 | Hazard Profile Builder | Complete |
| 06-03 | Orchestrator Integration + Tests | Complete |

Phase 6 delivers: USASpending award matching, FEMA NRI + USFS hazard profiling, per-Tribe JSON caches, orchestrator integration, and 23 Phase 6 tests.

## Next Phase Readiness

Phase 7 (Computation + DOCX) can begin. Prerequisites met:
- Award cache populated (data/award_cache/*.json)
- Hazard profiles populated (data/hazard_profiles/*.json)
- TribePacketContext has all data fields populated
- Orchestrator loads and displays all context layers
- 106 tests providing regression safety
