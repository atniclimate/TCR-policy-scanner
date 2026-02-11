# Phase 13: Hazard Population - Research

**Researched:** 2026-02-11
**Domain:** FEMA NRI data ingestion, geographic crosswalk, USFS wildfire data, area-weighted aggregation
**Confidence:** MEDIUM (see breakdown below)

## Summary

Phase 13 requires downloading FEMA National Risk Index (NRI) v1.20 county-level data, building a Tribe-to-county geographic crosswalk with area weights, aggregating NRI scores to the Tribe level using area-weighted averaging, and layering in USFS Wildfire Risk to Communities data. The existing `src/packets/hazards.py` (936 lines) has substantial scaffolding but uses MAX aggregation instead of area-weighted averaging and extracts top 3 hazards instead of the required top 5.

The critical architectural question is whether the FEMA NRI Tribal County Relational CSV includes area weights. Research strongly indicates it does NOT -- it provides binary overlap flags (which AIANNH areas overlap which counties) but not area proportions. This means computing area weights requires geospatial intersection of AIANNH and county shapefiles, which necessitates adding geopandas/shapely as dependencies.

**Primary recommendation:** Add geopandas + shapely to requirements.txt. Pre-compute the area-weighted crosswalk as a one-time script (like `scripts/build_registry.py`), output a JSON crosswalk file, then use that crosswalk in the main pipeline without runtime geospatial dependencies. This keeps the runtime lightweight while enabling accurate area weighting.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| geopandas | >=1.0.0 | Shapefile I/O + geometric overlay | Standard Python geospatial library; binary wheels now available for Windows via pip |
| shapely | >=2.0.0 | Geometry intersection + area calculation | Underlying geometry engine for geopandas; C-backed (GEOS) for performance |
| pyproj | >=3.3.0 | CRS transformations (to equal-area for accurate area calc) | Required for projecting WGS84 shapefiles to equal-area CRS |
| pyogrio | >=0.7.2 | Fast shapefile/GDB I/O backend for geopandas | Default geopandas I/O engine since v1.0; faster than fiona |

### Supporting (Already in requirements.txt)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openpyxl | >=3.1.0 | USFS XLSX parsing | Already installed; used for USFS wildfire data |
| csv (stdlib) | - | NRI CSV parsing | Already used in hazards.py |
| json (stdlib) | - | Profile JSON I/O | Already used throughout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| geopandas | Pure shapely + pyshp | More code, manual file I/O, but fewer dependencies |
| geopandas | Pre-computed crosswalk only | Would need someone to manually compute area weights externally |
| Runtime geospatial | Script-time geospatial | **RECOMMENDED**: Run geopandas only in build script, not at runtime |

**Installation:**
```bash
# For the crosswalk build script only (not needed at runtime)
pip install geopandas>=1.0.0 shapely>=2.0.0 pyproj>=3.3.0 pyogrio>=0.7.2
```

**Key insight on dependencies:** geopandas, shapely, pyproj, and pyogrio all provide pre-built binary wheels for Windows on Python 3.12+ as of 2025. The old "geopandas is hard to install on Windows" problem is largely resolved. However, to keep the main pipeline lightweight, these should be build-time dependencies for the crosswalk script only, not runtime dependencies for the main hazards pipeline.

## Architecture Patterns

### Recommended Approach: Two-Phase Architecture

```
Phase A: Build Scripts (run once, output data files)
  scripts/
    download_nri_data.py        # Downloads NRI county CSV + tribal relational CSV
    download_usfs_data.py       # Downloads USFS wildfire XLSX
    build_area_crosswalk.py     # Computes area-weighted AIANNH-to-county crosswalk
                                # Requires geopandas (build-time only)
                                # Outputs: data/nri/tribal_county_area_weights.json

Phase B: Hazard Pipeline (runtime, no geospatial dependencies)
  src/packets/hazards.py        # Reads pre-computed crosswalk + NRI data
                                # Performs area-weighted aggregation using weights from JSON
                                # Writes 592 hazard profile JSONs
```

### Pattern 1: Pre-Computed Area-Weighted Crosswalk
**What:** A build script that intersects AIANNH and county shapefiles, computes overlap areas, and outputs a JSON mapping.
**When to use:** When area weights are expensive to compute but the boundary data changes infrequently.
**Output schema:**
```json
{
  "metadata": {
    "built_at": "2026-02-11T...",
    "aiannh_source": "tl_2024_us_aiannh.zip",
    "county_source": "tl_2024_us_county.zip",
    "min_overlap_pct": 0.01,
    "total_aiannh_entities": 577,
    "total_county_links": 1842
  },
  "crosswalk": {
    "6015": [
      {"county_fips": "04013", "overlap_area_sqkm": 234.5, "weight": 0.72},
      {"county_fips": "04021", "overlap_area_sqkm": 91.2, "weight": 0.28}
    ]
  }
}
```

### Pattern 2: Area-Weighted Aggregation at Runtime
**What:** For each Tribe, look up overlapping counties and their weights, then compute weighted averages of NRI scores.
**Example:**
```python
# Area-weighted score aggregation
def aggregate_weighted_scores(county_records, weights):
    """Compute area-weighted average of NRI scores.

    Args:
        county_records: List of county NRI dicts with risk_score, etc.
        weights: Corresponding area overlap weights (sum to 1.0 per Tribe).
    """
    weighted_risk = sum(r["risk_score"] * w for r, w in zip(county_records, weights))
    weighted_eal = sum(r["eal_total"] * w for r, w in zip(county_records, weights))
    # EAL is a dollar amount -- area-weighted sum, not average
    return {"risk_score": weighted_risk, "eal_total": weighted_eal}
```

### Pattern 3: USFS Override of NRI WFIR
**What:** When USFS wildfire data exists for a Tribe, replace the NRI WFIR entry in all_hazards and store USFS-specific data separately.
**When to use:** Per CONTEXT.md decision: USFS data overrides NRI WFIR when available.

### Anti-Patterns to Avoid
- **Running geopandas at pipeline runtime:** Heavy, slow, unnecessary. Pre-compute once.
- **MAX aggregation for multi-county Tribes:** Current code uses MAX. CONTEXT.md requires area-weighted averaging. MAX inflates risk for Tribes spanning many counties.
- **Hardcoding NRI version:** The NRI version should come from the actual downloaded data, not be hardcoded as "1.20".
- **Ignoring 1% minimum overlap filter:** Sliver overlaps (< 1% area) from imprecise boundaries produce noise. Filter them out.
- **Re-deriving ratings from weighted scores using fixed percentile thresholds:** NRI Risk/EAL ratings use k-means clustering, not fixed thresholds. You cannot accurately re-derive them from a weighted score. See Pitfall 2.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Shapefile intersection + area calculation | Manual coordinate geometry | geopandas.overlay(how='intersection') + .area | Correct handling of CRS, edge cases, topology |
| CRS projection for area calculation | Assume WGS84 area is accurate | pyproj transform to EPSG:5070 (NAD83 Conus Albers) | WGS84 area in degrees is meaningless for area weighting |
| FIPS code matching/normalization | String comparison with leading zeros | Zero-pad FIPS to 5 chars consistently | State FIPS are 2 digits, county FIPS are 5 (state+county) |
| CSV download with retry | requests.get() with no error handling | requests + retry adapter + hash verification | Large files (39-411 MB) need robust download |
| XLSX column discovery | Hardcoded column indices | Dynamic header inspection (existing pattern) | USFS may update column names between releases |

**Key insight:** The geospatial intersection is a classic "looks simple but isn't" problem. Edge cases include multipolygon boundaries, CRS mismatches, topological errors in shapefiles, and Alaska's unique geometry (crossing the antimeridian).

## Common Pitfalls

### Pitfall 1: CRS Mismatch in Area Calculation
**What goes wrong:** Computing area from WGS84 (EPSG:4326) coordinates gives area in square degrees, which varies wildly by latitude. Alaska areas would be drastically wrong.
**Why it happens:** TIGER/Line shapefiles use WGS84 (lat/lon). Area in lat/lon is not proportional to real area.
**How to avoid:** Project both shapefiles to an equal-area CRS before computing intersection areas. Use EPSG:5070 (NAD83 / Conus Albers Equal Area) for CONUS and EPSG:3338 (NAD83 / Alaska Albers) for Alaska.
**Warning signs:** Alaska Native areas having wildly disproportionate weights.

### Pitfall 2: NRI Rating Re-derivation Is Not Straightforward
**What goes wrong:** Attempting to map a weighted score back to "Very Low" through "Very High" using fixed percentile cutoffs.
**Why it happens:** NRI uses TWO different rating methodologies:
- **SOVI and RESL ratings:** Based on quintiles of scores (fixed 20-percentile breakpoints). These CAN be approximated with score thresholds: 0-20 = Very Low, 20-40 = Relatively Low, 40-60 = Relatively Moderate, 60-80 = Relatively High, 80-100 = Very High.
- **Risk and EAL ratings:** Based on k-means clustering with cube-root transformation applied to values. The cluster boundaries are NOT fixed percentiles and vary by data distribution. These CANNOT be accurately re-derived from scores alone.
**How to avoid:** For SOVI/RESL, use the quintile approach. For Risk/EAL, use the quintile approach as a reasonable approximation (the data is already percentile-ranked 0-100, so quintile breakpoints are defensible), but document that this is an approximation of the actual k-means clustering FEMA uses. The CONTEXT.md says "re-derived from weighted score using FEMA's published thresholds" -- the published thresholds for SOVI/RESL are quintiles; for Risk/EAL the best available approximation is also quintiles of the 0-100 score.
**Warning signs:** Ratings that don't match what FEMA shows for the dominant county.

### Pitfall 3: Alaska Native Villages Without Polygon Boundaries
**What goes wrong:** Some Alaska Native Village Statistical Areas (ANVSAs) have very small polygons or unusual shapes in the AIANNH shapefile, making area-based crosswalk unreliable.
**Why it happens:** ANVSAs are statistical areas representing settlement patterns, not legal boundaries like reservations. They may overlap with borough boundaries in complex ways.
**How to avoid:** Per CONTEXT.md decision: use Census-designated place or borough matching for Alaska Native Villages when no polygon boundary exists. In practice, the AIANNH shapefile DOES include ANVSA polygons, so the standard area-weighted approach should work for most cases. Add a fallback to state/borough-level matching for any ANVSA with zero county intersections.
**Warning signs:** Alaska Tribes with zero matched counties despite having AIANNH GEOIDs.

### Pitfall 4: Oklahoma Tribal Statistical Areas Overlap
**What goes wrong:** Multiple Oklahoma Tribes share overlapping geographic areas (OTSAs), which is correct per CONTEXT.md decision.
**Why it happens:** Oklahoma Tribal Statistical Areas can overlap because multiple Tribes have jurisdiction in the same geographic area.
**How to avoid:** No special handling needed -- each Tribe gets hazard data from all overlapping counties independently. This is explicitly allowed.
**Warning signs:** None; this is expected behavior.

### Pitfall 5: NRI CSV Encoding and Size
**What goes wrong:** NRI county CSV is large (39-411 MB compressed). Reading it naively may fail or be slow.
**Why it happens:** 3,200+ counties x 18 hazards x multiple metrics = many columns.
**How to avoid:** Use csv.DictReader with explicit encoding="utf-8". The existing code handles this correctly. For downloads, implement progress reporting and hash verification.
**Warning signs:** MemoryError or slow startup.

### Pitfall 6: USFS Data Geographic Matching
**What goes wrong:** USFS Wildfire Risk to Communities data uses its own geographic identifiers that may not directly match AIANNH GEOIDs.
**Why it happens:** USFS data includes tribal areas derived from Census AIANNH but may use different identifiers or name formats.
**How to avoid:** Match by GEOID first, then by normalized name matching (existing pattern in hazards.py is good). The USFS XLSX download includes tribal areas explicitly.
**Warning signs:** Low USFS match rate (expecting 300+ matches for fire-prone Tribes).

## Code Examples

### Example 1: Area-Weighted Crosswalk Build Script
```python
# Source: geopandas overlay documentation + project patterns
import geopandas as gpd
import json
from pathlib import Path

def build_area_crosswalk(
    aiannh_shp: Path,
    county_shp: Path,
    output_path: Path,
    min_overlap_pct: float = 0.01,
):
    """Build area-weighted AIANNH-to-county crosswalk.

    Args:
        aiannh_shp: Path to TIGER/Line AIANNH shapefile.
        county_shp: Path to TIGER/Line county shapefile.
        output_path: Where to write the JSON crosswalk.
        min_overlap_pct: Minimum overlap fraction to include (0.01 = 1%).
    """
    # Load shapefiles
    aiannh = gpd.read_file(aiannh_shp)
    counties = gpd.read_file(county_shp)

    # Project to equal-area CRS for accurate area calculation
    # EPSG:5070 = NAD83 / Conus Albers Equal Area Conic
    aiannh_ea = aiannh.to_crs(epsg=5070)
    counties_ea = counties.to_crs(epsg=5070)

    # Compute original AIANNH areas
    aiannh_ea["aiannh_area"] = aiannh_ea.geometry.area

    # Perform intersection overlay
    intersection = gpd.overlay(aiannh_ea, counties_ea, how="intersection")
    intersection["overlap_area"] = intersection.geometry.area

    # Build crosswalk dict
    crosswalk = {}
    for _, row in intersection.iterrows():
        geoid = str(row["GEOID_1"])  # AIANNH GEOID
        county_fips = str(row["GEOID_2"])  # County FIPS
        aiannh_area = row["aiannh_area"]
        overlap_area = row["overlap_area"]

        overlap_pct = overlap_area / aiannh_area if aiannh_area > 0 else 0

        if overlap_pct < min_overlap_pct:
            continue  # Filter sliver overlaps

        if geoid not in crosswalk:
            crosswalk[geoid] = []
        crosswalk[geoid].append({
            "county_fips": county_fips.zfill(5),
            "overlap_area_sqkm": round(overlap_area / 1e6, 2),
            "weight": round(overlap_pct, 6),
        })

    # Normalize weights to sum to 1.0 per AIANNH area
    for geoid, entries in crosswalk.items():
        total_weight = sum(e["weight"] for e in entries)
        if total_weight > 0:
            for e in entries:
                e["weight"] = round(e["weight"] / total_weight, 6)

    # Write output
    output = {
        "metadata": {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "min_overlap_pct": min_overlap_pct,
            "total_aiannh_entities": len(crosswalk),
        },
        "crosswalk": crosswalk,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
```

### Example 2: Area-Weighted Score Aggregation
```python
# Source: project pattern from hazards.py, modified for area weighting
def aggregate_nri_weighted(
    county_records: list[dict],
    weights: list[float],
) -> dict:
    """Area-weighted aggregation of NRI county scores.

    Args:
        county_records: NRI county data dicts.
        weights: Area overlap weights (should sum to ~1.0).
    """
    total_w = sum(weights)
    if total_w == 0:
        return empty_profile()

    # Normalize weights
    norm_w = [w / total_w for w in weights]

    composite = {
        "risk_score": sum(r["risk_score"] * w for r, w in zip(county_records, norm_w)),
        "eal_total": sum(r["eal_total"] * w for r, w in zip(county_records, norm_w)),
        "eal_score": sum(r["eal_score"] * w for r, w in zip(county_records, norm_w)),
        "sovi_score": sum(r["sovi_score"] * w for r, w in zip(county_records, norm_w)),
        "resl_score": sum(r["resl_score"] * w for r, w in zip(county_records, norm_w)),
    }

    # Re-derive ratings from weighted scores using quintile thresholds
    composite["risk_rating"] = score_to_rating(composite["risk_score"])
    composite["sovi_rating"] = score_to_rating(composite["sovi_score"])
    composite["resl_rating"] = score_to_rating(composite["resl_score"])

    return composite

def score_to_rating(score: float) -> str:
    """Convert 0-100 percentile score to NRI rating string.

    Uses quintile breakpoints as approximation of FEMA's methodology.
    SOVI/RESL officially use quintiles. Risk/EAL officially use k-means
    but quintiles are a defensible approximation for derived scores.
    """
    if score >= 80:
        return "Very High"
    elif score >= 60:
        return "Relatively High"
    elif score >= 40:
        return "Relatively Moderate"
    elif score >= 20:
        return "Relatively Low"
    else:
        return "Very Low"
```

### Example 3: NRI Data Download
```python
# Source: standard requests download pattern
import requests
from pathlib import Path

NRI_COUNTY_URL = (
    "https://www.fema.gov/about/reports-and-data/openfema/nri/v120/"
    "NRI_Table_Counties.zip"
)
NRI_TRIBAL_URL = (
    "https://www.fema.gov/about/reports-and-data/openfema/nri/v120/"
    "NRI_Table_Tribal_Counties.zip"
)

def download_with_progress(url: str, dest: Path, chunk_size: int = 8192):
    """Download a file with progress reporting."""
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))

    dest.parent.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = (downloaded / total) * 100
                print(f"\r  {pct:.1f}% ({downloaded:,} / {total:,} bytes)", end="")
    print()
```

## Data Source Details

### 1. FEMA NRI County-Level CSV (v1.20, December 2025)

| Property | Value |
|----------|-------|
| Download URL | `https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_Counties.zip` |
| Format | ZIP containing CSV |
| File name inside ZIP | `NRI_Table_Counties.csv` (confirmed by existing code) |
| Size | 39 MB - 411 MB compressed (varies by format) |
| Version | v1.20 (December 2025) |
| Records | ~3,200 counties |
| CRS | N/A (tabular, uses STCOFIPS for geography) |
| Confidence | **HIGH** -- URL confirmed from official OpenFEMA data page |

**Key columns (confirmed from existing hazards.py code + FEMA documentation):**
- `STCOFIPS` -- 5-digit state+county FIPS code
- `COUNTY`, `STATE` -- human-readable names
- `RISK_SCORE`, `RISK_RATNG`, `RISK_VALUE` -- composite risk
- `EAL_VALT`, `EAL_SCORE`, `EAL_RATNG` -- expected annual loss
- `SOVI_SCORE`, `SOVI_RATNG` -- social vulnerability
- `RESL_SCORE`, `RESL_RATNG` -- community resilience
- Per-hazard: `{CODE}_RISKS`, `{CODE}_RISKR`, `{CODE}_EALT`, `{CODE}_AFREQ`, `{CODE}_EVNTS`
  where CODE is one of 18 hazard codes (AVLN, CFLD, CWAV, DRGT, ERQK, HAIL, HWAV, HRCN, ISTM, IFLD, LNDS, LTNG, SWND, TRND, TSUN, VLCN, WFIR, WNTW)

### 2. FEMA NRI Tribal County Relational CSV

| Property | Value |
|----------|-------|
| Download URL | `https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_Tribal_Counties.zip` |
| Format | ZIP containing CSV |
| Confidence | **MEDIUM** -- URL pattern confirmed from OpenFEMA page but exact column names unverified |

**Expected columns (based on existing code's column detection pattern and FEMA documentation references):**
- AIANNH GEOID column (possibly `AIESSION` or `GEOID` or `AESSION`)
- County FIPS column (possibly `STCOFIPS` or `COUNTYFIPS`)
- Likely NO area weight column -- this is a relational/bridge table providing binary overlap flags

**Critical finding:** The NRI Tribal County Relational CSV almost certainly does NOT include area weights. It is a relational table mapping which AIANNH areas touch which counties. The existing code's column detection logic (searching for "AIESSION", "AESSION", "GEOID", "AIANNH" and "STCOFIPS", "COUNTYFIPS") confirms this expectation. This means area weights must be computed from shapefiles.

### 3. USFS Wildfire Risk to Communities XLSX

| Property | Value |
|----------|-------|
| Download URL | `https://wildfirerisk.org/wp-content/uploads/2025/05/wrc_download_202505.xlsx` |
| Format | XLSX (Excel) |
| Geographic levels | Communities, tribal areas, counties, states (all in one file) |
| Key metrics | Risk to Homes, Wildfire Likelihood, Risk Reduction Zones |
| Tribal areas | Yes, explicitly included (derived from Census AIANNH) |
| Confidence | **HIGH** -- URL confirmed from official wildfirerisk.org download page |

**Metrics:**
- **Risk to Homes:** National percentile ranking of structural risk (0-100 scale)
- **Wildfire Likelihood:** Probability of wildfire occurrence by location
- **Conditional Risk to Structures:** Expected loss given fire (this is the metric specified in CONTEXT.md)
- Risk thresholds: Low (<40th), Medium (40-70th), High (70-90th), Very High (>90th percentile)

### 4. Census TIGER/Line AIANNH Shapefile

| Property | Value |
|----------|-------|
| Download URL | `https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip` |
| Format | ESRI Shapefile (ZIP) |
| Size | 8.7 MB |
| CRS | WGS84 (EPSG:4326) |
| Contents | All AIANNH areas: reservations, trust lands, ANVSAs, OTSAs, HHLs |
| Year | 2024 (released 2025-06-27) |
| Confidence | **HIGH** -- directory listing confirmed on Census FTP |

**Entity types included:**
- Federally recognized American Indian reservations
- Off-reservation trust land areas
- State-recognized American Indian reservations
- Alaska Native Village Statistical Areas (ANVSAs) -- POLYGONS (not points)
- Oklahoma Tribal Statistical Areas (OTSAs)
- Tribal Designated Statistical Areas (TDSAs)
- Hawaiian Home Lands (HHLs)

**Key fields:** GEOID (matches AIANNH crosswalk), NAME, AIANNH code, CLASSFP (feature class), FUNCSTAT

### 5. Census TIGER/Line County Shapefile

| Property | Value |
|----------|-------|
| Download URL | `https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip` |
| Format | ESRI Shapefile (ZIP) |
| CRS | WGS84 (EPSG:4326) |
| Confidence | **MEDIUM** -- URL follows standard Census TIGER pattern but not directly verified |

**Key fields:** GEOID (STCOFIPS equivalent), NAME, STATEFP, COUNTYFP

## NRI Rating Thresholds

### Methodology Summary (Confidence: MEDIUM)

NRI uses TWO different approaches for ratings:

**Social Vulnerability (SOVI) and Community Resilience (RESL):**
- Based on quintiles of component scores
- Fixed breakpoints on the 0-100 percentile scale:
  - 0-20: Very Low
  - 20-40: Relatively Low
  - 40-60: Relatively Moderate
  - 60-80: Relatively High
  - 80-100: Very High

**Risk and Expected Annual Loss (EAL):**
- Based on k-means clustering with cube-root transformation
- Breakpoints are NOT fixed; they are data-driven and vary by distribution
- Applied to the cube-root-transformed values, not directly to percentile scores

**Recommendation for area-weighted profiles:**
Use quintile breakpoints (0/20/40/60/80/100) for ALL rating re-derivation. Rationale:
1. SOVI/RESL officially use quintiles, so this is correct for those
2. Risk/EAL scores are already percentile-ranked 0-100, so quintile breakpoints produce reasonable ratings
3. The area-weighted scores are synthetic values that don't exist in FEMA's original dataset, so ANY re-derivation is an approximation
4. Consistency across all rating types simplifies the code
5. Document this as an approximation in the profile metadata

## Alaska Handling

**Key finding (Confidence: HIGH):** Alaska Native Village Statistical Areas (ANVSAs) ARE included as polygons in the TIGER/Line AIANNH shapefile. They are not points. This means the standard area-weighted crosswalk approach works for Alaska.

**Alaska-specific CRS concern:** EPSG:5070 (Conus Albers) distorts Alaska significantly. For accurate area calculation of Alaska entities, project Alaska features separately to EPSG:3338 (NAD83 / Alaska Albers).

**Implementation approach:**
1. Split AIANNH features into Alaska (STATEFP="02") and non-Alaska
2. Project Alaska to EPSG:3338, non-Alaska to EPSG:5070
3. Run intersection separately, combine results
4. Alternatively: use a global equal-area CRS like EPSG:6933 (World Cylindrical Equal Area) for all features as a simpler approach with slightly less accuracy

**Alaska borough matching fallback:** For any ANVSA with zero county/borough intersections, fall back to matching by the borough FIPS (Alaska has boroughs instead of counties, but they appear as "counties" in Census data with STATEFP="02").

## Performance Considerations

### Crosswalk Build Script
- **One-time computation:** ~577 AIANNH polygons intersected with ~3,200 county polygons
- **Expected runtime:** 30-120 seconds with geopandas overlay
- **Memory:** Shapefiles are small (AIANNH: 8.7 MB, counties: ~30 MB). GeoPandas can handle this easily.
- **Optimization:** Not needed for a one-time build script

### NRI County CSV Parsing
- **3,200 rows x ~200 columns:** Fast with csv.DictReader
- **Expected runtime:** 1-3 seconds
- **Memory:** ~50-100 MB in memory as dict

### Hazard Profile Generation (592 Tribes)
- **Per-Tribe:** Look up overlapping counties (O(1) dict lookup), compute weighted averages (O(k) where k=avg counties per Tribe, typically 1-10)
- **Total:** < 5 seconds for all 592 Tribes
- **I/O:** 592 JSON file writes, trivial

### USFS XLSX Parsing
- **Single XLSX file:** openpyxl read_only mode, fast
- **Expected runtime:** 5-15 seconds depending on file size

## Changes Required to Existing Code

### hazards.py Modifications
1. **Aggregation method:** Change from MAX to area-weighted averaging (major refactor of `_build_tribe_nri_profile`)
2. **Top hazards count:** Change from top 3 to top 5 (`sorted_hazards[:3]` -> `sorted_hazards[:5]`)
3. **Load area-weighted crosswalk:** New method to load pre-computed JSON crosswalk with weights
4. **Rating re-derivation:** Add `score_to_rating()` function using quintile breakpoints
5. **USFS override:** When USFS data exists, replace WFIR score in all_hazards
6. **Version tracking:** Read NRI version from data, not hardcode "1.20"
7. **Non-zero filtering:** Only store non-zero hazards in all_hazards per CONTEXT.md
8. **Coverage report:** Generate persistent report with per-state breakdown

### New Files
1. `scripts/download_nri_data.py` -- Download NRI county CSV + tribal relational CSV
2. `scripts/download_usfs_data.py` -- Download USFS wildfire XLSX
3. `scripts/build_area_crosswalk.py` -- Compute area-weighted AIANNH-to-county crosswalk
4. `data/nri/tribal_county_area_weights.json` -- Pre-computed crosswalk output

### paths.py Additions
```python
TRIBAL_COUNTY_WEIGHTS_PATH: Path = NRI_DIR / "tribal_county_area_weights.json"
"""Pre-computed area-weighted AIANNH-to-county crosswalk."""
```

## Claude's Discretion Recommendations

### Preserve original NRI WFIR score when USFS overrides?
**Recommendation: Yes, preserve it.** Store the original NRI WFIR score in a `nri_wfir_original` field within the `usfs_wildfire` section. This provides an audit trail at negligible cost (one extra field per profile). The main WFIR entry in `all_hazards` gets the USFS override value.

### Note field handling for populated profiles?
**Recommendation:** Set `note` field to `null` (or omit it) for successfully populated profiles. Only set `note` for profiles that have issues (no data, partial data, etc.). The existing pattern of using `note` for error explanations is good.

### Coverage report format?
**Recommendation: Both JSON and Markdown.** JSON for programmatic consumption, Markdown for human review. Output to `outputs/hazard_coverage_report.json` and `outputs/hazard_coverage_report.md`. The Markdown report should include per-state tables showing matched/unmatched Tribes.

### Internal caching strategy for boundary intersections?
**Recommendation:** Not needed at runtime since the crosswalk is pre-computed. The build script runs once and outputs a JSON file. If re-running is needed, the script just overwrites the output. No complex caching required.

## Open Questions

1. **NRI Tribal County Relational CSV exact column names**
   - What we know: The CSV exists and is downloadable. The existing code has robust column detection logic.
   - What's unclear: Exact column header names (AIESSION vs GEOID vs AESSION). Whether it includes ANY area/weight metadata.
   - Recommendation: Download the file and inspect headers. The existing column detection in hazards.py should handle variations.
   - Confidence: LOW for column names; HIGH that it exists and is parseable.

2. **USFS XLSX column names for "conditional risk to structures"**
   - What we know: The XLSX is downloadable from wildfirerisk.org. It includes tribal areas. It has "Risk to Homes" and "Wildfire Likelihood" columns.
   - What's unclear: Whether "conditional risk to structures" is a separate column or is the same as "Risk to Homes". The existing code searches for "risk_to_homes" and "risk score" patterns.
   - Recommendation: Download the file and inspect headers. The existing schema discovery pattern in hazards.py is well-designed for this.
   - Confidence: MEDIUM.

3. **EAL aggregation: weighted average vs weighted sum?**
   - What we know: CONTEXT.md says "area-weighted averaging" for all scores. But EAL is a dollar amount representing Expected Annual Loss.
   - What's unclear: Should EAL_VALT (dollar amount) be weighted-averaged or weighted-summed? A Tribe spanning 50% of county A and 50% of county B should arguably get half of each county's EAL, not the average.
   - Recommendation: Use weighted sum for EAL dollar amounts (EAL_VALT). Use weighted average for percentile scores (EAL_SCORE, RISK_SCORE, SOVI_SCORE, RESL_SCORE). Document this distinction.
   - Confidence: MEDIUM -- this is a modeling judgment call.

4. **Exact USFS download URL stability**
   - What we know: Current URL is `https://wildfirerisk.org/wp-content/uploads/2025/05/wrc_download_202505.xlsx`
   - What's unclear: Whether this URL changes with each data update (the `202505` suggests it's date-versioned)
   - Recommendation: Store the URL in config, not hardcoded. Add a check for newer versions.
   - Confidence: MEDIUM.

## Sources

### Primary (HIGH confidence)
- [FEMA OpenFEMA NRI Data Downloads](https://www.fema.gov/about/openfema/data-sets/national-risk-index-data) -- Confirmed download URLs for v1.20 county and tribal CSV
- [Census TIGER/Line AIANNH](https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/) -- Confirmed filename `tl_2024_us_aiannh.zip` (8.7MB)
- [Wildfire Risk to Communities Download](https://wildfirerisk.org/download/) -- Confirmed XLSX download with tribal areas
- [GeoPandas Installation](https://geopandas.org/en/stable/getting_started/install.html) -- Confirmed pip binary wheels for Windows

### Secondary (MEDIUM confidence)
- [GeoPandas Overlay Operations](https://geopandas.org/en/stable/docs/user_guide/set_operations.html) -- Intersection + area calculation patterns
- [FEMA NRI Scoring Methodology](https://hazards.fema.gov/nri/understanding-scores-ratings) -- Redirects to RAPT but search results confirm k-means for Risk/EAL, quintiles for SOVI/RESL
- [Wildfire Risk to Communities Methods](https://wildfirerisk.org/about/methods/) -- Confirms percentile thresholds for risk categories
- [Census TIGER/Line Documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2024/TGRSHP2024_TechDoc.pdf) -- AIANNH shapefile includes ANVSA polygons

### Tertiary (LOW confidence)
- NRI Tribal County Relational CSV column schema -- Could not verify exact headers; need to download and inspect
- NRI Data Dictionary CSV -- URL redirects to RAPT page; old version at `/Archive/v118_1/` also redirects
- USFS XLSX exact column names -- Need to download and inspect the actual file

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** -- geopandas/shapely are well-established; binary wheels confirmed for Windows
- Architecture: **HIGH** -- Pre-computed crosswalk pattern is proven in this codebase (see `scripts/build_registry.py`)
- Data sources: **HIGH** for download URLs; **LOW** for exact column schemas of tribal relational and USFS files
- Pitfalls: **MEDIUM** -- CRS issues and rating methodology are well-documented; some details unverifiable without actual data files
- Area-weighted crosswalk: **HIGH** -- This is the standard geospatial approach; geopandas overlay is well-documented

**Research date:** 2026-02-11
**Valid until:** 2026-04-11 (NRI data is versioned; USFS updates annually; shapefile URLs may change)
