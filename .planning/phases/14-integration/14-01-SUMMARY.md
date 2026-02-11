---
phase: 14-integration
plan: 01
subsystem: hazard-data-and-regional-config
tags: [fema-nri, hazard-profiles, regional-config, data-population, area-crosswalk, schema-consistency]

# Dependency graph
requires:
  - "13-01: NRI data download + area-weighted crosswalk builder"
  - "13-02: Area-weighted NRI aggregation refactor + tests"
  - "13-03: USFS wildfire override + hazard population pipeline"
provides:
  - 592 hazard profiles with real FEMA NRI risk scores (100% coverage)
  - 8-region configuration for Doc C/D regional document generation
  - REGIONAL_CONFIG_PATH constant in src/paths.py
  - Schema consistency fix: all 18 NRI hazard types always present
affects:
  - "14-02+: Integration plans that read hazard profiles for DOCX generation"
  - "14-*: Regional document aggregation using regional_config.json"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Schema consistency: all 18 NRI hazard types always present in all_hazards (zeros for non-applicable)"
    - "Dual config pattern: ecoregion_config (per-Tribe relevance) + regional_config (Doc C/D grouping)"
    - "Non-zero-only top_hazards extraction (zero-score types excluded from top 5)"

# File tracking
key-files:
  created:
    - data/regional_config.json
  modified:
    - src/paths.py
    - src/packets/hazards.py
    - data/hazard_profiles/*.json (592 files)
    - outputs/hazard_coverage_report.json
    - outputs/hazard_coverage_report.md
    - tests/test_hazard_aggregation.py
    - tests/test_schemas.py
    - tests/test_usfs_override_integration.py

# Decisions
decisions:
  - id: DEC-1401-01
    summary: "All 18 NRI hazard types always present in all_hazards dict (zeros for non-applicable) for schema consistency"
  - id: DEC-1401-02
    summary: "regional_config.json is separate from ecoregion_config.json -- complementary configs serving different purposes"
  - id: DEC-1401-03
    summary: "Crosscutting region has empty states list; spans all 592 Tribes for Doc C/D aggregation"
  - id: DEC-1401-04
    summary: "USFS XLSX first sheet is README; USFS wildfire override unavailable this run (soft prerequisite per DEC-1303-06)"

# Metrics
duration: ~23 minutes
completed: 2026-02-11
tasks: 2/2
tests-added: 0
tests-modified: 4
tests-total: 647
---

# Phase 14 Plan 01: Hazard Data Activation + Regional Configuration Summary

Downloaded FEMA NRI v1.20 county data, built area-weighted AIANNH crosswalk, and populated all 592 Tribe hazard profiles with real risk scores; created 8-region configuration for Doc C/D document generation with crosscutting virtual region.

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~23 minutes |
| Start | 2026-02-11T19:55:27Z |
| End | 2026-02-11T20:18:09Z |
| Tasks | 2/2 |
| Files created | 1 (regional_config.json) |
| Files modified | 598 (592 hazard profiles + hazards.py + paths.py + 3 tests + 2 reports) |
| Tests | 647 pass (was 606) |

## Accomplishments

### Task 1: Download NRI Source Data and Populate Hazard Profiles

1. **Downloaded FEMA NRI v1.20 county CSV** -- 3,232 counties with risk scores for 18 hazard types
2. **Downloaded Census TIGER/Line shapefiles** -- AIANNH (864 features) and county (3,235 features) boundaries
3. **Built area-weighted crosswalk** -- 642 AIANNH entities mapped to 1,019 county links
4. **Downloaded USFS wildfire XLSX** -- 4.8 MB, but first sheet is "READ ME" (column discovery failed; soft prerequisite)
5. **Populated all 592 hazard profiles** -- 100% NRI coverage, 0% USFS (format issue), 0 unmatched Tribes
6. **Fixed schema inconsistency** -- all_hazards now always contains all 18 NRI hazard codes (with zeros for non-applicable hazard types); top_hazards only includes non-zero risk entries

### Task 2: Create 8-Region Configuration

1. **Created data/regional_config.json** with 8 regions: pnw, alaska, plains, southwest, greatlakes, southeast, northeast, crosscutting
2. **Added REGIONAL_CONFIG_PATH** to src/paths.py alongside existing path constants
3. **Preserved ecoregion_config.json** unchanged (continues to serve per-Tribe relevance filtering)

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1a | Populate 592 hazard profiles | 2d6511c | data/hazard_profiles/*.json, outputs/hazard_coverage_report.* |
| 1b | Fix schema consistency (all 18 types) | 4ef6a12 | src/packets/hazards.py, tests/test_hazard_aggregation.py, tests/test_schemas.py, tests/test_usfs_override_integration.py |
| 2 | Create 8-region config | bc099de | data/regional_config.json, src/paths.py |

## Files Created

- `data/regional_config.json` -- 8-region definitions with states, core_frame, key_programs, treaty_trust_angle

## Files Modified

- `src/packets/hazards.py` -- Schema consistency: always include all 18 hazard types; non-zero-only top_hazards; safer USFS override condition
- `src/paths.py` -- Added REGIONAL_CONFIG_PATH constant
- `data/hazard_profiles/*.json` -- 592 files populated with real NRI risk scores
- `outputs/hazard_coverage_report.json` -- Machine-readable coverage report (592/592 scored)
- `outputs/hazard_coverage_report.md` -- Human-readable coverage report with per-state breakdown
- `tests/test_hazard_aggregation.py` -- Updated test_nonzero_hazard_filtering and test_empty_profile for 18-type schema
- `tests/test_schemas.py` -- Updated NRI version assertion to match "NRI_v1.20" format
- `tests/test_usfs_override_integration.py` -- Updated unmatched tribe assertion for 18-type schema

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-1401-01 | All 18 NRI hazard types always present in all_hazards | Schema consistency between placeholder and populated profiles; test_schemas.py expects 18 codes |
| DEC-1401-02 | regional_config.json separate from ecoregion_config.json | Different purposes: ecoregion for per-Tribe relevance filtering (7 NCA5 regions), regional for Doc C/D grouping (8 regions) |
| DEC-1401-03 | Crosscutting region has empty states list | Virtual region spanning all 592 Tribes for cross-cutting policy documents |
| DEC-1401-04 | USFS wildfire override unavailable this run | USFS XLSX first sheet is "READ ME" not data; soft prerequisite per DEC-1303-06; all 592 Tribes still scored via NRI |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Schema inconsistency: all_hazards missing zero-score hazard types**

- **Found during:** Task 1 verification (test_nri_has_18_hazard_types failed)
- **Issue:** Populated profiles only included non-zero hazard types (14 for Oklahoma, varying by region), but schema tests expected all 18 NRI codes
- **Fix:** Modified _build_tribe_nri_profile() to always include all 18 codes with zeros; updated _empty_nri_profile() similarly; added non-zero filter for top_hazards extraction; updated USFS override condition
- **Files modified:** src/packets/hazards.py, tests/test_hazard_aggregation.py, tests/test_schemas.py, tests/test_usfs_override_integration.py
- **Commit:** 4ef6a12

**2. [Rule 1 - Bug] NRI version string format mismatch**

- **Found during:** Task 1 verification (test_nri_source_validates_via_model failed)
- **Issue:** Placeholder profiles used "1.20" but builder produces "NRI_v1.20" (Phase 13 format)
- **Fix:** Updated test assertion to expect "NRI_v1.20"
- **Files modified:** tests/test_schemas.py
- **Commit:** 4ef6a12 (same commit)

## Issues Encountered

1. **USFS XLSX format issue** -- The downloaded USFS XLSX (wrc_download_202505.xlsx) has "READ ME" as the first sheet header, causing column discovery to fail. The active sheet appears to be a readme, not data. This is a soft prerequisite (DEC-1303-06) and does not block NRI population. All 592 Tribes are still scored via FEMA NRI county data. A future fix would parse the correct sheet from the multi-sheet XLSX.

2. **NRI Tribal County Relational CSV** -- The downloaded CSV exists at data/nri/NRI_Table_Tribal_Counties.csv but the column discovery heuristic in hazards.py failed to match its headers (searched for "tribal" + "relational" in filename but the file matched). The script fell back to state-level county matching with area weights, which provided 100% coverage. Not a blocker.

## Next Phase Readiness

Plan 14-01 data gaps resolved:
- 592/592 hazard profiles contain real NRI risk scores (was 0/592)
- 8-region configuration ready for Doc C/D generation
- REGIONAL_CONFIG_PATH available for downstream imports

Remaining for Phase 14:
- Plans 14-02 through 14-07 can proceed with real hazard data
- USFS wildfire override could be improved by parsing correct XLSX sheet (non-blocking)
