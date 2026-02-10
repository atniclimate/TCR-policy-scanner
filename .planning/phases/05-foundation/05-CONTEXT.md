# Phase 5: Foundation - Context

**Gathered:** 2026-02-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the Tribal registry (575 federally recognized Tribes), congressional mapping (Tribe-to-district with delegation), and `--prep-packets` CLI skeleton so that `--prep-packets --tribe <name>` resolves a Tribe, displays its delegation, and routes to the packet generation pathway. Actual DOCX output is stubbed — data backbone and command entry point only.

Requirements: REG-01, REG-02, REG-03, CONG-01, CONG-02.

</domain>

<decisions>
## Implementation Decisions

### CLI Output & Feedback
- **Tribe resolution display**: Claude's discretion — pick what feels natural for the CLI
- **Ambiguous names**: Auto-select best match + print warning showing alternatives (no interactive prompts — the tool must work in non-interactive contexts)
- **Progress indicators**: Rich progress bars for multi-step operations (registry loading, delegation lookups)
- **Batch mode (`--all-tribes`)**: Per-Tribe scrolling status lines: `[142/575] Cherokee Nation... done`
- **Match confidence**: Only show match score on fuzzy matches; exact matches proceed silently
- **Summary stats in delegation display**: No — just the detailed delegation list, counts are self-evident

### Tribe Search & Resolution
- **Name variants**: Search official BIA names AND known alternate/historical names from BIA data
- **Match strategy**: Exact substring match first; fall back to fuzzy search only if no exact hit
- **Partial names**: Substring search — `"Choctaw"` returns all Tribes containing that word in their name
- **Confidence display**: Only on fuzzy matches; exact matches proceed without score

### Registry Data Shape
- **Primary key**: BIA code (not EPA Tribe ID or NAICS)
- **File structure**: Single `tribal_registry.json` with array of all 575 Tribe objects
- **Ecoregions**: 7 custom advocacy-relevant regions derived from EPA Level III ecoregions; multi-ecoregion Tribes listed under ALL applicable ecoregions (not primary-only)
- **Extra metadata**: Retain useful fields from EPA API beyond minimum spec (website, population category, etc. if available)
- **Updateability**: One-time build; manually update if BIA list changes (no auto-refresh)
- **Data gaps**: Flag missing Tribes as warnings; skip until data source catches up (don't fabricate entries)

### Delegation Data
- **Cache structure**: Single `congressional_cache.json` with all members, committees, and Tribe-to-district mappings
- **Cache format**: DOCX-aware structure — minimize transformation needed in Phase 7 DOCX rendering
- **Congress tagging**: Tag all cached data with "119th Congress" for staleness detection
- **Party affiliation**: Yes — include party (e.g., "Sen. Jane Doe (R-AZ)")
- **Leadership roles**: Track chair, ranking member, vice chair per committee
- **Committee granularity**: Full committee + subcommittee assignments
- **Senator deduplication**: Show senators once per state (not repeated per district for multi-district Tribes)
- **Alaska handling**: Same format as all other Tribes — AK-AL displayed consistently, no special condensed format
- **Geographic detail**: Store which reservation/trust land overlaps which district (richer context for DOCX narratives)
- **Contact info**: Cache DC office address/phone from Congress.gov (for "reach out to" advocacy framing)
- **Vacancies**: Keep last-known member until next full refresh — packets are point-in-time snapshots
- **District maps in DOCX**: Yes — embed map images showing Tribe's congressional districts (Phase 7 renders; Phase 5 ensures geographic data supports map generation)

### Name Variant Storage
- Claude's discretion — pick the storage approach that works best for the search resolution system

### Delegation Grouping & Committee Depth
- Claude's discretion on grouping (by state vs by chamber) and committee display depth

</decisions>

<specifics>
## Specific Ideas

- CRS R48107 ("Selected Tribal Lands in Congressional Districts") is the authoritative Tribe-to-district mapping source. It's a PDF report, not a structured API. The 118th Congress version is available; an updated 119th Congress version (IR10001) may exist. The researcher should investigate extraction approaches (PDF tables vs Congressional District Geography Workbook Excel file).
- EPA Tribes Names Service API provides the registry data with BIA codes, but may not cover all 575 Tribes (Lumbee added very recently via FY2026 NDAA). Gap handling: flag and skip.
- The 7 advocacy-relevant ecoregions should be derived from EPA Level III ecoregions but grouped into categories meaningful for TCR advocacy (e.g., Pacific Northwest, Southwest, Alaska, Great Plains, Southeast, Northeast, Mountain West — researcher should determine best groupings).
- Congressional District Geography Workbook (119th Congress) from CRS may provide a more structured data source for Tribe-to-district mappings than the PDF report.

</specifics>

<deferred>
## Deferred Ideas

- Interactive district map visualization in DOCX packets — noted for Phase 7 rendering decisions (Phase 5 ensures geographic cache supports this)
- Auto-refresh of Tribal registry from EPA API — one-time build for now
- RIMS II economic multipliers — cost-prohibitive at $500/region, using published multipliers instead (Phase 7)

</deferred>

---

*Phase: 05-foundation*
*Context gathered: 2026-02-10*
