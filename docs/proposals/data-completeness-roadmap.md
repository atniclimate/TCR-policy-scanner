# Enhancement Proposal: Data Completeness Roadmap

**Author:** Horizon Walker, TCR Policy Scanner Research Team
**Date:** 2026-02-11
**Status:** Proposed
**Effort:** 34 story points across 5 sprints (staggered across milestones)

---

## Problem

The TCR Policy Scanner has the architecture to deliver comprehensive advocacy
intelligence to 592 Tribal Nations. It has the pipeline (6 stages), the graph
(9 node types, 10 edge types), the document engine (8-section DOCX per Tribe),
and the distribution mechanism (GitHub Pages widget). What it does not yet have
is the data to fill those structures.

**Current data inventory as of 2026-02-11:**

| Data Source | Files | Populated | Coverage |
|-------------|-------|-----------|----------|
| Tribal Registry | 1 | Yes | 592/592 (100%) |
| Congressional Cache | 1 | Yes | 538 members, 550/577 matched (95.3%) |
| Tribal Aliases | 1 | Yes | 3,751 aliases across 592 Tribes |
| Award Cache | 592 | Schema only | 0/592 populated (0%) |
| Hazard Profiles | 592 | Schema only | 0/592 populated (0%) |
| Program Inventory | 1 | Yes | 16/16 programs (100%) |
| Graph Schema | 1 | Yes | 20 authorities, 13 barriers, 8 vehicles |
| Ecoregion Config | 1 | Yes | 7 NCA5 regions (100%) |
| Policy Tracking | 1 | Yes | 16 CI scores (100%) |

The award cache files exist for all 592 Tribes but contain zero awards and zero
obligations. The note field reads: "No federal climate resilience awards found in
tracked programs." The hazard profile files exist for all 592 Tribes but all 18
NRI hazard types show risk_score: 0.0. The note reads: "NRI county data not loaded."

This means the DOCX advocacy packets -- the primary deliverable of this tool --
currently contain:
- Identity and registration data: **complete**
- Congressional delegation: **complete**
- Federal award history: **empty** (shows "first-time applicant" framing)
- Hazard profile: **empty** (shows no hazard data)
- Economic impact: **empty** (depends on awards + hazards)

Three of five major packet sections are operating on placeholder data. The
architecture is sound; the data pipes need to be connected to their sources.

## Vision

Every data gap has a specific API, a known record count, a quantifiable coverage
improvement, and a clear impact on Tribal advocacy. This roadmap orders them by
the principle: **fill the data that most improves the most packets for the most
Tribes first.**

After executing this roadmap, a Tribal Leader's advocacy packet transforms from
a document with strong identity/delegation sections and empty data sections into
a comprehensive intelligence product where every section is backed by verified
federal data.

## Priority-Ordered Data Source Roadmap

### Priority 1: USASpending Award Population (Critical Path)

**What it fills:** Award cache for all 592 Tribes
**API:** USASpending.gov `/api/v2/search/spending_by_award/`
**Current state:** 592 files with zero awards, zero obligations
**Impact:** Fills Section 4 (Federal Award History) and feeds Section 5 (Economic Impact)

#### Implementation

The infrastructure already exists:
- `src/scrapers/usaspending.py` -- the scraper
- `data/tribal_aliases.json` -- 3,751 name aliases for two-tier matching
- `src/packets/awards.py` -- award cache builder
- `scripts/` -- ingestion scripts framework

What is needed is a **batch population run** that:

1. For each of the 592 Tribes, query USASpending by recipient name using the
   curated alias table (primary match) and rapidfuzz fallback (score >= 85)
2. Filter results by the 16 tracked program CFDAs:
   - 15.156 (BIA TCR)
   - 15.124 (BIA TCR Awards)
   - 97.047, 97.039 (FEMA BRIC)
   - 66.468 (EPA STAG)
   - 66.926 (EPA GAP)
   - 20.284 (DOT PROTECT)
   - 10.720 (USDA Wildfire)
   - 81.087 (DOE Indian Energy)
   - 14.867 (HUD IHBG)
   - 20.205 (FHWA TTP)
   - 15.507 (USBR WaterSMART)
3. Write results to `data/award_cache/{tribe_id}.json`
4. Validate counts against known program award distributions

#### Estimated Records

| Program | CFDA | Est. Annual Awards | Est. Tribal Recipients |
|---------|------|-------------------|----------------------|
| BIA TCR | 15.156 | 150-200 | 100-150 Tribes |
| BIA TCR Awards | 15.124 | 50-80 | 40-60 Tribes |
| EPA GAP | 66.926 | 400-500 | 350-450 Tribes |
| EPA STAG | 66.468 | 200-300 | 150-250 Tribes |
| HUD IHBG | 14.867 | 500-600 | 400-500 Tribes |
| FHWA TTP | 20.205 | 300-400 | 250-350 Tribes |
| DOT PROTECT | 20.284 | 20-40 | 15-30 Tribes |
| DOE Indian Energy | 81.087 | 30-50 | 20-40 Tribes |
| USDA Wildfire | 10.720 | 40-80 | 30-60 Tribes |
| USBR WaterSMART | 15.507 | 10-20 | 8-15 Tribes |
| FEMA BRIC | 97.047/039 | 20-40 (pre-termination) | 15-30 Tribes |

**Total estimated records:** 1,720-2,310 awards across FY20-FY25
**Estimated Tribal coverage:** 450-550 of 592 Tribes with at least one award

#### API Complexity

- **Auth:** SAM_API_KEY required (already handled via env var)
- **Rate limits:** USASpending has generous limits (~1,000 req/hour)
- **Batch strategy:** Query by CFDA first (11 queries), then match to Tribes
  (more efficient than 592 Tribe-by-Tribe queries)
- **Data size:** ~50MB total across 592 cache files

**Effort: 5 SP (Sprint 1)**
**Coverage improvement: 0% -> ~80% of Tribes with award data**
**Packet impact: Section 4 goes from empty to populated for 450+ Tribes**

---

### Priority 2: FEMA NRI Hazard Data Population (Critical Path)

**What it fills:** Hazard profiles for all 592 Tribes
**API:** FEMA National Risk Index (NRI) via OpenFEMA API
**Current state:** 592 files with all zeros, "NRI county data not loaded"
**Impact:** Fills Section 3 (Hazard Profile) and feeds Section 5 (Economic Impact)

#### Implementation

The hazard profile infrastructure exists:
- `src/packets/hazards.py` -- hazard profile builder
- Data schema includes 18 NRI hazard types (AVLN through WNTW)
- Social vulnerability (SOVI) and community resilience (RESL) scores

What is needed:

1. Download FEMA NRI county-level dataset (CSV, ~3,200 counties)
2. Map Tribes to counties using:
   - AIANNH-to-county geographic overlay from Census TIGER/Line
   - Existing state assignments in `tribal_registry.json`
3. For each Tribe, aggregate county-level NRI scores:
   - Weighted average across overlapping counties
   - Extract top 5 hazards by risk score
   - Compute composite risk, SOVI, and RESL ratings
4. Write results to `data/hazard_profiles/{tribe_id}.json`

#### USFS Wildfire Integration

The hazard profile schema also includes a `usfs_wildfire` section (currently empty).
USFS publishes wildfire risk data at the community level:

- **Source:** USFS Wildfire Risk to Communities (wildfirerisk.org)
- **Data:** Community-level wildfire likelihood, exposure, and vulnerability
- **Mapping:** Match AIANNH boundaries to USFS community boundaries
- **Records:** ~300-400 Tribal communities with wildfire risk data

#### Estimated Coverage

| Source | Counties/Communities | Tribes Covered | Hazard Types |
|--------|---------------------|---------------|-------------|
| FEMA NRI | 3,143 counties | 550+ Tribes (via county overlay) | 18 types |
| USFS Wildfire | 70,000+ communities | 300-400 Tribes | 3 metrics |

**Combined coverage: 550+ of 592 Tribes with at least partial hazard data**

The remaining ~40 Tribes (primarily in Alaska and remote areas) may not have
county-level NRI coverage. For these, we use state-level fallback data with
reduced confidence scores.

#### API Complexity

- **Auth:** None required (OpenFEMA is public, unauthenticated)
- **Rate limits:** Generous (no documented limit)
- **Data size:** NRI dataset is ~150MB CSV (one-time download, then local processing)
- **Mapping complexity:** MODERATE -- requires Tribe-to-county geographic crosswalk

**Effort: 8 SP (Sprint 2)**
**Coverage improvement: 0% -> ~93% of Tribes with hazard data**
**Packet impact: Section 3 goes from empty to populated for 550+ Tribes**

---

### Priority 3: Economic Impact Activation (Dependent on P1 + P2)

**What it fills:** Economic impact section for all Tribes with award + hazard data
**Source:** Computation from awards (P1) + hazards (P2) + published multipliers
**Current state:** Empty (depends on upstream data)
**Impact:** Fills Section 5 (Economic Impact) with FEMA BCR and multiplier framing

#### Implementation

The economic impact engine exists (`src/packets/economic.py`) and uses:
- FEMA 4:1 Benefit-Cost Ratio for mitigation investments
- Published economic multipliers (jobs, local spending)
- District-level framing for congressional impact

Once awards (P1) and hazards (P2) are populated, economic impact computes
automatically. The only new work is:

1. Validate multiplier calculations against populated data
2. Handle edge cases (Tribes with awards but no hazards, or vice versa)
3. Add confidence scoring to economic projections (T4 tier, 0.70 base)

**Effort: 3 SP (Sprint 3, after P1 + P2 complete)**
**Coverage improvement: Automatic once P1 + P2 populate**
**Packet impact: Section 5 goes from empty to populated for 400+ Tribes**

---

### Priority 4: OpenFEMA Disaster Declaration History

**What it fills:** Historical disaster declaration context per Tribe
**API:** OpenFEMA `/api/open/v2/DisasterDeclarationssSummaries`
**Current state:** Not in pipeline
**Impact:** Enriches hazard profiles with real event history

#### Value Proposition

FEMA NRI provides probabilistic risk estimates. OpenFEMA disaster declarations
provide actual historical events. Together, they tell a powerful story: "Your
community faces HIGH wildfire risk (NRI) and has experienced 3 major disaster
declarations in the last 10 years (FEMA declarations). Federal mitigation
investment has a documented 4:1 return."

#### Implementation

1. Query OpenFEMA for all Tribal disaster declarations:
   - Filter: `designatedArea LIKE '%Tribe%' OR designatedArea LIKE '%Indian%'`
   - Also filter by FIPS code where Tribe-to-county mapping exists
2. For each Tribe, extract:
   - Declaration count (last 5, 10, 20 years)
   - Declaration types (DR, EM, FM, FS)
   - Total Individual and Public Assistance obligated
   - Most recent declaration date
3. Store in `data/disaster_cache/{tribe_id}.json`
4. Integrate into hazard profile section of DOCX packets

#### Estimated Records

OpenFEMA lists approximately 1,500-2,000 Tribal-related disaster declarations
since 1964. Recent years (2015-2025) contain approximately 300-500 relevant
declarations.

#### API Complexity

- **Auth:** None required (public API)
- **Rate limits:** 1,000 records per request, pagination required
- **Data quality:** Good -- structured records with dates, types, amounts
- **Mapping complexity:** MODERATE -- matching declaration areas to Tribes

**Effort: 5 SP (Sprint 4)**
**Coverage improvement: NEW data source -- ~200-300 Tribes with declaration history**
**Packet impact: Adds historical context to hazard section, strengthens BCR argument**

---

### Priority 5: Grants.gov Opportunity Enrichment

**What it fills:** Active and upcoming grant opportunities per program
**API:** Grants.gov `/api/search2` (already integrated)
**Current state:** Scraper exists, data flows to briefing but not to per-Tribe packets
**Impact:** Adds "Open Opportunities" section to DOCX packets

#### Value Proposition

The existing `grants_gov.py` scraper collects open Tribal-relevant grant
opportunities. This data flows into the daily briefing but is not currently
routed to per-Tribe packets. Adding an "Open Opportunities" section would give
each Tribe a list of grant opportunities they are eligible for, with deadlines
and application URLs.

#### Implementation

1. Filter existing Grants.gov scan results by Tribal eligibility codes
2. Match opportunities to programs by CFDA number
3. Route matched opportunities to per-Tribe context (via relevance filter)
4. Add "Open Opportunities" section to DOCX packets
5. Include deadline countdown and application URL

**Effort: 3 SP (Sprint 4)**
**Coverage improvement: Varies by grant cycle (~50-100 open opportunities)**
**Packet impact: Adds actionable next-steps section to every packet**

---

### Priority 6: Congressional Committee Assignment Enrichment

**What it fills:** Committee and subcommittee assignments for Tribal delegation members
**API:** Congress.gov `/api/member/{bioguideId}/committees`
**Current state:** Congressional cache has 538 members, committee data partially populated
**Impact:** Enriches delegation section with committee relevance

#### Implementation

The existing `data/congressional_cache.json` contains member data. Enriching
with full committee assignments enables:
- Flagging delegation members on Appropriations (direct funding influence)
- Flagging delegation members on Indian Affairs (direct policy influence)
- Flagging delegation members on Natural Resources (jurisdictional overlap)
- Prioritizing contact recommendations by committee relevance

**Effort: 2 SP (Sprint 5)**
**Coverage improvement: Enriches existing 538 member records**
**Packet impact: Makes delegation section more actionable**

---

### Priority 7: Federal Register Tribal Consultation Notices

**What it fills:** Active and scheduled Tribal consultation events
**API:** Federal Register API (already integrated via `federal_register.py`)
**Current state:** Scraper collects policy items, does not extract consultation events
**Impact:** Adds "Upcoming Consultations" section to packets

#### Implementation

1. Add consultation-specific search terms to Federal Register scraper
2. Extract consultation dates, agencies, topics, and RSVP deadlines
3. Match consultations to programs and Tribes
4. Add "Upcoming Consultations" section to DOCX packets

**Effort: 3 SP (Sprint 5)**
**Coverage improvement: ~20-40 active consultations at any time**
**Packet impact: Adds time-sensitive participation opportunities**

---

### Priority 8: NOAA Climate Projection Data (Horizon)

**What it fills:** Long-term climate risk projections per Tribe
**API:** NOAA Climate API / NCA5 regional projections
**Current state:** Not in pipeline (deferred from v1.1)
**Impact:** Adds 30-year outlook to hazard profiles

This is listed as out-of-scope in the current project constraints ("valuable but
deferred; adds significant integration complexity beyond NRI"). It remains a
horizon priority for future milestones.

**Effort: 8 SP (future milestone)**
**Coverage: All 592 Tribes (regional projection data)**
**Packet impact: Transforms hazard section from current-risk to future-risk**

## Coverage Impact Summary

```
Current State (v1.1):
  ┌────────────────────────────────────────────────────┐
  │  Section 1: Identity          ████████████████  100% │
  │  Section 2: Delegation        ████████████████   95% │
  │  Section 3: Hazard Profile    ░░░░░░░░░░░░░░░░    0% │
  │  Section 4: Award History     ░░░░░░░░░░░░░░░░    0% │
  │  Section 5: Economic Impact   ░░░░░░░░░░░░░░░░    0% │
  │  Overall Packet Completeness: ██████░░░░░░░░░░   39% │
  └────────────────────────────────────────────────────┘

After Priority 1 (Awards):
  ┌────────────────────────────────────────────────────┐
  │  Section 1: Identity          ████████████████  100% │
  │  Section 2: Delegation        ████████████████   95% │
  │  Section 3: Hazard Profile    ░░░░░░░░░░░░░░░░    0% │
  │  Section 4: Award History     █████████████░░░   80% │
  │  Section 5: Economic Impact   ░░░░░░░░░░░░░░░░    0% │
  │  Overall Packet Completeness: ██████████░░░░░░   55% │
  └────────────────────────────────────────────────────┘

After Priority 2 (Hazards):
  ┌────────────────────────────────────────────────────┐
  │  Section 1: Identity          ████████████████  100% │
  │  Section 2: Delegation        ████████████████   95% │
  │  Section 3: Hazard Profile    ███████████████░   93% │
  │  Section 4: Award History     █████████████░░░   80% │
  │  Section 5: Economic Impact   ░░░░░░░░░░░░░░░░    0% │
  │  Overall Packet Completeness: ████████████░░░░   74% │
  └────────────────────────────────────────────────────┘

After Priority 3 (Economic):
  ┌────────────────────────────────────────────────────┐
  │  Section 1: Identity          ████████████████  100% │
  │  Section 2: Delegation        ████████████████   95% │
  │  Section 3: Hazard Profile    ███████████████░   93% │
  │  Section 4: Award History     █████████████░░░   80% │
  │  Section 5: Economic Impact   ██████████░░░░░░   68% │
  │  Overall Packet Completeness: ██████████████░░   87% │
  └────────────────────────────────────────────────────┘

After All Priorities (1-7):
  ┌────────────────────────────────────────────────────┐
  │  Section 1: Identity          ████████████████  100% │
  │  Section 2: Delegation        ████████████████   98% │
  │  Section 3: Hazard Profile    ████████████████   95% │
  │  Section 4: Award History     ██████████████░░   85% │
  │  Section 5: Economic Impact   ████████████░░░░   75% │
  │  + Open Opportunities         ████████████░░░░   75% │
  │  + Consultations              ████████░░░░░░░░   50% │
  │  + Disaster Declarations      ████████████░░░░   75% │
  │  Overall Packet Completeness: ███████████████░   91% │
  └────────────────────────────────────────────────────┘
```

## Integration Difficulty Matrix

| Priority | API | Auth | Rate Limits | Mapping | New Code | Total Difficulty |
|----------|-----|------|-------------|---------|----------|-----------------|
| P1: USASpending | REST | SAM key (exists) | Generous | Alias table (exists) | Low | **EASY** |
| P2: FEMA NRI | CSV download | None | N/A | Tribe-to-county (new) | Medium | **MODERATE** |
| P3: Economic | Computation | N/A | N/A | Depends on P1+P2 | Low | **EASY** |
| P4: OpenFEMA | REST | None | Generous | Tribe-to-FIPS (partial) | Medium | **MODERATE** |
| P5: Grants.gov | REST | None (exists) | Generous | CFDA match (exists) | Low | **EASY** |
| P6: Congress API | REST | Key (exists) | 5K/hour | BioguideId (exists) | Low | **EASY** |
| P7: Fed Register | REST | None (exists) | Generous | Keyword match (exists) | Low | **EASY** |
| P8: NOAA Climate | Multiple | Varies | Varies | Geographic (complex) | High | **HARD** |

## Advocacy Impact Matrix

| Priority | Tribes Benefiting | Packet Improvement | Advocacy Strength |
|----------|------------------|-------------------|-------------------|
| P1: Awards | 450-550 | Section 4 populates | HIGH -- "Here is what we received" |
| P2: Hazards | 550+ | Section 3 populates | HIGH -- "Here is what we face" |
| P3: Economic | 400+ | Section 5 populates | HIGH -- "Here is the return on investment" |
| P4: Disasters | 200-300 | Hazard section enriched | MEDIUM -- "Here is what already happened" |
| P5: Grants | 592 (varies) | New section added | HIGH -- "Here is what to apply for next" |
| P6: Committees | 592 | Delegation enriched | MEDIUM -- "Here is who has the most leverage" |
| P7: Consultations | 592 (varies) | New section added | MEDIUM -- "Here is where to show up" |
| P8: NOAA | 592 | Hazard section enriched | HIGH -- "Here is what is coming" |

## Recommended Execution Order

**v1.2 Tech Debt (current milestone):** P1 (Awards) + P2 (Hazards) + P3 (Economic)
- These are the critical path items that transform packets from 39% to 87% complete
- P1 and P2 can run in parallel (no dependency)
- P3 activates automatically once P1 + P2 complete
- Total: 16 SP across 3 sprints

**v1.3 Enrichment:** P4 (Disasters) + P5 (Grants) + P6 (Committees) + P7 (Consultations)
- Adds new sections and enriches existing ones
- P4, P5, P6, P7 can all run in parallel (no dependencies between them)
- Total: 13 SP across 2 sprints

**v2.0 Horizon:** P8 (NOAA Climate) + other future sources
- Significant integration complexity, deferred until foundational data is solid
- Total: 8+ SP, timeline TBD

## Impact Statement: How This Serves Tribal Sovereignty

When a Tribal Leader walks into a congressional meeting with their advocacy packet,
the packet is only as strong as the data behind it. A packet that says "No federal
climate resilience awards found" when the Tribe has actually received $2.3M in EPA
GAP and BIA TCR funding is not just incomplete -- it undermines the advocacy position.
A packet with an empty hazard profile for a Tribe in tornado alley misses the
strongest argument for mitigation funding.

Every data gap in this roadmap represents a missed advocacy opportunity for a
specific Tribal Nation. Filling the award cache means 450+ Tribes walk into their
next meeting with documented federal investment history. Filling the hazard profiles
means 550+ Tribes can point to quantified climate risk data that justifies every
dollar they request.

The math is not abstract. If populating USASpending data reveals that the average
Tribe receives $1.2M across tracked programs, and the economic impact section frames
that investment at a 4:1 return, then every advocacy packet becomes a $4.8M argument
for continued and expanded funding. Multiply that across 450+ Tribes and the
collective advocacy value is measured in billions.

Data completeness is not a technical nice-to-have. It is the difference between a
Tribal Leader saying "we need more funding" and a Tribal Leader saying "here is
exactly what we received, here is the return it generated, and here is why the
next dollar matters." The second argument wins.

---

*Proposed by Horizon Walker. Fill every gap. Strengthen every packet. Serve every Tribe.*
