# Phase 18: Production Hardening - Context

**Gathered:** 2026-02-13
**Status:** Ready for planning

<domain>
## Phase Boundary

4-agent adversarial review of the complete TCR Policy Scanner system (scrapers, document generation, website, deployment pipelines) culminating in a go/no-go launch decision for 100-200 concurrent Tribal users during a 48-hour launch window. Includes a find-fix-verify cycle — agents report, Claude fixes, agents re-verify until clean.

</domain>

<decisions>
## Implementation Decisions

### Finding Severity & Triage
- **Scoring rubric**: Each finding gets a numeric score based on impact, likelihood, and user-facing visibility. Score determines P0/P1/P2/P3 classification.
- **Conflict resolution**: Agent domain expertise wins. Security findings defer to Dale Gribble, code inspection to Cyclops, UX to Mr. Magoo, hygiene to Marie Kondo.
- **Agent independence**: All 4 agents work fully in parallel with no cross-talk. No agent sees another's findings during their review. Prevents groupthink.
- **Output format**: JSON findings file + markdown summary per agent (same pattern as Phase 16). Machine-readable for tracking, human-readable for review. Output path: `outputs/bug_hunt/{agent}_findings.json` + `{agent}_summary.md`.

### Go/No-Go Criteria
- **Launch bar**: Zero P0 AND zero P1 for a full "go" decision. P2/P3 can ship.
- **Conditional go**: Allowed — "go with caveats" is a valid outcome (e.g., "go, but monitor X" or "go, but fix these P1s within 48 hours"). Still requires zero P0.
- **Decision authority**: Human (user) makes the final call after reviewing the synthesis report. Agents produce findings, Claude synthesizes, user decides.
- **Concurrency validation**: Focus on download reliability — can 200 people search and download DOCX files without errors? GitHub Pages CDN handles traffic. Test the user flow, not server load.

### Fix-Verify Cycle
- **Scope**: Full find-fix-verify cycle within this phase. Agents find issues, Claude fixes P0/P1s, then re-review confirms fixes.
- **Rounds**: Loop until clean — keep reviewing until zero P0/P1. If new issues appear during fixes, fix those too.
- **Marie Kondo findings**: Act on low-risk findings (dead code removal, import cleanup, simple hygiene). Skip anything that could introduce regressions. Use judgment.
- **Regression protocol**: Fix forward. If a fix introduces a new issue, fix the regression too rather than reverting. Iterate until both resolved.

### Agent Testing Scope
- **System coverage**: Full system — scrapers, document generation, website, deployment pipelines, CI/CD. All agents cover the complete attack surface.
- **Mr. Magoo target**: Both local preview AND live deployed site. Start with local for fast iteration, validate against live as final check.
- **Test data**: Real 592-Tribe dataset. Use actual DOCX files, real search index, real award/hazard data. Tests what ships.
- **Sovereignty strictness**: Strict zero-tolerance on tracking (no Google Analytics, no Google Fonts CDN, no cookies, CSP blocks external requests, no source maps in production). Flexible on presentation choices (naming conventions, framing language). Any tracking/data leakage violation is P0.

### Claude's Discretion
- Exact scoring rubric dimensions and thresholds (impact x likelihood x visibility weighting)
- Agent checklist item prioritization within each agent's domain
- Fix ordering when multiple P0/P1s exist simultaneously
- Whether to batch fixes or apply one-at-a-time with re-verification
- Marie Kondo finding risk assessment (which are "low-risk" enough to act on)

</decisions>

<specifics>
## Specific Ideas

- Reuse Phase 16's proven pattern: parallel agents -> JSON findings -> synthesis report -> fix cycle -> re-verify
- Mr. Magoo should navigate as a non-technical Tribal staff member — no source code reading, just the website experience
- Dale Gribble's 18-item UNDRIP/OCAP/CARE checklist is the sovereignty standard
- Cyclops's 15-item deep inspection checklist covers boundary conditions, race conditions, resource leaks
- Final synthesis should be a clear go/no-go recommendation with evidence, presented to user for decision

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 18-production-hardening*
*Context gathered: 2026-02-13*
