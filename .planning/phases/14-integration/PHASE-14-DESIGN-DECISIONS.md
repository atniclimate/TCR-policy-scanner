# Phase 14: Design Decisions Addendum
## Answers to Architecture Interview Questions

*TCR Policy Scanner v1.2*
*Created: 2026-02-11*
*Companion to: plans/PHASE-14-REFERENCE.md*

---

## 1. Air Gap & Attribution

### Rule: No Organizational Attribution Anywhere

Documents do not carry ATNI, NCAI, or any organizational name in cover pages, footers, headers, coordination sections, or regional framing. The tool produces the documents; the documents stand on their own as data-driven outputs.

### What Replaces Attribution

Headers, footers, and cover pages use **descriptive document metadata only**:

**Cover pages include:**
- Document title (e.g., "FY26 Climate Resilience Program Priorities")
- Tribe name or region name
- State(s) and ecoregion(s)
- Congressional delegation summary (X Senators, Y Representatives)
- Date generated
- Audience classification (see below)

**Headers (every page):**
- Doc A: `[Tribe Name] | Internal Strategy | CONFIDENTIAL`
- Doc B: `[Tribe Name] | FY26 Climate Resilience Program Priorities`
- Doc C: `[Region Name] | Regional Strategy | CONFIDENTIAL`
- Doc D: `[Region Name] | FY26 Regional Climate Resilience Overview`

**Footers (every page):**
- Page X of Y
- Generation date
- Doc A/C: `Confidential: For Internal Use Only`
- Doc B/D: `For Congressional Office Use`

**No footer or header contains:**
- Organization names (ATNI, NCAI, IndigenousACCESS, or any other)
- "Prepared by" attribution to any entity
- Author names or contact information
- Logos or organizational branding

### Air Gap Depth

The air gap is **comprehensive**, covering:

- **Document surfaces:** Cover pages, headers, footers, section titles, appendices
- **Body text:** No references to "our organization," "the Task Force," "the Committee," or similar organizational framing. Content reads as if the data speaks for itself.
- **Metadata/methodology notes:** Data source citations reference the federal sources directly (USASpending, FEMA NRI, BLS, BEA RIMS II, Congress.gov). The methodology appendix describes the computation approach (area-weighted NRI aggregation, RIMS II multiplier methodology, etc.) without attributing the pipeline to any entity.
- **Regional coordination sections (Doc C):** Framed as "coordinated Tribal approaches" and "regional alignment," not as outputs of any named coordination body.

### What IS Attributed

Federal data sources are cited explicitly and specifically (see Question 3). The documents present themselves as data products, not organizational products.

---

## 2. Narrative Voice & Tone

### Guiding Framework: Story of Self, Story of Us, Story of Now

Documents follow public narrative structure but compressed for rapid digestion. A congressional staffer should be able to extract the core message from any section in under 2 minutes.

**Story of Self (Tribe-specific):**
- Who is this Tribe, where are they, what do they face
- Specific hazards from NRI data, specific award history from USASpending
- Grounded in place and lived reality, not abstract policy language

**Story of Us (regional/InterTribal):**
- Shared hazards across Tribes in the region
- Shared congressional delegations, shared program dependencies
- "These Tribes face common challenges that common solutions serve"

**Story of Now (urgency without partisanship):**
- Actionable deadlines (BIL final year, NCAR feedback deadline, DHS funding cliff)
- Concrete asks tied to specific programs and dollar amounts
- Evidence-first: "Here is what was funded. Here is what is not reaching communities."

### Voice Calibration by Document Type

**Doc A / Doc C (Internal Strategy):**
- Assertive, strategic, direct
- Names political dynamics plainly: "This member sits on Appropriations and voted for the bill. The ask is oversight."
- Uses imperative framing: "Prioritize meeting with [Member] before [deadline]"
- Includes "why this matters" strategic context that would not appear in a handoff document
- The "Congress funded; Administration not delivering" frame is stated clearly and used as the organizing principle for all program analyses
- Sovereignty language is explicit: "Tribal self-determination," "trust responsibility," "treaty obligations," "government-to-government relationship"

**Doc B / Doc D (Congressional):**
- Objective, factual, measured
- Same underlying facts, different posture: statements of record rather than strategic interpretation
- The "Congress funded; Administration not delivering" frame is **implicit**, not stated as a strategic frame. Instead, each program section simply presents: (1) what Congress appropriated, (2) current program status, (3) what the Tribe/region is requesting. The reader draws the conclusion.
- Reads like a well-sourced briefing memo, not an advocacy playbook
- Tone: respectful of the reader's intelligence, does not oversell, lets the evidence carry the argument
- Digestibility target: any single hot sheet or section readable in under 2 minutes. Executive summary readable in under 1 minute.

### Language Calibration for Current Political Context

Documents recognize the current administration's priorities and messaging:

**Avoid in congressional-facing docs (Doc B/D):**
- Leading with "climate change" framing (use "extreme weather resilience," "natural hazard preparedness," "community resilience" instead)
- Partisan characterization of administrative actions (state facts without editorial)
- Language that reads as oppositional to the administration

**Lean into in congressional-facing docs (Doc B/D):**
- Tribal sovereignty and self-determination (aligns with current administration's stated support)
- Economic development and job creation in Tribal communities
- Public safety and disaster preparedness
- Infrastructure resilience and protection of federal investment
- Trust responsibility as a legal obligation, not a policy preference
- Bipartisan framing: "Congress made bipartisan funding decisions"
- Return on investment: "$4 return per $1 in federal mitigation investment" (FEMA/NIBS)

**Internal docs (Doc A/C) can be direct** about the political landscape, including naming the tension between the administration's stated support for Tribal sovereignty and its actions on climate program delivery. Internal docs serve strategic preparation; they can name what congressional docs cannot.

---

## 3. Content Classification Line

### The Dividing Line

The classification boundary falls between **interpretation** and **fact**:

| Internal Only (Doc A/C) | Congressional Safe (Doc B/D) |
|---|---|
| "This member is your strongest ally on Appropriations because they voted for the Interior bill and sit on the subcommittee that funds BIA-TCR" | "Sen. [Name] sits on the Senate Committee on Appropriations, Subcommittee on Interior, Environment, and Related Agencies" |
| "Approach Sen. [Name] with the economic development frame, not the trust responsibility frame, given their voting record on [bill]" | "This program supports economic development and resilience infrastructure in [district/state]" |
| "The cooperative agreement consolidation creates a narrow window to shape scope. Push for oversight hearings before the window closes." | "The BIA is restructuring cooperative agreements from multiple agreements to five consolidated agreements. The FY2026 timeline for this restructuring coincides with BIL final-year fund obligations." |
| "FEMA's cancellation of BRIC while holding $7-8B in the DRF is an Impoundment Control Act question. This is the lever." | "FEMA announced termination of BRIC on April 4, 2025. The Disaster Relief Fund holds approximately $7-8 billion in unobligated resources. IIJA provided $200M/year through FY2026 for pre-disaster mitigation." |
| "Sequence: brief [Member A] first to build committee momentum before approaching [Member B]" | (Does not appear in any form) |

### Specific Classification Rules

**INTERNAL ONLY (never appears in Doc B/D):**
- Member-by-member approach recommendations
- Sequencing strategy (who to meet first and why)
- Voting record analysis or political characterization of members
- "Leverage" language (pressure points, political dynamics, windows of opportunity)
- Messaging framework (audience-calibrated talking points)
- Strategic framing advice ("use trust responsibility frame with this member")
- References to other Tribes' strategies or coordinated sequencing
- Characterization of administrative actions as "hollowing," "withholding," or "circumventing"
- Impoundment Control Act framing or similar legal-strategic positioning

**CONGRESSIONAL SAFE (appears in Doc B/D):**
- Committee assignments (factual, from congress.gov)
- Appropriations amounts (factual, from enacted bills)
- Program status (factual: enacted, proposed, canceled, uncertain)
- Award history (factual, from USASpending)
- Hazard scores and rankings (factual, from FEMA NRI)
- Economic impact estimates with methodology citation (BEA RIMS II, BLS)
- District overlap percentages (factual, from geographic analysis)
- Policy alignment statements ("This program advances infrastructure resilience consistent with [statute/authority]")
- Treaty and trust responsibility as legal context (not as advocacy framing)
- Structural policy recommendations (multi-year stability, cost-share relief, direct access) framed as policy improvements, not tactical asks
- Specific funding amounts requested with evidence basis

### Data Source Attribution

**Every factual claim in every document cites its source.** The tool itself is never mentioned, but the federal data pipelines are cited explicitly:

- Award amounts: "Source: USASpending.gov, FY[XX]-FY[XX], CFDA [number]"
- Hazard scores: "Source: FEMA National Risk Index, county-level data aggregated to Tribal geographic boundaries"
- Economic impact: "Methodology: BEA RIMS II regional input-output multipliers (output multiplier range 1.8-2.4x); BLS employment requirements tables"
- Mitigation ROI: "Source: FEMA/NIBS Natural Hazard Mitigation Saves (MitSaves) 2018 Interim Report"
- Congressional data: "Source: Congress.gov, 119th Congress committee assignments"
- Appropriations figures: "Source: Consolidated Appropriations Act, 2026 (H.R. 7148); Interior-Environment/CJS/Energy-Water minibus (signed January 23, 2026)"
- Wildfire risk: "Source: USFS Wildfire Risk to Communities dataset"

This level of citation specificity means any congressional staffer can independently verify any number in the document. That is the design intent: the documents are credible because their data is traceable, not because an organization vouches for them.

---

## 4. Regional Document Identity

### Regional Definitions

Regions are defined by geographic and adaptive alignment, grouping Tribes that face common hazards and where similar adaptive and mitigative measures apply. The regions are:

| Region ID | Region Name | Adaptive/Mitigative Alignment |
|---|---|---|
| `pnw` | Pacific Northwest / Columbia River Basin | Drought, fisheries, snowpack, wildfire, treaty salmon, flood |
| `alaska` | Alaska | Permafrost, coastal erosion, displacement/relocation, infrastructure failure |
| `plains` | Great Plains / Northern Plains | Drought, extreme heat, water scarcity, wind energy, rangeland |
| `southwest` | Southwest / Great Basin | Drought, wildfire, extreme heat, water rights, solar energy |
| `greatlakes` | Great Lakes / Midwest | Flooding, invasive species, PFAS, algal blooms, treaty resources |
| `southeast` | Southeast / Gulf Coast / Five Tribes | Hurricanes, sea level rise, displacement, coastal resilience |
| `northeast` | Northeast / Mid-Atlantic / South and Eastern Tribes | Coastal flooding, sea level rise, precipitation, recognition intersection |
| `crosscutting` | Cross-Cutting (all regions) | Science infrastructure, NCAR, NSF, 638/CSC, structural policy |

The `southeast` region includes the Five Tribes (Cherokee, Chickasaw, Choctaw, Creek/Muscogee, Seminole) and other Southern and Eastern Tribal Nations. The `northeast` region includes South and Eastern Tribes with distinct federal recognition and land-into-trust dynamics. Ecoregion breakdowns within each region align Tribes facing the same hazard profile and where the same federal programs apply.

### Who "Owns" the Regional Narrative

Nobody owns it. The regional documents present **observed patterns in federal data** across Tribes in the same geography:

- "X Tribes in this region share [hazard] as a top-3 risk"
- "Y Tribes in this region have received awards from [program]"
- "Z Tribes in this region share congressional representation through [members]"
- "Coordinated investment in [program] across the region would serve [number] communities facing [shared hazard]"

The regional narrative is not positioned as the output of a coordination body. It is positioned as what the data shows when you look at the region as a whole.

### Internal Regional Framing (Doc C)

Doc C outlines the coordinated approach in strategic terms:

- **Funding equity:** Shows which Tribes in the region have received federal climate resilience investment and which have not. Identifies gaps where first-time applicants could be strategically supported. Frames coordination as ensuring that federal investment serves the region as a whole rather than concentrating in Tribes with existing grant-writing capacity.
- **Optimized resource distribution:** Shows where program expertise exists in the region (Tribes that have successfully navigated specific programs) and how that expertise could inform regional approaches. Identifies where shared technical assistance, joint applications, or complementary proposals would strengthen outcomes for all.
- **Delegation alignment:** Maps which congressional members represent multiple Tribes in the region and where coordinated asks from multiple Tribes to the same member create a stronger signal.
- **Sequencing and coordination:** Recommends how Tribes in the region could align meeting schedules, joint letters, and testimony to present a unified regional voice.

The word "federation" does not appear. The concept is operationalized through the data: "Here is what coordinated action looks like, here is why it serves everyone better."

### Congressional Regional Framing (Doc D)

Doc D makes the regional case in terms that resonate with congressional priorities and the current administration's stated values:

**Public safety and disaster preparedness:**
- "X Tribes across Y states face [shared hazard]. Federal investment in resilience infrastructure protects communities and reduces future disaster response costs."
- Mitigation ROI data at regional scale: "Aggregate federal mitigation investment across the region generates an estimated $[X] in avoided future costs."

**Economic benefit, state and region-wide:**
- Aggregate economic impact: "Federal climate resilience programs in this region support an estimated [X] jobs and generate $[Y] in regional economic activity."
- Per-state breakdowns where relevant
- "These investments benefit Tribal and non-Tribal communities alike through shared infrastructure, regional economic activity, and reduced disaster burden on state and federal emergency systems."

**Tribal sovereignty and economic development:**
- Aligned with the current administration's stated commitment to Tribal sovereignty and self-determination
- "Tribal Nations in this region are pursuing energy sovereignty, infrastructure resilience, and economic development through these federal programs."
- "Self-determination contracts and self-governance compacts under ISDEAA enable Tribes to administer these programs directly, reducing federal overhead and increasing community impact."

**Resilience against extreme weather vulnerability:**
- Uses "extreme weather," "natural hazards," "community resilience," "infrastructure protection" (not "climate change" as the lead frame)
- Connects to bipartisan infrastructure investment (IIJA/BIL) framing
- "These programs protect federal infrastructure investments from natural hazard risks"

**Resource utilization and accountability:**
- "Congress appropriated $[X] for these programs in FY2026. This overview documents how those funds serve Tribal communities in [region] and the economic returns they generate."
- Positions the document as a resource utilization report, not an advocacy document

**What Doc D does NOT contain:**
- The word "federation" or "coordinated strategy"
- References to inter-Tribal coordination mechanisms
- Funding equity analysis (that is internal strategic framing)
- Characterization of administrative actions
- Sequencing or approach recommendations

Doc D simply shows: here are the Tribes, here are the hazards, here are the programs, here is the economic impact, here is what the region needs. The coordination benefit is implicit in the aggregate numbers.

---

## Summary: Classification Quick Reference

```
                    INTERNAL (Doc A/C)              CONGRESSIONAL (Doc B/D)
                    ──────────────────              ───────────────────────
Attribution         None (descriptive metadata)     None (descriptive metadata)
Org names           Never                           Never
Voice               Strategic, assertive, direct    Objective, factual, measured
Frame               "Congress funded; Admin not      Implicit (facts speak)
                     delivering" (explicit)
Climate language    Can use freely                  "Extreme weather resilience,"
                                                     "natural hazards," "community
                                                     resilience"
Sovereignty         Explicit strategic framing      Legal context, economic
                                                     development alignment
Leverage            Yes (per-program, per-member)   No
Approach strategy   Yes (sequencing, framing recs)  No
Messaging framework Yes                             No
Member analysis     Strategic notes + voting record Committee assignments only
Coordination        Funding equity, sequencing,     Regional benefits, aggregate
                     resource sharing                economic impact
Regional frame      Coordinated approach serves     Public safety, economic
                     all Tribes in region            benefit, infrastructure
                                                     resilience, sovereignty
Data sources        Cited                           Cited (same level of detail)
Tool attribution    Never                           Never
```

---

*Addendum created: 2026-02-11*
*Answers questions 1-4 of Phase 14 architecture interview*
*Drop into repo at: plans/PHASE-14-DESIGN-DECISIONS.md*
