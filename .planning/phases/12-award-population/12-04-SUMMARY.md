# Plan 12-04 Summary: Housing Authority Alias Gap Closure

**Status:** Complete
**Commits:** `8949644`, `0cfdaf2`
**Tests:** 606 passed, 0 failed

## What Was Done

### Task 1: Housing Authority Alias Infrastructure
- Created `scripts/generate_ha_aliases.py` — standalone generator that:
  - Programmatically generates HA name patterns from registry short names (suffix stripping, state removal)
  - Includes 70+ curated overrides for USASpending name variants
  - Excludes 18 regional/multi-Tribe authorities (Cook Inlet, Bering Straits, etc.)
  - Produces `data/housing_authority_aliases.json` (15,027 aliases)
- `scripts/build_tribal_aliases.py` already had `_merge_housing_authority_aliases()` — no changes needed
- Created `tests/test_housing_authority_aliases.py` — 26 tests covering:
  - File validity and structure (4 tests)
  - All tribe_ids valid against registry (1 test)
  - 10 known housing authority mappings verified (parametrized)
  - 6 regional authority exclusions verified (parametrized)
  - Alias table integration (2 tests)
  - Matcher resolution with tmp_path fixtures (3 tests)
- Rebuilt `data/tribal_aliases.json`: 18,776 total aliases

### Task 2: Award Population and Coverage Validation
- Ran 5 iterative rounds of curated overrides against live USASpending API:
  - Round 1 (initial HA file): 424/592 (regression from incomplete patterns)
  - Round 2 (suffix stripping + curated): 433/592
  - Round 3 (Red Lake, Colville, Yurok, Fort Peck, Sault, etc.): 439/592
  - Round 4 (Sisseton, Lummi, Shoshone Bannock, Ho-Chunk, etc.): 444/592
  - Round 5 (Apsaalooke/Crow, Puyallup, Penobscot, Ponca, etc.): 448/592
  - Round 6 (San Carlos Tribal Council, Bois Forte, Cheyenne-Arapaho): **451/592 (76.2%)**
- Coverage target: 450+ -- **PASS**
- API resilience: circuit breaker recovered after transient USASpending 500s
- 592 cache files written with enhanced matching results

## Coverage Progression

| Iteration | Tribes | % | Delta |
|-----------|--------|---|-------|
| Pre-gap   | 418    | 70.6% | baseline |
| Round 1   | 424    | 71.6% | +6 |
| Round 2   | 433    | 73.1% | +9 |
| Round 3   | 439    | 74.2% | +6 |
| Round 4   | 444    | 75.0% | +5 |
| Round 5   | 448    | 75.7% | +4 |
| Round 6   | **451** | **76.2%** | +3 |

## Key Decisions
- DEC-1204-01: Housing authority aliases generated programmatically (suffix stripping) + curated overrides (5 rounds)
- DEC-1204-02: Regional Alaska HAs (Cook Inlet, Bering Straits, Interior, etc.) excluded — serve multiple Nations
- DEC-1204-03: BIA-prefixed names (e.g., "DOI TRB WA UPPER SKAGIT") added as curated overrides
- DEC-1204-04: Self-designation names (Apsaalooke = Crow, Sicangu Wicoti = Rosebud) included in curated overrides
- DEC-1204-05: MN Chippewa component bands (Bois Forte, White Earth, Mille Lacs, Fond du Lac, Leech Lake) mapped to parent epa_100000161

## Files Modified
- `scripts/generate_ha_aliases.py` (created) — 270 lines
- `data/housing_authority_aliases.json` (created) — 15,027 aliases
- `data/tribal_aliases.json` (rebuilt) — 18,776 aliases
- `tests/test_housing_authority_aliases.py` (created) — 239 lines, 26 tests
- `data/award_cache/*.json` (regenerated, not committed)
- `outputs/award_population_report.json` (regenerated, not committed)

## Requirement Satisfied
- **AWRD-04:** 451/592 Tribes (76.2%) have at least one non-zero award record (target: 450+)
