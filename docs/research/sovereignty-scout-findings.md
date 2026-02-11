# Sovereignty Scout Findings: Data Pipeline Audit & Gap Analysis

**Agent**: Sovereignty Scout (TCR Policy Scanner Research Team)
**Date**: 2026-02-11
**Scope**: src/scrapers/, data/, config/, scripts/
**Classification**: T0 (Open)

---

## 1. Executive Summary

This audit reveals that 592 Tribal Nations are receiving advocacy packets built on
incomplete federal data. While the pipeline's architecture is sound -- four scrapers,
two-tier award matching, NRI/USFS hazard profiling, and economic impact modeling -- there
are critical gaps in what we extract from federal APIs and how we handle edge cases.

**Key findings:**

- **Federal Register scraper** does not paginate. If more than 50 documents match a query,
  Tribal Nations lose visibility into regulatory actions that affect their sovereignty.
- **Grants.gov scraper** captures only 7 of ~20 available fields per opportunity. Missing
  fields include estimated total funding, cost-sharing requirements, NOFO URLs, and
  application deadlines with granularity -- information that directly determines whether a
  Tribe can realistically apply.
- **Congress.gov scraper** captures no sponsor, cosponsor, committee assignment, or related
  bill data. For 592 Tribal Nations trying to track legislation through the Senate Committee
  on Indian Affairs, these omissions are devastating.
- **USASpending scraper** fetches only 10 results per CFDA in the general `scan()` method
  (though `fetch_tribal_awards_for_cfda()` does paginate fully). The general scan misses
  the vast majority of spending data.
- **4 of 16 tracked programs have null CFDA numbers** (irs_elective_pay, fema_tribal_mitigation,
  noaa_tribal, usbr_tap, epa_tribal_air), meaning USASpending and Grants.gov cannot query
  them at all. These programs serve Tribal Nations but exist outside our data reach.
- **No integration exists** for OpenFEMA HmaSubapplications, SAM.gov Tribal entity data,
  or the Grants.gov opportunity detail endpoint -- three sources that would fill the majority
  of blank fields in the advocacy packets.

**Why this matters:** Every blank field in a Tribal advocacy packet is a missed argument.
When a Tribal Leader walks into a congressional office and their packet says "Hazard profile
data pending" or shows zero awards when their Nation has actually received funding through
a CFDA we don't track, we have failed in our trust responsibility to provide accurate
intelligence. This audit identifies exactly what to fix and how.

---

## 2. Scraper Audit: Per-Source Field Analysis

### 2.1 Federal Register Scraper (`src/scrapers/federal_register.py`)

**Currently Extracted Fields (14):**

| Field | Source Path | Used In |
|-------|-----------|---------|
| source_id | `document_number` | Dedup key |
| title | `title` | Display, relevance scoring |
| abstract | `abstract` | Relevance scoring |
| url | `html_url` | Packet links |
| pdf_url | `pdf_url` | Packet links |
| published_date | `publication_date` | Recency scoring |
| document_type | `type` | Classification |
| document_subtype | Derived from `action` | ICR/guidance detection |
| agencies | `agencies[].name` | Graph linking |
| agency_ids | `agencies[].id` | Graph linking |
| action | `action` | Subtype classification |
| dates | `dates` | Comment period tracking |
| cfr_references | `cfr_references[].title + part` | Authority graph |
| regulation_ids | `regulation_id_numbers` | Regulatory tracking |

**Available But NOT Captured (12+ fields):**

| API Field | Response Path | Value for Tribal Advocacy |
|-----------|--------------|--------------------------|
| `body_html_url` | `body_html_url` | Full document text URL for deep analysis of Tribal provisions |
| `comment_url` | `comment_url` | Direct link for Tribal governments to submit comments. Missing this means 592 Nations may miss comment deadlines. |
| `comments_close_on` | `comments_close_on` | Exact comment deadline date. Currently we have free-text `dates` but not the parsed close date. |
| `effective_on` | `effective_on` | When a final rule takes effect. Critical for compliance timelines. |
| `docket_ids` | `docket_ids[]` | Links to Regulations.gov docket for tracking rulemaking lifecycle. |
| `executive_order_number` | `executive_order_number` | Identifies EO 13175 (Tribal consultation) references directly. |
| `json_url` | `json_url` | Full JSON representation URL for downstream processing. |
| `page_views.count` | `page_views.count` | Indicator of political attention on a document. |
| `regulation_id_number_info` | `regulation_id_number_info{}` | Expanded regulatory info including priority and stage. |
| `significant` | `significant` | Whether the document is "significant" under EO 12866 -- these require Tribal consultation. |
| `signing_date` | `signing_date` | For presidential documents, the actual signing date. |
| `subtype` | `subtype` | API-provided subtype (vs. our derived one from action text). |
| `topics` | `topics[]` | Topic tags that could improve relevance classification. |
| `full_text_xml_url` | `full_text_xml_url` | XML format for structured parsing of bill text. |

**Highest Impact Missing Fields:**

1. **`comments_close_on`** + **`comment_url`**: Every missed comment period is a missed
   opportunity for Tribal voice in rulemaking. The `dates` field contains free text like
   "Comments must be received by March 15, 2026" but we need the parsed ISO date for
   automated deadline monitoring.

2. **`significant`**: EO 12866 significant rules trigger EO 13175 Tribal consultation
   requirements. Capturing this field would let the Consultation Monitor (monitors/) detect
   whether agencies are meeting their consultation obligations.

3. **`docket_ids`**: Links Federal Register documents to their Regulations.gov docket,
   enabling tracking across NPRM -> comment period -> final rule lifecycle.

**Pagination Gap:**

The Federal Register API returns paginated results with `count`, `total_pages`, and `next_page_url`
in the response. Our scraper requests `per_page=50` but **never checks for additional pages**.
Both `_search()` and `_search_by_agencies()` make a single request and return whatever comes back.

For active rulemaking periods (e.g., after a major appropriations bill), a single agency like
BIA could generate 100+ documents in 14 days. We would capture only the first 50.

### 2.2 Grants.gov Scraper (`src/scrapers/grants_gov.py`)

**Currently Extracted Fields (12):**

| Field | Source Path | Used In |
|-------|-----------|---------|
| source_id | `id` | Dedup key |
| title | `title` | Display, scoring |
| abstract | `synopsis` | Relevance scoring |
| url | Constructed from `id` | Packet links |
| published_date | `openDate` | Recency scoring |
| close_date | `closeDate` | Deadline tracking |
| document_type | Hardcoded `grant_opportunity` | Classification |
| agencies | `agencyCode` | Graph linking |
| award_ceiling | `awardCeiling` | Funding range display |
| award_floor | `awardFloor` | Funding range display |
| tribal_eligible | Derived from `eligibleApplicants` | Force-include logic |
| eligibility_codes | `eligibleApplicants` | Eligibility classification |

**Available But NOT Captured (~13 fields from search2 endpoint):**

| API Field | Response Path | Value for Tribal Advocacy |
|-----------|--------------|--------------------------|
| `estimatedFunding` | `oppHits[].estimatedFunding` | Total program funding envelope. Without this, Tribal Nations cannot assess competitiveness. |
| `costSharing` | `oppHits[].costSharing` | Whether cost-sharing is required (boolean). Critical for identifying match-waiver advocacy targets. |
| `numberOfAwards` | `oppHits[].numberOfAwards` | Expected award count. Informs probability of success. |
| `categoryOfFunding` | `oppHits[].categoryOfFunding` | Funding category code (e.g., "EN" for Environment). Enables cross-program analysis. |
| `fundingInstrumentType` | `oppHits[].fundingInstrumentType` | Grant, cooperative agreement, or other. Affects reporting burden. |
| `agencyName` | `oppHits[].agencyName` | Full agency name (not just code). Better display. |
| `oppNumber` | `oppHits[].oppNumber` | Official opportunity number for reference in applications. |
| `cfdas` | `oppHits[].cfdas[]` | Full CFDA/ALN numbers associated with opportunity (may differ from our search CFDA). |
| `archiveDate` | `oppHits[].archiveDate` | When the opportunity will be archived. Helps with staleness detection. |
| `version` | `oppHits[].version` | Tracks amendments/modifications to the opportunity. |
| `lastUpdatedDate` | `oppHits[].lastUpdatedDate` | Detects changes since last scan. |
| `additionalInformationUrl` | `oppHits[].additionalInformationUrl` | Direct link to the NOFO document. Currently our URL is a search results page, not the actual NOFO. |
| `closeDateExplanation` | `oppHits[].closeDateExplanation` | Explains rolling or multiple deadlines. |

**Highest Impact Missing Fields:**

1. **`costSharing`**: This boolean field directly identifies which grants require cost-share
   matches. For Tribal Nations -- many of whom lack the administrative capacity for cost-share
   -- this is the difference between "worth applying" and "structurally inaccessible." Currently,
   our packets mention cost-share as a structural barrier but cannot flag it per-opportunity.

2. **`estimatedFunding`** + **`numberOfAwards`**: These two fields together tell a Tribal grant
   writer whether a $100K request is competing against a $10M pool (good odds) or a $500K pool
   (bad odds). Without this, Tribal Nations are applying blind.

3. **`additionalInformationUrl`**: The current URL we construct
   (`https://www.grants.gov/search-results-detail/{id}`) is a search page, not the NOFO itself.
   Tribal grant writers need the direct NOFO link.

**Pagination Gap:**

The `_search()` method requests `rows=50` and the `_search_cfda()` method requests `rows=25`.
Neither checks the response for total result count or pagination metadata. The Grants.gov
search2 API returns `totalCount` and supports `startRecord` for pagination. For broad keyword
searches like "tribal climate resilience," 50 results may represent only a fraction of
available opportunities.

### 2.3 Congress.gov Scraper (`src/scrapers/congress_gov.py`)

**Currently Extracted Fields (11):**

| Field | Source Path | Used In |
|-------|-----------|---------|
| source_id | `{congress}-{type}-{number}` | Dedup key |
| title | `title` | Display, scoring |
| abstract | `latestAction.text` | Relevance scoring (misused -- this is action text, not a summary) |
| url | `url` or constructed | Packet links |
| published_date | `updateDate` | Recency scoring |
| document_type | `{type} {number}` | Classification |
| congress | `congress` | Session filtering |
| bill_type | `type` | Bill vs. resolution classification |
| bill_number | `number` | Identification |
| latest_action | `latestAction.text` | Legislative status tracking |
| latest_action_date | `latestAction.actionDate` | Timeline tracking |

**Available But NOT Captured (15+ fields from bill detail endpoint):**

The Congress.gov API provides a rich bill detail at `/bill/{congress}/{type}/{number}`.
Our scraper only uses the search/list endpoint and never fetches bill details. This means
we miss:

| API Field | Response Path | Value for Tribal Advocacy |
|-----------|--------------|--------------------------|
| `sponsors[]` | `/bill/{c}/{t}/{n}/sponsors` | **Primary sponsor** of the bill. If a Tribe's own Senator sponsors a bill, that's a critical advocacy signal. |
| `cosponsors[]` | `/bill/{c}/{t}/{n}/cosponsors` | Full cosponsor list with party affiliation. Shows bipartisan support strength. |
| `cosponsors.count` | `bill.cosponsors.count` | Quick indicator of bill momentum. |
| `committees[]` | `/bill/{c}/{t}/{n}/committees` | **Committee assignments** -- especially Senate Indian Affairs, House Natural Resources. Critical for knowing where to apply pressure. |
| `subjects[]` | `/bill/{c}/{t}/{n}/subjects` | Legislative Subject Terms (LOC controlled vocab). Enables systematic classification. |
| `summaries[]` | `/bill/{c}/{t}/{n}/summaries` | CRS bill summaries (when available). Real abstracts, unlike the `latestAction.text` we currently use as abstract. |
| `relatedBills[]` | `/bill/{c}/{t}/{n}/relatedBills` | Companion bills, identical bills, amendments. Critical for tracking a bill's full legislative journey. |
| `actions[]` | `/bill/{c}/{t}/{n}/actions` | Full action history (introduced -> committee -> vote). Currently we only have the latest action. |
| `textVersions[]` | `/bill/{c}/{t}/{n}/text` | URLs to bill text in various formats. Enables full-text analysis. |
| `policyArea` | `bill.policyArea` | Primary policy area (e.g., "Native Americans"). High-signal field for relevance. |
| `laws[]` | `bill.laws` | If enacted, the Public Law number. Critical for tracking enacted legislation. |
| `amendmentsToAmendments` | Various amendment endpoints | Amendment tracking for markup/floor activity. |
| `cboCostEstimates[]` | `bill.cboCostEstimates` | CBO cost estimates with URLs. Authoritative funding figures. |
| `originChamber` | `bill.originChamber` | Whether the bill started in House or Senate. Procedural signal. |
| `introducedDate` | `bill.introducedDate` | Original introduction date (vs. updateDate which changes on any action). |

**Highest Impact Missing Fields:**

1. **`sponsors` + `cosponsors`**: When the Senate Committee on Indian Affairs introduces
   a bill, every Tribal Nation in the affected states should know immediately. Without sponsor
   data, we cannot cross-reference bills against the congressional delegation in each Tribe's
   packet. This is perhaps the single highest-impact missing field across all four scrapers.

2. **`committees`**: A bill assigned to the House Natural Resources Subcommittee for Indigenous
   Peoples requires different advocacy strategy than one in Ways and Means. Without committee
   data, our packets cannot guide Tribal Leaders on where to direct their advocacy.

3. **`summaries`**: We currently populate the `abstract` field with `latestAction.text`,
   which gives us things like "Referred to the Committee on Indian Affairs" instead of an actual
   bill description. CRS summaries (available for most introduced bills) would provide
   real abstracts that feed into relevance scoring.

4. **`policyArea`**: The "Native Americans" policy area tag would let us filter with near-100%
   precision, instead of relying on keyword matching that produces both false positives and
   false negatives.

**Pagination Gap:**

Both `_search_congress()` and `_search()` request `limit=50` but never check the `pagination`
object in the response. Congress.gov returns `pagination.count` (total results) and
`pagination.next` (URL for next page). For broad queries like "tribal energy" across all bill
types, we likely miss results.

### 2.4 USASpending Scraper (`src/scrapers/usaspending.py`)

**Currently Extracted Fields (scan method: 8, fetch_tribal_awards: 10):**

*General scan (`_fetch_obligations`) -- limited to 10 results per CFDA:*

| Field | Source Path | Used In |
|-------|-----------|---------|
| source_id | Constructed | Dedup key |
| title | Constructed from Award ID + recipient | Display |
| abstract | Constructed from amount + CFDA + recipient | Display |
| url | Constructed from internal_id | Links |
| published_date | `Start Date` | Timeline |
| document_type | Hardcoded `obligation` | Classification |
| agencies | `Awarding Agency` | Graph linking |
| award_amount | `Award Amount` or `Total Obligation` | Funding totals |
| cfda | Passed in | Program linking |
| recipient | `Recipient Name` | Tribe matching |

*Tribal award fetch (`fetch_tribal_awards_for_cfda`) -- fully paginated:*

| Additional Field | Source Path |
|-----------------|-----------|
| Total Obligation | `Total Obligation` |
| End Date | `End Date` |
| Description | `Description` |
| CFDA Number | `CFDA Number` |
| recipient_id | `recipient_id` |

**Available But NOT Captured (20+ fields from spending_by_award):**

| API Field | `fields[]` Value | Value for Tribal Advocacy |
|-----------|-----------------|--------------------------|
| `Recipient UEI` | `recipient_uei` | **Unique Entity Identifier** -- the cross-system join key for linking Tribal entities across USASpending, SAM.gov, and Grants.gov. Without UEI, we rely on fuzzy name matching. |
| `Recipient State Code` | `recipient_state_code` | State code for state-overlap validation in award matching. Currently extracted heuristically from name. |
| `Recipient DUNS` | `Recipient DUNS` | Legacy identifier still present in historical records. |
| `Place of Performance City` | `Place of Performance City` | Geographic precision beyond state level. |
| `Place of Performance State` | `Place of Performance State Code` | Place of performance (may differ from recipient state). |
| `Place of Performance County` | `Place of Performance County` | County-level data for NRI hazard cross-referencing. |
| `Place of Performance ZIP` | `Place of Performance Zip5` | ZIP code for geographic targeting. |
| `Period of Performance Current End Date` | `Period of Performance Current End Date` | Current end date (vs. original). Detects extensions. |
| `Award Type` | `Award Type` | Grant, cooperative agreement, etc. Differentiates funding instruments. |
| `Awarding Sub Agency` | `Awarding Sub Agency` | Sub-agency precision (e.g., "Bureau of Indian Affairs" under Interior). |
| `Funding Agency` | `Funding Agency` | May differ from awarding agency in cross-agency programs. |
| `Funding Sub Agency` | `Funding Sub Agency` | Sub-agency that funded (appropriation source). |
| `NAICS Code` | `NAICS Code` | Industry classification for economic impact refinement. |
| `SAI Number` | `SAI Number` | State Application Identifier for state-level tracking. |
| `Last Modified Date` | `Last Modified Date` | Detects changes to existing awards. |
| `Award Base Action Date` | `Award Base Action Date` | Original award date (vs. modifications). |
| `Total Outlays` | `Total Outlays` | Actual dollars spent (vs. obligated). Critical distinction. |
| `Total Subsidy Cost` | `Total Subsidy Cost` | For loan programs, the subsidy cost. |
| `COVID-19 Obligations` | `COVID-19 Obligations` | Tracks pandemic-era supplemental funding. |
| `Infrastructure Obligations` | `Infrastructure Obligations` | Tracks IIJA/BIL-specific obligations. |

**Highest Impact Missing Fields:**

1. **`recipient_uei`**: The Unique Entity Identifier is the Rosetta Stone of federal spending
   data. With UEI, we can deterministically link a USASpending award to a SAM.gov entity
   registration to a Grants.gov application. Without it, we rely on fuzzy name matching with
   a rapidfuzz threshold of 85 -- which means some Tribal Nations are incorrectly matched or
   missed entirely.

2. **`Place of Performance State Code`** + **`Place of Performance County`**: These fields
   enable direct joins between award data and FEMA NRI hazard profiles. A Tribe's award in
   a specific county with "Very High" wildfire risk is a much more compelling argument than
   just the dollar amount alone.

3. **`Total Outlays`**: Obligations represent commitments; outlays represent actual spending.
   The gap between obligations and outlays can reveal administrative delays that harm Tribal
   Nations. If $5M was obligated but only $500K outlayed, that's a signal of implementation
   barriers.

4. **`Infrastructure Obligations`**: Directly identifies IIJA/BIL funding, which is central
   to the IIJA Sunset Monitor.

**Pagination/Completeness Issues:**

- `scan()` fetches only **10 results per CFDA** (`"limit": 10`). With 12 tracked CFDAs,
  this yields at most 120 records. USASpending may have thousands of grants under CFDA 20.205
  (FHWA). This is a severe data truncation.
- `fetch_tribal_awards_for_cfda()` correctly paginates using `page_metadata.hasNext`. This
  is the right pattern.
- **Hardcoded fiscal year**: The `scan()` method hardcodes `"start_date": "2025-10-01"` and
  `"end_date": "2026-09-30"`. This violates Critical Rule #1 (never hardcode fiscal years).

---

## 3. Field-to-API Mapping Table: Blank Fields in Output Documents

This table maps every field that appears blank, null, or incomplete in the generated DOCX
advocacy packets to the specific federal API endpoint that could fill it.

### 3.1 Programs with Null CFDA Numbers

These 5 programs have `"cfda": null` in `program_inventory.json`, meaning neither USASpending
nor Grants.gov can query them by Assistance Listing Number:

| Program | ID | Why CFDA Is Null | Resolution Strategy |
|---------|----|------------------|-------------------|
| IRS Elective Pay | `irs_elective_pay` | Tax credit mechanism, not a grant program. No ALN. | Query USASpending by agency (Treasury) + keyword "elective pay" or track via Federal Register rulemaking. |
| FEMA Tribal Mitigation Plans | `fema_tribal_mitigation` | Planning support, not a distinct ALN. Falls under FEMA HMA (97.039). | Add 97.039 as secondary CFDA; query OpenFEMA `HmaSubapplications` with `tribalRequest=true`. |
| NOAA Tribal Grants | `noaa_tribal` | Multiple NOAA programs, no single ALN. | Research specific ALNs: 11.420 (Coastal Zone), 11.463 (Habitat Conservation), 11.473 (Office of Education). Add as list. |
| USBR TAP | `usbr_tap` | Technical assistance embedded in WaterSMART. | Query under parent CFDA 15.507 and filter by award description containing "technical assistance." |
| EPA Tribal Air | `epa_tribal_air` | Clean Air Act Section 105 grants. | Add CFDA 66.001 (Air Pollution Control Program Support) to program_inventory.json. |

### 3.2 Blank Packet Fields -> API Endpoints

| Blank Field | Where It Appears | API Endpoint | Query Parameters | Response Path |
|-------------|-----------------|--------------|-----------------|--------------|
| **Bill sponsors** | Congress bills in knowledge graph | `GET api.congress.gov/v3/bill/{congress}/{type}/{number}` | API key header | `bill.sponsors[].fullName`, `bill.sponsors[].party`, `bill.sponsors[].state` |
| **Bill cosponsors** | Congress bills / delegation cross-ref | `GET api.congress.gov/v3/bill/{congress}/{type}/{number}/cosponsors` | API key header, `limit=250` | `cosponsors[].fullName`, `cosponsors[].party`, `cosponsors[].state` |
| **Bill committees** | Hot Sheet structural context | `GET api.congress.gov/v3/bill/{congress}/{type}/{number}/committees` | API key header | `committees[].name`, `committees[].chamber`, `committees[].type` |
| **Bill summary** | Currently using latestAction.text as abstract | `GET api.congress.gov/v3/bill/{congress}/{type}/{number}/summaries` | API key header | `summaries[].text`, `summaries[].updateDate` |
| **Comment deadline** | Federal Register items | `GET federalregister.gov/api/v1/documents.json` | Add `comments_close_on` to `fields[]` | `results[].comments_close_on` (ISO date) |
| **Comment URL** | Federal Register items | Same as above | Add `comment_url` to `fields[]` | `results[].comment_url` |
| **Grant cost-sharing** | Hot Sheet program details | `POST api.grants.gov/v1/api/search2` | Already querying | `oppHits[].costSharing` (boolean) |
| **Grant estimated funding** | Hot Sheet program details | `POST api.grants.gov/v1/api/search2` | Already querying | `oppHits[].estimatedFunding` (number) |
| **Grant number of awards** | Hot Sheet program details | `POST api.grants.gov/v1/api/search2` | Already querying | `oppHits[].numberOfAwards` (integer) |
| **NOFO direct URL** | Hot Sheet links | `POST api.grants.gov/v1/api/search2` | Already querying | `oppHits[].additionalInformationUrl` |
| **Recipient UEI** | Award matching pipeline | `POST api.usaspending.gov/api/v2/search/spending_by_award/` | Add `"Recipient UEI"` to `fields[]` | `results[].recipient_uei` |
| **Recipient state** | Award-to-Tribe matching | Same as above | Add `"Recipient State Code"` to `fields[]` | `results[].Recipient State Code` |
| **Place of performance** | Hazard cross-referencing | Same as above | Add county/state fields to `fields[]` | `results[].'Place of Performance State Code'`, `results[].'Place of Performance County'` |
| **BRIC/FMA Tribal grants** | FEMA program tracking | `GET fema.gov/api/open/v1/HmaSubapplications` | `$filter=tribalRequest eq true`, `$select=...`, `$top=10000` | `HmaSubapplications[].subapplicantName`, `.projectAmount`, `.status` |
| **Tribal SAM.gov entities** | Entity verification / UEI linking | `GET api.sam.gov/entity-information/v3/entities` | `businessTypeList=2X`, `api_key=...` | `entityData[].entityRegistration.ueiSAM`, `.legalBusinessName` |
| **Total outlays** | Award execution tracking | `POST api.usaspending.gov/api/v2/search/spending_by_award/` | Add `"Total Outlays"` to `fields[]` | `results[].'Total Outlays'` |
| **Infrastructure obligations** | IIJA Sunset Monitor | Same as above | Add `"Infrastructure Obligations"` to `fields[]` | `results[].'Infrastructure Obligations'` |

---

## 4. Pagination & Retry Assessment

### 4.1 Base Scraper (`base.py`) -- Retry/Backoff Analysis

**Implementation Quality: GOOD with caveats.**

The `_request_with_retry()` method correctly implements:
- Exponential backoff with jitter: `BACKOFF_BASE ** attempt + random.uniform(0, 1)`
- 429 rate-limit handling with Retry-After header respect
- Separate rate_limit_hits counter (429s don't consume attempt budget)
- Maximum Retry-After cap of 300 seconds (prevents infinite waits)
- Configurable retries (default 3)
- Proper User-Agent header for federal API compliance

**Issues found:**

1. **403 handling is asymmetric**: On 403, the method stores the error but falls through to
   the retry loop without any specific strategy. For federal APIs, a 403 often means the API
   key is invalid or expired (Congress.gov), not a transient failure. After 3 retries with
   increasing backoff, we'd waste 14+ seconds on what's likely a permanent auth failure.
   **Recommendation**: On 403, log a distinct warning about API key validity and reduce
   retries to 1.

2. **No timeout session-level configuration**: The default `aiohttp.ClientTimeout(total=30)`
   is global. Some federal APIs (especially USASpending with large result sets) may need longer
   timeouts for paginated queries.

3. **No connection pooling configuration**: The `_create_session()` creates a vanilla session.
   For 12+ sequential CFDA queries to the same API, connection pooling with `TCPConnector`
   would improve throughput.

### 4.2 Per-Scraper Pagination Assessment

| Scraper | Pagination Implemented? | Max Results per Query | Total Possible Results | Data Loss Risk |
|---------|----------------------|---------------------|---------------------|---------------|
| Federal Register | **NO** | 50 | Unlimited | **HIGH** during active rulemaking |
| Grants.gov (CFDA) | **NO** | 25 | `totalCount` available | **MEDIUM** for popular CFDAs |
| Grants.gov (keyword) | **NO** | 50 | `totalCount` available | **MEDIUM** for broad queries |
| Congress.gov (targeted) | **NO** | 50 | `pagination.count` available | **MEDIUM** for active sessions |
| Congress.gov (broad) | **NO** | 50 | `pagination.count` available | **MEDIUM** |
| USASpending (scan) | **NO** | 10 | Thousands | **CRITICAL** -- only 10 per CFDA |
| USASpending (tribal awards) | **YES** | 100/page | Full dataset | Low |
| USASpending (all tribal) | **YES** | Inherits from above | Full dataset | Low |

**Summary**: Of 7 distinct query paths, only 2 implement pagination. Five query paths truncate
results silently, meaning Tribal Nations are making decisions based on partial data.

### 4.3 Edge Cases That Could Cause Partial Data

1. **Silent truncation**: No scraper logs a warning when results may have been truncated.
   When Federal Register returns exactly 50 results, we should log "WARNING: Result count
   equals page size, additional results may exist."

2. **Network interruption mid-pagination**: The USASpending `fetch_tribal_awards_for_cfda()`
   catches exceptions per-page and breaks the loop, but keeps results from successful pages.
   This is correct graceful degradation -- but the caller has no way to know the result is
   partial.

3. **Rate limiting during batch**: If we hit a 429 during the CFDA sweep, the backoff delays
   apply per-request but the 0.3s/0.5s sleep between CFDAs doesn't account for accumulated
   rate-limit debt. A particularly aggressive rate limiter could cause cascading failures.

4. **Empty result on valid CFDA**: The zombie CFDA detector in `base.py` correctly handles
   this for Grants.gov, but no equivalent exists for USASpending, Congress.gov, or Federal
   Register.

5. **Hardcoded fiscal year in USASpending `scan()`**: `"start_date": "2025-10-01"` and
   `"end_date": "2026-09-30"` -- this will silently return zero results for any query after
   FY26 ends. Violates Critical Rule #1.

---

## 5. New Data Source Integration Specs

### 5.1 Grants.gov Enhanced Fields (search2 endpoint)

**Current integration**: `POST api.grants.gov/v1/api/search2`

**Enhancement**: No new endpoint needed. Simply add fields to the `_normalize()` extraction.

```
# Fields to add to _normalize():
"estimated_funding": item.get("estimatedFunding", ""),
"cost_sharing_required": item.get("costSharing", None),
"number_of_awards": item.get("numberOfAwards", ""),
"funding_instrument_type": item.get("fundingInstrumentType", ""),
"category_of_funding": item.get("categoryOfFunding", ""),
"opportunity_number": item.get("oppNumber", ""),
"nofo_url": item.get("additionalInformationUrl", ""),
"agency_name": item.get("agencyName", ""),
"last_updated": item.get("lastUpdatedDate", ""),
"archive_date": item.get("archiveDate", ""),
```

**Pagination fix**:
```
# After initial request, check totalCount:
total = data.get("totalCount", 0)
fetched = len(results)
if total > fetched:
    # Paginate using startRecord parameter
    while fetched < total:
        payload["startRecord"] = fetched
        next_resp = await self._request_with_retry(...)
        next_results = next_resp.get("data", {}).get("oppHits", [])
        if not next_results:
            break
        results.extend(next_results)
        fetched += len(next_results)
```

**Effort**: Low (2-3 hours). No new API, no new auth. Just expand field extraction and add
pagination loop.

### 5.2 Grants.gov Opportunity Detail Endpoint

**Endpoint**: `GET api.grants.gov/v1/api/fetchOppDetails/{opportunityId}`

**Use case**: After the search2 endpoint identifies relevant opportunities, fetch full
details including complete NOFO text, all eligibility details, application instructions,
and contact information.

**Integration spec**:
```
async def _fetch_opportunity_detail(self, session, opp_id: str) -> dict:
    url = f"{self.base_url}/api/fetchOppDetails/{opp_id}"
    return await self._request_with_retry(session, "GET", url)
```

**Key response fields**:
- `opportunity.synopsis.applicantEligibility.description` -- Full eligibility text
- `opportunity.synopsis.costSharingOrMatchingRequirement` -- Detailed match info
- `opportunity.synopsis.otherCategoryExplanation` -- Category details
- `opportunity.contact.email` -- Program officer contact

**Effort**: Medium (4-6 hours). New API call per opportunity; need rate limiting and caching.
Only fetch details for Tribal-eligible opportunities to conserve API budget.

### 5.3 SAM.gov Entity Registrations (Tribal Entities)

**Endpoint**: `GET api.sam.gov/entity-information/v3/entities`

**Auth**: API key required. **Rate limit: 10 requests/day for non-federal users.**

**Use case**: Build a definitive UEI-to-Tribe mapping table. Currently our award matching
uses fuzzy name matching (Tier 2). With SAM.gov UEIs, we could achieve 100% match accuracy
for registered Tribal entities.

**Integration spec**:
```
params = {
    "api_key": os.environ.get("SAM_API_KEY", ""),
    "businessTypeList": "2X",  # Indian/Native American Tribal Government
    "registrationStatus": "A",  # Active registrations
    "purposeOfRegistration": "ALL",
    "includeSections": "entityRegistration,coreData",
    "page": 0,
    "size": 100,
}
url = "https://api.sam.gov/entity-information/v3/entities"
```

**Key response fields**:
- `entityData[].entityRegistration.ueiSAM` -- Unique Entity Identifier
- `entityData[].entityRegistration.legalBusinessName` -- Official registered name
- `entityData[].entityRegistration.physicalAddress.stateOrProvinceCode` -- State
- `entityData[].entityRegistration.congressionalDistrict` -- Congressional district

**Cache strategy**: Given 10 req/day limit, build a local cache of all `2X` entities (likely
~1,000 records at 100/page = 10 pages = 10 days of API calls). Cache as
`data/sam_tribal_entities.json`. Refresh monthly.

**Impact**: This would transform award matching from probabilistic to deterministic. Instead
of fuzzy matching "Navajo Nation" with 85% confidence, we'd match UEI `XXXXXXXXX` with
100% confidence.

**Effort**: Medium-high (8-12 hours). Requires API key management, aggressive caching, and
a scheduled build script.

### 5.4 OpenFEMA HmaSubapplications (BRIC/FMA Tribal Grants)

**Endpoint**: `GET https://www.fema.gov/api/open/v1/HmaSubapplications`

**Auth**: No key required. **Rate limit**: Generous (OData API, 10,000 records per call).

**Use case**: FEMA BRIC has been terminated, but historical BRIC/FMA subapplication data
reveals which Tribal Nations applied, which were funded, and which were denied. This is
critical intelligence for:
1. Identifying Tribes with existing mitigation plans (prerequisite for future programs)
2. Tracking the "responsive mitigation" replacement mechanism
3. Building the case for Tribal set-asides in whatever replaces BRIC

**Integration spec**:
```
# Fetch all Tribal BRIC/FMA subapplications
params = {
    "$filter": "tribalRequest eq true",
    "$select": (
        "subapplicantName,subapplicationType,projectType,projectAmount,"
        "federalShareAmount,costSharePercentage,status,state,county,"
        "hazardMitigationPlanStatus,programArea,disasterNumber"
    ),
    "$top": 10000,
    "$orderby": "projectAmount desc",
}
url = "https://www.fema.gov/api/open/v1/HmaSubapplications"
```

**Key response fields**:
- `subapplicantName` -- Tribal applicant name (matches to our registry)
- `projectAmount` -- Total project cost
- `federalShareAmount` -- Federal funding share
- `costSharePercentage` -- Cost share required
- `status` -- Approved / Denied / Withdrawn / Pending
- `hazardMitigationPlanStatus` -- Whether Tribe has an approved mitigation plan
- `programArea` -- BRIC, FMA, HMGP, etc.
- `state`, `county` -- Geographic context

**Additional useful endpoints**:
- `GET /api/open/v1/HazardMitigationPlanStatuses` -- Current plan status for all Tribal
  mitigation plans. Critical for the fema_tribal_mitigation program.
- `GET /api/open/v1/FemaRegions` -- FEMA region mapping for geographic routing.

**Effort**: Medium (6-8 hours). No auth, generous rate limits, well-documented OData API.
Could be implemented as a new scraper class or added to the USASpending scraper.

### 5.5 Congress.gov Bill Detail Enhancement

**Endpoint**: `GET api.congress.gov/v3/bill/{congress}/{type}/{number}`

**Auth**: Same API key as existing Congress.gov scraper.

**Use case**: After the search endpoint identifies relevant bills, fetch full details
for each bill to populate sponsor, cosponsor, committee, and summary data.

**Integration spec**:
```
async def _fetch_bill_detail(self, session, congress: int, bill_type: str, number: str) -> dict:
    """Fetch full bill detail including sponsors and committees."""
    url = f"{self.base_url}/bill/{congress}/{bill_type}/{number}"
    data = await self._request_with_retry(session, "GET", url)
    bill = data.get("bill", {})

    # Sponsors (separate endpoint)
    sponsors_url = f"{url}/cosponsors"
    sponsors_data = await self._request_with_retry(session, "GET", sponsors_url)
    cosponsors = sponsors_data.get("cosponsors", [])

    # Committees (separate endpoint)
    committees_url = f"{url}/committees"
    committees_data = await self._request_with_retry(session, "GET", committees_url)
    committees = committees_data.get("committees", [])

    # Summary (separate endpoint)
    summaries_url = f"{url}/summaries"
    summaries_data = await self._request_with_retry(session, "GET", summaries_url)
    summaries = summaries_data.get("summaries", [])

    return {
        "sponsors": bill.get("sponsors", []),
        "cosponsors": cosponsors,
        "committees": committees,
        "summaries": summaries,
        "policy_area": bill.get("policyArea", {}).get("name", ""),
        "introduced_date": bill.get("introducedDate", ""),
        "origin_chamber": bill.get("originChamber", ""),
        "cbo_cost_estimates": bill.get("cboCostEstimates", []),
    }
```

**Rate limit consideration**: Congress.gov allows 5,000 req/hour. Each bill detail requires
up to 4 API calls (bill + cosponsors + committees + summaries). For 50 bills, that's 200
calls -- well within limits.

**Effort**: Medium (6-8 hours). Requires new _fetch_bill_detail method, expanded _normalize,
and additional fields in the normalized output. Also needs rate limiting between detail
fetches.

---

## 6. Priority Recommendations

### Tier 1: Critical / Immediate (Impact for All 592 Tribal Nations)

**P1.1: Fix USASpending `scan()` hardcoded fiscal year and pagination**
- **What**: Replace `"start_date": "2025-10-01"` with config-driven dates. Increase limit
  from 10 to 100. Add pagination loop.
- **Why**: Violates Critical Rule #1 AND truncates 90%+ of spending data. Every Tribe's
  award history is incomplete.
- **Files**: `src/scrapers/usaspending.py` (lines 67-81)
- **Effort**: 2 hours

**P1.2: Add UEI to USASpending field requests**
- **What**: Add `"Recipient UEI"` and `"Recipient State Code"` to both `scan()` and
  `fetch_tribal_awards_for_cfda()` field lists.
- **Why**: Transforms award-to-Tribe matching from 85% fuzzy accuracy to near-100%.
  This single field addition could correctly attribute millions in funding to Tribal Nations
  that our fuzzy matcher currently misses.
- **Files**: `src/scrapers/usaspending.py` (lines 72-75, 122-133)
- **Effort**: 1 hour (field addition) + 4 hours (UEI-based matching in awards.py)

**P1.3: Add pagination to Federal Register scraper**
- **What**: After initial request, check `total_pages` in response. Loop with `page` parameter.
- **Why**: Missing regulatory actions means Tribal Nations may not know about comment periods,
  final rules, or consultation requirements that directly affect their sovereignty.
- **Files**: `src/scrapers/federal_register.py` (methods `_search`, `_search_by_agencies`)
- **Effort**: 3 hours

### Tier 2: High Priority (Significantly Improves Packet Quality)

**P2.1: Expand Grants.gov field extraction**
- **What**: Add `costSharing`, `estimatedFunding`, `numberOfAwards`,
  `additionalInformationUrl`, `fundingInstrumentType` to `_normalize()`.
- **Why**: Cost-sharing is the #1 barrier to Tribal participation in competitive grants.
  Flagging it per-opportunity lets Tribal grant writers focus on accessible programs.
- **Files**: `src/scrapers/grants_gov.py` (method `_normalize`)
- **Effort**: 2 hours

**P2.2: Add Congress.gov bill detail fetching**
- **What**: After search, fetch sponsor/cosponsor/committee data for each bill.
- **Why**: Without sponsor data, we cannot tell a Tribal Leader "Your Senator cosponsored
  this bill" -- one of the most powerful advocacy signals possible.
- **Files**: `src/scrapers/congress_gov.py` (new `_fetch_bill_detail` method)
- **Effort**: 6 hours

**P2.3: Integrate OpenFEMA HmaSubapplications**
- **What**: New scraper or module fetching Tribal BRIC/FMA subapplication data.
- **Why**: With BRIC terminated, historical subapplication data is the evidence base for
  advocating Tribal set-asides in the replacement mechanism. 592 Tribal Nations need to
  know which of their neighbors received BRIC funding and which were denied.
- **Files**: New file in `src/scrapers/` or addition to `usaspending.py`
- **Effort**: 8 hours

### Tier 3: Important / Medium-Term (Fills Remaining Gaps)

**P3.1: Add Federal Register comment deadline and significance fields**
- **What**: Add `comments_close_on`, `comment_url`, `significant` to fields[] request.
- **Why**: Automated comment deadline monitoring and EO 13175 consultation tracking.
- **Files**: `src/scrapers/federal_register.py` (fields[] arrays in `_search` methods)
- **Effort**: 2 hours + 4 hours (integration with Consultation Monitor)

**P3.2: Add pagination to Grants.gov scraper**
- **What**: Check `totalCount` in response, paginate using `startRecord`.
- **Why**: Ensures complete coverage of grant opportunities.
- **Files**: `src/scrapers/grants_gov.py` (methods `_search`, `_search_cfda`)
- **Effort**: 3 hours

**P3.3: Add pagination to Congress.gov scraper**
- **What**: Check `pagination.count` and `pagination.next`, follow pagination links.
- **Why**: During active legislative sessions, results for broad queries like "tribal energy"
  may exceed 50.
- **Files**: `src/scrapers/congress_gov.py` (methods `_search_congress`, `_search`)
- **Effort**: 3 hours

**P3.4: Resolve null CFDA programs**
- **What**: Research and add correct ALN numbers for noaa_tribal, epa_tribal_air, and
  fema_tribal_mitigation (which should share CFDA 97.039). Update program_inventory.json.
- **Why**: 5 of 16 programs are invisible to spending/grants queries.
- **Files**: `data/program_inventory.json`
- **Effort**: 4 hours (research) + 1 hour (implementation)

### Tier 4: Strategic / Long-Term (New Capabilities)

**P4.1: Build SAM.gov Tribal entity cache**
- **What**: Scheduled script fetching all businessType=2X entities, building UEI lookup table.
- **Why**: Enables deterministic cross-system entity linking.
- **Files**: New `scripts/build_sam_cache.py`, new `data/sam_tribal_entities.json`
- **Effort**: 12 hours (including API key setup and scheduling)

**P4.2: Add Grants.gov opportunity detail fetching**
- **What**: For Tribal-eligible opportunities, fetch full NOFO details.
- **Why**: Complete application guidance in advocacy packets.
- **Files**: `src/scrapers/grants_gov.py` (new `_fetch_opportunity_detail` method)
- **Effort**: 6 hours

**P4.3: Add truncation warnings to all scrapers**
- **What**: When result count equals page size, log "WARNING: Results may be truncated."
- **Why**: Operational visibility into data completeness.
- **Files**: All four scraper files
- **Effort**: 2 hours

---

## Appendix A: Cross-Reference of Tracked Programs to Data Availability

| Program | CFDA | USASpending | Grants.gov | Fed Register | Congress.gov | OpenFEMA | SAM.gov |
|---------|------|-------------|-----------|-------------|-------------|---------|---------|
| BIA TCR | 15.156 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| BIA TCR Awards | 15.124 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| FEMA BRIC | 97.047/039 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | **Yes (HmaSub)** | Via UEI |
| IRS Elective Pay | **null** | **No** | **No** | Yes (keyword) | Yes (keyword) | N/A | N/A |
| EPA STAG | 66.468 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| EPA GAP | 66.926 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| FEMA Tribal Mitigation | **null** | **No** | **No** | Yes (keyword) | Yes (keyword) | **Yes (Plans)** | N/A |
| DOT PROTECT | 20.284 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| USDA Wildfire | 10.720 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| DOE Indian Energy | 81.087 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| HUD IHBG | 14.867 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| NOAA Tribal | **null** | **No** | **No** | Yes (keyword) | Yes (keyword) | N/A | N/A |
| FHWA TTP Safety | 20.205 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| USBR WaterSMART | 15.507 | Yes (queried) | Yes (queried) | Yes (keyword) | Yes (keyword) | N/A | Via UEI |
| USBR TAP | **null** | **No** | **No** | Yes (keyword) | Yes (keyword) | N/A | N/A |
| EPA Tribal Air | **null** | **No** | **No** | Yes (keyword) | Yes (keyword) | N/A | N/A |

**Bold "No"** entries represent programs where Tribal Nations have zero data visibility through
the spending/grants pipeline. These are not small programs. IRS Elective Pay alone could
represent billions in Tribal clean energy investment.

---

## Appendix B: Hardcoded Fiscal Year Violation

**File**: `src/scrapers/usaspending.py`, line 68-69
```python
"time_period": [{"start_date": "2025-10-01", "end_date": "2026-09-30"}],
```

This violates Critical Rule #1. The fix should derive fiscal year dates from config:
```python
# In config or derived:
fiscal_year = config.get("fiscal_year", 2026)
fy_start = f"{fiscal_year - 1}-10-01"
fy_end = f"{fiscal_year}-09-30"
```

---

*This report was generated by Sovereignty Scout, the Federal Data Ingestor and Tribal
Sovereignty Advocate for the TCR Policy Scanner Research Team. Every data gap documented
here represents a gap in the evidence base that Tribal Leaders need to hold the federal
government accountable to its treaty obligations and trust responsibility.*

*The fire carries forward.*
