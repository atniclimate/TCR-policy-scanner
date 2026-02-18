# Phase 19 Plan 05: SVI 2022 Builder Summary

**One-liner:** CDC/ATSDR SVI 2022 integration pipeline with Theme 3 exclusion, custom 3-theme composite (mean of Themes 1+2+4), area-weighted crosswalk aggregation, and -999 sentinel handling.

## Frontmatter

| Key | Value |
|-----|-------|
| phase | 19 |
| plan | 05 |
| subsystem | packets, schemas, vulnerability |
| tags | svi, cdc, social-vulnerability, theme-exclusion, area-weighted, sovereignty |
| requires | 19-01 (path constants: SVI_COUNTY_PATH, VULNERABILITY_PROFILES_DIR), 19-02 (SVIProfile/SVITheme schemas) |
| provides | SVIProfileBuilder class, _safe_svi_float helper, SVI_INCLUDED_THEMES/SVI_EXCLUDED_THEMES constants, per-Tribe SVI profile JSON output |
| affects | 19-06 (composite vulnerability builder consumes SVI profiles), Phase 20+ (Doc E rendering) |
| tech-stack.added | None (reuses existing _safe_float from hazards.py) |
| tech-stack.patterns | HazardProfileBuilder 9-step template adapted for single-source SVI pipeline |
| duration | ~10 minutes |
| completed | 2026-02-18 |

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Implement SVIProfileBuilder | 645609f | src/packets/svi_builder.py |
| 2 | Write SVI builder tests | 79e02f3 | tests/test_svi_builder.py |

## Key Files

### Created
- `src/packets/svi_builder.py` -- 565 LOC SVIProfileBuilder with 9-step template: CSV parsing, sentinel handling, Theme 3 exclusion, area-weighted aggregation, Pydantic validation, atomic writes, coverage reporting
- `tests/test_svi_builder.py` -- 54 tests across 7 test classes covering sentinel handling, theme exclusion, composite computation, area-weighted aggregation, builder orchestration, data gaps, and integration

### Modified
- None

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 19-05-DEC-01 | Import _safe_float from src.packets.hazards rather than duplicating | DRY principle; hazards.py _safe_float is battle-tested with NaN/Inf handling |
| 19-05-DEC-02 | Output directory defaults to data/svi/profiles/ (not vulnerability_profiles/) | SVI profiles are intermediate data consumed by the composite builder (19-06); final vulnerability profiles go to vulnerability_profiles/ |
| 19-05-DEC-03 | Skip counties where ALL 3 included themes are 0.0 | Zero across all themes indicates suppressed/unavailable data, not actual zero vulnerability |
| 19-05-DEC-04 | Store RPL_THEMES in parsed data for reference but never use in composite | RPL_THEMES includes Theme 3; our composite must be independently computed from Themes 1+2+4 |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- SVIProfileBuilder follows HazardProfileBuilder 9-step template (init, crosswalk, weights, CSV parse, aggregate, build_all, atomic_write, coverage)
- SVI 2022 CSV parsed with -999 sentinel handling via _safe_svi_float
- Theme 3 explicitly excluded: not extracted from CSV, not in SVI_INCLUDED_THEMES, SVITheme schema rejects theme3
- Custom 3-theme composite = mean(theme1, theme2, theme4) validated by SVIProfile.validate_composite_mean
- Area-weighted crosswalk aggregation with weight normalization
- Coverage percentage and data gap detection (MISSING_SVI, ALASKA_PARTIAL)
- Atomic writes with utf-8 encoding and path traversal guard
- 54 tests (53 pass, 1 skip for conditional integration)
- All 1156 existing tests pass (no regressions)

## Test Summary

| Metric | Value |
|--------|-------|
| Tests before | 1103 |
| Tests after | 1156 |
| New tests added | 54 (test_svi_builder.py) |
| Tests modified | 0 |
| All passing | Yes (53 pass + 1 skip) |

## Test Classes

| Class | Tests | Coverage |
|-------|-------|----------|
| TestSafeSviFloat | 12 | Sentinel -999 (int/float/str), valid passthrough, None, empty, whitespace, custom default |
| TestThemeExclusion | 8 | Included themes 1/2/4, theme3 excluded, disjoint sets, CSV skip, schema reject |
| TestSVICompositeComputation | 6 | 3-theme average, all zeros, all ones, unequal, RPL_THEMES unused, mismatch rejected |
| TestSVIAreaWeightedAggregation | 8 | Single county, two county, composite, missing county, normalization, coverage_pct, zero weight, all-zero skip |
| TestSVIProfileBuilder | 9 | Init, path traversal (2), atomic write, schema validation, build count, FIPS fallback, sentinel CSV, missing CSV |
| TestSVIDataGaps | 5 | Zero coverage, full coverage, Alaska partial, no crosswalk, empty data |
| TestSVIThemeNames | 5 | Coverage of included themes, theme3 absent, individual names |
| TestSVIIntegration | 1 | Conditional on real CSV existence |

## Next Phase Readiness

Plan 19-05 deliverables enable the composite vulnerability builder (19-06):
- SVIProfileBuilder produces per-Tribe SVI profiles with validated composite scores
- SVIProfile Pydantic model provides the social_vulnerability component (0.35 weight)
- Data gaps (MISSING_SVI, ALASKA_PARTIAL) propagate to composite confidence scoring
- No blockers identified
