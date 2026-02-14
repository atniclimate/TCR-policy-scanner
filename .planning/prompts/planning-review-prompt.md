# Claude Code Prompt: v1.3 Documentation Closeout & Harmonization

**Context:** The TCR Policy Scanner v1.3 Production Launch milestone is COMPLETE. GO confirmed 2026-02-14. All 18 phases across 4 milestones are done (70 plans, 115 requirements, 964 tests). Before running `/gsd:audit-milestone` or `/gsd:complete-milestone` and before planning the next milestone, all `.planning/` documentation needs a comprehensive review to ensure consistency, completeness, accuracy, and that nothing has been missed or left stale.

**Your role:** Documentation auditor and harmonizer. You are READ-ONLY on source code (do not modify any Python, JS, HTML, or CSS files). You WRITE to `.planning/` files only.

---

## Step 1: Read Everything First

Read these files in order. Do not start writing until you have read ALL of them:

```
.planning/PROJECT.md
.planning/STATE.md
.planning/ROADMAP.md
.planning/ROADMAP-SUPPLEMENTAL-UPDATES.md
.planning/MILESTONES.md
.planning/V1_3-OPERATIONS-PLAN.md
.planning/milestones/v1_0-ROADMAP.md
.planning/milestones/v1_0-REQUIREMENTS.md
.planning/milestones/v1_0-MILESTONE-AUDIT.md
.planning/milestones/v1_1-ROADMAP.md
.planning/milestones/v1_1-REQUIREMENTS.md
.planning/milestones/v1_1-MILESTONE-AUDIT.md
.planning/milestones/v1_2-ROADMAP.md
.planning/milestones/v1_2-REQUIREMENTS.md
.planning/milestones/v1_2-MILESTONE-AUDIT.md
.planning/REQUIREMENTS.md (v1.3 active requirements)
```

Also read the actual codebase state to ground-truth the documentation:

```bash
# Get actual Python source file count
find src/ -name "*.py" | wc -l

# Get actual test count
python -m pytest --co -q 2>/dev/null | tail -1

# Get actual LOC (src + tests)
find src/ tests/ -name "*.py" -exec cat {} + | wc -l

# Get actual document count in outputs
find outputs/packets/ -name "*.docx" 2>/dev/null | wc -l

# Get actual website files
ls -la docs/ 2>/dev/null || ls -la website/ 2>/dev/null

# Check git log for v1.2 end and v1.3 range
git log --oneline -20

# Check for any data files added in v1.3
ls -la data/congressional_intel* data/cfda_map* src/cfda_map* 2>/dev/null
find data/ -name "*.json" | wc -l
find src/ -name "*.py" -newer .planning/milestones/v1_2-MILESTONE-AUDIT.md | head -30
```

---

## Step 2: Identify Inconsistencies

Create a findings file at `.planning/DOCUMENTATION-REVIEW.md` with these sections:

### 2A: Cross-Document Consistency Audit

Check every numeric claim, date, status, and cross-reference across all documents. Known issues to investigate (non-exhaustive):

**Stale counts and metrics in PROJECT.md:**
- Says "95 source files" and "~37,900 LOC" and "743 tests" -- these are v1.2 numbers. v1.3 added Phase 15-18 code. STATE.md says 98 files and 964 tests. What are the ACTUAL current numbers from the codebase?
- "Known tech debt (8 items, 0 critical)" is from v1.2. What is the current tech debt inventory after v1.3? (STATE.md records 2 new P3 findings: CYCLOPS-016, DALE-019)
- Test suite description says "743 tests across 20+ modules" -- stale
- "Shipped v1.2 with ~37,900 LOC Python across 95 source files" -- stale, project has shipped v1.3 now

**Stale scope statements in PROJECT.md:**
- "Out of Scope" section lists "Scraper pagination fixes -- important but separate concern; v1.3 candidate" -- Phase 15 Plan 15-02 DELIVERED scraper pagination hardening for all 4 scrapers. This must move to Validated requirements.
- "Out of Scope" lists "Congress.gov bill detail fetching -- v1.3 candidate" -- Phase 15 Plan 15-04 DELIVERED bill detail fetcher + bill-to-program mapping. This must move to Validated requirements.
- "Target features" for v1.3 lists items vaguely ("Surface-level congressional intelligence improvements") but Phase 15 delivered a full congressional intelligence pipeline with confidence scoring. Description needs to match reality.

**PROJECT.md "Current Milestone" section:**
- Last updated "2026-02-12 after v1.3 milestone initialization" but v1.3 is now COMPLETE (GO confirmed 2026-02-14). The entire "Current Milestone" framing needs to shift to reflecting v1.3 as shipped.

**MILESTONES.md:**
- Has NO v1.3 entry. It stops at v1.2. This is the most critical gap -- v1.3 delivered 4 phases, 21 plans, 39 requirements, 221 new tests, congressional intelligence, document quality assurance, a production website, and survived 2 rounds of adversarial agent review. All of this is undocumented in the milestones file.

**ROADMAP.md:**
- Phase 18 shows plans 18-04, 18-05, 18-06 as unchecked `[ ]` but STATE.md confirms all are COMPLETE. Checkboxes and progress table need updating.
- Progress table shows Phase 18 as "3/6 In progress" -- should be "6/6 Complete" with completion date 2026-02-14.

**V1_3-OPERATIONS-PLAN.md:**
- Describes a 3-phase architecture (Phase 1: DOCX Visual QA, Phase 2: Website Launch, Phase 3: Production Hardening) but actual v1.3 execution was 4 phases (Phase 15: Congressional Intel, Phase 16: Doc QA, Phase 17: Website, Phase 18: Hardening). The operations plan was the pre-execution vision; the ROADMAP.md reflects what actually shipped. There is no retrospective documenting this divergence.

**ROADMAP-SUPPLEMENTAL-UPDATES.md:**
- This is a v1.2-era artifact containing table replacements and coverage updates that were apparently never merged into the main ROADMAP.md. It references Phase 12 gap closure and Phase 14 requirements (INTG-06, INTG-07, INTG-08). Since v1.2 is shipped and its ROADMAP is archived, this file is orphaned. Determine its disposition.

**Cross-reference integrity:**
- Do all 36 decision IDs in STATE.md (DEC-1501-01 through DEC-1806-01) trace back to documented plans?
- Does the ROADMAP.md coverage section (39/39 mapped) match REQUIREMENTS.md?
- Are the agent swarm definitions in ROADMAP.md consistent with V1_3-OPERATIONS-PLAN.md and actual execution?

### 2B: Completeness Audit

Check what documentation SHOULD exist but DOESN'T:

- [ ] **v1.3 MILESTONE-AUDIT.md** -- Does not exist. Must be created following the pattern of v1.0/v1.1/v1.2 audit files. Should include: requirements coverage (39/39), phase verification (4/4), cross-phase integration, E2E flow verification, test suite stats, tech debt inventory, architectural decisions, and quantitative summary.
- [ ] **v1.3 REQUIREMENTS archive** -- Current REQUIREMENTS.md should be archived to `milestones/v1_3-REQUIREMENTS.md` with all 39 requirements marked complete.
- [ ] **MILESTONES.md v1.3 entry** -- Missing entirely. Must follow the established pattern: "Delivered" paragraph, "Phases completed", "Key accomplishments", "Stats" table, "Git range", "What's next".
- [ ] **PROJECT.md v1.3 validated requirements** -- 39 requirements from v1.3 need to move from "Active" to "Validated" with milestone version tags (v1.3).
- [ ] **v1.3 ROADMAP archive** -- Once the milestone is formally closed, the current ROADMAP.md should be archived to `milestones/v1_3-ROADMAP.md` (like v1.0/v1.1/v1.2 roadmaps were archived).
- [ ] **Data dictionary** -- The data architecture has grown to include: tribal_registry.json, congressional_cache.json, tribal_aliases.json, housing_authority_aliases.json, award_cache/*.json (592 files), hazard_profiles/*.json (592 files), congressional_intel.json, regional_config.json, ecoregion_config.json, cfda_map.py, and more. Is there a single document describing every data file, its schema, source API, refresh cadence, and TSDF classification?
- [ ] **Deployment runbook** -- Is there a single document a human could follow to deploy the full system from scratch? (GitHub Actions secrets, GitHub Pages config, SquareSpace embed, domain setup)
- [ ] **Architecture diagram or module map** -- PROJECT.md has text pipeline descriptions but no comprehensive map showing how ~98 Python source files relate to each other. With 4 document types, 4 scrapers, 5 monitors, a knowledge graph, congressional intelligence pipeline, confidence scoring, regional aggregation, and a website build pipeline, a module dependency map would help the next contributor.

### 2C: Functionality Description Audit

The documentation should enable someone unfamiliar with the project to understand WHAT the tool does, HOW it works, and WHY design decisions were made. Check whether PROJECT.md accurately describes these current capabilities:

- **Congressional intelligence pipeline** (Phase 15): Bill tracking with relevance scoring, delegation data, committee activity, bill-to-program mapping via CFDA, confidence scoring with source weights and freshness decay. Is any of this described in PROJECT.md?
- **Confidence scoring system**: Source weights (Congress.gov, Federal Register, Grants.gov, USASpending), freshness decay (0.01 rate, ~69 day half-life), HIGH/MEDIUM/LOW display labels with no raw numeric scores shown to users. Documented anywhere outside STATE.md decisions?
- **4 document types with audience differentiation**: Doc A (Tribal internal strategy), Doc B (congressional evidence-only), Doc C (regional internal), Doc D (regional congressional). Air gap enforcement preventing strategy/leverage content from appearing in congressional-facing documents. Is this clearly explained for someone who has never seen the project?
- **Website capabilities**: Fuzzy search via Fuse.js across 592 Tribal Nations with alias matching, ARIA combobox with keyboard navigation, dark mode with CRT scanline effect, mobile responsive (375px+), SquareSpace iframe embed with sandbox permissions, GitHub Pages deployment, WCAG 2.1 AA compliance. Described in PROJECT.md?
- **Agent swarm methodology**: 4 milestones used progressively sophisticated agent swarm patterns (4 territory agents in Phase 15, 5 parallel audit agents in Phase 16, 4 review agents in Phase 17, 4 adversarial bug hunters with 2 rounds in Phase 18). Is this methodology documented as a reusable pattern for future milestones?
- **Production hardening results**: Trust score 9/10, Joy score 9/10, zero P0/P1/P2 issues remaining, 2 P3 accepted for launch. GO decision confirmed. Is the launch readiness state clearly captured?

### 2D: Gap Analysis for Next Milestone

Before planning the next milestone, surface:

**Deferred from v1.3:**
- VoteNode deferred pending Senate.gov structured vote data (DEC-1503-04)
- Voting records deferred pending Senate API availability (DEC-1504-03)
- 2 P3 findings accepted but not fixed: CYCLOPS-016, DALE-019 (DEC-1805-01). What are these specifically? Can you find them in the outputs/bug_hunt/ findings files?

**Tech debt carried forward:**
- Compile the complete current tech debt inventory from: v1.2 audit (8 items), v1.3 Phase 15-18 decisions, 18-05 re-audit findings, and any items noted in plan summaries
- Which v1.2 tech debt items were resolved by v1.3? (e.g., scraper pagination was v1.2 tech debt, fixed in Phase 15)
- Which remain?

**Deferred from earlier milestones never picked up:**
- v1.0: "No live scraper integration tests" (TEST-01 through TEST-05) -- still deferred?
- v1.0: "Hardcoded FY26 dates" -- resolved by v1.2 dynamic FY config?
- v1.1: "Award/hazard caches seeded with empty structures" -- resolved by v1.2 data population?
- v1.1: "SquareSpace embed URL is placeholder" -- resolved by v1.2 production URLs?
- Verify each deferred item from v1.0/v1.1/v1.2 audits: resolved, still deferred, or no longer relevant?

**STATE.md Todos:**
- DOCX layout and presentation redesign
- Extreme weather vulnerability data
- Climate risk/impact/vulnerability assessments per Tribe
- NOAA climate projections, EPA EJScreen, CDC/ATSDR SVI
- Are these still the right priorities for the next milestone?

**Emergent needs from v1.3 execution:**
- What did the 2-round adversarial audit reveal about system gaps that go beyond P0-P3 bug fixes?
- What UX improvements were identified but categorized as out-of-scope for v1.3?
- Are there scaling concerns for moving beyond the 100-200 user launch window?
- The website is vanilla HTML/JS/CSS -- are there maintenance or feature-addition concerns?

---

## Step 3: Update Documents

After completing the findings file, update documents in this order:

### 3A: PROJECT.md (highest priority -- project identity document)

This file should describe the system AS IT EXISTS TODAY, not as it existed at v1.2. Updates:

1. **Validated requirements list**: Add all v1.3 capabilities with "-- v1.3" tags. Key additions:
   - Scraper pagination hardening (all 4 scrapers paginate to completion with safety caps)
   - Congressional intelligence pipeline (bill tracking, bill-to-program CFDA mapping, committee activity)
   - Confidence scoring with source weights and freshness decay (HIGH/MEDIUM/LOW display)
   - Structural validation for 992-document corpus
   - Production website with Fuse.js fuzzy search, ARIA combobox, dark mode, SquareSpace embed
   - WCAG 2.1 AA compliance (keyboard nav, 4.5:1 contrast, reduced motion)
   - GitHub Pages automated deployment pipeline
   - Production hardening with 2-round adversarial agent audit (trust 9/10, joy 9/10)
   - GitHub Actions pinned to commit SHAs for supply chain protection
   - CSP headers blocking external requests

2. **Out of Scope**: Remove "Scraper pagination fixes" and "Congress.gov bill detail fetching" (both delivered). Review remaining items for accuracy.

3. **Current Milestone / Current State**: Update to reflect v1.3 COMPLETE. Either set "Current Milestone" to "Planning next milestone" or mark v1.3 as shipped alongside v1.0/v1.1/v1.2.

4. **Numeric metrics**: Update source file count, LOC, test count, document count to actual codebase values. Use the bash commands from Step 1 -- do not guess.

5. **Known tech debt**: Replace v1.2's 8-item list with current inventory.

6. **Data files inventory**: Add any new data files from v1.3 (congressional_intel.json, cfda_map references, etc.)

7. **Key Decisions table**: Add significant v1.3 decisions (confidence scoring methodology, bill relevance scoring weights, air gap exemptions, NO-GO then GO pattern, GitHub Actions SHA pinning, etc.)

8. **Last updated timestamp**: Set to today's date with accurate description.

### 3B: MILESTONES.md (critical gap -- v1.3 entry missing)

Add a complete v1.3 entry following the exact pattern of v1.0/v1.1/v1.2 entries:

```markdown
## v1.3 Production Launch (Complete: 2026-02-14)

**Delivered:** [single paragraph summarizing what v1.3 delivered]

**Phases completed:** 15-18 (21 plans total)

**Key accomplishments:**
[bullet list of major deliverables, matching the detail level of v1.0/v1.1/v1.2 entries]

**Stats:**
[table matching format of previous entries]

**Git range:** `8f96850` (v1.2 end) -> `[VERIFY: actual v1.3 end commit]`

**What's next:** [placeholder for next milestone]
```

Derive the "Delivered" paragraph and "Key accomplishments" from:
- ROADMAP.md Phase 15-18 goals and success criteria
- STATE.md v1.3 phase structure and decisions
- The fact that this milestone took the system from "992 documents with tech debt" to "production-ready website with adversarial verification"

### 3C: ROADMAP.md

1. Update Phase 18 plan checkboxes: mark 18-04, 18-05, 18-06 as `[x]`
2. Update progress table: Phase 18 row should show "6/6 | Complete | 2026-02-14"
3. Verify all other entries are accurate

### 3D: STATE.md

STATE.md appears to already be updated (v1.3 COMPLETE, GO confirmed). Verify:
- Performance Metrics table is accurate (cross-check with codebase)
- Decisions list is complete (36 entries -- any missing?)
- Todos section reflects actual priorities
- Session Continuity accurately captures the resume point
- LOC figure (~37,900) may be stale if v1.3 added significant code -- verify

### 3E: V1_3-OPERATIONS-PLAN.md

Add a **Retrospective** section at the bottom documenting:

```markdown
## Retrospective (added [date])

### Plan vs. Execution

The operations plan designed a 3-phase approach:
1. DOCX Visual QA ("The Inspector")
2. Website Launch ("The Storefront")  
3. Production Hardening (Bug Hunt Swarm)

Actual execution expanded to 4 phases:
1. Phase 15: Congressional Intelligence Pipeline (not in original plan)
2. Phase 16: Document Quality Assurance (evolved from "DOCX Visual QA")
3. Phase 17: Website Deployment (evolved from "Website Launch")
4. Phase 18: Production Hardening (closest to original plan)

### Key Divergences
[What changed and why -- Phase 15 was added because congressional intelligence was identified as a v1.3 requirement during milestone initialization]

### What Worked
[Agent swarm methodology, territory-based parallelism, adversarial review pattern, NO-GO then fix then re-audit pattern]

### What Would Be Done Differently
[Any lessons learned about planning, estimation, agent design, etc.]
```

This retrospective is institutional knowledge for designing the next milestone's operations plan.

### 3F: ROADMAP-SUPPLEMENTAL-UPDATES.md

This file contains v1.2-era updates (Phase 12 gap closure, Phase 14 requirements INTG-06/07/08) that were never merged. Since v1.2 is archived and its roadmap is in `milestones/v1_2-ROADMAP.md`:

1. Verify whether the information in the supplemental file IS reflected in `v1_2-ROADMAP.md` and `v1_2-REQUIREMENTS.md`
2. If yes: add a deprecation header to the file noting it is superseded
3. If no: merge the missing information into the archived v1.2 files first, then deprecate

### 3G: Archive preparation

Prepare (but do not execute without confirmation) the archive steps:
- Note that current `REQUIREMENTS.md` should be copied to `milestones/v1_3-REQUIREMENTS.md` with all 39 requirements marked complete
- Note that current `ROADMAP.md` should be copied to `milestones/v1_3-ROADMAP.md` with all completion markers
- Document these as recommended actions in the summary -- they should happen as part of `/gsd:complete-milestone`

---

## Step 4: Create Summary

After all updates, create `.planning/DOCUMENTATION-REVIEW-SUMMARY.md` with:

1. **Changes made** -- list every file modified and what changed (section-level specificity)
2. **Gaps remaining** -- anything that could not be resolved without human input
3. **Recommended human actions** -- things Patrick needs to decide, verify, or approve
4. **Deferred items inventory** -- complete list of all deferred/tech-debt items across all 4 milestones with current status (resolved, still deferred, no longer relevant)
5. **Next milestone readiness assessment** -- is the documentation foundation solid enough to begin planning? What would the next milestone planner need to know that is not yet written down?

---

## Rules

- **Do NOT modify any source code** (Python, JS, HTML, CSS, YAML, JSON data files). Documentation files in `.planning/` only.
- **Do NOT fabricate numbers.** If you cannot determine an actual count from the codebase, write "VERIFY: [what needs checking]" and flag it for human resolution. A wrong number is worse than no number.
- **Preserve voice.** This project capitalizes Indigenous/Tribal/Nations/Peoples/Knowledge, avoids em dashes where possible, uses relational framing, and maintains sovereignty-centered language. Match the existing writing style in each document.
- **Preserve structure.** When updating existing documents, maintain their organizational pattern. Do not restructure documents without noting why in the findings file.
- **Write findings to disk immediately.** Do not hold findings in your context window across multiple file operations. Write them to `.planning/DOCUMENTATION-REVIEW.md` as you discover them.
- **Be specific.** "PROJECT.md line 91 says 'Scraper pagination fixes -- v1.3 candidate' but Phase 15 Plan 15-02 delivered this (ROADMAP.md Phase 15 requirements include INTEL-02)" is useful. "Some items might be stale" is not.
- **Flag uncertainties.** If two documents disagree and you cannot determine which is correct from the codebase, flag both values and note the discrepancy for human resolution.
- **Respect the archive pattern.** Files in `milestones/` are historical records. Only add missing information or correct factual errors -- do not rewrite or restructure archived documents.

---

## Why This Matters

This tool serves 592 Tribal Nations. The documentation is not just process overhead. It is the institutional memory that enables the next person, the next Claude Code session, or the next collaborator to pick up where we left off and continue the work in a good way. Accurate documentation means accurate tool-building. Incomplete documentation means repeated work, missed context, and compounding drift. This review closes the loop on v1.3 so the next milestone starts from a clean, truthful foundation.

Small things have big impact.

---

*Prepared: 2026-02-13*
*For: TCR Policy Scanner .planning/ documentation review and v1.3 closeout*
*Scope: All .planning/ files, read-only on source code*
*Trigger: Run after v1.3 GO confirmed, before `/gsd:complete-milestone`*
