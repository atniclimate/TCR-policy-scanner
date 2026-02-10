# Technology Stack: Tribe-Specific Advocacy Packet Generation

**Project:** TCR Policy Scanner v1.1
**Researched:** 2026-02-10
**Scope:** NEW capabilities only (DOCX generation + 6 data layers)

---

## Existing Stack (DO NOT RE-ADD)

Already validated in v1.0 -- listed for integration context only:

| Technology | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime |
| aiohttp | >=3.9.0 | Async HTTP client (all scrapers use `BaseScraper._request_with_retry`) |
| python-dateutil | >=2.8.0 | Date parsing |
| jinja2 | >=3.1.0 | Template rendering |
| pytest | (dev) | Test framework |

---

## NEW Libraries to Add

### 1. python-docx -- DOCX Document Generation

| Attribute | Value |
|---|---|
| **Package** | `python-docx` |
| **Pin** | `>=1.1.2,<2.0` |
| **Latest verified** | 1.2.0 (released 2025-06-16) |
| **License** | MIT |
| **Python support** | >=3.9 (compatible with our 3.12) |
| **PyPI downloads** | ~1.3M weekly |
| **Confidence** | HIGH (PyPI verified) |

**Why python-docx:** The only production-stable pure-Python library for creating .docx files. No alternatives worth considering -- Aspose is proprietary/paid, docx-template (docxtpl) wraps python-docx and adds Jinja2 templating but we already have Jinja2 and need fine-grained control over table formatting, merged cells, and conditional sections.

**Capabilities verified (from official docs):**
- Tables with cell merging, column widths, row heights, and built-in Word styles
- Headers and footers (per-section, different first page)
- Page breaks (paragraph-level `page_break_before` style property)
- Images (inline via `add_picture()` with width/height control)
- Paragraph styles, character formatting (bold, italic, color, font size)
- Section properties (page size, margins, orientation)

**What python-docx does NOT do (confirmed limitations):**
- No mail merge / template variable substitution (use docxtpl if needed later)
- No chart generation (would need `python-pptx` or pre-rendered images)
- No PDF conversion (would need LibreOffice headless or similar)
- Headers/footers cannot contain dynamically-added media other than images

**Integration pattern:** Synchronous library. Call from report generation phase after all async data collection is complete. No need to wrap in asyncio -- document construction is CPU-bound, not I/O-bound, and takes <1s per document.

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
```

### 2. rapidfuzz -- Fuzzy String Matching

| Attribute | Value |
|---|---|
| **Package** | `rapidfuzz` |
| **Pin** | `>=3.6.0,<4.0` |
| **Latest verified** | 3.14.3 (released 2025-11-01) |
| **License** | MIT |
| **Python support** | >=3.10 (compatible with our 3.12) |
| **Confidence** | HIGH (PyPI verified) |

**Why rapidfuzz over thefuzz:** rapidfuzz is the clear winner for this use case:
- **Performance:** C++ core, 10-100x faster than thefuzz (critical when matching 575 Tribe names against potentially thousands of USASpending recipients)
- **License:** MIT (thefuzz is GPL -- viral license risk)
- **API-compatible:** Drop-in replacement for thefuzz/fuzzywuzzy
- **Active maintenance:** Regular releases through 2025

**Why NOT thefuzz:** GPL license is unacceptable for a project that may be distributed. thefuzz is also pure Python and prohibitively slow for batch matching.

**Integration pattern:** Used in the USASpending award-matching layer to fuzzy-match tribal entity names against `Recipient Name` fields from the existing USASpending scraper.

```python
from rapidfuzz import fuzz, process

# Match a Tribe name against USASpending recipients
# Use token_sort_ratio to handle word-order differences
# e.g. "Navajo Nation" vs "THE NAVAJO NATION"
matches = process.extract(
    tribe_name,
    recipient_names,
    scorer=fuzz.token_sort_ratio,
    score_cutoff=80,
    limit=5,
)
```

### 3. censusgeocode (OPTIONAL -- evaluate vs. raw aiohttp)

| Attribute | Value |
|---|---|
| **Package** | `censusgeocode` |
| **Latest verified** | 0.6.0 (on PyPI) |
| **License** | MIT |
| **Confidence** | MEDIUM |

**Recommendation: DO NOT ADD.** Use raw aiohttp calls to the Census Geocoder API instead. Reasons:
- censusgeocode is synchronous (wraps `requests`), would need thread pool executor
- Our existing `BaseScraper._request_with_retry` already handles the HTTP + retry pattern
- One less dependency to maintain
- Census API is simple enough (single GET endpoint) to not need a wrapper

---

## Libraries Explicitly NOT Adding (and Why)

| Library | Why Not |
|---|---|
| `thefuzz` / `fuzzywuzzy` | GPL license; slower than rapidfuzz; no advantages |
| `censusgeocode` | Sync-only; trivial to call Census API via aiohttp directly |
| `geopandas` / `shapely` | Massive dependencies (GDAL, etc.); we don't need GIS operations -- just lat/lng lookups and FIPS code matching |
| `openpyxl` | Not needed; we read XLSX once at build time, can vendor as CSV/JSON |
| `docxtpl` | Adds Jinja2-in-DOCX templating; we already have Jinja2 for data prep and python-docx for document construction -- docxtpl adds complexity without benefit for our programmatic table/section generation |
| `requests` | Already using aiohttp for all HTTP; adding requests creates two HTTP stacks |
| `pandas` | Heavyweight for CSV parsing; stdlib `csv` module + list comprehensions suffice for our data volumes |

---

## Data Layer 1: Tribal Registry (575 Federally Recognized Tribes)

### Primary Source: Federal Register + EPA Tribes Names Service

**CRITICAL UPDATE:** As of January 30, 2026, there are **575** federally recognized Tribes (not 574). The Lumbee Tribe of North Carolina was added following the FY2026 NDAA (December 18, 2025). Federal Register document 2026-01899.

#### EPA Tribes Names Service API

| Attribute | Value |
|---|---|
| **Base URL** | `https://cdxapi.epa.gov/oms-tribes-rest-services` |
| **Endpoints** | `GET /api/v1/tribes` (all tribes, basic data) |
| | `GET /api/v1/tribeDetails` (detailed, filterable) |
| | `GET /api/v1/tribeDetails/{epaTribalInternalId}` (single tribe) |
| **Authentication** | **None required** (public API, no key) |
| **Rate limits** | Not documented; use polite 0.3s delay per existing pattern |
| **Response format** | JSON |
| **Confidence** | HIGH (EPA official documentation verified) |

**Key fields returned:**
- `epaTribalInternalId` -- unique EPA identifier
- `currentName` -- official current tribal name
- `currentBIATribalCode` -- BIA code (critical for cross-referencing)
- `currentBIARecognizedFlag` -- federal recognition status
- `epaLocations` -- state, EPA region (geographic placement)
- `names` -- historical names with date ranges (useful for fuzzy matching aliases)
- `biaTribalCodes` -- historical BIA codes

**Integration strategy:**
1. Fetch all 575 Tribes via `GET /api/v1/tribes` on first run
2. Cache locally as JSON (tribes list changes ~1x/year)
3. Use `currentName` + historical `names` as the fuzzy-match corpus for USASpending matching
4. Use `epaLocations` for state-level geographic assignment

#### BIA Tribal Leaders Directory (Supplementary)

| Attribute | Value |
|---|---|
| **URL** | `https://www.bia.gov/service/tribal-leaders-directory` |
| **Format** | Interactive web directory (no REST API) |
| **Use** | Manual reference / validation only |
| **Confidence** | HIGH (BIA official) |

**Note:** The BIA directory is interactive/map-based with no documented REST API. The EPA Tribes Names Service is the programmatic source. For geographic coordinates of tribal lands, the best source is the Census TIGER/Line AIANNH (American Indian/Alaska Native/Native Hawaiian Areas) shapefile, but we should avoid GIS dependencies and instead use the state-level data from EPA + county FIPS matching.

#### Federal Register (Official Authority)

| Attribute | Value |
|---|---|
| **Document** | FR Doc 2026-01899 (January 30, 2026) |
| **URL** | `https://www.federalregister.gov/documents/2026/01/30/2026-01899/...` |
| **Use** | Authoritative count validation (575 entities) |
| **Format** | PDF list -- not machine-readable |
| **Confidence** | HIGH (legal authority) |

---

## Data Layer 2: Congressional Mapping

### Congress.gov API v3 (Members + Committees)

The existing `CongressGovScraper` already authenticates and queries this API for bills. The member/committee endpoints use the same API key and base URL.

| Attribute | Value |
|---|---|
| **Base URL** | `https://api.congress.gov/v3` |
| **Auth** | API key via `X-Api-Key` header (already configured in existing scraper) |
| **Rate limit** | 5,000 requests/hour |
| **Response format** | JSON |
| **Pagination** | 20 results default, max 250 per page, offset-based |
| **Confidence** | HIGH (GitHub docs + existing working integration) |

#### Member Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /member/congress/119/{stateCode}` | All members from a state in 119th Congress |
| `GET /member/congress/119/{stateCode}/{district}` | Specific House member by state+district |
| `GET /member/{bioguideId}` | Full member detail (terms, leadership, contact) |

**Key fields returned:**
- `bioguideId`, `name` (first, last, directOrder, inverted)
- `state`, `district`, `partyName`
- `terms` (array: chamber, congress, startYear, endYear, district, memberType)
- `officialUrl`, `officeAddress`, `phoneNumber`
- `depiction.imageUrl` (official portrait)
- `sponsoredLegislation` / `cosponsoredLegislation` counts + URLs

**IMPORTANT LIMITATION:** Member endpoint does NOT return committee assignments directly. Committee membership requires separate queries.

#### Committee Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /committee/119/house` | All House committees in 119th Congress |
| `GET /committee/119/senate` | All Senate committees in 119th Congress |
| `GET /committee/{chamber}/{systemCode}` | Specific committee detail |

**Note:** The committee endpoint does not directly return member rosters. To build a member-to-committee mapping, you must either:
1. Query each committee and find members (if the API supports it -- documentation is ambiguous), OR
2. Use the ProPublica Congress API (free, has `/members/{id}/committees`), OR
3. Scrape committee membership from congress.gov pages

**Recommendation:** Start with Congress.gov API for member data (already integrated). For committee assignments, build a static lookup table from congress.gov website data that updates per Congress (every 2 years). This avoids API complexity and rate limit pressure.

### Census Geocoder API (Coordinate-to-District Mapping)

| Attribute | Value |
|---|---|
| **Base URL** | `https://geocoding.geo.census.gov/geocoder` |
| **Endpoint** | `GET /geographies/coordinates` |
| **Auth** | **None required** |
| **Rate limits** | Not documented; use polite delays |
| **Response format** | JSON |
| **Confidence** | HIGH (Census Bureau official, verified) |

**Query format:**
```
GET /geographies/coordinates?x={longitude}&y={latitude}&benchmark=Public_AR_Current&vintage=Current_Current&layers=all&format=json
```

**Returns:** Congressional district (119th), state legislative districts, county FIPS, census tract -- all in one call.

**Integration strategy:** For each Tribe, we need lat/lng coordinates. Options:
1. If Tribe has a known reservation centroid (from AIANNH data), use that
2. If Tribe is state-identified but not geographically specific, use state capital or known administrative location
3. Map Tribe -> county FIPS -> congressional district

**Batch API also available:** POST to `/geographies/addressbatch` with CSV upload for up to 10,000 addresses. Useful if we pre-compute all 575 Tribe locations.

---

## Data Layer 3: USASpending Award Matching

### Existing Infrastructure

The `USASpendingScraper` already queries `https://api.usaspending.gov/api/v2/search/spending_by_award/` by CFDA number. It returns `Recipient Name` fields.

### New Capability: Per-Tribe Fuzzy Matching

**No new API endpoints needed.** The matching happens locally:

1. Existing scraper pulls award data with `Recipient Name` field
2. New matching layer uses `rapidfuzz` to match each `Recipient Name` against:
   - Current EPA tribal names (575 entries)
   - Historical tribal names (from EPA Tribes Names Service `names` array)
   - Known abbreviations/variants (manually curated aliases)

**USASpending Recipient Name Patterns for Tribes:**
- "THE NAVAJO NATION" (uppercase, with "THE")
- "MUSCOGEE (CREEK) NATION" (parenthetical alternate names)
- "PUEBLO OF LAGUNA" (Pueblo naming convention)
- "CONFEDERATED TRIBES OF THE COLVILLE RESERVATION" (long formal names)
- "SITKA TRIBE OF ALASKA" (state qualifier)

**Matching strategy:**
```python
from rapidfuzz import fuzz, process

# Pre-process: build name corpus from EPA data
tribe_names = {}  # Maps normalized name -> tribe_id
for tribe in epa_tribes:
    # Add current name
    tribe_names[normalize(tribe["currentName"])] = tribe["epaTribalInternalId"]
    # Add historical names
    for hist in tribe.get("names", []):
        tribe_names[normalize(hist["name"])] = tribe["epaTribalInternalId"]

# Match recipients
def match_recipient_to_tribe(recipient_name: str) -> tuple[str | None, int]:
    """Returns (tribe_id, confidence_score) or (None, 0)."""
    result = process.extractOne(
        normalize(recipient_name),
        tribe_names.keys(),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=75,
    )
    if result:
        matched_name, score, _ = result
        return tribe_names[matched_name], score
    return None, 0
```

**Score threshold recommendation:** 75 for `token_sort_ratio`. Below 75 produces too many false positives. Above 85 misses legitimate variations. Calibrate against known matches.

---

## Data Layer 4: Hazard Profiling

### 4A. FEMA National Risk Index (NRI)

| Attribute | Value |
|---|---|
| **Data access** | **CSV download** (NOT available via OpenFEMA API) |
| **Download URL** | `https://www.fema.gov/about/openfema/data-sets/national-risk-index-data` |
| **Current version** | v1.20 (December 2025) |
| **Geographic levels** | County, Census Tract, State, **Tribal Areas** |
| **Format** | CSV, Shapefile, Geodatabase |
| **Auth** | None (public download) |
| **Confidence** | HIGH (FEMA official, verified December 2025 release) |

**CRITICAL FINDING:** NRI data is marked "Files Only" on the OpenFEMA datasets page -- it is NOT available through the OpenFEMA REST API. This means we must download the CSV file(s) and embed/bundle them with the project rather than querying an API at runtime.

**Data fields (per county/tribal area):**
- Overall Risk Index (composite score + rating)
- Expected Annual Loss (EAL) -- total and per-hazard for all 18 hazard types
- Social Vulnerability score
- Community Resilience score
- Per-hazard scores: Annualized Frequency, Exposure, Historical Loss Ratio
- FIPS codes for geographic join

**18 Hazard Types:**
Avalanche, Coastal Flooding, Cold Wave, Drought, Earthquake, Hail, Heat Wave, Hurricane, Ice Storm, Inland Flooding, Landslide, Lightning, Strong Wind, Tornado, Tsunami, Volcanic Activity, **Wildfire**, Winter Weather

**Integration strategy:**
1. Download NRI CSV at build time (or cache with monthly refresh)
2. Parse with stdlib `csv` module into dict keyed by county FIPS
3. For each Tribe, look up county FIPS -> NRI hazard profile
4. Extract top 3-5 hazards by Expected Annual Loss for the advocacy packet
5. File size: county-level CSV is manageable (~3,200 rows, ~50MB with all fields)

### 4B. EPA EJScreen -- Environmental Justice Indicators

| Attribute | Value |
|---|---|
| **Status** | **REMOVED from EPA website (Feb 5, 2025)** |
| **Alternative access** | Data files preserved at multiple sources |
| **Data URL (Zenodo)** | `https://zenodo.org/records/14767363` |
| **Data URL (EPA FTP, may be down)** | `https://gaftp.epa.gov/EJScreen/` |
| **Alternative tool** | `https://screening-tools.com/epa-ejscreen` (PEDP coalition) |
| **Version** | 2.3 (2024 data, latest before removal) |
| **Geographic level** | Census block group, Census tract |
| **Format** | CSV, Geodatabase |
| **Confidence** | MEDIUM (data preserved but official API unreliable) |

**RISK FLAG:** EJScreen was removed from EPA's website in February 2025. The mapping API at `ejscreen.epa.gov` may be intermittently available or permanently down. **Do NOT depend on the EJScreen REST API for production use.**

**Recommended approach:** Download the EJScreen v2.3 CSV data file from Zenodo archive and bundle it:
- Block-group level data with 13 environmental indicators
- EJ Index and Supplemental Index per indicator
- Join to Tribal areas via census tract/block group FIPS codes

**Key indicators relevant to Tribal climate resilience:**
- Particulate Matter 2.5
- Ozone
- Diesel Particulate Matter
- Proximity to Superfund sites (NPL)
- Proximity to hazardous waste facilities (RMP)
- Wastewater discharge indicator
- Underground Storage Tanks
- Low-Income percentage
- Linguistic Isolation
- Unemployment Rate

**Integration strategy:**
1. Download EJScreen CSV from Zenodo (one-time, ~200MB at block group level)
2. Aggregate to census tract level for Tribal land areas
3. Store as compressed JSON/CSV in project data directory
4. Look up by census tract FIPS codes associated with each Tribe's geography

### 4C. USFS Wildfire Risk to Communities

| Attribute | Value |
|---|---|
| **Download URL** | `https://wildfirerisk.org/download/` |
| **Direct file** | `https://wildfirerisk.org/wp-content/uploads/2025/05/wrc_download_202505.xlsx` |
| **Version** | 2024 (LANDFIRE 2020 v2.2.0 fuels data) |
| **Geographic levels** | Communities, **Tribal Areas**, Counties, States |
| **Format** | XLSX spreadsheet |
| **Auth** | None (public download) |
| **Confidence** | HIGH (USFS official, direct download URL verified) |

**Key data fields:**
- Risk to Homes (national percentile rank)
- Wildfire Likelihood (national percentile rank)
- Risk Reduction Zones (Minimal/Indirect/Direct Exposure, Wildfire Transmission)
- Fraction of buildings exposed (direct + indirect)

**Why this is valuable:** It provides **Tribal area-specific** wildfire risk scores already computed. No need to intersect geographies -- the USFS dataset includes Tribal areas as a first-class geographic unit.

**Integration strategy:**
1. Download XLSX once at build time
2. Convert to JSON/CSV at build time (use `openpyxl` in a one-time build script, or convert manually and commit the CSV)
3. Index by Tribal area name for direct lookup
4. XLSX is small (~5MB), so embedding in project is fine

**Note on openpyxl:** We said "do not add openpyxl" to runtime dependencies. Correct -- use it only in a one-time data conversion script, OR pre-convert the XLSX to CSV manually and commit the CSV. The runtime code reads CSV only.

### 4D. NOAA Climate Data (via ACIS Web Services)

| Attribute | Value |
|---|---|
| **Base URL** | `http://data.rcc-acis.org/` |
| **Endpoints** | `MultiStnData` (multiple stations by area) |
| | `GridData` (gridded climate data) |
| | `General` (geographic metadata) |
| **Auth** | **None required** |
| **Rate limits** | Not documented; use polite delays |
| **Response format** | JSON |
| **Confidence** | MEDIUM (ACIS docs verified, but county-level projection data availability unclear) |

**Available climate elements:**
- Maximum temperature (`maxt`), Minimum temperature (`mint`), Average temperature (`avgt`)
- Precipitation (`pcpn`)
- Snowfall (`snow`), Snow depth (`snwd`)
- Cooling/Heating/Growing degree days (`cdd`, `hdd`, `gdd`)

**Query by county FIPS:**
```
POST http://data.rcc-acis.org/MultiStnData
{
    "county": "36001",
    "sdate": "2020-01-01",
    "edate": "2025-12-31",
    "elems": ["maxt", "mint", "pcpn"]
}
```

**IMPORTANT LIMITATION:** ACIS provides **historical climate observations and normals**, NOT future climate projections. For projections, the source is the NOAA Climate Explorer (LOCA downscaled data), which does not have a documented REST API -- it uses ACIS internally but exposes data through its web UI and downloadable Jupyter notebooks.

**Recommendation for climate projections:**
1. Use ACIS for historical climate normals (30-year averages) per county -- this is well-supported via API
2. For forward-looking projections, download county-level projection data from Climate Explorer's data directory: `https://crt-climate-explorer.nemac.org/data/`
3. Pre-download projection summaries for all US counties and bundle as static data
4. This is a PHASE 2 enhancement -- historical normals are sufficient for MVP

---

## Data Layer 5: Economic Impact

### 5A. BEA Regional Economic Data (FREE Alternative to RIMS II)

| Attribute | Value |
|---|---|
| **Base URL** | `https://apps.bea.gov/api/data` |
| **Auth** | **Free API key required** (register at `apps.bea.gov/api/signup/`) |
| **Rate limits** | Not documented; standard federal API etiquette |
| **Response format** | JSON |
| **Confidence** | HIGH (BEA official, verified) |

**CRITICAL FINDING:** BEA RIMS II multipliers are **pay-per-use ($500/region or $150/industry)** with NO free API access. They are purchased through BEA staff, not available programmatically.

**Recommended free alternative:** BEA Regional Data API provides county-level GDP and personal income data that can be used to derive simplified economic impact estimates:

| Table | Content | Use |
|---|---|---|
| `CAGDP9` | Real GDP by county | County economic output for context |
| `CAINC1` | Personal income summary by county | Per capita income for vulnerability context |
| `CAINC5N` | Personal income by NAICS industry | Industry breakdown for impact narrative |

**Query format:**
```
GET https://apps.bea.gov/api/data?UserID={key}&method=GetData&datasetname=Regional&TableName=CAGDP9&LineCode=1&GeoFIPS={county_fips}&Year=2023,2024&ResultFormat=JSON
```

**Integration with economic impact narrative:**
Instead of RIMS II multipliers (which we cannot access for free), use a simplified approach:
1. Pull county GDP and per-capita income from BEA
2. Show grant amounts as % of county GDP for scale
3. Use FEMA's published pre-calculated Benefit-Cost ratios for hazard mitigation projects (available in FEMA BCA documentation)
4. FEMA's BCA Toolkit provides standard multiplier assumptions for Tribal hazard mitigation grants

### 5B. FEMA Benefit-Cost Analysis (Streamlined)

| Attribute | Value |
|---|---|
| **Documentation** | `https://www.fema.gov/grants/tools/benefit-cost-analysis` |
| **Methodology** | FEMA's published pre-calculated benefit-cost efficiencies |
| **Discount rate** | 3.1% (reduced from 7% -- favorable for Tribal Nations) |
| **Auth** | None (published methodology) |
| **Confidence** | HIGH (FEMA official) |

FEMA publishes streamlined cost-effectiveness values for projects under $1M and offers BCA assistance specifically to Tribal Nations. These published values can be used as standard multipliers without purchasing RIMS II data:
- Pre-calculated benefit-cost values per project type (flood, wind, fire)
- Streamlined narrative methodology for Tribal projects under $1M
- Standard economic parameters (discount rate, project useful life)

**Integration strategy:**
1. Embed FEMA's published BCA parameters as static config
2. For each Tribe's grant amount, compute simplified BCR using FEMA's streamlined methodology
3. Contextualize with BEA county GDP data
4. Flag in the DOCX packet: "Economic impact calculated using FEMA streamlined BCA methodology"

---

## Data Layer 6: DOCX Document Generation

### Architecture Decision: Build Documents Programmatically

**Decision: Use python-docx directly, NOT a template-based approach.**

**Rationale:**
- Advocacy packets have highly dynamic content (variable number of hazards, programs, legislators)
- Table row counts vary per Tribe (some have 3 relevant programs, some have 12)
- Conditional sections (wildfire section only for fire-prone Tribes, coastal flooding only for coastal)
- Template approaches (docxtpl) struggle with conditional table rows and dynamic section inclusion
- python-docx's programmatic API gives full control over every element

**Document structure (per Tribe):**
```
1. Cover page (Tribe name, date, TCR branding)
2. Executive Summary (key stats, top recommendations)
3. Tribal Profile (location, congressional reps, regional context)
4. Hazard Profile (NRI data, top hazards, EAL figures)
5. Funding Landscape (current obligations per CFDA, award amounts)
6. Economic Impact (BCR estimates, county GDP context)
7. Congressional Advocacy Guide (members, committees, talking points)
8. Appendix: Data Sources and Methodology
```

**Performance estimate:** python-docx generates a 20-page document in <1 second. For 575 Tribes: ~10 minutes total for all packets. Parallelizable if needed (each packet is independent), but serial generation is sufficient.

---

## Updated requirements.txt

```
# Existing (unchanged)
aiohttp>=3.9.0
python-dateutil>=2.8.0
jinja2>=3.1.0

# New for v1.1
python-docx>=1.1.2,<2.0
rapidfuzz>=3.6.0,<4.0
```

**That's it. Two new runtime dependencies.** All data APIs are accessed via the existing aiohttp stack. Static data files (NRI CSV, EJScreen CSV, Wildfire Risk CSV) are bundled as project data, not library dependencies.

---

## API Summary Matrix

| Data Source | Type | Auth | Rate Limit | Format | Async Compatible | Confidence |
|---|---|---|---|---|---|---|
| EPA Tribes Names | REST API | None | Undocumented | JSON | Yes (aiohttp) | HIGH |
| Congress.gov Members | REST API | API key (existing) | 5,000/hr | JSON | Yes (aiohttp) | HIGH |
| Census Geocoder | REST API | None | Undocumented | JSON | Yes (aiohttp) | HIGH |
| USASpending Awards | REST API | None (existing) | Undocumented | JSON | Yes (existing scraper) | HIGH |
| FEMA NRI | CSV download | None | N/A | CSV | N/A (static file) | HIGH |
| EJScreen | CSV download | None | N/A | CSV | N/A (static file) | MEDIUM |
| Wildfire Risk | XLSX download | None | N/A | XLSX->CSV | N/A (static file) | HIGH |
| NOAA/ACIS Climate | REST API | None | Undocumented | JSON | Yes (aiohttp) | MEDIUM |
| BEA Regional | REST API | Free API key | Undocumented | JSON | Yes (aiohttp) | HIGH |
| FEMA BCA | Published values | None | N/A | Static config | N/A | HIGH |

---

## Integration Architecture with Existing Stack

```
Existing Pipeline (v1.0)                New Data Layers (v1.1)
========================                ======================

BaseScraper (aiohttp)  --------+------> TribalRegistryScraper (EPA API)
                               |------> CongressMemberScraper (Congress.gov API)
                               |------> CensusDistrictScraper (Census Geocoder)
                               |------> ClimateDataScraper (ACIS API)
                               |------> BEARegionalScraper (BEA API)
                               |
USASpendingScraper ----+------> FuzzyMatcher (rapidfuzz) ---> per-Tribe awards
                       |
Static Data Loaders ---+------> NRILoader (CSV)
                       |------> EJScreenLoader (CSV)
                       |------> WildfireRiskLoader (CSV)
                       |------> FEMABCAConfig (static params)
                       |
All data collected ----+------> DocxPacketGenerator (python-docx)
                               |  -> 575 individual .docx files
                               |  -> outputs/packets/{tribe_id}/{date}.docx
```

New scrapers extend `BaseScraper` to inherit retry logic, rate limiting, and User-Agent compliance. Static data loaders are simple file readers, not scrapers.

---

## Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| EJScreen data becomes fully unavailable | MEDIUM | Zenodo archive is durable; Harvard Dataverse backup exists; data is v2.3 frozen |
| Census Geocoder rate-limits batch requests | LOW | Pre-compute all 575 Tribe->district mappings once, cache result |
| NRI CSV format changes in future releases | LOW | Data dictionary versioned; pin to v1.20; check on quarterly refresh |
| BEA API key registration blocked | LOW | Registration is instant/free; key is per-email; have backup email |
| Climate projections need more granularity | MEDIUM | Phase 2: download LOCA county projections from Climate Explorer |
| RIMS II multipliers needed for accurate impact | MEDIUM | FEMA BCA streamlined approach is sufficient for advocacy context |
| Lumbee Tribe addition changes count to 575 | RESOLVED | Updated count; EPA API will reflect this when refreshed |
| Congress.gov committee API doesn't return members | MEDIUM | Build static committee-member lookup; update per Congress |

---

## Sources

### Verified (HIGH confidence)
- [python-docx 1.2.0 on PyPI](https://pypi.org/project/python-docx/) -- version, license, Python support
- [RapidFuzz 3.14.3 on PyPI](https://pypi.org/project/rapidfuzz/) -- version, license, Python support
- [EPA Tribes Names Service](https://www.epa.gov/data/tribes-names-service) -- API endpoints, no-auth, fields
- [Congress.gov API Member Endpoint](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md) -- endpoints, rate limits
- [Congress.gov API Committee Endpoint](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/CommitteeEndpoint.md) -- committee structure
- [OpenFEMA API Documentation](https://www.fema.gov/about/openfema/api) -- base URL, query format, no-auth
- [FEMA NRI Data](https://www.fema.gov/about/openfema/data-sets/national-risk-index-data) -- CSV download, v1.20, December 2025
- [Census Geocoder API](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html) -- endpoint format, coordinates lookup
- [USFS Wildfire Risk to Communities](https://wildfirerisk.org/download/) -- download URL, tribal area data
- [Federal Register 2026-01899](https://www.federalregister.gov/documents/2026/01/30/2026-01899/) -- 575 Tribes, Lumbee addition
- [BEA API Documentation](https://apps.bea.gov/API/docs/index.htm) -- free key, Regional dataset
- [FEMA Benefit-Cost Analysis](https://www.fema.gov/grants/tools/benefit-cost-analysis) -- streamlined BCA, 3.1% discount rate

### Partially Verified (MEDIUM confidence)
- [ACIS Web Services](https://docs.rcc-acis.org/acisws/) -- endpoints verified, county-level projection availability unclear
- [EJScreen Data on Zenodo](https://zenodo.org/records/14767363) -- archived data verified, long-term availability uncertain
- [Climate Explorer](https://crt-climate-explorer.nemac.org/) -- data directory exists, programmatic access underdocumented
- [BEA RIMS II pricing](https://apps.bea.gov/regional/rims/rimsii/) -- $500/region confirmed via search, no free API confirmed
