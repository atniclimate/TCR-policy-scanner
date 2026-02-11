---
phase: 13-hazard-population
plan: 01
subsystem: data-pipeline
tags: [fema-nri, census-tiger, aiannh, crosswalk, geopandas, geospatial, area-weights]

# Dependency graph
requires: []
provides:
  - NRI county CSV + tribal relational CSV download script with retry and atomic writes
  - Census TIGER/Line AIANNH and county shapefile download script
  - Area-weighted AIANNH-to-county crosswalk build script (dual-CRS)
  - TRIBAL_COUNTY_WEIGHTS_PATH constant in src/paths.py
  - Geospatial dependencies (geopandas, shapely, pyproj, pyogrio) in requirements.txt
affects: [13-02 (hazard profile builder), 13-03 (hazard integration), 14-integration]

# Tech tracking
tech-stack:
  added:
    - "geopandas>=1.0.0 (geospatial data processing)"
    - "shapely>=2.0.0 (geometric operations)"
    - "pyproj>=3.3.0 (CRS projections)"
    - "pyogrio>=0.7.2 (fast shapefile I/O)"
    - "requests>=2.31.0 (HTTP downloads with streaming)"
  patterns:
    - "Dual-CRS: EPSG:3338 for Alaska, EPSG:5070 for CONUS equal-area calculations"
    - "Area-weighted crosswalk: geometric intersection with normalized weights per AIANNH GEOID"
    - "1% minimum overlap filter to remove sliver intersections from boundary digitization artifacts"
    - "Streaming download with retry: temp file + os.replace() atomic write pattern"

key-files:
  created:
    - scripts/download_nri_data.py
    - scripts/build_area_crosswalk.py
  modified:
    - src/paths.py
    - requirements.txt
    - .gitignore

key-decisions:
  - "DEC-1301-01: data/nri/ added to .gitignore since it contains large downloaded data files (shapefiles, CSVs)"
  - "DEC-1301-02: requests library added to requirements.txt for download script (aiohttp not needed for sync downloads)"
  - "DEC-1301-03: Shapefile ZIPs extract to subdirectories (aiannh/, county/) to keep data/nri/ organized"

patterns-established:
  - "Geospatial download + build pattern: download_nri_data.py fetches raw data, build_area_crosswalk.py processes it"
  - "Dual-CRS projection: split features by STATEFP, project Alaska to EPSG:3338 and CONUS to EPSG:5070"
  - "Weight normalization: raw overlap percentages normalized to sum to 1.0 per GEOID after minimum threshold filter"

# Metrics
duration: 22min
completed: 2026-02-11
---

# Phase 13 Plan 01: NRI Data Download and Area Crosswalk Summary

**FEMA NRI + Census TIGER download scripts and geopandas-based AIANNH-to-county area-weighted crosswalk builder with dual-CRS projection (EPSG:5070 CONUS + EPSG:3338 Alaska) and 1% minimum overlap filter**

## Performance

- **Duration:** 22 min
- **Started:** 2026-02-11T15:00:15Z
- **Completed:** 2026-02-11T15:22:44Z
- **Tasks:** 2/2
- **Files created:** 2 (scripts/download_nri_data.py, scripts/build_area_crosswalk.py)
- **Files modified:** 3 (src/paths.py, requirements.txt, .gitignore)

## Accomplishments

- Download script fetches 4 files: NRI county CSV, NRI tribal-county relational CSV, AIANNH shapefile, county shapefile
- Streaming download with retry (2 attempts, 5-second delay) and atomic write pattern
- Skip-if-exists logic with --force override for re-downloads
- Area crosswalk script loads shapefiles, splits by Alaska vs CONUS, projects to equal-area CRS
- Geometric intersection via gpd.overlay() computes overlap areas between AIANNH and county boundaries
- 1% minimum overlap filter removes sliver intersections from boundary digitization artifacts
- Weights normalized to sum to 1.0 per AIANNH GEOID for downstream hazard aggregation
- TRIBAL_COUNTY_WEIGHTS_PATH added to src/paths.py (imports only pathlib.Path, per DEC-0901-01)
- Geospatial dependencies (geopandas, shapely, pyproj, pyogrio) added to requirements.txt
- data/nri/ added to .gitignore for large downloaded files
- All 469 existing tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: NRI data download script + paths constant + dependencies** - `43e5749` (feat)
2. **Task 2: Area-weighted AIANNH-to-county crosswalk build script** - `64dbab9` (feat)

## Files Created/Modified

- `scripts/download_nri_data.py` - Downloads FEMA NRI CSVs and Census TIGER shapefiles with retry, progress, and atomic writes (222 lines)
- `scripts/build_area_crosswalk.py` - Geopandas-based AIANNH-to-county area intersection and weight computation with dual-CRS (435 lines)
- `src/paths.py` - Added TRIBAL_COUNTY_WEIGHTS_PATH constant pointing to data/nri/tribal_county_area_weights.json
- `requirements.txt` - Added requests, geopandas, shapely, pyproj, pyogrio dependencies
- `.gitignore` - Added data/nri/ for large downloaded data files

## Decisions Made

- **DEC-1301-01:** data/nri/ added to .gitignore since downloaded shapefiles and CSVs are large binary/text files that should not be version-controlled
- **DEC-1301-02:** requests library added for synchronous streaming downloads (simpler than aiohttp for CLI script that doesn't need async)
- **DEC-1301-03:** Shapefile ZIPs extract to named subdirectories (aiannh/, county/) for organization and to avoid filename collisions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added data/nri/ to .gitignore**
- **Found during:** Task 1
- **Issue:** Downloaded NRI CSVs and Census TIGER shapefiles are large files (10-100+ MB) that should not be committed to git
- **Fix:** Added `data/nri/` to .gitignore
- **Files modified:** .gitignore
- **Committed in:** `43e5749` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (missing critical)
**Impact on plan:** Necessary for correct git hygiene. No scope creep. All planned functionality delivered.

## Issues Encountered

None.

## User Setup Required

Before running the crosswalk builder, install geospatial dependencies and download data:
```bash
pip install -r requirements.txt
python scripts/download_nri_data.py
python scripts/build_area_crosswalk.py
```

## Next Phase Readiness

- **Plan 13-02:** Can build hazard profile population script that reads the crosswalk JSON and NRI county CSV
- **Plan 13-03:** Integration testing once hazard profiles are populated
- **No blockers** for subsequent plans

---
*Phase: 13-hazard-population*
*Completed: 2026-02-11*
