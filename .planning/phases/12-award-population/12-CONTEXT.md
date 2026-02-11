# Phase 12: Award Population - Context

**Gathered:** 2026-02-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Populate 592 Tribal award cache files with real USASpending data queried by CFDA number. Two-tier name matching (alias table + rapidfuzz) links recipients to Tribes. Target: 450+ Tribes with at least one non-zero award record. This phase builds the data; pipeline integration and economic impact computation are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Fiscal year scope
- 5-year window: FY22 through FY26 (captures full IIJA era)
- Dynamic fiscal year boundaries via config (not hardcoded year strings)
- Cache files store both total obligation AND year-by-year breakdown for trend display
- Include all financial assistance types (grants, cooperative agreements, direct payments) -- not just grants

### No-CFDA programs
- IRS Elective Pay (no CFDA) is skipped in award queries
- Packet acknowledges Elective Pay is not trackable via spending data
- 11 unique CFDA batch queries cover the remaining 15 programs (some share CFDAs)

### Name matching strategy
- Two-tier: curated alias table first, rapidfuzz fallback at >= 85 score
- Alias table seeded from EPA registry canonical names, then enriched with discovered USASpending recipient name variants
- Auto-accept all matches at >= 85 (no manual review tier)
- Consortium/inter-Tribal org awards logged separately but NOT attributed to individual member Tribes in v1.2

### Unmatched award handling
- Drop silently -- if it doesn't match after both tiers, it's not a Tribal recipient we track
- No sub-award checking for state pass-through funds (too indirect to attribute reliably)
- Same "first-time applicant opportunity" message for all zero-award Tribes (no differentiation between genuine zeros and matching gaps)

### Deduplication
- Deduplicate by USASpending award ID (unique key)

### Cache update lifecycle
- One-shot standalone script for v1.2 (pipeline integration deferred to future version)
- Full overwrite on re-run (no merge logic -- fresh pull every time)
- Console summary + JSON report output (machine-readable for Phase 14 validation)
- Optional `--tribe` flag for single-Tribe debugging (default: all 592)

### Claude's Discretion
- Exact USASpending API endpoint selection and pagination strategy
- Alias table file format and storage location
- Batch query parallelization approach
- Error handling and retry behavior for USASpending API calls
- JSON report schema and location

</decisions>

<specifics>
## Specific Ideas

- Year-by-year breakdown enables trend analysis in packets: "funding is growing" vs "funding is declining" narrative
- Consortium awards should be captured (not lost) even though they're not attributed -- future version can build the membership mapping
- Script should feel like a standalone tool: run it, get a report, inspect the results

</specifics>

<deferred>
## Deferred Ideas

- Consortium-to-member-Tribe attribution (requires curated membership mapping) -- future version
- Sub-award checking for state pass-through funds -- future version
- Pipeline integration (award freshness checking, scheduled re-queries) -- future version
- Differentiated no-match messaging (genuine zero vs matching gap) -- future version

</deferred>

---

*Phase: 12-award-population*
*Context gathered: 2026-02-11*
