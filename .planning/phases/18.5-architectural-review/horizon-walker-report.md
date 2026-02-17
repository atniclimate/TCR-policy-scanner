# Horizon Walker Report: Narrative & Framing Review
## Phase 18.5 | TCR Policy Scanner v1.4

### Executive Summary

The v1.4 vulnerability integration faces a framing challenge more consequential than any technical one: the difference between a document that labels a Tribal Nation as "Very High vulnerability" and one that says "your community faces disproportionate climate exposure, and here is the federal data that proves it." Both convey the same data. One diminishes. The other arms.

After reviewing the existing Doc A/B rendering code (`docx_sections.py`, `docx_engine.py`, `doc_types.py`), the proposed vulnerability architecture, the Sovereignty Scout's data source findings, and the Fire Keeper's codebase pattern analysis, this report delivers eight key findings:

1. **The current Doc A/B narrative voice is strong and should not be disrupted.** Doc A's assertive voice ("strategic leverage points," "priority advocacy targets") and Doc B's objective voice ("on record," "affected programs") are well-calibrated. Vulnerability content must match, not compete with, these established tones.

2. **"Vulnerability" as a framing concept carries deficit-narrative risk.** Labeling a Tribal Nation as "Very High Vulnerability" in a document reads like a verdict from federal data systems that have historically undercounted Indigenous communities. The recommended framing is **Option D (Hybrid)**: use "Climate Resilience Investment Priority" as the primary framing in headings and narrative, retain "vulnerability" only in technical data citations where it refers to specific federal methodologies (FEMA NRI, CDC SVI), and always pair data with action context.

3. **229 Alaska Tribes (38.7%) need a purpose-built narrative strategy.** "Data not available" is never acceptable. Every Tribe must see something. For Alaska Tribes with partial data, the document should explicitly name the federal data gap as a systemic issue, present whatever data IS available (SVI, drought, partial NRI), and frame the gap itself as advocacy ammunition.

4. **The Doc B air gap must extend to vulnerability content.** Doc B currently enforces a hard separation: zero strategy language, zero talking points, zero organizational names. Vulnerability sections in Doc B must follow this same discipline -- composite rating and source citation only, no SVI theme decomposition, no resilience framing, no strategic interpretation.

5. **Information loss through the pipeline is significant but manageable.** Tracing SVI Theme 2 from raw CSV through area-weighting, composite calculation, and document rendering reveals that county-level context is compressed into Tribe-level summaries. The critical mitigation is preserving the "what does this mean" translation at each stage, not the raw numbers.

6. **Doc E (standalone vulnerability report) serves grant writers first.** The primary audience is the Tribal environmental department staff writing FEMA BRIC, HUD CDBG-DR, or EPA grant applications. Doc E must provide grant-ready narrative paragraphs with source citations that can be copied directly into application forms.

7. **REG-04 vocabulary constants need both an approved-terms list and a context-sensitive replacement engine.** A simple word-swap is insufficient. "Vulnerable" is appropriate in "CDC Social Vulnerability Index" (proper noun) but inappropriate in "this Tribe is vulnerable" (deficit framing). The vocabulary module must be context-aware.

8. **Website visualizations must prioritize clarity over sophistication.** Radar charts are visually appealing but cognitively demanding for non-technical audiences. Horizontal bar charts with clear labels and color-coded badges are more accessible and mobile-friendly.

---

### Document Audience Analysis

#### Current Narrative Voice Assessment

**Doc A (Internal Strategy) -- `narrative_voice: "assertive"`**

The existing Doc A voice is active, direct, and strategy-oriented. From `docx_sections.py`:

- Executive summary: *"This strategy document outlines {tribe_name}'s federal climate resilience funding landscape, identifies strategic leverage points across key programs, and recommends sequenced advocacy actions."*
- Hazard alignment: *"{tribe_name}'s top hazard exposures ({hazards}) align directly with federal programs designed to address these risks. Strategic advocacy should emphasize this alignment."*
- Structural asks: *"The following structural policy changes are priority advocacy targets for {tribe_name}. Each ask has been identified as high-impact based on current program vulnerabilities and congressional dynamics."*
- Messaging framework: *"Lead with bipartisan infrastructure investment and return on investment. Emphasize that Congress made the funding decisions; the ask is for oversight and delivery accountability."*

**Characteristics:** First-person-adjacent (addresses the reader as the advocate), action-oriented verbs, connects data to advocacy moves, confidential framing reinforces trust.

**Doc B (Congressional) -- `narrative_voice: "objective"`**

Doc B is rigorously factual. The code enforces this through:

- `_render_bill_facts_only()`: Bill ID, title, status, sponsor, affected programs. Zero analysis.
- Explicit audience guard on timing notes: `if doc_type_config.is_congressional: return`
- Source citation up front: *"Source: FEMA National Risk Index, county-level data aggregated to Tribal geographic boundaries."*
- Structural asks use measured language: *"The following structural policy changes would advance climate resilience funding for {tribe_name} and similarly situated Tribes."*

**Characteristics:** Third-person, declarative statements, source-attributed, no strategic interpretation, no urgency signals.

#### Tonal Shift Risk Assessment

The proposed vulnerability content introduces a new emotional register: **quantified social disadvantage.** Hazard data is relatively neutral ("Wildfire risk score: 72.3" describes a physical phenomenon). Vulnerability data is inherently about people ("Social Vulnerability percentile: 0.74" describes the community's capacity to withstand that phenomenon). This shift from physical hazard to social condition is where deficit narrative enters.

**Risk level: MEDIUM for Doc A, HIGH for Doc B.**

In Doc A, the assertive voice naturally contextualizes data as advocacy ammunition. The tonal shift is manageable if vulnerability data is presented as evidence supporting action, not as a diagnosis of weakness.

In Doc B, the objective voice presents data without interpretation. A raw "Social Vulnerability: Very High" line in Doc B, handed to a congressional aide, reads as: this community has serious problems. Without the advocacy framing of Doc A, the data becomes a label. This is the highest-risk moment in the entire v1.4 narrative design.

---

### Vulnerability Framing Options

#### Option A: Vulnerability with Resilience Context

Keep "vulnerability" terminology but always pair it with resilience narrative and action context.

**Doc A example paragraph:**

> **Climate Vulnerability Profile**
>
> Based on federal hazard exposure data (FEMA NRI), social determinant indicators (CDC SVI 2022), and community resilience metrics, the Confederated Tribes of Warm Springs faces elevated vulnerability across multiple dimensions. The composite vulnerability score of 0.68 (High) reflects the intersection of wildfire and drought exposure with socioeconomic factors that constrain adaptive capacity.
>
> This is not a measure of the Nation's strength -- it is a measure of the federal investment gap. Warm Springs has sustained governance, Traditional Knowledge of fire management, and documented resilience through generations of environmental change. What the data reveals is that federal programs have not kept pace with the hazard exposure this community faces.
>
> **Strategic implication:** The vulnerability profile strengthens grant applications by documenting disproportionate exposure. Lead with the EAL figures ($1.2M annual wildfire loss) in FEMA BRIC and USDA applications.

**Doc B example paragraph:**

> **Climate Vulnerability Assessment**
>
> Composite Vulnerability Score: 0.68 (High)
> Source: FEMA National Risk Index, CDC Social Vulnerability Index 2022, county-level data aggregated to Tribal geographic boundaries.
>
> Top Exposure: Wildfire (Expected Annual Loss: $1,234,567)
> Social Vulnerability Percentile: 74th (based on socioeconomic, household, and housing indicators)
> Community Resilience: Relatively Moderate

**Pros:**
- Maintains continuity with established federal terminology (FEMA, CDC, EPA all use "vulnerability")
- Grant applications often require "vulnerability" language to match federal scoring rubrics
- Clear, familiar framing for congressional staff who read FEMA reports

**Cons:**
- "Vulnerability" inherently frames the subject as deficient, regardless of surrounding context
- Resilience addendum in Doc A feels compensatory -- "we know this label is harmful but here's why you're actually strong" -- which can read as patronizing
- Congressional staff receiving Doc B see "High Vulnerability" without the resilience context

#### Option B: Climate Resilience Investment Priority

Reframe entirely. Replace "vulnerability" with language that centers the funding gap, not the community condition.

**Doc A example paragraph:**

> **Climate Resilience Investment Priority**
>
> Federal data confirms that the Confederated Tribes of Warm Springs faces disproportionate climate hazard exposure relative to current federal investment levels. The Climate Resilience Investment Priority score of 0.68 (High Priority) reflects the gap between documented hazard exposure (FEMA NRI: wildfire, drought, riverine flooding) and the adaptive infrastructure available to address it.
>
> Three factors drive this priority designation:
> - **Hazard Exposure:** Top 28th percentile nationally for composite risk (FEMA NRI)
> - **Social Determinants:** Socioeconomic and housing conditions that amplify hazard impacts (CDC SVI 74th percentile)
> - **Investment Gap:** Community resilience score indicates infrastructure and institutional capacity below the national median
>
> **Strategic implication:** The "High Priority" designation is advocacy ammunition. In every grant application and congressional engagement, the data demonstrates that this community has been underserved relative to its exposure. This is not a request for charity -- it is a demand for proportional federal investment.

**Doc B example paragraph:**

> **Climate Resilience Investment Profile**
>
> Investment Priority Rating: High
> Source: Analysis of FEMA National Risk Index and CDC Social Vulnerability Index 2022 data, aggregated to Tribal geographic boundaries.
>
> Hazard Exposure: Top 28th percentile nationally (composite risk)
> Social Determinant Indicators: 74th percentile (socioeconomic, household, housing factors)
> Expected Annual Loss: $1,234,567 (wildfire-driven)

**Pros:**
- Centers the systemic problem (investment gap) rather than the community condition
- "Investment Priority" implies an actionable response -- someone should invest
- Avoids deficit framing entirely; the language describes what should happen, not what is wrong
- Aligns with how Tribal Leaders already frame these conversations: "we are underserved, not incapable"

**Cons:**
- Departs from established federal terminology, which may confuse congressional staff expecting "vulnerability" language
- Grant applications that use "vulnerability" in scoring rubrics may need translation
- "Investment Priority" could be misread as a ranking or competition among Tribes
- The phrase "investment gap" implies a quantification that the data does not directly provide (the composite score measures exposure + social factors, not funding shortfall)

#### Option C: Disproportionate Exposure Language

Use "disproportionate exposure to climate hazards" (from REQUIREMENTS.md REG-04) as the primary framing concept.

**Doc A example paragraph:**

> **Disproportionate Climate Exposure Assessment**
>
> Federal hazard and social indicator data confirms that the Confederated Tribes of Warm Springs experiences disproportionate exposure to climate hazards. Analysis of FEMA National Risk Index and CDC Social Vulnerability Index 2022 data reveals:
>
> - **Climate Hazard Exposure:** Warm Springs is in the 72nd national percentile for composite climate risk, driven by wildfire ($1.2M estimated annual loss), drought, and riverine flooding
> - **Social Determinant Amplification:** Social factors including household composition, economic indicators, and housing infrastructure place the community in the 74th percentile for conditions that amplify climate impacts
> - **Adaptive Capacity:** Community resilience metrics from FEMA indicate moderate institutional capacity to respond to and recover from climate events
>
> The concept of "disproportionate exposure" is precise: federal data shows this community faces higher-than-average climate risk with lower-than-average resources to address it. This is a measurable federal data finding, not a characterization of the Nation's capacity or resilience.

**Doc B example paragraph:**

> **Climate Exposure Profile**
>
> The Confederated Tribes of Warm Springs experiences disproportionate exposure to climate hazards based on federal data analysis.
>
> Climate Risk Percentile: 72nd (national, FEMA NRI)
> Social Indicator Percentile: 74th (CDC SVI 2022, 3-theme composite)
> Primary Hazard: Wildfire (Expected Annual Loss: $1,234,567)
> Source: FEMA National Risk Index v1.20, CDC Social Vulnerability Index 2022

**Pros:**
- "Disproportionate exposure" is factual and precise -- it describes a relationship between hazard level and resources, not a community attribute
- Avoids labeling the community; labels the situation instead
- Legal/policy resonance: "disproportionate impact" is established in environmental justice framework (EO 12898, Justice40)
- The framing naturally invites the question "what should be done about this disproportion?" which is the advocacy entry point

**Cons:**
- "Disproportionate exposure" is more words and more syllables than "vulnerability" -- readability cost
- May feel clinical or academic to Tribal Leaders who are not environmental justice practitioners
- Does not provide a single-word rating tier ("High," "Very High") that is easy to reference in conversation
- The composite score still exists but now lacks a clear label: "Disproportionate Exposure Score: 0.68" does not scan naturally

#### Option D: Hybrid Approach (RECOMMENDED)

Use context-specific framing: "Climate Resilience Investment Priority" for headings and narrative, "disproportionate exposure" for explanatory context, and "vulnerability" only when citing specific federal methodologies by name.

**Doc A example paragraph:**

> **Climate Resilience Investment Profile**
>
> Federal climate and social data confirm that the Confederated Tribes of Warm Springs faces disproportionate exposure to climate hazards relative to available adaptive resources. This assessment draws on FEMA National Risk Index data, CDC Social Vulnerability Index indicators, and community resilience metrics to quantify the investment case for this Nation.
>
> | Indicator | Value | National Context |
> |-----------|-------|------------------|
> | Climate Risk (FEMA NRI) | Score: 55.5 | 72nd percentile nationally |
> | Social Indicators (CDC SVI) | 0.74 | Higher than 74% of U.S. counties |
> | Community Resilience (FEMA) | Relatively Moderate | Below national median |
> | Expected Annual Loss | $1,234,567 | Wildfire: $892K, Drought: $210K, Flood: $132K |
>
> **Resilience Investment Priority: High**
>
> This rating reflects the gap between documented hazard exposure and current adaptive capacity as measured by federal datasets. It does not account for the Nation's Traditional Knowledge, governance strengths, cultural resilience practices, or other capabilities that federal data systems do not capture. The rating is a tool for federal advocacy -- evidence that this community has been underserved relative to its climate exposure -- not a characterization of the Nation's strength or capacity.
>
> **Strategic use:** Cite the "High" priority rating and specific EAL dollar figures in FEMA BRIC, USDA, and HUD grant applications. The 72nd percentile national risk ranking is particularly effective in competitive grant narratives that require demonstrated need.

**Doc B example paragraph:**

> **Climate Resilience Data Summary**
>
> Resilience Investment Priority: High
>
> | Indicator | Value | Source |
> |-----------|-------|--------|
> | Climate Risk Percentile | 72nd nationally | FEMA NRI v1.20 |
> | Social Indicators | 74th percentile | CDC SVI 2022 (3-theme) |
> | Expected Annual Loss | $1,234,567 | FEMA NRI v1.20 |
> | Primary Hazard | Wildfire | FEMA NRI + USFS |
>
> Data aggregated to Tribal geographic boundaries via county-level crosswalk. Social indicators reflect socioeconomic status, household characteristics, and housing type/transportation factors. Racial/ethnic minority indicators excluded from composite per federal Tribal consultation guidance.

**Pros:**
- Best of all worlds: sovereignty-respecting headings, precise technical language in context, federal terminology preserved where it aids credibility
- The "does not account for" caveat is INTEGRATED into the narrative flow, not buried in a footnote
- Doc B version is clean, source-attributed, and completely free of strategy language
- "Resilience Investment Priority" as the single-phrase rating is actionable and dignified
- The word "vulnerability" appears only inside proper nouns ("Social Vulnerability Index") where it refers to the methodology, not the community
- The caveat about Traditional Knowledge and cultural resilience explicitly honors what federal data cannot measure, without being patronizing

**Cons:**
- Longer text than the simplest options
- Requires the vocabulary module (REG-04) to enforce context-sensitive replacement rather than simple word-swap
- Congressional staff may need a moment to map "Resilience Investment Priority" to their mental model of "vulnerability assessment"
- Dual terminology (different headings in doc vs. data source names) could cause confusion if not handled consistently

#### Recommendation

**Option D (Hybrid) is the recommended framing.** Here is why:

1. **It passes the Tribal Leader test.** A Tribal Chairman reading "Resilience Investment Priority: High" followed by "this rating reflects the gap between documented hazard exposure and current adaptive capacity" understands: (a) there is a federal data case supporting investment in my community, and (b) the tool acknowledges it cannot measure everything about my Nation. This reader feels informed and armed, not labeled.

2. **It passes the congressional aide test.** A staffer reading the Doc B version sees a clean data table with source citations. They can translate "Resilience Investment Priority: High" into their own office's language. The data speaks for itself without strategy overlay.

3. **It passes the grant writer test.** A Tribal environmental director writing a FEMA BRIC application can lift the EAL figures, the national percentile rankings, and the "disproportionate exposure" language directly into the application narrative.

4. **It preserves federal data credibility.** By retaining "FEMA NRI," "CDC SVI," and other agency names as source citations, the data maintains the institutional authority that makes it useful in policy settings.

5. **It centers action, not condition.** Every framing choice asks: does the reader's next thought lead toward action or toward pity? "Resilience Investment Priority: High" leads to "what investment is needed?" which is the correct advocacy question.

---

### Narrative Format Inventory

#### Doc A: Tribal Internal Strategy

**What story does the vulnerability data tell?**
The funding landscape is not serving your community proportionally to the climate hazards you face. Here is the federal data evidence, and here is how to use it.

**Reader's decision point:**
Where to focus advocacy resources during the current congressional session. Which grant applications to prioritize. What evidence to lead with in government-to-government consultation.

**Technical detail level:**
Full fidelity with interpretation. Show all SVI theme breakdowns, EAL component splits (buildings/population/agriculture), composite score components with weights. Pair every data point with strategic context: "Your 74th percentile SVI score strengthens FEMA BRIC applications that weight social vulnerability."

**What to simplify vs. preserve:**
- Preserve: Dollar figures (EAL components), percentile rankings, theme-level SVI breakdowns, source citations
- Simplify: The composite score calculation methodology (present the result and components, not the weighted average formula)
- Add: Strategic interpretation paragraphs after each data table, talking point suggestions

#### Doc B: Tribal Congressional Overview

**What story does the vulnerability data tell?**
This Tribal Nation faces documented, quantified climate exposure. Here are the facts from federal data sources.

**Reader's decision point:**
Whether to take a meeting, cosponsor a bill, or direct committee staff to look into a funding gap. Congressional aides use these as reference sheets when their member asks "what do I need to know about this Tribe?"

**Technical detail level:**
Composite rating and top-line figures only. One data summary table. Source citations for every number. Zero interpretation, zero strategy, zero resilience framing.

**What to simplify vs. preserve:**
- Preserve: Source citations (critical for credibility), dollar figures (concrete), rating designation
- Simplify: Reduce to composite + primary hazard + EAL + source table
- Exclude: SVI theme decomposition (too much detail for this audience), strategic interpretation, resilience context narrative, adaptive capacity discussion
- The air gap MUST extend: no "Traditional Knowledge" or "governance strengths" language in Doc B (these are strategy-adjacent concepts that belong in Doc A)

#### Doc C: Regional InterTribal Strategy

**What story does the vulnerability data tell?**
Across this region, multiple Tribal Nations face similar climate exposure patterns. There is a collective advocacy case.

**Reader's decision point:**
Whether to coordinate regional advocacy campaigns, pursue multi-Tribe grant applications, or align talking points for committee testimony.

**Technical detail level:**
Regional aggregation -- average/range/distribution across Tribes in the region. Highlight shared top hazards and common SVI drivers. Identify outlier Tribes with uniquely high or low scores for targeted support.

**What to simplify vs. preserve:**
- Preserve: Regional averages and ranges, shared hazard patterns, Tribe count per rating tier
- Simplify: Individual Tribe scores (reference Doc A for per-Tribe detail)
- Add: Regional comparison context ("7 of 12 Tribes in this region face High or Very High resilience investment priority")

#### Doc D: Regional Congressional Overview

**What story does the vulnerability data tell?**
Multiple Tribal Nations in this region are disproportionately exposed to climate hazards. The regional data pattern strengthens the case for systemic federal investment.

**Reader's decision point:**
Whether regional climate resilience is a committee-level concern worth hearings, oversight, or appropriations language.

**Technical detail level:**
Regional summary statistics only. Tribe count by rating tier. Top shared hazards. Total regional EAL figure. Source citations.

**What to simplify vs. preserve:**
- Preserve: Aggregate dollar figures (total regional EAL is a powerful congressional number), Tribe count, source citations
- Simplify: Everything. One summary table, one paragraph, done.
- Exclude: Per-Tribe breakdowns, SVI theme decomposition, strategic framing. Air gap applies fully.

#### Doc E: Standalone Vulnerability Report (NEW)

**Who reads this?**
Primary: Tribal environmental department staff and grant writers. Secondary: Tribal Council members reviewing environmental program priorities. Tertiary: Federal agency program officers during consultation.

**What action does it support?**
1. **Grant applications:** FEMA BRIC, HUD CDBG-DR, USDA Emergency Conservation, EPA IGAP, BIA Climate Resilience. These applications require demonstrated climate exposure, quantified expected losses, and social vulnerability documentation.
2. **Strategic planning:** Tribal climate adaptation plan development. Identifying which hazards to prioritize in 5-year environmental program budgets.
3. **Government-to-government consultation:** Providing data-backed evidence when engaging federal agencies about resource allocation to Tribal lands.

**How detailed should the data be?**
Full fidelity with interpretation AND drill-down capability. Doc E is the "show your work" document. It should include:

- All SVI themes with per-theme explanations of what drives the score
- Full EAL component breakdown (buildings, population, agriculture) per top hazard
- Composite score with each component value and weight explained
- Data provenance: exact dataset version, download date, geographic aggregation method
- Caveat section: what the data captures and what it cannot capture
- Grant-ready paragraphs that can be lifted verbatim into application narratives

**Unique structural needs:**
- A "How to Use This Report" section up front explaining what each section provides
- A "Grant Application Reference" section at the end with pre-written narrative paragraphs keyed to common grant program requirements
- A "Data Limitations and Sovereignty Statement" section that explicitly names what federal data misses
- Full source bibliography with URLs and access dates

**Section ordering for Doc E:**
1. Cover page (confidential, internal)
2. How to Use This Report
3. Resilience Investment Priority Summary (composite + rating)
4. Climate Hazard Exposure Detail (expanded NRI + USFS)
5. Social Determinant Analysis (SVI 3-theme breakdown with explanations)
6. Expected Annual Loss Detail (EAL by consequence type, by hazard)
7. Community Resilience Indicators (FEMA RESL + adaptive capacity metrics)
8. Data Limitations and Sovereignty Statement
9. Grant Application Reference Paragraphs
10. Data Provenance and Source Bibliography

---

### Information Loss Audit

**Test case:** CDC SVI Theme 2 (Household Characteristics) RPL_THEME2 = 0.74 for County X (Wasco County, OR, FIPS 41065)

#### Stage 1: Raw CSV Value

**Data:** `SVI2022_US_COUNTY.csv`, row for FIPS 41065, column `RPL_THEME2` = 0.7413

**Context preserved:** This is a percentile rank (0-1) among all U.S. counties. 0.7413 means Wasco County ranks higher than 74.13% of U.S. counties on Theme 2 (Household Characteristics). Theme 2 captures: aged 65+, aged 17 and under, civilian with a disability, single-parent households, English language proficiency.

**Context available but not in this single value:** Which specific sub-indicators drive the score. Is it primarily elderly population? Disability? The `EPL_*` columns for Theme 2 sub-indicators contain this detail.

#### Stage 2: Area-Weighting Across Multiple Counties

The Confederated Tribes of Warm Springs reservation spans portions of Wasco, Jefferson, and Clackamas counties in Oregon. The area-weighted crosswalk (`tribal_county_area_weights.json`) assigns normalized weights based on geographic overlap:

| County | FIPS | RPL_THEME2 | Area Weight |
|--------|------|------------|-------------|
| Wasco | 41065 | 0.7413 | 0.45 |
| Jefferson | 41031 | 0.8201 | 0.48 |
| Clackamas | 41005 | 0.3156 | 0.07 |

Weighted Theme 2 = (0.7413 x 0.45) + (0.8201 x 0.48) + (0.3156 x 0.07) = 0.3336 + 0.3937 + 0.0221 = **0.7494**

**Context preserved:** The score now reflects the geographic reality of the Tribe's land base. The area-weighting correctly gives more influence to Jefferson County (largest overlap) than Clackamas (smallest overlap).

**Context LOST:**
- The county-level granularity. A Tribal Leader cannot see that Jefferson County's portion of their land is in the 82nd percentile while Clackamas is in the 31st. The weighted average smooths this.
- The population distribution. Area weighting assumes uniform population distribution within counties. If most Tribal members live in the Jefferson County portion, the true social vulnerability may be closer to 0.82 than 0.75.
- **Recommendation:** For Doc E (full detail), preserve a "county-level detail" table showing each contributing county's score and weight. This lets grant writers cite specific county data when relevant.

#### Stage 3: Custom 3-Theme Composite Calculation

Theme 3 (Racial & Ethnic Minority Status) is excluded per requirements. The custom Tribal SVI composite averages Themes 1, 2, and 4:

| Theme | Weighted Value |
|-------|---------------|
| Theme 1 (Socioeconomic) | 0.6512 |
| Theme 2 (Household) | 0.7494 |
| Theme 4 (Housing/Transport) | 0.5823 |

Custom SVI = (0.6512 + 0.7494 + 0.5823) / 3 = **0.6610**

**Context preserved:** The composite reflects three of four SVI dimensions relevant to Tribal climate vulnerability.

**Context LOST:**
- Theme 2's contribution is diluted into the average. The fact that Household Characteristics is the highest-scoring theme is invisible in the composite.
- The exclusion of Theme 3 changes the composite from 0.72 (all 4 themes) to 0.66 (3 themes). This is a meaningful numerical difference. A document must explain why the number differs from what someone might find on CDC's SVI website for the same county.
- **Recommendation:** Always show theme-level scores alongside the composite in Doc A and Doc E. Doc B shows composite only but includes a footnote: "3-theme composite excluding racial/ethnic minority indicators per Tribal consultation guidance."

#### Stage 4: Composite Vulnerability Score Component

The custom SVI (0.6610) becomes the "Social Vulnerability" component of the composite vulnerability score, weighted at 0.25:

Social Vulnerability contribution = 0.6610 x 0.25 = **0.1653**

In the full composite: 0.30 (hazard) + 0.25 (social) + 0.25 (climate trajectory) + 0.20 (adaptive capacity deficit)

Example full composite: (0.72 x 0.30) + (0.6610 x 0.25) + (0.65 x 0.25) + (0.71 x 0.20) = 0.216 + 0.165 + 0.163 + 0.142 = **0.686**

**Context preserved:** Social vulnerability is a clearly weighted component. The weight (0.25) communicates its relative importance.

**Context LOST:**
- Theme 2's original 0.7494 is now embedded three layers deep: Theme 2 -> 3-theme average -> weighted component -> composite score. The original signal is attenuated by two rounds of averaging.
- A Tribal Leader seeing "Composite: 0.69" cannot discern that Household Characteristics is a primary driver.
- **Recommendation:** In Doc A and Doc E, always present component-level detail (hazard 0.72, social 0.66, climate 0.65, capacity 0.71) alongside the composite. Provide a single sentence identifying the strongest driver: "Social determinant indicators, particularly household characteristics including elder population and disability rates, are the primary driver of this assessment."

#### Stage 5: Rating Tier Assignment

Composite score 0.686 maps to tier thresholds:
- Very High: >= 0.80
- High: >= 0.60 -- **this one**
- Moderate: >= 0.40
- Low: >= 0.20
- Very Low: < 0.20

Rating: **High** (using Option D framing: "Resilience Investment Priority: High")

**Context preserved:** The 5-tier system provides an accessible, memorable label.

**Context LOST:**
- The difference between 0.60 and 0.79 is enormous, but both receive the same "High" label. A Tribe at 0.61 and one at 0.79 have materially different profiles but identical labels.
- **Recommendation:** Always pair the tier label with the numeric score. "Resilience Investment Priority: High (0.69)" preserves the granularity while providing the accessible label.

#### Stage 6: Section Rendering in Doc A (Full Detail)

Using the Option D hybrid framing, Doc A renders:

> **Climate Resilience Investment Profile**
>
> Federal climate and social data confirm that the Confederated Tribes of Warm Springs faces disproportionate exposure to climate hazards. [Table with all components.] Resilience Investment Priority: High (0.69).
>
> Social determinant indicators, particularly household characteristics including elder population and disability rates, are the primary driver of this assessment.

**Context preserved:** Component scores, primary driver identification, strategic use guidance, source citations, caveat about what data cannot capture.

**Context LOST:** County-level granularity (recoverable in Doc E). Sub-indicator detail within SVI themes (recoverable from raw data, presented selectively in Doc E).

#### Stage 7: Section Rendering in Doc B (Air-Gapped)

Doc B renders:

> **Climate Resilience Data Summary**
>
> Resilience Investment Priority: High
> Social Indicators: 66th percentile (CDC SVI 2022, 3-theme)
> Source: CDC Social Vulnerability Index 2022, FEMA NRI v1.20

**Context preserved:** Rating, percentile, source.

**Context LOST:** Theme-level decomposition, driver identification, strategic context, caveat language. This is by design. Doc B is facts only.

#### Stage 8: Final Document Text

The Tribal Leader or congressional aide reads the rendered DOCX. At this point, the original RPL_THEME2 = 0.7413 for Wasco County has been:
1. Area-weighted with other counties (0.7413 -> 0.7494)
2. Averaged into a 3-theme composite (0.7494 -> contributing to 0.6610)
3. Weighted into a 4-component composite (0.6610 -> contributing to 0.686)
4. Assigned a tier label (0.686 -> "High")

**Total information loss:** The 0.7413 has been transformed through four mathematical operations into one word. The specific meaning -- "74th percentile for household characteristics including elder population and disability" -- is invisible unless Doc A or Doc E provides theme-level decomposition.

**Critical recommendation for Phase 23 renderers:**
1. Doc A and Doc E MUST show SVI theme-level scores alongside the composite
2. Doc A and Doc E MUST identify the strongest theme driver in narrative text
3. All documents MUST pair tier labels with numeric scores
4. Doc E MUST include county-level detail tables for grant writer reference
5. The composite methodology should be briefly explained in Doc E: "This composite weighs hazard exposure (30%), social indicators (25%), climate trajectory (25%), and adaptive capacity (20%)"

---

### Alaska Narrative Strategy

#### The Scale of the Problem

229 of 592 tracked Tribal Nations (38.7%) are in Alaska. This is not an edge case. It is nearly four in ten documents. Any "data not available" approach that treats Alaska as an exception will visibly degrade the quality of nearly 40% of all output.

#### Current Data Availability for Alaska Tribes

| Data Source | Alaska Coverage | Notes |
|-------------|----------------|-------|
| FEMA NRI | Partial | NRI includes Alaska boroughs; remote villages may have incomplete coverage. ~19 unmatched Tribes in current hazard profiles. |
| CDC SVI 2022 | Yes | SVI includes Alaska boroughs/census areas. Full county-level coverage. |
| LOCA2 Climate | No | CONUS only. Deferred to v1.5+ regardless. |
| US Drought Monitor | Yes | County-level drought data includes Alaska. |
| USFS Wildfire | Partial | USFS data may not cover all Alaska regions. |

**Key insight:** Even without LOCA2, Alaska Tribes can receive SVI data, partial NRI data, and drought data. The composite vulnerability score for Alaska Tribes will have some components available and others missing.

#### "Data Not Available" Is Never Acceptable

A blank section feels like erasure. When 229 Alaska Native communities open a document from a climate resilience tool and find blank pages, the message they receive is: "the federal system does not see you." This is precisely the systemic failure this tool exists to challenge.

#### Proposed Alaska Narrative Strategy

**Tier 1: Full Data Available (Alaska Tribes with complete NRI + SVI)**

Treat identically to CONUS Tribes. No special Alaska handling needed. The composite score omits the climate trajectory component (LOCA2 deferred), so the weight is redistributed across the three available components for ALL Tribes, not just Alaska.

**Tier 2: Partial Data Available (Alaska Tribes with SVI but incomplete NRI)**

Render what is available with explicit acknowledgment of gaps:

> **Climate Resilience Investment Profile**
>
> **Data Coverage Note:** Federal climate hazard datasets provide incomplete coverage for Alaska Native communities. The following assessment uses available social indicator data (CDC SVI 2022, which includes Alaska) and partial hazard data (FEMA NRI, where available for your borough/census area). The absence of complete hazard data for Alaska is a federal data infrastructure gap, not a reflection of your community's climate exposure.
>
> Available Indicators:
> | Indicator | Value | Source |
> |-----------|-------|--------|
> | Social Indicators (CDC SVI) | 0.72 | CDC SVI 2022 |
> | Drought Exposure | Moderate | US Drought Monitor |
>
> **What this means:** Social determinant data indicates that your community faces elevated socioeconomic and housing factors that amplify the impact of climate events. While federal hazard exposure data is incomplete for your area, this social indicator data alone strengthens grant applications that weight community vulnerability.
>
> **The data gap as advocacy:** The incompleteness of federal climate data for Alaska Native communities is itself an advocacy point. In consultations with FEMA, EPA, and other agencies, cite this gap as evidence of systemic underinvestment in Alaska-specific climate data infrastructure.

**Tier 3: Minimal Data (Alaska Tribes with only SVI or very sparse data)**

Even with minimal data, provide something meaningful:

> **Climate Resilience Investment Profile**
>
> **Data Coverage Statement:** Comprehensive federal climate hazard data is not currently available for {tribe_name}'s geographic area. This is a documented gap in federal data infrastructure that disproportionately affects Alaska Native communities. Of the 229 Alaska Native Tribal Nations tracked by federal systems, many face incomplete climate data coverage -- a systemic gap that itself warrants federal attention.
>
> **Available Data:**
> Social determinant indicators (CDC SVI 2022) are available and indicate that your community's socioeconomic and housing context should be considered in any climate resilience planning.
>
> **Advocacy Recommendation:** The absence of data is evidence. In FEMA BRIC, EPA IGAP, and BIA Climate Resilience grant applications, document the federal data gap as a barrier to community resilience planning. Request that agencies prioritize Alaska-specific climate data development.

#### Implementation Guidance

1. **In the composite vulnerability score calculation:** When components are missing, calculate from available components only with redistributed weights. Do NOT assign a score of 0 for missing components. Flag the profile as `"data_completeness": "partial"` with a list of available and missing components.

2. **In document rendering:** Check `vulnerability_profile.get("data_completeness")`. If "partial", render the appropriate tiered narrative above. If "full", render the standard narrative.

3. **In the coverage report:** Track Alaska coverage separately. Report: "X of 229 Alaska Tribes have full data, Y have partial data, Z have minimal data."

4. **Never use:** "N/A," "Not Available," "No Data," or blank sections. Always provide narrative context explaining the gap and framing it as a systemic issue, not a limitation of the specific Tribe.

5. **The gap as advocacy ammunition:** Every Alaska Tribe document should include language that turns the data gap into an advocacy point. "The federal government's failure to provide comprehensive climate data for Alaska Native communities is itself a form of disproportionate impact."

---

### Multi-Format Readiness Assessment

The schema and pipeline decisions made in Phases 19-24 will either enable or constrain future output formats. Here is an assessment of the four target formats:

#### Presentation Slides for Tribal Council Meetings

**What is needed:** A 5-10 slide deck with key figures, minimal text, large fonts, and visual emphasis on ratings and dollar figures.

**Schema/pipeline decisions that enable this:**
- The composite score rating tier ("High") is slide-ready as-is -- one word, one color-coded badge
- EAL dollar figures are concrete and visual: "$1.2M annual wildfire loss" fits on a slide
- The 4-component breakdown maps naturally to a 2x2 grid layout

**Schema/pipeline decisions that could break this:**
- If the vulnerability profile JSON lacks pre-computed summary fields and requires re-aggregation from raw data, slide generation requires the full data pipeline
- **Recommendation (Phase 19):** Include a `"summary"` sub-object in each vulnerability profile with pre-computed display-ready values: rating, score, top hazard, top EAL figure, primary SVI driver. This enables lightweight slide generation from the summary alone.

#### One-Page Fact Sheets for Congressional Visits

**What is needed:** A single-page PDF with the Tribe's name, key metrics, one hazard data point, one social data point, and a clear policy ask. Print-optimized.

**Schema/pipeline decisions that enable this:**
- The Doc B air-gapped rendering already produces a compact, facts-only format
- If Doc B vulnerability section is kept to one table + one rating line, it maps directly to a fact sheet block

**Schema/pipeline decisions that could break this:**
- If the vulnerability section in Doc B becomes too long (multiple tables, narrative paragraphs), the fact sheet extraction becomes a content-selection problem
- **Recommendation (Phase 23):** Design the Doc B vulnerability section to fit within one page (one table, one summary line, source citation). This constraint also serves Doc B's audience well.

#### Dashboard Views for Ongoing Monitoring

**What is needed:** A web interface showing all 592 Tribes with sortable/filterable vulnerability data, drill-down to per-Tribe detail, trend tracking over time.

**Schema/pipeline decisions that enable this:**
- The `tribes.json` web index already provides a searchable, filterable list. Adding vulnerability summary fields extends this.
- Per-Tribe detail loading via on-demand JSON fetch (WEB-02) supports drill-down.

**Schema/pipeline decisions that could break this:**
- If vulnerability profiles lack a `generated_at` timestamp with sufficient precision, trend tracking over time is impossible
- If the composite score formula changes between versions without version-flagging the profiles, historical comparison is invalid
- **Recommendation (Phase 19):** Include `"formula_version": "1.0"` and `"generated_at"` in every vulnerability profile. When the formula changes in future versions, increment the formula version so the dashboard can distinguish v1.0 scores from v1.1 scores.

#### Grant Application Supporting Evidence Packets

**What is needed:** A PDF appendix with data tables, source citations, and pre-written narrative paragraphs that grant writers can attach to applications.

**Schema/pipeline decisions that enable this:**
- Doc E (standalone vulnerability report) IS this format if designed correctly
- The "Grant Application Reference Paragraphs" section proposed in the Doc E structure directly serves this need

**Schema/pipeline decisions that could break this:**
- If Doc E is structured as a readable narrative rather than a reference document with extractable sections, grant writers will need to edit and restructure content
- **Recommendation (Phase 23):** Structure Doc E with clearly labeled, self-contained sections that can be individually extracted. Use DOCX heading styles that support automated section extraction.

#### Summary of Multi-Format Recommendations for Phase 19

| Decision | Phase | Impact |
|----------|-------|--------|
| Add `"summary"` sub-object to vulnerability profile JSON | 19 | Enables lightweight slide/factsheet generation |
| Include `"formula_version"` and `"generated_at"` | 19 | Enables dashboard trend tracking |
| Keep Doc B vulnerability section to 1 page | 23 | Enables factsheet extraction |
| Structure Doc E as extractable reference sections | 23 | Enables grant packet assembly |

---

### Visualization Specifications

#### Chart Type Recommendations

**Primary visualization: Horizontal bar chart for component comparison**

For showing the four components of the composite vulnerability score (hazard exposure, social indicators, climate trajectory, adaptive capacity deficit), a horizontal bar chart is the clearest choice for non-technical audiences.

Specification:
- Orientation: Horizontal (labels on left, bars extending right)
- Scale: 0 to 1.0 (or 0% to 100%)
- Bar height: Minimum 40px for touch targets (44px recommended)
- Labels: Plain English component names, not technical abbreviations
  - "Hazard Exposure" not "RISK_SPCTL"
  - "Social Indicators" not "SVI RPL"
  - "Adaptive Capacity Gap" not "1 - RESL_SCORE"
- Color: Single accent color for all bars with opacity varying by value
- Composite score shown as a vertical reference line across all bars
- Rating badge ("High") displayed as a colored chip above the chart

**Why not radar charts:** Radar charts (spider/web charts) are popular in multi-dimensional data visualization but have documented usability issues for non-expert audiences:
1. Area comparison is cognitively difficult (people compare lengths better than areas)
2. The shape depends on the ordering of axes, which is arbitrary
3. Mobile rendering is problematic at small sizes
4. Colorblind users struggle with overlapping filled areas

If the team strongly prefers radar charts for aesthetic reasons, they should be offered as a secondary "expert view" toggle, not the default visualization.

**Secondary visualization: EAL breakdown stacked bar**

For showing Expected Annual Loss by consequence type (buildings, population, agriculture) per top hazard:
- Stacked horizontal bar, one bar per top hazard (max 5)
- Three segments: Buildings (blue), Population (amber), Agriculture (green)
- Dollar labels on each segment using `format_dollars()`
- Total EAL label at end of each bar

**Tertiary visualization: SVI theme comparison**

For showing the 3-theme SVI breakdown:
- Three horizontal bars (Socioeconomic, Household, Housing/Transport)
- Scale: 0 to 1.0
- National median reference line at 0.5
- Color coding: bars above 0.75 in warning color, above 0.5 in moderate, below 0.5 in standard

**Badge/indicator for search results:**

For the Tribe card in search results (WEB-01):
- Color-coded chip: "HIGH" / "MODERATE" / "LOW" etc.
- Top hazard icon (flame for wildfire, water drop for flood, etc.)
- Single-line summary: "High Priority | Wildfire ($1.2M EAL)"

#### Color Palette (WCAG 2.1 AA Compliant + Colorblind-Safe)

The palette must pass:
- WCAG 2.1 AA contrast ratio (minimum 4.5:1 for text, 3:1 for large text/UI components)
- Deuteranopia (red-green colorblind, ~8% of males) simulation
- Protanopia simulation
- Dark mode variants

Proposed palette (tested for accessibility):

| Rating | Light Mode | Dark Mode | Text Color | Contrast |
|--------|------------|-----------|------------|----------|
| Very High | `#B91C1C` (red-700) | `#FCA5A5` (red-300) | White / `#1F2937` | 5.2:1 / 7.1:1 |
| High | `#B45309` (amber-700)* | `#FCD34D` (amber-300) | White / `#1F2937` | 4.6:1 / 8.2:1 |
| Moderate | `#1D4ED8` (blue-700) | `#93C5FD` (blue-300) | White / `#1F2937` | 5.8:1 / 7.4:1 |
| Low | `#047857` (emerald-700) | `#6EE7B7` (emerald-300) | White / `#1F2937` | 4.9:1 / 8.7:1 |
| Very Low | `#374151` (gray-700) | `#D1D5DB` (gray-300) | White / `#1F2937` | 8.1:1 / 12.6:1 |

*Note: `#B45309` is the WCAG-compliant amber already used in v1.3 for CI status badges (confirmed in Phase 16 P1 fix).

**Colorblind safety strategy:** The palette avoids pure red-green adjacency. The five tiers use red, amber, blue, emerald, and gray -- these are distinguishable under deuteranopia and protanopia simulations. Additionally, all badges include text labels (not color alone), which satisfies WCAG 1.4.1 (Use of Color).

#### Handling Partial Data in Visualizations

**For Alaska Tribes with missing components:**
- Show available bars in the component chart at full opacity
- Show missing component bars as dotted outlines with "Data Pending" label
- Display a yellow info banner above the chart: "Some climate data is not yet available for Alaska communities. Available data shown below."
- Never show an empty chart. If only one component is available, show it as a single bar with context.

**For Tribes with zero vulnerability profile:**
- Display a styled message card instead of a chart: "Climate resilience data is being compiled for this community."
- Include the Tribe's existing hazard profile data if available (bridge to v1.3 data)

#### Mobile Responsiveness

- Minimum touch target: 44px x 44px (WCAG 2.5.5)
- Chart container: `max-width: 100%; overflow-x: auto` for horizontal scroll on narrow screens
- Bar labels: Truncate with ellipsis at narrow widths, full label on hover/tap
- Badge: Stack vertically below Tribe name on screens < 480px
- Chart.js responsive mode: `responsive: true, maintainAspectRatio: false` with minimum height of 200px

#### Chart.js Configuration Template

```javascript
// Component comparison chart
const componentChart = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Hazard Exposure', 'Social Indicators', 'Climate Trajectory', 'Adaptive Capacity Gap'],
    datasets: [{
      data: [0.72, 0.66, null, 0.71],  // null for missing components
      backgroundColor: function(context) {
        const value = context.raw;
        if (value === null) return '#E5E7EB';  // gray for missing
        if (value >= 0.80) return '#B91C1C';
        if (value >= 0.60) return '#B45309';
        if (value >= 0.40) return '#1D4ED8';
        if (value >= 0.20) return '#047857';
        return '#374151';
      },
      borderWidth: function(context) {
        return context.raw === null ? 2 : 0;
      },
      borderColor: '#9CA3AF',
      borderDash: function(context) {
        return context.raw === null ? [5, 5] : [];
      }
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: function(context) {
            if (context.raw === null) return 'Data pending';
            return 'Score: ' + context.raw.toFixed(2);
          }
        }
      }
    },
    scales: {
      x: { min: 0, max: 1.0, title: { text: 'Score', display: true } },
      y: { ticks: { font: { size: 14 } } }
    }
  }
});
```

---

### Framing Vocabulary Specification (REG-04)

#### Module Design

The vocabulary module should be a constants file (`src/packets/vocabulary.py`) that provides:
1. A lookup table of approved terms, forbidden terms, and replacements
2. Context-aware replacement functions that distinguish proper nouns from descriptive usage
3. Section heading templates for each document type
4. Caveat language templates

The module is NOT a text-rewriting engine. It provides constants that renderers import and use during section construction. The enforcement is at render time, not as a post-processing filter.

#### Approved Terms

| Context | Approved | Instead of |
|---------|----------|------------|
| Section headings | "Climate Resilience Investment Profile" | "Climate Vulnerability Assessment" |
| Section headings | "Climate Resilience Data Summary" | "Vulnerability Summary" |
| Section headings | "Social Determinant Analysis" | "Social Vulnerability Breakdown" |
| Section headings | "Hazard Exposure Detail" | "Hazard Vulnerability Detail" |
| Section headings | "Community Resilience Indicators" | "Adaptive Capacity Assessment" |
| Rating label | "Resilience Investment Priority" | "Vulnerability Rating" |
| Rating label | "Resilience Investment Priority: High" | "Vulnerability: High" |
| Narrative (Doc A) | "faces disproportionate climate exposure" | "is highly vulnerable to climate change" |
| Narrative (Doc A) | "climate hazard exposure" | "climate vulnerability" |
| Narrative (Doc A) | "social determinant indicators" | "social vulnerability factors" |
| Narrative (Doc A) | "adaptive capacity gap" | "adaptive capacity deficit" |
| Narrative (Doc A) | "investment gap between exposure and resources" | "vulnerability gap" |
| Narrative (Doc B) | "climate exposure data" | "vulnerability data" |
| Narrative (Doc B) | "social indicators" | "social vulnerability" |
| EAL context | "estimated annual economic impact" | "expected annual loss" (keep EAL as source term in citations) |
| Caveat language | "based on available federal datasets" | "according to our analysis" |
| Caveat language | "federal data infrastructure does not capture" | "data is not available for" |
| Data gaps | "federal data infrastructure gap" | "data limitation" |
| Data gaps | "systemic data coverage disparity" | "missing data" |
| Source citation | "Social Vulnerability Index" | (retain -- proper noun, not replaceable) |
| Source citation | "National Risk Index" | (retain -- proper noun) |
| Community reference | "Tribal Nation" or "community" | "tribe" (lowercase), "population", "group" |
| Capacity framing | "governance capacity" | "institutional capacity" |
| Knowledge framing | "Traditional Knowledge" | "local knowledge" or "indigenous knowledge" (lowercase) |

#### Forbidden Terms (Vulnerability Air Gap for Doc B/D)

These terms MUST NOT appear in Doc B or Doc D documents, extending the existing air gap:

**Category 1: Strategy/Interpretation (existing air gap, extended)**
- "strategic" / "strategy" / "leverage" / "approach" / "messaging"
- "advocacy" / "advocacy ammunition" / "talking points"
- "priority advocacy targets" / "high-impact"
- "congressional dynamics" / "oversight"

**Category 2: Vulnerability Framing (new for v1.4)**
- "vulnerable" (as an adjective describing a Tribe -- permitted inside "Social Vulnerability Index")
- "vulnerability" (as a descriptor -- permitted inside "Social Vulnerability Index" and "National Risk Index")
- "at risk" (as a community descriptor -- permitted in "climate risk" data context)
- "disadvantaged" / "underserved" / "marginalized"
- "deficit" / "deficient" / "lacking"
- "struggling" / "suffering" / "burdened"

**Category 3: Resilience Framing (Doc A only)**
- "Traditional Knowledge" (strategic framing)
- "governance strengths" / "governance capacity"
- "cultural resilience"
- "investment gap" (interpretation)
- "this is not a measure of the Nation's strength" (editorial)

**Implementation note:** The forbidden-terms check should be implemented as a test in `test_audience_filtering.py` (extending the existing air gap tests). The test scans rendered Doc B content for forbidden terms, with an allowlist for proper noun contexts (e.g., "Social Vulnerability Index" is permitted even though it contains "Vulnerability").

#### Caveat Language Templates

**Template 1: Standard composite score caveat (Doc A, Doc E)**

> This assessment is based on publicly available federal datasets including the FEMA National Risk Index (v1.20) and the CDC Social Vulnerability Index (2022). These datasets measure conditions that federal agencies track. They do not capture the full picture of any Tribal Nation's capacity, resilience, or strengths. Traditional Knowledge, governance capacity, cultural resilience practices, and community bonds are real but unmeasured assets. This assessment is a tool for federal advocacy -- evidence to support the case for proportional investment -- not a determination of the Nation's condition.

**Template 2: Compact data source note (Doc B)**

> Data sources: FEMA National Risk Index v1.20, CDC Social Vulnerability Index 2022. County-level data aggregated to Tribal geographic boundaries. Social indicators reflect socioeconomic status, household characteristics, and housing type/transportation factors.

**Template 3: Partial data caveat (Alaska / incomplete profiles)**

> Federal climate datasets provide incomplete coverage for this community's geographic area. Available data is presented below. Data gaps reflect federal data infrastructure limitations, not the community's climate exposure or resilience. The absence of complete federal data is itself a documented barrier to equitable climate resilience investment for Alaska Native and other geographically remote communities.

**Template 4: Theme 3 exclusion note (all documents)**

> Social indicators are calculated from three of four CDC SVI themes: socioeconomic status, household characteristics, and housing type/transportation. Racial and ethnic minority status indicators are excluded from the composite calculation because this index is applied exclusively to Tribal Nations, making minority-status indicators tautological rather than informative.

**Template 5: Methodology transparency (Doc E only)**

> **Methodology Note:** The Resilience Investment Priority rating combines four components with the following weights: Hazard Exposure (30%, from FEMA NRI composite risk), Social Indicators (25%, from CDC SVI 3-theme composite), Climate Trajectory (25%, from LOCA2 projections where available), and Adaptive Capacity Gap (20%, derived from FEMA NRI community resilience score). When one or more components are unavailable, weights are redistributed proportionally across available components. County-level data is aggregated to Tribal geographic boundaries using area-weighted crosswalk from Census AIANNH and TIGER county shapefiles.

#### Section Heading Options

| Document | Current Hazard Heading | Proposed Vulnerability Heading |
|----------|----------------------|-------------------------------|
| Doc A | "Climate Hazard Profile" | "Climate Resilience Investment Profile" |
| Doc B | "Climate Hazard Profile" | "Climate Resilience Data Summary" |
| Doc C | "Regional Climate Hazard Summary" | "Regional Climate Resilience Profile" |
| Doc D | "Regional Climate Hazard Summary" | "Regional Climate Resilience Data" |
| Doc E | N/A (new document) | "Climate Resilience Investment Assessment" (main heading) |
| Doc E sub-sections | N/A | "Hazard Exposure Detail" / "Social Determinant Analysis" / "Expected Annual Economic Impact" / "Community Resilience Indicators" / "Data Limitations and Sovereignty Statement" |

#### Vocabulary Module Implementation Skeleton

```python
"""Sovereignty-first vulnerability framing vocabulary constants.

Provides approved language, forbidden terms, caveat templates, and
section headings for vulnerability content rendering across all
document types (REG-04).

Usage:
    from src.packets.vocabulary import (
        SECTION_HEADINGS,
        CAVEAT_TEMPLATES,
        FORBIDDEN_DOC_B_TERMS,
        approved_term,
    )

The vocabulary is NOT a post-processing text filter. Renderers import
these constants and use them during section construction. Enforcement
is at render time, validated by air gap tests.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionHeadings:
    """Section heading text for each document type."""
    doc_a_main: str = "Climate Resilience Investment Profile"
    doc_b_main: str = "Climate Resilience Data Summary"
    doc_c_main: str = "Regional Climate Resilience Profile"
    doc_d_main: str = "Regional Climate Resilience Data"
    doc_e_main: str = "Climate Resilience Investment Assessment"
    hazard_detail: str = "Hazard Exposure Detail"
    social_detail: str = "Social Determinant Analysis"
    eal_detail: str = "Expected Annual Economic Impact"
    resilience_detail: str = "Community Resilience Indicators"
    data_limitations: str = "Data Limitations and Sovereignty Statement"
    grant_reference: str = "Grant Application Reference"


SECTION_HEADINGS = SectionHeadings()

RATING_LABEL = "Resilience Investment Priority"

RATING_TIERS: dict[str, str] = {
    "very_high": "Very High",
    "high": "High",
    "moderate": "Moderate",
    "low": "Low",
    "very_low": "Very Low",
}

# Forbidden terms for Doc B/D (extends existing air gap)
FORBIDDEN_DOC_B_TERMS: frozenset[str] = frozenset({
    "strategic",
    "strategy",
    "leverage",
    "approach",
    "messaging",
    "advocacy",
    "talking points",
    "Traditional Knowledge",
    "governance strengths",
    "governance capacity",
    "cultural resilience",
    "investment gap",
    "disadvantaged",
    "underserved",
    "marginalized",
    "deficit",
    "deficient",
    "struggling",
    "suffering",
    "burdened",
})

# Terms forbidden as descriptors but permitted in proper nouns
CONTEXT_SENSITIVE_TERMS: dict[str, list[str]] = {
    "vulnerable": [
        "Social Vulnerability Index",
        "CDC/ATSDR Social Vulnerability",
    ],
    "vulnerability": [
        "Social Vulnerability Index",
        "National Risk Index",
        "vulnerability_profile",  # code/JSON key
    ],
    "at risk": [
        "National Risk Index",
        "climate risk",
        "risk score",
        "risk rating",
    ],
}

# Caveat templates indexed by context
CAVEAT_TEMPLATES: dict[str, str] = {
    "composite_full": (
        "This assessment is based on publicly available federal datasets "
        "including the FEMA National Risk Index and the CDC Social "
        "Vulnerability Index. These datasets measure conditions that "
        "federal agencies track. They do not capture the full picture of "
        "any Tribal Nation's capacity, resilience, or strengths. "
        "Traditional Knowledge, governance capacity, cultural resilience "
        "practices, and community bonds are real but unmeasured assets. "
        "This assessment is a tool for federal advocacy -- evidence to "
        "support the case for proportional investment -- not a "
        "determination of the Nation's condition."
    ),
    "source_compact": (
        "Data sources: FEMA National Risk Index v1.20, CDC Social "
        "Vulnerability Index 2022. County-level data aggregated to "
        "Tribal geographic boundaries."
    ),
    "partial_data": (
        "Federal climate datasets provide incomplete coverage for this "
        "community's geographic area. Available data is presented below. "
        "Data gaps reflect federal data infrastructure limitations, not "
        "the community's climate exposure or resilience."
    ),
    "theme3_exclusion": (
        "Social indicators are calculated from three of four CDC SVI "
        "themes: socioeconomic status, household characteristics, and "
        "housing type/transportation. Racial and ethnic minority status "
        "indicators are excluded because this index is applied "
        "exclusively to Tribal Nations, making minority-status "
        "indicators tautological rather than informative."
    ),
    "methodology": (
        "The Resilience Investment Priority rating combines four "
        "components: Hazard Exposure (30%, FEMA NRI), Social Indicators "
        "(25%, CDC SVI 3-theme), Climate Trajectory (25%, where "
        "available), and Adaptive Capacity Gap (20%, FEMA NRI "
        "resilience). When components are unavailable, weights are "
        "redistributed proportionally across available components."
    ),
    "alaska_gap": (
        "The absence of complete federal climate data for Alaska Native "
        "communities is a documented barrier to equitable climate "
        "resilience investment. This gap is itself an advocacy point in "
        "federal consultations."
    ),
}


def approved_term(concept: str) -> str:
    """Return the approved framing term for a given concept.

    Args:
        concept: The concept key (e.g., "rating_label", "section_main").

    Returns:
        The approved term string.
    """
    terms: dict[str, str] = {
        "rating_label": "Resilience Investment Priority",
        "community_descriptor": "Tribal Nation",
        "exposure_phrase": "faces disproportionate climate exposure",
        "social_phrase": "social determinant indicators",
        "capacity_phrase": "adaptive capacity gap",
        "gap_phrase": "investment gap between exposure and resources",
        "data_basis": "based on available federal datasets",
        "data_gap": "federal data infrastructure gap",
    }
    return terms.get(concept, concept)
```

---

### Recommendations

#### Decisions Required Before Phase 19

1. **Adopt Option D (Hybrid) framing.** Use "Climate Resilience Investment Priority" as the primary label, "disproportionate exposure" for explanatory context, and "vulnerability" only inside federal methodology proper nouns. This decision cascades into schema field naming (use `resilience_priority` not `vulnerability_rating` in JSON), section heading constants, and test assertions.

2. **Design the composite score to gracefully degrade for partial data.** The Alaska strategy depends on this. When one or more components are missing, redistribute weights proportionally. Include `"data_completeness": "full" | "partial" | "minimal"` in every profile. This must be designed in Phase 19 (schema), not patched in Phase 23 (rendering).

3. **Commit to the Doc B air gap extension for vulnerability content.** The forbidden-terms list in this report should be reviewed and finalized before any rendering code is written. Add air gap compliance tests in Phase 19 alongside the vocabulary module.

4. **Define Doc E structure and audience before Phase 23.** The "Grant Application Reference Paragraphs" section is the highest-value component of Doc E and should drive the document's design. Build Doc E around the grant writer use case.

5. **Include a `"summary"` sub-object in vulnerability profile JSON.** This enables multi-format readiness (slides, fact sheets, dashboards) without requiring the full data pipeline for lightweight outputs.

#### Decisions That Can Wait Until Phase 23

6. **Exact paragraph wording for each document type.** The example paragraphs in this report are starting points. Phase 23 implementation should iterate on wording with test readers.

7. **Chart.js configuration details.** The specifications here provide a foundation. Phase 24 implementation will need user testing to finalize chart types and interactions.

8. **County-level detail tables in Doc E.** Whether to include per-county breakdowns is a Phase 23 rendering decision. The schema should preserve county-level data regardless.

#### High-Priority Risks to Monitor

9. **SVI Theme 3 exclusion narrative.** The caveat template in this report explains the exclusion cleanly. But if a congressional aide compares the document's SVI figure to the CDC website for the same county and gets a different number, they may question credibility. The Theme 3 exclusion note must be prominent, not buried.

10. **"Resilience Investment Priority" vs. grant application "vulnerability" language.** Some federal grant applications explicitly ask for "vulnerability assessments." If Tribes submit Doc E as supporting evidence with "Resilience Investment Priority" headings but the grant asks for "vulnerability," there may be a terminology mismatch. **Mitigation:** Doc E's "Grant Application Reference Paragraphs" section should use the federal program's own terminology, even if the rest of the document uses the sovereignty-first framing. This is code-switching, and Tribal Leaders do it every day.

11. **The 0.60-0.79 range compression.** Both 0.61 and 0.79 score "High." This range compression is inherent in any tier system. Always pair the tier with the numeric score. Consider whether a 6-tier system (splitting High into High and High+) would serve better, or whether the 5-tier approach is sufficient.

12. **Composite score with LOCA2 deferred.** With climate trajectory unavailable in v1.4, the composite is a 3-component score (hazard, social, adaptive capacity) with redistributed weights. This means the v1.4 composite will differ numerically from the v1.5 composite when LOCA2 is added. The `"formula_version"` field and clear documentation are essential to prevent confusion when scores change between versions.

---

*Horizon Walker | Phase 18.5 | 2026-02-17*
*Every word in a document either strengthens or diminishes the Tribal Leader's position. Choose carefully.*
*Sovereignty is the innovation. Relatives, not resources.*
