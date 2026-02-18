# Phase 20: Flood & Water Data - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Six flood and water data sources are fetched, parsed, and cached per Tribe through the existing county FIPS crosswalk: NFIP flood insurance (OpenFEMA), FEMA disaster declarations (OpenFEMA), FEMA NFHL flood zone designations, USGS Water Services streamflow, NOAA Atlas 14 precipitation frequency, and NOAA CO-OPS coastal water levels. All data pre-cached with provenance metadata. No new geographic bridge files. Composite scoring and document rendering are separate phases (22 and 23).

</domain>

<decisions>
## Implementation Decisions

### Historical Depth
- FEMA disaster declarations (FLOOD-02): 20-year window (2005-present), post-Katrina era
- NFIP flood insurance (FLOOD-01): all available history (full cumulative record, no time cap)
- USGS streamflow (FLOOD-04): peak annual flows (full record) plus last 1-2 years of daily data
- NOAA Atlas 14 (FLOOD-05): key return periods only (10-year, 25-year, 50-year, 100-year)
- NOAA CO-OPS (FLOOD-06): 20-year daily water level record (match declarations window)
- FEMA NFHL (FLOOD-03): current snapshot with effective date per map panel

### Disaster Declarations Scope
- Include ALL disaster types (not just flood/water-related) -- broader vulnerability picture, complements existing NRI hazard data
- Store all dollar amounts: Individual Assistance, Public Assistance, Hazard Mitigation Grant Program amounts per declaration
- Enables grant narrative like "$X in federal disaster aid received over 20 years"

### NFHL Flood Zone Data
- Store zone designations (A, AE, V, X, etc.) AND percentages of area in each zone
- Capture map panel effective dates (enables "flood maps last updated 2012" advocacy narrative for outdated maps)
- Include NFIP community participation status (whether community participates in the National Flood Insurance Program)

### Coastal Tribe Classification
- Definition: county-based -- if any county in a Tribe's crosswalk is NOAA-designated coastal, the Tribe is coastal
- Three-way classification: marine (ocean coast), lacustrine (Great Lakes), inland
- Great Lakes Tribes get separate "lacustrine" category distinct from marine coastal -- they face real coastal hazards but different character
- "Coastal wins" rule: if ANY county in crosswalk is coastal, the Tribe gets that coastal classification (inclusive)
- Stored as a base Tribe attribute (coastal_type: marine/lacustrine/inland) reusable by Phase 21+ -- not scoped to Phase 20 only
- Alaska coastal Tribes: flag as coastal even if no CO-OPS data exists; note absence as federal monitoring gap (consistent with 18.5-DEC-06 Alaska strategy)

### Streamflow Gauge Selection
- County crosswalk match, filtered by drainage area size threshold
- Keep ALL gauges that pass the size filter (no cap on count per Tribe)
- Store per gauge: site metadata, location, drainage area, period of record, peak annual flows, recent daily data, flood/action stage thresholds from NWS
- Store raw USGS API response alongside parsed Pydantic schema data (enables debugging and reprocessing without re-fetching)
- Tribes with no gauges in crosswalk counties: record as "monitoring gap" -- frames as federal infrastructure gap, not data absence

### Missing Data Framing
- Two categories for missing data: "not applicable" (source doesn't apply, e.g., coastal data for inland Tribe) vs "monitoring gap" (source SHOULD have data but infrastructure doesn't exist)
- Monitoring gap cases include a per-source suggested advocacy action (e.g., "USGS streamflow monitoring gap -- request gauge installation through [program]")
- Coverage report includes: X Tribes with data, Y Tribes not applicable, Z Tribes with monitoring gap -- per source
- Use existing VULNERABILITY_FRAMING constants from Phase 19 (REG-04). No new flood-specific framing terms -- new narrative language is a Phase 23 rendering concern

### Claude's Discretion
- Coastal flag storage approach (stored attribute vs derived) -- pick based on existing codebase patterns
- Drainage area size filter threshold and whether it's configurable or fixed -- pick what's practical and consistent with existing config patterns
- Specific advocacy action text for each monitoring gap type -- research appropriate federal programs during planning

</decisions>

<specifics>
## Specific Ideas

- Alaska data gaps should be framed as federal infrastructure failures, not Tribal data gaps (consistent with 18.5-DEC-06 three-tier Alaska narrative strategy)
- NFHL map currency dates are a powerful advocacy tool -- outdated flood maps are a known problem in Indian Country and documenting this strengthens remapping arguments
- NFIP community participation status matters because many Tribal Nations are not NFIP participants, which affects flood insurance availability and disaster recovery
- USGS new Water Services API (DEC-07 from Phase 18.5) -- build against new endpoint, not legacy
- Raw + parsed storage for USGS data enables reprocessing if schema evolves without re-fetching (important given API rate limits)

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 20-flood-water-data*
*Context gathered: 2026-02-17*
