# Phase 19 Plan 04: NRI Expanded Builder Summary

**One-liner:** NRIExpandedBuilder with SHA256 version pinning, national percentile from RISK_SCORE rank, EAL breakdowns, community resilience, and CT FIPS remapping following 9-step template.

## Plan Metadata

| Field | Value |
|-------|-------|
| Phase | 19 - Schema & Core Data Foundation |
| Plan | 04 |
| Type | execute |
| Wave | 2 |
| Depends on | 19-01, 19-02 |
| Duration | ~11 minutes |
| Completed | 2026-02-18 |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement NRIExpandedBuilder | 69c3729 | src/packets/nri_expanded.py |
| 2 | Write NRI expanded builder tests | 0d71a4d | tests/test_nri_expanded.py |

## What Was Built

### NRIExpandedBuilder (src/packets/nri_expanded.py)

Follows the HazardProfileBuilder 9-step template:

1. **__init__**: Config-driven paths for NRI CSV, SHA256 expectation, output dir
2. **_load_crosswalk**: AIANNH GEOID to tribe_id mapping (reused pattern)
3. **_load_area_weights**: Pre-computed area-weighted county overlap (reused pattern)
4. **_load_nri_csv**: SHA256 in 64KB chunks (XCUT-03), CT FIPS remapping, header validation
5. **compute_national_percentiles**: RISK_SCORE rank via bisect_left (18.5-DEC-01)
6. **_aggregate_tribe_nri**: Area-weighted EAL breakdown, SOVI, RESL, top 5 hazards
7. **build_all_profiles**: Full orchestration with NRIExpanded Pydantic validation
8. **_atomic_write**: Path traversal guard + tempfile + os.replace + cleanup
9. **_generate_coverage_report**: Version metadata, profile counts, county stats

### Key Features

- **SHA256 version pinning (XCUT-03)**: Computed in 64KB chunks, WARNING on mismatch (not error)
- **National percentile (18.5-DEC-01)**: rank / (N-1) * 100, single county -> 50.0, zero -> 0.0
- **EAL breakdown**: buildings, population, agriculture, population equivalence
- **Community resilience**: RESL_SCORE extraction and area-weighted aggregation
- **CT FIPS mapping**: 8 legacy-to-planning and 8 planning-to-legacy entries, auto-detect crosswalk format
- **Pydantic validation**: Every profile validated against NRIExpanded schema before write

### Test Suite (tests/test_nri_expanded.py)

48 tests across 7 test classes:
- TestCTFIPSMapping (9): completeness, roundtrip, range, non-CT
- TestNationalPercentile (8): ranked, single, zero, tied, range, empty base
- TestNRIExpandedBuilder (22): init, SHA256, warnings, aggregation, weights, coverage, hazards, path traversal, atomic write, empty profiles, SOVI/RESL
- TestValidateNRIChecksum (3): valid, invalid, case-insensitive
- TestBuildAllProfiles (4): writes files, content valid, no CSV, coverage report
- TestCTFIPSInCSV (1): legacy remapped to planning
- TestNRIExpandedIntegration (1): conditional real CSV load

## Decisions Made

No new decisions. All implementation followed existing decisions:
- 18.5-DEC-01: Compute percentile from RISK_SCORE rank (not RISK_NPCTL)
- XCUT-03: SHA256 version pinning with WARNING on mismatch
- DEC-04: Community resilience feeds adaptive capacity deficit component

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- [x] NRIExpandedBuilder follows all 9 steps of HazardProfileBuilder template
- [x] SHA256 checksum computed with validation
- [x] National percentile from RISK_SCORE rank (not from CSV)
- [x] EAL breakdown extracted (buildings, population, agriculture, pop equiv)
- [x] Community resilience score extracted (RESL_SCORE)
- [x] CT FIPS handling for both legacy and planning region formats
- [x] Area-weighted aggregation uses existing crosswalk
- [x] Atomic writes with utf-8 encoding
- [x] 48 tests passing (25+ requirement exceeded)
- [x] All 1204 tests pass (1204 passed, 1 skipped)

## Test Results

```
1204 passed, 1 skipped in 121.20s
```

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| src/packets/nri_expanded.py | 797 | NRIExpandedBuilder implementation |
| tests/test_nri_expanded.py | 825 | 48-test comprehensive test suite |

## Next Phase Readiness

Plan 19-04 provides the NRI expanded builder needed by:
- Plan 19-05 (SVI builder) -- parallel Wave 2 plan, no dependency
- Plan 19-06 (composite vulnerability) -- consumes NRI expanded profiles
- Phase 22 (pipeline integration) -- wires builder into packet orchestrator
