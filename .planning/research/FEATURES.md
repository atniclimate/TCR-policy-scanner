# Feature Landscape: Tribe-Specific Advocacy Packet Generation

**Domain:** Per-Tribe congressional advocacy intelligence packets (DOCX) for 574 federally recognized Tribes
**Researched:** 2026-02-10
**Confidence:** MEDIUM overall (data source availability HIGH, domain patterns MEDIUM, batch performance LOW)

---

## Table Stakes

Features users expect. Missing any of these and the packet is not usable for its intended purpose (walking into a congressional office with a Tribe-specific document).

### TS-01: Per-Tribe Document Identity

| Attribute | Value |
|-----------|-------|
| **Description** | Each DOCX packet names the Tribe in its title, headers, and cover page. Congressional staff must see "Navajo Nation Climate Resilience Program Priorities" not a generic document. |
| **Why Expected** | A congressional staffer receiving a generic "Tribal climate priorities" document will treat it as background noise. A document titled with the specific Tribe attending the meeting demands engagement. |
| **Complexity** | Low |
| **Dependencies** | Tribal Registry (new data layer mapping 574 Tribes to states, ecoregions) |
| **Existing Assets** | None -- v1.0 produces a single shared briefing, not per-Tribe |

### TS-02: Per-Program Hot Sheets with Tribe-Specific Data

| Attribute | Value |
|-----------|-------|
| **Description** | Each of the 16 tracked programs gets a "Hot Sheet" section in the per-Tribe DOCX. Each Hot Sheet includes: program status (CI, advocacy goal), Tribe-specific award history, local hazard relevance, district economic impact, and congressional delegation. This is the core content unit. |
| **Why Expected** | The existing Hot Sheets format (from ATNI/NCAI conventions) is how Tribal policy staff consume program information. Each program gets its own page or section. The scanner must replicate this structure but populate it with Tribe-localized data. |
| **Complexity** | High -- requires data assembly from 5 distinct sources per Tribe per program |
| **Dependencies** | USASpending award matching (existing scraper), hazard profiling (new), economic impact (new), congressional mapping (new), program inventory (existing) |
| **Existing Assets** | 16-program inventory with CI scores, advocacy goals, advocacy levers, tightened language, Hot Sheets status -- all reusable |

### TS-03: Congressional Delegation Section

| Attribute | Value |
|-----------|-------|
| **Description** | Each packet identifies the Tribe's senators (2 per state), House representative(s), and their committee assignments relevant to the 16 programs (e.g., Appropriations, Energy & Natural Resources, Indian Affairs). |
| **Why Expected** | Advocacy packets exist to facilitate meetings with specific Members of Congress. If the packet does not name the Tribe's delegation and their committee power, the packet fails its primary purpose. |
| **Complexity** | Medium |
| **Dependencies** | Tribal Registry (state), Census TIGER (Tribe-to-district mapping), Congress.gov API (members/committees -- API key already available) |
| **Existing Assets** | Congress.gov scraper (v1.0) already has API key and session management; needs new endpoint queries for members/committees |

### TS-04: USASpending Award History Per Tribe Per Program

| Attribute | Value |
|-----------|-------|
| **Description** | For each program Hot Sheet, show the Tribe's award history: total obligations, fiscal years, project descriptions. "Navajo Nation received $2.3M under BIA TCR across FY22-FY25 for drought adaptation planning." |
| **Why Expected** | Congressional staff evaluate advocacy asks against a Tribe's track record. "We have successfully used this program before" is the most persuasive single sentence in an advocacy meeting. Absence of this data makes the packet purely aspirational rather than evidence-based. |
| **Complexity** | High -- fuzzy name matching between USASpending recipient names and the 574 official Tribal names is the hardest data-quality problem in the system |
| **Dependencies** | USASpending API (existing scraper, needs new recipient-search queries), Tribal Registry (canonical names + known aliases) |
| **Existing Assets** | USASpendingScraper already queries by CFDA with retry logic; needs extension to query by recipient_search_text |
| **Key Risk** | Tribal names in USASpending are inconsistently recorded. "Navajo Nation" vs "The Navajo Nation" vs "Navajo Tribal Utility Authority" vs "Navajo Nation Division of Natural Resources". Fuzzy matching must be conservative (prefer false negatives over false positives -- attributing the wrong Tribe's awards is worse than showing no data). |

### TS-05: Advocacy Language Per Program

| Attribute | Value |
|-----------|-------|
| **Description** | Each Hot Sheet includes ready-made advocacy language: what to ask, why it matters, and the structural frame (trust responsibility, sovereignty, climate justice). Derived from the decision engine's advocacy goal + the tightened language already in program_inventory.json. |
| **Why Expected** | Tribal policy staff need talking points they can hand to a leader walking into a meeting. Raw data without framing is not actionable. The existing advocacy_lever, tightened_language, and Five Structural Asks provide the raw material. |
| **Complexity** | Medium |
| **Dependencies** | Decision engine classifications (existing), program inventory tightened_language (existing), Five Structural Asks (existing graph nodes) |
| **Existing Assets** | ADVOCACY_GOALS mapping, per-program tightened_language, structural asks with ADVANCES edges |

### TS-06: DOCX Output Format

| Attribute | Value |
|-----------|-------|
| **Description** | Output as Microsoft Word DOCX files. Not PDF, not Markdown, not HTML. Congressional offices work in Word. Tribal policy staff need to edit before distribution (add political context, adjust talking points for the specific meeting). |
| **Why Expected** | Confirmed by domain requirements. Congressional offices print and share Word documents. Editability is essential -- these are drafts that a policy analyst reviews before distribution. |
| **Complexity** | Medium -- python-docx is well-documented for programmatic generation, but achieving professional formatting (consistent styles, headers/footers, page breaks, tables) requires careful implementation |
| **Dependencies** | python-docx library (new dependency) |
| **Existing Assets** | None -- v1.0 generates Markdown and JSON only |

### TS-07: Shared Strategic Overview Document (Document 2)

| Attribute | Value |
|-----------|-------|
| **Description** | A single shared DOCX document covering the overall FY26 funding landscape: appropriations status, 7 ecoregion strategic priorities, science infrastructure threats, FEMA analysis, cross-cutting framework, and messaging guidance. Not per-Tribe -- used as a companion to the per-Tribe packet. |
| **Why Expected** | The per-Tribe document answers "what matters to YOUR Tribe." The shared document answers "what is the overall landscape." Both are needed for effective advocacy. A Tribal leader needs context beyond their specific programs. |
| **Complexity** | Medium |
| **Dependencies** | Monitor data (existing), program inventory (existing), ecoregion framework (new static data), appropriations landscape (partially in existing CI data) |
| **Existing Assets** | 14-section briefing already contains reconciliation watch, IIJA countdown, CI dashboard, advocacy goals, structural asks -- much of this content maps to Document 2 sections |

### TS-08: Batch and Ad-Hoc Generation Modes

| Attribute | Value |
|-----------|-------|
| **Description** | CLI supports two modes: (1) batch -- generate packets for all 574 Tribes; (2) ad-hoc -- generate a single Tribe's packet by name or ID. Batch is for pre-event preparation. Ad-hoc is for when a specific Tribe requests their packet. |
| **Why Expected** | Before NCAI Mid-Year, staff run batch to prepare 574 packets. When a Tribal leader calls asking for their packet before a congressional meeting next week, staff run ad-hoc. Both use cases are routine. |
| **Complexity** | Low (CLI flag routing) |
| **Dependencies** | DOCX generation engine (TS-06), Tribal Registry (TS-01) |
| **Existing Assets** | main.py CLI pattern with argparse; add --generate-packets and --tribe flags |

---

## Differentiators

Features that set this system apart from manual advocacy packet preparation. Not expected (nobody else automates this), but uniquely valuable.

### DF-01: Hazard Profiling Per Tribe

| Attribute | Value |
|-----------|-------|
| **Description** | Each Tribe's packet includes localized hazard data: top natural hazard risks from FEMA NRI (18 hazard types), wildfire risk from USFS, and climate projections. "Standing Rock Sioux Tribe: HIGH risk for drought, MODERATE risk for wildfire, inland flooding." |
| **Value Proposition** | Transforms the packet from a funding document to a climate intelligence document. Congressional staff see that the ask is grounded in local risk data, not just generic climate concerns. No other Tribal advocacy tool combines federal hazard data with program-level funding asks. |
| **Complexity** | High -- requires ingesting and cross-referencing FEMA NRI tribal datasets (shapefile/CSV), USFS wildfire risk data, and mapping Tribal areas to hazard zones. The data exists in downloadable form but is large and geospatially complex. |
| **Dependencies** | FEMA NRI tribal datasets (free download, CSV/shapefile/geodatabase, 18 hazard types, v1.20 Dec 2025), USFS Wildfire Risk to Communities (free download, includes tribal areas in tabular spreadsheet), Tribal Registry (geographic mapping) |
| **Data Availability** | HIGH confidence. FEMA NRI provides dedicated tribal datasets in multiple formats. USFS wildfire risk includes tribal areas in tabular downloads. Both are free, T0 public data. |

### DF-02: District Economic Impact Framing

| Attribute | Value |
|-----------|-------|
| **Description** | For each program, frame the economic impact in the congressional district: USASpending obligations multiplied by regional economic multipliers to show jobs/output impact, plus FEMA 4:1 benefit-cost ratio for pre-disaster mitigation. "BIA TCR funding to [Tribe] generated an estimated $X in economic activity in [District], supporting Y jobs." |
| **Value Proposition** | Congressional staff think in district terms. A dollar spent in their district matters more than a dollar spent nationally. This reframes Tribal program funding as a district economic investment, which is the most persuasive framing for appropriations defense. |
| **Complexity** | Medium-High |
| **Dependencies** | USASpending obligation data (TS-04), congressional district mapping (TS-03), BEA regional multipliers or proxy multipliers |
| **Key Risk** | BEA RIMS II multipliers cost $500 per region (as of Aug 2025). For 574 Tribes across potentially hundreds of regions, this is cost-prohibitive. **Recommendation:** Use published literature-based standard multipliers (2.0x for direct spending, 1.5x for indirect) plus FEMA's established 4:1 pre-disaster mitigation BCR rather than purchasing RIMS II data. This is standard practice in federal advocacy -- the exact multiplier matters less than the framing. Congressional staff are accustomed to standard multiplier ranges. |

### DF-03: Change Tracking ("Since Last Packet" Diffs)

| Attribute | Value |
|-----------|-------|
| **Description** | Each packet includes a "What Changed" section showing shifts since the last time that Tribe's packet was generated: CI status changes, new legislative threats, funding amount changes, new grant opportunities, advocacy goal reclassifications. |
| **Value Proposition** | Tribal leaders attend multiple advocacy events per year. Without diff tracking, every packet looks the same and loses urgency. "Since your NCAI Mid-Year packet: FEMA BRIC status changed from AT_RISK to FLAGGED" creates immediate actionability. |
| **Complexity** | Medium |
| **Dependencies** | Per-Tribe packet state persistence (new -- store last-generated state per Tribe), change detection logic (existing ChangeDetector pattern adaptable) |
| **Existing Assets** | ChangeDetector class compares scan-to-scan; needs adaptation for packet-to-packet comparison. CI history tracking (90-entry cap) provides trend data. |

### DF-04: Ecoregion Priority Framework

| Attribute | Value |
|-----------|-------|
| **Description** | Each Tribe is classified into one of 7 ecoregions. The packet sections and program prioritization reflect ecoregion-specific priorities (e.g., Arctic/subarctic Tribes prioritize permafrost and coastal erosion; Southwest Tribes prioritize drought and wildfire). |
| **Value Proposition** | Avoids the trap of generic climate messaging. A Tribe in coastal Louisiana has fundamentally different climate priorities than a Tribe in interior Alaska. Ecoregion classification enables automatic prioritization without manual per-Tribe customization. |
| **Complexity** | Medium |
| **Dependencies** | Tribal Registry with ecoregion classification (new static data layer), ecoregion-to-program priority mapping (new static configuration) |
| **Existing Assets** | 7 ecoregion framework referenced in project scope; needs encoding as data |

### DF-05: Five Structural Asks Integration

| Attribute | Value |
|-----------|-------|
| **Description** | Each packet weaves the Five Structural Asks (cross-cutting advocacy levers from the knowledge graph) into the per-program Hot Sheets, showing which structural asks advance which programs relevant to that Tribe. |
| **Value Proposition** | Connects per-program advocacy to the broader strategic framework. A Tribal leader can say "we support Structural Ask #3 because it directly advances three programs that serve our community." |
| **Complexity** | Low |
| **Dependencies** | Knowledge graph ADVANCES edges (existing), Five Structural Asks nodes (existing) |
| **Existing Assets** | 5 structural ask nodes, 26 ADVANCES edges, 9 MITIGATED_BY edges -- all in the existing graph |

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain that would waste effort or cause harm.

### AF-01: DO NOT Build a Per-Tribe Data Collection Layer

| Anti-Feature | Tribal-specific sensitive data collection (enrollment data, internal governance documents, internal climate adaptation plans, cultural resource locations) |
| **Why Avoid** | The project is classified T0 (Open) -- all data from public federal sources. Collecting Tribal-specific sensitive data would (a) violate data sovereignty principles, (b) require Tribal consent protocols that are outside this project's scope, (c) create security/privacy obligations the system is not designed for, (d) potentially expose sensitive cultural or governance information. |
| **What to Do Instead** | Use only public federal data (USASpending, FEMA NRI, Census TIGER, Congress.gov) to construct Tribe-specific views. The Tribe's own data remains under Tribal control. The system tells Tribes what the federal government's data says about programs serving them -- not what the Tribe itself has shared. |

### AF-02: DO NOT Build an AI/LLM Text Generation Layer

| Anti-Feature | Using an LLM to generate advocacy talking points, narrative summaries, or policy analysis text |
| **Why Avoid** | (a) Hallucination risk in a domain where factual accuracy has legal and political consequences. A wrong dollar figure or misattributed program status in a congressional meeting damages credibility irreparably. (b) Tribal advocacy language carries cultural and political nuance that cannot be reliably generated by AI. (c) The existing tightened_language, advocacy_lever, and structural asks fields already provide human-authored advocacy framing. (d) Congressional offices are increasingly skeptical of AI-generated content. |
| **What to Do Instead** | Use template-based text assembly from verified data fields. The decision engine and program inventory already contain human-authored advocacy language. Assemble, do not generate. |

### AF-03: DO NOT Build Real-Time Document Editing / Collaboration

| Anti-Feature | In-browser document editing, track changes review workflow, multi-user collaboration on packets |
| **Why Avoid** | The system generates DOCX files that are opened in Microsoft Word for editing. Tribal policy staff already have Word-based review workflows. Building a parallel editing system (a) duplicates existing tools, (b) adds massive frontend complexity, (c) is not what users asked for. |
| **What to Do Instead** | Generate clean, well-structured DOCX files that open correctly in Word. Let the existing Word-based review workflow handle editing. |

### AF-04: DO NOT Attempt Per-Tribe Customized Program Selection

| Anti-Feature | Automatically selecting which of the 16 programs to include based on a Tribe's characteristics (dropping "irrelevant" programs) |
| **Why Avoid** | All 16 programs are relevant to all 574 Tribes at the policy advocacy level. A Tribe that has never received FEMA BRIC funding still advocates for the program because (a) they might apply in the future, (b) the program's policy status affects the broader funding ecosystem, (c) structural asks cross-cut all programs. Automatically dropping programs based on award history or geography would reduce advocacy surface area. |
| **What to Do Instead** | Include all 16 programs in every packet. Vary the Tribe-specific data (some programs will show award history, others will show "No awards to date -- potential new program for [Tribe]"). The absence of data is itself informative. |

### AF-05: DO NOT Build a Frontend Dashboard or Web UI

| Anti-Feature | A web application for browsing/generating packets |
| **Why Avoid** | Explicitly out of scope per project constraints. The users are policy analysts running CLI tools on a schedule. A web UI adds deployment complexity (hosting, auth, CORS, etc.) that provides no value for the current user base. |
| **What to Do Instead** | CLI with clear flags (--generate-packets --tribe "Navajo Nation" or --generate-packets --batch). Integrate with existing GitHub Actions for batch runs. |

### AF-06: DO NOT Purchase BEA RIMS II Multiplier Data

| Anti-Feature | Spending $500+ per region on official RIMS II multipliers for economic impact calculations |
| **Why Avoid** | (a) Cost-prohibitive at scale (hundreds of regions). (b) The precision of RIMS II is not needed for advocacy framing -- congressional staff expect approximate multiplier ranges, not precise input-output coefficients. (c) Standard federal advocacy practice uses literature-based multiplier estimates. |
| **What to Do Instead** | Use established, citable standard multipliers: ~2.0x total output multiplier for direct federal spending (published range for government grants), plus FEMA's documented 4:1 benefit-cost ratio for pre-disaster mitigation investments. Cite the sources (e.g., "FEMA estimates every $1 invested in pre-disaster mitigation saves $4 in future disaster costs"). |

---

## Feature Dependencies

```
                       Tribal Registry (TS-01)
                      /      |       |        \
                     /       |       |         \
         Congressional    USASpending  Hazard     Ecoregion
         Mapping (TS-03)  Awards (TS-04)  Profiling   Framework
              |               |         (DF-01)    (DF-04)
              |               |            |           |
              +-------+-------+-----+------+-----------+
                      |             |
                 DOCX Engine     Economic
                 (TS-06)        Impact (DF-02)
                      |             |
              +-------+-------------+
              |
         Per-Program Hot Sheets (TS-02)
              |
         Advocacy Language (TS-05)
              |
         Structural Asks (DF-05)
              |
    +----+----+----+
    |              |
 Document 1    Document 2
 Per-Tribe     Shared
 (TS-01)      (TS-07)
    |              |
 Change Tracking (DF-03)
    |
 Batch/Ad-Hoc CLI (TS-08)
```

Critical path: Tribal Registry --> Congressional Mapping + USASpending Awards + Hazard Profiling --> DOCX Engine --> Hot Sheets Assembly --> CLI Integration

### Dependency Details

| Feature | Hard Dependencies | Soft Dependencies |
|---------|-------------------|-------------------|
| TS-01 Per-Tribe Identity | Tribal Registry data | -- |
| TS-02 Hot Sheets | TS-01, TS-03, TS-04, TS-05, TS-06 | DF-01, DF-02, DF-04, DF-05 |
| TS-03 Congressional Delegation | Tribal Registry (state), Census TIGER, Congress.gov API | -- |
| TS-04 USASpending Awards | Tribal Registry (names + aliases), USASpending API | -- |
| TS-05 Advocacy Language | Decision engine (existing), program inventory (existing) | DF-05 structural asks |
| TS-06 DOCX Engine | python-docx library | -- |
| TS-07 Document 2 | TS-06, monitor data (existing) | DF-04 ecoregions |
| TS-08 Batch/Ad-Hoc CLI | TS-01, TS-06 | All other features |
| DF-01 Hazard Profiling | FEMA NRI data, USFS wildfire data, Tribal Registry | -- |
| DF-02 Economic Impact | TS-04, TS-03, standard multipliers | -- |
| DF-03 Change Tracking | Packet state persistence, TS-02 | -- |
| DF-04 Ecoregion Framework | Tribal Registry with ecoregion classification | -- |
| DF-05 Structural Asks | Knowledge graph (existing) | -- |

---

## MVP Recommendation

For an MVP that delivers usable per-Tribe advocacy packets:

### Phase 1: Foundation (Must Ship First)

1. **Tribal Registry** (TS-01) -- 574 Tribes mapped to states, ecoregions, known aliases for USASpending matching. This is the data backbone everything else depends on.
2. **DOCX Generation Engine** (TS-06) -- python-docx infrastructure for programmatic document construction. Styles, headers/footers, page breaks, tables.
3. **Document 2: Shared Strategic Overview** (TS-07) -- Easier to build first because it draws primarily from existing data (CI dashboard, monitors, structural asks). Validates the DOCX engine before tackling per-Tribe complexity.

### Phase 2: Per-Tribe Data Assembly

4. **Congressional Mapping** (TS-03) -- Census TIGER + Congress.gov API for delegation per Tribe.
5. **USASpending Award Matching** (TS-04) -- Per-Tribe per-program award history with conservative fuzzy matching.
6. **Hazard Profiling** (DF-01) -- FEMA NRI + USFS wildfire data per Tribe.

### Phase 3: Packet Assembly

7. **Per-Program Hot Sheets** (TS-02) -- Assemble Tribe-specific data into 16-program Hot Sheet format.
8. **Advocacy Language** (TS-05) -- Template-based talking points from existing program data.
9. **Structural Asks Integration** (DF-05) -- Weave structural asks into Hot Sheets.
10. **Document 1: Per-Tribe Program Priorities** (TS-01 + TS-02) -- Full per-Tribe DOCX.

### Phase 4: Operations

11. **Batch/Ad-Hoc CLI** (TS-08) -- Generation modes.
12. **Economic Impact Framing** (DF-02) -- Standard multipliers applied to USASpending data.
13. **Ecoregion Priority Framework** (DF-04) -- Priority ordering by ecoregion.
14. **Change Tracking** (DF-03) -- Since-last-packet diffs.

### Defer to Post-MVP

- **EPA EJScreen integration**: EJScreen was removed from EPA's website on Feb 5, 2025. Reconstructed versions exist at screening-tools.com (PEDP) but stability is uncertain. FEMA NRI + USFS wildfire data provide adequate hazard coverage without EJScreen. Revisit if/when EPA restores official access.
- **NOAA Climate Projections**: Native Climate (native-climate.com) provides tribal-specific projections for 633 tribally controlled areas using NASA NEX-GDDP-CMIP6 data. This is valuable but adds significant data integration complexity. FEMA NRI covers the essential hazard data; NOAA projections could enhance future versions.
- **Interactive packet preview**: CLI-only for now. A preview mode could render packet sections to console for quick validation.

---

## Data Source Availability Assessment

| Source | Status | Format | Cost | Confidence |
|--------|--------|--------|------|------------|
| BIA Tribal List | Available | Federal Register notice, EPA xlsx | Free | HIGH |
| Census TIGER | Available (2025 shapefiles released Sep 2025) | Shapefile | Free | HIGH |
| Congress.gov API | Available (API key in hand) | REST JSON | Free | HIGH |
| USASpending API | Available (already integrated) | REST JSON | Free | HIGH |
| FEMA NRI v1.20 | Available (Dec 2025 release) | CSV/shapefile/geodatabase | Free | HIGH |
| USFS Wildfire Risk | Available | Tabular spreadsheet, GIS | Free | HIGH |
| BEA RIMS II | Available but cost-prohibitive | Purchase per region | $500/region | N/A (not recommended) |
| EPA EJScreen | Removed from EPA Feb 2025 | Reconstructed at screening-tools.com | Free (unofficial) | LOW |
| NOAA Climate Projections | Available | API + download | Free | MEDIUM |
| Native Climate | Available | Open-access datasets | Free | MEDIUM |

---

## Sources

### Authoritative

- [FEMA National Risk Index Data](https://www.fema.gov/about/openfema/data-sets/national-risk-index-data) -- Tribal datasets in shapefile/CSV/geodatabase, 18 hazard types, v1.20 Dec 2025
- [FEMA NRI Data Resources](https://hazards.fema.gov/nri/data-resources) -- Download portal (redirects to RAPT as of Feb 2026)
- [USASpending API](https://api.usaspending.gov/) -- recipient_search_text filter, recipient_type_names filter
- [USASpending API search filters](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/search_filters.md) -- Documented filter parameters
- [Census TIGER/Line Shapefiles](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) -- 2025 shapefiles with congressional districts and tribal areas
- [Congress.gov API](https://gpo.congress.gov/) -- Members, committees, congressional districts
- [BIA Tribal Leaders Directory](https://www.bia.gov/service/tribal-leaders-directory) -- Official tribal listing
- [EPA Tribes Services](https://www.epa.gov/data/tribes-services) -- Tribe Entity Mapping Spreadsheet with BIA codes
- [USFS Wildfire Risk to Communities](https://wildfirerisk.org/download/) -- Tabular data including tribal areas
- [BEA RIMS II](https://apps.bea.gov/regional/rims/rimsii/) -- Regional multipliers ($500/region as of Aug 2025)
- [Native Climate Projections](https://native-climate.com/projections/) -- Tribal-specific climate projections for 633 areas

### Community/Research

- [EJScreen removal and reconstruction](https://screening-tools.com/epa-ejscreen) -- PEDP reconstruction of EJScreen v2.3
- [python-docx batch performance](https://github.com/python-openxml/python-docx/issues/158) -- Performance considerations for batch generation
- [NCAI Tribal Unity Impact Days](https://www.ncai.org/news/unity-25-strengthening-tribal-voices) -- 2025 tribal priorities including FY26 appropriations
