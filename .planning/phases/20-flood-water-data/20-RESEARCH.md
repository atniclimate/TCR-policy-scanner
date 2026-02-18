# Phase 20: Flood & Water Data - Research

**Researched:** 2026-02-17
**Domain:** Federal flood/water API integration (OpenFEMA, USGS, NOAA), county-level aggregation, pre-cached JSON pipeline
**Confidence:** MEDIUM (API endpoints verified via official docs; some specifics from training data need runtime validation)

## Summary

Phase 20 integrates six federal flood and water data sources into per-Tribe cached JSON files, routed through the existing county FIPS crosswalk (`tribal_county_area_weights.json`). The data sources span two OpenFEMA endpoints (NFIP claims, disaster declarations), FEMA NFHL flood zone data, USGS streamflow (new OGC API + legacy peak flows), NOAA Atlas 14 precipitation frequency estimates, and NOAA CO-OPS coastal water levels.

The architecture follows the established 9-step builder pattern from Phase 19 (SVI/NRI builders): init -> crosswalk -> weights -> API fetch -> aggregation -> atomic write -> path guard -> Pydantic validation -> coverage report. All six sources are free, require no API keys, and return JSON or CSV. The main challenges are: (1) OpenFEMA pagination for 2.7M+ NFIP claims records, (2) USGS peak streamflow data is NOT yet on the new API (must use legacy NWIS), (3) NOAA Atlas 14 has no formal REST API (URL parameter scraping required), and (4) coastal classification requires a static reference dataset.

**Primary recommendation:** Build six independent builder classes following the SVIProfileBuilder template. Use synchronous `requests` (not aiohttp) since these are one-time population scripts run offline. Implement per-source circuit breakers. Pre-download the NOAA coastal counties reference list and the NWPS gauges CSV as static reference files rather than querying APIs at runtime.

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.31+ | Synchronous HTTP for population scripts | Already available; population scripts are sequential batch jobs, not async pipeline scrapers |
| pydantic | 2.x | Schema validation for flood cache JSON | Established pattern from vulnerability.py schemas (Phase 19) |
| pathlib | stdlib | Path construction and traversal guards | Project standard per CLAUDE.md |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiohttp | 3.9+ | Only if population scripts need async fan-out | NOT recommended for Phase 20 -- use requests for simplicity |
| csv | stdlib | Parse NWPS gauge CSV, Atlas 14 CSV downloads | NWPS gauge reference, Atlas 14 PF estimates |
| json | stdlib | Parse API responses, write cache files | All six data sources |
| tempfile + os | stdlib | Atomic writes (mkstemp + os.replace) | Established pattern from _geo_common.py |

### New Dependencies (evaluate)
| Library | Version | Purpose | Decision |
|---------|---------|---------|----------|
| dataretrieval | 1.1.2 | USGS Python client (get_peak, get_dv, get_info) | USE for FLOOD-04 peak flows (wraps legacy NWIS). Modern waterdata module wraps new OGC API. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dataretrieval | Raw HTTP to NWIS | dataretrieval handles RDB parsing, date formatting, and the transition to new API. Adds a dependency but saves substantial parsing code. |
| requests (sync) | aiohttp (async) | Population scripts are one-time batch jobs. Async adds complexity for no benefit. Existing scrapers use aiohttp for the live pipeline, but population scripts (populate_awards.py, populate_hazards.py) are simpler. |

**Installation:**
```bash
pip install dataretrieval
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  packets/
    flood_nfip.py          # FLOOD-01: NFIP claims/policies builder
    flood_declarations.py  # FLOOD-02: Disaster declarations builder
    flood_nfhl.py          # FLOOD-03: NFHL community flood zone builder
    flood_streamflow.py    # FLOOD-04: USGS streamflow builder
    flood_precipitation.py # FLOOD-05: Atlas 14 precipitation builder
    flood_coastal.py       # FLOOD-06: NOAA CO-OPS coastal builder
    _flood_common.py       # Shared: coastal classification, HTTP helpers, rate limiting
  schemas/
    flood.py               # Pydantic models for all 6 flood data types
data/
  flood_cache/             # Per-Tribe flood JSON files (592 files)
  reference/
    coastal_counties.json  # Static NOAA coastal county classification
    nwps_gauges.csv        # Static NWS gauge metadata with flood stages
scripts/
  populate_flood_data.py   # CLI orchestrator for all 6 flood builders
  download_flood_reference.py  # One-time download of reference files
```

### Pattern 1: OpenFEMA Paginated Fetch
**What:** Query OpenFEMA APIs with OData $filter by county FIPS, paginating with $skip/$top.
**When to use:** FLOOD-01 (NFIP claims) and FLOOD-02 (disaster declarations).
**Example:**
```python
# Source: https://www.fema.gov/about/openfema/api
import requests
import logging
import time

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fema.gov/api/open/v2"
MAX_PER_PAGE = 1000  # Safe default; max is 10,000

def fetch_openfema_paginated(
    endpoint: str,
    filter_expr: str,
    select_fields: list[str] | None = None,
    max_records: int = 100_000,
) -> list[dict]:
    """Fetch all records from an OpenFEMA endpoint with pagination.

    Args:
        endpoint: API entity name (e.g., "FimaNfipClaims").
        filter_expr: OData $filter expression.
        select_fields: Optional list of field names to select.
        max_records: Safety cap on total records.

    Returns:
        List of all matching records.
    """
    all_records = []
    skip = 0
    url = f"{BASE_URL}/{endpoint}"

    while True:
        params = {
            "$filter": filter_expr,
            "$top": MAX_PER_PAGE,
            "$skip": skip,
            "$count": "true",
        }
        if select_fields:
            params["$select"] = ",".join(select_fields)

        logger.info(
            "Fetching %s: skip=%d, filter=%s",
            endpoint, skip, filter_expr[:80],
        )

        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        entity_key = next(
            (k for k in data if k not in ("metadata",)),
            endpoint,
        )
        records = data.get(entity_key, [])
        all_records.extend(records)

        if len(records) < MAX_PER_PAGE:
            break  # Last page
        if len(all_records) >= max_records:
            logger.warning("Hit max_records cap (%d)", max_records)
            break

        skip += MAX_PER_PAGE
        time.sleep(0.5)  # Rate limiting courtesy

    logger.info(
        "Fetched %d total records from %s", len(all_records), endpoint,
    )
    return all_records
```

### Pattern 2: USGS New OGC API for Monitoring Locations
**What:** Query api.waterdata.usgs.gov OGC API for site metadata and daily values.
**When to use:** FLOOD-04 site discovery and recent daily streamflow.
**Example:**
```python
# Source: https://api.waterdata.usgs.gov/docs/ogcapi/
import requests

USGS_OGC_BASE = "https://api.waterdata.usgs.gov/ogcapi/v0"

def get_monitoring_locations_by_county(
    county_fips: str,
    site_type: str = "ST",  # Streams
) -> list[dict]:
    """Query USGS OGC API for stream monitoring locations in a county.

    Args:
        county_fips: 5-digit county FIPS code.
        site_type: Site type code (ST=stream, default).

    Returns:
        List of GeoJSON feature dicts for matching sites.
    """
    url = f"{USGS_OGC_BASE}/collections/monitoring-locations/items"
    params = {
        "f": "json",
        "county_code": county_fips,
        "site_type_code": site_type,
        "limit": 500,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("features", [])
```

### Pattern 3: USGS Legacy Peak Flows via dataretrieval
**What:** Use dataretrieval-python to fetch peak annual streamflow for a gauge.
**When to use:** FLOOD-04 peak flow history (not yet on new API per DEC-07 fallback).
**Example:**
```python
# Source: https://github.com/DOI-USGS/dataretrieval-python
from dataretrieval import nwis

def get_peak_flows(site_no: str) -> list[dict]:
    """Fetch peak annual streamflow data for a USGS site.

    Args:
        site_no: USGS site number (e.g., "12345678").

    Returns:
        List of peak flow records with year, discharge, date.
    """
    df, metadata = nwis.get_peak(sites=site_no)
    records = []
    for _, row in df.iterrows():
        records.append({
            "date": str(row.name),
            "peak_discharge_cfs": float(row.get("peak_va", 0)),
            "gage_height_ft": float(row.get("gage_ht", 0)) if row.get("gage_ht") else None,
        })
    return records
```

### Pattern 4: NOAA CO-OPS Water Level Fetch
**What:** Query CO-OPS datagetter for hourly water levels at a station.
**When to use:** FLOOD-06 coastal water level history.
**Example:**
```python
# Source: https://api.tidesandcurrents.noaa.gov/api/prod/
import requests

COOPS_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

def fetch_water_levels(
    station_id: str,
    begin_date: str,  # "YYYYMMDD"
    end_date: str,
    product: str = "hourly_height",
    datum: str = "MLLW",
) -> dict:
    """Fetch water level data from NOAA CO-OPS.

    Note: hourly_height has a 1-year max per request.
    For multi-year queries, iterate year by year.
    """
    params = {
        "station": station_id,
        "begin_date": begin_date,
        "end_date": end_date,
        "product": product,
        "datum": datum,
        "units": "english",
        "time_zone": "gmt",
        "format": "json",
        "application": "TCR_Policy_Scanner",
    }
    resp = requests.get(COOPS_BASE, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()
```

### Pattern 5: Builder Template (9-Step)
**What:** All six flood builders follow the established builder pattern from Phase 19.
**When to use:** Every builder class.
**Template steps:**
1. `__init__()` -- Load config, crosswalk, area weights, registry
2. Load AIANNH crosswalk via `_geo_common.load_aiannh_crosswalk()`
3. Load area weights via `_geo_common.load_area_weights()`
4. Data fetch -- API calls or CSV/file loading (source-specific)
5. Per-Tribe aggregation -- area-weighted, county-level matching
6. Override/enrichment (if applicable, e.g., USFS wildfire override pattern)
7. `build_all_profiles()` -- orchestration loop over 592 Tribes
8. Atomic write via `_geo_common.atomic_write_json()`
9. Coverage report generation (JSON + Markdown)

### Anti-Patterns to Avoid
- **Downloading full NFIP dataset (80M+ records):** Filter by county at query time, never bulk download.
- **Using aiohttp for population scripts:** These are sequential batch jobs, not the live scan pipeline. Synchronous requests are simpler and sufficient.
- **Querying Atlas 14 per-Tribe:** Atlas 14 data is location-based. Query per county centroid once, then aggregate to Tribes via crosswalk.
- **Treating all 592 Tribes as coastal:** Only ~100-150 Tribes have coastal county overlap. Pre-classify and skip FLOOD-06 for inland Tribes.
- **Hardcoding API URLs in builder classes:** Define all endpoints as module-level constants or in config.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| USGS peak flow parsing | Custom RDB parser | `dataretrieval.nwis.get_peak()` | RDB format has header rows, comment lines, and type codes that are tricky to parse correctly |
| USGS site metadata | Custom NWIS query builder | `dataretrieval.waterdata.get_monitoring_locations()` or direct OGC API | Well-tested, handles pagination and format conversion |
| Atomic JSON writes | Custom temp-file pattern | `_geo_common.atomic_write_json()` | Already battle-tested in hazards/SVI builders |
| Crosswalk loading | Re-implement AIANNH loading | `_geo_common.load_aiannh_crosswalk()` and `load_area_weights()` | Shared across all builders, tested |
| NaN/Inf handling | Ad-hoc float conversion | `hazards._safe_float()` | Move to `_geo_common` or `_flood_common` for reuse |
| Coastal county lookup | Runtime API query | Static JSON reference file | NOAA coastal counties change very rarely; pre-download once |
| Flood stage thresholds | API query per gauge at runtime | Pre-downloaded `nwps_all_gauges_report.csv` | NWS provides a comprehensive CSV dump with all gauges |

**Key insight:** The heaviest lifting in this phase is HTTP pagination and rate limiting, not data transformation. The county-to-Tribe aggregation is already solved by the crosswalk infrastructure. Don't rebuild it.

## Common Pitfalls

### Pitfall 1: OpenFEMA Pagination Off-by-One
**What goes wrong:** Missing the last page of results because the loop checks `len(records) == 0` instead of `len(records) < $top`.
**Why it happens:** The API returns exactly $top records when more exist, and fewer than $top on the last page. But if the total is an exact multiple of $top, the last full page looks like there might be more.
**How to avoid:** Use `$count=true` in the request. Check the metadata count field. Continue until `skip >= count` or `len(records) < $top`.
**Warning signs:** Coverage report shows fewer claims/declarations than expected for high-population counties.

### Pitfall 2: NFIP Claims Dataset Size (2.7M+ Records)
**What goes wrong:** Trying to fetch all NFIP claims for all counties in one pass overwhelms memory and takes hours.
**Why it happens:** The NFIP claims dataset has 2.7M+ records. Querying without county filters returns massive result sets.
**How to avoid:** Query per-county FIPS (from crosswalk), not per-state or nationally. With ~700 unique county FIPS in the crosswalk, each county query returns manageable batches. Use `$select` to limit fields returned.
**Warning signs:** Script takes >1 hour per county, memory usage >2GB.

### Pitfall 3: CO-OPS Data Length Limits
**What goes wrong:** Requesting more than 1 year of hourly water level data in a single request returns an error.
**Why it happens:** CO-OPS enforces strict per-request time limits: 6-min data = 1 month max, hourly = 1 year max, daily = 10 years max.
**How to avoid:** Use `daily_mean` product for 20-year windows (fits in 2 requests). Or loop year-by-year for hourly data. Always check the "error" key in the JSON response.
**Warning signs:** API returns `{"error": {"message": "..."}}` instead of data.

### Pitfall 4: USGS Peak Flows Not on New API
**What goes wrong:** Building against api.waterdata.usgs.gov for peak flows and finding no peak flow collection.
**Why it happens:** Per DEC-07, we should use the new API. But peak flows are explicitly NOT yet modernized (the blog post confirms "peaks and ratings do not have a proposed timeline for modernization"). The new API has: monitoring-locations, daily, continuous, latest-continuous, latest-daily, field-measurements, time-series-metadata. No peaks.
**How to avoid:** Use `dataretrieval.nwis.get_peak()` for peak flows (legacy NWIS). Use new OGC API for monitoring-location discovery and daily values. Document the hybrid approach.
**Warning signs:** Empty results when querying api.waterdata.usgs.gov for peak data.

### Pitfall 5: Atlas 14 Has No Formal REST API
**What goes wrong:** Assuming NOAA provides a clean JSON API for precipitation frequency data.
**Why it happens:** Atlas 14 PFDS is a web application, not an API. The "API" is really URL parameters on the PFDS print page.
**How to avoid:** Two approaches: (a) Use the USGS `pfdf` library which wraps the PFDS download, or (b) download pre-computed GIS grids for all volumes and extract county-level values locally. Option (b) is more reliable for batch processing. The GIS grids are available at https://hdsc.nws.noaa.gov/pfds/pfds_gis.html in ASCII grid format.
**Warning signs:** Intermittent failures when scraping PFDS; results vary by session.

### Pitfall 6: NFHL WFS 1000-Feature Limit
**What goes wrong:** Geospatial queries to NFHL return incomplete data (capped at 1000 features).
**Why it happens:** FEMA's NFHL WFS service limits responses to 1000 features per request. Full geospatial intersection is out of scope (noted in prior decisions).
**How to avoid:** Use the NFIP Community Status Book API instead (`/v1/NfipCommunityStatusBook`). It provides community-level NFIP participation status, CRS ratings, and discount percentages. These communities map to counties. Supplement with NFIP claims/policies data which already has flood zone fields (`ratedFloodZone`, `floodZoneCurrent`).
**Warning signs:** Partial flood zone data, inconsistent polygon counts.

### Pitfall 7: County FIPS Zero-Padding
**What goes wrong:** County FIPS "1001" fails to match crosswalk entry "01001".
**Why it happens:** OpenFEMA returns countyCode as integers or variably padded strings. USGS uses 5-digit strings. The crosswalk uses 5-digit zero-padded strings.
**How to avoid:** Always `str(fips).zfill(5)` immediately after receiving any FIPS code from any API. The project already does this in HazardProfileBuilder.
**Warning signs:** Low match rates between API data and crosswalk.

### Pitfall 8: Disaster Declarations Don't Have Dollar Amounts
**What goes wrong:** Expecting dollar amounts (IA/PA/HMGP) in the DisasterDeclarationsSummaries endpoint.
**Why it happens:** The declarations endpoint has program flags (ihProgramDeclared, paProgramDeclared) but NOT dollar amounts. Dollar amounts are in separate datasets: PublicAssistanceFundedProjectsSummaries and HazardMitigationAssistanceProjects.
**How to avoid:** For Phase 20, store program flags and declaration metadata from DisasterDeclarationsSummaries. If dollar amounts are needed, query the PA/HMGP datasets separately. The 20-CONTEXT.md says "Store all dollar amounts: IA, PA, HMGP" -- this requires joining across OpenFEMA datasets.
**Warning signs:** Null/missing dollar fields in declaration records.

## Code Examples

### OpenFEMA NFIP Claims by County
```python
# Source: https://www.fema.gov/about/openfema/api
# Fields: https://www.fema.gov/openfema-data-page/fima-nfip-redacted-claims-v2

def fetch_nfip_claims_for_county(county_fips: str) -> list[dict]:
    """Fetch NFIP claims for a single county.

    Args:
        county_fips: 5-digit FIPS code (e.g., "53033").

    Returns:
        List of claim records with loss amounts, dates, flood zones.
    """
    filter_expr = f"countyCode eq '{county_fips}'"
    select = [
        "countyCode", "state", "dateOfLoss",
        "amountPaidOnBuildingClaim", "amountPaidOnContentsClaim",
        "amountPaidOnIncreasedCostOfComplianceClaim",
        "ratedFloodZone", "floodZoneCurrent",
        "occupancyType", "yearOfLoss",
    ]
    return fetch_openfema_paginated(
        "FimaNfipClaims", filter_expr, select_fields=select,
    )
```

### OpenFEMA Disaster Declarations by County
```python
# Source: https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2

def fetch_declarations_for_county(
    county_fips: str,
    min_year: int = 2005,
) -> list[dict]:
    """Fetch disaster declarations for a county since min_year.

    Args:
        county_fips: 5-digit FIPS (only last 3 digits used in API: countyCode).
        min_year: Start year for 20-year window.

    Returns:
        List of declaration records.
    """
    # OpenFEMA uses separate fipsStateCode (2-digit) and fipsCountyCode (3-digit)
    state_fips = county_fips[:2]
    county_code = county_fips[2:]  # Last 3 digits
    filter_expr = (
        f"fipsStateCode eq '{state_fips}' "
        f"and fipsCountyCode eq '{county_code}' "
        f"and fyDeclared ge {min_year}"
    )
    return fetch_openfema_paginated(
        "DisasterDeclarationsSummaries", filter_expr,
    )
```

### NFIP Community Status (FLOOD-03 Alternative)
```python
# Source: https://www.fema.gov/openfema-data-page/nfip-community-status-book-v1

def fetch_nfip_community_status(state: str) -> list[dict]:
    """Fetch NFIP Community Status Book for a state.

    Provides: community participation, CRS class rating,
    SFHA discount rates, effective dates.
    25,053 total records -- can fetch per-state.

    Args:
        state: 2-letter state code.

    Returns:
        List of community records with CRS ratings.
    """
    url = "https://www.fema.gov/api/open/v1/NfipCommunityStatusBook"
    params = {
        "$filter": f"state eq '{state}'",
        "$top": 1000,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("NfipCommunityStatusBook", [])
```

### Coastal County Classification
```python
# Static reference approach -- pre-built JSON file

COASTAL_COUNTIES: dict[str, str] = {}  # FIPS -> "marine" | "lacustrine"

# Great Lakes states for lacustrine classification
GREAT_LAKES_STATES = {"MN", "WI", "IL", "IN", "MI", "OH", "PA", "NY"}

def classify_tribe_coastal(
    tribe_counties: list[str],
    coastal_ref: dict[str, str],
) -> str:
    """Classify a Tribe as marine, lacustrine, or inland.

    Per 20-CONTEXT.md:
    - County-based: if any county in crosswalk is NOAA-designated coastal
    - Three-way: marine, lacustrine (Great Lakes), inland
    - "Coastal wins" rule: if any county is marine, Tribe is marine
    """
    has_marine = False
    has_lacustrine = False

    for fips in tribe_counties:
        coast_type = coastal_ref.get(fips)
        if coast_type == "marine":
            has_marine = True
        elif coast_type == "lacustrine":
            has_lacustrine = True

    if has_marine:
        return "marine"
    elif has_lacustrine:
        return "lacustrine"
    return "inland"
```

### NOAA CO-OPS Station Discovery via Metadata API
```python
# Source: https://api.tidesandcurrents.noaa.gov/mdapi/prod/

COOPS_META_BASE = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"

def get_coops_stations() -> list[dict]:
    """Fetch all CO-OPS water level stations with metadata.

    Returns list of station dicts with id, name, lat, lon, state.
    """
    url = f"{COOPS_META_BASE}/stations.json"
    params = {"type": "waterlevels"}
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("stations", [])

def get_flood_levels(station_id: str) -> dict:
    """Fetch NOS flood threshold levels for a station."""
    url = f"{COOPS_META_BASE}/stations/{station_id}/floodlevels.json"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()
```

### NWS Flood Stage Reference (Static CSV)
```python
# Source: https://water.noaa.gov/resources/downloads/reports/nwps_all_gauges_report.csv
# 46 columns including: location name, state, county, lat, lon,
# action stage, flood stage, moderate flood stage, major flood stage, USGS ID

import csv

def load_nwps_gauge_reference(csv_path: str) -> dict[str, dict]:
    """Load NWS gauge metadata with flood thresholds.

    The CSV has ~10,000 gauges nationwide with flood stage thresholds.
    Returns dict keyed by USGS site ID for cross-reference with FLOOD-04.
    """
    gauges = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            usgs_id = row.get("usgs_id", "").strip()
            if usgs_id:
                gauges[usgs_id] = {
                    "name": row.get("location name", ""),
                    "state": row.get("state", ""),
                    "county": row.get("county", ""),
                    "lat": _safe_float(row.get("latitude")),
                    "lon": _safe_float(row.get("longitude")),
                    "action_stage_ft": _safe_float(row.get("action stage")),
                    "flood_stage_ft": _safe_float(row.get("flood stage")),
                    "moderate_flood_stage_ft": _safe_float(row.get("moderate flood stage")),
                    "major_flood_stage_ft": _safe_float(row.get("major flood stage")),
                }
    return gauges
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| USGS waterservices.usgs.gov (legacy) | api.waterdata.usgs.gov (OGC API) | 2024-2025 rollout | New API for site discovery and daily values; peaks NOT yet migrated |
| NWIS peak streamflow via NWIS web | dataretrieval-python v1.1.2 | Jan 2026 | Python wrapper handles both legacy and modern endpoints |
| AHPS (Advanced Hydrologic Prediction Service) | NWPS (National Water Prediction Service) | March 2024 | New API at api.water.noaa.gov/nwps/v1/; AHPS data preserved |
| NOAA Atlas 14 (current) | NOAA Atlas 15 (upcoming) | In development | Atlas 15 will supersede Atlas 14; build against 14 now, document migration path |
| OpenFEMA v1 | OpenFEMA v2 | Ongoing | v2 endpoints preferred; $count replacing $inlinecount |
| CO-OPS manual station lookup | CO-OPS Metadata API + Derived Products API | 2023+ | Programmatic flood threshold discovery via floodlevels.json |

**Deprecated/outdated:**
- USGS waterservices.usgs.gov: Decommission planned "early 2027" per USGS blog. Use new API where possible, legacy only for peaks.
- AHPS: Replaced by NWPS in March 2024. API endpoints at api.water.noaa.gov.
- OpenFEMA `$inlinecount`: Being replaced by `$count`. Use `$count=true` instead.

## Data Source Details

### FLOOD-01: NFIP Claims (OpenFEMA)
- **Endpoint:** `https://www.fema.gov/api/open/v2/FimaNfipClaims`
- **Records:** 2,719,735 total (as of Feb 2026)
- **Key fields:** countyCode, state, dateOfLoss, yearOfLoss, amountPaidOnBuildingClaim, amountPaidOnContentsClaim, amountPaidOnIncreasedCostOfComplianceClaim, ratedFloodZone, floodZoneCurrent, occupancyType
- **Filter:** `$filter=countyCode eq '{fips}'` (3-digit county code only, use with state)
- **Pagination:** $top=1000 (default), max 10,000; $skip for offset; $count=true for total
- **Rate limit:** Not formally documented; recommend 0.5s delay between requests
- **No API key required**

### FLOOD-01 (supplement): NFIP Policies (OpenFEMA)
- **Endpoint:** `https://www.fema.gov/api/open/v2/FimaNfipPolicies`
- **Records:** 80,000,000+ total policy transactions
- **Key fields:** countyCode, policyEffectiveDate, policyTerminationDate, totalInsurancePremiumOfThePolicy, buildingReplacement-Cost, floodZone, crsClassCode
- **WARNING:** This dataset is enormous. Filter aggressively. Consider using only the most recent policy snapshot rather than full history.
- **Strategy:** Query active policies within a date range per county, not full history.

### FLOOD-02: Disaster Declarations (OpenFEMA)
- **Endpoint:** `https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries`
- **Records:** ~68,000 total (1953-present)
- **Key fields:** fipsStateCode, fipsCountyCode, disasterNumber, declarationDate, incidentType, incidentBeginDate, incidentEndDate, declarationTitle, ihProgramDeclared, iaProgramDeclared, paProgramDeclared, hmProgramDeclared, fyDeclared
- **Filter:** `$filter=fipsStateCode eq '{ss}' and fipsCountyCode eq '{ccc}' and fyDeclared ge 2005`
- **NOTE:** Declaration records do NOT contain dollar amounts. For IA/PA/HMGP amounts, must join with:
  - `PublicAssistanceFundedProjectsSummaries` (v1) for PA dollars
  - `HazardMitigationAssistanceProjects` for HMGP dollars
- **20-CONTEXT says store dollar amounts** -- this requires multi-dataset joins per disaster number

### FLOOD-03: NFHL Flood Zones
- **Original plan:** FEMA NFHL WFS geospatial service
- **Problem:** WFS 1000-feature limit makes county-level queries impractical for full geospatial analysis
- **Revised approach:** Use NFIP Community Status Book API + claims/policies flood zone field aggregation
  - **Community Status Book:** `https://www.fema.gov/api/open/v1/NfipCommunityStatusBook`
  - **25,053 communities** with fields: communityIdNumber, county, state, participatingInNFIP, classRating (CRS 1-10), sfhaDiscount, nonSfhaDiscount, currentlyEffectiveMapDate
  - **Tribal flag:** Boolean `tribal` field identifies Tribal communities
  - Supplement with flood zone distribution derived from NFIP claims data (ratedFloodZone field) to approximate zone percentages
- **Alternative for zone percentages:** Download NFHL county shapefiles from FEMA Map Service Center, use geopandas for area calculation (heavier, but more accurate)

### FLOOD-04: USGS Streamflow
- **Site discovery:** New OGC API at `https://api.waterdata.usgs.gov/ogcapi/v0/collections/monitoring-locations/items`
  - Filter: `county_code={fips}&site_type_code=ST` (streams)
  - Returns: GeoJSON features with site_no, name, lat/lon, drainage_area, contributing_drainage_area
  - Pagination: `limit` + `offset` parameters; `next` link in response
- **Daily values:** New OGC API at `https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items`
  - Filter: `monitoring_location_id=USGS-{site_no}&parameter_code=00060&time=P365D` (discharge, last year)
  - Parameter 00060 = streamflow/discharge in cfs
- **Peak flows:** Legacy NWIS only (NOT on new API)
  - Use `dataretrieval.nwis.get_peak(sites=site_no)` or
  - Direct URL: `https://nwis.waterdata.usgs.gov/usa/nwis/peak?site_no={site_no}&format=rdb`
  - Returns: annual peak discharge, gage height, date
- **Drainage area filter:** Per 20-CONTEXT.md, keep all gauges that pass size filter. Recommend: drainage_area > 0 and drainage_area <= 10,000 sq mi (filters out huge river mainstems like Mississippi that don't represent local flood risk).
- **Flood/action stages:** Cross-reference USGS site IDs with NWS NWPS gauge CSV (`nwps_all_gauges_report.csv`) to get NWS flood categories

### FLOOD-05: NOAA Atlas 14 Precipitation
- **No formal REST API.** Two approaches:
  1. **PFDS URL scraping:** `https://hdsc.nws.noaa.gov/pfds/pfds_printpage.html?lat={lat}&lon={lon}&data=depth&units=english&series=pds` (returns HTML, must parse)
  2. **pfdf Python library:** `pfdf.data.noaa.atlas14.download(lat, lon)` returns CSV path
  3. **GIS grid download:** Pre-download ASCII grids from https://hdsc.nws.noaa.gov/pfds/pfds_gis.html and extract values at county centroids
- **Recommended approach for batch processing:** Download GIS grids for needed volumes, extract at county centroid lat/lon, store key return periods (10yr, 25yr, 50yr, 100yr per 20-CONTEXT.md)
- **Return periods available:** 1, 2, 5, 10, 25, 50, 100, 200, 500, 1000-year
- **Durations available:** 5min to 60-day (19 options)
- **Atlas 15 migration:** Document that Atlas 15 is in development and will supersede Atlas 14. Build against Atlas 14 now with clear migration path.

### FLOOD-06: NOAA CO-OPS Coastal Water Levels
- **Data endpoint:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
  - Required params: station, begin_date, end_date, product, datum, units, time_zone, format
  - Products: water_level (6-min), hourly_height (hourly), daily_mean (daily), monthly_mean, high_low, predictions
  - Datum: MLLW, MSL, MHHW, NAVD, etc.
  - **Time limits:** 6-min = 1 month max, hourly = 1 year max, daily_mean = 10 years max
- **Metadata endpoint:** `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=waterlevels`
  - Returns all water level stations with id, name, lat, lon, state
- **Flood levels endpoint:** `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{id}/floodlevels.json`
  - Returns: NOS Minor/Moderate/Major flood thresholds, NWS thresholds
- **Station-to-county mapping:** CO-OPS API does not filter by county. Must:
  1. Fetch all water level stations (~300-400 stations nationwide)
  2. Match to coastal counties by lat/lon proximity or state
  3. Store station-to-county mapping as reference data
- **20-year daily window:** Use `product=daily_mean` with `begin_date/end_date` spanning 10 years per request (2 requests for 20 years)

### Coastal County Classification
- **NOAA ENOW definition:** 452 coastal shoreline counties + watershed counties
- **Data source:** ENOW Counties List PDF (https://coast.noaa.gov/data/digitalcoast/pdf/enow-counties-list.pdf) -- must be converted to machine-readable format
- **Alternative:** Census BDS Coastal Counties methodology classifies by shoreline vs watershed
- **Classification scheme (per 20-CONTEXT.md):**
  - **Marine:** Counties adjacent to Atlantic, Pacific, or Gulf of Mexico
  - **Lacustrine:** Counties adjacent to Great Lakes (MN, WI, IL, IN, MI, OH, PA, NY shoreline)
  - **Inland:** All other counties
- **Implementation:** Create `data/reference/coastal_counties.json` with FIPS -> type mapping
  - Source from NOAA ENOW list + Great Lakes state identification
  - ~452 shoreline + ~320 watershed = ~772 coastal counties total
  - For Phase 20, use shoreline counties only (more conservative, direct flood risk)
- **Alaska:** Flag as coastal even without CO-OPS data (per 20-CONTEXT.md)

## Missing Data Framing (per 20-CONTEXT.md)

Two categories of missing data:
1. **Not applicable:** e.g., coastal water levels for inland Tribes, tidal data for Great Lakes
2. **Monitoring gap:** e.g., no USGS gauges in Tribal area, no NFIP claims history

Per-source monitoring gap advocacy actions (Claude's discretion):
- **NFIP (no claims):** "Contact FEMA Region to explore NFIP participation and flood insurance affordability programs"
- **Declarations (none found):** "Request FEMA review of historical disaster impacts that may not have received formal declarations"
- **Streamflow (no gauges):** "Advocate for USGS gauge installation through the Cooperative Water Program or Bureau of Indian Affairs water resources monitoring"
- **Precipitation (no data):** "Request inclusion in next NOAA Atlas update cycle for improved local precipitation frequency estimates"
- **Coastal (inland):** Not applicable framing, not monitoring gap
- **NFHL (no community):** "Contact FEMA Mapping to ensure community flood maps are current and Tribal lands are properly mapped"

## Open Questions

1. **NFIP Claims countyCode format**
   - What we know: The field is called `countyCode` and is searchable. Claims have ~2.7M records.
   - What's unclear: Is `countyCode` a 3-digit county code (requiring separate state filter) or a 5-digit FIPS? The API docs show `countyCode` without specifying padding. Need to verify with a test query.
   - Recommendation: Test with a known county (e.g., `countyCode eq '033'` for King County WA with `state eq 'WA'`). If 3-digit, pair with fipsStateCode. LOW confidence until tested.

2. **Atlas 14 batch approach viability**
   - What we know: GIS grids exist for download. The pfdf library can query per lat/lon.
   - What's unclear: Whether the PFDS web service is reliable enough for 700+ sequential county-centroid queries. GIS grid extraction requires rasterio or gdal.
   - Recommendation: Download GIS grids as primary approach. Fall back to pfdf library if grid processing is too complex. Flag for runtime validation.

3. **Disaster declaration dollar amounts**
   - What we know: 20-CONTEXT.md says "Store all dollar amounts: IA, PA, HMGP." But DisasterDeclarationsSummaries does NOT have dollar fields.
   - What's unclear: Whether dollar amounts should be fetched from separate PA/HMGP datasets (adding 2 more OpenFEMA API integrations).
   - Recommendation: Phase 20 stores declarations with program flags. Add a follow-up task (or separate plan) to join PA/HMGP dollar amounts by disaster number. Scope creep risk if included in initial build.

4. **USGS drainage area filter threshold**
   - What we know: Per 20-CONTEXT.md, filter by drainage area size threshold (Claude's discretion).
   - What's unclear: The right threshold. Too low = noisy small streams; too high = only major rivers.
   - Recommendation: drainage_area >= 10 sq mi AND drainage_area <= 5,000 sq mi. This captures meaningful watersheds while excluding both tiny headwater streams and massive river mainstems. Configurable in scanner_config.json.

5. **CO-OPS station-to-county mapping accuracy**
   - What we know: CO-OPS API returns station lat/lon but not county.
   - What's unclear: How reliably we can assign stations to counties by proximity. Stations may be on state/county borders.
   - Recommendation: Use a simple nearest-county approach based on station coordinates. For the ~300-400 water level stations, this is manageable. Store the mapping in the coastal reference file.

## Sources

### Primary (HIGH confidence)
- OpenFEMA API Documentation: https://www.fema.gov/about/openfema/api -- pagination, filters, OData syntax verified
- OpenFEMA NFIP Claims v2 dataset page: https://www.fema.gov/openfema-data-page/fima-nfip-redacted-claims-v2 -- field names, record count
- OpenFEMA Disaster Declarations v2: https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2 -- field list, date range
- NFIP Community Status Book v1: https://www.fema.gov/openfema-data-page/nfip-community-status-book-v1 -- 15 fields verified, API endpoint
- USGS Water Data APIs: https://api.waterdata.usgs.gov/ -- OGC API collections list verified
- USGS OGC API monitoring-locations queryables: https://api.waterdata.usgs.gov/ogcapi/v0/collections/monitoring-locations/queryables -- county_code, state_code, site_type_code confirmed
- USGS blog (2025 updates): https://waterdata.usgs.gov/blog/wdfn-updates-2025/ -- decommission timeline, peaks not yet migrated
- CO-OPS Data Retrieval API: https://api.tidesandcurrents.noaa.gov/api/prod/ -- datagetter parameters, time limits, products
- CO-OPS Metadata API: https://api.tidesandcurrents.noaa.gov/mdapi/prod/ -- station metadata, flood levels endpoint
- NWPS gauges CSV: https://water.noaa.gov/resources/downloads/reports/nwps_all_gauges_report.csv -- 46 fields, flood stages verified
- dataretrieval-python v1.1.2: https://github.com/DOI-USGS/dataretrieval-python -- get_peak, get_dv, get_info functions

### Secondary (MEDIUM confidence)
- OpenFEMA pagination best practices: https://www.fema.gov/about/openfema/working-with-large-data-sets -- $top max 10,000
- NOAA ENOW coastal counties definition: https://coast.noaa.gov/data/digitalcoast/pdf/defining-coastal-counties.pdf -- 452 shoreline counties
- NOAA Atlas 14 PFDS: https://hdsc.nws.noaa.gov/pfds/ -- web interface confirmed, no formal API
- USGS pfdf library: https://ghsc.code-pages.usgs.gov/lhp/pfdf/api/data/noaa/atlas14.html -- download function parameters
- FEMA NFHL overview: https://www.fema.gov/flood-maps/national-flood-hazard-layer -- data availability, WFS limitations

### Tertiary (LOW confidence)
- Atlas 14 GIS grid extraction approach: inferred from GIS format page, not tested
- Disaster declaration dollar amount join strategy: inferred from dataset structure
- USGS drainage area threshold of 10-5000 sq mi: engineering judgment, not empirically validated
- CO-OPS station count (~300-400 water level stations): approximate from metadata query

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- existing project patterns, established libraries
- Architecture: HIGH -- follows proven 9-step builder template from Phase 19
- API endpoints/fields: MEDIUM -- verified via official docs but not runtime-tested
- Pitfalls: HIGH -- documented from official API limitations and constraints
- Atlas 14 approach: MEDIUM -- no formal API; two viable alternatives identified but not tested
- Data completeness: LOW -- cannot verify coverage rates without running queries

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (30 days -- federal APIs change slowly; USGS migration timeline may shift)
