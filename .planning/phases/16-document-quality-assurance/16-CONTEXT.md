# Phase 16: Document Quality Assurance - Context

**Gathered:** 2026-02-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Audit the entire 992-document corpus across 5 quality dimensions (structural, design, accuracy, pipeline, test coverage) using 5 agents, then fix all defects found in the generation code, and re-validate. Phase delivers clean documents and a quality gate that Phase 17 depends on. Does NOT add new document features or change document content — only validates and repairs existing output.

</domain>

<decisions>
## Implementation Decisions

### Fix-or-report scope
- **Audit + fix**: Phase 16 delivers clean documents, not just a findings report
- Fixes go into the **generation code** (docx_styles.py, docx_sections.py, etc.) so all future runs produce correct output — no post-hoc DOCX patching
- Audit agents are **extended with write permissions** in the fix wave — same agents that found the issues also fix them
- Two-wave structure: Wave 1 = read-only audit producing findings JSON; Wave 2 = agents fix issues in generation code + regenerate + verify

### Gate enforcement
- **Zero P0 and P1 defects** required before Phase 17 can start — hard gate
- P2/P3 issues may remain as documented known issues
- **Severity is independent per finding** — each defect scored P0-P3 based on its own impact, not automatically derived from which audit dimension (accuracy/audience/design/copy) it falls under
- An accuracy typo might be P3; a design issue breaking layout might be P0

### Gate output
- **SYNTHESIS.md** produced as a human-readable quality certificate: pass/fail status, defect counts by severity, links to per-agent JSON files
- Per-agent JSON files (`outputs/docx_review/{agent}_findings.json`) contain detailed findings
- **Known issues section** in SYNTHESIS.md tracks all remaining P2/P3 items with locations and descriptions for future cleanup

### Claude's Discretion
- Re-validation strategy: full re-audit vs targeted spot-check after fixes, based on defect severity and count
- P0-P3 severity criteria definitions (balanced between audit dimension hierarchy and individual impact)
- Agent workflow sequencing within the two waves
- How to handle defects that span multiple agent territories

</decisions>

<specifics>
## Specific Ideas

- Priority hierarchy from roadmap still applies for **conflict resolution** when agents disagree: accuracy > audience > political > design > copy
- The 5 agents are already defined with territories in the roadmap — territories should be respected during fix wave too
- 992-document corpus = all generated DOCX packets across 4 doc types for 592 Tribes (minus Tribes with insufficient data)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-document-quality-assurance*
*Context gathered: 2026-02-12*
