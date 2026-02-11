# Phase 12: Award Population - Research

**Researched:** 2026-02-11
**Domain:** USASpending API batch querying, Tribal name fuzzy matching, award cache population
**Confidence:** HIGH (existing code verified + API behavior confirmed)

## Summary

Phase 12 populates 592 Tribal award cache files with real USASpending data. The existing codebase already contains the core infrastructure: `src/scrapers/usaspending.py` with `fetch_tribal_awards_for_cfda()` and `fetch_all_tribal_awards()`, plus `src/packets/awards.py` with `TribalAwardMatcher` (two-tier matching + cache writer). The CONTEXT decisions require extending this to a 5-year window (FY22-FY26), adding year-by-year breakdowns, expanding award_type_codes to include direct payments (codes 06/10), fixing 2 missing CFDA mappings, and building a standalone script with CLI and JSON report output.

The USASpending API has a **10,000 record hard limit** per query. This is manageable because querying per-CFDA with `recipient_type_names: ["indian_native_american_tribal_government"]` naturally limits results to a few hundred per CFDA. The 5-year time window could increase result counts, so year-by-year querying per CFDA is the safe approach (14 CFDAs x 5 years = 70 queries, well within practical limits).

The alias table (`data/tribal_aliases.json`) has 3,751 entries covering all 592 Tribes at 6.3 aliases average. The rapidfuzz (v3.14.3) `token_sort_ratio` with score >= 85 threshold correctly rejects false positives between similar Tribes (e.g., Cherokee Nation vs Eastern Band of Cherokee Indians scores 55) while catching exact-match variants. State-overlap validation provides an additional anti-false-positive guard. The 85 threshold may miss some long-suffix USASpending names (e.g., "TURTLE MOUNTAIN BAND OF CHIPPEWA INDIANS OF NORTH DAKOTA" scores only 83 against the EPA name), so the alias table enrichment step after first API pull is critical.

**Primary recommendation:** Use the existing `TribalAwardMatcher` and `USASpendingScraper` as the foundation. Extend with per-fiscal-year querying, expanded award_type_codes, year-by-year breakdown in cache schema, and wrap in a standalone CLI script with JSON reporting.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | 3.x | Async HTTP client for USASpending API | Already used by all scrapers |
| rapidfuzz | 3.14.3 | Fuzzy string matching (Tier 2) | Already a project dependency, confirmed working |
| asyncio | stdlib | Async orchestration | Standard for Python async |
| json | stdlib | Cache file I/O | Standard |
| argparse | stdlib | CLI argument parsing for standalone script | Standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | File path operations | All path construction via src.paths |
| logging | stdlib | Structured logging | All modules |
| collections.Counter | stdlib | Statistics aggregation | Coverage reporting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rapidfuzz token_sort_ratio | rapidfuzz WRatio | WRatio is more versatile but less predictable; token_sort_ratio better for "same words, different order" which is the actual Tribal name matching pattern |
| Per-year queries | Single 5-year query | Single query risks hitting 10K limit on popular CFDAs; per-year is safer and enables year-by-year breakdown naturally |
| process.extract | Manual loop | process.extract/cdist is faster for batch matching but existing code already uses manual loop with state validation; keep consistent |

**Installation:**
```bash
# No new dependencies -- all already in requirements.txt
pip install -r requirements.txt
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  scrapers/
    usaspending.py       # EXTEND: add 5-year window, expanded award_type_codes, 2 missing CFDAs
  packets/
    awards.py            # EXTEND: year-by-year breakdown in cache schema, enrichment loop
scripts/
  populate_awards.py     # NEW: standalone CLI script
  build_tribal_aliases.py  # EXISTS: alias table builder (may need enrichment hook)
data/
  tribal_aliases.json    # EXISTS: 3,751 aliases for 592 Tribes
  award_cache/           # EXISTS: 592 placeholder JSON files to be populated
```

### Pattern 1: CFDA-per-Year Batch Query Strategy
**What:** Query USASpending API once per (CFDA, fiscal_year) pair rather than once per CFDA with a wide time window.
**When to use:** Always for this phase (avoids 10K record limit, enables year-by-year breakdown).
**Example:**
```python
# Source: Verified against existing src/scrapers/usaspending.py + CONTEXT decisions
async def fetch_tribal_awards_by_year(
    self, session: aiohttp.ClientSession, cfda: str, fy: int,
) -> list[dict]:
    """Fetch Tribal awards for a single CFDA in a single fiscal year."""
    fy_start = f"{fy - 1}-10-01"
    fy_end = f"{fy}-09-30"
    payload = {
        "filters": {
            "award_type_codes": ["02", "03", "04", "05", "06", "10"],  # Grants + direct payments
            "program_numbers": [cfda],
            "recipient_type_names": ["indian_native_american_tribal_government"],
            "time_period": [{"start_date": fy_start, "end_date": fy_end}],
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount",
            "Total Obligation", "Start Date", "End Date",
            "Description", "CFDA Number", "Awarding Agency", "recipient_id",
        ],
        "subawards": False,
        "page": 1,
        "limit": 100,
        "sort": "Award Amount",
        "order": "desc",
    }
    # ... pagination loop (existing pattern from fetch_tribal_awards_for_cfda)
```

### Pattern 2: Two-Tier Matching with Enrichment
**What:** After first API pull, collect all unmatched recipient names and analyze for alias table enrichment opportunities.
**When to use:** During the "bootstrap" phase of award population and periodically when re-running.
**Example:**
```python
# After match_all_awards(), export unmatched names for alias enrichment
unmatched_names = []
for cfda, awards in awards_by_cfda.items():
    for award in awards:
        recipient = award.get("Recipient Name", "")
        if not matcher.match_recipient_to_tribe(recipient):
            unmatched_names.append({
                "recipient_name": recipient,
                "cfda": cfda,
                "obligation": award.get("Total Obligation", 0),
            })
# Log/report unmatched for manual review and alias table enrichment
```

### Pattern 3: Enhanced Cache Schema with Year-by-Year Breakdown
**What:** Cache files include per-fiscal-year obligation breakdowns alongside the flat award list.
**When to use:** All cache writes (enables trend analysis in packets).
**Example:**
```python
# Source: CONTEXT decision on year-by-year breakdown
cache_data = {
    "tribe_id": tribe_id,
    "tribe_name": tribe["name"],
    "fiscal_year_range": {"start": 2022, "end": 2026},
    "awards": awards,  # flat list of all awards across years
    "total_obligation": total_obligation,
    "award_count": len(awards),
    "cfda_summary": cfda_summary,
    "yearly_obligations": {
        "FY22": sum_for_fy(awards, 2022),
        "FY23": sum_for_fy(awards, 2023),
        "FY24": sum_for_fy(awards, 2024),
        "FY25": sum_for_fy(awards, 2025),
        "FY26": sum_for_fy(awards, 2026),
    },
    "trend": "increasing" | "decreasing" | "stable" | "new" | "none",
}
```

### Pattern 4: Deduplication by Award ID
**What:** USASpending award IDs are unique keys. Deduplicate across fiscal year queries (a multi-year award may appear in multiple year queries).
**When to use:** After fetching all data, before matching.
**Example:**
```python
seen_award_ids: set[str] = set()
deduped: list[dict] = []
for award in all_awards:
    aid = award.get("Award ID", "")
    if aid and aid not in seen_award_ids:
        seen_award_ids.add(aid)
        deduped.append(award)
```

### Anti-Patterns to Avoid
- **Querying per-Tribe (592 queries):** The CONTEXT explicitly calls for CFDA-based batching. 14 CFDAs x 5 years = 70 queries, not 592.
- **Hardcoding fiscal years:** Use `src.config.FISCAL_YEAR_INT` and compute FY22 as `FISCAL_YEAR_INT - 4`. Never string-literal "FY26".
- **Merging old cache data:** CONTEXT says full overwrite on re-run. No merge logic.
- **Attributing consortium awards to member Tribes:** CONTEXT defers this to a future version. Log them separately.
- **Using `process.extract` without state validation:** The manual loop in `TribalAwardMatcher.match_recipient_to_tribe()` includes state-overlap validation that `process.extract` doesn't support natively. Keep the manual approach for correctness.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Alias table generation | Manual CSV parsing | `scripts/build_tribal_aliases.py` | Already generates 3,751 aliases from registry with state-stripping, parenthetical handling, etc. |
| USASpending API retry/backoff | Custom retry logic | `BaseScraper._request_with_retry()` | Handles 429 rate limits, exponential backoff, configurable retries |
| Tribal registry lookup | Custom name indexing | `src/packets/registry.TribalRegistry` | Lazy-loading, 3-tier resolution, cached search corpus |
| Path construction | String concatenation | `src/paths.award_cache_path(tribe_id)` | Centralized, cross-platform, consistent |
| Fiscal year math | Hardcoded dates | `src/config.FISCAL_YEAR_INT`, `FISCAL_YEAR_START`, `FISCAL_YEAR_END` | Dynamic, computed from October 1 boundary |
| Dollar formatting | f-string formatting | `src.utils.format_dollars()` | Project-wide standard (Critical Rule #2) |

**Key insight:** The existing codebase already has 80% of the infrastructure for this phase. The work is primarily about extending `USASpendingScraper` to support per-year queries, extending `TribalAwardMatcher.write_cache()` for the enhanced schema, and wrapping everything in a standalone CLI script.

## Common Pitfalls

### Pitfall 1: USASpending 10,000 Record Hard Limit
**What goes wrong:** A single query for a popular CFDA across 5 years could exceed 10,000 results, silently truncating data.
**Why it happens:** The API has an undocumented 10K ceiling. Pagination works up to page 100 x limit 100.
**How to avoid:** Query per (CFDA, fiscal_year) pair, not per CFDA with a 5-year window. Each individual query should return well under 10K results for Tribal-filtered data.
**Warning signs:** `page_metadata.hasNext` still True at page 100, or result count exactly 10,000.

### Pitfall 2: Award Deduplication Across Years
**What goes wrong:** Multi-year awards (especially cooperative agreements) span fiscal years. The same Award ID may appear in FY24 and FY25 queries, inflating totals.
**Why it happens:** USASpending returns awards active during the queried time period, not just those started in that period.
**How to avoid:** Deduplicate by Award ID across all fetched results before matching. Use start_date to assign awards to their originating fiscal year for the yearly breakdown.
**Warning signs:** Total obligation for a Tribe seems implausibly high; same Award ID appears multiple times in the flat awards list.

### Pitfall 3: False Positive Fuzzy Matches Between Similar Tribes
**What goes wrong:** "Seneca Nation of Indians" matches to "Seneca-Cayuga Nation" instead of staying as the correct Seneca Nation.
**Why it happens:** Tribal names share common words ("Nation", "Indians", "Band", "Tribe"). Without state validation, the wrong Tribe could win.
**How to avoid:** The existing code already has state-overlap validation (recipient state must match Tribe's states). Keep this guard active. The 85 threshold also rejects most cross-Tribe matches (verified: Seneca vs Seneca-Cayuga scores 59).
**Warning signs:** Coverage report shows awards assigned to Tribes in unexpected states.

### Pitfall 4: Alaska Native Village Naming Variations
**What goes wrong:** 229 Alaska Native villages (39% of registry) have naming patterns that differ from lower-48 Tribes. USASpending may use "NATIVE VILLAGE OF BARROW INUPIAT TRADITIONAL GOVERNMENT" while registry has "Native Village of Barrow".
**Why it happens:** Alaska Native entities use distinctive naming patterns (Native Village of X, Village of X, X Traditional Council) that get extended in USASpending with additional descriptors.
**How to avoid:** The alias table already includes alternate names from the registry. After first API pull, analyze unmatched Alaska names and enrich the alias table with discovered USASpending variants.
**Warning signs:** Coverage analysis shows disproportionately low matching rate for Alaska Tribes vs lower-48.

### Pitfall 5: Consortium and Inter-Tribal Organization Awards
**What goes wrong:** "INTER TRIBAL COUNCIL OF ARIZONA" or "NORTHWEST PORTLAND AREA INDIAN HEALTH BOARD" receives large awards that don't map to any single Tribe.
**Why it happens:** Many federal programs fund inter-Tribal organizations that serve multiple member Tribes.
**How to avoid:** Per CONTEXT decision, log consortium awards separately but do NOT attribute to individual member Tribes. Check if recipient_name contains patterns like "inter tribal", "consortium", "council of", "intertribal".
**Warning signs:** Large unmatched awards with consortium-pattern names.

### Pitfall 6: Missing CFDA Mappings
**What goes wrong:** Awards under CFDA 11.483 (NOAA Tribal) and 66.038 (EPA Tribal Air) are never fetched because they're not in `CFDA_TO_PROGRAM`.
**Why it happens:** The scraper's `CFDA_TO_PROGRAM` map has 12 entries but the program inventory has 14 unique CFDAs.
**How to avoid:** Add the 2 missing CFDAs to the map: `"11.483": "noaa_tribal"` and `"66.038": "epa_tribal_air"`.
**Warning signs:** Programs NOAA Tribal and EPA Tribal Air always show zero awards across all Tribes.

### Pitfall 7: Windows File Encoding
**What goes wrong:** JSON cache files written without `encoding="utf-8"` corrupt Tribal names with non-ASCII characters (diacritics in some Tribal names).
**Why it happens:** Windows default encoding is locale-dependent (often cp1252).
**How to avoid:** Always pass `encoding="utf-8"` to `open()` calls. The existing code already does this correctly.
**Warning signs:** Garbled characters in Tribe names when reading cache files.

### Pitfall 8: Award Type Code Expansion
**What goes wrong:** Only querying grant codes (02-05) misses direct payments (06, 10) that some programs use.
**Why it happens:** CONTEXT explicitly says "Include all financial assistance types (grants, cooperative agreements, direct payments)".
**How to avoid:** Expand `award_type_codes` to `["02", "03", "04", "05", "06", "10"]`. Exclude loans (07, 08), insurance (09), and other (11) as they don't apply to these programs.
**Warning signs:** Programs known to use direct payments show zero awards.

## Code Examples

Verified patterns from the existing codebase:

### Existing Scraper Fetch Pattern (confirmed working)
```python
# Source: src/scrapers/usaspending.py lines 94-169
async def fetch_tribal_awards_for_cfda(
    self, session: aiohttp.ClientSession, cfda: str,
) -> list[dict]:
    url = f"{self.base_url}/search/spending_by_award/"
    all_results: list[dict] = []
    page = 1
    while True:
        payload = {
            "filters": {
                "award_type_codes": ["02", "03", "04", "05"],
                "program_numbers": [cfda],
                "recipient_type_names": ["indian_native_american_tribal_government"],
            },
            "fields": [...],
            "subawards": False,
            "page": page,
            "limit": 100,
            "sort": "Award Amount",
            "order": "desc",
        }
        data = await self._request_with_retry(session, "POST", url, json=payload)
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if not data.get("page_metadata", {}).get("hasNext", False):
            break
        page += 1
    return all_results
```

### Existing Two-Tier Matching (confirmed working)
```python
# Source: src/packets/awards.py lines 100-177
def match_recipient_to_tribe(self, recipient_name, recipient_state=None):
    normalized = recipient_name.strip().lower()
    # Tier 1: Alias table (O(1))
    tribe_id = self.alias_table.get(normalized)
    if tribe_id:
        return self.registry.get_by_id(tribe_id)
    # Tier 2: rapidfuzz token_sort_ratio >= 85 + state validation
    for tribe in self.registry.get_all():
        for name in [tribe["name"]] + tribe.get("alternate_names", []):
            score = fuzz.token_sort_ratio(normalized, name.lower())
            if score >= self.fuzzy_threshold:
                if recipient_state and tribe.get("states"):
                    if recipient_state.upper() not in tribe["states"]:
                        continue
                # Track best match...
    return best_match
```

### Existing Cache Write Pattern (to be extended)
```python
# Source: src/packets/awards.py lines 248-303
def write_cache(self, matched_awards: dict[str, list[dict]]) -> int:
    self.cache_dir.mkdir(parents=True, exist_ok=True)
    for tribe in self.registry.get_all():
        tribe_id = tribe["tribe_id"]
        awards = matched_awards.get(tribe_id, [])
        cache_data = {
            "tribe_id": tribe_id,
            "tribe_name": tribe["name"],
            "awards": awards,
            "total_obligation": sum(a.get("obligation", 0.0) for a in awards),
            "award_count": len(awards),
            "cfda_summary": cfda_summary,
        }
        # ... write JSON
```

### Standalone Script CLI Pattern (to be built)
```python
# Source: Pattern from scripts/build_tribal_aliases.py
#!/usr/bin/env python3
"""Populate award cache files from USASpending API.

Usage:
    python scripts/populate_awards.py              # All 592 Tribes
    python scripts/populate_awards.py --tribe epa_100000001  # Single Tribe debug
    python scripts/populate_awards.py --dry-run    # Fetch + match but don't write
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import FISCAL_YEAR_INT
from src.paths import SCANNER_CONFIG_PATH

def main():
    parser = argparse.ArgumentParser(description="Populate award cache from USASpending")
    parser.add_argument("--tribe", help="Single tribe_id for debugging")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and match but don't write")
    parser.add_argument("--report", default="outputs/award_population_report.json",
                        help="Path for JSON summary report")
    args = parser.parse_args()
    # ... load config, create scraper + matcher, run, write report
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CFDA (Catalog of Federal Domestic Assistance) | ALN (Assistance Listing Number) | 2018 (SAM.gov migration) | Same numbers, new name. USASpending API still uses `program_numbers` and `CFDA Number` field names |
| Single FY query | Multi-year window | Phase 12 decision | 5-year view enables trend analysis |
| Grants only (02-05) | All financial assistance (02-06, 10) | Phase 12 decision | Captures direct payments to Tribes |
| Full overwrite cache | Full overwrite (unchanged) | v1.2 | No merge logic needed -- simplifies implementation |

**Deprecated/outdated:**
- CFDA terminology: The government has migrated to "Assistance Listing Number" (ALN) but USASpending API still uses CFDA-based field names. No code changes needed.

## Key Quantitative Findings

| Metric | Value | Source | Confidence |
|--------|-------|--------|------------|
| Total Tribes in registry | 592 | data/tribal_registry.json | HIGH |
| Alaska Native entities | 229 (39%) | Registry analysis | HIGH |
| Lower-48 Tribes | 363 (61%) | Registry analysis | HIGH |
| Alias table entries | 3,751 | data/tribal_aliases.json | HIGH |
| Average aliases per Tribe | 6.3 | Alias analysis | HIGH |
| Tribes with <=2 aliases | 157 (27%) | Alias analysis | HIGH |
| CFDAs in program inventory | 14 unique | data/program_inventory.json | HIGH |
| CFDAs in scraper map | 12 | src/scrapers/usaspending.py | HIGH |
| Missing CFDA mappings | 2 (11.483, 66.038) | Comparison analysis | HIGH |
| API max results per query | 10,000 | Community forum reports | MEDIUM |
| API max page size | 100 | API contract docs | HIGH |
| Total queries needed | ~70 (14 CFDAs x 5 FYs) | Computed | HIGH |
| Target coverage | 450+ of 592 | CONTEXT decision | HIGH |
| rapidfuzz version | 3.14.3 | pip check | HIGH |
| Fuzzy threshold | 85 (token_sort_ratio) | CONTEXT decision | HIGH |

### Fuzzy Match Score Analysis (verified with rapidfuzz 3.14.3)

| EPA Name | USASpending Name | Score | Decision |
|----------|-----------------|-------|----------|
| Navajo Nation | THE NAVAJO NATION | 87 | MATCH (alias table would catch first) |
| Muckleshoot Indian Tribe | MUCKLESHOOT INDIAN TRIBE | 100 | MATCH |
| Quinault Indian Nation | QUINAULT INDIAN NATION | 100 | MATCH |
| Turtle Mountain Band of Chippewa Indians | TURTLE MOUNTAIN BAND OF CHIPPEWA INDIANS OF NORTH DAKOTA | 83 | MISS (needs alias) |
| Confederated Tribes of Warm Springs | THE CONFEDERATED TRIBES OF THE WARM SPRINGS RESERVATION OF OREGON | 70 | MISS (needs alias) |
| Standing Rock Sioux Tribe | STANDING ROCK SIOUX TRIBE OF NORTH AND SOUTH DAKOTA | 66 | MISS (needs alias) |
| Cherokee Nation | Eastern Band of Cherokee Indians | 55 | CORRECT REJECT |
| Seneca Nation of Indians | Seneca-Cayuga Nation | 59 | CORRECT REJECT |
| Crow Tribe of Montana | Crow Creek Sioux Tribe | 56 | CORRECT REJECT |
| Navajo Nation | NAVAJO TRIBAL UTILITY AUTHORITY | 45 | CORRECT REJECT (consortium) |

**Analysis:** The 85 threshold correctly rejects all cross-Tribe false positives tested (max 59). However, legitimate long-suffix variants score 66-83, below threshold. The alias table must cover these. The `build_tribal_aliases.py` script already strips state suffixes and generates variants, handling most of these cases. The critical enrichment step is to feed USASpending recipient names back into the alias table after the first API pull.

## Coverage Feasibility Analysis

**Target:** 450+ of 592 Tribes with at least one non-zero award.

**Feasibility assessment: ACHIEVABLE (HIGH confidence)**

Rationale:
- 16 programs span transportation (FHWA TTP), housing (HUD IHBG), environment (EPA GAP, STAG), energy (DOE), and resilience (BIA TCR, FEMA)
- HUD IHBG is a formula program -- nearly all federally recognized Tribes receive it
- EPA GAP is broadly distributed to most Tribes for base environmental capacity
- FHWA TTP (Tribal Transportation Program) is formula-based under 23 U.S.C. 202
- Combined, these three programs alone likely cover 400+ Tribes
- Adding BIA TCR, DOE Indian Energy, and competitive programs extends coverage further
- 5-year window (FY22-FY26) increases likelihood any Tribe received at least one award

**Risk factors for coverage gaps:**
- Tribes that primarily receive funding through state pass-through (not tracked)
- Very small Tribes or newly recognized Tribes
- Alaska Native villages that receive funding primarily through regional organizations
- Consortium-funded Tribes (awards not attributed per CONTEXT decision)

## Open Questions

Things that couldn't be fully resolved:

1. **Exact USASpending API rate limit**
   - What we know: The API is free, no API key required. It has a 10,000 record ceiling per query. The existing scraper uses 0.5s delay between requests without issues.
   - What's unclear: Official rate limit (requests/second or requests/minute) is not documented. The existing code's 0.3-0.5s delay has been sufficient.
   - Recommendation: Keep 0.5s delay between requests. Add exponential backoff on 429 responses (already in BaseScraper). For 70 queries, total request time is ~35 seconds minimum plus response time -- very manageable.

2. **Completeness of `recipient_type_names` filter**
   - What we know: `"indian_native_american_tribal_government"` is used in the existing scraper and appears to work for filtering Tribal recipients.
   - What's unclear: Whether this filter catches ALL Tribal awards or if some awards are classified under other recipient types (e.g., "other_than_small_business" for Alaska Native Corporations).
   - Recommendation: Use the filter as-is. Alaska Native Corporations (business entities under ANCSA) may appear under different recipient types, but they are not federally recognized Tribal governments in our registry anyway.

3. **Award deduplication edge cases**
   - What we know: Award IDs are unique identifiers in USASpending. Multi-year awards may appear in multiple fiscal year queries.
   - What's unclear: Whether the "Award ID" field is always populated and always unique across fiscal years, or if some awards use different ID formats.
   - Recommendation: Deduplicate by Award ID. If Award ID is empty (edge case), use a composite key of (recipient_name + cfda + obligation + start_date).

## Sources

### Primary (HIGH confidence)
- `src/scrapers/usaspending.py` - Existing USASpending scraper with fetch_tribal_awards_for_cfda()
- `src/packets/awards.py` - Existing TribalAwardMatcher with two-tier matching
- `src/packets/registry.py` - TribalRegistry with lazy loading and 3-tier resolution
- `scripts/build_tribal_aliases.py` - Alias table builder
- `data/tribal_aliases.json` - 3,751 aliases covering 592 Tribes
- `data/tribal_registry.json` - 592 Tribe registry with alternate names
- `data/program_inventory.json` - 16 programs with CFDA numbers
- `config/scanner_config.json` - Awards config (alias_path, cache_dir, fuzzy_threshold)
- `12-CONTEXT.md` - User decisions for Phase 12

### Secondary (MEDIUM confidence)
- [USASpending API Contract - spending_by_award.md](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md) - Endpoint specification
- [USASpending API Search Filters](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/search_filters.md) - Filter documentation
- [Award Type Codes Whitepaper](https://fedspendingtransparency.github.io/whitepapers/types/) - Financial assistance type codes 02-11
- [Power Platform forum on 10K limit](https://community.powerplatform.com/forums/thread/details/?threadid=41cab5ba-a74a-ef11-a317-000d3a15433f) - 10,000 record hard limit confirmation

### Tertiary (LOW confidence)
- General web search on Alaska Native entity naming patterns - informational but not authoritative
- RapidFuzz documentation via web search - verified against local installation (v3.14.3)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, versions confirmed
- Architecture: HIGH - Existing code provides 80% of infrastructure; patterns verified with real data
- Pitfalls: HIGH - Fuzzy matching edge cases verified with real rapidfuzz scores; API limits confirmed from multiple sources
- Coverage feasibility: MEDIUM - Based on program distribution knowledge; actual coverage depends on API data

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (30 days -- USASpending API is stable; no major changes expected)
