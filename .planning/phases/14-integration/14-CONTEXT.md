# Phase 14: Integration, Document Generation & Validation - Context

**Gathered:** 2026-02-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire all populated data sources (Phase 12 awards, Phase 13 hazards, congressional cache, Tribal registry) together so an agent swarm produces ~1,200 advocacy documents across 4 types (2 audience tiers x 2 geographic scopes), validates quality, and deploys via GitHub Pages. This phase transforms raw cached data into complete, data-backed documents for 400+ Tribes and all 8 regions.

**Document types:**
- Doc A: Tribal Internal Strategy (CONFIDENTIAL) -- leverage, approach, messaging
- Doc B: Tribal Congressional Overview -- evidence-only, no strategy content
- Doc C: Regional InterTribal Strategy (CONFIDENTIAL) -- coordinated approach, funding equity
- Doc D: Regional Congressional Overview -- public safety, economic benefit, resource utilization

**NOT in scope:** New data acquisition, new scrapers, changes to the scoring/monitoring pipeline, or interactive dashboards.

</domain>

<decisions>
## Implementation Decisions

### Air Gap & Attribution

**Rule: No organizational attribution anywhere.**

- No references to ATNI, ATNI Climate Resilience Committee, NCAI, NCAI Climate Action Task Force, or any other organizational entity in any document surface (cover pages, headers, footers, body text, metadata, methodology notes, coordination sections)
- Documents present as standalone data products -- the data speaks for itself
- Cover pages include: document title, Tribe/region name, state(s), ecoregion(s), delegation summary, date, audience classification
- Headers per page:
  - Doc A: `[Tribe Name] | Internal Strategy | CONFIDENTIAL`
  - Doc B: `[Tribe Name] | FY26 Climate Resilience Program Priorities`
  - Doc C: `[Region Name] | Regional Strategy | CONFIDENTIAL`
  - Doc D: `[Region Name] | FY26 Regional Climate Resilience Overview`
- Footers per page: Page X of Y, generation date, plus `Confidential: For Internal Use Only` (A/C) or `For Congressional Office Use` (B/D)
- No "Prepared by," no author names, no logos, no branding
- Federal data sources cited directly and specifically (USASpending, FEMA NRI, BEA RIMS II, BLS, Congress.gov, USFS)
- Methodology appendix describes computation approach without attributing the pipeline to any entity

### Narrative Voice & Tone

**Framework: Story of Self / Story of Us / Story of Now** (compressed for rapid digestion -- any section readable in under 2 minutes, executive summary under 1 minute)

**Internal docs (A/C):** Assertive, strategic, direct
- Names political dynamics plainly
- Imperative framing ("Prioritize meeting with [Member] before [deadline]")
- "Congress funded; Administration not delivering" stated explicitly as organizing principle
- Sovereignty language explicit: self-determination, trust responsibility, treaty obligations, government-to-government relationship
- Can name tensions between administration's stated support for sovereignty and its actions on climate program delivery

**Congressional docs (B/D):** Objective, factual, measured
- Same facts, different posture -- statements of record, not strategic interpretation
- "Congress funded; Administration not delivering" is implicit (each section shows: what Congress appropriated, current status, what Tribe requests -- reader draws the conclusion)
- Reads like a well-sourced briefing memo
- Lets evidence carry the argument

**Political context calibration:**
- Congressional docs AVOID leading with "climate change" -- use "extreme weather resilience," "natural hazard preparedness," "community resilience," "infrastructure protection"
- Congressional docs LEAN INTO: Tribal sovereignty and self-determination, economic development and job creation, public safety, infrastructure resilience, trust responsibility as legal obligation, bipartisan framing, ROI ($4 return per $1 FEMA/NIBS)
- Internal docs can be direct about the full political landscape

### Content Classification Line

**Boundary: interpretation vs. fact**

**INTERNAL ONLY (never in Doc B/D):**
- Member-by-member approach recommendations
- Sequencing strategy (who to meet first and why)
- Voting record analysis or political characterization of members
- "Leverage" language (pressure points, political dynamics, windows of opportunity)
- Messaging framework (audience-calibrated talking points)
- Strategic framing advice ("use trust responsibility frame with this member")
- References to other Tribes' strategies or coordinated sequencing
- Characterization of admin actions as "hollowing," "withholding," or "circumventing"
- Impoundment Control Act framing or similar legal-strategic positioning

**CONGRESSIONAL SAFE (in Doc B/D):**
- Committee assignments (factual, from Congress.gov)
- Appropriations amounts (factual, from enacted bills)
- Program status (factual: enacted, proposed, canceled, uncertain)
- Award history (factual, from USASpending)
- Hazard scores/rankings (factual, from FEMA NRI)
- Economic impact estimates with methodology citation
- District overlap percentages (factual, from geographic analysis)
- Policy alignment statements
- Treaty/trust responsibility as legal context (not advocacy framing)
- Structural policy recommendations framed as policy improvements, not tactical asks
- Specific funding amounts requested with evidence basis

**Data source citation format (all documents):**
- Award amounts: "Source: USASpending.gov, FY[XX]-FY[XX], CFDA [number]"
- Hazard scores: "Source: FEMA National Risk Index, county-level data aggregated to Tribal geographic boundaries"
- Economic impact: "Methodology: BEA RIMS II regional input-output multipliers (1.8-2.4x); BLS employment requirements tables"
- Mitigation ROI: "Source: FEMA/NIBS MitSaves 2018 Interim Report"
- Congressional data: "Source: Congress.gov, 119th Congress committee assignments"
- Appropriations: "Source: Consolidated Appropriations Act, 2026"
- Wildfire risk: "Source: USFS Wildfire Risk to Communities dataset"

### Regional Document Identity

**8 regions defined by adaptive/mitigative alignment:**
- Pacific NW / Columbia River Basin (pnw)
- Alaska (alaska)
- Great Plains / Northern Plains (plains)
- Southwest / Great Basin (southwest)
- Great Lakes / Midwest (greatlakes)
- Southeast / Gulf Coast / Five Tribes (southeast)
- Northeast / Mid-Atlantic / South and Eastern Tribes (northeast)
- Cross-Cutting -- all regions (crosscutting)

**Nobody "owns" the regional narrative.** Regional docs present observed patterns in federal data:
- "X Tribes in this region share [hazard] as a top-3 risk"
- "Y Tribes have received awards from [program]"
- "Z Tribes share congressional representation through [members]"

**Doc C (Internal Regional):** Funding equity, optimized resource distribution, delegation alignment, sequencing/coordination. No "federation" language -- concept operationalized through the data: "Here is what coordinated action looks like."

**Doc D (Congressional Regional):** Public safety, economic benefit statewide/regionwide, Tribal sovereignty and economic development, extreme weather resilience framing, resource utilization and accountability. Positioned as a resource utilization report. Does NOT contain: federation, coordinated strategy, inter-Tribal coordination mechanisms, funding equity, admin characterization.

### Cross-Cutting Region

- Cross-cutting gets **both** standalone Doc C and Doc D (as the 9th region) AND key cross-cutting themes (science infrastructure threats, 638/CSC, structural policy) appear as appendices in every other regional document
- Some duplication accepted to ensure material is always accessible in context

### Deployment Architecture

- Both internal and congressional docs deploy to GitHub Pages at **separate URL paths**
- Internal docs at `/internal/` (obscured, not indexed)
- Congressional docs at `/congressional/`
- No authentication, but clear structural separation
- v1.1 search/download widget updated to serve the new 4-document-type system with document type selection per Tribe plus a regional documents section

### Data Completeness & Tiered Generation

- **Full documents** (Doc A + Doc B) for Tribes with complete data across all sources (~400 Tribes)
- **Abbreviated data summary documents** for Tribes with partial data (~190 Tribes) that show what IS available without pretending full analysis exists
- Format of abbreviated docs is Claude's discretion based on available data per Tribe
- Regional docs (C/D) aggregate from whatever data is available, noting coverage gaps

### Prototype Text Handling

- **Hybrid approach:** Ecoregion narrative templates and structural asks use scrubbed/adapted prototype prose (well-crafted, stable language)
- Per-program and per-Tribe narratives are **regenerated from data** (must reflect real data, not generic text)
- All prototype content must be air-gap scrubbed before inclusion (no organizational references survive)

### Structural Policy Asks

- The 5 structural asks are **scrubbed and reframed** for FY26 political context and air-gap compliance
- Same substance, updated framing
- Appear in all 4 doc types: internal framing (A/C) vs. policy recommendation framing (B/D)

### Quality Review Process

- **Full auto with spot-check**: Quality review agent swarm auto-fixes everything it can (formatting, citation format, placeholder text, audience differentiation leaks)
- Regenerates failing documents automatically
- Produces a **spot-check report** (5 Tribes per ecoregion = 35 Tribes) for human validation
- Only truly unfixable issues escalate to human review
- Uses the **/docx:review** agent swarm trigger pattern for output design and review coordination

### Claude's Discretion

- Agent swarm internal architecture (data assembler, narrative composer, formatter, quality reviewer implementation details)
- Abbreviated data summary document format for partial-data Tribes
- Technical DOCX formatting choices (spacing, typography, table widths)
- Cross-cutting appendix content selection for regional docs
- Performance optimization for batch generation (~1,200 documents)
- Wave sequencing adjustments if needed during execution

</decisions>

<specifics>
## Specific Ideas

- Congressional docs should read like CRS reports -- the reader draws conclusions from well-presented evidence, the document doesn't tell them what to think
- Internal docs should read like a campaign briefing book -- strategic, actionable, specific about who to talk to and what to say
- "The documents are credible because their data is traceable, not because an organization vouches for them"
- Any congressional staffer should be able to independently verify any number in the document using the cited sources
- The air gap is designed so these documents could never be characterized as "lobbying" -- they are data products that present federal data about federal programs serving Tribal communities
- Current political context: align congressional-facing language with current administration's stated values (sovereignty, self-determination, economic development, public safety) while internal docs can name the fuller political landscape
- Ecoregion narrative templates from prototype (PNW treaty fisheries, Alaska displacement, Southwest water rights, etc.) are stable and well-crafted -- scrub and reuse
- The /docx:review agent swarm should be involved in output design and quality review coordination

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 14-integration*
*Context gathered: 2026-02-11*
*Reference documents: PHASE-14-REFERENCE.md, PHASE-14-DESIGN-DECISIONS.md*
