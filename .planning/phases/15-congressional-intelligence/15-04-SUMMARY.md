---
phase: 15
plan: 04
subsystem: congressional-intelligence
tags: [congress-api, bill-detail, relevance-scoring, pydantic, cache-builder]
requires: [15-01]
provides: [bill-detail-fetcher, bill-to-program-mapping, congressional-intel-cache]
affects: [15-05, 15-06, 15-07]
tech-stack:
  added: []
  patterns: [relevance-scoring, sub-endpoint-fetching, atomic-write, pydantic-validation]
key-files:
  created:
    - scripts/build_congressional_intel.py
  modified:
    - src/scrapers/congress_gov.py
    - config/scanner_config.json
    - src/paths.py
decisions:
  - id: DEC-1504-01
    description: "Bill relevance scored with 4 weighted components: subject overlap (0.30), CFDA reference (0.25), committee match (0.20), keyword density (0.25)"
  - id: DEC-1504-02
    description: "Two-phase relevance scoring: initial quick score from title keywords, then full score with detail data after fetch"
  - id: DEC-1504-03
    description: "Voting records deferred pending Senate API availability (House roll call available in Congress.gov API v3 beta for 118th+)"
metrics:
  duration: 4m
  completed: 2026-02-12
---

# Phase 15 Plan 04: Bill Detail Fetcher Summary

**One-liner:** Congress.gov bill detail fetcher with 4 sub-endpoints, weighted relevance scoring, and validated BillIntelligence cache builder

## What Was Done

### Task 1: Add bill detail fetching to CongressGovScraper
Added `_fetch_bill_detail()` async method to `CongressGovScraper` that fetches full bill records from the Congress.gov API v3. The method queries 5 endpoints per bill:

1. **Main bill record** (`/bill/{congress}/{type}/{number}`) -- includes sponsor inline
2. **Actions** (`/actions?limit=250`) -- legislative history steps
3. **Cosponsors** (`/cosponsors?limit=250`) -- cosponsor list with party/state
4. **Subjects** (`/subjects?limit=250`) -- legislative subjects and policy area
5. **Text versions** (`/text?limit=20`) -- bill text URLs by format

Key design decisions:
- 0.3s delay between sub-endpoint fetches for rate limit safety
- Individual try/except per sub-endpoint so one failure does not lose all data
- API key via X-Api-Key header (inherited from scraper __init__)

### Task 2: Congressional intel cache builder and config
Created `scripts/build_congressional_intel.py` with a 4-phase pipeline:

1. **Search**: Use existing paginated `scan()` to collect Tribal-relevant bills
2. **Score**: Compute initial relevance from title keywords, rank top N
3. **Detail fetch**: Call `_fetch_bill_detail()` for top candidates, compute full relevance score
4. **Validate and write**: Validate against `BillIntelligence` Pydantic model, atomic write to `data/congressional_intel.json`

**Bill-to-program relevance scoring (INTEL-03):**
- Subject overlap (weight 0.30): bill's legislativeSubjects vs program keywords
- CFDA/ALN reference (weight 0.25): bill title/subjects mention tracked CFDA numbers
- Committee match (weight 0.20): bill referred to Tribal-relevant committees (SLIA, HSII, SSAP, etc.)
- Keyword density (weight 0.25): Tribal keyword matches in bill title

**Config additions:**
```json
"congressional_intel": {
  "data_path": "data/congressional_intel.json",
  "relevance_threshold": 0.30,
  "max_bills_detail": 50,
  "congress": 119,
  "detail_delay_seconds": 0.3,
  "bill_types": ["hr", "s", "hjres", "sjres"]
}
```

**INTEL-04 delegation enhancement:** Committee data is already present in `congressional_cache.json`. Voting records noted as pending (House roll call available via Congress.gov API v3 beta for 118th+ Congress; Senate votes NOT yet available in the API).

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-1504-01 | 4-component weighted relevance scoring | Balances subject specificity, CFDA precision, committee relevance, and keyword breadth |
| DEC-1504-02 | Two-phase scoring (quick + full) | Avoids fetching bill detail for clearly irrelevant bills; stays within max_bills_detail cap |
| DEC-1504-03 | Voting records deferred | Senate.gov does not provide structured vote data via API; House roll call is beta-only |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added CONGRESSIONAL_INTEL_PATH to src/paths.py**
- **Found during:** Task 2
- **Issue:** The build script needed a centralized path constant for the congressional intel cache file
- **Fix:** Added `CONGRESSIONAL_INTEL_PATH` to `src/paths.py` following established pattern
- **Files modified:** src/paths.py
- **Commit:** 5010be4

**2. [Rule 1 - Bug] Removed unused `import re`**
- **Found during:** Task 2 verification
- **Issue:** `re` was imported but not used in the build script
- **Fix:** Removed the unused import
- **Files modified:** scripts/build_congressional_intel.py
- **Commit:** 5010be4

## Verification Results

| Check | Result |
|-------|--------|
| `_fetch_bill_detail()` exists with 4 sub-endpoints | PASS |
| `build_congressional_intel.py` syntax valid | PASS |
| Config has `congressional_intel` section | PASS |
| No API keys in URL query params | PASS |
| No hardcoded fiscal years | PASS |
| `encoding="utf-8"` on all file operations | PASS |
| All 743 existing tests pass | PASS |

## Commits

| Hash | Message |
|------|---------|
| 7c54426 | feat(15-04): add bill detail fetcher to CongressGovScraper |
| 5010be4 | feat(15-04): create congressional intel cache builder and config |

## Next Phase Readiness

Plan 15-05 (DOCX renderers) can now consume:
- `CongressGovScraper._fetch_bill_detail()` for real-time bill detail
- `data/congressional_intel.json` cache file with validated BillIntelligence records
- Relevance scores and matched_programs for bill-to-program mapping
- Config-driven parameters for all thresholds and limits

No blockers identified for downstream plans.
