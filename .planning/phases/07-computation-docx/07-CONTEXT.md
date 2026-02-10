# Phase 7: Computation + DOCX Generation - Context

**Gathered:** 2026-02-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform cached per-Tribe data (awards, hazards, congressional delegation) into professional DOCX advocacy packet sections using python-docx. Delivers the DOCX engine, economic impact calculations, per-program Hot Sheets with advocacy language, and structural asks integration. Complete document assembly (cover page, executive summary, full packet) is Phase 8.

Requirements: ECON-01, DOC-01, DOC-02, DOC-03, DOC-04

</domain>

<decisions>
## Implementation Decisions

### Hot Sheet Layout & Density

- **Page target:** One page per Hot Sheet, overflow to 1.5-2 pages OK when data is rich
- **Content format:** Claude's discretion (table-driven vs narrative mix)
- **CI status display:** Color-coded visual indicator (traffic light) PLUS informative text label with context (e.g., "At Risk -- FY26 CR reduces funding 12%"). Rich visual emphasis to draw the eye to priorities
- **Section order:** Fixed section order across all Hot Sheets, but omit sections with no data (hide empty)
- **Visual implementation:** Word-native formatting plus small inline shapes (colored boxes/circles) for status badges -- "rich but safe" approach
- **Zero-award handling:** Advocacy pivot -- replace award history section with "First-Time Applicant Advantage" framing. Position zero history as competitive strength, not weakness
- **Program filtering:** Only include programs relevant to the Tribe's hazard profile. Target 8-12 programs per Tribe instead of all 16. Omitted programs listed in an appendix with brief paragraph each (what it does, why lower priority, how to learn more)
- **Relevance criteria:** Claude's discretion (likely hazard-driven + award history inclusion)
- **Hot Sheet ordering:** By priority/risk -- highest-relevance programs first, leading with the Tribe's most critical climate programs
- **Key Ask callout:** Prominent callout box on every Hot Sheet, structured as 3-line block:
  - ASK: [One-line specific ask]
  - WHY: [One-line Tribe-specific justification]
  - IMPACT: [One-line economic/community impact]

### Economic Impact Framing

- **Multiplier presentation:** Range with citation -- "Generated an estimated $4.2M-$5.6M in regional economic activity (BEA methodology range: 1.8-2.4x)"
- **Job estimates:** Yes, include with methodology -- BLS jobs-per-million-output ratios, presented as ranges
- **FEMA BCR framing:** Use BOTH future savings narrative ("Every $1 invested saves $4 in future disaster costs") AND ROI language ("delivers a 4:1 return on federal investment")
- **Zero-award economic impact:** Claude's discretion on whether to show hypothetical potential or program-level data
- **Impact scope:** Claude's discretion on district vs state level presentation
- **Multi-district Tribes:** Show total economic impact PLUS per-district breakdown using Census area overlap percentages
- **Benchmarks:** Include program average comparison -- "The average Tribal [program] award generates $X. [Tribe]'s awards generated $Y."
- **Methodology placement:** Footnote on each Hot Sheet (small, visible but not distracting)

### Document Styling & Branding

- **Visual tone:** Professional modern -- clean sans-serif, strategic color use, plenty of whitespace. Like a Brookings or McKinsey brief
- **Color palette:** Status-driven -- red/yellow/green traffic light for CI classification as primary color system. Functional color carrying meaning, not decoration
- **Status color mapping:** At Risk = red, Watch = yellow/amber, Stable = green
- **Typography:** Arial/Helvetica font family
- **Table styling:** Alternating row shading (zebra striping) for data tables
- **Cover page:** Include state/region map showing Tribe's location relative to congressional districts (visual context for staffers unfamiliar with the Tribe)
- **Headers/footers:** Claude's discretion on layout
- **Style reference:** Create from scratch as part of this phase -- programmatic style definitions, no external template file

### Advocacy Language Assembly

- **Language source:** Direct insertion of tightened_language and advocacy_lever fields from program inventory. Minimal transformation -- keep advocacy language human-authored
- **Structural asks:** Claude's discretion on how the Five Structural Asks integrate into Hot Sheets (mapped per program, separate section, or hybrid)
- **Status-driven tone:** Framing shifts by CI classification:
  - At Risk: defensive framing ("prevent loss of $X", "critical to maintain")
  - Watch: protective framing ("ensure continuity", "safeguard")
  - Stable: growth framing ("invest to expand impact", "build on success")
- **Legislative references:** Yes, include specific bill numbers, hearings, and committee actions from v1.0 pipeline's legislative tracking data
- **Committee matching:** Flag when a Tribe's senator/representative sits on the committee relevant to a program -- high-value targeting callout: "[Senator X] sits on [Committee] -- direct influence on this program"
- **Office-specific actions:** Each Hot Sheet includes "What You Can Do" section tailored to the specific congressional office: co-sponsor specific bills, request briefings, submit appropriations requests

### Claude's Discretion

- Content format within Hot Sheets (table-driven vs narrative vs hybrid)
- Relevance criteria for program filtering (likely hazard + award history)
- Zero-award economic impact approach (hypothetical potential vs program-level)
- District vs state level economic impact scope
- Structural asks integration pattern
- Header/footer layout design
- Loading/skeleton behavior
- Error state handling

</decisions>

<specifics>
## Specific Ideas

- Key Ask callout box is the single most important design element -- it's what a staffer remembers after scanning. Structured 3-line format (ASK/WHY/IMPACT) ensures completeness
- The committee-match flag turns a generic briefing into a targeted advocacy tool. When Senator Murkowski sits on Indian Affairs Committee and the Hot Sheet highlights that, it changes how the packet is used
- Zero-award Tribes get "First-Time Applicant Advantage" framing -- this is a deliberate strategic choice, not a data gap
- Economic impact uses range with citation for credibility -- never a single inflated number
- Cover page map provides instant geographic context for staffers who may not know where the Tribe is located
- Only relevant programs (8-12 per Tribe) means every page in the packet earns its place. Omitted programs get dignified treatment in the appendix

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 07-computation-docx*
*Context gathered: 2026-02-10*
