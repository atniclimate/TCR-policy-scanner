---
phase: 05-foundation
plan: 03
subsystem: congressional-mapping
tags: [congress, census, delegation, committees, crosswalk]
dependency-graph:
  requires: []
  provides: [congressional_cache, aiannh_crosswalk, congressional_mapper]
  affects: [05-04, 07-xx]
tech-stack:
  added: [pyyaml]
  patterns: [multi-source-cache-build, lazy-loading, atomic-json-write, multi-tier-name-matching]
key-files:
  created:
    - scripts/build_congress_cache.py
    - src/packets/congress.py
    - data/congressional_cache.json
    - data/aiannh_tribe_crosswalk.json
    - data/census/tab20_cd11920_aiannh20_natl.txt
  modified: []
decisions:
  - id: crosswalk-multi-tier
    description: "Four-tier AIANNH-to-Tribe matching: exact variants, substring containment, fuzzy (>=80), unmatched log"
  - id: census-over-crs
    description: "Census CD119-AIANNH relationship file used instead of CRS R48107 PDF (119th Congress, machine-readable)"
  - id: substring-matching
    description: "Substring containment matching added for Alaska ANVSA names (Census 'Akiachak ANVSA' -> EPA 'Akiachak Native Community')"
  - id: 538-members
    description: "Congress.gov API returned 538 members for 119th Congress (not 541 as estimated)"
metrics:
  duration: "~7 minutes"
  completed: 2026-02-10
---

# Phase 5 Plan 3: Congressional Mapping Data Layer Summary

**One-liner:** Census CD119-AIANNH + Congress.gov API + unitedstates YAML assembled into 501-tribe delegation cache with 538 members, 46 committees, and multi-tier crosswalk matching 550/577 AIANNH entities.

## What Was Built

### Build Script (`scripts/build_congress_cache.py`)
Six-step pipeline that assembles `congressional_cache.json` from three data sources:

1. **Step 0:** Download Census CD119-AIANNH relationship file (182KB pipe-delimited, 1270 rows)
2. **Step 1:** Parse Census file -- filter to 683 federal AIANNH rows across 577 unique entities using CLASSFP codes (D1/D2/D3/D5/D8/D6/E1)
3. **Step 2:** Build AIANNH-to-Tribe crosswalk with four-tier matching (exact variants, substring, fuzzy, unmatched log) -- matched 550/577 entities (95.3%)
4. **Step 3:** Fetch 538 members from Congress.gov API for 119th Congress (3 paginated requests at limit=250, X-Api-Key header)
5. **Step 4:** Download and parse committee-membership-current.yaml + committees-current.yaml, index 46 target committees (SLIA, SSAP, SSEG, SSCM, HSII, HSAP and subcommittees)
6. **Step 5-6:** Assemble per-Tribe delegations and write atomic JSON

Supports `--skip-api` for Census-only mode, `--verbose` for debug logging, graceful degradation without tribal_registry.json.

### Runtime Module (`src/packets/congress.py`)
`CongressionalMapper` class with lazy-loading and 10 lookup methods:
- `get_delegation(tribe_id)` -- full delegation record
- `get_senators(tribe_id)` -- deduplicated per state
- `get_representatives(tribe_id)` -- House reps per district
- `get_relevant_committees(tribe_id)` -- committees where delegation serves
- `get_committee_members(committee_id)` -- committee roster
- `get_member(bioguide_id)` -- individual member lookup
- `get_congress_session()` -- returns "119"

### Data Files
- `data/congressional_cache.json` -- 538 members, 46 committees, 501 tribe delegations
- `data/aiannh_tribe_crosswalk.json` -- 550 mappings (214 exact, 329 substring, 7 fuzzy, 27 unmatched)
- `data/census/tab20_cd11920_aiannh20_natl.txt` -- cached Census source file

## Key Verification Results

| Check | Result |
|-------|--------|
| Navajo districts | 4 districts across AZ, NM, UT (66.2%, 23.8%, 8.2%, 1.9% overlap) |
| Navajo senators | 6 (2 AZ, 2 NM, 2 UT) -- no duplicates |
| Navajo representatives | 4 (AZ-02, NM-03, UT-03, NM-02) |
| Alaska tribes on AK-AL | 217 tribes mapped to AK-AL |
| Senator deduplication | No duplicates in any delegation |
| Congress session | "119" |
| SLIA committee | 11 members, Chair: Lisa Murkowski (R-AK) |

## Decisions Made

1. **Census CD119-AIANNH over CRS R48107** -- Census file is machine-readable, current (119th Congress), and has area overlap data. CRS report is 118th Congress PDF.

2. **Four-tier crosswalk matching** -- Single-pass name normalization was insufficient (only 60/577 matched). Added name variant generation (stripping "Native Village of", "ANVSA", etc.), substring containment matching, and fuzzy fallback. Final result: 550/577 (95.3%).

3. **538 members (not 541)** -- Congress.gov API returned 538 current members for 119th Congress. Research estimated 541. Difference is likely vacancies.

4. **46 target committees** -- Indexed all target committees (SLIA, SSAP, SSEG, SSCM, HSII, HSAP) plus their subcommittees, totaling 46 committee/subcommittee records.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Crosswalk matching far too weak with single-pass normalization**
- **Found during:** Task 1, Step 2
- **Issue:** Initial normalize-and-match approach only matched 60/577 entities. Alaska ANVSA names (e.g., "Akiachak ANVSA") did not match EPA names (e.g., "Akiachak Native Community") because normalization only stripped the suffix, leaving a bare name that didn't appear in the lookup keyed by full EPA names.
- **Fix:** Added `_generate_name_variants()` to produce multiple normalized variants by stripping both Census-style and EPA-style prefixes/suffixes, plus a substring containment tier that matches core names within longer names. Result: 550/577 matched (95.3%).
- **Files modified:** scripts/build_congress_cache.py
- **Commit:** c5589ee

## Next Phase Readiness

Plan 05-04 (CLI skeleton) can proceed -- it needs CongressionalMapper which is now delivered. The 27 unmatched AIANNH entities are edge cases (multi-tribal OTSAs, name divergence too large for automated matching). They can be addressed with manual overrides in the crosswalk file.

## Commits

| Hash | Description |
|------|-------------|
| c5589ee | feat(05-03): create congressional cache build script with Census + API + YAML pipeline |
| 74f8d06 | feat(05-03): create CongressionalMapper runtime module for delegation lookups |
