---
phase: "05"
plan: "02"
subsystem: "tribal-registry"
tags: ["epa-api", "tribal-data", "fuzzy-matching", "rapidfuzz", "registry"]
dependency_graph:
  requires: []
  provides: ["tribal-registry-data", "tribal-name-resolution", "build-script"]
  affects: ["05-04", "06-01", "06-02", "07-01", "08-01"]
tech_stack:
  added: []
  patterns: ["lazy-loading", "3-tier-resolution", "atomic-write", "async-fetch"]
key_files:
  created:
    - "scripts/build_registry.py"
    - "data/tribal_registry.json"
    - "src/packets/registry.py"
  modified: []
decisions:
  - id: "DEC-0502-01"
    description: "Use WRatio scorer instead of token_sort_ratio for fuzzy matching"
    rationale: "token_sort_ratio gives ~20% scores for short queries against long multi-word tribe names; WRatio auto-selects partial matching and handles length disparity"
  - id: "DEC-0502-02"
    description: "EPA API returns text/plain content type -- parse JSON from text response"
    rationale: "aiohttp rejects resp.json() when content type is not application/json; read as text and json.loads() works correctly"
  - id: "DEC-0502-03"
    description: "Registry contains 592 tribes (not 574 as originally estimated)"
    rationale: "EPA API now returns 592 records with AllTribes filter; original estimate was from truncated WebFetch during research"
metrics:
  duration: "~5 minutes"
  completed: "2026-02-10"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 05 Plan 02: Tribal Registry Data Layer Summary

**One-liner:** EPA API fetcher + lazy-loaded TribalRegistry with exact/substring/fuzzy name resolution over 592 tribes

## What Was Built

### scripts/build_registry.py
One-time async script that fetches all federally recognized Tribes from the EPA Tribes Names Service API (`/api/v1/tribeDetails?tribalBandFilter=AllTribes`). Transforms raw EPA records into standardized schema with `epa_*` primary keys, extracts states from structured `epaLocations` array, collects historical name variants for search corpus, and writes `data/tribal_registry.json` using atomic tmp+replace pattern. Falls back to a 5-tribe placeholder if the API is unreachable.

### data/tribal_registry.json
592 tribe records fetched from EPA API on 2026-02-10. Each record contains: `tribe_id` (epa_* primary key), `bia_code` (optional, "TBD" for 235 Alaska entities), `name`, `states`, `alternate_names`, `epa_region`, `tribal_band_flag`, and `bia_recognized`. Metadata tracks source, fetch timestamp, and counts.

### src/packets/registry.py
Runtime `TribalRegistry` class with:
- **Lazy loading:** JSON parsed on first data access, not at construction
- **Tier 1 -- Exact match:** Case-insensitive match on official `name` field
- **Tier 2 -- Substring:** Searches `name` + `alternate_names`; returns single dict if unambiguous, list if multiple matches
- **Tier 3 -- Fuzzy:** rapidfuzz `WRatio` scorer with score_cutoff=60; handles short queries against long multi-word names
- **Search corpus:** 1216 entries (592 names + 624 alternates), cached after first build
- **API:** `resolve()`, `fuzzy_search()`, `get_by_id()`, `get_all()`

## Task Completion

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create build_registry.py + fetch tribes | `e2fca93` | scripts/build_registry.py, data/tribal_registry.json |
| 2 | Create TribalRegistry runtime module | `4d8ca27` | src/packets/registry.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] EPA API returns text/plain content type**
- **Found during:** Task 1 execution
- **Issue:** aiohttp's `resp.json()` raises ContentTypeError because EPA API returns `text/plain;charset=utf-8` instead of `application/json`
- **Fix:** Changed to `resp.text(encoding="utf-8")` followed by `json.loads(text)`
- **Files modified:** scripts/build_registry.py
- **Commit:** e2fca93

**2. [Rule 1 - Bug] token_sort_ratio ineffective for short queries**
- **Found during:** Task 2 verification
- **Issue:** `token_sort_ratio` scored "Navaho" at only 20.8% against "Navajo Nation, Arizona, New Mexico, & Utah" because it distributes weight across all tokens in the long name
- **Fix:** Switched Tier 3 scorer to `fuzz.WRatio` which auto-selects partial matching strategy and handles length disparity (scores "Navaho" at 60+ against Navajo names)
- **Files modified:** src/packets/registry.py
- **Commit:** 4d8ca27

## Data Profile

| Metric | Value |
|--------|-------|
| Total tribes | 592 |
| Unique tribe_ids | 592 (0 duplicates) |
| BIA code TBD (Alaska) | 235 |
| Search corpus entries | 1216 |
| Alternate names | 624 |
| Lumbee Tribe | Not in EPA data (warning logged) |

## Decisions Made

1. **WRatio over token_sort_ratio** (DEC-0502-01): WRatio automatically handles partial matching for short queries against long tribe names. This is critical for user-facing name resolution where queries like "Navaho" or "Seminol" need to match.

2. **Text response parsing** (DEC-0502-02): EPA API serves JSON with text/plain content type. Standard practice for government APIs with non-standard content types.

3. **592 tribes instead of 574** (DEC-0502-03): The EPA API now returns 592 records with AllTribes filter. This exceeds the original research estimate of ~574 (which was based on truncated WebFetch responses). The additional records may include recently added tribal bands.

## Verification Results

All checks passed:
- `build_registry.py --verbose` runs successfully, fetches 592 tribes
- `tribal_registry.json` is valid JSON with correct schema
- No duplicate tribe_id values
- All Alaska entries have valid `epa_*` IDs (not `bia_TBD`)
- Tier 1 exact match: "Navajo Nation, Arizona, New Mexico, & Utah" -> correct dict
- Tier 2 substring: "Choctaw" -> 3 matches (ambiguous list)
- Tier 2 substring: "Tlingit" -> 2 matches
- Tier 3 fuzzy: "Navaho" -> matches including Navajo Nation
- `get_by_id("epa_100000171")` -> Navajo Nation
- `get_all()` -> 592 tribes
- Lumbee absence logged as warning (not error)

## Next Phase Readiness

This plan provides the foundation for all downstream modules:
- **05-04 (Config):** Can reference `data/tribal_registry.json` path in packet config
- **06-01 (Congressional):** Uses `TribalRegistry.get_all()` for state-based district mapping
- **06-02 (Awards):** Uses `TribalRegistry.resolve()` for name matching against USASpending
- **07-01 (Computation):** Uses registry as the canonical tribe list for packet generation
- **08-01 (Assembly):** Uses `TribalRegistry.get_by_id()` for per-tribe DOCX generation

No blockers. The Lumbee Tribe absence is expected and handled (warning, not error).
