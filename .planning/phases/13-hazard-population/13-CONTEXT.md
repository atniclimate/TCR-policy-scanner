# Phase 13: Hazard Population - Context

**Gathered:** 2026-02-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Populate 592 hazard profile JSON files with real FEMA NRI risk scores and USFS wildfire data. Requires downloading the NRI county dataset, building a Tribe-to-county geographic crosswalk from Census TIGER/Line AIANNH boundaries, aggregating county scores to the Tribe level via area-weighted averaging, extracting top-5 hazards per Tribe, and layering USFS wildfire data for fire-prone Tribes. Target: 550+ profiles with real scored data.

Economic impact computation and packet rendering are Phase 14 concerns.

</domain>

<decisions>
## Implementation Decisions

### Geographic crosswalk
- Minimum 1% area overlap required for a county to qualify for a Tribe's profile (filters sliver overlaps)
- Boundary source: Census TIGER/Line AIANNH shapefile (official, freely downloadable, standard projection)
- Alaska Native Villages: use Census-designated place or borough matching when no polygon boundary exists in AIANNH (not point-buffer fallback)
- Oklahoma Tribal Statistical Areas: shared counties are fine -- each Tribe gets hazard data from all overlapping counties regardless of whether other Tribes share those counties

### Score aggregation
- Area-weighted composite: weight each county's per-hazard score by its area overlap fraction, then rank to determine top 5
- Same area-weighting method applies to composite scores (risk_score, sovi_score, resl_score) -- consistent methodology
- Ranking driven by risk_score (0-100 NRI relative index), but EAL dollar amounts also stored in profile for advocacy citation
- Risk rating strings (e.g., "Very High") re-derived from the weighted score using FEMA's published thresholds -- not taken from any single county
- Only non-zero hazards stored in all_hazards (drop zero-score hazard types from profile). Top-5 still extracted from non-zero set
- counties_analyzed field updated with count; no additional provenance metadata (FIPS codes, weights) stored
- Single-county Tribes: no special handling -- counties_analyzed=1 already communicates this

### Wildfire data layering
- USFS data overrides NRI WFIR: when USFS conditional-risk-to-structures data exists, it replaces the NRI wildfire score in the WFIR hazard entry
- Fire-prone eligibility: any Tribe whose NRI WFIR score is non-zero qualifies for USFS data lookup (300+ expected)
- USFS metric: conditional risk to structures (expected loss given fire) -- most relevant for funding advocacy
- usfs_wildfire section stores USFS-specific data; WFIR in all_hazards reflects the USFS override when available

### Coverage gap handling
- Unmatched Tribes (no polygon, no Census-designated place match): leave as zeroes in existing schema. Downstream already handles zero-data profiles
- Coverage report: generate a persistent report (coverage_report.json or .md) with per-state breakdown, match rates, and list of unmatched Tribes. Feeds Phase 14 validation
- NRI dataset version: track actual release version (e.g., "NRI_Table_Counties_v1.19.0") in each profile's version field for freshness checks

### Claude's Discretion
- Whether to preserve original NRI WFIR score when USFS overrides (audit trail vs. simplicity)
- Note field handling for populated profiles (clear it, update with methodology summary, or leave)
- Exact FEMA rating threshold breakpoints for re-deriving risk_rating strings
- Coverage report format (JSON vs Markdown vs both)
- Internal caching strategy for large boundary intersection computations

</decisions>

<specifics>
## Specific Ideas

- Existing hazard profile schema has 18 NRI hazard types already defined -- populated profiles should only retain non-zero hazards (schema change from current all-18 placeholder)
- The usfs_wildfire section is currently an empty dict `{}` -- needs structure definition during implementation
- River Runner research found 0% hazard profile population (592 placeholder files) -- this phase takes it to 550+
- USFS conditional risk to structures was chosen over burn probability because it shows potential impact, not just likelihood -- stronger for advocacy packets

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 13-hazard-population*
*Context gathered: 2026-02-11*
