# Phase 14: Integration, Document Generation & Validation
## Reference Document for Claude Code Agent Swarm

*TCR Policy Scanner v1.2*
*Created: 2026-02-11*

---

## Overview

Phase 14 transforms raw data (awards from Phase 12, hazards from Phase 13, congressional/registry from prior phases) into **six document types** across two audience tiers (Tribal Internal, Congressional External) and two geographic scopes (Individual Tribe, Regional/InterTribal). An agent swarm handles document composition, narrative quality review, data validation, and deployment.

Phase 14 expands from the original 3 plans to **5 waves** with 8 plans total.

---

## Document Architecture

### Audience x Scope Matrix

```
                    │  Individual Tribe          │  Regional / InterTribal
────────────────────┼────────────────────────────┼──────────────────────────────
 INTERNAL           │  Doc A: Tribal Strategy    │  Doc C: InterTribal Strategy
 (Confidential)     │  (funding + congressional  │  (coordinated regional
                    │   approach + leverage)     │   federation approach)
────────────────────┼────────────────────────────┼──────────────────────────────
 CONGRESSIONAL      │  Doc B: Tribal Overview    │  Doc D: Regional Overview
 (External)         │  (funding asks + hot       │  (regional case for broader
                    │   sheets + evidence)       │   funding implications)
────────────────────┴────────────────────────────┴──────────────────────────────
```

**Total per Tribe:** 2 documents (Doc A + Doc B)
**Total per Region:** 2 documents (Doc C + Doc D)
**Regions:** 7 ecoregions (Pacific NW, Alaska, Great Plains, Southwest, Great Lakes, Southeast, Northeast) + 1 cross-cutting = 8
**Estimated output:** ~1,184 Tribe-level docs (592 x 2) + 16 regional docs = ~1,200 documents

---

## Document Specifications

### Doc A: Tribal Internal Strategy
**Filename pattern:** `{tribe_slug}_internal_strategy_fy26.docx`
**Classification:** `CONFIDENTIAL -- FOR INTERNAL TRIBAL USE ONLY`
**Audience:** Tribal leadership, authorized staff, climate program coordinators
**Purpose:** Comprehensive strategy combining federal funding landscape analysis with congressional engagement approach, including leverage points, talking points, and tactical recommendations

#### Content Structure (with TOC and in-document links)

```
COVER PAGE
  - Confidentiality banner
  - Tribe name, state(s), ecoregion(s)
  - "FY26 Federal Funding Overview & Strategy"
  - Prepared date, attribution

TABLE OF CONTENTS (auto-generated, linked)

PART I: FEDERAL FUNDING STRATEGY
  1. Executive Summary
     - FY26 appropriations landscape (2-3 paragraphs)
     - Key strategic frame: "Congress funded; Administration not delivering"
     - Top 3 priority programs with status indicators
     - Aggregate economic impact potential across all programs

  2. Appropriations Landscape
     - What passed (Interior-Environment, CJS, Energy-Water)
     - Administration proposals vs. congressional action (table)
     - Strategic implication column highlighting delivery gaps

  3. Program-by-Program Analysis (ordered by relevance to Tribe's hazard profile)
     For each program:
       - Status indicator [Stable | At Risk | Flagged | Secure | Uncertain]
       - Program overview (2-3 sentences)
       - Award history (real data from Phase 12 caches, NOT placeholder)
         * Prior awards: amounts, fiscal years, trend direction
         * OR first-time applicant positioning if no history
       - Hazard alignment (from Phase 13 NRI data)
         * Which of the Tribe's top-5 hazards this program addresses
         * Risk score context
       - Economic impact (real computation, not program averages)
         * Regional multiplier using actual award amounts
         * Per-district allocation using geographic overlap percentages
         * Jobs supported estimate
       - STRATEGIC LEVERAGE (INTERNAL ONLY)
         * Actionable deadlines
         * Political context and pressure points
         * Framing recommendations for different committee audiences
       - APPROACH STRATEGY (INTERNAL ONLY)
         * Which delegation members to prioritize and why
         * Committee alignment analysis
         * Bipartisan framing vs. trust responsibility framing guidance
         * Sequencing recommendations (who to approach first)

  4. Structural Policy Asks
     - The 5 structural asks with program cross-references
     - Priority ranking based on Tribe's specific situation

PART II: CONGRESSIONAL ENGAGEMENT BRIEFING
  5. Congressional Delegation Analysis
     - Full delegation table with committee assignments
     - STRATEGIC NOTES (INTERNAL ONLY)
       * Committee influence mapping per program
       * Relationship context (voting record on relevant bills)
       * Recommended approach per member (e.g., trust responsibility frame
         for R members on Indian Affairs; economic development frame for
         R members on Appropriations)

  6. Ecoregion Strategic Context
     - Region-specific priorities and leverage (from FY26 strategy prototype)
     - Key messages tailored to this Tribe's ecoregion
     - Cross-ecoregion connections if Tribe spans multiple

  7. Specific Congressional Actions Requested
     - Oversight hearings
     - GAO reviews
     - NCAR protection (if relevant to ecoregion)
     - FEMA accountability
     - BIL final year obligations
     - FY2027 preparation

  8. Strategic Messaging Framework
     - Audience-calibrated messages:
       * Appropriations members
       * Authorizing committee members
       * Senate Committee on Indian Affairs
       * Bipartisan framing
       * District-level framing
       * Treaty/trust frame

APPENDICES
  A. Science Infrastructure Threats (NCAR, NSF grants, USGS hollowing)
  B. FEMA Detail (BRIC, EMPG, HMGP, DRF status)
  C. Additional Programs (lower priority for this Tribe)
  D. Data Sources & Methodology
  E. Confidentiality Notice

PAGE NUMBERS: Yes, "Page X of Y" in footer
IN-DOCUMENT LINKS: Yes, TOC entries link to sections; program references cross-link
HEADER: Tribe name + "CONFIDENTIAL" on every page
FOOTER: Page numbers + generation date
```

#### Data Sources Wired In
- **Phase 12 (Awards):** Real USASpending data per Tribe per program per FY
- **Phase 13 (Hazards):** NRI area-weighted scores, top-5 hazards, USFS wildfire
- **Congressional cache:** Delegation members, committee assignments, district overlaps
- **Registry cache:** Tribe metadata (state, ecoregion, geographic boundaries)
- **Program inventory:** 16 programs with CFDA, access_type, funding_type, status
- **Ecoregion strategy templates:** From FY26 Federal Funding Strategy prototype content

#### Key Differentiators from Doc B
- Contains LEVERAGE sections (what pressure points exist)
- Contains APPROACH STRATEGY (who to talk to, in what order, with what frame)
- Contains MESSAGING FRAMEWORK (audience-calibrated talking points)
- Contains strategic notes on delegation members (voting record context)
- Marked CONFIDENTIAL throughout
- Designed for Tribal staff preparation, not for handoff

---

### Doc B: Tribal Congressional Overview
**Filename pattern:** `{tribe_slug}_congressional_overview_fy26.docx`
**Classification:** `For Congressional Office Use`
**Audience:** Congressional offices, staffers, committee staff
**Purpose:** Clean, evidence-based funding overview with program hot sheets. Designed to be left behind after meetings or sent to offices. No internal strategy, leverage, or approach content.

#### Content Structure

```
COVER PAGE
  - Tribe name, state(s), ecoregion(s)
  - "FY26 Climate Resilience Program Priorities"
  - Delegation summary (X Senators, Y Representatives)
  - Prepared date

TABLE OF CONTENTS

EXECUTIVE SUMMARY
  - Tribe's hazard profile summary (from Phase 13 real data)
    * Overall NRI risk rating with score
    * Social vulnerability index
    * Top 5 hazards ranked
  - Award history summary (from Phase 12 real data)
    * Total prior federal climate resilience awards
    * Trend direction
    * OR first-time applicant positioning
  - Program count and status breakdown
  - Aggregate funding ask and economic impact

CONGRESSIONAL DELEGATION TABLE
  - Name, role, state, district, relevant committees
  - Count of members with relevant committee assignments

PROGRAM HOT SHEETS (one per relevant program, ordered by priority)
  Each hot sheet contains:
    - Program name + status indicator badge
    - Federal home agency
    - One-line status summary
    - Program overview (2-3 sentences)
    - Award history (real data, not placeholder)
    - District economic impact (real computation)
      * Total regional impact range
      * Per-district allocation table
      * Jobs supported
      * Mitigation ROI ($4:$1 where applicable)
    - Advocacy position (what to ask for)
    - Key Ask box (ASK / WHY / IMPACT)
    - Structural policy asks relevant to this program
    - Delegation alignment (which members sit on relevant committees)
    - NO leverage analysis
    - NO approach strategy
    - NO sequencing recommendations

CLIMATE HAZARD PROFILE (full page)
  - Overall risk rating with score
  - Social vulnerability with score
  - Top 5 hazards with NRI scores
  - Hazard-to-program mapping table

STRUCTURAL POLICY ASKS (aggregate)
  - 5 structural asks with programs each would advance
  - Framed as policy recommendations, not tactical leverage

APPENDIX
  - Additional programs (lower priority)
  - Economic impact methodology note
  - Data sources

PAGE NUMBERS: Yes
HEADER: Tribe name on every page
FOOTER: "Prepared [date] | For Congressional Office Use"
NO CONFIDENTIAL MARKINGS (this is designed for handoff)
```

#### Key Differentiators from Doc A
- NO leverage sections
- NO approach strategy
- NO messaging framework
- NO strategic notes on members
- Clean, professional, evidence-forward
- Designed to be left with congressional offices
- Hot sheet format for quick reference per program
- Hazard profile is prominent (evidence-first)

---

### Doc C: InterTribal Regional Strategy
**Filename pattern:** `{region_slug}_intertribal_strategy_fy26.docx`
**Classification:** `CONFIDENTIAL -- FOR INTERNAL TRIBAL USE ONLY`
**Audience:** ATNI leadership, regional Tribal organization staff, InterTribal coordination bodies
**Purpose:** Shows how coordinated InterTribal approaches strengthen the case for all Tribes in the region. Emphasizes federation over competition. Internal strategy document.

#### Content Structure

```
COVER PAGE
  - Confidentiality banner
  - Region name (e.g., "Pacific Northwest / Columbia River Basin")
  - "FY26 InterTribal Climate Resilience Strategy"
  - Tribe count in region
  - Prepared date, ATNI attribution

TABLE OF CONTENTS

1. REGIONAL EXECUTIVE SUMMARY
   - Number of Tribes in region
   - Aggregate hazard profile (composite NRI across region)
   - Total prior federal awards to region (sum from Phase 12)
   - Aggregate economic impact potential
   - "Federation vs. competition" strategic frame

2. THE CASE FOR COORDINATED ADVOCACY
   - Why InterTribal coordination > individual competition
   - Shared hazards across the region (common NRI risks)
   - Shared congressional delegation overlap (Tribes sharing same reps)
   - Shared program dependencies (which programs serve multiple Tribes)
   - Treaty and trust responsibility framing at regional scale
   - STRATEGIC LEVERAGE: Regional voice is louder than individual asks

3. REGIONAL HAZARD SYNTHESIS
   - Composite hazard map (textual description of shared risks)
   - Which hazards affect the most Tribes in this region
   - Hazard trend analysis where available
   - Connection to specific programs

4. REGIONAL AWARD LANDSCAPE
   - Aggregate awards by program across all Tribes in region
   - Coverage gaps (which Tribes have zero awards)
   - First-time applicant cluster identification
   - Trend analysis (is the region gaining or losing federal investment?)

5. PROGRAM PRIORITIES BY REGION
   For each priority program (region-specific ordering):
     - Regional relevance narrative
     - Aggregate regional economic impact
     - Coverage: X of Y Tribes have received awards
     - STRATEGIC LEVERAGE for coordinated regional ask
     - COORDINATION STRATEGY: How Tribes can align asks

6. CONGRESSIONAL STRATEGY
   - Delegation members who serve multiple Tribes in region
   - Committee concentration analysis
   - APPROACH STRATEGY: Coordinated delegation meetings
   - Key messages calibrated to regional framing
   - Sequencing: regional briefing before individual meetings

7. STRUCTURAL POLICY ASKS (Regional Frame)
   - Same 5 structural asks framed at regional scale
   - Regional evidence base for each ask

8. COORDINATION MECHANISMS
   - ATNI Strategic Working Group role
   - ISN data sharing protocols
   - Joint advocacy calendar recommendations
   - Resource sharing opportunities

APPENDICES
  A. Tribes in this region (list with key stats)
  B. Regional delegation complete roster
  C. Regional award data tables
  D. Methodology

PAGE NUMBERS: Yes
HEADER: Region name + "CONFIDENTIAL"
FOOTER: Page numbers + "ATNI Climate Resilience Committee"
```

#### Key Differentiators
- Regional aggregation of all Tribe-level data
- "Federation not competition" framing throughout
- Shows congressional delegation overlap (shared leverage)
- Coordination mechanisms and sequencing
- Identifies coverage gaps for strategic targeting

---

### Doc D: Regional Congressional Overview
**Filename pattern:** `{region_slug}_congressional_overview_fy26.docx`
**Classification:** `For Congressional Office Use`
**Audience:** Congressional offices, committee staff, regional caucuses
**Purpose:** Makes the case for the broader region's funding needs and the implications of investment (or disinvestment) at regional scale. Clean, evidence-forward.

#### Content Structure

```
COVER PAGE
  - Region name
  - "FY26 Tribal Climate Resilience: Regional Overview"
  - Tribe count, state count, delegation count
  - Prepared date

TABLE OF CONTENTS

1. REGIONAL OVERVIEW
   - X Tribes across Y states in this region
   - Aggregate population and geographic scope
   - Regional significance narrative (treaty fisheries, water rights,
     coastal resilience, etc.)

2. REGIONAL HAZARD PROFILE
   - Composite risk assessment
   - Most prevalent hazards across the region
   - Social vulnerability context
   - Connection to broader regional economic risks

3. FEDERAL INVESTMENT LANDSCAPE
   - Total prior awards to Tribes in this region
   - Awards by program (table)
   - Coverage analysis: X% of Tribes have received climate resilience funding
   - Economic impact of existing federal investment
   - Investment gap analysis

4. REGIONAL FUNDING PRIORITIES
   For each priority program:
     - Regional relevance (2-3 sentences)
     - Number of Tribes served/eligible
     - Aggregate economic impact potential
     - Key ask (clean, evidence-based)
     - NO leverage analysis
     - NO approach strategy

5. ECONOMIC IMPACT ANALYSIS
   - Aggregate regional multiplier effects
   - Jobs supported across the region
   - Mitigation ROI at regional scale
   - "Investing in Tribal resilience protects regional economies"

6. REGIONAL DELEGATION
   - Full delegation table for the region
   - Committee assignments relevant to Tribal climate programs
   - NO strategic notes or approach recommendations

7. STRUCTURAL POLICY RECOMMENDATIONS
   - 5 structural asks framed as policy recommendations
   - Regional evidence base

APPENDIX
  - Tribes in this region
  - Program-by-program regional data
  - Methodology

PAGE NUMBERS: Yes
HEADER: Region name
FOOTER: "Prepared [date] | For Congressional Office Use"
NO CONFIDENTIAL MARKINGS
```

---

## Wave Structure

### Wave 1: Data Integration & Economic Impact (Plan 14-01)
**Goal:** Wire all data sources together so economic impact computations use real data, not placeholders

**Tasks:**
1. Refactor economic impact computation in packet builder:
   - Replace program-average fallbacks with real Phase 12 award amounts
   - Use Phase 13 NRI scores to weight hazard alignment narratives
   - Compute per-district impact using real geographic overlap percentages
2. Validate Tribe-level data completeness:
   - For each of 592 Tribes, check: awards cache, hazards cache, congressional cache, registry
   - Generate completeness report: which Tribes have all 4 data sources populated
   - Target: 400+ Tribes with complete data across all sources
3. Create data aggregation functions for regional documents:
   - Sum awards across Tribes per region
   - Composite NRI scores per region
   - Delegation overlap analysis per region
   - Coverage gap identification per region

**Success Criteria:**
1. Economic impact sections use real award amounts (not program averages) for all Tribes with Phase 12 data
2. Hazard-to-program alignment uses real NRI top-5 hazards (not placeholder text)
3. Regional aggregation functions produce valid composite data for all 8 regions
4. Completeness report shows 400+ Tribes with all 4 data sources

---

### Wave 2: Document Generation (Plans 14-02a, 14-02b, 14-02c, 14-02d)
**Goal:** Agent swarm generates all 4 document types with real data, compelling narrative, and proper formatting

**Agent Swarm Architecture:**
The document generation agent swarm consists of specialized agents that know how to produce compelling, evidence-cited advocacy documents. Each agent role:

- **Data Assembler Agent:** Reads all cache files for a Tribe/region, validates completeness, assembles the data payload. Flags missing data and selects appropriate fallback language.
- **Narrative Composer Agent:** Takes data payload and produces section-by-section narrative content. Follows these principles:
  - Cite evidence: every claim backed by specific data (award amounts, NRI scores, congressional vote records)
  - Relational framing: "who is affected, how, when, and why" (not abstract policy language)
  - Sovereignty-centered language: capitalize Indigenous/Tribal/Nations/Peoples/Knowledge; use "relatives not resources" concepts
  - Strategic differentiation: Internal docs include leverage/approach; Congressional docs are evidence-only
  - Ecoregion calibration: narratives reflect regional context (treaty fisheries for PNW, water rights for Southwest, etc.)
- **Formatting Agent:** Applies docx formatting using the /docx skill:
  - Table of Contents with in-document links
  - Page numbers ("Page X of Y")
  - Headers per page (Tribe/region name + classification)
  - Status indicator badges (color-coded if possible, text-based fallback)
  - Tables with proper DXA widths, cell margins, shading
  - Consistent heading hierarchy (Heading1, Heading2, Heading3)
  - Page breaks between major sections
  - Confidentiality banners where appropriate
- **Quality Reviewer Agent:** Checks each generated document against quality criteria (see Wave 3)

**Plan 14-02a: Tribe Internal Strategy Generator (Doc A)**
- Template construction using docx-js
- Section generators for each Part I and Part II section
- Leverage/approach content inclusion (internal-only sections)
- Messaging framework generation per Tribe
- Batch generation for 592 Tribes
- Target: 400+ complete documents

**Plan 14-02b: Tribe Congressional Overview Generator (Doc B)**
- Hot sheet template construction
- Evidence-forward narrative (no leverage/approach content)
- Hazard profile section with real NRI data
- Clean formatting for congressional handoff
- Batch generation for 592 Tribes
- Target: 400+ complete documents

**Plan 14-02c: Regional InterTribal Strategy Generator (Doc C)**
- Regional data aggregation → narrative
- "Federation not competition" framing
- Delegation overlap analysis per region
- Coordination mechanism recommendations
- Generate for 8 regions (7 ecoregions + cross-cutting)

**Plan 14-02d: Regional Congressional Overview Generator (Doc D)**
- Regional evidence synthesis
- Aggregate economic impact analysis
- Regional hazard composite
- Generate for 8 regions

**Success Criteria:**
1. Doc A generated for 400+ Tribes with all sections populated from real data
2. Doc B generated for 400+ Tribes with hot sheets backed by real awards and hazards
3. Doc C generated for all 8 regions with composite data
4. Doc D generated for all 8 regions with clean congressional formatting
5. Internal docs contain leverage/approach; congressional docs do not
6. All documents have TOC, page numbers, headers, in-document links

---

### Wave 3: Document Quality Review (Plan 14-03)
**Goal:** Agent swarm reviews generated documents for narrative quality, evidence citation, formatting consistency, and compelling advocacy structure

**Review Process:**
This wave uses a `/docx:review` trigger pattern to invoke the quality review agent swarm. The review agents evaluate each document against the following criteria:

**Narrative Quality Checklist:**
- [ ] Executive summary conveys urgency without partisan framing
- [ ] Every dollar figure is sourced (USASpending, NRI, BEA RIMS II)
- [ ] Every hazard claim backed by NRI score
- [ ] Every economic impact backed by award data + multiplier methodology
- [ ] Ecoregion framing matches the Tribe's actual geographic context
- [ ] "Congress funded; Administration not delivering" frame is clear but not overused
- [ ] Treaty/trust responsibility language present where appropriate
- [ ] No placeholder text survives ("data pending", "TBD", score of 0.0 without context)

**Evidence Citation Checklist:**
- [ ] Award amounts match Phase 12 cache data
- [ ] Hazard scores match Phase 13 cache data
- [ ] Congressional assignments match congressional cache data
- [ ] District overlap percentages match registry data
- [ ] Economic impact calculations are arithmetically correct
- [ ] Methodology footnotes present on every economic impact section

**Formatting Checklist:**
- [ ] TOC present and links work
- [ ] Page numbers on every page
- [ ] Headers match document classification (CONFIDENTIAL vs. For Congressional Office Use)
- [ ] Tables render correctly (DXA widths, cell margins, shading)
- [ ] Status indicators are consistent across programs
- [ ] No orphaned headings (heading without content before next heading)
- [ ] Confidentiality banners on internal docs only
- [ ] No strategy/leverage content in congressional docs

**Audience Differentiation Checklist:**
- [ ] Doc A contains: leverage, approach strategy, messaging framework, strategic notes
- [ ] Doc B does NOT contain: leverage, approach strategy, messaging framework, strategic notes
- [ ] Doc C contains: coordination strategy, federation framing, shared leverage
- [ ] Doc D does NOT contain: coordination strategy, leverage, approach

**Automated Checks (scriptable):**
- Text search for "placeholder", "TBD", "pending", "0.0" (without context)
- Verify no leverage/approach keywords in Doc B or Doc D
- Verify CONFIDENTIAL banner in Doc A and Doc C only
- Verify page count > minimum (Doc A: 15+ pages, Doc B: 10+ pages)
- Verify economic impact math (award * multiplier range = stated range)

**Sample Validation:**
- Pull 5 Tribes per ecoregion (35 total) for manual spot-check
- Compare Doc A and Doc B for the same Tribe to verify differentiation
- Compare Doc C and Doc D for the same region to verify differentiation

**Success Criteria:**
1. Automated checks pass for 95%+ of generated documents
2. Sample validation confirms narrative quality for 35 spot-checked Tribes
3. Zero placeholder text in documents for Tribes with complete data
4. Audience differentiation confirmed (no strategy leaks into congressional docs)

---

### Wave 4: Data Validation & Documentation (Plan 14-04)
**Goal:** Comprehensive validation script reports coverage across all cache types and VERIFICATION.md documents methodology

**Tasks:**
1. Data validation script (`scripts/validate_coverage.py`):
   - Reports coverage percentages per cache type:
     * Awards: X/592 Tribes with non-zero award data
     * Hazards: X/592 Tribes with scored hazard profiles
     * Congressional: X/592 Tribes with delegation data
     * Registry: X/592 Tribes with complete metadata
   - Reports document generation success:
     * Doc A: X/592 generated
     * Doc B: X/592 generated
     * Doc C: X/8 regions generated
     * Doc D: X/8 regions generated
   - Identifies coverage gaps with specific Tribe IDs
   - Outputs JSON report + human-readable markdown summary

2. VERIFICATION.md:
   - v1.2 testing methodology
   - Data source descriptions and freshness dates
   - Sample validation results (35 spot-checked Tribes)
   - Known coverage gaps with explanations
   - Document type specifications and differentiation rationale
   - Agent swarm architecture description
   - Economic impact methodology documentation

**Success Criteria:**
1. Validation script runs and produces complete coverage report
2. VERIFICATION.md documents all methodology decisions
3. Coverage gaps are identified and categorized (fixable vs. structural)
4. Report confirms 400+ Tribes with complete packets (Doc A + Doc B)

---

### Wave 5: Deployment (Plan 14-05)
**Goal:** GitHub Pages serves updated packets with production URLs

**Tasks:**
1. GitHub Pages deployment configuration
2. Production URL structure finalization (no SquareSpace placeholders)
3. Index pages per region and per Tribe
4. Access control considerations (internal vs. congressional docs)
5. Download packaging (zip per Tribe with both docs, zip per region with both docs)

**Success Criteria:**
1. GitHub Pages deployment serves updated packets
2. Production URLs resolve (no placeholder domains)
3. Internal docs clearly separated from congressional docs in deployment structure
4. Index pages functional for navigation

---

## Agent Swarm Specification

### Swarm Composition

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│  Manages wave sequencing, tracks progress, handles errors   │
└─────────┬──────────────┬──────────────┬─────────────────────┘
          │              │              │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼──────┐
    │   DATA     │  │ NARRATIVE  │  │ FORMATTING│
    │ ASSEMBLER  │  │ COMPOSER   │  │   AGENT   │
    │            │  │            │  │           │
    │ Reads cache│  │ Writes     │  │ Applies   │
    │ files,     │  │ compelling │  │ docx-js   │
    │ validates, │  │ evidence-  │  │ templates,│
    │ assembles  │  │ cited      │  │ TOC, page │
    │ payloads   │  │ narratives │  │ numbers   │
    └────────────┘  └────────────┘  └───────────┘
          │              │              │
    ┌─────▼──────────────▼──────────────▼─────────┐
    │              QUALITY REVIEWER                 │
    │  Checks narrative, evidence, formatting,     │
    │  audience differentiation                    │
    └──────────────────────────────────────────────┘
```

### Agent Behavior Rules

**Data Assembler:**
- MUST read from Phase 12 award caches, Phase 13 hazard caches, congressional caches, registry
- MUST flag missing data explicitly (do not silently fall back to placeholders)
- MUST compute regional aggregates for Doc C and Doc D
- Output: structured JSON payload per Tribe/region

**Narrative Composer:**
- MUST cite specific evidence for every claim (dollar amounts, NRI scores, committee assignments)
- MUST differentiate internal (leverage/approach) from congressional (evidence-only) content
- MUST use sovereignty-centered language conventions:
  - Capitalize: Indigenous, Tribal, Nations, Peoples, Knowledge, Traditional Ecological Knowledge
  - Avoid em dashes
  - Use relational framing (who/how/when/why)
  - "Relatives not resources" as conceptual frame
- MUST calibrate ecoregion narratives to match prototype content (see prototype section below)
- MUST NOT include placeholder text for Tribes with real data
- For Tribes with missing data: use explicit "Data pending" with explanation, not fake numbers

**Formatting Agent:**
- MUST follow /docx SKILL.md conventions (docx-js, US Letter, Arial, DXA widths)
- MUST include: TOC, page numbers, headers, in-document section links
- MUST use proper numbering config (no unicode bullets)
- MUST validate output with `scripts/office/validate.py`
- MUST differentiate header/footer by document type:
  - Doc A: "CONFIDENTIAL" header, page numbers footer
  - Doc B: Tribe name header, "For Congressional Office Use" footer
  - Doc C: "CONFIDENTIAL" header, "ATNI Climate Resilience Committee" footer
  - Doc D: Region name header, "For Congressional Office Use" footer

**Quality Reviewer:**
- MUST run all 4 checklists (narrative, evidence, formatting, audience differentiation)
- MUST run automated text searches for leaked content
- MUST sample-validate 5 Tribes per ecoregion
- MUST produce review report per batch

---

## Prototype Content Mapping

The following maps prototype document sections to the new document architecture, showing where content flows:

### From FY26_Federal_Funding_Strategy.docx (Internal Prototype)

| Prototype Section | Maps To |
|---|---|
| Executive Summary + Strategic Framing | Doc A: Part I, Section 1 |
| FY2026 Appropriations Landscape | Doc A: Part I, Section 2 |
| BIA-TCR Strategic Analysis | Doc A: Part I, Section 3 (program entry for BIA-TCR) |
| Strategic Leverage boxes | Doc A ONLY (Part I, per-program leverage) |
| Key Message boxes | Doc A: Part II, Section 8 (messaging framework) |
| Ecoregion Strategic Priorities | Doc A: Part II, Section 6; Doc C: Section 5 |
| Ecoregion Lobbying Priority Matrix | Doc A: Part II, Section 6; Doc C: Section 5 |
| Science Infrastructure Threats | Doc A: Appendix A |
| FEMA Detail | Doc A: Appendix B |
| Five Structural Asks | Doc A: Part I, Section 4; Doc B: Structural Policy Asks |
| Strategic Messaging Framework | Doc A: Part II, Section 8 (INTERNAL ONLY) |
| Specific Congressional Actions | Doc A: Part II, Section 7 |

### From FY2026_Congressional_Briefing.docx (Congressional Prototype)

| Prototype Section | Maps To |
|---|---|
| Executive Summary | Doc B: Executive Summary (evidence-only version) |
| FY2026 Appropriations Status | Doc B: context within hot sheets |
| Program-specific Lobbying Priority boxes | Doc B: Key Ask boxes (stripped of leverage) |
| Ecoregion Lobbying Priorities Summary | Doc D: Section 4 |
| Congressional Actions Requested | Doc B: appended to structural asks |
| Core Argument | Doc D: Section 1 framing |

### From epa_100000171.docx (Current Scanner Output)

| Current Output Section | Maps To |
|---|---|
| Program Hot Sheets (list) | Doc B: Hot Sheets (enhanced with real data) |
| Congressional Delegation table | Doc A: Part II, Section 5; Doc B: Delegation table |
| Per-program award history | Doc A + Doc B: enhanced with Phase 12 real data |
| Per-program economic impact | Doc A + Doc B: enhanced with real computations |
| Per-program Key Ask box | Doc B: Key Ask (evidence-only); Doc A: Key Ask + leverage |
| Structural Policy Asks | Doc A: Section 4; Doc B: Structural Asks |
| Climate Hazard Profile | Doc B: Hazard Profile (enhanced with Phase 13 real data) |
| Delegation per program | Doc A: approach strategy per program; Doc B: committee alignment |

---

## Ecoregion Narrative Templates

The Narrative Composer agent should use these region-specific frames (derived from the FY26 strategy prototype):

| Region | Core Frame | Key Programs | Treaty/Trust Angle |
|---|---|---|---|
| Pacific NW / Columbia Basin | Drought, fisheries, snowpack, treaty salmon | NIDIS, SNOTEL, NW CASC, NMFS | Treaty fisheries, ceded lands |
| Alaska | Permafrost, displacement, relocation | BIA-TCR relocation, STAG, FEMA | Existential displacement, trust responsibility |
| Great Plains | Drought, water scarcity, extreme heat | WaterSMART, BOR TAP, DOE energy | Water rights, treaty obligations |
| Southwest / Great Basin | Drought, wildfire, water, extreme heat | WaterSMART, DOE solar, CWDG | Senior water rights, Colorado River |
| Great Lakes / Midwest | Flooding, invasive species, PFAS, algal blooms | EPA GAP, USGS Great Lakes | Treaty resources (wild rice, fisheries), ceded territories |
| Southeast / Gulf Coast | Hurricanes, sea level rise, displacement | BIA-TCR relocation, FEMA, NOAA coastal | Coastal displacement, trust responsibility |
| Northeast / Mid-Atlantic | Coastal flooding, sea level rise, precipitation | NOAA coastal, FEMA, EPA water quality | Recognition/trust land intersection |
| Cross-cutting | Science infrastructure, NCAR, NSF, 638/CSC | BIA-TCR, NSF/NCAR, EPA GAP, FEMA | All treaty/trust angles |

---

## Requirements Traceability

| Requirement | Wave | Plan |
|---|---|---|
| INTG-01: Economic impact auto-computes with real data | Wave 1 | 14-01 |
| INTG-02: Batch generation produces complete packets for 400+ Tribes | Wave 2 | 14-02a,b |
| INTG-03: Validation script reports coverage | Wave 4 | 14-04 |
| INTG-04: VERIFICATION.md documents methodology | Wave 4 | 14-04 |
| INTG-05: GitHub Pages deployment with production URLs | Wave 5 | 14-05 |
| INTG-06: (new) Documents differentiate internal vs. congressional audiences | Wave 2,3 | 14-02a,b,c,d + 14-03 |
| INTG-07: (new) Regional InterTribal documents produced for all 8 regions | Wave 2 | 14-02c,d |
| INTG-08: (new) Agent swarm quality review validates all outputs | Wave 3 | 14-03 |

---

## Updated Phase 14 Roadmap Text

*(Drop this into ROADMAP.md to replace the existing Phase 14 section)*

```markdown
### Phase 14: Integration, Document Generation & Validation
**Goal**: All data sources wire together so the agent swarm produces complete, data-backed advocacy documents in 4 types (Tribe internal strategy, Tribe congressional overview, regional InterTribal strategy, regional congressional overview) for 400+ Tribes and all 8 regions
**Wave**: 3-7 (after Phases 11, 12, 13 complete)
**Depends on**: Phase 11, Phase 12, Phase 13 (all data populated + API resilience in place)
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04, INTG-05, INTG-06, INTG-07, INTG-08
**Success Criteria** (what must be TRUE when this phase completes):
  1. Economic impact section auto-computes using real award amounts and hazard scores (no placeholder fallbacks)
  2. Batch document generation for all 592 Tribes produces complete Tribal packets (Doc A + Doc B) for 400+ Tribes
  3. Regional document generation produces InterTribal strategy (Doc C) and congressional overview (Doc D) for all 8 regions
  4. Internal documents (Doc A, Doc C) contain leverage, approach strategy, and messaging; congressional documents (Doc B, Doc D) contain evidence only
  5. Agent swarm quality review validates narrative quality, evidence citation, formatting, and audience differentiation
  6. A data validation script reports coverage percentages across all cache types (awards, hazards, congressional, registry) and document generation success rates
  7. VERIFICATION.md documents the v1.2 testing methodology, sample validation results, and known coverage gaps
  8. GitHub Pages deployment serves updated packets with production URLs (no SquareSpace placeholders)
**Plans**: 8 plans across 5 waves

Plans:
- [ ] 14-01-PLAN.md -- Economic impact activation + data aggregation functions + completeness reporting [Wave 1]
- [ ] 14-02a-PLAN.md -- Doc A: Tribe Internal Strategy generator (agent swarm: data assembler + narrative composer + formatting) [Wave 2]
- [ ] 14-02b-PLAN.md -- Doc B: Tribe Congressional Overview generator (hot sheets, evidence-only, no leverage) [Wave 2]
- [ ] 14-02c-PLAN.md -- Doc C: Regional InterTribal Strategy generator (federation framing, coordination strategy) [Wave 2]
- [ ] 14-02d-PLAN.md -- Doc D: Regional Congressional Overview generator (regional evidence synthesis) [Wave 2]
- [ ] 14-03-PLAN.md -- Agent swarm quality review (/docx:review): narrative, evidence, formatting, audience differentiation checklists [Wave 3]
- [ ] 14-04-PLAN.md -- Data validation script + VERIFICATION.md documentation [Wave 4]
- [ ] 14-05-PLAN.md -- GitHub Pages deployment config + production URL finalization [Wave 5]
```

---

## File Location

This reference document should be accessible to Claude Code at:
```
plans/PHASE-14-REFERENCE.md
```

All plan files should be created at:
```
plans/14-01-PLAN.md
plans/14-02a-PLAN.md
plans/14-02b-PLAN.md
plans/14-02c-PLAN.md
plans/14-02d-PLAN.md
plans/14-03-PLAN.md
plans/14-04-PLAN.md
plans/14-05-PLAN.md
```

---

*Reference document created: 2026-02-11*
*Prototype sources analyzed: FY26_Federal_Funding_Strategy.docx, FY2026_Tribal_Climate_Resilience_Congressional_Briefing.docx, epa_100000171.docx*
*Document types: 4 (2 audience tiers x 2 geographic scopes)*
*Waves: 5 (data integration, document generation, quality review, validation, deployment)*
*Plans: 8 total*
