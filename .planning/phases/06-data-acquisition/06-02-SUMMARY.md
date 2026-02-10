# Phase 6 Plan 02: Hazard Profiling Pipeline Summary

**One-liner:** HazardProfileBuilder with FEMA NRI county CSV ingestion (18 hazard types), USFS wildfire XLSX parsing with schema discovery, AIANNH crosswalk bridging, and 592 per-Tribe hazard profile JSON cache files.

## Execution Details

| Field | Value |
|-------|-------|
| Phase | 06-data-acquisition |
| Plan | 02 |
| Status | Complete |
| Tasks | 1/1 |
| Duration | ~4 minutes |
| Completed | 2026-02-10 |
| Tests | 83/83 passing (no regressions) |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `2e5a01d` | feat | Add HazardProfileBuilder with NRI + USFS ingestion pipeline |

## Files Created

| File | Purpose |
|------|---------|
| `src/packets/hazards.py` | HazardProfileBuilder class: NRI county CSV parsing, USFS XLSX parsing, AIANNH crosswalk bridging, per-Tribe profile aggregation and caching |
| `data/hazard_profiles/*.json` | 592 per-Tribe hazard profile cache files (one per Tribe, currently sparse/empty awaiting NRI/USFS data download) |

## Files Modified

| File | Changes |
|------|---------|
| `requirements.txt` | Added `openpyxl>=3.1.0` for USFS XLSX parsing |

## Key Design Decisions

1. **MAX aggregation for risk, SUM for losses**: Per-hazard risk scores use MAX across overlapping counties (conservative, highlights worst-case exposure). Expected annual loss (EAL) uses SUM to reflect total exposure. Social vulnerability uses MAX (worst), community resilience uses MIN (worst).
2. **State-level fallback**: When NRI tribal relational CSV is unavailable or a Tribe has no AIANNH-to-county mapping, falls back to matching all counties in the Tribe's state(s). Less precise but ensures every Tribe gets some hazard data.
3. **Schema discovery for USFS XLSX**: Since USFS column names are uncertain (LOW confidence from research), the parser inspects headers by keyword matching (geoid, name, risk, likelihood) rather than hardcoding column names.
4. **Tribal relational CSV column discovery**: NRI tribal relational CSV column names are also discovered dynamically (MEDIUM confidence) -- searches for GEOID/AIANNH and STCOFIPS/COUNTYFIPS patterns.
5. **Empty profiles for unmatched Tribes**: All 592 Tribes get a cache file even with zero data -- includes a `note` field explaining why data is missing. This ensures downstream DOCX generation never crashes on missing cache.
6. **Reverse crosswalk**: Built tribe_id -> list[GEOID] inverse mapping to handle the 20 Tribes spanning multiple AIANNH areas (e.g., epa_100000161 spans 7 AIANNH boundaries).

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| `pip show openpyxl` confirms installation | Pass (3.1.5) |
| `from src.packets.hazards import HazardProfileBuilder` | Pass |
| `NRI_HAZARD_CODES` has 18 entries | Pass |
| `_safe_float()` handles None, empty, non-numeric | Pass |
| Missing NRI CSV handled gracefully (warning, not crash) | Pass |
| Missing NRI directory handled gracefully | Pass |
| Missing USFS directory handled gracefully | Pass |
| `build_all_profiles()` writes 592 cache files | Pass |
| Cache file JSON structure matches schema spec | Pass |
| 83/83 existing tests passing | Pass |

## Downstream Dependencies

- **Phase 6 Plan 03** (06-03): May reference hazard profiles for integration testing
- **Phase 7**: DOCX generation will read `data/hazard_profiles/{tribe_id}.json` for hazard sections
- **Phase 7**: Economic impact multiplier math requires float values (confirmed: all numeric values stored as float)

## Data Pipeline Notes

The hazard profiles are currently **sparse/empty** because NRI and USFS source data files have not been downloaded yet. To populate with real data:

1. **NRI County Data**: Download from https://hazards.fema.gov/nri/data-resources -> place `NRI_Table_Counties.csv` in `data/nri/`
2. **NRI Tribal Relational**: Download tribal county relational CSV -> place in `data/nri/` (filename must contain "Tribal" and "Relational")
3. **USFS Wildfire Risk**: Download from https://wildfirerisk.org/ -> place XLSX in `data/usfs/`
4. Re-run `build_all_profiles()` to populate all 592 cache files with real scores

The code gracefully handles all combinations of available/missing source files.

## Architecture

```
FEMA NRI County CSV ──┐
                      ├──> HazardProfileBuilder ──> data/hazard_profiles/{tribe_id}.json
NRI Tribal Relational ┤                              (592 files)
                      │
AIANNH Crosswalk ─────┤    Aggregation:
                      │    - Risk: MAX across counties
USFS Wildfire XLSX ───┘    - EAL: SUM across counties
                           - Top 3 hazards by risk score
```
