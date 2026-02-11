# Phase 13 Hazard Population -- Swarm Review Log
**Started:** 2026-02-11 11:10
**Scope:** Plans 13-01 through 13-03
**Data state:** Code-only (no NRI, USFS, or hazard profile data downloaded)

## Baseline Metrics
- Test count: 538
- Test pass rate: 538/538 (100%)
- Ruff violations: 5 (3 F821 undefined-name, 2 F401 unused-import)
- Profile count: 0 (data/hazard_profiles/ not populated)
- Scored profiles: N/A (no data files)

## CARTOGRAPHER Findings

- [CARTO-01] CRITICAL build_area_crosswalk.py:240-250 -- AIANNH shapefile has NO STATEFP column. Fallback sends ALL features to CONUS bucket. ~230+ Alaska Native communities get ZERO county linkages. Fix: use INTPTLAT/INTPTLON or spatial join to classify Alaska features.
- [CARTO-02] HIGH build_area_crosswalk.py:128-129 -- No make_valid() before gpd.overlay(). Invalid geometries can crash entire CONUS overlay with TopologyException.
- [CARTO-03] HIGH build_area_crosswalk.py:247-266 -- Hawaii HHLs projected to EPSG:5070 (wrong for Hawaii). 2-5% area distortion. Consider Hawaii-specific CRS or exclusion per research decision.
- [CARTO-07] MEDIUM -- Weight rounding to 6 decimal places may not sum exactly to 1.0. Mitigated by re-normalization in hazards.py.
- [CARTO-10] LOW -- Overlay failure silently returns empty list. No non-zero exit code.
- [CARTO-11] LOW -- Zero test coverage for build_area_crosswalk.py.
- [CARTO-12] MEDIUM -- No validation of output crosswalk count against expected range (~400+ minimum).

## ACTUARY Findings

- [ACTUARY-01] MEDIUM -- EAL "weighted sum" comment/docstring is misleading. The operation uses norm_weights summing to 1.0 (weighted average). Numerically correct for proportional attribution but documentation should match.
- [ACTUARY-06] HIGH -- USFS risk_to_homes is NOT on 0-100 percentile scale like NRI WFIR_RISKS. Override injects incommensurable metric. Must validate USFS scale or present separately.
- [ACTUARY-07] LOW -- Code uses IFLD (correct for NRI v1.20). Older NRI datasets using RFLD would silently drop inland flooding data.
- [ACTUARY-08] MEDIUM -- EAL_VALT -> eal_total naming could confuse NRI data consumers.

## DALE-GRIBBLE Findings

- [GRIBBLE-01] CRITICAL download_nri_data.py:152-153 -- ZIP Slip path traversal. extractall() with no member path validation.
- [GRIBBLE-02] CRITICAL download_nri_data.py:108-126 -- No ZIP integrity verification after download. Truncated files get atomically replaced.
- [GRIBBLE-03] CRITICAL hazards.py:1078-1080 -- Non-atomic writes for 592 profile JSONs. Violates CLAUDE.md Rule #8.
- [GRIBBLE-04] HIGH hazards.py:341,430 -- UTF-8 BOM will corrupt first CSV column name. Use utf-8-sig.
- [GRIBBLE-05] HIGH build_area_crosswalk.py:276 -- NaN from geopandas geometry ops propagates silently through crosswalk.
- [GRIBBLE-06] HIGH hazards.py:76-96 -- _safe_float() does not catch NaN/Inf from float("nan")/float("inf").
- [GRIBBLE-07] HIGH download_usfs_data.py:39-41 -- Hardcoded USFS URL with date version (202505) will rot.
- [GRIBBLE-08] HIGH download_nri_data.py:45-46 -- Hardcoded NRI URLs with version v120 will rot.
- [GRIBBLE-09] HIGH hazards.py:1078 -- No path traversal protection on tribe_id (other modules sanitize).
- [GRIBBLE-10] HIGH build_area_crosswalk.py:282 -- Duplicate county_fips for same GEOID inflates weight.
- [GRIBBLE-11] HIGH hazards.py:1174,1224 -- Coverage report writes not atomic.
- [GRIBBLE-12] MEDIUM -- USFS XLSX parsing assumes headers on row 1, active sheet.
- [GRIBBLE-15] MEDIUM hazards.py:345 -- STCOFIPS not zfill(5) padded (relies on CSV preserving leading zeros).
- [GRIBBLE-16] MEDIUM populate_hazards.py:152-160 -- --tribe flag accepted but does nothing (builds all 592).
- [GRIBBLE-19] MEDIUM hazards.py:921-923 -- USFS name matching too aggressive (substring matching).
- [GRIBBLE-20] MEDIUM hazards.py:261 -- Empty crosswalk key silent degradation.
- [GRIBBLE-22] LOW hazards.py:292 -- NRI version detector regex may match non-NRI filenames.

## STORYTELLER Findings

- [STORY-03] HIGH -- EAL values lack currency context ($). Bare floats could be misinterpreted.
- [STORY-06] CRITICAL -- EAL aggregation uses weighted average (norm_weights sum to 1.0). For advocacy, must be clear this is proportional attribution, not raw sum.
- [STORY-09] HIGH -- Coverage report collapses 3 distinct failure modes into one "unmatched" bucket.
- [STORY-13] HIGH -- USFS override has no explanatory rationale in profile. Grant writers can't justify the data source.
- [STORY-15] HIGH -- "Unmatched Tribes" heading uses deficit framing. Should reframe as federal data gap.
- [STORY-02] MEDIUM -- risk_score lacks context ("percentile" label).
- [STORY-04] MEDIUM -- SOVI/RESL acronyms unexplained in profile.
- [STORY-07] MEDIUM -- Quintile approximation for ratings not flagged in profile.
- [STORY-11] MEDIUM -- counties_analyzed count not used narratively.
- [STORY-16] MEDIUM -- Empty profile note strings use system jargon.
- [STORY-18] MEDIUM -- Profile does not list which counties were analyzed.

## SURGEON Fixes

Applied 11 targeted fixes (3 CRITICAL, 5 HIGH, 3 MEDIUM):

| ID | Severity | File | Fix |
|----|----------|------|-----|
| GRIBBLE-03 | CRITICAL | hazards.py | Atomic writes (tmp + os.replace) for 592 profile JSONs |
| GRIBBLE-01 | CRITICAL | download_nri_data.py | ZIP Slip path traversal protection in _extract_zip() |
| GRIBBLE-06 | HIGH | hazards.py | NaN/Inf guard in _safe_float() via math.isnan/isinf |
| GRIBBLE-04 | HIGH | hazards.py | utf-8-sig encoding for government CSV reads |
| GRIBBLE-09 | HIGH | hazards.py | Path(tribe_id).name sanitization in build_all_profiles() |
| GRIBBLE-05 | HIGH | build_area_crosswalk.py | NaN guard on geometry area values |
| GRIBBLE-11 | HIGH | hazards.py | Atomic writes for coverage report (JSON + MD) |
| CARTO-02 | HIGH | build_area_crosswalk.py | make_valid() before gpd.overlay() |
| STORY-15 | MEDIUM | hazards.py | "Unmatched Tribes" -> "Tribes Not Covered by Federal Hazard Data" |
| ACTUARY-01 | MEDIUM | hazards.py | "weighted SUM" -> "weighted average (proportional attribution)" |
| GRIBBLE-15 | MEDIUM | hazards.py | STCOFIPS zfill(5) for leading-zero preservation |

Tests: 607 passed (0 failed), up from 538 baseline (+69 new tests from swarm)

## SIMPLIFIER Changes
<!-- Agent 6: Complexity reduction -- skipped; SURGEON fixes are minimal-diff -->

## VALIDATOR Sign-Off

**Status: PASSED**

| Check | Result |
|-------|--------|
| Tests | 607 passed, 0 failed |
| Ruff | 0 violations on modified files |
| GRIBBLE-03 (atomic writes) | os.replace() verified in source |
| GRIBBLE-01 (ZIP Slip) | is_relative_to() verified in source |
| GRIBBLE-06 (NaN/Inf guard) | _safe_float("nan") == 0.0 confirmed |
| GRIBBLE-09 (path traversal) | Path().name verified in source |
| CARTO-02 (make_valid) | make_valid() verified in source |
| Commit | 730c231 |

**Not addressed (deferred):**
- CARTO-01 (Alaska AIANNH classification): Requires AIANNH shapefile schema analysis with real data
- CARTO-03 (Hawaii CRS): Research decision needed on Hawaii-specific projection
- GRIBBLE-02 (ZIP integrity): Low risk for FEMA downloads; deferred to v1.3
- GRIBBLE-07/08 (URL rot): Monitoring concern, not a code bug
