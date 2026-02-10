# Phase 6: Data Acquisition - Research

**Researched:** 2026-02-10
**Domain:** USASpending API querying, fuzzy name matching, FEMA NRI hazard data, USFS wildfire risk data
**Confidence:** MEDIUM (HIGH for API structure and libraries, MEDIUM for NRI tribal data specifics, LOW for USFS tribal CSV format)

## Summary

Phase 6 requires building four data acquisition capabilities: (1) batch Tribal award queries against USASpending.gov API, (2) two-tier Tribal name matching to attribute awards to the correct Tribe, (3) FEMA National Risk Index hazard profile ingestion, and (4) USFS Wildfire Risk to Communities data integration. All results are cached as per-Tribe JSON files for zero-API-call DOCX generation in Phase 7.

The USASpending.gov API v2 provides a free, no-key REST API with a `spending_by_award` POST endpoint that supports both `program_numbers` (CFDA) and `recipient_type_names` filters with page-based pagination. The project has 12 unique CFDAs across 11 tracked programs (not 16 as mentioned in some earlier specs). The batch strategy is one API call per CFDA with `recipient_type_names: ["indian_native_american_tribal_government"]` filter, paginating through all results -- yielding 12 base calls plus pagination follow-ups.

For name matching, rapidfuzz (already in requirements.txt at >=3.14.0) provides `token_sort_ratio` as specified in the requirement (>= 85 threshold). The existing TribalRegistry already uses `WRatio` for its tier-3 fuzzy matching, but AWARD-02 needs a separate, stricter matching pipeline with `token_sort_ratio` (as specified) plus state-overlap validation. The curated alias table serves as the primary lookup (exact match), with rapidfuzz as fallback only.

FEMA NRI v1.20 (December 2025) provides county and census tract data with 18 hazard types, 1,061+ fields. Tribal-specific data comes via "Tribal Relational Database" CSVs that map AIANNH areas to NRI counties/tracts. USFS Wildfire Risk to Communities provides a downloadable XLSX with risk metrics for tribal areas.

**Primary recommendation:** Build a `TribalAwardMatcher` class (curated alias dict + rapidfuzz token_sort_ratio >= 85 + state overlap) and a `HazardProfileBuilder` class (NRI CSV parser + USFS XLSX parser), both feeding per-Tribe JSON cache files. Modify the existing `USASpendingScraper` to support batch Tribal queries with full pagination.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | >=3.9.0 | Async HTTP for USASpending API calls | Already in project; BaseScraper uses it |
| rapidfuzz | >=3.14.0 | Fuzzy string matching for Tribal name attribution | Already in project; requirement specifies token_sort_ratio |
| openpyxl | >=3.1.0 | Read USFS Wildfire Risk XLSX file | Standard Python XLSX reader; needed for wrc_download_202505.xlsx |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| csv (stdlib) | N/A | Parse NRI CSV data | FEMA NRI data comes as CSV |
| json (stdlib) | N/A | Read/write per-Tribe cache files | All cache files are JSON |
| pathlib (stdlib) | N/A | File path management | Cache directory structure |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl | pandas | Heavier dependency; overkill for reading one sheet of a single XLSX |
| csv stdlib | pandas | Same -- pandas would add ~100MB dependency for simple CSV parsing |
| aiohttp | httpx | Would require changing BaseScraper; not worth the churn |

**Installation:**
```bash
pip install openpyxl>=3.1.0
```

Note: aiohttp and rapidfuzz are already in requirements.txt. Only openpyxl is new.

## Architecture Patterns

### Recommended Project Structure
```
src/
  packets/
    awards.py          # TribalAwardMatcher + batch query logic (AWARD-01, AWARD-02)
    hazards.py         # HazardProfileBuilder (HAZ-01, HAZ-02)
    orchestrator.py    # Updated to call awards + hazards during prep
  scrapers/
    usaspending.py     # Modified: add batch Tribal query method (reuses BaseScraper)
data/
  tribal_aliases.json  # Curated alias table: USASpending name -> tribe_id
  nri/                 # Pre-downloaded FEMA NRI CSV files
    NRI_Table_Counties.csv
    NRI_Tribal_Counties_Relational.csv  # Or similar tribal relational file
  usfs/
    wrc_download_202505.xlsx            # Pre-downloaded USFS wildfire data
  award_cache/         # Per-Tribe award cache (auto-generated)
    {tribe_id}.json
  hazard_profiles/     # Per-Tribe hazard cache (auto-generated)
    {tribe_id}.json
```

### Pattern 1: Batch Query with Full Pagination
**What:** Query USASpending once per CFDA with Tribal recipient filter, paginate through ALL results.
**When to use:** AWARD-01 -- fetching all Tribal awards per program.
**Example:**
```python
# Source: USASpending API contract (GitHub)
async def fetch_tribal_awards_for_cfda(
    self, session: aiohttp.ClientSession, cfda: str
) -> list[dict]:
    """Fetch ALL Tribal awards for a single CFDA with full pagination."""
    all_results = []
    page = 1
    limit = 100  # Max practical page size

    while True:
        payload = {
            "filters": {
                "award_type_codes": ["02", "03", "04", "05"],  # Grants
                "program_numbers": [cfda],
                "recipient_type_names": ["indian_native_american_tribal_government"],
            },
            "fields": [
                "Award ID", "Recipient Name", "Award Amount",
                "Total Obligation", "Awarding Agency", "Start Date",
                "End Date", "recipient_id", "Description",
                "CFDA Number",
            ],
            "subawards": False,
            "page": page,
            "limit": limit,
            "sort": "Award Amount",
            "order": "desc",
        }
        url = f"{self.base_url}/search/spending_by_award/"
        data = await self._request_with_retry(session, "POST", url, json=payload)

        results = data.get("results", [])
        all_results.extend(results)

        has_next = data.get("page_metadata", {}).get("hasNext", False)
        if not has_next or not results:
            break
        page += 1

    return all_results
```

### Pattern 2: Two-Tier Name Matching with State Validation
**What:** Curated alias table as primary lookup (O(1) dict), rapidfuzz token_sort_ratio as fallback with state-overlap guard.
**When to use:** AWARD-02 -- attributing USASpending recipient names to registry Tribes.
**Example:**
```python
# Source: project requirements + rapidfuzz docs
from rapidfuzz import fuzz

def match_recipient_to_tribe(
    self,
    recipient_name: str,
    recipient_state: str | None = None,
) -> dict | None:
    """Match a USASpending recipient name to a registry Tribe.

    Tier 1: Curated alias table (exact lookup, O(1))
    Tier 2: rapidfuzz token_sort_ratio >= 85 with state overlap validation

    Returns None (skip) when no confident match -- false negatives preferred.
    """
    normalized = recipient_name.strip().lower()

    # Tier 1: Curated alias table
    tribe_id = self.alias_table.get(normalized)
    if tribe_id:
        return self.registry.get_by_id(tribe_id)

    # Tier 2: Fuzzy matching with state validation
    best_match = None
    best_score = 0

    for tribe in self.registry.get_all():
        # Check all name variants
        names_to_check = [tribe["name"]] + tribe.get("alternate_names", [])
        for name in names_to_check:
            score = fuzz.token_sort_ratio(
                normalized, name.lower()
            )
            if score >= 85 and score > best_score:
                # State overlap validation
                if recipient_state and tribe.get("states"):
                    if recipient_state not in tribe["states"]:
                        continue  # State mismatch -- skip
                best_match = tribe
                best_score = score

    return best_match  # None if nothing >= 85 with state match
```

### Pattern 3: Pre-Downloaded Data Ingestion
**What:** Parse pre-downloaded CSV/XLSX files into per-Tribe JSON cache.
**When to use:** HAZ-01 (NRI CSV) and HAZ-02 (USFS XLSX).
**Example:**
```python
# Source: stdlib csv + project patterns
import csv
from pathlib import Path

def ingest_nri_tribal_data(nri_csv_path: Path) -> dict[str, dict]:
    """Parse NRI tribal relational CSV into per-area hazard profiles.

    Returns dict keyed by geographic identifier (e.g., STCOFIPS).
    """
    profiles = {}
    with open(nri_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            area_id = row.get("STCOFIPS") or row.get("NRI_ID", "")
            profiles[area_id] = {
                "risk_score": float(row.get("RISK_SCORE", 0)),
                "risk_rating": row.get("RISK_RATNG", ""),
                "eal_total": float(row.get("EAL_VALT", 0)),
                "eal_score": float(row.get("EAL_SCORE", 0)),
                "sovi_score": float(row.get("SOVI_SCORE", 0)),
                "sovi_rating": row.get("SOVI_RATNG", ""),
                "resl_score": float(row.get("RESL_SCORE", 0)),
                "resl_rating": row.get("RESL_RATNG", ""),
                "hazards": _extract_per_hazard_metrics(row),
            }
    return profiles
```

### Pattern 4: Per-Tribe Cache File with Empty-Award Advocacy Context
**What:** Every Tribe gets a cache file, even with zero awards. Zero-award files include advocacy framing.
**When to use:** Cache write step after award matching.
**Example:**
```python
# Source: project CONTEXT.md decisions
def write_award_cache(tribe_id: str, awards: list[dict], cache_dir: Path) -> None:
    """Write per-Tribe award cache. Zero awards get advocacy context."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_data = {
        "tribe_id": tribe_id,
        "awards": awards,
        "total_obligation": sum(a.get("obligation", 0) for a in awards),
        "cfda_summary": _summarize_by_cfda(awards),
    }

    if not awards:
        cache_data["no_awards_context"] = (
            "No federal climate resilience awards found in tracked programs. "
            "This represents a first-time applicant opportunity -- "
            "the Tribe can leverage this status to demonstrate unmet need "
            "in competitive grant applications."
        )

    cache_path = cache_dir / f"{tribe_id}.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)
```

### Anti-Patterns to Avoid
- **Per-Tribe API calls:** NEVER query USASpending 592 times (once per Tribe). Query once per CFDA (12 calls), then match results to Tribes locally. The batch approach reduces 9,472 potential calls to 12.
- **Trusting fuzzy matches without state validation:** A high token_sort_ratio score alone is insufficient. "Choctaw Nation of Oklahoma" and "Mississippi Band of Choctaw Indians" will score high against each other. State overlap is the critical guard.
- **Storing confidence metadata in cache:** Decision from CONTEXT.md -- if it passes threshold, treat as authoritative. No "verified" vs "approximate" distinction.
- **Using WRatio for award matching:** The requirement specifies `token_sort_ratio` for AWARD-02. WRatio is used by the existing registry (Tier 3) for interactive name resolution, but award matching needs the stricter, more predictable token_sort_ratio.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom edit-distance algorithm | rapidfuzz `fuzz.token_sort_ratio` | Handles word reordering; C-optimized; 100x faster than pure Python |
| CSV parsing | Custom line splitting | `csv.DictReader` (stdlib) | Handles quoting, escaping, Unicode; NRI CSV has 1000+ columns |
| XLSX reading | Custom XML parsing | openpyxl | XLSX is a complex ZIP+XML format; openpyxl handles all edge cases |
| HTTP retry logic | Custom retry loop | BaseScraper._request_with_retry | Already exists with exponential backoff, 429 handling, rate limiting |
| Pagination | Manual offset math | USASpending page_metadata.hasNext | API provides next-page indicator; just check the boolean |
| Name normalization | Custom lowercasing/stripping | rapidfuzz `utils.default_process` | Strips non-alphanumeric, lowercases, handles Unicode normalization |

**Key insight:** The hard problem here is not the plumbing (HTTP calls, file I/O) -- it is the name matching accuracy. rapidfuzz provides the fuzzy matching, but the curated alias table and state-overlap validation are where the real data quality protection lives. Those must be hand-built because they encode domain knowledge about Tribal naming patterns.

## Common Pitfalls

### Pitfall 1: False Positive Award Attribution
**What goes wrong:** Award from "Choctaw Nation of Oklahoma" gets attributed to "Mississippi Band of Choctaw Indians" because both contain "Choctaw" and score well on fuzzy matching.
**Why it happens:** Many Tribal names share root words (Choctaw, Sioux, Paiute, Shoshone, etc.). Without state-overlap validation, fuzzy matching produces dangerous false positives.
**How to avoid:**
1. Curated alias table catches known variants (primary defense)
2. `token_sort_ratio >= 85` threshold is strict enough to reject partial matches
3. State-overlap validation ensures the matched Tribe and the award recipient share at least one state
4. When in doubt, skip the match (false negatives preferred per CONTEXT.md)
**Warning signs:** Multiple Tribes claiming the same award; Tribes with awards in states where they have no land.

### Pitfall 2: USASpending Pagination Truncation
**What goes wrong:** Only first page (10-100 results) retrieved, missing the tail of awards for popular CFDAs.
**Why it happens:** Default limit is 10. The existing scraper uses `"limit": 10` and never paginates.
**How to avoid:** Set limit to 100 (or higher), check `page_metadata.hasNext`, loop until false.
**Warning signs:** Every CFDA returning exactly `limit` number of results.

### Pitfall 3: USASpending Recipient Name Inconsistency
**What goes wrong:** Same Tribe appears under multiple names in USASpending (e.g., "NAVAJO NATION", "Navajo Nation", "THE NAVAJO NATION", "Navajo Nation - Window Rock, AZ").
**Why it happens:** USASpending aggregates from SAM.gov registrations; Tribes may register multiple entities or change names.
**How to avoid:** Normalize to lowercase, trim whitespace, use token_sort_ratio (word-order invariant). The curated alias table should map known USASpending variants.
**Warning signs:** Same Tribe matching under different names; duplicate awards in cache.

### Pitfall 4: NRI Tribal Data Is Relational, Not Direct
**What goes wrong:** Attempting to find a "tribal" row directly in the NRI county or tract CSV.
**Why it happens:** NRI does not have tribal areas as a primary geographic unit. Instead, FEMA provides separate "Tribal Relational Database" files that map AIANNH boundaries to the counties/tracts that overlap with them.
**How to avoid:** Download the tribal relational CSV separately, join it with the county/tract data, then aggregate risk scores for each Tribal area.
**Warning signs:** No tribal rows found in the main NRI CSV; trying to search by Tribe name in county data.

### Pitfall 5: CFDA Count Mismatch
**What goes wrong:** Code assumes 16 CFDAs (from an earlier spec version) but only 12 exist in program_inventory.json.
**Why it happens:** The requirement description mentions "16 CFDAs" but program_inventory.json has exactly 12 unique CFDA values across 11 programs (fema_bric has 2: 97.047 and 97.039). Five programs have null CFDA.
**How to avoid:** Read CFDAs dynamically from program_inventory.json, not from a hardcoded constant. The existing CFDA_TO_PROGRAM in usaspending.py has 12 entries matching the inventory.
**Warning signs:** Hardcoded CFDA lists that don't match the inventory; missing programs in batch queries.

### Pitfall 6: Windows File Encoding
**What goes wrong:** CSV/JSON files written without explicit `encoding="utf-8"` default to locale encoding on Windows, corrupting Tribal names with diacritics or special characters.
**Why it happens:** Python's `open()` uses locale encoding by default on Windows.
**How to avoid:** Always pass `encoding="utf-8"` to `open()`, `Path.write_text()`, and `json.dump()` calls.
**Warning signs:** Mojibake in Tribal names; test failures on Windows but not Linux.

### Pitfall 7: Award Amounts for Multiplier Math
**What goes wrong:** Cache stores formatted strings ("$1,234,567") instead of numeric values, breaking Phase 7 economic multiplier calculations.
**Why it happens:** USASpending returns mixed types; careless normalization preserves string formatting.
**How to avoid:** Always convert `Award Amount` and `Total Obligation` to float at ingestion time. Cache numeric values, not formatted strings.
**Warning signs:** TypeError in Phase 7 when trying to multiply award amounts.

## Code Examples

### USASpending Batch Query Structure (AWARD-01)
```python
# Source: USASpending API GitHub contract + existing BaseScraper pattern
async def fetch_all_tribal_awards(self) -> dict[str, list[dict]]:
    """Fetch all Tribal awards across all tracked CFDAs.

    Returns dict keyed by CFDA number, values are lists of award dicts.
    12 API calls (one per CFDA) + pagination follow-ups.
    """
    all_awards: dict[str, list[dict]] = {}

    async with self._create_session() as session:
        for cfda in self.tracked_cfdas:
            try:
                awards = await self._fetch_tribal_awards_paginated(
                    session, cfda
                )
                all_awards[cfda] = awards
                logger.info(
                    "CFDA %s: fetched %d Tribal awards", cfda, len(awards)
                )
            except Exception:
                logger.exception("Error fetching Tribal awards for CFDA %s", cfda)
                all_awards[cfda] = []

            await asyncio.sleep(0.5)  # Rate limiting courtesy

    return all_awards
```

### Alias Table Structure (AWARD-02)
```json
{
  "_metadata": {
    "description": "Curated mapping: USASpending recipient name (lowercased) -> tribe_id",
    "version": "1.0",
    "entries": 50,
    "last_updated": "2026-02-10"
  },
  "aliases": {
    "navajo nation": "epa_100000306",
    "the navajo nation": "epa_100000306",
    "navajo nation - window rock az": "epa_100000306",
    "cherokee nation": "epa_100000064",
    "cherokee nation of oklahoma": "epa_100000064",
    "muscogee (creek) nation": "epa_100000299",
    "muscogee creek nation": "epa_100000299"
  }
}
```

### NRI Hazard Type Field Naming (HAZ-01)
```python
# Source: ArcGIS FeatureServer field listing for NRI Counties (verified)
# 18 hazard types with standard abbreviation prefixes:
NRI_HAZARD_CODES = {
    "AVLN": "Avalanche",
    "CFLD": "Coastal Flooding",
    "CWAV": "Cold Wave",
    "DRGT": "Drought",
    "ERQK": "Earthquake",
    "HAIL": "Hail",
    "HWAV": "Heat Wave",
    "HRCN": "Hurricane",
    "ISTM": "Ice Storm",
    "IFLD": "Inland Flooding",     # Note: some docs say "Riverine Flooding"
    "LNDS": "Landslide",
    "LTNG": "Lightning",
    "SWND": "Strong Wind",
    "TRND": "Tornado",
    "TSUN": "Tsunami",
    "VLCN": "Volcanic Activity",
    "WFIR": "Wildfire",
    "WNTW": "Winter Weather",
}

# Per-hazard field suffixes (append to hazard code):
# _EVNTS  = Number of Events
# _AFREQ  = Annualized Frequency
# _EALT   = Expected Annual Loss: Total ($)
# _EALS   = Expected Annual Loss: Score (0-100)
# _EALR   = Expected Annual Loss: Rating (text)
# _RISKS  = Risk Index Score (0-100)
# _RISKR  = Risk Index Rating (text)
# _RISKV  = Risk Index Value

# Composite fields (no hazard prefix):
# RISK_SCORE, RISK_RATNG, RISK_VALUE
# EAL_SCORE, EAL_RATNG, EAL_VALT
# SOVI_SCORE, SOVI_RATNG
# RESL_SCORE, RESL_RATNG, RESL_VALUE
```

### Per-Tribe Hazard Profile Cache Schema (HAZ-01 + HAZ-02)
```python
# Recommended cache file schema for data/hazard_profiles/{tribe_id}.json
hazard_profile = {
    "tribe_id": "epa_100000306",
    "tribe_name": "Navajo Nation",
    "sources": {
        "fema_nri": {
            "version": "1.20",
            "composite": {
                "risk_score": 45.2,
                "risk_rating": "Relatively Moderate",
                "eal_total": 12345678.90,
                "eal_score": 52.1,
                "sovi_score": 67.3,
                "sovi_rating": "Relatively High",
                "resl_score": 28.4,
                "resl_rating": "Relatively Low",
            },
            "top_hazards": [
                {
                    "type": "Wildfire",
                    "code": "WFIR",
                    "risk_score": 78.5,
                    "risk_rating": "Relatively High",
                    "eal_total": 5678901.23,
                },
                {
                    "type": "Drought",
                    "code": "DRGT",
                    "risk_score": 65.2,
                    "risk_rating": "Relatively Moderate",
                    "eal_total": 3456789.01,
                },
            ],
            "all_hazards": {
                "WFIR": {"risk_score": 78.5, "eal_total": 5678901.23},
                "DRGT": {"risk_score": 65.2, "eal_total": 3456789.01},
                # ... all 18 hazards
            },
        },
        "usfs_wildfire": {
            "risk_to_homes": 0.85,
            "wildfire_likelihood": "High",
            # Additional USFS metrics
        },
    },
    "generated_at": "2026-02-10T12:00:00+00:00",
}
```

### USASpending API recipient_type_names Values (AWARD-01)
```python
# Source: usaspending-website GitHub (recipientType.js) - VERIFIED
# Key Tribal-related values for the recipient_type_names filter:
TRIBAL_RECIPIENT_TYPES = [
    "indian_native_american_tribal_government",  # Primary: Tribal governments
    # Other potentially relevant types (use if broadening search):
    # "tribally_owned_firm",
    # "american_indian_owned_business",
    # "native_american_owned_business",
    # "alaskan_native_corporation_owned_firm",
    # "native_hawaiian_organization_owned_firm",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-Tribe USASpending queries (592 x 12 = 7,104 calls) | Batch per-CFDA with Tribal filter (12 calls + pagination) | Phase 6 design | 99.8% fewer API calls |
| Top-10 results per CFDA (existing scraper) | Full pagination through all results | Phase 6 AWARD-01 | Captures all Tribal awards, not just largest 10 |
| fuzz.WRatio score_cutoff=60 (existing registry) | fuzz.token_sort_ratio score_cutoff=85 + state validation | Phase 6 AWARD-02 | Much stricter matching; prevents cross-Tribe false positives |
| NRI hazards.fema.gov interactive tool | Pre-downloaded CSV + local parsing | Phase 6 HAZ-01 | Offline access; batch processing for 592 Tribes |

**Deprecated/outdated:**
- NRI URLs at `hazards.fema.gov/nri/` now redirect to `www.fema.gov/emergency-managers/practitioners/resilience-analysis-and-planning-tool` (RAPT). Data downloads should go through `www.fema.gov/about/openfema/data-sets/national-risk-index-data`
- USASpending API v1 endpoints are deprecated; v2 is current

## USASpending API Key Details

**Base URL:** `https://api.usaspending.gov/api/v2` (already configured in scanner_config.json)
**No API key required** (confirmed in config: `"requires_key": false`)

**Request structure for spending_by_award:**
- Method: POST
- Content-Type: application/json
- Page-based pagination: `page` (int), `limit` (int, default 10)
- Response: `results` array + `page_metadata.hasNext` boolean

**Key filter: `recipient_type_names`**
- Exact value for Tribal governments: `"indian_native_american_tribal_government"`
- This is verified from the USASpending website source code (recipientType.js)

**Key filter: `program_numbers`**
- Takes CFDA/Assistance Listing numbers as strings: e.g., `["15.156"]`
- Already used by existing scraper

**Available response fields for assistance awards:**
- Award ID, Recipient Name, Award Amount, Total Obligation
- Start Date, End Date, Description
- CFDA Number, primary_assistance_listing
- Awarding Agency, recipient_id

**Rate limiting:** No documented rate limit, but 429 responses are possible. The existing BaseScraper already handles 429 with Retry-After header respect.

## NRI Data Structure Details

**Current version:** v1.20 (December 2025)
**Total fields per record:** 1,061+ (18 hazards x ~55 metrics each + composite fields)
**Download:** www.fema.gov/about/openfema/data-sets/national-risk-index-data

**Rating scale (5 categories):**
- Very Low, Relatively Low, Relatively Moderate, Relatively High, Very High

**Tribal data approach:**
- NRI does NOT have Tribal areas as a primary geographic unit
- FEMA provides "Tribal County Relational Database" and "Tribal Census Tract Relational Database" as separate downloads
- These relational files map AIANNH (American Indian/Alaska Native/Native Hawaiian) boundaries to overlapping NRI counties/tracts
- Implementation must: (1) load relational mapping, (2) look up corresponding county/tract NRI data, (3) aggregate (area-weighted or max) to produce per-Tribe profiles
- The project already has `aiannh_tribe_crosswalk.json` (214 auto-matched + 7 fuzzy + 27 unmatched) which maps Census AIANNH GEOIDs to EPA tribe_ids

## USFS Wildfire Risk Data Details

**Download:** https://wildfirerisk.org/wp-content/uploads/2025/05/wrc_download_202505.xlsx
**Format:** XLSX (openpyxl needed to read)
**Coverage:** 600+ tribal areas across all 50 states

**Key metrics (expected based on documentation):**
- Risk to Homes (housing unit risk)
- Wildfire Likelihood (burn probability)
- Risk Reduction Zones
- Housing Unit Impact (HUImpact)

**Note:** The exact column structure of the XLSX could not be verified without downloading and parsing the actual file. The planner should include a task to download the file and inspect its schema before building the parser.

## Open Questions

1. **NRI Tribal Relational CSV exact format**
   - What we know: FEMA provides "Tribal County Relational Database" and "Tribal Census Tract Relational Database" as separate CSV downloads
   - What's unclear: The exact column names, how AIANNH GEOIDs map to NRI_IDs, and whether area-weighted aggregation is needed
   - Recommendation: First task should download the tribal relational CSV and inspect its schema. The existing `aiannh_tribe_crosswalk.json` (from Phase 5) provides Census GEOID to EPA tribe_id mapping that will bridge the gap

2. **USFS XLSX exact column names**
   - What we know: Contains risk metrics for 600+ tribal areas
   - What's unclear: Exact column headers for tribal area rows, geographic identifier used (AIANNH GEOID? Tribe name?)
   - Recommendation: Download and inspect the XLSX as a first task; schema discovery before parser implementation

3. **USASpending Tribal award volume per CFDA**
   - What we know: 12 CFDAs will be queried, each potentially returning hundreds of results
   - What's unclear: How many total Tribal awards exist per CFDA (determines pagination depth)
   - Recommendation: Implement pagination defensively (no upper bound on pages); add logging for total counts per CFDA

4. **Alias table bootstrap strategy**
   - What we know: Curated alias table is the primary name matching defense (CONTEXT.md: Claude's discretion)
   - What's unclear: How to seed the initial alias table without first running the batch query
   - Recommendation: Bootstrap from registry alternate_names (already in tribal_registry.json) + known USASpending naming patterns. Refine after first batch run by logging unmatched recipients for manual review.

5. **NRI data for unmatched Tribes (27 from crosswalk)**
   - What we know: 27 AIANNH entities are unmatched in the existing crosswalk
   - What's unclear: Whether these 27 have no NRI data or just need manual matching
   - Recommendation: Log these as warnings; hazard profile will have null/missing NRI data for these Tribes

## Sources

### Primary (HIGH confidence)
- USASpending API contract (spending_by_award): https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
- USASpending recipient_type_names values: https://github.com/fedspendingtransparency/usaspending-website/blob/master/src/js/dataMapping/search/recipientType.js -- confirmed `indian_native_american_tribal_government`
- USASpending search_filters contract: https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/search_filters.md
- NRI Counties FeatureServer fields: https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0 -- all 1,061+ fields verified
- rapidfuzz docs (fuzz module): https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html
- Existing codebase: src/scrapers/usaspending.py, src/scrapers/base.py, src/packets/registry.py

### Secondary (MEDIUM confidence)
- FEMA NRI data downloads: https://www.fema.gov/about/openfema/data-sets/national-risk-index-data -- v1.20 confirmed, tribal relational databases confirmed available
- USFS Wildfire Risk to Communities: https://wildfirerisk.org/download/ -- tribal coverage confirmed, XLSX download link confirmed
- NRI hazard codes (18 types): Cross-verified from ArcGIS FeatureServer fields + multiple web sources

### Tertiary (LOW confidence)
- USFS XLSX exact column structure: Could not verify without downloading the actual 50MB+ file
- NRI Tribal Relational CSV exact columns: FEMA data dictionary redirects to new RAPT page; format inferred from county data structure
- USASpending API page size limits: No documented maximum for the `limit` parameter; 100 is a safe practical choice

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - aiohttp/rapidfuzz already in project; openpyxl is well-established
- USASpending API: HIGH - contract verified from GitHub source; recipient type values verified from website source
- NRI data structure: HIGH for field names (verified from ArcGIS FeatureServer); MEDIUM for tribal relational mapping specifics
- USFS data structure: LOW - format known (XLSX), metrics known, but exact column names unverified
- Name matching strategy: MEDIUM - rapidfuzz token_sort_ratio is well-documented; threshold tuning (85) is a requirement; state-overlap validation is sound but untested against real USASpending data
- Pitfalls: HIGH - based on domain knowledge of Tribal naming complexity + verified API behavior

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days; NRI data stable, USASpending API stable, USFS data updated ~annually)
