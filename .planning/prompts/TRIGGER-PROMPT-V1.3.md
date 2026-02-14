# TCR Research Team — v1.3 Congressional Intelligence Trigger Prompt

Copy everything below the `---` line and paste into a Claude Code session at `F:\tcr-policy-scanner`.

---

```
I need you to lead the TCR Policy Scanner Research Team for the v1.3 milestone:
Congressional Intelligence Intake. This feeds directly into the DOCX advocacy
packet generation phase.

## Context

Read STATE.md — v1.2 is SHIPPED (743 tests, 95 files, ~37,900 LOC, 992 documents).
Read .planning/PROJECT.md for full project context.
Read V1.3-OPERATIONS-PLAN.md for the 3-phase operations plan.

v1.3 focus: Build the congressional intelligence pipeline that transforms raw
Congress.gov data into actionable content in the DOCX advocacy packets. This
milestone's output becomes the input for the DOCX QA phase (Phase 1 of Operations Plan).

Key v1.3 candidates from STATE.md:
- Congressional alert system (21 story points, 3 sprints)
- Congress.gov bill detail fetching
- Scraper pagination fixes (3 of 4 silently truncate)
- Confidence scoring for intelligence products

## The Research Team

Create an agent team with 4 teammates. Each has a v1.3 mission focused on
congressional intelligence flowing into DOCX generation.

### Teammate 1: Sovereignty Scout (sovereignty-scout)
Definition: .claude/agents/sovereignty-scout.md

Spawn prompt: "You are Sovereignty Scout. Read .claude/agents/sovereignty-scout.md
for your full identity and v1.3 mission. You own src/scrapers/, data/, config/,
and scripts/. Your v1.3 tasks:
1. Build Congress.gov bill detail fetcher (full bill records with sponsors,
   committees, actions, subjects, text URLs)
2. Fix pagination in all 4 scrapers (3 of 4 silently truncate — this is critical)
3. Build congressional-to-program mapping (bills → ALNs → relevance scores)
4. Enhance delegation data with live committee assignments and voting records
Output: congressional_intel.json consumable by the DOCX orchestrator.
Coordinate with Fire Keeper on data model schema BEFORE building.
Coordinate with River Runner on test fixtures from real API responses.
Report findings with advocacy framing — not 'fetched 47 records' but '47 active
awards supporting Tribal climate resilience.'"

### Teammate 2: Fire Keeper (fire-keeper)
Definition: .claude/agents/fire-keeper.md

Spawn prompt: "You are Fire Keeper. Read .claude/agents/fire-keeper.md for your
full identity and v1.3 mission. You own src/, tests/, validate_data_integrity.py,
and requirements.txt. Your v1.3 tasks:
1. Build Pydantic models for congressional data (Legislator, BillIntelligence,
   VoteRecord, CongressionalIntelReport) — these are the CONTRACT
2. Extend TribePacketContext with CongressionalContext
3. Build DOCX section renderers for congressional content:
   - Doc A: delegation + bills + talking points + timing
   - Doc B: delegation + bills (facts only, NO strategy)
   - Doc C/D: regional aggregation
4. Implement confidence scoring (source weights × freshness decay)
5. Verify v1.2 Four Fixes are still clean (grep checks for logger, FY, format_dollars, paths)
Air gap compliance is non-negotiable: zero org/tool names in rendered content.
Coordinate with Scout on data model — your models must match their output.
Run tests after every change."

### Teammate 3: River Runner (river-runner)
Definition: .claude/agents/river-runner.md

Spawn prompt: "You are River Runner. Read .claude/agents/river-runner.md for your
full identity and v1.3 mission. You own tests/, validate_data_integrity.py,
schema validation, and CI workflows. Your v1.3 tasks:
Track A — Congressional Validation:
1. Scraper pagination tests (all 4 scrapers: full pagination, truncation detection, circuit breaker)
2. Congressional model validation tests (against real API response shapes)
3. Congressional-to-program mapping tests (ALN correctness, urgency correlation)
Track B — DOCX QA Infrastructure:
4. Build scripts/validate_docx_structure.py (the Phase 1 Session 1A tool)
5. DOCX content correctness tests (dollar amounts, air gap, audience leakage)
6. End-to-end pipeline test (congressional data → context → DOCX → validation)
7. Confidence scoring tests (decay curves, display thresholds)
Track C — CI Enhancement:
8. Add congressional scan + validation to GitHub Actions
9. Add DOCX structural validation to packet generation workflow
Target: 900+ tests by v1.3 ship (currently 743).
Coordinate with Scout on test fixtures from real API responses.
Coordinate with Fire Keeper on model test expectations."

### Teammate 4: Horizon Walker (horizon-walker)
Definition: .claude/agents/horizon-walker.md

Spawn prompt: "You are Horizon Walker. Read .claude/agents/horizon-walker.md for
your full identity and v1.3 mission. You own docs/, .planning/, and docs/web/.
Your v1.3 tasks:
1. Write ENH-001: Congressional Alert System architecture (21 story points → 3 sprints,
   fully decomposed with change detection, alert classification, per-Tribe routing)
2. Write V1.3-PHASE-MAP.md showing data flow from Congress.gov through DOCX agents
   through website agents through bug hunters to Tribal Leader's hands
3. Update DATA-COMPLETENESS-V1.3.md with congressional sources + confidence scores
4. Write ENH-002: Knowledge Graph Congressional Nodes (Bill, Legislator, Committee, Vote
   node types with edge types and query examples)
5. Write ENH-003: Interactive Graph Visualization spec (D3.js, SquareSpace-safe,
   accessible, actionable for a frontend developer)
Every spec gets an Impact Statement answering: 'How does this help a Tribal Leader
protect their community?'
Coordinate with ALL teammates — your phase map reflects their ground truth."

## Coordination Rules

1. Sovereignty Scout and Fire Keeper must agree on the congressional data model
   BEFORE either builds against it. Schedule this as the FIRST coordination task.
2. River Runner writes tests for Scout's scrapers and Fire Keeper's models —
   coordinate on fixtures and expected behaviors.
3. Horizon Walker's phase map and completeness roadmap depend on ground-truth
   findings from all 3 other teammates. Walker collects, synthesizes, documents.
4. File ownership is strict:
   - Scout: src/scrapers/, data/, config/, scripts/
   - Fire Keeper: src/ (non-scraper), src/packets/, src/models/
   - River Runner: tests/, validate_data_integrity.py, .github/workflows/
   - Horizon Walker: docs/, .planning/
5. All changes must pass: python -m pytest tests/ -v
6. The team lead synthesizes progress into a status update after each round.

## Success Criteria

The Research Team has succeeded when:
- [ ] Congress.gov bill details flow into congressional_intel.json
- [ ] All 4 scrapers paginate fully (zero silent truncation)
- [ ] Congressional data validates against Pydantic models
- [ ] DOCX packets render congressional intelligence (all 4 doc types)
- [ ] Confidence scores appear on intelligence products
- [ ] DOCX structural validator exists and runs in CI
- [ ] Test count reaches 900+ (from 743)
- [ ] Phase integration map shows every handoff between all agent teams
- [ ] Congressional alert system is architecturally specified (ENH-001)
- [ ] All new code respects CLAUDE.md values and critical rules
- [ ] Air gap audit passes: zero org/tool names in rendered content

## What Comes After This Team

When this team completes, their output feeds three sequential phases:

Phase 1 (DOCX QA): 5 specialist agents audit the generated documents
  → Design Aficionado, Accuracy Agent, Pipeline Surgeon, Gatekeeper, Gap Finder

Phase 2 (Website): 4 agents build and deploy the SquareSpace front-end
  → Web Wizard, Mind Reader, Keen Kerner, Pipeline Professor

Phase 3 (Production Hardening): 4 agents × 2 clones stress-test the live product
  → Mr. Magoo, Cyclops, Dale Gribble, Marie Kondo

The quality of THIS team's work determines the quality of everything downstream.
Congressional intelligence that's incomplete, poorly modeled, or incorrectly
rendered will propagate errors through 13 subsequent agents and into the hands
of Tribal Leaders. Build it right.

Begin by reading CLAUDE.md, STATE.md, and the agent definitions. Then create the team.
```
