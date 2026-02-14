# Phase 18: Production Hardening - Research

**Researched:** 2026-02-13
**Domain:** Adversarial code review, security audit, experiential UX testing, code hygiene, go/no-go launch decision
**Confidence:** HIGH

## Summary

Phase 18 is a 4-agent adversarial review of the complete TCR Policy Scanner system (96 Python source files, ~37,900 LOC, 964 tests, 992 DOCX documents, vanilla HTML/JS/CSS website with Fuse.js search, and 3 GitHub Actions deployment workflows). The goal is a go/no-go launch decision confirming zero P0 critical issues for a 100-200 concurrent Tribal user launch over a 48-hour window.

This phase reuses the proven Phase 16 pattern: parallel agent audit (Wave 1) producing JSON findings + markdown summary, followed by a fix-verify cycle (Wave 2) that resolves P0/P1 issues, then a synthesis report (Wave 3) with a human go/no-go decision. The key differences from Phase 16 are: (1) scope expands from DOCX generation code to the *entire system* including website, deployment, scrapers, and pipeline, (2) agent methods diversify from read-only code audit to include experiential testing (Mr. Magoo) and security/sovereignty audit (Dale Gribble), and (3) the output is a launch decision, not just a quality certificate.

There are 3 known P1 issues inherited from Phase 17 (dark mode contrast failures in CSS) that must be fixed in this phase. The Marie Kondo agent provides an additional dimension not present in Phase 16 -- code hygiene findings that may be acted upon during the fix wave if low-risk.

**Primary recommendation:** Structure as 3 plans in 3 waves: Wave 1 (audit + pre-fix known P1s), Wave 2 (fix P0/P1 findings + apply low-risk Marie Kondo suggestions + re-verify), Wave 3 (synthesis report + human go/no-go checkpoint).

## Standard Stack

### Core

No new libraries are needed. Phase 18 is purely audit, fix, and verify. The existing stack is the subject of review:

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Python pipeline | Python | 3.12 | All scrapers, document generation, data population |
| DOCX generation | python-docx | latest | DocxEngine, StyleManager, HotSheetRenderer |
| Fuzzy matching | rapidfuzz | latest | Tribal alias matching for USASpending |
| Website | vanilla HTML/JS/CSS | ES5 compatible | No framework, no build step |
| Search | Fuse.js | 7.1.0 | Self-hosted UMD bundle, fuzzy search for 592 Tribes |
| CI/CD | GitHub Actions | v4/v5 actions | 3 workflows: daily-scan, generate-packets, deploy-website |
| Hosting | GitHub Pages | CDN | Static file serving for DOCX downloads |
| Testing | pytest | latest | 964 tests across 31 test files |
| Linting | ruff | latest | Zero violations enforced |

### Supporting (Audit Tooling)

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `python -m pytest tests/ -v` | Run full test suite | After every fix to confirm zero regressions |
| `ruff check .` | Lint check | After Marie Kondo cleanup to confirm no violations |
| `python -m http.server 8080 -d docs/web` | Local website preview | Mr. Magoo experiential testing |
| `grep -rn` | Air gap compliance | XCUT-01 verification during Dale Gribble audit |

### Alternatives Considered

None. Phase 18 does not introduce new technology -- it validates the existing stack.

## Architecture Patterns

### Proven Pattern: Phase 16 Two-Wave Audit-Fix Structure

The Phase 16 pattern worked in 2 plans and should be adapted for Phase 18's broader scope:

**Phase 16 (reference):**
- Plan 16-01 (Wave 1): 5 parallel READ-ONLY audit agents -> 5 JSON findings files
- Plan 16-02 (Wave 2): Fix P0/P1 -> add tests -> re-verify -> SYNTHESIS.md quality certificate
- Result: 40 findings (0 P0, 6 P1, 16 P2, 18 P3), all 6 P1s fixed, SYNTHESIS.md PASS

**Phase 18 adaptation (3 plans):**

```
Plan 18-01 (Wave 1: Pre-Fix + Audit)
├── Fix 3 known P1 dark mode contrast issues from Phase 17
├── Run 4 parallel agents (Cyclops, Dale Gribble, Mr. Magoo, Marie Kondo)
├── Each agent produces: outputs/bug_hunt/{agent}_findings.json + {agent}_summary.md
└── Scope: Full system (website + Python pipeline + CI/CD + deployment)

Plan 18-02 (Wave 2: Fix + Verify)
├── Triage all findings across 4 agents
├── Fix all P0 and P1 issues in priority order
├── Apply low-risk Marie Kondo suggestions (dead code, unused imports)
├── Run full test suite after each fix batch
├── Re-run affected agent checklists to verify fixes
└── Loop until zero P0/P1 remaining

Plan 18-03 (Wave 3: Synthesis + Launch Decision)
├── Produce outputs/bug_hunt/SYNTHESIS.md
├── Aggregate all findings into priority matrix
├── Identify cross-agent themes
├── Compute combined trust assessment
├── Present go/no-go recommendation to human
└── Human makes final launch decision
```

### Agent File Domains (No Overlap)

Each agent has distinct territories to avoid conflicting findings:

| Agent | Source Files | Output Files |
|-------|------------|--------------|
| Cyclops | `docs/web/js/*.js`, `src/packets/orchestrator.py`, `src/packets/docx_engine.py`, `src/main.py`, data flow tracing | `outputs/bug_hunt/cyclops_findings.json`, `cyclops_summary.md` |
| Dale Gribble | `docs/web/index.html`, `docs/web/css/style.css`, `.github/workflows/*.yml`, `src/scrapers/*.py`, CSP/tracking/sovereignty | `outputs/bug_hunt/dale-gribble_findings.json`, `dale-gribble_summary.md` |
| Mr. Magoo | No source code. Tests deployed website experience via local server + live site | `outputs/bug_hunt/mr-magoo_findings.json`, `mr-magoo_summary.md` |
| Marie Kondo | All `src/**/*.py` (96 files), `scripts/*.py` (17 files), `tests/test_*.py` (31 files) | `outputs/bug_hunt/marie-kondo_findings.json`, `marie-kondo_summary.md` |

### Finding Severity Classification

Use the Phase 16 precedent adapted for production hardening:

| Severity | Criteria | Action |
|----------|----------|--------|
| P0 Critical | Data sovereignty violation, tracking/analytics present, complete feature failure, data leak, security vulnerability | **Must fix before launch. Blocks go decision.** |
| P1 Major | WCAG AA contrast failure, broken download flow for subset of users, silent data loss, missing error handling on critical path | **Must fix or document workaround before launch.** |
| P2 Moderate | Cosmetic issues affecting usability, borderline contrast, edge case failures, minor code quality | Fix post-launch. Document in known issues. |
| P3 Minor | Code style, naming, dead code, optimization opportunities, enhancement ideas | Backlog for future cleanup. |

### Output JSON Schema

Reuse the per-agent JSON format. Each agent defines their own schema in their `.md` file:

- **Cyclops**: `id`, `severity`, `category`, `file`, `line`, `code_snippet`, `the_flaw`, `proof`, `blast_radius`, `fix`
- **Dale Gribble**: `id`, `severity`, `category`, `threat`, `evidence`, `attack_vector`, `sovereignty_impact`, `fix`, `paranoia_level`
- **Mr. Magoo**: `id`, `severity`, `category`, `what_happened`, `what_i_expected`, `how_i_got_here`, `how_it_felt`, `suggestion`
- **Marie Kondo**: `inventory` (dependencies, components, styles, utilities, configuration), `joy_score`, `joy_score_potential`

### Synthesis Report Structure

```
outputs/bug_hunt/SYNTHESIS.md
├── Overall Status: PASS / CONDITIONAL PASS / FAIL
├── Severity Summary (table: P0/P1/P2/P3 counts, found/fixed/remaining)
├── Per-Agent Summary (findings count by severity per agent)
├── Fixes Applied (for each P0/P1: file, issue, fix, verification, commit)
├── Cross-Agent Themes (patterns flagged by multiple agents)
├── Known Issues (remaining P2/P3 with documentation)
├── Trust Assessment (Mr. Magoo trust_score, Dale Gribble sovereignty_assessment)
├── Concurrency Assessment (GitHub Pages CDN, download reliability for 200 users)
├── Go/No-Go Recommendation (evidence-based, presented to human)
└── Quality Certificate (zero P0/P1, test count, timestamp)
```

### Anti-Patterns to Avoid

- **Agent cross-talk:** Do NOT let agents see each other's findings during Wave 1. Independence prevents groupthink.
- **Fix cascades:** Do NOT apply large refactors from Marie Kondo findings that touch >3 files. High regression risk.
- **Scope creep:** Do NOT add new features during production hardening. Fix forward only.
- **Silent skips:** Do NOT mark a finding as "won't fix" without documenting why. Every P0/P1 needs explicit resolution.
- **Test erosion:** Do NOT reduce test count. Any fix that removes tests must add equivalent or better coverage.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dark mode contrast checking | Manual color math | Use the Phase 16 WCAG contrast calculation pattern | Contrast ratio = (L1 + 0.05) / (L2 + 0.05), already validated in design-aficionado findings |
| Website experiential testing | Selenium/Playwright automation | Mr. Magoo manual-style narrated walkthrough | The persona IS the test methodology -- cognitive friction testing can't be automated |
| Sovereignty compliance check | New checklist | Dale Gribble's 18-item UNDRIP/OCAP/CARE checklist | Already defined and battle-tested conceptually |
| Code hygiene detection | New analysis tool | Marie Kondo's 3-pass inventory method | Systematic: dependencies -> code -> config, already defined |
| Finding JSON format | New schema | Reuse each agent's defined schema from their `.md` files | Consistency with Phase 16 pattern |

**Key insight:** The agent definitions (`.planning/cyclops.md`, etc.) ARE the specifications. They define checklists, output formats, and methods. The planner should reference them directly, not recreate.

## Common Pitfalls

### Pitfall 1: Known P1 Issues Not Fixed Before Audit

**What goes wrong:** Agents re-discover the 3 known P1 dark mode contrast issues from Phase 17, wasting audit capacity on already-known problems.
**Why it happens:** Phase 17 shipped with CONDITIONAL PASS -- 3 P1 issues deferred to Phase 18.
**How to avoid:** Fix the 3 P1 dark mode contrast issues FIRST (before running agents). They are CSS-only fixes in `docs/web/css/style.css`:
1. P1-01: `.btn-download` dark mode contrast (add `background: #1a5276` override)
2. P1-02: Badge dark mode contrast (add darker badge backgrounds)
3. P1-03: Selected listbox option dark mode contrast (add `background: #1a5276`)
**Warning signs:** Any agent finding that references `prefers-color-scheme: dark` contrast.

### Pitfall 2: Mr. Magoo Reading Source Code

**What goes wrong:** The experiential testing agent references line numbers, function names, or internal implementation details.
**Why it happens:** Natural tendency to use all available information.
**How to avoid:** Mr. Magoo's instructions explicitly say "DO NOT read source code." Only provide the local preview URL and the live deployed site URL. Findings should be in plain English from a user's perspective.
**Warning signs:** Any Mr. Magoo finding that references a file path or function name.

### Pitfall 3: Marie Kondo Suggesting Risky Refactors

**What goes wrong:** Code hygiene suggestions that touch core pipeline logic (orchestrator, DocxEngine, scrapers) introduce regressions.
**Why it happens:** The line between "cleanup" and "refactor" is blurry.
**How to avoid:** Per CONTEXT.md: "Act on low-risk findings (dead code removal, import cleanup, simple hygiene). Skip anything that could introduce regressions."
- **Low-risk (act on):** Remove unused imports, delete dead functions confirmed unused by grep, remove TODO comments for resolved issues
- **High-risk (skip):** Restructure module boundaries, consolidate classes, change function signatures, modify data flow
**Warning signs:** Any Marie Kondo suggestion that changes an interface or touches >3 files.

### Pitfall 4: GitHub Pages Concurrency Misunderstanding

**What goes wrong:** Over-engineering load testing for a static file CDN.
**Why it happens:** "100-200 concurrent users" sounds like it needs stress testing.
**How to avoid:** GitHub Pages CDN serves static files. The concurrency concern is about *download reliability*, not server load. Per CONTEXT.md: "Focus on download reliability -- can 200 people search and download DOCX files without errors?" The answer is almost certainly yes for GitHub Pages, but the agents should verify:
- Download links resolve correctly (no 404s)
- Large DOCX files (some may be 1-2MB) complete download
- "Download Both" button doesn't get blocked by popup blockers
- Manifest freshness doesn't cause stale cache issues
**Warning signs:** Any plan to run load tests against GitHub Pages.

### Pitfall 5: ATNI/Air Gap References in Source Comments

**What goes wrong:** Dale Gribble or XCUT compliance finds "ATNI" references that are in code comments, git URLs, or planning docs (not user-facing content).
**Why it happens:** XCUT-01 says zero references to "ATNI" in "rendered DOCX content or website-facing text." The scope is user-facing, not internal.
**How to avoid:** Distinguish between:
- **P0 violation:** `atni` in rendered DOCX text, website HTML body, or metadata visible to users
- **P3 cosmetic:** `atni` in HTML comments (already known: P3-02 from Phase 17 in `index.html` line 67), git remote URLs, planning docs, code comments
**Warning signs:** Long lists of ATNI grep hits that are all in non-user-facing locations.

### Pitfall 6: Website Stack Mismatch in Agent Checklists

**What goes wrong:** Agent checklists reference React components, TypeScript, npm packages, or Vite -- but the website is vanilla HTML/JS/CSS with no build step.
**Why it happens:** The agent definitions (cyclops.md, marie-kondo.md) were written assuming a React+Vite stack (as originally planned in Phase 17 requirements), but Phase 17 actually shipped as enhanced vanilla HTML/JS/CSS with self-hosted Fuse.js.
**How to avoid:** When executing checklists, skip items that don't apply to the actual stack:
- **Cyclops:** Skip "React error boundaries" (item 10) -- no React. Check vanilla JS error handling instead.
- **Marie Kondo:** Skip npm dependency inventory, component inventory, TypeScript checks, shadcn directory audit, tree-shaking analysis. Focus on Python pipeline dependency hygiene + website JS/CSS unused code.
- **Dale Gribble:** All items apply as-is (security concerns are stack-agnostic).
- **Mr. Magoo:** All items apply as-is (experiential testing is stack-agnostic).
**Warning signs:** Agent findings mentioning React, TypeScript, npm, Vite, or shadcn.

## Code Examples

### Pre-Fix: Dark Mode Contrast (CSS-only, before Wave 1)

Source: Phase 17 SYNTHESIS.md P1-01, P1-02, P1-03

```css
/* Add to docs/web/css/style.css inside @media (prefers-color-scheme: dark) block */

@media (prefers-color-scheme: dark) {
  /* P1-01: Button contrast fix */
  .btn-download { background: #1a5276; }
  .btn-download:hover { background: #1f6d9b; }
  .btn-internal { background: #1e5631; }
  .btn-internal:hover { background: #2d7a47; }
  .btn-both { background: #5b2c6f; }
  .btn-both:hover { background: #76448a; }

  /* P1-02: Badge contrast fix */
  .badge-fresh { background: #1e7a3d; }
  .badge-aging { background: #b45309; }
  .badge-stale { background: #a93226; }
  .badge-unknown { background: #5a6268; }

  /* P1-03: Selected option contrast fix */
  .listbox li[role="option"][aria-selected="true"] {
    background: #1a5276;
    color: #fff;
  }
}
```

### Finding JSON Example (Cyclops)

```json
{
  "agent": "Cyclops",
  "timestamp": "2026-02-13T...",
  "findings": [
    {
      "id": "CYCLOPS-001",
      "severity": "P1",
      "category": "error-handling",
      "file": "docs/web/js/app.js",
      "line": 52,
      "code_snippet": "fetch(TRIBES_URL).then(function(response) {",
      "the_flaw": "No timeout on fetch -- if GitHub Pages is slow, user waits indefinitely",
      "proof": "Throttle network to GPRS in DevTools, loading message persists with no timeout",
      "blast_radius": "All users on slow connections see infinite loading state",
      "fix": "Add AbortController with 10s timeout"
    }
  ],
  "traces_completed": ["user search -> Fuse.js -> card render -> download click"],
  "structural_assessment": "..."
}
```

### Synthesis Report Example (Go/No-Go Section)

```markdown
## Go/No-Go Recommendation

**Recommendation: GO** (with caveats)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Zero P0 critical issues | PASS | 0 P0 findings across all 4 agents |
| All P1 issues resolved | PASS | N P1 findings fixed, M verified |
| Mr. Magoo trust_score >= 7 | PASS | trust_score: 8/10 |
| Dale Gribble sovereignty PASS | PASS | 18/18 checklist items clear |
| Cyclops structural integrity | PASS | 15/15 checklist items clear |
| 964+ tests passing | PASS | 970 tests, 0 failures |
| GitHub Pages download reliability | PASS | All 992 documents downloadable |

**Caveats:**
- N P2 items remain (documented in Known Issues)
- M Marie Kondo suggestions deferred to future milestone

**Decision authority: Human (user) makes the final call.**
```

## State of the Art

| Old Approach (Phase 16) | Current Approach (Phase 18) | Why Changed |
|------------------------|-----------------------------|-------------|
| 5 code-only audit agents | 4 diversified agents (code + security + UX + hygiene) | Broader adversarial coverage |
| DOCX generation scope only | Full system scope (website + pipeline + CI/CD) | Production launch requires system-wide confidence |
| Quality certificate output | Go/no-go launch decision output | Decision gate, not just quality gate |
| 2-wave (audit, fix) | 3-wave (pre-fix + audit, fix + verify, synthesis + decision) | Pre-fix known P1s to avoid re-discovery |

**Key insight from Phase 16:** The 2-plan structure (audit wave, fix wave) worked cleanly. Phase 18 adds a third wave (synthesis + launch decision) but the core audit-fix-verify loop is identical.

## Inherited Issues (Must Address in Phase 18)

From Phase 17 SYNTHESIS.md (CONDITIONAL PASS):

| ID | Severity | File | Description | Fix |
|----|----------|------|-------------|-----|
| P1-01 | P1 | `docs/web/css/style.css` | `.btn-download` dark mode contrast failure (2.46:1) | Add dark mode background overrides |
| P1-02 | P1 | `docs/web/css/style.css` | Badge dark mode contrast failures (2.19-3.82:1) | Add darker badge backgrounds in dark mode |
| P1-03 | P1 | `docs/web/css/style.css` | Selected listbox option dark mode contrast (1.94:1) | Add dark mode selected state override |
| P2-01 | P2 | `docs/web/css/style.css` | Muted text borderline contrast (4.45:1 vs 4.5:1 threshold) | Darken `--tcr-muted` to `#636b73` |
| P2-02 | P2 | `docs/web/css/style.css` | Missing `.option-alias` CSS class | Add CSS for alias hint styling |
| P2-04 | P2 | `docs/web/js/app.js` | `scrollIntoView` ignores reduced motion | Check `prefers-reduced-motion` in JS |
| P2-05 | P2 | `docs/web/css/style.css` | Light mode selected option borderline contrast (4.30:1) | Use darker accent color for selected state |
| P3-02 | P3 | `docs/web/index.html` | `atniclimate.github.io` in HTML comment | Replace with placeholder or remove comment |
| P3-03 | P3 | `docs/web/js/app.js` | No `rel="noopener"` on download links | Add `a.rel = "noopener"` |
| P3-06 | P3 | `docs/web/index.html` | No `<noscript>` fallback | Add `<noscript>` message |

These should all be fixed in the pre-fix step of Wave 1 (before running agents), so agents audit a clean baseline.

## Agent-Specific Research

### Cyclops: Deep Code Inspection

**Scope:** All JavaScript (3 files: `app.js`, `combobox.js`, `fuse.min.js`) + key Python modules (orchestrator, docx_engine, main)

**Checklist analysis (15 items from cyclops.md):**

1. GitHub Pages down fallback -- `app.js` has `fetch().catch()` showing error message (line 102-107). No retry logic.
2. Special characters in Tribe names -- `sanitizeFilename()` strips non-alphanumeric except space/underscore/hyphen (line 381). Test with "Confederated Tribes of the Chehalis Reservation" and apostrophe names like "Coeur d'Alene".
3. Manifest staleness -- `manifest.json` generated at deploy time with `deployed_at` timestamp. Client doesn't fetch manifest. No staleness risk for downloads (direct file links).
4. Search race conditions -- `combobox.js` has no debounce but caps results at 15. Fuse.js search is synchronous, so no race possible. `_lastResults` updated atomically.
5. Download cleanup on abort -- `downloadBoth()` creates and removes temporary anchors. No fetch() involved, so no abort needed.
6. XSS in Tribe name display -- `textContent` used throughout (never `innerHTML`). Safe.
7. 592 results boundary -- Fuse.js caps at 15 results. State filter renders all tribes in a state (max ~80 for Alaska). No unbounded list.
8. Ecoregion mapping -- Built by `build_web_index.py` from config. Injective if config is correct.
9. Caching -- No service worker. Browser cache + GitHub Pages CDN. Standard HTTP caching.
10. React error boundaries -- **N/A** (no React). Vanilla JS has no error boundaries; global try/catch in init.
11. Missing packet -- `showCard()` shows "Documents are being prepared" message when no documents exist.
12. Fetch timeout -- **No timeout on fetch()**. This is a real finding candidate.
13. Case/diacritic sensitivity -- Fuse.js `threshold: 0.4` with `ignoreLocation: true`. No explicit diacritic normalization. This is a finding candidate.
14. Content-Disposition -- GitHub Pages serves `.docx` files. `download` attribute on `<a>` element sets filename. Content-Disposition is server-side (GitHub Pages default).
15. Memory leaks -- `renderOptions()` clears all children before re-rendering. No unbounded growth.

**Key areas to trace:** The complete data path from user input through Fuse.js search through card render through download click through DOCX delivery.

### Dale Gribble: Security & Sovereignty

**Scope:** All external network requests, CSP headers, tracking scripts, font loading, cookies, referrer policy, source maps, TSDF compliance

**Checklist analysis (18 items from dale-gribble.md):**

1. HTTPS + CSP -- GitHub Pages serves HTTPS. No custom CSP headers set (no `<meta>` CSP in index.html). **Finding candidate: No CSP header.**
2. Manifest enumeration -- `tribes.json` is publicly accessible and lists all 592 Tribes with their file paths. This is by design (T0 data), but should be documented.
3. Referrer leakage in SquareSpace embed -- `Referrer-Policy` not set. Default is `strict-origin-when-cross-origin`. Finding candidate.
4. Analytics/tracking -- No analytics scripts. No Google Fonts. No cookies. System fonts only. Fuse.js self-hosted. Should PASS.
5. TSDF T0/T1 enforcement -- All data is T0 (public federal data). No T1 (Tribal-specific) data collected.
6. Modified URL downloading other Tribe's packets -- File paths in `tribes.json` are predictable (based on Tribe name). But all documents are T0 (public) -- this is intentional public access.
7. CDN dependencies -- Only `fuse.min.js` (self-hosted). No external CDN. Should PASS.
8. JS disabled degradation -- Loading message persists. No `<noscript>` fallback. Finding candidate (P3).
9. GitHub API rate limits -- No GitHub API calls. Static file serving only. N/A.
10. PII in filenames/URLs -- Tribe names in file paths are federal register names (public data). No PII.
11. MITM GitHub Pages -> SquareSpace -- HTTPS in both directions. iframe sandbox restricts capabilities.
12. Google Fonts -- No Google Fonts. System fonts only. PASS.
13. Cookies -- No cookies set by the website. GitHub Pages may set technical cookies. Finding candidate.
14. IP exposure to GitHub -- Standard HTTPS request. GitHub sees requesting IP. This is unavoidable for any CDN. Document as "tinfoil-hat" paranoia level.
15. Malicious SquareSpace plugin -- `sandbox` attribute restricts iframe. Plugin can't access iframe content with `allow-same-origin`.
16. Subresource Integrity -- No external resources, so SRI not needed. All files self-hosted.
17. Hardcoded API keys -- No API keys in website code. Secrets are in GitHub Actions only.
18. Source maps -- No build step, no source maps. PASS.

**Sovereignty-specific:**
- UNDRIP: Tribal data self-determination respected (T0 only)
- OCAP: Ownership (federal data, not Tribal), Control (ATNI controls distribution), Access (public), Possession (GitHub hosted)
- CARE: Collective Benefit (yes), Authority to Control (yes via repository), Responsibility (yes), Ethics (yes)

### Mr. Magoo: Experiential Testing

**Scope:** Website experience as a non-technical Tribal staff member

**Testing method:** Navigate `http://localhost:8080` (local) and the deployed GitHub Pages site. No source code. No DevTools.

**Checklist walkthrough (12 items from mr-magoo.md):**
1. Find Tribe without exact spelling -- Test "navjo" for Navajo, "cheroke" for Cherokee, "colville" for Colville
2. Download button clarity -- Buttons say "Internal Strategy" and "Congressional Overview". Is this clear to a Tribal staff member?
3. Wrong download retry -- Can user easily navigate back and download a different document?
4. Speed/jank -- How fast does search respond? Any visible delay?
5. Confusion points -- Is the purpose of the page obvious within 5 seconds?
6. Error messages -- What happens with gibberish input? Empty results?
7. TSDF disclaimer -- Not currently visible on the page. Finding candidate.
8. Mobile experience -- Test at 375px viewport width
9. Shareable link -- No deep linking to a specific Tribe. Finding candidate.
10. Broken feel -- Any visual glitches or layout issues?
11. Visual design -- Professional? Respectful?
12. Council-ready -- Would a Tribal Leader show this to their council?

### Marie Kondo: Code Hygiene

**Scope:** 96 Python source files, 17 scripts, 31 test files, 6 web files

**Three-pass inventory adapted for actual stack:**

**Pass 1: Python Dependency Inventory**
- Check `requirements.txt` against actual imports across 96 source files
- Identify any packages installed but never imported
- Flag large dependencies that could be replaced (unlikely given mature codebase)

**Pass 2: Python Code Inventory**
- Unused functions: Functions defined but never called (grep for def name, check callers)
- Unused imports: Imports that are never referenced in the file
- Dead code: Commented-out blocks, unreachable paths after early returns
- Module size: Flag modules >500 LOC for documentation (orchestrator at 1335, docx_sections at 1443)
- Duplicate patterns: Similar utility functions in different modules
- TODO/FIXME: Resolved issues still marked as TODO

**Pass 3: Configuration Inventory**
- `config/scanner_config.json`: Unused config keys
- `.github/workflows/*.yml`: Duplicate steps between workflows
- `pyproject.toml`: Ruff config completeness
- Web files: Unused CSS classes, unused JS functions

**Key constraint from CONTEXT.md:** "Act on low-risk findings (dead code removal, import cleanup, simple hygiene). Skip anything that could introduce regressions."

## Open Questions

1. **Live deployed site availability**
   - What we know: GitHub Pages deployment is configured via `deploy-website.yml` and `generate-packets.yml`
   - What's unclear: Whether the live site at `atniclimate.github.io/TCR-policy-scanner/` is currently deployed with the latest Phase 17 code. Mr. Magoo needs to test both local AND live.
   - Recommendation: Verify live site is current before Mr. Magoo tests it. If not deployed, use manual `workflow_dispatch` to trigger deployment, or scope Mr. Magoo testing to local preview only.

2. **Marie Kondo checklist finalization**
   - What we know: The checklist in `marie-kondo.md` references React/npm/TypeScript/shadcn which don't apply to the actual vanilla JS website. The Python pipeline hygiene items are not explicitly listed.
   - What's unclear: Whether to update the Marie Kondo agent definition before running, or adapt at execution time.
   - Recommendation: Adapt at execution time. The 3-pass inventory method (dependencies, code, configuration) is stack-agnostic. Skip inapplicable checklist items and substitute Python-specific checks. Do NOT modify the agent definition file.

3. **Concurrent user validation method**
   - What we know: GitHub Pages CDN handles static file serving. 200 concurrent users downloading DOCX files should be well within capacity.
   - What's unclear: Whether any formal validation is expected beyond agent assessment.
   - Recommendation: Per CONTEXT.md: "Focus on download reliability -- can 200 people search and download DOCX files without errors?" This is a qualitative assessment by the agents, not a quantitative load test. GitHub Pages serves Netflix-scale traffic; 200 concurrent DOCX downloads is trivial.

## Sources

### Primary (HIGH confidence)
- Phase 16 SYNTHESIS.md -- Pattern for audit-fix-verify cycle, severity classification, quality certificate format
- Phase 17 SYNTHESIS.md -- Known P1 issues, website architecture, performance metrics
- Agent definitions: `cyclops.md`, `dale-gribble.md`, `mr-magoo.md`, `marie-kondo.md` -- Checklists, output formats, methods
- `18-CONTEXT.md` -- User decisions on severity scoring, go/no-go criteria, fix-verify cycle, agent scope
- Direct codebase inspection -- `docs/web/` (6 files), `src/` (96 files), `.github/workflows/` (3 files)

### Secondary (MEDIUM confidence)
- Phase 16 plan structure (16-01, 16-02) -- Two-wave execution pattern
- Phase 17 plan 05 (17-05) -- 4-agent review synthesis structure
- `REQUIREMENTS.md` HARD-01 through HARD-05 -- Requirement definitions

### Tertiary (LOW confidence)
- None. All research is based on direct codebase and planning document inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new technology, all existing tools verified by inspection
- Architecture: HIGH -- Reusing proven Phase 16 pattern with well-documented adaptations
- Pitfalls: HIGH -- Based on direct codebase analysis and Phase 16/17 experience
- Agent checklists: HIGH -- Read directly from agent definition files
- Open questions: MEDIUM -- Live site deployment status needs verification

**Research date:** 2026-02-13
**Valid until:** 2026-02-20 (7 days -- fast-moving production phase)
