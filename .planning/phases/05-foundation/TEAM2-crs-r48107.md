# Team 2: CRS R48107 Data Extraction Research (CONG-01)

**Researched:** 2026-02-10
**Domain:** Tribe-to-congressional-district mapping
**Confidence:** HIGH (primary data source verified, alternative superior source identified)

---

## Report Overview

CRS Report R48107, "Selected Tribal Lands in 118th Congressional Districts," is a Congressional Research Service report authored by Mainon A. Schwartz and Mariel J. Murray. The most recent version (R48107.6) was published September 23, 2024. It maps tribal lands to congressional districts for the 118th Congress (2023-2025) using 2022 Census Bureau data.

**Critical finding:** R48107 covers the **118th Congress** (now expired). The 119th Congress (2025-2026) uses **different district boundaries** due to 2020 redistricting. R48107 is therefore stale for the current Congress. CRS has published a companion report IR10001, "Tribal and Other Indigenous Lands in the 119th Congress" (by Murray and Schwartz), but this report's availability and structure could not be fully verified.

**Better alternative identified:** The Census Bureau publishes a machine-readable, pipe-delimited **119th Congressional District to AIANNH Relationship File** (`tab20_cd11920_aiannh20_natl.txt`) that provides the same Tribe-to-district crosswalk in a directly parseable format. This is the recommended primary data source.

## Access Methods

### CRS R48107 (118th Congress -- STALE)

| Method | URL | Format | Status |
|--------|-----|--------|--------|
| Congress.gov product page | https://www.congress.gov/crs-product/R48107 | Landing page | Available |
| PDF v1 (Jun 2024) | https://www.congress.gov/crs_external_products/R/PDF/R48107/R48107.1.pdf | PDF | Available |
| PDF v6 (Sep 2024) | https://www.congress.gov/crs_external_products/R/PDF/R48107/R48107.6.pdf | PDF (latest) | Available |
| FAS mirror | https://sgp.fas.org/crs/misc/R48107.pdf | PDF | Available |
| EveryCRSReport | https://www.everycrsreport.com/reports/R48107.html | HTML summary | Available |
| HTML table view | https://www.congress.gov/crs_external_products/R/HTML/R48107.web.html | HTML (403 error) | Blocked |

**Key limitation:** R48107 is a PDF report, not structured data. No CSV/Excel/JSON version exists. The HTML version returns 403 errors from Congress.gov.

### Census CD119-AIANNH Relationship File (119th Congress -- CURRENT)

| Resource | URL | Format | Status |
|----------|-----|--------|--------|
| National file | https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_aiannh20_natl.txt | Pipe-delimited TXT (178KB) | Available, verified |
| State files | https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_aiannh20_st{NN}.txt | Pipe-delimited TXT | Available (52 files) |
| Record layout | https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/cong-dist-rel-record-layout.html | HTML | Available |
| All dates | 2024-10-24 | -- | Current for 119th Congress |

### CRS Congressional District Geography Workbook (119th Congress)

| Resource | URL | Format | Status |
|----------|-----|--------|--------|
| Product page | https://www.congress.gov/crs-product/IN12489 | Landing page | Available |
| Excel download | https://www.crs.gov/Products/Documents/CDGW_119CD/xlsm/ | Excel (.xlsm) | Available (CRS.gov login may be required) |
| Latest update | January 12, 2026 | -- | Current |

**Note:** The CRS Workbook is an Excel file with ~532,000 rows across 45 geographic categories including "Native American Areas" and "Tribal Government Offices" (added Aug 2025). However, it requires CRS.gov access, which is restricted to congressional users. The Census relationship file is publicly available and contains the same underlying data.

## Table Extraction Approach

### Recommendation: DO NOT extract from the CRS R48107 PDF

The CRS R48107 PDF is the wrong approach for three reasons:

1. **118th Congress districts** -- stale for the current 119th Congress
2. **PDF extraction is fragile** -- the report contains 24 state-specific tables plus 3 appendix tables with varying formats
3. **Machine-readable alternative exists** -- the Census CD119-AIANNH file provides the same crosswalk as structured data

### Recommended Approach: Use Census CD119-AIANNH Relationship File

**Use the file:** `tab20_cd11920_aiannh20_natl.txt`

**File format:** Pipe-delimited (`|`) text, 178KB, ~3000+ rows

**Columns (17 fields):**

| Column | Description | Example |
|--------|-------------|---------|
| `OID_CD119_20` | Census object ID for congressional district | 2119035781135773 |
| `GEOID_CD119_20` | State FIPS + district code (4 chars) | 0401 (AZ-01) |
| `NAMELSAD_CD119_20` | District name | "Congressional District 1" |
| `AREALAND_CD119_20` | Total district land area (sq meters) | 18752973689 |
| `AREAWATER_CD119_20` | Total district water area (sq meters) | 2274743296 |
| `MTFCC_CD119_20` | MAF/TIGER feature class code | G5200 |
| `FUNCSTAT_CD119_20` | Functional status | N |
| `OID_AIANNH_20` | Census object ID for AIANNH area | 2519076091260 |
| `GEOID_AIANNH_20` | AIANNH area census code (4 chars) | 2430 (Navajo) |
| `NAMELSAD_AIANNH_20` | AIANNH area name + legal/stat description | "Navajo Nation Reservation and Off-Reservation Trust Land" |
| `AREALAND_AIANNH_20` | Total AIANNH land area (sq meters) | ... |
| `AREAWATER_AIANNH_20` | Total AIANNH water area (sq meters) | ... |
| `MTFCC_AIANNH_20` | AIANNH feature class code | G2100 |
| `CLASSFP_AIANNH_20` | Classification code (see below) | D1 |
| `FUNCSTAT_AIANNH_20` | Functional status | A |
| `AREALAND_PART` | Land area of the intersection (sq meters) | 1420623 |
| `AREAWATER_PART` | Water area of the intersection (sq meters) | 7844 |

**Key fields for the crosswalk:**
- `GEOID_CD119_20` -> parse state FIPS (first 2 chars) + district number (last 2 chars) -> "AZ-01", "NM-02", etc.
- `GEOID_AIANNH_20` -> Census AIANNH area code (links to specific tribal area)
- `NAMELSAD_AIANNH_20` -> Human-readable tribal area name
- `CLASSFP_AIANNH_20` -> Type of area (see classification codes)
- `AREALAND_PART` -> Size of the overlap (for "how much" of the tribal area is in this district)

### CLASSFP Classification Codes (AIANNH)

| Code | Meaning | Relevance |
|------|---------|-----------|
| D1 | Federally recognized reservation + off-reservation trust land | **Primary target** |
| D2 | Federally recognized reservation only | **Primary target** |
| D3 | Federally recognized off-reservation trust land only | **Primary target** |
| D5 | Off-reservation trust land portion (of D1 entity) | **Primary target** |
| D8 | Reservation portion (of D1 entity) | **Primary target** |
| D6 | Oklahoma Tribal Statistical Area (OTSA) or Tribal Designated Statistical Area (TDSA) | **Include** (OK Tribes) |
| E1 | Alaska Native Village Statistical Area (ANVSA) | **Include** (AK Tribes) |
| D4 | State-recognized reservation | Exclude (not federally recognized) |
| D9 | State Designated Tribal Statistical Area (SDTSA) | Exclude |
| F1 | Hawaiian Home Lands | Exclude (not Tribal) |

### Python Parsing Code

```python
import csv
from collections import defaultdict
from pathlib import Path

def parse_cd119_aiannh(filepath: Path) -> dict[str, list[dict]]:
    """Parse Census CD119-AIANNH relationship file into tribe-to-district mapping.

    Returns: dict keyed by AIANNH GEOID -> list of district records
    """
    # CLASSFP codes for federally recognized tribal areas
    FEDERAL_CLASSFP = {"D1", "D2", "D3", "D5", "D8", "D6", "E1"}

    # State FIPS to abbreviation
    FIPS_TO_STATE = {
        "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
        "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
        "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
        "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
        "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
        "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
        "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
        "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
        "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
        "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
        "56": "WY",
    }

    tribe_districts = defaultdict(list)

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            classfp = row["CLASSFP_AIANNH_20"]
            if classfp not in FEDERAL_CLASSFP:
                continue

            cd_geoid = row["GEOID_CD119_20"]
            state_fips = cd_geoid[:2]
            district_num = cd_geoid[2:]
            state_abbr = FIPS_TO_STATE.get(state_fips, state_fips)

            # Format district: "AZ-01" or "AK-AL" for at-large
            if district_num == "00":
                district_label = f"{state_abbr}-AL"
            else:
                district_label = f"{state_abbr}-{district_num.zfill(2)}"

            aiannh_geoid = row["GEOID_AIANNH_20"]
            aiannh_name = row["NAMELSAD_AIANNH_20"]
            overlap_land = int(row["AREALAND_PART"])
            total_land = int(row["AREALAND_AIANNH_20"])

            tribe_districts[aiannh_geoid].append({
                "district": district_label,
                "state": state_abbr,
                "aiannh_name": aiannh_name,
                "classfp": classfp,
                "overlap_land_sqm": overlap_land,
                "total_land_sqm": total_land,
                "overlap_pct": round(overlap_land / total_land * 100, 1) if total_land > 0 else 0,
            })

    return dict(tribe_districts)
```

## Data Structure & Fields

### R48107 Table Structure (for reference)

The CRS R48107 PDF contains:
- **Tables 1-24:** State-by-state tables with columns: Map Location, Federally Recognized Tribe, Congressional District
- **Table A-1:** States with multiple districts but only one Tribe (7 states)
- **Table A-2:** Single-district states with multiple Tribes (5 states)
- **Table A-3:** All Tribes alphabetically with State(s) and Congressional District(s) -- this is the master crosswalk table

Table A-3 columns:
- Federally Recognized Tribe (name, with former names in italics)
- State(s)
- Congressional District(s)

### Census Relationship File Structure

The Census file is **row-per-intersection**: each row represents one overlap between one congressional district and one AIANNH area. A Tribe spanning 4 districts produces 4 rows. This is the natural many-to-many representation.

**Derived many-to-many data model:**

```python
@dataclass
class TribeDistrictMapping:
    """Many-to-many relationship between Tribal areas and congressional districts."""
    aiannh_geoid: str          # Census AIANNH code, e.g., "2430"
    aiannh_name: str           # e.g., "Navajo Nation Reservation and Off-Reservation Trust Land"
    districts: list[dict]      # List of {district, state, overlap_pct}
    states: list[str]          # Unique states, e.g., ["AZ", "NM", "UT"]
    classfp: str               # AIANNH classification code
```

## Multi-State & Alaska Handling

### Multi-State Tribes (e.g., Navajo Nation)

The Census relationship file naturally handles multi-state Tribes because each row is an intersection. The Navajo Nation (AIANNH GEOID 2430) appears in the file as multiple rows:
- One row for the AZ-01 overlap
- One row for the AZ-02 overlap
- One row for the NM-02 overlap
- One row for the UT-02 overlap (or similar; exact district numbers depend on 119th Congress boundaries)

The `AREALAND_PART` field gives the land area of each intersection in square meters, enabling calculation of what percentage of the reservation lies in each district.

### Alaska at-Large

Alaska has a single at-large congressional district (CD code `0200` in the file, which maps to `AK-AL`). The file lists each Alaska Native Village Statistical Area (ANVSA, CLASSFP = E1) as a separate row. There are approximately **229 ANVSA entities** in Alaska.

All Alaska entries share the same district (`AK-AL`), but each ANVSA is a distinct row. When building the Tribe-to-district mapping:
- Each Alaska Native Tribe/village maps to `AK-AL`
- Senator deduplication: both Alaska senators serve all 229 entities
- The mapping is trivial for Alaska but the **AIANNH-to-Tribe linkage** requires the EPA Tribes Names Service or BIA list to connect each ANVSA to its federally recognized Tribe name

### Oklahoma Tribal Statistical Areas (OTSAs)

Oklahoma Tribes often lack formal reservations (due to the ANCSA-equivalent history). Instead, they have OTSAs (CLASSFP = D6). These are statistical areas, not legal boundaries, but they represent the jurisdictional areas of Oklahoma Tribes. The Census file includes OTSAs with their CD119 intersections.

### Tribes Without Geographic Areas in Census Data

**Key gap:** Not all 575 federally recognized Tribes have geographic boundaries in the Census AIANNH file. Some Tribes:
- Have no reservation or trust land
- Have trust land too small to appear in Census data
- Were recently recognized and not yet in Census geographic files

For these Tribes, the **CRS Workbook's "Tribal Government Offices" category** (added August 2025) provides the headquarters location as a point, which can be geocoded to a congressional district. The BIA Tribal Leaders Directory also provides office locations.

**Estimated coverage:** The Census AIANNH file covers the geographic areas of approximately **620+ AIANNH entities** (including ANVSAs, OTSAs, reservations, trust lands). This exceeds the 575 Tribe count because some Tribes have multiple geographic entities (reservation + ORTL) and some entities are joint-use areas.

## Mapping AIANNH Entities to Federally Recognized Tribes

### The Core Challenge

Census AIANNH entities are **geographic areas**, not Tribes. The relationship is:
- **One Tribe** may have **multiple AIANNH entities** (reservation + separate trust land parcels)
- **Some AIANNH entities** span **multiple Tribes** (joint-use areas)
- The AIANNH `NAMELSAD` field often differs from the BIA/EPA Tribe name

Examples:
- Census: "Navajo Nation Reservation and Off-Reservation Trust Land" -> BIA: "Navajo Nation"
- Census: "Cherokee OTSA" -> BIA: "Cherokee Nation"
- Census: "Poarch Creek Reservation" -> BIA: "Poarch Band of Creek Indians"

### Recommended Linkage Approach

1. **EPA Tribes Names Service** provides BIA codes, Tribe names, and (for some) Census AIANNH codes. Use as primary crosswalk.
2. **Name matching** between Census `NAMELSAD_AIANNH_20` and EPA/BIA Tribe names, using substring matching and a curated alias table for known mismatches.
3. **Manual curation** for the ~10-20 Tribes where automated matching fails. Store in a static mapping file.

### Data Model for the Full Crosswalk

```python
# Final output structure for congressional_cache.json
{
    "metadata": {
        "congress": 119,
        "source": "Census CD119-AIANNH Relationship File (2024-10-24)",
        "tribe_count": 575,
        "generated": "2026-XX-XX"
    },
    "tribe_district_map": {
        "navajo_nation": {
            "tribe_name": "Navajo Nation",
            "bia_code": "NN",
            "aiannh_geoids": ["2430"],
            "districts": [
                {"district": "AZ-02", "state": "AZ", "overlap_pct": 45.2},
                {"district": "AZ-01", "state": "AZ", "overlap_pct": 12.3},
                {"district": "NM-02", "state": "NM", "overlap_pct": 38.1},
                {"district": "UT-02", "state": "UT", "overlap_pct": 4.4}
            ],
            "states": ["AZ", "NM", "UT"]
        },
        "akiak_native_community": {
            "tribe_name": "Akiak Native Community",
            "bia_code": "...",
            "aiannh_geoids": ["0070"],
            "districts": [
                {"district": "AK-AL", "state": "AK", "overlap_pct": 100.0}
            ],
            "states": ["AK"]
        }
    }
}
```

## Alternative Data Sources

### 1. Census TIGER AIANNH Shapefiles + CD119 Shapefiles (GIS approach)

| Attribute | Value |
|-----------|-------|
| AIANNH Shapefile | https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html (2025 release, Sep 2025) |
| CD119 Shapefile | Same site, select "119th Congressional Districts" |
| Approach | Load both in geopandas, use `gpd.overlay()` or `gpd.sjoin()` for spatial intersection |
| Pros | Full geometric detail, enables area-based overlap percentages, supports map generation (Phase 7) |
| Cons | Heavy dependencies (geopandas, shapely, fiona), slower, overkill for just the crosswalk |
| Verdict | **Not needed for the crosswalk** (Census relationship file already computes the intersections). Needed later for **map image generation** in Phase 7 DOCX packets. |

### 2. CRS Congressional District Geography Workbook (Excel)

| Attribute | Value |
|-----------|-------|
| URL | https://www.crs.gov/Products/Documents/CDGW_119CD/xlsm/ |
| Format | Excel (.xlsm) with 5 worksheets, ~532K rows |
| Access | Restricted to CRS.gov users (congressional staff) |
| Content | 45 geographic categories including Native American Areas and Tribal Government Offices |
| Verdict | **Cannot use** -- restricted access. The underlying Census data it draws from is publicly available in the relationship files. |

### 3. BIA Geographic Data

| Attribute | Value |
|-----------|-------|
| Source | BIA TGIS (Tribal GIS) |
| Format | Shapefiles, inconsistent availability |
| Coverage | Boundaries for BIA-managed lands |
| Verdict | **Supplementary** -- BIA data is authoritative for boundaries but not available as a CD crosswalk. Census TIGER derives from BIA boundaries anyway. |

### 4. NHGIS Geographic Crosswalks

| Attribute | Value |
|-----------|-------|
| URL | https://www.nhgis.org/geographic-crosswalks |
| Format | CSV in ZIP archives |
| Content | Crosswalks between various Census geographies |
| Verdict | **Supplementary** -- may have AIANNH-to-CD crosswalks but the Census relationship file is more authoritative and direct. |

## Recommendations

### Primary Data Source: Census CD119-AIANNH Relationship File

**Use:** `tab20_cd11920_aiannh20_natl.txt` from the Census Bureau

**Why:**
1. Machine-readable (pipe-delimited CSV, trivial to parse)
2. Covers the **119th Congress** (current)
3. Official Census Bureau data (same source R48107 uses)
4. Includes area measurements for overlap percentage calculation
5. Covers all AIANNH entity types (reservations, trust lands, ANVSAs, OTSAs)
6. Publicly available, no access restrictions
7. Small file (178KB), no heavy GIS dependencies needed

**Download and store at:** `data/census/tab20_cd11920_aiannh20_natl.txt`

### Build Pipeline

1. **Download** the Census relationship file (one-time, store in `data/census/`)
2. **Parse** using Python's `csv` module with `delimiter="|"`
3. **Filter** by CLASSFP to include only federally recognized entities (D1, D2, D3, D5, D8, D6, E1)
4. **Transform** GEOID_CD119_20 into state abbreviation + district format ("AZ-02")
5. **Group** by AIANNH GEOID to get per-Tribe district lists
6. **Link** AIANNH GEOIDs to Tribe IDs using EPA Tribes Names Service data (Team 1's output)
7. **Handle gaps** for Tribes without Census geographic areas using BIA office geocoding
8. **Store** result in `congressional_cache.json` as the authoritative crosswalk

### Do NOT Use R48107 PDF Extraction

The R48107 PDF is:
- For the **wrong Congress** (118th, not 119th)
- Hard to parse reliably (PDF tables across 27 tables, varying formats)
- Missing area overlap data (just says "yes/no" not percentage)
- Superseded by the Census relationship file it was derived from

### PDF Extraction Libraries (If Ever Needed)

If a future version of R48107 for the 119th Congress is published and there's a need to extract its tables:

| Library | Version | Strengths | For CRS Reports |
|---------|---------|-----------|-----------------|
| **pdfplumber** | 0.11+ | Best for complex table layouts, visual debugging | **Recommended** -- CRS reports have bordered tables |
| camelot-py | 1.0.9 | Best for simple lattice tables | Good alternative |
| tabula-py | 2.9+ | Easy API, multi-page support | Requires Java (JRE dependency) |

**pdfplumber** is recommended because CRS report tables have clear bordered cells (lattice layout), and pdfplumber handles multi-page tables and irregular cell sizes well. However, **this should not be needed** given the Census alternative.

## Confidence Level

| Area | Confidence | Reasoning |
|------|------------|-----------|
| Census CD119-AIANNH file existence and format | **HIGH** | File verified, first rows examined, columns documented |
| Census file covers 119th Congress | **HIGH** | File name includes "cd119", dated 2024-10-24, Census documentation confirms |
| CLASSFP codes for filtering | **HIGH** | Verified against Census technical documentation |
| AIANNH-to-Tribe linkage challenge | **HIGH** | Well-documented Census vs BIA naming discrepancy |
| R48107 covers 118th Congress only | **HIGH** | Confirmed from report title and all versions |
| IR10001 (119th Congress CRS report) | **LOW** | Referenced in CRS Workbook docs but could not access or verify contents |
| CRS Workbook access restriction | **MEDIUM** | Download URL exists at crs.gov but may require congressional credentials |
| Coverage of all 575 Tribes | **MEDIUM** | Census has 620+ AIANNH entities but some Tribes may lack geographic representation |

## Open Questions

1. **AIANNH-to-Tribe mapping completeness:** How many of the 575 federally recognized Tribes have Census AIANNH geographic entities? What is the exact gap? Team 1 (EPA Tribes Names Service) should investigate whether EPA data includes Census AIANNH codes for each Tribe.

2. **Lumbee Tribe coverage:** The Lumbee Tribe was recently federally recognized via FY2026 NDAA. Is it in the Census AIANNH file? If not, its office location in Pembroke, NC can be geocoded to a district.

3. **CRS IR10001 availability:** The CRS Congressional District Geography Workbook references "CRS Report IR10001, Tribal and Other Indigenous Lands in the 119th Congress." This report may contain a 119th-Congress version of R48107's tables. Could not locate or access it. Low priority since the Census file is sufficient.

4. **Oklahoma OTSA-to-Tribe mapping:** Oklahoma has ~38 OTSAs. Do OTSA names reliably map to Tribe names? (Likely yes with string matching -- "Cherokee OTSA" -> "Cherokee Nation" -- but needs verification.)

5. **Joint-use areas:** Some AIANNH entities are administered by multiple Tribes. How to handle? Recommendation: create one mapping entry per Tribe that administers the area.

6. **Map generation data:** Phase 7 DOCX packets need district map images. The Census TIGER shapefiles (both AIANNH and CD119) will be needed then, but the crosswalk for Phase 5 does not require them.

## Sources

### Primary (HIGH confidence)
- Census CD119-AIANNH Relationship File: https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_aiannh20_natl.txt (verified, first rows examined)
- Census Relationship Files directory: https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/ (52 state files + national file verified)
- Census AIANNH Relationship File example (format verification): https://www2.census.gov/geo/docs/maps-data/data/rel2020/aiannh/tab20_aiannh20_cousub20_natl.txt
- CRS R48107 Product Page: https://www.congress.gov/crs-product/R48107
- CRS R48107 PDF (Sep 2024): https://www.congress.gov/crs_external_products/R/PDF/R48107/R48107.6.pdf
- Census Class Codes Reference: https://www2.census.gov/geo/pdfs/reference/ClassCodes.pdf

### Secondary (MEDIUM confidence)
- CRS Congressional District Geography Workbook (IN12489): https://www.congress.gov/crs-product/IN12489
- EveryCRSReport R48107 summary: https://www.everycrsreport.com/reports/R48107.html
- EveryCRSReport IN12489 (Workbook): https://www.everycrsreport.com/reports/IN12489.html
- Census TIGER/Line Shapefiles: https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html
- Census Relationship Files landing page: https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html
- Census AIANNH Record Layout: https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/2020-aiannh-record-layout.html

### Tertiary (LOW confidence)
- CRS IR10001 reference (mentioned in Workbook docs, not directly accessed)
- pdfplumber capabilities: https://github.com/jsvine/pdfplumber
- Best PDF extraction libraries comparison: https://unstract.com/blog/extract-tables-from-pdf-python/
