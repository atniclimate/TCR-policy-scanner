# Roadmap: TCR Policy Scanner v1.2

## Overview

v1.2 transforms 592 Tribal advocacy packets from framework to tool by populating the three empty data sections (awards, hazards, economic impact) with real federal data. Prerequisite tech debt -- config hardening, code quality, API resilience -- is addressed first so data population runs reliably against live APIs. After v1.2, packet completeness rises from ~39% to ~87% and every Tribal Leader gets a document backed by real numbers.

## Phases

**Phase Numbering:**
- Integer phases (9, 10, ...): Planned milestone work (continues from v1.1 Phase 8)
- Decimal phases (9.1, etc): Urgent insertions if needed

**Wave Notation:** Phases in the same wave can execute in parallel.

```
Wave 1:  Phase 9 (Config) ────────┐
         Phase 10 (Quality) ──────┤
                                   v
Wave 2:  Phase 11 (API Resilience)┐
         Phase 12 (Awards) ───────┤
                                   v
Wave 3:  Phase 13 (Hazards) ─────┐
         Phase 14 (Integration) ──┘  (14 depends on 11+12+13)
```

- [ ] **Phase 9: Config Hardening** -- All file paths resolve via config or pathlib; zero hardcoded path strings in source
- [ ] **Phase 10: Code Quality** -- Codebase passes ruff clean with complete program inventory and no dead code
- [ ] **Phase 11: API Resilience** -- Pipeline survives API outages via circuit breakers and graceful cache fallback
- [ ] **Phase 12: Award Population** -- 450+ Tribes have real USASpending award data in their cache files
- [ ] **Phase 13: Hazard Population** -- 550+ Tribes have real FEMA NRI hazard scores and ranked risks
- [ ] **Phase 14: Integration & Validation** -- End-to-end packets produce complete, data-backed documents for 400+ Tribes

## Phase Details

### Phase 9: Config Hardening
**Goal**: Every file path in the codebase resolves through configuration or pathlib -- no hardcoded path strings survive in source code
**Wave**: 1
**Depends on**: None (entry point)
**Requirements**: CONF-01, CONF-02
**Success Criteria** (what must be TRUE when this phase completes):
  1. Running `rg "structural_asks" src/` returns zero hardcoded path strings for structural asks
  2. A centralized `src/paths.py` module exists and all source files import paths from it (not constructing ad-hoc)
  3. Changing a data directory location in one place propagates to all consumers without code changes
  4. All 383+ existing tests still pass after path refactoring
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md -- Structural asks path resolution via config/pathlib [Wave 1]
- [ ] 09-02-PLAN.md -- Centralized path constants module (src/paths.py) [Wave 1]

---

### Phase 10: Code Quality
**Goal**: Codebase is lint-clean with complete program metadata and no dead code or unused imports
**Wave**: 1 (parallel with Phase 9)
**Depends on**: None (entry point)
**Requirements**: QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE when this phase completes):
  1. All 16 programs in `program_inventory.json` have non-null values for cfda, access_type, and funding_type fields
  2. `ruff check .` exits with zero violations
  3. No unused imports remain in any source file under `src/`
  4. All 383+ existing tests still pass after cleanup
**Plans**: 2 plans

Plans:
- [ ] 10-01-PLAN.md -- Complete program_inventory.json field coverage [Wave 1]
- [ ] 10-02-PLAN.md -- Dead code removal and ruff-clean codebase [Wave 1]

---

### Phase 11: API Resilience
**Goal**: Pipeline survives external API outages gracefully -- circuit breakers prevent cascade failures, cached data keeps packets flowing
**Wave**: 2
**Depends on**: Phase 9, Phase 10 (clean codebase + centralized paths needed before wrapping API calls)
**Requirements**: RESL-01, RESL-02, RESL-03, RESL-04
**Success Criteria** (what must be TRUE when this phase completes):
  1. All external API calls (4 scrapers + USASpending) are wrapped in a circuit breaker that transitions through CLOSED/OPEN/HALF_OPEN states
  2. Retry counts and backoff multipliers are configurable in `scanner_config.json` (not hardcoded)
  3. When an API is unreachable, the pipeline completes using cached data and logs a degradation warning
  4. A health check command reports availability status (UP/DOWN/DEGRADED) for all 4 API sources
  5. At least 15 new tests cover circuit breaker state transitions and graceful degradation paths
**Plans**: 2 plans

Plans:
- [ ] 11-01-PLAN.md -- Circuit breaker implementation + configurable retry/backoff [Wave 2]
- [ ] 11-02-PLAN.md -- Graceful degradation (cache fallback) + health check command [Wave 2]

---

### Phase 12: Award Population
**Goal**: Real USASpending award data populates cache files for 592 Tribes, with 450+ having at least one non-zero award record
**Wave**: 2 (parallel with Phase 11)
**Depends on**: Phase 9, Phase 10 (centralized paths + clean code for new award scripts)
**Requirements**: AWRD-01, AWRD-02, AWRD-03, AWRD-04
**Success Criteria** (what must be TRUE when this phase completes):
  1. Award population queries USASpending by CFDA number (11 batch queries, not 592 per-Tribe queries)
  2. Tribe matching uses a curated alias table first, then rapidfuzz fallback at >= 85 score for unmatched recipients
  3. 592 award cache JSON files contain real data (not placeholder/empty structures)
  4. 450+ Tribes have at least one non-zero award record with plausible obligation amounts
**Plans**: 3 plans

Plans:
- [ ] 12-01-PLAN.md -- Batch USASpending query engine (CFDA-based) [Wave 2]
- [ ] 12-02-PLAN.md -- Two-tier Tribe name matching (alias table + rapidfuzz) [Wave 2]
- [ ] 12-03-PLAN.md -- Award cache population + coverage validation [Wave 2]

---

### Phase 13: Hazard Population
**Goal**: Real FEMA NRI hazard data populates profile files for 592 Tribes via geographic crosswalk, with 550+ having scored risk profiles
**Wave**: 3
**Depends on**: Phase 9, Phase 10 (centralized paths for new data scripts)
**Requirements**: HZRD-01, HZRD-02, HZRD-03, HZRD-04, HZRD-05, HZRD-06
**Success Criteria** (what must be TRUE when this phase completes):
  1. FEMA NRI county-level dataset is downloaded and cached locally
  2. A Tribe-to-county geographic crosswalk maps AIANNH boundaries to overlapping counties with area weights
  3. County NRI scores are aggregated to the Tribe level using area-weighted averaging
  4. Each Tribe with county data has its top 5 hazards extracted, ranked, and stored in the hazard profile
  5. 300+ Tribes in fire-prone regions have USFS wildfire risk data populated
  6. 550+ of 592 hazard profile JSON files contain real scored data (not placeholders)
**Plans**: 3 plans

Plans:
- [ ] 13-01-PLAN.md -- FEMA NRI download + Tribe-to-county geographic crosswalk [Wave 3]
- [ ] 13-02-PLAN.md -- NRI score aggregation + top-5 hazard extraction per Tribe [Wave 3]
- [ ] 13-03-PLAN.md -- USFS wildfire data + hazard cache population for 592 Tribes [Wave 3]

---

### Phase 14: Integration & Validation
**Goal**: All data sources wire together so end-to-end packet generation produces complete, data-backed advocacy documents for 400+ Tribes
**Wave**: 3 (after Phases 11, 12, 13 complete)
**Depends on**: Phase 11, Phase 12, Phase 13 (all data populated + API resilience in place)
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04, INTG-05, INTG-06
**Success Criteria** (what must be TRUE when this phase completes):
  1. Economic impact section auto-computes using real award amounts and hazard scores (no placeholder fallbacks)
  2. Batch packet generation for all 592 Tribes completes without error, producing complete packets for 400+
  3. A data validation script reports coverage percentages across all cache types (awards, hazards, congressional, registry)
  4. VERIFICATION.md documents the v1.2 testing methodology, sample validation results, and known coverage gaps
  5. GitHub Pages deployment serves updated packets with production URLs (no SquareSpace placeholders)
**Plans**: 3 plans

Plans:
- [ ] 14-01-PLAN.md -- Economic impact activation + end-to-end packet validation [Wave 3]
- [ ] 14-02-PLAN.md -- Data validation script + VERIFICATION.md documentation [Wave 3]
- [ ] 14-03-PLAN.md -- GitHub Pages deployment config + production URL finalization [Wave 3]

---

## Progress

| Phase | Plans | Plans Complete | Status | Completed |
|-------|-------|----------------|--------|-----------|
| 9 - Config Hardening | 2 | 0 | Pending | -- |
| 10 - Code Quality | 2 | 0 | Pending | -- |
| 11 - API Resilience | 2 | 0 | Pending | -- |
| 12 - Award Population | 3 | 0 | Pending | -- |
| 13 - Hazard Population | 3 | 0 | Pending | -- |
| 14 - Integration & Validation | 3 | 0 | Pending | -- |
| **Total** | **15** | **0** | -- | -- |

## Dependency & Wave Summary

| Wave | Phases | Can Parallelize | Depends On |
|------|--------|-----------------|------------|
| Wave 1 | Phase 9, Phase 10 | Yes (independent) | None |
| Wave 2 | Phase 11, Phase 12 | Yes (independent) | Wave 1 |
| Wave 3 | Phase 13, Phase 14 | Phase 13 first, then Phase 14 | Phase 13 depends on Wave 1; Phase 14 depends on 11+12+13 |

## Coverage

```
CONF-01 -> Phase 9
CONF-02 -> Phase 9
QUAL-01 -> Phase 10
QUAL-02 -> Phase 10
RESL-01 -> Phase 11
RESL-02 -> Phase 11
RESL-03 -> Phase 11
RESL-04 -> Phase 11
AWRD-01 -> Phase 12
AWRD-02 -> Phase 12
AWRD-03 -> Phase 12
AWRD-04 -> Phase 12
HZRD-01 -> Phase 13
HZRD-02 -> Phase 13
HZRD-03 -> Phase 13
HZRD-04 -> Phase 13
HZRD-05 -> Phase 13
HZRD-06 -> Phase 13
INTG-01 -> Phase 14
INTG-02 -> Phase 14
INTG-03 -> Phase 14
INTG-04 -> Phase 14
INTG-05 -> Phase 14
INTG-06 -> Phase 14

Mapped: 24/24
Orphaned: 0
Duplicates: 0
```

---
*Roadmap created: 2026-02-11*
*Depth: quick*
*Coverage: 24/24 requirements mapped*
*Phases: 6 (numbered 9-14, continuing from v1.1)*
*Plans: 15 total*
