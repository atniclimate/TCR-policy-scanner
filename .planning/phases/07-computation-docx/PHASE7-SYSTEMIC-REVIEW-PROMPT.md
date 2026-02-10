# Phase 7 Systemic Review: Comprehensive Agent Swarm Prompt

## Mission

Execute a critical systemic review of TCR Policy Scanner Phase 7 (Computation + DOCX Generation) -- the 7 new source modules, 4 test files, updated orchestrator, and all integration seams. This review ensures the code is functional, correct, secure, and Phase 8-ready before any further development occurs.

**Non-negotiable constraint:** All references to NCAI and ATNI must be removed from the entire codebase to prevent perceived ethical violations. These organizations did not authorize use of their names in this tool.

---

## Project State Snapshot

| Metric | Value |
|--------|-------|
| Milestone | v1.1 Tribe-Specific Advocacy Packets |
| Phase | 7 of 8 (Computation + DOCX Generation) |
| Plans completed | 4/4 (07-01 through 07-04) |
| Phase 7 source modules | 7 files in `src/packets/` |
| Phase 7 test files | 4 files in `tests/` |
| Total tests passing | ~220+ (193 at 07-03 + integration tests from 07-04) |
| Requirements targeted | ECON-01, DOC-01, DOC-02, DOC-03, DOC-04 |
| Python version | 3.12 |
| Key dependency | python-docx (programmatic DOCX generation) |
| Platform | Windows (F:\tcr-policy-scanner) + GitHub Actions (Linux) |

### Phase 7 Source Files (Review Targets)

| File | Purpose | Lines | Plan |
|------|---------|-------|------|
| `src/packets/economic.py` | Economic impact calculator (BEA multipliers, BCR, benchmarks) | ~396 | 07-01 |
| `src/packets/relevance.py` | Program relevance filter (hazard-based, 8-12 programs) | ~328 | 07-01 |
| `src/packets/docx_styles.py` | Style manager, CI status colors, cell shading helpers | ~271 | 07-02 |
| `src/packets/docx_engine.py` | Document creation, page layout, atomic save, full assembly | ~205 | 07-02/04 |
| `src/packets/docx_hotsheet.py` | Hot Sheet renderer (10 sub-sections per program) | ~714 | 07-03 |
| `src/packets/docx_sections.py` | Cover page, TOC, appendix renderers | ~235 | 07-04 |
| `src/packets/orchestrator.py` | PacketOrchestrator (updated with generate_packet) | ~486 | 07-04 |

### Phase 7 Test Files

| File | Tests | Coverage Area |
|------|-------|---------------|
| `tests/test_economic.py` | ~16 | Calculator, BCR, benchmarks, relevance filter |
| `tests/test_docx_styles.py` | ~17 | StyleManager, helpers, engine skeleton |
| `tests/test_docx_hotsheet.py` | ~35 | All Hot Sheet sections, CI statuses, edge cases |
| `tests/test_docx_integration.py` | ~19 | End-to-end pipeline, DOCX validity, content verification |

### Upstream Dependencies (DO NOT MODIFY)

- `src/packets/context.py` -- TribePacketContext dataclass
- `src/packets/registry.py` -- TribalRegistry
- `src/packets/congress.py` -- CongressionalMapper
- `src/packets/ecoregion.py` -- EcoregionMapper
- `src/packets/awards.py` -- TribalAwardMatcher
- `src/packets/hazards.py` -- HazardProfileBuilder
- `data/program_inventory.json` -- 16-program inventory
- `data/graph_schema.json` -- Structural asks, authorities, barriers
- `config/scanner_config.json` -- Application configuration

---

## NCAI/ATNI Reference Removal (CRITICAL)

All references to "NCAI" (National Congress of American Indians) and "ATNI" (Affiliated Tribes of Northwest Indians) must be removed from the entire codebase. These organizations did not authorize association with this tool. This is an ethical compliance requirement, not optional cleanup.

### Files Containing References (12 files identified)

**Source code (1 file):**
- `src/analysis/relevance.py:3` -- docstring: "ATNI program inventory"

**Documentation and planning (11 files):**
- `README.md` -- Lines 10, 17, 259: "ATNI Climate Resilience Committee", "ATNI program inventory"
- `FY26_TCR_PolicyScanner_Reference.md` -- Lines 3, 49: "ATNI | Climate Resilience Committee"
- `docs/CLAUDE-CODE-PROMPT.md` -- Lines 10, 12, 14: "ATNI TCR Policy Scanner", repo URL
- `docs/STRATEGIC-FRAMEWORK.md` -- Line 1: "ATNI TCR"
- `.planning/v1.1-session-prompt.md` -- Lines 12, 20, 40, 46, 52, 63, 106: Multiple NCAI/ATNI event references
- `.planning/MILESTONES.md` -- Line 28: "NCAI, ATNI"
- `.planning/PROJECT.md` -- Lines 7, 58, 126: "NCAI Climate Action Task Force", "ATNI"
- `.planning/research/FEATURES.md` -- Lines 28, 89, 125, 325: ATNI/NCAI references
- `.planning/research/ARCHITECTURE.md` -- Line 520: "Prepared for [Tribe] by ATNI"
- `.planning/phases/05-foundation/TEAM1-epa-tribes-api.md` -- Lines 301, 451: "NCAI Tribal Directory"
- `.planning/phases/07-computation-docx/07-RESEARCH.md` -- Line 446: "NCAI Honor the Promises"

### Replacement Strategy

- **In source code:** Replace "ATNI program inventory" with "tracked program inventory" or equivalent neutral language
- **In README/docs:** Replace organizational attributions with generic descriptions:
  - "ATNI Climate Resilience Committee" -> "Tribal Climate Resilience advocacy" or remove attribution entirely
  - "NCAI Climate Action Task Force" -> "Tribal Climate Resilience program"
  - "github.com/atniclimate/" -> "private repository" (no org-specific URL)
  - "Maintained By: ATNI..." -> "Maintained by project contributors"
  - "Prepared for [Tribe] by ATNI" -> "Prepared for [Tribe]"
- **In planning/research docs:** Replace specific organizational names with generic references
  - "NCAI Mid-Year" -> "advocacy event"
  - "ATNI sessions" -> "policy sessions"
  - "NCAI Honor the Promises" -> remove or generalize the reference
- **DO NOT** replace the organizational names with other specific organizations
- **DO NOT** change the functional meaning of any sentence -- only swap the proper nouns

---

## Review Domains and Agent Assignments

### Wave 1: Static Analysis + NCAI/ATNI Removal (4 agents, parallel)

**Agent 1: NCAI/ATNI Reference Purge** (code-simplifier or general-purpose)
- Scope: All 12 files listed above
- Task: Replace every NCAI/ATNI reference per the replacement strategy
- Coordination: Write completed replacements to `REVIEW-COORDINATION.md` Section A
- Verify: `grep -ri "NCAI\|ATNI" .` returns zero matches across entire repo
- Tools: Grep, Read, Edit
- **MUST run first or in parallel with non-overlapping agents**

**Agent 2: Python Code Quality + Correctness** (code-simplifier or feature-dev:code-reviewer)
- Scope: All 7 Phase 7 source files
- Checks:
  - `datetime.utcnow()` usage (must be `datetime.now(timezone.utc)`)
  - `open()` without `encoding="utf-8"` on Windows
  - `Path.write_text()` without encoding
  - Mutable default arguments in function signatures
  - `0 or default` falsy patterns for nullable ints
  - Type annotation correctness (Python 3.12 union syntax `X | Y`)
  - Import ordering and unused imports
  - Consistent logger naming patterns
  - Edge cases: None values flowing through dict.get() chains
  - Division by zero guards (jobs_per_million with $0 obligation)
  - Float precision issues in dollar formatting
- Coordination: Write findings to `REVIEW-COORDINATION.md` Section B
- Tools: Read, Grep, code-simplifier patterns

**Agent 3: python-docx Best Practices** (general-purpose with Context7)
- Scope: docx_styles.py, docx_engine.py, docx_hotsheet.py, docx_sections.py
- Research: Use Context7 to fetch python-docx documentation for:
  - OxmlElement reuse bugs (cell shading pattern)
  - Style collision handling
  - Atomic file save patterns with python-docx
  - Header/footer paragraph management
  - Page break vs section break behavior
  - Table formatting XML patterns
  - Known issues with python-docx on Windows
- Checks:
  - OxmlElement created fresh per call (not reused)
  - Style names checked before creation (no ValueError)
  - Cell shading uses correct XML namespace
  - `paragraph.clear()` vs `cell.text = ""` patterns
  - Table row/cell access patterns (bounds checking)
  - Header/footer `is_linked_to_previous` set correctly
  - Import of `WD_ALIGN_PARAGRAPH` inside method body (docx_engine.py:111) -- should be at module level
  - Document save with `NamedTemporaryFile` on Windows (delete=False required)
- Coordination: Write findings to `REVIEW-COORDINATION.md` Section C
- Tools: Context7 MCP (resolve-library-id, query-docs), Read

**Agent 4: Data Flow Integrity** (feature-dev:code-explorer or general-purpose)
- Scope: Full data path from orchestrator -> economic calculator -> relevance filter -> DOCX engine -> renderers
- Trace these critical paths:
  1. `orchestrator.generate_packet_from_context()` -> `EconomicImpactCalculator.compute()`: Does the `awards` list format match what compute() expects? Are `districts` in the expected schema?
  2. `ProgramRelevanceFilter.filter_for_tribe()` -> programs dict: Does the filter return dicts with `id`, `name`, `cfda`, `ci_status` fields? Do downstream renderers depend on fields that the filter might strip?
  3. `TribeEconomicSummary.by_program` -> `HotSheetRenderer.render_all_hotsheets()`: Impact lookup by `program_id` -- what if program IDs in economic summary don't match program dict `id` fields?
  4. `context.hazard_profile` schema: Orchestrator loads from `hazard_data.get("sources", {})` but hotsheet renderer checks both `hazard_profile.get("fema_nri")` AND `hazard_profile.get("sources", {}).get("fema_nri")` -- is there a wrapper inconsistency?
  5. `_load_structural_asks()`: Hardcoded path `data/graph_schema.json` -- does this work on GitHub Actions? Should it use config?
  6. `DocxEngine.__init__` reads `config["packets"]["output_dir"]` but `generate_packet_from_context` creates engine with `self.config` -- are the config paths consistent?
- Coordination: Write findings to `REVIEW-COORDINATION.md` Section D
- Tools: Read, Grep, Glob

### Wave 2: Domain + Security Review (3 agents, parallel, after Wave 1 completes)

**Agent 5: Security Audit** (dale-gribble or security-auditor)
- Scope: All Phase 7 files + config/scanner_config.json
- Checks:
  - Path traversal: Can `tribe_id` in `DocxEngine.save()` contain `../` to write outside output_dir?
  - Temp file cleanup: Does `NamedTemporaryFile` always get cleaned up on exception?
  - Config injection: Can scanner_config.json values lead to arbitrary file writes?
  - Information disclosure: Does DOCX metadata (author, title, revision) leak system info?
  - XML injection via python-docx: Can malicious Tribe names or program names inject XML into .docx?
  - Logging of sensitive data: Are Tribe names or financial data logged at inappropriate levels?
  - Denial of service: Can a massive awards list or 1000+ programs cause memory exhaustion?
  - `json.load()` without size limit on graph_schema.json
  - `os.replace()` race conditions on Windows
  - Concurrent write safety if two processes generate for same Tribe
- Coordination: Write findings to `REVIEW-COORDINATION.md` Section E
- Tools: Read, Grep, security audit patterns

**Agent 6: Test Coverage + Correctness** (test-writer or tester)
- Scope: All 4 Phase 7 test files + source they test
- Checks:
  - Test isolation: Do tests share state? Can test order affect results?
  - Fixture correctness: Do mock programs/context match actual data schemas?
  - Missing edge cases:
    - `economic.py`: What about `float('inf')` obligation? NaN? Extremely large numbers?
    - `relevance.py`: What if `programs` dict is empty? What if all programs are critical?
    - `docx_hotsheet.py`: What about very long Tribe names (100+ chars)? Unicode in names?
    - `docx_engine.py`: What if output_dir is read-only? What if disk is full?
    - `docx_sections.py`: What if context has 50 programs? Performance?
  - Test/source parity: Are all public methods tested? Any dead code paths?
  - Integration test robustness: Do tests clean up tmp files?
  - `test_minimum_test_count` meta-test: Is the hardcoded 193 correct? Should be updated?
  - Assertion quality: Are assertions specific enough? `assert len(texts) >= 10` vs checking actual content
- Coordination: Write findings to `REVIEW-COORDINATION.md` Section F
- Tools: Read, Grep, pytest analysis

**Agent 7: GitHub Best Practices + Phase 8 Readiness** (general-purpose with WebSearch)
- Scope: Project structure, documentation, CI/CD, GitHub deployment
- Research (WebSearch):
  - Best practices for python-docx projects hosted on GitHub (2025-2026)
  - DOCX generation libraries comparison (python-docx vs alternatives)
  - GitHub Actions workflows for Python DOCX generation projects
  - pytest best practices for document generation testing
  - python-docx performance optimization for batch generation
- Documentation review:
  - Is README accurate after NCAI/ATNI removal?
  - Are all Phase 7 modules documented in project docs?
  - Is CLAUDE.md current and accurate?
  - Are planning docs up to date (STATE.md, ROADMAP.md checkboxes)?
  - Is REQUIREMENTS.md marking Phase 7 items as Pending when code exists?
- Phase 8 preparation checklist:
  - [ ] STATE.md updated to reflect Phase 7 completion
  - [ ] ROADMAP.md checkboxes for 07-01 through 07-04 marked [x]
  - [ ] REQUIREMENTS.md updated: ECON-01, DOC-01, DOC-02, DOC-03, DOC-04 marked complete
  - [ ] All 07-*-SUMMARY.md files exist and are accurate
  - [ ] Phase 8 context file (.planning/phases/08-assembly-polish/08-CONTEXT.md) needs creation
  - [ ] Memory files (MEMORY.md) updated with Phase 7 completion
  - [ ] Test count in test_minimum_test_count updated to actual count
- Coordination: Write findings to `REVIEW-COORDINATION.md` Section G
- Tools: WebSearch, WebFetch, Read, Glob

### Wave 3: Cross-Validation + Fix Integration (2 agents, after Wave 2)

**Agent 8: Conflict Detection + Fix Orchestrator** (general-purpose)
- Scope: `REVIEW-COORDINATION.md` all sections
- Task:
  1. Read all findings from Sections A-G
  2. Identify conflicts (e.g., Agent 2 wants to change a line that Agent 1 already changed)
  3. Identify cascade risks (e.g., changing a data format breaks a downstream consumer)
  4. Prioritize fixes by impact: Critical (crashes/data corruption) > High (incorrect output) > Medium (code quality) > Low (style/docs)
  5. Write a consolidated `PHASE7-FIX-PLAN.md` with:
     - Each fix numbered (F7-01 through F7-NN)
     - File(s) affected
     - Agent that found it
     - Priority (Critical/High/Medium/Low)
     - Proposed change (specific enough to implement)
     - Risk assessment (what could break)
     - Test to verify the fix
  6. Group fixes into non-overlapping batches for parallel execution
- Tools: Read, Write

**Agent 9: Fix Verification Design** (tester or test-writer)
- Scope: `PHASE7-FIX-PLAN.md`
- Task:
  1. For each fix in the plan, design a specific verification step
  2. Identify which existing tests cover the fix (test mapping)
  3. Identify which fixes need NEW tests
  4. Write test specifications for any new tests needed
  5. Design a final verification sequence:
     - `python -m pytest tests/ -v --tb=short` -- all tests pass
     - `grep -ri "NCAI\|ATNI" .` -- zero results
     - `python -c "from src.packets.orchestrator import PacketOrchestrator"` -- import chain works
     - Manual spot check: generate one .docx and verify in Word
  6. Append to `PHASE7-FIX-PLAN.md` Section: Verification

---

## Coordination Document Schema

All agents write findings to a shared coordination document at:
`F:\tcr-policy-scanner\.planning\phases\07-computation-docx\REVIEW-COORDINATION.md`

### Document Structure

```markdown
# Phase 7 Review Coordination

## Section A: NCAI/ATNI Removal (Agent 1)
### Files Modified
### Changes Made
### Verification

## Section B: Code Quality (Agent 2)
### Critical Findings
### High Findings
### Medium Findings
### Low Findings

## Section C: python-docx Patterns (Agent 3)
### Documentation Findings
### Pattern Issues
### Recommendations

## Section D: Data Flow (Agent 4)
### Path Traces
### Schema Mismatches Found
### Integration Risks

## Section E: Security (Agent 5)
### Critical Vulnerabilities
### Medium Risk Items
### Informational

## Section F: Test Coverage (Agent 6)
### Coverage Gaps
### Test Quality Issues
### New Tests Needed

## Section G: GitHub + Phase 8 Readiness (Agent 7)
### Best Practices Findings
### Documentation Gaps
### Phase 8 Preparation Status
```

---

## Available Tools and MCPs

### MCP Servers Available
- **Context7** (`mcp__context7__resolve-library-id`, `mcp__context7__query-docs`): Fetch current python-docx docs, pytest patterns, dataclass best practices
- **Ref** (`mcp__Ref__ref_search_documentation`): Search library documentation
- **GitHub** (`mcp__plugin_github_github__*`): Repository operations if needed
- **Playwright** (`mcp__plugin_playwright_playwright__*`): Browser automation for doc research

### Agent Types for Review
| Agent Type | Best For | Wave |
|------------|----------|------|
| `code-simplifier` | NCAI/ATNI removal, code cleanup | 1 |
| `feature-dev:code-reviewer` | Code quality, pattern analysis | 1 |
| `general-purpose` | Context7 research, data flow tracing | 1 |
| `feature-dev:code-explorer` | Dependency tracing, architecture analysis | 1 |
| `dale-gribble` | Security audit, vulnerability hunting | 2 |
| `tester` | Test quality, coverage analysis | 2 |
| `test-writer` | Test specification, verification design | 3 |
| `debugger` | Root cause analysis if issues found | 3 |

### Skills Available
- `/commit-commands:commit` -- For committing fixes
- `/gsd:verify-work` -- For UAT validation
- `/code-review:code-review` -- For PR-style review

---

## Known Issues from Previous Reviews (Context)

These were identified in v1.0 Pass 1 and Pass 2 reviews. Phase 7 agents should verify these patterns weren't reintroduced:

### From Pass 1 (tcr-review-learnings.md)
- Hardcoded FY26 dates (check if new code has similar)
- Test coverage gaps (Phase 7 should be well-tested -- verify)
- CFDA mapping duplication (check economic.py and relevance.py)

### From Pass 2 (tcr-pass2-findings.md)
- CFDA numbers can be wrong (verify 07-01 PROGRAM_BENCHMARK_AVERAGES keys match program_inventory.json IDs)
- Missing `access_type`/`funding_type` fields disable logic paths (check if docx_hotsheet.py handles missing fields)
- `confidence_index: None` -> TypeError (check if Hot Sheet handles None CI values)
- STABLE_BUT_VULNERABLE categorization (verify FRAMING_BY_STATUS has correct framing)

### Windows-Specific Checks
- `open()` must pass `encoding="utf-8"` (not just in new code -- verify ALL open() calls in Phase 7)
- `Path.write_text()` must pass encoding
- `NamedTemporaryFile(delete=False)` required on Windows
- `os.replace()` may fail if target is open in Word
- File paths with special characters in Tribe names

---

## Success Criteria for This Review

1. **Zero NCAI/ATNI references** in entire codebase (verified by grep)
2. **All existing tests still pass** (220+ tests, zero regressions)
3. **Every Critical finding has a fix** (no Critical items left unresolved)
4. **Data flow integrity verified** end-to-end from orchestrator to saved .docx
5. **Security audit complete** with no Critical vulnerabilities
6. **Documentation updated** for Phase 8 readiness
7. **Memory files consistent** with actual project state
8. **PHASE7-FIX-PLAN.md produced** with prioritized, non-conflicting fix batches
9. **Phase 7 requirements** (ECON-01, DOC-01-04) marked complete in REQUIREMENTS.md
10. **STATE.md and ROADMAP.md** reflect Phase 7 completion

---

## Execution Instructions

### For the Orchestrating Agent

1. **Create coordination document** first: Write empty `REVIEW-COORDINATION.md` with section headers
2. **Launch Wave 1** (4 agents in parallel):
   - Agent 1: NCAI/ATNI purge (code-simplifier or general-purpose)
   - Agent 2: Code quality (feature-dev:code-reviewer)
   - Agent 3: python-docx best practices (general-purpose + Context7)
   - Agent 4: Data flow integrity (feature-dev:code-explorer)
3. **Wait for Wave 1 completion**, read all Section A-D findings
4. **Launch Wave 2** (3 agents in parallel):
   - Agent 5: Security audit (dale-gribble)
   - Agent 6: Test coverage (tester)
   - Agent 7: GitHub + Phase 8 readiness (general-purpose + WebSearch)
5. **Wait for Wave 2 completion**, read all Section E-G findings
6. **Launch Wave 3** (2 agents in parallel):
   - Agent 8: Conflict detection + fix plan (general-purpose)
   - Agent 9: Verification design (test-writer)
7. **Review PHASE7-FIX-PLAN.md** before any fixes are applied
8. **Execute fixes** in prioritized batches (Critical first, then High, etc.)
9. **Run full test suite** after all fixes: `python -m pytest tests/ -v --tb=short`
10. **Verify NCAI/ATNI removal**: `grep -ri "NCAI\|ATNI" . --include="*.py" --include="*.md" --include="*.json"`
11. **Update documentation** (STATE.md, ROADMAP.md, REQUIREMENTS.md, MEMORY.md)
12. **Commit** with descriptive message

### Critical Rules for All Agents

1. **DO NOT modify upstream Phase 5-6 modules** (context.py, registry.py, congress.py, ecoregion.py, awards.py, hazards.py)
2. **DO NOT modify test_packets.py or test_decision_engine.py** (v1.0 test files)
3. **Write findings to REVIEW-COORDINATION.md** before making any changes
4. **Check the coordination doc** before editing any file to prevent merge conflicts
5. **Use `encoding="utf-8"`** on every `open()` call in any fix
6. **Use `datetime.now(timezone.utc)`** not `datetime.utcnow()`
7. **Run pytest after every fix batch** to catch regressions immediately
8. **One fix must not introduce another problem** -- the coordination doc is the guard rail

---

*Generated: 2026-02-10*
*For: TCR Policy Scanner v1.1 Phase 7 Critical Systemic Review*
*Project: F:\tcr-policy-scanner*
