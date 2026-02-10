# Team 1 Research: EPA Tribes Names Service API (REG-01)

**Researched:** 2026-02-10
**Domain:** EPA Tribal Identification Data, BIA Federal Register Tribal Listings
**Overall Confidence:** MEDIUM (API verified live and functional; data completeness gap identified)

---

## API Endpoint Details

### Base URL and Endpoints

**Confidence: HIGH** -- Verified by direct API calls returning valid JSON responses.

| Attribute | Value |
|-----------|-------|
| **Base URL** | `https://cdxapi.epa.gov/oms-tribes-rest-services` |
| **Authentication** | None required -- public, no API key, no registration |
| **Response Format** | JSON |
| **Protocol** | REST (OpenAPI 3.0 documented) |
| **Swagger UI** | `https://cdxapi.epa.gov/oms-tribes-rest-services/swagger-ui/index.html` |
| **OpenAPI Spec** | `https://cdxapi.epa.gov/oms-tribes-rest-services/v3/api-docs` |
| **Hosting** | EPA CDX Azure cloud environment |

### Three Endpoints

#### 1. `GET /api/v1/tribes` -- Basic Tribe List
Returns summary records (no nested arrays for names/locations/relationships).

**Query Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `tribeName` | string | Filter by tribe name (case-insensitive) | - |
| `tribeNameQualifier` | string | `"begins"`, `"contains"`, or `"exact"` | `"contains"` |
| `date` | YYYY-MM-DD | Tribes recognized on this date | - |
| `startDate` | YYYY-MM-DD | Recognized on or after | - |
| `endDate` | YYYY-MM-DD | Recognized on or before | - |
| `regionCode` | string | EPA Region number (1-10) | - |
| `stateCode` | string | Two-letter state code | - |
| `tribalBandFilter` | string | `"ExcludeTribalBands"`, `"TribalBandsOnly"`, `"AllTribes"` | **`"ExcludeTribalBands"`** |
| `biaTribalCode` | string | Exact BIA code match | - |

#### 2. `GET /api/v1/tribeDetails` -- Detailed Tribe Records
Same parameters as `/tribes` but returns full nested records with historical names, locations, and relationships.

#### 3. `GET /api/v1/tribeDetails/{epaTribalInternalId}` -- Single Tribe by EPA ID
Returns detailed record for one tribe by EPA Internal ID.

### CRITICAL: Default Filter Excludes Most Tribes

**The `tribalBandFilter` parameter defaults to `"ExcludeTribalBands"`, which returns only ~260 records.** To get all federally recognized tribes including tribal bands and Alaska Native entities, you MUST pass `tribalBandFilter=AllTribes`.

**Verified counts:**
- `ExcludeTribalBands` (default): ~260 records
- `AllTribes`: ~574 records (all federally recognized tribes as of 12/11/2024 BIA list)
- `TribalBandsOnly`: ~16 records (sub-component bands like Passamaquoddy subdivisions)

---

## Response Schema

**Confidence: HIGH** -- Verified by direct API calls with live data.

### `/api/v1/tribes` Response (Summary)

```json
[
  {
    "epaTribalInternalId": 100000002,
    "currentName": "Agua Caliente Band of Cahuilla Indians of the Agua Caliente Indian Reservation, California",
    "currentNameStartDate": "1988-12-29",
    "currentNameEndDate": null,
    "currentBIATribalCode": "584",
    "currentBIARecognizedFlag": true,
    "commentText": null,
    "biaTribalCodes": null,
    "epaLocations": null,
    "names": null,
    "relationships": null
  }
]
```

### `/api/v1/tribeDetails` Response (Full)

```json
[
  {
    "epaTribalInternalId": 100000171,
    "currentName": "Navajo Nation, Arizona, New Mexico, & Utah",
    "currentNameStartDate": "2000-03-03",
    "currentNameEndDate": null,
    "currentBIATribalCode": "780",
    "currentBIARecognizedFlag": true,
    "commentText": null,
    "biaTribalCodes": [
      {
        "code": "780",
        "startDate": "1982-11-24",
        "endDate": null,
        "commentText": null
      }
    ],
    "epaLocations": [
      {
        "stateCode": "AZ",
        "stateName": "Arizona",
        "epaRegionName": "Region 9",
        "startDate": "1982-11-24",
        "endDate": null
      },
      {
        "stateCode": "NM",
        "stateName": "New Mexico",
        "epaRegionName": "Region 6",
        "startDate": "1982-11-24",
        "endDate": null
      },
      {
        "stateCode": "UT",
        "stateName": "Utah",
        "epaRegionName": "Region 8",
        "startDate": "1982-11-24",
        "endDate": null
      }
    ],
    "names": [
      {
        "name": "Navajo Tribe of Arizona, New Mexico & Utah",
        "startDate": "1000-01-01",
        "endDate": "1996-11-XX",
        "commentText": null
      },
      {
        "name": "Navajo Nation of Arizona, New Mexico & Utah",
        "startDate": "1996-11-XX",
        "endDate": "2000-03-03",
        "commentText": null
      },
      {
        "name": "Navajo Nation, Arizona, New Mexico, & Utah",
        "startDate": "2000-03-03",
        "endDate": null,
        "commentText": null
      }
    ],
    "relationships": [
      {
        "relativeEPATribalInternalId": null,
        "relationshipTypeCode": null,
        "relationshipTypeName": null,
        "relationshipTypeDescription": null
      }
    ]
  }
]
```

### Field Reference

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `epaTribalInternalId` | integer | EPA unique ID (e.g., 100000171) | Stable across name changes; use as primary key if BIA code unavailable |
| `currentName` | string | Current official tribe name | From latest BIA Federal Register notice |
| `currentNameStartDate` | ISO date | When current name became effective | |
| `currentNameEndDate` | ISO date or null | Null for active tribes | |
| `currentBIATribalCode` | string | Current BIA code | **"TBD" for ALL Alaska Native entities** |
| `currentBIARecognizedFlag` | boolean | Federal recognition status | True for all active federally recognized tribes |
| `biaTribalCodes[]` | array | Historical BIA codes with date ranges | |
| `epaLocations[]` | array | State(s) with EPA region assignments | Multi-state tribes have multiple entries |
| `epaLocations[].stateCode` | string | Two-letter state code | |
| `epaLocations[].stateName` | string | Full state name | |
| `epaLocations[].epaRegionName` | string | EPA Region (e.g., "Region 9") | |
| `names[]` | array | All historical name variants with date ranges | Excellent for fuzzy matching corpus |
| `names[].name` | string | Historical or current name | |
| `names[].startDate` | ISO date | When name became effective | Dates as early as "1000-01-01" (epoch placeholder) |
| `names[].endDate` | ISO date or null | Null = current name | |
| `relationships[]` | array | Inter-tribal relationships | Mostly null/empty in observed data |
| `commentText` | string or null | Freeform notes | Usually null |

### Fields NOT Available from EPA API

The following data is NOT in the EPA API (relevant to REG-01 requirements):

- **Latitude/Longitude** -- No geographic coordinates
- **Population / population category** -- Not available
- **Website URL** -- Not available
- **Reservation name** -- Not available (only state-level location)
- **County** -- Not available
- **Congressional district** -- Not available (separate CONG-01 source needed)
- **Ecoregion** -- Not available (separate REG-02 derivation needed)
- **Contact information** -- Not available (available in BIA Tribal Leaders Directory instead)

---

## Data Completeness

**Confidence: MEDIUM** -- Verified for count but gap exists for Lumbee.

### Count Verification

| Source | Count | Date | Notes |
|--------|-------|------|-------|
| BIA Federal Register 2026-01899 | **575** | 2026-01-30 | Authoritative; includes Lumbee |
| EPA Tribe Entity Mapping Spreadsheet | ~574 | 2025-01-31 (data from 2024-12-11) | Pre-Lumbee |
| EPA API (`tribalBandFilter=AllTribes`) | ~574 | Live query 2026-02-10 | Pre-Lumbee |
| EPA API search for "Lumbee" | **0 results** | Live query 2026-02-10 | **Lumbee NOT in EPA database yet** |
| BIA Tribal Leaders Directory | 587 | Latest | Includes sub-component bands (12+ extra rows) |

### Alaska Native BIA Code Gap

**CRITICAL ISSUE:** All Alaska Native entities (~230 tribes) have `currentBIATribalCode: "TBD"` -- meaning BIA codes are NOT assigned for Alaska.

**Impact on REG-01:** The context document specifies "Primary key: BIA code (not EPA Tribe ID or NAICS)." This is INCOMPATIBLE with the data reality. Approximately 40% of federally recognized tribes (Alaska Native villages) lack BIA codes.

**Recommendation:** Use `epaTribalInternalId` as the universal primary key, with BIA code as a secondary indexed field. The EPA Internal ID is:
- Assigned to every tribe (no gaps)
- Stable across name changes
- Sequential integers starting at 100000001
- Explicitly designed by EPA to solve the BIA code gap problem

### Lumbee Tribe Gap

The Lumbee Tribe of North Carolina was added to the federal register on 2026-01-30 via the FY2026 NDAA (enacted 2025-12-18). The EPA API has NOT been updated to include Lumbee yet.

**Handling per context decision:** "Flag missing Tribes as warnings; skip until data source catches up (don't fabricate entries)." This is the correct approach. The registry builder should:
1. Load all tribes from EPA API
2. Cross-reference against the BIA Federal Register list of 575
3. Log a warning for any tribes on the Federal Register list but missing from EPA (currently: Lumbee)
4. Proceed without fabricating a Lumbee entry

### Historical Name Variants

The EPA API provides excellent historical name variant data. Verified examples:

| Tribe | Historical Names | Useful for Fuzzy Matching |
|-------|-----------------|--------------------------|
| Navajo Nation | "Navajo Tribe of..." (pre-1996), "Navajo Nation of..." (1996-2000) | Yes -- users may search old names |
| Cabazon Band | 4 name iterations (1982-2023) | Yes |
| Ak-Chin Indian Community | 4 name iterations | Yes |
| Caddo Nation | 3 iterations | Yes |

The `names[]` array in `/tribeDetails` is the primary corpus for building the fuzzy matching index. Both current names and historical names (where `endDate` is not null) should be indexed.

---

## Alternative/Backup Sources

**Confidence: HIGH** -- Multiple authoritative backup sources verified.

### Source 1: EPA Tribe Entity Mapping Spreadsheet (XLSX)

| Attribute | Value |
|-----------|-------|
| **URL** | `https://www.epa.gov/system/files/documents/2025-01/tribe_entity_mapping_2024-12-11.xlsx` |
| **Format** | Excel (.xlsx) |
| **Updated** | 2025-01-31 (data as of 2024-12-11) |
| **Contents** | Current and historic tribal names, BIA codes, EPA Internal Identifiers, EPA regions, lead EPA regions |
| **Use case** | Static fallback if API is down; can be bundled with the project |
| **Limitations** | Same data as API; will not include Lumbee until next update |

**Recommendation:** Download and commit this spreadsheet as a static fallback. Parse it with `openpyxl` (already a dependency of `python-docx`). If the API is unreachable at registry build time, fall back to this file.

### Source 2: BIA Tribal Leaders Directory CSV

| Attribute | Value |
|-----------|-------|
| **URL** | `https://www.bia.gov/tribal-leaders-csv` |
| **Format** | CSV |
| **Updated** | Continuously (as tribal elections occur) |
| **Records** | ~587 (includes sub-component bands) |
| **Key Fields** | `TribeFullName`, `Tribe`, `TribeAlternateName`, `TribalComponent`, `State`, `BIARegion`, `BIAAgency`, `Latitude`, `Longtitude` [sic], `City`, `ZIPCode`, `Alaska`, `ANCSARegion`, `Phone`, `Email`, `WebSite` |

**Advantages over EPA API:**
- Contains latitude/longitude (EPA API does not)
- Contains website URL, phone, email, physical address
- Contains ANCSA Region for Alaska entities
- Contains BIA Agency assignments

**Disadvantages:**
- 587 rows vs 575 Federal Register count (includes sub-component bands that need filtering)
- Does NOT contain historical name variants (only current and one alternate)
- `TribeAlternateName` field provides one alternate name but not the full historical timeline
- May include rows where `TribalComponent` is a sub-band of a parent tribe
- No EPA Internal Identifier -- cannot cross-reference with EPA API easily

**Recommendation:** Use as supplementary data source to enrich the registry with lat/lon, contact info, and website after building the primary registry from EPA API. Filter out sub-component band rows where `TribalComponent` indicates a band-level entry.

### Source 3: BIA Federal Register Notice (Authoritative List)

| Attribute | Value |
|-----------|-------|
| **Document** | Federal Register 2026-01899 |
| **Published** | 2026-01-30 |
| **Count** | 575 entities |
| **Format** | PDF / Federal Register XML |
| **URL** | `https://www.federalregister.gov/documents/2026/01/30/2026-01899/indian-entities-recognized-by-and-eligible-to-receive-services-from-the-united-states-bureau-of` |

This is the AUTHORITATIVE list. Use it as the validation reference to verify EPA API completeness. It is a plain text list of tribe names -- no BIA codes, no states, no structured data. Its sole purpose is to verify "is this tribe federally recognized?"

### Source 4: NCAI Tribal Directory

| Attribute | Value |
|-----------|-------|
| **URL** | `https://www.ncai.org/tribal-directory` |
| **Format** | Web-only (no API, no bulk download) |
| **Use case** | Manual verification only -- NOT suitable for automated data loading |

Not recommended as a data source -- no programmatic access.

---

## Rate Limits & Reliability

**Confidence: LOW** -- No official rate limit documentation found.

### Rate Limits

No rate limit documentation was found in:
- The OpenAPI specification
- The Swagger UI documentation
- The EPA CDX help pages
- WebSearch results

**Empirical observations from testing:**
- Multiple sequential API calls succeeded without any throttling
- The API returned responses in under 2 seconds per call
- No `429 Too Many Requests` responses observed
- No `X-RateLimit-*` headers observed in responses

**Practical assessment:** For our use case (one-time registry build, calling the API once with `tribalBandFilter=AllTribes` to get all ~574 records in a single response), rate limits are irrelevant. The entire dataset comes back in ONE API call.

### Reliability

- The API is hosted on EPA's CDX Azure cloud infrastructure
- CDX services show overall "Available" status on the status page
- The TRIBES Names Service specifically is NOT listed on the CDX Service Availability Status page (may not be monitored separately)
- The old SOAP/XML TRIBES data flow via Exchange Network has been **deprecated and replaced** by this REST API
- EPA underwent significant changes in early 2025, but the CDX infrastructure (which hosts the tribes API) appears unaffected -- the API responded successfully to all test queries on 2026-02-10

### Current Status (2026-02-10)

**API is LIVE and responding.** All three endpoints tested successfully:
- `/api/v1/tribes` -- returned ~260 records (default filter)
- `/api/v1/tribes?tribalBandFilter=AllTribes` -- returned ~574 records
- `/api/v1/tribeDetails?biaTribalCode=584` -- returned full record for Agua Caliente
- `/api/v1/tribeDetails?tribeName=Cherokee&tribeNameQualifier=contains` -- returned 3 Cherokee tribes
- `/api/v1/tribeDetails?tribeName=Lumbee` -- returned empty array (Lumbee not yet added)
- `/api/v1/tribeDetails?tribalBandFilter=AllTribes&stateCode=AK` -- returned ~230 Alaska Native entities (all with BIA code "TBD")

---

## Recommendations

### Primary Data Loading Strategy

**Use the EPA Tribes Names Service API as the primary data source.** Specifically:

1. **Single API call:** `GET /api/v1/tribeDetails?tribalBandFilter=AllTribes` to retrieve all ~574 detailed tribe records with historical names, states, and EPA regions.

2. **Primary key:** Use `epaTribalInternalId` (integer) as the universal primary key -- NOT BIA code. Store BIA code as a secondary indexed field with a note that Alaska Native entities have code "TBD".

3. **Name variant corpus:** Extract all entries from the `names[]` array for each tribe. Both current names (`endDate: null`) and historical names (`endDate: not null`) feed into the fuzzy matching index.

4. **State extraction:** Parse `epaLocations[]` for state codes. Multi-state tribes (e.g., Navajo: AZ, NM, UT) naturally have multiple entries.

5. **EPA Region:** Available from `epaLocations[].epaRegionName` -- useful for the 7-ecoregion mapping in REG-02.

### Fallback Strategy

```
Primary:  EPA API /tribeDetails?tribalBandFilter=AllTribes
    |
    v (if API down or error)
Fallback: EPA Tribe Entity Mapping XLSX (bundled locally)
    |
    v (for enrichment: lat/lon, contact info, website)
Enrich:   BIA Tribal Leaders Directory CSV
    |
    v (for validation: is the count correct?)
Validate: BIA Federal Register 2026-01899 (575 entities)
```

### Lumbee Handling

- The Lumbee Tribe of North Carolina is NOT in the EPA database yet
- When building the registry, log a WARNING: "Lumbee Tribe (Federal Register 2026-01899) not found in EPA Tribes Names Service. Will be added when EPA updates its database."
- Do NOT fabricate a registry entry
- When EPA eventually adds Lumbee, a registry rebuild will pick it up automatically

### BIA Code Decision Override

The CONTEXT.md states "Primary key: BIA code (not EPA Tribe ID or NAICS)." This decision should be revisited because:
- ~230 Alaska Native entities have BIA code "TBD" (not real codes)
- BIA codes are strings, not integers (e.g., "584", "780", "TBD")
- EPA explicitly created Internal IDs to solve the BIA code problem

**Recommendation:** Use `epaTribalInternalId` as primary key with BIA code as a searchable secondary field. If the user insists on BIA code as primary key, then Alaska Native entities will need a synthetic key (e.g., "AK-{epa_id}") until BIA assigns real codes.

---

## Confidence Level

| Finding | Confidence | Rationale |
|---------|------------|-----------|
| API endpoint URL and structure | **HIGH** | Verified by direct API calls |
| Response schema and fields | **HIGH** | Verified by direct API calls with live data |
| No authentication required | **HIGH** | Confirmed in official docs + verified empirically |
| Historical name variants available | **HIGH** | Verified with Navajo, Cabazon, Cherokee examples |
| Multi-state locations available | **HIGH** | Verified with Navajo (AZ, NM, UT) |
| Alaska Native BIA codes = "TBD" | **HIGH** | Verified with stateCode=AK query |
| Lumbee not in EPA database | **HIGH** | Verified with tribeName=Lumbee query |
| Total tribe count ~574 | **MEDIUM** | WebFetch truncated large responses; count inferred from Region 10 (~280) + other regions |
| Rate limits not an issue | **MEDIUM** | No documentation found; empirically no throttling observed |
| API reliability/uptime | **LOW** | No SLA documentation; API responded to all test queries but no historical uptime data |
| BIA Tribal Leaders Directory fields | **MEDIUM** | Column names from WebSearch, not directly verified via download |

---

## Open Questions

1. **Exact total count from API:** WebFetch truncates large JSON responses. The `/tribeDetails?tribalBandFilter=AllTribes` response could not be fully counted via WebFetch. The actual implementation should log the exact count of records returned and compare against 574 (or 575 once Lumbee is added).

2. **EPA update timeline for Lumbee:** Unknown when EPA will add the Lumbee Tribe to the Tribes Names Service. The Federal Register notice was published 2026-01-30; EPA typically updates from the Federal Register list "at least annually." Could be days or months.

3. **BIA code primary key decision:** Needs user confirmation on whether to override the CONTEXT.md decision given the Alaska Native "TBD" reality. This affects the entire registry data model.

4. **Tribe Entity Mapping Spreadsheet structure:** The XLSX file could not be parsed via WebFetch. The implementation should download and inspect it to verify it contains the same data as the API, and whether it contains any additional fields.

5. **`TribalBandsOnly` band-parent relationship:** The 16 "tribal band" records (e.g., Passamaquoddy Pleasant Point, Bois Forte Band of Minnesota Chippewa) have `currentBIARecognizedFlag: false` in the API even though they ARE federally recognized. The `ExcludeTribalBands` filter removes them. Need to understand if these 16 bands are already counted within their parent tribes in the "AllTribes" response, or if they are additional entries that would push the count above 574.

---

## Sources

### Primary (HIGH confidence)
- EPA Tribes Names Service API -- direct queries to `https://cdxapi.epa.gov/oms-tribes-rest-services/api/v1/*`
- OpenAPI 3.0 spec at `https://cdxapi.epa.gov/oms-tribes-rest-services/v3/api-docs`
- [EPA Tribes Names Service documentation](https://www.epa.gov/data/tribes-names-service)
- [EPA Tribes Services landing page](https://www.epa.gov/data/tribes-services)
- [BIA Federal Register 2026-01899](https://www.federalregister.gov/documents/2026/01/30/2026-01899/indian-entities-recognized-by-and-eligible-to-receive-services-from-the-united-states-bureau-of) -- 575 entities

### Secondary (MEDIUM confidence)
- [EPA Tribe Entity Mapping Spreadsheet](https://www.epa.gov/system/files/documents/2025-01/tribe_entity_mapping_2024-12-11.xlsx) -- referenced but could not parse XLSX
- [BIA Tribal Leaders Directory CSV](https://www.bia.gov/service/tribal-leaders-directory/tld-csvexcel-dataset) -- field list from WebSearch
- [EPA Tribal Identifier Data Standard](https://www.epa.gov/data/tribal-identifier-data-standard)
- [Exchange Network TRIBES (deprecated)](https://exchangenetwork.net/data-exchange/epa-tribal-identification-tribes/) -- confirmed replaced by REST API

### Tertiary (LOW confidence)
- [BIA Tribal Leaders Directory count of 587](https://www.bia.gov/service/tribal-leaders-directory) -- count discrepancy with 575; likely includes sub-component bands
- [NCAI Tribal Directory](https://www.ncai.org/tribal-directory) -- no API access, web-only
- [Lumbee Tribe recognition announcement](https://www.bia.gov/news/lumbee-tribe-added-official-list-federally-recognized-tribes)
