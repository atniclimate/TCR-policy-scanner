---
phase: 19-schema-core-data-foundation
plan: 02
subsystem: schemas
tags: [pydantic, vulnerability, tdd, validation, enums]
depends_on:
  requires: []
  provides: [vulnerability-schemas, investment-priority-tier, data-gap-types, composite-score-model]
  affects: [19-04, 19-05, 19-06, 20, 21, 22, 23]
tech-stack:
  added: []
  patterns: [pydantic-v2-strenum, field-clamping, model-validator-tier-consistency, sentinel-rejection]
key-files:
  created:
    - src/schemas/vulnerability.py
    - tests/test_vulnerability_schemas.py
  modified:
    - src/schemas/__init__.py
decisions: []
metrics:
  duration: ~8 minutes
  completed: 2026-02-17
  tests-added: 68
  tests-total: 1084
---

# Phase 19 Plan 02: Vulnerability Pydantic v2 Schemas Summary

**One-liner:** 8 Pydantic v2 models with StrEnum tiers, percentile clamping, sentinel rejection, and composite/mean consistency validators via TDD RED-GREEN cycle.

## What Was Done

Implemented all vulnerability assessment data contracts for the v1.4 Climate Vulnerability Intelligence pipeline using strict TDD (RED then GREEN).

### Models Implemented (8 total in `src/schemas/vulnerability.py`)

| Model | Type | Key Validation |
|-------|------|----------------|
| DataGapType | StrEnum (6 values) | MISSING_SVI, PARTIAL_NRI, ZERO_AREA_WEIGHT, ALASKA_PARTIAL, NO_COASTAL_DATA, SOURCE_UNAVAILABLE |
| InvestmentPriorityTier | StrEnum (5 values) | from_score() classmethod with >= boundary logic |
| NRIExpanded | BaseModel | risk_percentile clamped [0, 100], tribe_id epa_ prefix, top_hazards max 5 |
| SVITheme | BaseModel | theme_id restricted to theme1/2/4 (theme3 excluded per DEC-02), -999 sentinel rejected |
| SVIProfile | BaseModel | max 3 themes, composite must match mean within 0.01 tolerance |
| CompositeComponent | BaseModel | 3 valid component names (hazard_exposure, social_vulnerability, adaptive_capacity_deficit) |
| CompositeScore | BaseModel | tier must match InvestmentPriorityTier.from_score(score) via model_validator |
| VulnerabilityProfile | BaseModel | Optional nri/svi/composite sub-profiles, tribe_id validation, required versions |

### TDD Execution

| Phase | Tests | Status |
|-------|-------|--------|
| RED | 68 tests written | All FAIL (ModuleNotFoundError) |
| GREEN | 8 models + __init__.py | All 68 PASS |
| REFACTOR | Not needed | Code already clean |

### Test Coverage (68 tests across 8 classes)

- TestDataGapType: 5 tests (enum values, count, string, construction, invalid)
- TestInvestmentPriorityTier: 9 tests (all 5 tier boundaries, exact boundaries, string enum)
- TestNRIExpanded: 13 tests (valid profile, clamping, tribe_id, negative values, ranges)
- TestSVITheme: 7 tests (valid, theme_id restriction, -999 rejection, percentile range)
- TestSVIProfile: 8 tests (3 themes, max validation, composite/mean, defaults, gaps)
- TestCompositeComponent: 5 tests (valid, 3 names, invalid, score range, default)
- TestCompositeScore: 10 tests (valid, tier/score consistency for all 5 tiers, range, mappings)
- TestVulnerabilityProfile: 9 tests (minimal, tribe_id, defaults, nested data, required fields)
- TestImportsAndReexports: 2 tests (direct import, __init__.py re-export)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 494d50f | test | add failing tests for vulnerability schemas (RED) |
| 5560c73 | feat | implement vulnerability Pydantic v2 schemas (GREEN) |

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

No new decisions. Implementation follows existing decisions:
- DEC-02: Theme 3 excluded from Tribal SVI (custom composite from Themes 1+2+4)
- DEC-04: 3-component formula (0.40 hazard + 0.35 social + 0.25 adaptive capacity deficit)
- DEC-05: "Climate Resilience Investment Priority" framing (Hybrid Option D)

## Verification

- [x] All 8 vulnerability models importable from `src.schemas.vulnerability`
- [x] All 8 models re-exported from `src.schemas.__init__`
- [x] 68 new tests covering valid, invalid, and boundary conditions
- [x] DataGapType enum has exactly 6 values
- [x] InvestmentPriorityTier.from_score() classifies all 5 tiers correctly
- [x] CompositeScore model_validator enforces tier/score consistency
- [x] SVIProfile model_validator enforces max 3 themes and composite/mean consistency
- [x] All 1,084 tests pass (964 baseline + 68 new + 52 from parallel plans)
- [x] Zero regressions in existing test suite

## Next Phase Readiness

These schemas are the data contracts for all downstream v1.4 work:
- Plans 19-04 through 19-06 (Wave 2-3) will build on these models
- Phase 20 (Flood & Water) will populate NRIExpanded
- Phase 21 (Climate, Geologic, Infrastructure) will populate CompositeComponent
- Phase 22 (Vulnerability Profiles) will assemble VulnerabilityProfile
- Phase 23 (Document Rendering) will render from these contracts

No blockers. All models ready for consumption.
