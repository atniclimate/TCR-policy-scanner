---
phase: 15
plan: 06
subsystem: testing
tags: [pytest, pydantic, pagination, docx-rendering, confidence-scoring]
depends_on: [15-01, 15-02, 15-04, 15-05]
provides:
  - 167 new tests for Phase 15 congressional intelligence
  - Total suite: 951 tests (exceeds 900 target)
  - Pagination coverage for all 4 scrapers
  - Model validation coverage for all 5 congressional models
  - Confidence scoring boundary tests
  - DOCX rendering audience differentiation verification
affects: [15-07, 16]
tech-stack:
  added: []
  patterns: [asyncio.run for pytest-anyio compatibility, table-cell-text extraction for DOCX rendering tests]
key-files:
  created:
    - tests/test_congressional_models.py
    - tests/test_confidence.py
    - tests/test_pagination.py
    - tests/test_congressional_rendering.py
  modified: []
decisions:
  - id: DEC-1506-01
    decision: Use asyncio.run() instead of asyncio.get_event_loop().run_until_complete() for scraper pagination tests to avoid event loop conflicts with pytest-anyio
  - id: DEC-1506-02
    decision: Regional congressional section tests extract text from both paragraphs and table cells since bill data renders in tables
metrics:
  duration: ~14 minutes
  completed: 2026-02-12
  tests_added: 167
  total_tests: 951
---

# Phase 15 Plan 06: Test Suite Summary

167 new tests across 4 test files covering congressional intelligence models, confidence scoring, scraper pagination, and DOCX rendering with audience differentiation. Total suite: 951 tests (target was 900+).

## Completed Tasks

| Task | Name | Commit | Tests Added |
|------|------|--------|-------------|
| 1 | Congressional model + confidence tests | d8bed29 | 90 (58 model + 32 confidence) |
| 2 | Pagination + rendering tests | ceb6216 | 77 (46 pagination + 31 rendering) |

## Test Breakdown

### test_congressional_models.py (58 tests)
- **BillAction** (8): Construction, defaults, missing required, serialization, chamber variants
- **BillIntelligence** (25): All 8 bill type codes accepted, 7 invalid types rejected, relevance_score range [0,1], cosponsor_count >= 0, nested BillAction list, latest_action, sponsor dict, matched_programs, serialization roundtrip, real-world data sample, missing required fields
- **VoteRecord** (5): Construction, defaults, missing vote_id, Senate vote, serialization
- **Legislator** (5): Construction, defaults, missing bioguide/name, committee list
- **CongressionalIntelReport** (8): Construction, defaults, bills list, empty bills, nested bill validation, confidence dict, tribe_id validation, delegation_enhanced flag

### test_confidence.py (32 tests)
- **compute_confidence** (15): Fresh data, stale data (69-day half-life), very stale (365 days), invalid date, None date, custom decay_rate, custom reference_date, future date, weight 0.0/1.0, timezone-aware/naive, known values, rounding, default reference
- **confidence_level** (9): All threshold boundaries at 0.7, 0.4, and intermediate values
- **section_confidence** (8): Known source weight, unknown fallback, dict structure, fresh/stale, per-source weights (grants_gov, usaspending, inferred)

### test_pagination.py (46 tests)
- **Congress.gov** (14): Single/multi-page, empty, safety cap 2500, dedup, error on page 2, broad search variants, _normalize, pagination metadata, stops at limit, _fetch_bill_detail with sub-endpoints, sub-endpoint error handling
- **Federal Register** (12): Single/multi-page, empty, safety cap 20 pages, missing total_pages default, agency sweep single/multi/cap, _normalize, ICR/guidance detection, stops on empty
- **Grants.gov** (12): CFDA single/multi-page, empty, safety cap 1000, keyword single/multi/cap, Tribal eligibility detection, startRecordNum offset verification, _normalize, stops on empty
- **USASpending** (8): Single/multi-page, empty, safety cap 5000, hasNext truncation, _normalize, error recovery, page-number pagination

### test_congressional_rendering.py (31 tests)
- **render_bill_intelligence_section** (19): Empty bills, empty intel, Doc A heading, Doc B heading, Doc A talking points, Doc B no talking points, Doc B zero strategy words, confidence badge, sort by relevance, single bill, 10+ bills, sponsor/committees/affected programs in Doc A, Doc B relevance filter, Doc B all-below-threshold message, Doc B facts-only content, default compact cards, timing note
- **DocxEngine ordering** (5): Bill intelligence in document, bills before delegation, missing/None intel no crash, Doc B section
- **Regional congressional** (5): Shared bill aggregation, empty bills message, confidence badge, Doc C coordination note, unique bills from different Tribes
- **Air gap verification** (2): Comprehensive zero-strategy-words check, facts-only content validation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] asyncio event loop compatibility**
- **Found during:** Task 2 full-suite verification
- **Issue:** `asyncio.get_event_loop().run_until_complete()` fails when pytest-anyio closes the event loop after other test files run
- **Fix:** Replaced all instances with `asyncio.run()` which creates a fresh event loop per test
- **Files modified:** tests/test_pagination.py

**2. [Rule 1 - Bug] Regional bill data in tables not paragraphs**
- **Found during:** Task 2 regional rendering tests
- **Issue:** `render_regional_congressional_section` puts bill data in table cells, not paragraphs; text extraction missed table content
- **Fix:** Added `_get_all_doc_text()` helper that extracts text from both paragraphs and table cells; fixed bill_number override in mock data
- **Files modified:** tests/test_congressional_rendering.py

## Success Criteria Verification

| Criterion | Status |
|-----------|--------|
| INTEL-09: 157+ new tests | PASS (167 new tests) |
| Total exceeds 900 | PASS (951 total) |
| Pagination tests for all 4 scrapers | PASS (14+12+12+8 = 46 tests) |
| Congressional model validation tests | PASS (58 tests across 5 models) |
| Confidence scoring unit tests | PASS (32 tests with boundary conditions) |
| DOCX rendering audience differentiation | PASS (Doc A vs Doc B verified, air gap confirmed) |
