# Phase 6: Data Acquisition - Context

**Gathered:** 2026-02-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Fetch and cache per-Tribe USASpending award histories and climate hazard profiles (FEMA NRI + USFS wildfire) so that any Tribe's funding track record and top climate risks can be retrieved without API calls at DOCX generation time. Covers all 592 Tribes from the registry built in Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Award match handling
- Borderline fuzzy matches (85-90 score range): Claude's discretion on threshold tuning based on data quality analysis
- Alias table curation approach: Claude's discretion -- bootstrap from data patterns, manual review, or registry variants as appropriate
- No confidence metadata in cached results -- if a match passes the threshold, treat it as authoritative (no "verified" vs "approximate" distinction in cache files)
- Zero-match Tribes get a cache file with empty awards array plus a `no_awards_context` field providing advocacy framing (e.g., "No federal awards found -- first-time applicant opportunity")

### Claude's Discretion
- Borderline match threshold tuning (exact cutoff within the >= 85 framework)
- Alias table curation methodology (data-driven bootstrap vs known variants vs hybrid)
- Hazard profile composition (top N hazards, score formatting, NRI + USFS blending)
- Award history depth (fiscal year range, per-FY vs cumulative, project description inclusion)
- Cache file schema details beyond the decisions above

</decisions>

<specifics>
## Specific Ideas

- False positives in award matching are explicitly worse than false negatives -- when in doubt, skip the match
- Zero-award Tribes should be framed as opportunity, not deficit -- the advocacy framing in the cache enables Phase 7 DOCX to present "first-time applicant" positively
- Award data flows into economic impact calculations in Phase 7 -- whatever is cached must support multiplier math (obligation amounts at minimum)

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 06-data-acquisition*
*Context gathered: 2026-02-10*
