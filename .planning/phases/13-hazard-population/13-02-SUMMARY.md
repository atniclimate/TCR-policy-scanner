---
phase: 13-hazard-population
plan: 02
subsystem: hazard-profiling
tags: [fema-nri, area-weighted, aggregation, quintile, score-to-rating, hazards]

# Dependency graph
requires:
  - "13-01: NRI data download scripts + area-weighted crosswalk builder"
provides:
  - Area-weighted NRI aggregation in HazardProfileBuilder
  - score_to_rating() quintile-based rating derivation function
  - Non-zero hazard filtering (zero-score types omitted from profiles)
  - Top-5 hazard extraction (upgraded from top-3)
  - Comprehensive unit tests for aggregation correctness
affects:
  - "13-03: Profile regeneration (consumes the refactored builder)"
  - "14-*: Integration phase (reads generated hazard profiles)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Area-weighted averaging for geographic aggregation"
    - "Quintile breakpoints for rating derivation"
    - "Non-zero filtering for sparse data"

# File tracking
key-files:
  created:
    - tests/test_hazard_aggregation.py
  modified:
    - src/packets/hazards.py
    - src/schemas/models.py
    - tests/test_packets.py

# Decisions
decisions:
  - id: DEC-1302-01
    summary: "EAL dollar amounts use weighted SUM (not average) to reflect proportional exposure"
  - id: DEC-1302-02
    summary: "Ratings re-derived from weighted scores via quintile breakpoints (not MAX of source ratings)"
  - id: DEC-1302-03
    summary: "Version string changed from '1.20' to 'NRI_v1.20' to document data source"
  - id: DEC-1302-04
    summary: "Empty profiles use empty all_hazards dict instead of 18-entry zero dict"

# Metrics
duration: ~12 minutes
completed: 2026-02-11
tasks: 2/2
tests-added: 22
tests-total: 497
---

# Phase 13 Plan 02: Area-Weighted NRI Aggregation Summary

Area-weighted averaging for multi-county Tribal hazard profiles with quintile-based rating re-derivation, non-zero filtering, and top-5 hazard extraction.

## What Changed

### Task 1: score_to_rating() and aggregation refactor (f9c38ae)

**src/packets/hazards.py** -- Major refactor of the NRI aggregation engine:

1. **New import**: `TRIBAL_COUNTY_WEIGHTS_PATH` from `src.paths` for area crosswalk loading
2. **New function**: `score_to_rating()` maps 0-100 percentile scores to NRI rating strings using quintile breakpoints (Very Low / Relatively Low / Relatively Moderate / Relatively High / Very High)
3. **New method**: `_load_area_weights()` reads the pre-computed area-weighted AIANNH-to-county crosswalk JSON produced by `scripts/build_area_crosswalk.py`
4. **Refactored**: `_build_tribe_nri_profile()` replaced MAX-based aggregation with area-weighted averaging:
   - Percentile scores (risk_score, eal_score, sovi_score, resl_score): weighted AVERAGE
   - Dollar amounts (eal_total): weighted SUM proportional to geographic overlap
   - Ratings: re-derived from weighted scores via `score_to_rating()` (not MAX of source ratings)
   - Fallback chain: area weights -> relational CSV (equal weights) -> state-level (equal weights)
5. **Non-zero filtering**: Only hazards with `risk_score > 0` stored in `all_hazards`
6. **Top 5**: Changed from top-3 to top-5 hazard extraction
7. **Removed**: `_max_rating()` and `_min_rating()` static methods (replaced by `score_to_rating()`)
8. **Updated**: `_empty_nri_profile()` uses empty `all_hazards` dict and adds `eal_rating` field

**src/schemas/models.py** -- Added `eal_rating` field to `NRIComposite` Pydantic model

**tests/test_packets.py** -- Updated existing hazard builder tests for area-weighted behavior

### Task 2: Unit tests for aggregation (078c8d4)

**tests/test_hazard_aggregation.py** -- 22 new tests in 2 classes:

- `TestScoreToRating` (11 tests): boundary values, quintile edges, completeness, return types
- `TestAreaWeightedAggregation` (11 tests): single-county passthrough, equal weights, unequal area weights, non-zero filtering, top-5 extraction, EAL dollar weighted sum, rating re-derivation, empty profiles, eal_rating field, version format, fallback behavior

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added eal_rating to NRIComposite Pydantic model**

- **Found during:** Task 1
- **Issue:** The new code generates `eal_rating` in composite output, but the Pydantic model lacked this field
- **Fix:** Added `eal_rating: str = Field(default="", description="Expected Annual Loss rating")` to `NRIComposite`
- **Files modified:** src/schemas/models.py
- **Commit:** f9c38ae

## Requirements Satisfied

- **HZRD-03**: County NRI scores aggregated to Tribe level using area-weighted averaging
- **HZRD-04**: Top 5 hazards per Tribe extracted and ranked by risk_score descending

## Next Phase Readiness

Plan 13-03 can now regenerate all 592 hazard profiles using the refactored builder. The area-weighted crosswalk from 13-01 plus this plan's aggregation refactor are the prerequisites for the bulk regeneration.

**Note:** Two pre-existing test failures exist in test_schemas.py (award cache validation and FundingRecord defaults) from Phase 12 work. These are unrelated to hazard aggregation.
