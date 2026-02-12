# Phase 15: Congressional Intelligence Pipeline - Research

**Researched:** 2026-02-12
**Domain:** Congressional bill tracking, scraper pagination hardening, confidence scoring, DOCX enrichment
**Confidence:** HIGH (codebase patterns verified directly; API docs fetched from official sources)

## Summary

Phase 15 enriches the TCR Policy Scanner's 592-Tribe advocacy packets with congressional intelligence: bill tracking, delegation enhancement, committee activity, and confidence-scored data sections. It also hardens all 4 existing scrapers for zero-truncation pagination.

The codebase already has the foundational pieces: a `CongressGovScraper` that queries `api.congress.gov/v3` for bills by keyword, a `CongressionalMapper` that loads pre-built `congressional_cache.json` with delegation data (districts, senators, representatives, committee assignments), a `TribePacketContext` dataclass carrying congressional fields, and a full DOCX rendering pipeline with audience-differentiated section renderers. Phase 15 extends these foundations rather than replacing them.

The Congress.gov API v3 provides bill detail endpoints (sponsors, cosponsors, actions, subjects, text URLs, committees), member endpoints (sponsored/cosponsored legislation), and newly-available House roll call vote endpoints. The API requires an API key (already configured as `CONGRESS_API_KEY`), has a 5,000 requests/hour rate limit, uses offset-based pagination with max 250 results per page, and returns JSON.

**Primary recommendation:** Extend the existing `CongressGovScraper` with bill detail fetching and full pagination; add new Pydantic models in `src/schemas/models.py`; extend `TribePacketContext` with a `congressional_intel` field; add bill-section and enhanced-delegation renderers to `docx_sections.py`; implement confidence scoring as a pure-function module; and harden all 4 scrapers' scan() methods with pagination loops that assert zero truncation.

## Standard Stack

### Core (already installed, no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | >=3.9.0 | Async HTTP for Congress.gov API | Already used by all 4 scrapers |
| pydantic | >=2.0.0 | Data validation for congressional models | Already used for all data models |
| python-docx | >=1.1.0 | DOCX rendering of congressional sections | Already used for all packet assembly |
| python-dateutil | >=2.8.0 | Date parsing for freshness decay | Already installed |
| rapidfuzz | >=3.14.0 | Fuzzy matching for bill-to-program mapping | Already used for award matching |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyyaml | >=6.0.0 | Committee data from unitedstates YAML | Already used by build_congress_cache.py |
| pytest | (dev) | Test framework | All 743+ existing tests use it |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom confidence module | External ML scoring | Overkill; simple exponential decay + source weights is sufficient for 4 data sources |
| ProPublica Congress API | Congress.gov API v3 | ProPublica was deprecated/limited; Congress.gov is the authoritative source already in use |
| LegiScan API | Congress.gov API v3 | Commercial API; Congress.gov is free and already integrated |

**Installation:** No new packages required. All dependencies are already in `requirements.txt`.

## Architecture Patterns

### Existing Project Structure (directories that Phase 15 touches)

```
src/
  scrapers/
    base.py               # BaseScraper with retry, circuit breaker (EXTEND pagination)
    congress_gov.py        # CongressGovScraper (EXTEND with bill detail + pagination)
    federal_register.py    # FederalRegisterScraper (ADD pagination)
    grants_gov.py          # GrantsGovScraper (ADD pagination)
    usaspending.py         # USASpendingScraper (ALREADY has pagination in fetch_tribal_awards_*)
  packets/
    context.py             # TribePacketContext dataclass (EXTEND with congressional_intel)
    congress.py            # CongressionalMapper (EXTEND with voting/cosponsorship)
    docx_sections.py       # Section renderers (ADD bill + enhanced delegation sections)
    docx_engine.py         # DocxEngine.generate() (ADD bill section to assembly)
    orchestrator.py        # PacketOrchestrator (ADD congressional intel loading)
  schemas/
    models.py              # Pydantic models (ADD congressional intelligence models)
  graph/
    schema.py              # Graph node types (ADD BillNode, LegislatorNode)
    builder.py             # GraphBuilder (EXTEND with congressional enrichment)
config/
  scanner_config.json      # Config (ADD congressional_intel section)
scripts/
  build_congress_cache.py  # EXISTING cache builder (reference for API patterns)
data/
  congressional_intel.json # NEW: cached bill intelligence data
tests/
  test_congressional_*.py  # NEW: congressional model + pagination tests
```

### Pattern 1: Bill Detail Fetching (Sovereignty Scout)

**What:** Extend `CongressGovScraper` to fetch bill detail sub-resources after initial search.
**When to use:** INTEL-01 requires sponsors, committees, actions, subjects, text URLs.

The existing `_search_congress()` and `_search()` methods return bill list data from `/v3/bill/{congress}/{type}` endpoints. Bill detail requires separate requests to sub-endpoints.

**Example (verified against existing scraper patterns):**
```python
# Source: Existing congress_gov.py patterns + Congress.gov API v3 docs
async def _fetch_bill_detail(
    self, session, congress: int, bill_type: str, bill_number: str,
) -> dict:
    """Fetch full bill detail including sponsors, actions, committees."""
    base = f"{self.base_url}/bill/{congress}/{bill_type}/{bill_number}"

    # Parallel sub-resource fetches (using existing _request_with_retry)
    detail = await self._request_with_retry(session, "GET", base)
    bill = detail.get("bill", {})

    # Sponsors (inline in bill response)
    # Actions: /actions sub-endpoint
    actions_url = f"{base}/actions?limit=250"
    actions_data = await self._request_with_retry(session, "GET", actions_url)

    # Cosponsors: /cosponsors sub-endpoint
    cosponsors_url = f"{base}/cosponsors?limit=250"
    cosponsors_data = await self._request_with_retry(session, "GET", cosponsors_url)

    # Subjects: /subjects sub-endpoint
    subjects_url = f"{base}/subjects?limit=250"
    subjects_data = await self._request_with_retry(session, "GET", subjects_url)

    # Text URLs: /text sub-endpoint
    text_url = f"{base}/text?limit=20"
    text_data = await self._request_with_retry(session, "GET", text_url)

    return {
        "bill": bill,
        "actions": actions_data.get("actions", []),
        "cosponsors": cosponsors_data.get("cosponsors", []),
        "subjects": subjects_data.get("subjects", {}).get("legislativeSubjects", []),
        "policy_area": subjects_data.get("subjects", {}).get("policyArea", {}),
        "text_versions": text_data.get("textVersions", []),
    }
```

**Rate limit management:** At 5,000 requests/hour, fetching detail for 50 bills (each requiring ~5 sub-requests = 250 requests) is well within limits. Add 0.3s delay between bill detail fetches to stay safe.

### Pattern 2: Full Pagination with Zero Truncation (Sovereignty Scout)

**What:** Add pagination loops to all 4 scrapers' scan() methods.
**When to use:** INTEL-02 requires zero silent truncation.

**Critical gap in existing scrapers:**
- `federal_register.py`: Uses `per_page=50`, no pagination loop. Federal Register API supports `page` parameter.
- `grants_gov.py`: Uses `rows=50` or `rows=25`, no pagination loop. Grants.gov supports `startRecordNum` parameter.
- `congress_gov.py`: Uses `limit=50`, no pagination loop. Congress.gov API supports `offset` parameter with `pagination.next` URL.
- `usaspending.py`: Already has full pagination in `fetch_tribal_awards_*` methods using `page` + `hasNext`. The `scan()` method's `_fetch_obligations()` uses `limit=10` and no pagination (but this is for overview data, not Tribal awards).

**Example (verified against existing USASpending pagination pattern):**
```python
# Pattern from usaspending.py line 136-187, adapted for congress_gov.py
async def _search_congress_paginated(
    self, session, term: str, bill_type: str = "", congress: int = 119,
) -> list[dict]:
    """Search with full pagination. Zero truncation guarantee."""
    all_bills = []
    offset = 0
    limit = 250  # Congress.gov API max per page

    while True:
        params = {
            "query": term,
            "sort": "updateDate+desc",
            "limit": limit,
            "offset": offset,
        }
        endpoint = f"{self.base_url}/bill/{congress}"
        if bill_type:
            endpoint = f"{endpoint}/{bill_type}"
        url = f"{endpoint}?{urlencode(params)}"

        data = await self._request_with_retry(session, "GET", url)
        bills = data.get("bills", [])
        if not bills:
            break

        all_bills.extend(bills)

        # Check for next page via pagination object
        pagination = data.get("pagination", {})
        if not pagination.get("next"):
            break

        offset += limit

        # Safety cap: 10 pages = 2,500 bills per query is extreme
        if offset >= 2500:
            logger.warning(
                "Congress.gov: %s/%s hit 2,500 result cap for '%s'",
                congress, bill_type, term,
            )
            break

        await asyncio.sleep(0.3)

    return [self._normalize(bill) for bill in all_bills]
```

### Pattern 3: Pydantic Congressional Models (Fire Keeper)

**What:** Define Pydantic v2 models for bill intelligence, vote records, and congressional intel report.
**When to use:** INTEL-05 requires Legislator, VoteRecord, BillIntelligence, BillAction, CongressionalIntelReport.

**Follow existing model patterns in `src/schemas/models.py`:**
- Use `Field(...)` with description and examples
- Use `field_validator` for enum validation
- Use `model_validator` for cross-field checks
- Use `Optional[...]` for nullable fields
- Use `frozenset` for valid value enumerations

```python
# Source: Existing models.py patterns (lines 1-979)
class BillAction(BaseModel):
    """Single legislative action on a bill."""
    action_date: str = Field(..., description="Action date (YYYY-MM-DD)")
    text: str = Field(..., description="Action description text")
    action_type: str = Field(default="", description="Action type code")
    chamber: str = Field(default="", description="Chamber where action occurred")

class BillIntelligence(BaseModel):
    """Full intelligence record for a congressional bill."""
    bill_id: str = Field(..., description="Bill identifier (e.g., '119-HR-1234')")
    congress: int = Field(..., description="Congress number")
    bill_type: str = Field(..., description="Bill type code (HR, S, etc.)")
    bill_number: int = Field(..., description="Bill number")
    title: str = Field(..., description="Bill title")
    sponsor: Optional[dict] = Field(default=None, description="Primary sponsor info")
    cosponsors: list[dict] = Field(default_factory=list)
    cosponsor_count: int = Field(default=0, ge=0)
    actions: list[BillAction] = Field(default_factory=list)
    latest_action: Optional[BillAction] = Field(default=None)
    committees: list[dict] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    policy_area: str = Field(default="")
    text_url: str = Field(default="")
    congress_url: str = Field(default="")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_programs: list[str] = Field(default_factory=list)
    update_date: str = Field(default="")
    introduced_date: str = Field(default="")

class CongressionalIntelReport(BaseModel):
    """Aggregated congressional intelligence for a single Tribe."""
    tribe_id: str = Field(...)
    generated_at: str = Field(...)
    bills: list[BillIntelligence] = Field(default_factory=list)
    delegation_enhanced: bool = Field(default=False)
    confidence: dict = Field(default_factory=dict)
```

### Pattern 4: Confidence Scoring (Fire Keeper)

**What:** Pure-function module computing confidence scores from source weights and freshness decay.
**When to use:** INTEL-08 requires source weights x freshness decay.

**Formula (exponential decay with source weighting):**
```
confidence = source_weight * e^(-lambda * days_since_update)
```

Where:
- `source_weight`: 0.0-1.0 from scanner_config.json `authority_weight` (FR=0.9, Grants.gov=0.85, Congress.gov=0.8, USASpending=0.7)
- `lambda`: decay rate (configurable, default 0.01 = half-life ~69 days)
- `days_since_update`: days since the data point was last updated

**Confidence levels for display:**
- HIGH: >= 0.7 (data fresh and from authoritative source)
- MEDIUM: 0.4 - 0.69
- LOW: < 0.4

```python
import math
from datetime import datetime, timezone

def compute_confidence(
    source_weight: float,
    last_updated: str,
    decay_rate: float = 0.01,
    reference_date: datetime | None = None,
) -> float:
    """Compute confidence score from source weight and freshness."""
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)
    try:
        updated = datetime.fromisoformat(last_updated)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        days = max(0, (reference_date - updated).days)
    except (ValueError, TypeError):
        days = 365  # Unknown date -> assume very stale
    return round(source_weight * math.exp(-decay_rate * days), 3)

def confidence_level(score: float) -> str:
    if score >= 0.7:
        return "HIGH"
    elif score >= 0.4:
        return "MEDIUM"
    return "LOW"
```

### Pattern 5: DOCX Bill Section Rendering (Fire Keeper)

**What:** New section renderer for congressional bills in advocacy packets.
**When to use:** INTEL-07 requires congressional content in all 4 doc types.

**Follow existing render_* function signature pattern from `docx_sections.py`:**
```python
def render_bill_intelligence_section(
    document: Document,
    context: TribePacketContext,
    style_manager: StyleManager,
    doc_type_config: DocumentTypeConfig | None = None,
) -> None:
    """Render the congressional bill intelligence section.

    Per 15-CONTEXT.md decisions:
    - Doc A: Top 2-3 bills get full briefing; remaining get compact cards.
      Bills-first ordering (before delegation section).
    - Doc B: Curated subset only, facts only, zero strategy/talking points.
    - Doc C/D: Regional aggregation (Claude's discretion).
    """
```

**Key constraint from CONTEXT.md:** Bills section must appear BEFORE delegation section in Doc A. This means modifying the section ordering in `DocxEngine.generate()` (currently delegation is section 4, after executive summary).

### Pattern 6: Knowledge Graph Extension (Horizon Walker)

**What:** Add BillNode and LegislatorNode to graph schema with new edge types.
**When to use:** INTEL-14 requires congressional nodes.

**Extend existing `src/graph/schema.py` patterns:**
```python
@dataclass
class BillNode:
    """Congressional bill tracked for Tribal relevance."""
    id: str          # e.g., "bill_119_hr_1234"
    congress: int
    bill_type: str
    bill_number: int
    title: str = ""
    status: str = ""
    relevance_score: float = 0.0

@dataclass
class LegislatorNode:
    """Congressional member with Tribal advocacy relevance."""
    id: str          # bioguide_id
    name: str
    chamber: str = ""
    state: str = ""
    party: str = ""
```

**New edge types:**
- `SPONSORED_BY`: BillNode -> LegislatorNode
- `REFERRED_TO`: BillNode -> Committee (string ID)
- `AFFECTS_PROGRAM`: BillNode -> ProgramNode (with relevance_score metadata)
- `DELEGATES_TO`: TribeNode -> LegislatorNode

### Anti-Patterns to Avoid

- **Do NOT create a new scraper class for bill details.** Extend the existing `CongressGovScraper` -- bill detail is part of the Congress.gov data source, not a separate source.
- **Do NOT use python-docx section breaks between bill cards.** Per the memory: "Page breaks not section breaks between Hot Sheets (sections disrupt headers/footers)."
- **Do NOT fetch bill detail for ALL bills.** Fetch detail only for bills that pass relevance scoring (top 10-15 per scan). The detail endpoints are expensive (5+ sub-requests each).
- **Do NOT put API keys in URL query params.** Per memory and existing pattern in `congress_gov.py`, use `X-Api-Key` header.
- **Do NOT hardcode fiscal years.** Import from `src.config`.
- **Do NOT create a separate `models/congressional.py` file.** Add models to existing `src/schemas/models.py` to maintain the single-module pattern.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bill-to-program mapping | Custom keyword regex per bill | rapidfuzz matching on bill subjects/title against program keywords + CFDA references | Already proven for award matching (85+ threshold); bill subjects are CRS-assigned standardized terms |
| Exponential decay scoring | Custom decay implementation | `math.exp()` with configurable lambda | Python stdlib, 2 lines of code |
| Congressional member lookup | Re-query Congress.gov API per Tribe | Existing `congressional_cache.json` + `CongressionalMapper` | Cache already has 501/592 Tribes mapped with full member data |
| AIANNH-to-district mapping | Census geospatial processing | Existing `build_congress_cache.py` crosswalk | Already built, tested, covers 501 Tribes |
| DOCX table formatting | Raw python-docx table API | Existing `format_header_row()`, `apply_zebra_stripe()` from `docx_styles.py` | Consistent styling across all sections |
| Pagination in scrapers | Each scraper builds own loop | Extract pattern from `usaspending.py` `fetch_tribal_awards_by_year()` (page/hasNext) into shared helper or replicate per-scraper | USASpending already has the correct pagination pattern |

**Key insight:** The existing codebase already handles 80% of the congressional data pipeline. Phase 15 extends rather than replaces. The `congressional_cache.json` already has member data, committee assignments, and Tribe-to-district mappings. What's missing is live bill tracking, bill-to-program relevance scoring, and confidence computation.

## Common Pitfalls

### Pitfall 1: Congress.gov API Pagination Truncation

**What goes wrong:** Congress.gov returns max 250 results per page. Setting `limit=50` (current code) with no pagination loop silently truncates results when a query matches more than 50 bills.
**Why it happens:** The existing `_search_congress()` and `_search()` methods use a single request without checking `pagination.next`.
**How to avoid:** Every search method MUST loop on `pagination.next` until it's empty or absent. Log total count vs retrieved count.
**Warning signs:** `len(all_items)` exactly equals `limit` parameter after scan.

### Pitfall 2: Federal Register Pagination Is Different

**What goes wrong:** Federal Register API uses `page` parameter (1-indexed) and returns `total_pages` in response. It does NOT use offset/limit like Congress.gov.
**Why it happens:** Each API has its own pagination convention.
**How to avoid:** Implement per-scraper pagination appropriate to each API's convention. Do NOT try to build a generic paginator.
**Warning signs:** Response includes `total_pages > 1` but code only fetches page 1.

### Pitfall 3: Grants.gov Pagination

**What goes wrong:** Grants.gov API uses `startRecordNum` parameter for offset. Missing this silently truncates to first 50 results.
**Why it happens:** Grants.gov POST API (`/api/search2`) returns `hitCount` (total) and `oppHits` (page results). If `hitCount > rows`, there are more pages.
**How to avoid:** Loop while `len(results_so_far) < hit_count` using `startRecordNum` offset. Cap at a reasonable limit (e.g., 1000).
**Warning signs:** `hitCount` in response exceeds `len(oppHits)`.

### Pitfall 4: Rate Limiting Across Sub-Endpoints

**What goes wrong:** Fetching bill detail for 50 bills at 5 sub-requests each = 250 requests in rapid succession, potentially hitting the 5,000/hour rate limit if combined with other scraper activity.
**Why it happens:** Bill detail fetching is chattier than list endpoints.
**How to avoid:** Add `await asyncio.sleep(0.3)` between bill detail fetches. Budget rate limit: reserve 1,000 requests for bill detail out of 5,000/hour budget.
**Warning signs:** 429 responses increasing during bill detail phase.

### Pitfall 5: Audience Leakage in Bill Sections

**What goes wrong:** Doc B (congressional-facing) accidentally includes strategy language, talking points, or advocacy recommendations from the bill analysis.
**Why it happens:** Developers copy Doc A renderer and forget to strip strategic content.
**How to avoid:** Use `doc_type_config.is_congressional` guard on every strategic subsection. Per CONTEXT.md: Doc B gets "curated subset only -- facts only, zero strategy, zero talking points."
**Warning signs:** Words like "strategic", "leverage", "recommend", "talking point" appearing in Doc B output.

### Pitfall 6: python-docx Element Reuse

**What goes wrong:** Sharing OxmlElement instances across cells causes corrupt DOCX files.
**Why it happens:** python-docx XML elements are mutable singletons; assigning to a new parent detaches from old parent.
**How to avoid:** Per memory: "OxmlElement must be fresh per call (not reused across cells)." Create new formatting elements for each cell.
**Warning signs:** Missing formatting in second/third table cells.

### Pitfall 7: Windows File Encoding

**What goes wrong:** JSON files written without `encoding="utf-8"` get locale-encoded on Windows, causing UTF-8 decode errors on CI (Linux).
**Why it happens:** Python's `open()` defaults to locale encoding on Windows.
**How to avoid:** Per CLAUDE.md rule 7: "Always pass encoding='utf-8' to open() and Path.write_text() on Windows."
**Warning signs:** `UnicodeDecodeError` in CI but not local tests.

### Pitfall 8: Stale Congressional Data in Confidence Scoring

**What goes wrong:** Congressional cache data (built once) gets scored as "fresh" indefinitely because the `built_at` timestamp is from the cache build, not the underlying data.
**Why it happens:** Confusing data-build timestamp with data-currency timestamp.
**How to avoid:** Track `data_as_of` separately from `built_at`. For bills, use `updateDate`. For members, use `last_api_fetch` date. Score freshness against the data-currency date.
**Warning signs:** Confidence scores remaining at HIGH indefinitely without re-scanning.

## Code Examples

### Existing Scraper Architecture (verified from codebase)

```python
# Source: src/scrapers/base.py (lines 30-149)
# All scrapers inherit from BaseScraper which provides:
# - self._headers with User-Agent
# - self._circuit_breaker (per-source)
# - self._request_with_retry(session, method, url, **kwargs) -> dict
#   - Exponential backoff with jitter
#   - 429 rate limit handling with Retry-After header
#   - Circuit breaker integration (CLOSED/OPEN/HALF_OPEN)
#   - Config-driven retry count, backoff base, timeout
```

### Existing Congressional Cache Structure (verified from codebase)

```python
# Source: scripts/build_congress_cache.py (lines 1016-1032)
# congressional_cache.json structure:
{
    "metadata": {
        "congress_session": "119",
        "built_at": "2026-02-11T...",
        "total_members": 535,
        "total_committees": 42,
        "total_tribes_mapped": 501,
    },
    "members": {
        "C001120": {
            "bioguide_id": "C001120",
            "name": "Crenshaw, Dan",
            "state": "TX",
            "district": 2,
            "party": "Republican",
            "party_abbr": "R",
            "chamber": "House",
            "formatted_name": "Rep. Dan Crenshaw (R-TX-02)",
            "committees": [
                {
                    "committee_id": "HSAP",
                    "committee_name": "House Committee on Appropriations",
                    "role": "member",
                    "rank": 15,
                }
            ],
        }
    },
    "committees": {
        "SLIA": {
            "name": "Senate Committee on Indian Affairs",
            "chamber": "senate",
            "members": [{"bioguide_id": "...", "role": "chair", ...}],
        }
    },
    "delegations": {
        "epa_100000342": {
            "tribe_id": "epa_100000342",
            "districts": [{"district": "AZ-01", "state": "AZ", "overlap_pct": 95.2}],
            "states": ["AZ"],
            "senators": [{...}],
            "representatives": [{...}],
        }
    },
}
```

### Existing TribePacketContext (verified from codebase)

```python
# Source: src/packets/context.py (lines 1-74)
@dataclass
class TribePacketContext:
    # Identity
    tribe_id: str
    tribe_name: str
    states: list[str] = field(default_factory=list)
    ecoregions: list[str] = field(default_factory=list)
    bia_code: str = ""
    epa_id: str = ""

    # Congressional
    districts: list[dict] = field(default_factory=list)
    senators: list[dict] = field(default_factory=list)
    representatives: list[dict] = field(default_factory=list)

    # Awards + Hazards
    awards: list[dict] = field(default_factory=list)
    hazard_profile: dict = field(default_factory=dict)
    economic_impact: dict = field(default_factory=dict)

    # Metadata
    generated_at: str = ""
    congress_session: str = "119"

    # Phase 15 extension point:
    # congressional_intel: dict = field(default_factory=dict)
```

### Existing DocxEngine.generate() Section Ordering (verified from codebase)

```python
# Source: src/packets/docx_engine.py (lines 323-378)
# Current section order in generate():
# 1. Cover page
# 2. Table of contents
# 3. Executive summary
# 4. Congressional delegation  <-- Phase 15: move after bills
# 5. Hot Sheets (8-12 programs)
# 6. Hazard profile summary
# 7. Structural asks
# 8. Messaging framework (Doc A only)
# 9. Change tracking (internal only)
# 10. Appendix

# Phase 15 new ordering for Doc A:
# 1. Cover page
# 2. Table of contents
# 3. Executive summary
# 4. **Bill intelligence section** (NEW - per CONTEXT.md "bills-first")
# 5. Congressional delegation (enhanced)
# 6. Hot Sheets
# 7. Hazard profile summary
# 8. Structural asks
# 9. Messaging framework (Doc A only)
# 10. Change tracking (internal only)
# 11. Appendix
```

### Existing CI Pipeline Structure (verified from codebase)

```yaml
# Source: .github/workflows/daily-scan.yml
# Uses CONGRESS_API_KEY secret, runs python -m src.main --verbose
# Source: .github/workflows/generate-packets.yml
# Uses CONGRESS_API_KEY + SAM_API_KEY, runs --prep-packets --all-tribes
# Both already have the CONGRESS_API_KEY secret configured
```

### Congress.gov API v3 Endpoint Map (verified from official docs)

```
# Bill endpoints:
GET /v3/bill                                    # List all bills
GET /v3/bill/{congress}                         # Bills by Congress
GET /v3/bill/{congress}/{type}                  # Bills by Congress + type
GET /v3/bill/{congress}/{type}/{number}         # Bill detail
GET /v3/bill/{congress}/{type}/{number}/actions  # Bill actions
GET /v3/bill/{congress}/{type}/{number}/cosponsors  # Cosponsors
GET /v3/bill/{congress}/{type}/{number}/subjects    # Subjects
GET /v3/bill/{congress}/{type}/{number}/text        # Text versions
GET /v3/bill/{congress}/{type}/{number}/committees  # Committee referrals

# Member endpoints:
GET /v3/member                                  # List all members
GET /v3/member/congress/{congress}              # Members by Congress
GET /v3/member/{bioguideId}                     # Member detail
GET /v3/member/{bioguideId}/sponsored-legislation     # Sponsored bills
GET /v3/member/{bioguideId}/cosponsored-legislation   # Cosponsored bills

# Committee endpoints:
GET /v3/committee/{chamber}/{systemCode}        # Committee detail
GET /v3/committee/{chamber}/{systemCode}/bills  # Committee bills

# Authentication: X-Api-Key header (NOT query param)
# Rate limit: 5,000 requests/hour
# Pagination: offset + limit (max 250 per page)
# Response: pagination.next URL indicates more pages
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ProPublica Congress API | Congress.gov API v3 | ProPublica wound down | Use official LOC API; already integrated |
| Query-param API keys | Header-based API keys (`X-Api-Key`) | Security best practice | Prevents key leakage in logs/referer |
| Single-page scraping | Full pagination with truncation detection | Phase 15 | Zero silent data loss |
| Static delegation-only packets | Bill intelligence + delegation | Phase 15 | Actionable intelligence for Tribal Leaders |
| No data confidence indicators | Source weight x freshness decay | Phase 15 | Leaders know how current their data is |

**Deprecated/outdated:**
- **ProPublica Congress API**: No longer maintained as a public API. Use Congress.gov API v3.
- **Senate roll call votes API**: Not yet available in Congress.gov API v3. House roll call votes are beta (118th Congress onward, May 2025). Senate voting records must use alternative sources or be deferred.

## Open Questions

1. **Senate Vote Records**
   - What we know: Congress.gov API v3 added House roll call votes in May 2025 (beta, 118th Congress+). Senate votes are NOT yet available in the API.
   - What's unclear: Whether Senate votes will be added to the API, and on what timeline.
   - Recommendation: For INTEL-04 (voting records), implement House vote fetching from the API and note Senate votes as "pending API availability." Alternatively, use the Senate.gov XML vote data (not via Congress.gov API) as a supplemental source, but this adds complexity. **Recommend deferring Senate voting records to a future phase** unless the existing unitedstates/congress-legislators YAML already includes vote data (it does not -- it only has membership data).

2. **Bill-to-Program Relevance Scoring Threshold**
   - What we know: Existing relevance scoring uses weights (program_match=0.35, keyword_density=0.20, recency=0.10, source_authority=0.15, action_relevance=0.20) with a 0.30 threshold. Bill-to-program mapping should use a similar weighted approach.
   - What's unclear: The exact threshold for bill relevance. Too low = noise; too high = missed bills.
   - Recommendation: Start with 0.30 (matching existing threshold), tune based on test data. Bill relevance factors: (1) bill subjects overlap with program keywords, (2) bill sponsor is in Tribe's delegation, (3) bill referred to relevant committee (SLIA, HSII, etc.), (4) bill text mentions CFDA numbers.

3. **Congressional Intel Cache Location**
   - What we know: Awards use `data/award_cache/{tribe_id}.json`, hazards use `data/hazard_profiles/{tribe_id}.json`. Congressional intel could follow the same per-Tribe pattern or use a single `data/congressional_intel.json`.
   - What's unclear: Whether to use per-Tribe files or a single aggregated file.
   - Recommendation: Use a **single** `data/congressional_intel.json` file, NOT per-Tribe. Bills are shared across Tribes (many Tribes may be affected by the same bill). Per-Tribe caching would duplicate bill data 592 times. The aggregated file contains all tracked bills with their relevance data; the orchestrator filters per-Tribe at render time based on the Tribe's state, programs, and delegation.

4. **Confidence Indicator Visual Treatment**
   - What we know: CONTEXT.md gives Claude's discretion on confidence presentation.
   - What's unclear: Whether to use inline badges (like CI_STATUS_LABELS), separate column, or section header.
   - Recommendation: Use inline badges after section titles, matching the existing CI status badge pattern: `[HIGH]`, `[MEDIUM]`, `[LOW]` in small gray font. This is consistent with the existing `CI_STATUS_LABELS` rendering in `docx_sections.py`.

## Sources

### Primary (HIGH confidence)
- Congress.gov API v3 GitHub repository: https://github.com/LibraryOfCongress/api.congress.gov - Bill, Member, Committee endpoint docs
- Congress.gov API README: https://github.com/LibraryOfCongress/api.congress.gov/blob/main/README.md - Rate limits, pagination, auth
- LOC Blog: https://blogs.loc.gov/law/2025/05/introducing-house-roll-call-votes-in-the-congress-gov-api/ - House votes beta
- Existing codebase: `src/scrapers/congress_gov.py`, `src/packets/congress.py`, `scripts/build_congress_cache.py`, `src/schemas/models.py`, `src/packets/docx_sections.py`, `src/packets/docx_engine.py` - All patterns verified directly from source

### Secondary (MEDIUM confidence)
- Congress.gov API LOC page: https://www.loc.gov/apis/additional-apis/congress-dot-gov-api/ - Endpoint coverage overview
- Exponential decay scoring: https://arxiv.org/html/2509.19376 - Recency prior patterns (2025 paper)

### Tertiary (LOW confidence)
- Senate vote availability: Based on absence from official docs and blog post focus on House only. May have changed since research date.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies; all libraries already installed and proven in codebase
- Architecture: HIGH - All patterns extend existing, verified codebase structures (scrapers, models, DOCX renderers, graph)
- API endpoints: HIGH - Verified against official GitHub documentation from Library of Congress
- Pagination patterns: HIGH - Existing USASpending pagination is a proven template; API pagination conventions verified from official docs
- Confidence scoring: HIGH - Exponential decay is well-established math; implementation is trivial
- Senate votes: LOW - Not yet in Congress.gov API v3; timeline unknown
- Bill relevance threshold: MEDIUM - Reasonable starting point (0.30) but will need empirical tuning

**Research date:** 2026-02-12
**Valid until:** 2026-03-14 (30 days -- Congress.gov API is stable; codebase patterns won't change)
