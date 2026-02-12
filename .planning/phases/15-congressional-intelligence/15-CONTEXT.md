# Phase 15: Congressional Intelligence Pipeline - Context

**Gathered:** 2026-02-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich 592-Tribe DOCX advocacy packets with congressional intelligence -- bill tracking, delegation data, committee activity, confidence-scored sections -- and harden all 4 scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) for zero-truncation pagination. Covers 15 INTEL requirements + 3 XCUT cross-cutting requirements. Agent swarm: Sovereignty Scout, Fire Keeper, River Runner, Horizon Walker.

</domain>

<decisions>
## Implementation Decisions

### Congressional section ordering (Doc A)
- Lead with active bills ("Legislation Affecting Your Programs"), not delegation
- Bills create urgency -- the Leader should see what's moving right now before who represents them
- Delegation section follows bills

### Bill detail tiering (Doc A)
- Top 2-3 bills by relevance score get full briefing treatment: bill number, title, sponsors, committee, status, timeline, affected programs, talking points, recommended action (8-10 lines)
- Remaining bills get compact card format: bill number, title, status, affected programs, 1-sentence impact (3-4 lines)
- Keeps the document scannable while giving depth where it matters

### Doc B congressional content (facts only, shared with congressional offices)
- Curated subset only -- include bills directly tied to the Tribe's tracked programs
- No "nice to know" items, no strategy, no talking points, no timing advice
- Tighter and more professional than Doc A -- let the data speak
- Zero audience leakage: nothing in Doc B should reveal the Tribe's advocacy strategy

### Doc C/D regional aggregation
- Claude's Discretion: determine best aggregation strategy based on existing Doc C/D patterns
- Options include shared-bills-only, per-state breakdown, or hybrid -- choose what fits the existing regional document structure

### Claude's Discretion
- Regional aggregation strategy for Doc C/D congressional sections
- Confidence indicator presentation (HIGH/MEDIUM/LOW) -- placement, visual treatment
- Bill relevance criteria and filtering logic (keyword scope, committee filtering, recency window)
- Architecture spec depth for INTEL-12 (alert system), INTEL-13 (integration map), INTEL-14 (knowledge graph)
- Exact section headings and typography for congressional content
- Delegation section layout and information density

</decisions>

<specifics>
## Specific Ideas

- Bills-first ordering mirrors how policy staff actually consume briefings -- "what's moving?" before "who do I call?"
- Tiered bill detail prevents the document from bloating while ensuring the most important legislation gets full treatment
- Doc B's curated subset approach ensures congressional offices only see what's directly relevant to that Tribe's programs, maintaining professional credibility

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 15-congressional-intelligence*
*Context gathered: 2026-02-12*
