# Documentation Review Synthesis

*Produced by: The Conductor*
*Date: 2026-02-13*
*Agents: Maynard-James (consistency), Ranger (organization), Banjo (ground-truth), Tahoma (narrative)*

## Agreed Facts (multiple agents found the same issue)

These findings were identified by 2+ agents and are confirmed by ground truth:

| Issue | Agents | Ground Truth | Fix |
|-------|--------|-------------|-----|
| MILESTONES.md missing v1.3 entry | MJ-006, RNG-004, TAH-002 | v1.3 completed 2026-02-14 | Add v1.3 entry (Tahoma drafted) |
| PROJECT.md "What This Is" stale (v1.2 state) | MJ-004, TAH-001, TAH-009 | System is v1.3 | Rewrite (Tahoma drafted) |
| PROJECT.md test count: 743 (v1.2) | MJ-009, RNG-009, TAH-009 | Banjo: 964 tests | Update to 964 |
| PROJECT.md source file count: 95 | MJ-007, RNG-025 | Banjo: 54 src, 102 active | Update with qualifier |
| PROJECT.md Out of Scope lists delivered items | MJ-005, RNG-024, TAH-010 | INTEL-01, INTEL-02 shipped | Remove 2 items |
| PROJECT.md no v1.3 validated requirements | RNG-005, TAH-003 | 39 requirements complete | Add v1.3 entries |
| PROJECT.md "Current Milestone" still active | MJ-004, RNG-008, TAH-009 | v1.3 COMPLETE | Past tense |
| PROJECT.md timestamp stale (2026-02-12) | MJ-012, TAH-019 | Completed 2026-02-14 | Update |
| ROADMAP.md v1.3 header says "in progress" | MJ-003, RNG-010 | v1.3 COMPLETE | Mark complete |
| CLAUDE.md test count: 287 (v1.1) | MJ-017, TAH-011 | Banjo: 964 tests | Update to 964 |
| REQUIREMENTS.md WEB stack: React/Vite | MJ-025, MJ-037, TAH-013 | Banjo: vanilla HTML/JS/CSS | Fix stack reference |
| milestones/ missing v1.3 archives | RNG-001, RNG-002, RNG-003, RNG-032 | Archives not created | Copy during closeout |
| Plan count: 70 claimed vs 67 arithmetic | MJ-001, MJ-002 | Banjo: 9+17+20+20=66, or 9+17+20+21=67 | Reconcile |
| DOCX count: 992 claimed vs 996 filesystem | MJ-010, RNG-027 | Banjo: 996 total, 992 matched (4 extras) | 992 is correct |
| V1.3-OPERATIONS-PLAN.md no retrospective | MJ-015, RNG-016, TAH-012 | Plan was 3 phases, execution was 4 | Add retrospective |
| congressional_intel.json vs congressional_cache.json | MJ-028, RNG-026 | Banjo: cache.json exists, intel.json does not | Standardize references |

## Conflicts (agents disagree)

### DOCX Count: 992 vs 996
- **Maynard-James:** 992 claimed in docs vs 996 on filesystem = mismatch (MJ-010)
- **Banjo:** 992 is correct for Doc A+B+C+D. The 4 extras are top-level files (epa_001.docx, epa_100000168.docx, epa_100000171.docx, STRATEGIC-OVERVIEW.docx) -- test/sample artifacts not part of the production corpus.
- **Resolution:** Keep 992 as the documented count. Add a note that 4 additional sample files exist. No conflict.

### Source File Count: 95 vs 98 vs 102
- **Maynard-James:** None of the documented counts match (MJ-007)
- **Banjo:** 54 src + 33 tests + 14 scripts + 1 root = 102 active. "98" may be a stale snapshot before Phase 18 additions.
- **Resolution:** ~~Use "98 Python source files" from STATE.md.~~ **POST-REVIEW FIX:** Corrected to 102 Python files (54 src + 33 tests + 14 scripts + 1 root) across all authoritative docs.

### Total Plan Count: 70 vs 67
- **Maynard-James:** 9+17+20+21 = 67, not 70 (MJ-001). Also, v1.3 claims 21 plans but ROADMAP lists 20 (MJ-002).
- **Banjo:** Confirmed arithmetic: 9+17+20+21 = 67. If v1.3 is 20 (per ROADMAP plan listing), total = 66.
- **Resolution:** ~~Defer to Patrick.~~ **POST-REVIEW FIX:** Corrected to 66 total plans (9+17+20+20). The "+1 integration" was the audit's integration check step, not an actual PLAN.md file. v1.3 = 20 plans.

### LOC: ~37,900 vs 38,340
- **Maynard-James:** Frozen at v1.2 snapshot (MJ-008)
- **Banjo:** src+tests = 38,340. The tilde (~) makes it approximate. "Acceptable" per Banjo.
- **Resolution:** Update to "~38,300 LOC (src + tests)" for accuracy. Not a P1.

## Verified Ground Truth (Banjo's numbers supersede all document claims)

| Metric | Documents Claim | Banjo Verified | Action |
|--------|----------------|----------------|--------|
| Tests | 964 (STATE.md), 743 (PROJECT.md), 287 (CLAUDE.md) | **964** | Fix PROJECT.md and CLAUDE.md |
| Source files (src/) | 95 (PROJECT.md), 98 (STATE.md) | **54** (src only), **102** (all active) | Clarify scope, update |
| LOC (src+tests) | ~37,900 | **38,340** | Update to ~38,300 |
| DOCX files | 992 | **992** matched + 4 samples = 996 total | Keep 992, note extras |
| Git HEAD | e8a4aba | **e8a4aba** | Confirmed |
| v1.2 end commit | 8f96850 | **8f96850** | Confirmed |
| paths.py constants | 25 | **35** | Update PROJECT.md |
| paths.py consumers | 47 | **35** | Update PROJECT.md |
| Congressional data file | congressional_intel.json | **congressional_cache.json** (3.4M) | Fix references |
| All capabilities | Per REQUIREMENTS.md | **All verified in code** | No action |
| CYCLOPS-016 | P3 accepted | **URIError on malformed hash, console-only** | Document |
| DALE-019 | P3 accepted | **daily-scan.yml not SHA-pinned** | Document |

## Priority-Ordered Action Items

### P1: Must fix before milestone closure

1. **Add v1.3 entry to MILESTONES.md** (MJ-006, RNG-004, TAH-002) -- Tahoma drafted entry
2. **Update PROJECT.md "What This Is" paragraph** (TAH-001) -- Tahoma drafted replacement
3. **Update PROJECT.md Validated Requirements** (RNG-005, TAH-003) -- add v1.3 capabilities
4. **Update PROJECT.md Current State** to v1.3 COMPLETE (MJ-004, TAH-009)
5. **Remove delivered items from PROJECT.md Out of Scope** (MJ-005, TAH-010)
6. **Update PROJECT.md test count 743 -> 964** (MJ-009)
7. **Update PROJECT.md timestamp** (MJ-012, TAH-019)
8. **Update ROADMAP.md v1.3 header** from "in progress" to "complete" (MJ-003, RNG-010)
9. **Update CLAUDE.md test count 287 -> 964** (MJ-017, TAH-011)
10. **Fix REQUIREMENTS.md WEB stack reference** (MJ-037, TAH-013)
11. **Document archive readiness** for milestones/ (RNG-001, RNG-002, RNG-003)

### P2: Should fix for documentation quality

12. **Rewrite PROJECT.md "Target Features" to past tense** (MJ-013)
13. **Update PROJECT.md tech debt section** from v1.2 to v1.3 state (MJ-018)
14. **Add v1.3 Key Decisions to PROJECT.md** (RNG-007, TAH-020)
15. **Update PROJECT.md paths.py stats** 25->35 constants, 47->35 consumers (Banjo)
16. **Update PROJECT.md source file count** with qualifier (MJ-007)
17. **Update CLAUDE.md structure tree and What section** (TAH-011)
18. **Add retrospective to V1.3-OPERATIONS-PLAN.md** (TAH-012) -- Tahoma drafted
19. **Add deprecation header to ROADMAP-SUPPLEMENTAL-UPDATES.md** (MJ-016, RNG-011)
20. **Standardize Phase 15 naming** (MJ-020, MJ-029)
21. **Update Document 1/2 naming to Doc A/B/C/D** in PROJECT.md legacy entries (MJ-021)
22. **Add git range to v1.3-MILESTONE-AUDIT.md** (MJ-022)
23. **Verify Phase 15-17 completion dates** (MJ-019)

### P3: Nice to have

24. Reorder MILESTONES.md to consistent chronological order (MJ-024, RNG-028)
25. Move PHASE-14 files into phases/14-integration/ (RNG-014)
26. Move top-level REVIEW-COORDINATION.md to phases/16/ (RNG-015)
27. Mark consumed prompts (TRIGGER-PROMPT-V1.3.md, v1.1-session-prompt.md) (RNG-012, RNG-013)
28. Add air gap definition to PROJECT.md (TAH-014)
29. Add TSDF framework definition (TAH-017)
30. Add pipeline relationship explanation (TAH-015)
31. Create data dictionary for future milestone (RNG-021)
32. Create deployment runbook for future milestone (RNG-022)

## Deferred (Not Fixing Now)

- **Archive file corrections** (MJ-014): v1.2-REQUIREMENTS.md says "11 program queries" vs actual 14. Archive is historical record -- acceptable.
- **WEB requirement ID collision** across milestones (MJ-035): Low priority, noted for future ID scheme.
- **Bug hunt SYNTHESIS.md stale counts** (Banjo): Audit artifact, not living document.
- **MILESTONES.md v1.2 paths.py stats** (25 constants, 47 files): Point-in-time snapshot, acceptable.

---
*Synthesis complete. 32 action items identified (11 P1, 12 P2, 9 P3). Proceeding to document updates.*
