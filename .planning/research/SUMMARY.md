# Project Research Summary

**Project:** TCR Policy Scanner v1.3 "Production Launch"
**Domain:** Tribal Climate Resilience policy intelligence pipeline — production readiness
**Researched:** 2026-02-12
**Confidence:** HIGH

## Executive Summary

The TCR Policy Scanner is a Tribal advocacy document generation system that transforms federal climate policy intelligence into customized DOCX packets for 592 Federally Recognized Tribal Nations. Version 1.3 represents the production launch phase — transitioning from a functional prototype to a production-ready distribution system serving 100-200 concurrent users during critical federal policy windows.

The research reveals three major architectural gaps that must be closed for production readiness: **data completeness** (3 of 4 scrapers silently truncate results by not paginating API responses), **distribution infrastructure** (a React/Vite website that currently downloads fake text blobs instead of real DOCX files), and **trustworthiness** (no confidence scoring or quality validation for 992 generated documents). The existing Python pipeline (743 tests passing, v1.0-v1.2 milestones complete) is production-grade. The new website frontend drafted in `.planning/website/` has 47 known issues spanning P0 (fake downloads, mock data for 46 Tribes vs 592) to P3 (typography). The critical path is: fix scraper pagination for complete data → fix website to serve real DOCX → validate document quality → harden for production load.

**Key risks:** (1) SquareSpace iframe sandbox attributes may block downloads from embedded content — this is the deployment target and must be tested first; (2) Indigenous data sovereignty violations via third-party tracking scripts (Google Analytics, Google Fonts CDN) would destroy trust with Tribal communities; (3) The system ships TODAY for peak usage Feb 12-13, 2026 — time pressure creates temptation to skip critical accessibility (WCAG 2.1 AA) and quality validation steps. Mitigation: ruthlessly prioritize P0 fixes (real downloads, 592-Tribe coverage, SquareSpace iframe test), defer all non-blocking features, and add automated quality gates (DOCX structural validation, client-side accessibility audit, zero third-party request checks).

## Key Findings

### Recommended Stack

**No new production Python dependencies needed.** All data reliability fixes (scraper pagination, bill detail fetching, confidence scoring) are pure logic changes using existing libraries (aiohttp, python-docx, pydantic). The scraper pagination pattern already exists in `usaspending.py` and should be copied to the three unpaginated scrapers (Federal Register, Grants.gov, Congress.gov).

**Website stack: React 18 + Vite 6 + Tailwind v4 (DO NOT upgrade to React 19 or Vite 7).** React 19's Server Components provide zero value for a static GitHub Pages SPA and risk breaking shadcn/Radix components. Vite 7's Rolldown bundler introduces breaking plugin changes. The draft website is on these versions and they are stable/supported. Add Fuse.js 7.1.0 for 592-Tribe fuzzy search autocomplete (lightweight at 7KB gzipped). Remove 30+ unused dependencies (embla-carousel, recharts, react-day-picker, etc.) that bloat the bundle.

**DOCX visual QA: LibreOffice headless + Playwright + Pillow (dev-only dependencies).** This three-stage pipeline (DOCX → PDF via LibreOffice CLI → screenshots via Playwright → pixel-diff via Pillow) validates visual rendering quality across 992 documents. Structural validation (heading hierarchy, table presence, font consistency) uses the existing `python-docx` library with no new dependencies — extend the existing `DocumentQualityReviewer` class.

**Core technologies:**
- **Python 3.12** (existing): Runtime for scrapers, packet generation, confidence scoring — no changes
- **aiohttp** (existing): Async HTTP client, BaseScraper pattern handles retry + circuit breaker — pagination loops call `_request_with_retry()` naturally
- **python-docx** (existing): DOCX generation + structural validation — existing StyleManager/HotSheetRenderer stay unchanged
- **React 18.3.1** (stay on v18): Static SPA for document distribution — DO NOT upgrade to React 19 (Server Components not needed for static GitHub Pages deployment)
- **Vite 6.x** (stay on v6): Build tool — DO NOT upgrade to Vite 7 (Rolldown bundler breaking changes)
- **Fuse.js 7.1.0** (NEW): Client-side fuzzy search for 592-Tribe autocomplete — purpose-built for typo tolerance, 592 items loads in <1ms
- **Playwright 1.58.0** (NEW, dev-only): DOCX visual QA screenshots via headless Chromium
- **LibreOffice 24.2+** (system dependency, CI-only): DOCX-to-PDF conversion for visual QA
- **Pillow 11.0.0** (NEW, dev-only): Image comparison for visual regression detection

### Expected Features

**Must have (table stakes) — these are P0 blockers for production:**

1. **Real DOCX downloads** — Current system generates fake text blobs (5-line plaintext stubs). The Python `DocxEngine` produces real 150KB advocacy packets, but the React frontend download handler creates in-browser Blobs instead of linking to GitHub Pages-hosted files. This is the single most trust-destroying behavior.

2. **Full 592-Tribe coverage** — Currently serving 46 hardcoded Tribes in `mockData.ts` vs 592 in the actual `tribal_registry.json`. 546 of 592 Tribal Nations find nothing when they search.

3. **Scraper pagination** — Federal Register, Grants.gov, and Congress.gov scrapers fetch page 1 only (25-50 results) and never check for `next_page_url` or pagination tokens. Silent data loss when results exceed page size. USASpending already paginates correctly; copy its pattern.

4. **WCAG 2.1 AA compliance** — The autocomplete widget has no ARIA roles (`role="combobox"`, `aria-expanded`, `aria-activedescendant`), no keyboard navigation through suggestions, no live region announcements, and potential color contrast failures. Keyboard-only and screen reader users cannot complete the search → download flow.

5. **SquareSpace iframe embedding** — The primary deployment target. Requires `sandbox="allow-scripts allow-same-origin allow-downloads allow-popups"` attribute on the iframe Code Block. Without `allow-downloads`, Chrome 83+ silently blocks all download attempts. This MUST be tested in actual SquareSpace environment before declaring "ready."

6. **Performance for 100-200 concurrent users** — GitHub Pages serves static files via Fastly CDN. 992 DOCX files at ~100KB each = ~100MB total, well within 100GB/month bandwidth limits. Critical: Vite `base` path must be set to `/tcr-policy-scanner/` for GitHub Pages repository-level hosting, or all assets return 404 (blank white page).

**Should have (differentiators) — these elevate trust and professionalism:**

1. **Confidence scoring** — Intelligence products without confidence indicators are opinion, not analysis. Each DOCX section should show "Data Confidence: HIGH/MEDIUM/LOW" based on: source diversity (how many independent APIs contributed), temporal currency (data freshness < 30 days), completeness (awards + hazards + congressional data all present). Use qualitative labels NOT numeric scores (research shows numeric scores create false precision and overconfidence bias).

2. **DOCX visual QA automation** — 992 documents cannot be manually reviewed. Existing `DocumentQualityReviewer` checks text content (audience leakage, air gap violations, placeholders) but not visual formatting (heading hierarchy, table structure, font consistency). Add structural checks using `python-docx` object model (no new dependencies). For visual regression, use LibreOffice headless + Playwright to screenshot sample pages.

3. **Freshness indicators** — Display "Data as of: [date]" in website footer and DOCX headers. The existing `build_web_index.py` already includes `generated_at` timestamp in `tribes.json`. This builds trust by showing when intelligence was last refreshed.

4. **Congress.gov bill detail enrichment** — Current scraper fetches bill listings but not detail sub-endpoints (cosponsors, actions, summaries, subjects). For policy intelligence, users need to know who supports a bill (cosponsors), whether it is moving (actions), and what it does (CRS summaries). Each bill has sub-endpoints at `/bill/{congress}/{type}/{number}/{sub}`. Fetch 3 highest-value endpoints: actions, cosponsors, summaries.

**Defer (v2+) — not essential for Feb 12-13 peak usage:**

- Action Center landing page (pre-written email templates, elected official directories)
- Download analytics beyond GitHub Pages built-in traffic data
- PDF conversion of DOCX files (congressional offices use Word, not PDF)
- Multi-language translation (requires professional translation of regulatory terminology)
- Full-text search across 992 documents (Tribe name autocomplete is sufficient; users come looking for their Nation)

### Architecture Approach

The system has three planes: **Pipeline Plane** (Python async scrapers + packet generation), **Distribution Plane** (React website + GitHub Pages), and **QA Automation Plane** (new for v1.3). The critical integration point is: React website fetches `tribes.json` manifest at runtime (not build time), constructs download URLs from the `documents` object, and links to DOCX files served as static assets from `docs/web/tribes/`. The pipeline and website are decoupled — packets regenerate weekly via `generate-packets.yml`, website builds once and redeploys only when features change.

**Data sovereignty constraint:** Zero third-party requests. No Google Analytics (behavioral data about which Tribal Nations are searching violates CARE Principles for Indigenous Data Governance). No Google Fonts CDN (self-host `League Spartan` and `Roboto` fonts). No error tracking services (Sentry, LogRocket). Enforce with CSP meta tag in `index.html`: `default-src 'self'; font-src 'self'; connect-src 'self'`. Add CI test that scans build output for third-party URLs.

**Major components:**

1. **Scraper pagination loops** — Modify 3 scrapers (`federal_register.py`, `grants_gov.py`, `congress_gov.py`) to add pagination loops using native API mechanisms (Federal Register: `next_page_url` in response; Grants.gov: `startRecordNum` offset + `totalHits` count; Congress.gov: `offset` param + `pagination.next` URL). Safety cap at 10 pages (500-1000 results) per query to prevent infinite loops.

2. **ConfidenceScorer** (new module) — Computes per-section confidence levels based on data completeness (award count, hazard sources), recency (cache age vs generation time), and source diversity (number of APIs that contributed). Integrates into `PacketOrchestrator._build_context()` AFTER assembling context, BEFORE DOCX generation. Stores in `context.confidence_scores` dict. Renders in DOCX via `docx_sections.py` as subtle indicators (colored sidebar or footnote).

3. **React website** — Replaces vanilla JS widget at `docs/web/`. Vite builds to `docs/web/` (configure `outDir`). Must NOT clobber `data/tribes.json` or `tribes/` DOCX files. Fetches `tribes.json` at runtime (`useEffect` on mount), indexes with Fuse.js for fuzzy search, constructs download URLs as relative paths: `tribes/internal/{tribe_id}.docx`. Critical: replace `mockData.ts` import with runtime fetch. Remove all Blob-based download code.

4. **QA screenshot pipeline** (new script) — `scripts/qa_screenshot.py` converts DOCX → PDF via LibreOffice headless (`soffice --headless --convert-to pdf`), opens PDF in Playwright Chromium, captures full-page screenshots, generates HTML gallery for human review. Runs AFTER `generate-packets.yml` completes. Read-only consumer of packet output.

5. **build_web_index.py** (enhanced) — Already generates `tribes.json` manifest. Add confidence scores to output if computed during packet generation. Runs as final step in `generate-packets.yml` workflow AFTER DOCX files copied to `docs/web/tribes/`, BEFORE Pages deployment.

### Critical Pitfalls

1. **Fake downloads destroy trust** — The current download handler generates 5-line text blobs saved as `.txt` files. A Tribal Leader sees "REPORT READY FOR DOWNLOAD," clicks the button, and receives nothing. This is the single highest priority fix. Prevention: replace Blob generation with URL-based downloads pointing to actual DOCX files on GitHub Pages (`tribes/{doc_type}/{tribe_id}.docx`). Test by opening the downloaded file in Microsoft Word — if it's a text file, the fix failed.

2. **SquareSpace iframe sandbox blocks downloads** — Chrome 83+ blocks downloads from sandboxed iframes unless `allow-downloads` is explicitly set in the `sandbox` attribute. SquareSpace's default embed blocks may not include this flag. Prevention: use SquareSpace Code Block (not Embed Block) to manually set `sandbox="allow-scripts allow-same-origin allow-downloads allow-popups"`. Fallback: use `window.open()` to escape the iframe context (requires `allow-popups`). Test in actual SquareSpace preview environment before declaring ready.

3. **Three scrapers silently truncate results** — Federal Register (per_page=50, no loop), Grants.gov (rows=25, no offset), Congress.gov (limit=50, no offset) fetch page 1 only. If an API returns 150 results, items 51-150 are silently dropped. Prevention: implement pagination for each API using native mechanisms. Add safety cap (max 10 pages). Log total items collected vs API-reported total. Compare before/after counts to verify pagination worked.

4. **Vite base path breaks GitHub Pages deployment** — Default `base: "/"` resolves assets against domain root (`github.io/main.js`). Repository-level hosting requires `base: "/tcr-policy-scanner/"` to resolve correctly (`github.io/tcr-policy-scanner/main.js`). Without this, deployed site shows blank white page with all JS/CSS returning 404. Prevention: set `base` in `vite.config.ts` conditionally (`process.env.NODE_ENV === 'production' ? '/tcr-policy-scanner/' : '/'`). Verify Network tab shows all assets loading with 200 status codes.

5. **Indigenous data sovereignty violations via tracking scripts** — Google Analytics, Google Fonts CDN, Sentry, or any third-party service creates behavioral metadata about which Tribal Nations are searching for policy intelligence. This violates CARE Principles (Authority to Control) and OCAP (Ownership, Control, Access, Possession). Prevention: audit all external requests via Network tab — verify ZERO requests to domains other than `github.io`. Self-host all fonts. Add CSP meta tag. Document the constraint in README. Add CI test that scans build output for third-party URLs.

6. **WCAG 2.1 AA failures exclude users** — The autocomplete has no ARIA roles (`role="combobox"`, `aria-expanded`), no keyboard navigation (arrow keys through suggestions), no live region announcements (result count changes), and potential color contrast failures (`text-cyan-300/60` at 60% opacity). Prevention: follow WAI-ARIA Combobox Pattern exactly. Add `aria-live="polite"` region for result count. Use Radix UI's `Select` component (already a dependency) for the RegionSelector dropdown. Test with NVDA/VoiceOver manually and axe-core in CI.

7. **Confidence scores create overconfidence bias** — Displaying "Data Confidence: HIGH (0.95)" when the 0.95 score reflects developer assumptions (T1 source = 1.00) rather than empirical calibration leads to false precision. Tribal Leaders may cite uncalibrated scores in congressional testimony. Prevention: use qualitative labels ("VERIFIED" / "ESTIMATED" / "PENDING") NOT numeric scores. Add disclaimers explaining what "HIGH" means. Start conservative — defer numeric scores until after empirical validation against known outcomes.

## Implications for Roadmap

Based on research, the milestone decomposes into 5-7 phases with clear dependencies. Critical path: data reliability → document quality → website deployment → production hardening. The SquareSpace iframe test MUST happen first (before building any website features) because if iframe embedding is blocked by GitHub Pages headers (`X-Frame-Options: DENY`), the entire deployment architecture changes.

### Phase 1: Scraper Pagination + Bill Detail Fetching
**Rationale:** Data completeness is the foundation. All downstream features (confidence scoring, DOCX quality, website distribution) depend on complete, accurate data. Fix silent data truncation before improving output. Pagination pattern already exists in `usaspending.py` — copy to 3 unpaginated scrapers.

**Delivers:**
- Complete results from Federal Register (up to 2000-result API limit), Grants.gov (all pages until `totalHits` exhausted), Congress.gov (follow `pagination.next` until null)
- Congress.gov bill detail sub-endpoints (actions, cosponsors, summaries) enriching legislative intelligence
- Measurable increase in items collected per scan (log before/after counts)

**Addresses:** TS-04 (scraper pagination), TS-05 (bill detail enrichment) from FEATURES.md

**Avoids:** C-4 (silent truncation), M-4 (rate limiting during pagination) from PITFALLS.md

**Stack:** No new dependencies. Pure logic changes using existing `BaseScraper._request_with_retry()`.

**Research flag:** LOW — pattern already exists, APIs are well-documented. Standard implementation phase.

---

### Phase 2: Confidence Scoring
**Rationale:** Depends on complete data from Phase 1 (pagination must provide full source coverage before confidence can be assessed). Produces metadata that both DOCX rendering (Phase 3) and website (Phase 5) consume. Build computation layer before building display layers.

**Delivers:**
- New module `src/packets/confidence.py` with `ConfidenceScorer` class
- Per-section confidence levels (overall, congressional, awards, hazards, economic) based on: source diversity, data freshness, completeness, match quality
- Integration into `PacketOrchestrator._build_context()`
- Qualitative labels ("HIGH"/"MEDIUM"/"LOW") NOT numeric scores (defers numeric scores to post-calibration)

**Addresses:** DF-01 (confidence scoring) from FEATURES.md

**Avoids:** M-3 (overconfidence bias) from PITFALLS.md by using qualitative labels and adding disclaimers

**Stack:** No new dependencies. Pure computation on existing `TribePacketContext` data.

**Research flag:** LOW — deterministic scoring with known inputs. Defer ML/calibration to v2+.

---

### Phase 3: DOCX Quality Enhancements
**Rationale:** Depends on confidence scores from Phase 2 (renders confidence badges in section headers). DOCX improvements must ship BEFORE the website distributes them to users (Phase 5).

**Delivers:**
- Confidence badges rendered in DOCX section headers via `docx_sections.py`
- Source citations per data point (which API contributed this figure)
- Structural validation script (`scripts/validate_docx_structure.py`) checking: heading hierarchy, table presence, font consistency, no placeholders
- Visual QA automation (`scripts/qa_screenshot.py`): DOCX → PDF → screenshots → HTML gallery
- Full batch regeneration with verified output

**Addresses:** DF-02 (DOCX visual QA) from FEATURES.md

**Avoids:** Shipping unreviewed documents to production (quality gate before distribution)

**Stack:** Playwright 1.58.0, LibreOffice 24.2+, Pillow 11.0.0 (dev-only dependencies)

**Research flag:** MEDIUM — LibreOffice headless and Playwright integration needs testing on GitHub Actions `ubuntu-latest`. Verify `apt-get install libreoffice-writer-nogui` + `playwright install chromium --with-deps` works in CI.

---

### Phase 4: SquareSpace Iframe Validation (GATE)
**Rationale:** This is a GO/NO-GO decision point. If GitHub Pages blocks iframe embedding via `X-Frame-Options` or CSP `frame-ancestors`, the entire deployment architecture changes (alternative: Cloudflare Pages, Vercel, or direct link instead of embed). MUST test before building website features (Phase 5).

**Delivers:**
- Deployed "Hello World" test page to GitHub Pages
- SquareSpace Code Block with iframe embed + correct `sandbox` attributes
- Verified rendering in SquareSpace preview environment
- Documented fallback plan if embedding fails
- Decision: proceed with embedded architecture OR pivot to direct link

**Addresses:** TS-07 (SquareSpace iframe embedding) from FEATURES.md

**Avoids:** C-3 (sandbox blocks downloads), M-6 (X-Frame-Options blocks embedding) from PITFALLS.md

**Stack:** No code changes. Pure infrastructure validation.

**Research flag:** HIGH — GitHub Pages iframe behavior is documented but varies by configuration. Must test empirically. SquareSpace sandbox attribute control is a known limitation. This phase is HIGH RISK.

---

### Phase 5: Website Production Launch (GATE PASSED)
**Rationale:** Assumes Phase 4 validated iframe embedding works. This is the largest single feature — fixing 47 known issues in `.planning/website/`. Depends on: verified DOCX from Phase 3 (what we're distributing), confidence data from Phase 2 (what we display), SquareSpace test from Phase 4 (how we deploy).

**Delivers:**
- Fixed P0 issues: real DOCX downloads (replace Blob generation with URL construction), 592-Tribe coverage (replace `mockData.ts` with runtime `tribes.json` fetch)
- Fuse.js 7.1.0 integration for fuzzy search autocomplete
- Removed 30+ unused dependencies (embla-carousel, recharts, react-day-picker, cmdk, etc.)
- Vite `base` path configured: `/tcr-policy-scanner/`
- Build pipeline: Vite output → `docs/web/`, merged with DOCX files + `tribes.json`
- Deployed to GitHub Pages, embedded in SquareSpace with verified download flow

**Addresses:** TS-01 (real downloads), TS-02 (592 coverage), TS-06 (performance) from FEATURES.md

**Avoids:** C-1 (fake downloads), TD-1 (mock data), C-5 (Vite base path), C-2 (MIME type issues), M-5 (404 fallback delivers HTML) from PITFALLS.md

**Stack:** React 18.3.1, Vite 6.x, Fuse.js 7.1.0, Tailwind v4

**Research flag:** MEDIUM — React/Vite deployment to GitHub Pages is well-documented, but the merger of SPA output + static DOCX files in `generate-packets.yml` needs workflow engineering. Vite `base` path and 404.html SPA hack need careful testing.

---

### Phase 6: Accessibility (WCAG 2.1 AA)
**Rationale:** Can run in parallel with Phase 5 (website launch) but should complete BEFORE declaring production-ready. Keyboard-only and screen reader users are part of the target audience (Tribal climate coordinators, federal partners). Section 508 compliance expected for federal-facing tools.

**Delivers:**
- WAI-ARIA Combobox Pattern implemented: `role="combobox"`, `aria-expanded`, `aria-activedescendant`, arrow-key navigation
- `aria-live="polite"` region announcing result count changes
- Color contrast audit (all combinations meet 4.5:1 for text, 3:1 for UI components)
- Skip navigation link (visible on focus)
- Radix UI `Select` component for RegionSelector dropdown (built-in accessibility)
- Keyboard-only testing: search → select → download flow completable without mouse
- axe-core CI check + manual NVDA/VoiceOver testing

**Addresses:** TS-03 (WCAG 2.1 AA compliance) from FEATURES.md

**Avoids:** M-1 (WCAG failures exclude users) from PITFALLS.md

**Stack:** Radix UI components (already a dependency), axe-core (CI testing)

**Research flag:** LOW — WCAG 2.1 AA is well-documented. WAI-ARIA Combobox Pattern is standardized. Radix UI provides accessible components out-of-box.

---

### Phase 7: Production Hardening
**Rationale:** Final phase. Assumes website deployed (Phase 5), accessibility verified (Phase 6), DOCX quality validated (Phase 3). This is stress testing, bug hunting, and final go/no-go before peak usage Feb 12-13.

**Delivers:**
- Data sovereignty audit: zero third-party requests (Network tab verification), self-hosted fonts, CSP meta tag, CI test for third-party URLs
- Performance testing: 100-200 concurrent user simulation, verify GitHub Pages CDN handles load
- Bug hunt swarm: atomic → pairs → chains → stress (LAUNCH-SWARM.md strategy)
- Freshness indicators: "Data as of: [date]" in website footer and DOCX headers
- Final batch regeneration with all v1.3 features active
- Go/no-go decision based on: download flow works, SquareSpace embed works, accessibility passes, no third-party tracking, documents are trustworthy

**Addresses:** DF-04 (freshness indicators) from FEATURES.md

**Avoids:** C-6 (data sovereignty violations), PT-1 (large JSON load), PT-2 (concurrent user bursts) from PITFALLS.md

**Stack:** No new dependencies. Testing and validation only.

**Research flag:** LOW — standard testing practices. GitHub Pages performance limits are documented (100GB/month bandwidth, 1GB site size). The 1.1GB DOCX corpus (992 files * ~500KB avg) approaches the limit — may need GitHub Releases for storage (defer to monitoring).

---

### Phase Ordering Rationale

**Critical path dependencies:**
- Phase 1 (pagination) MUST precede Phase 2 (confidence scoring) — can't assess confidence without complete data
- Phase 2 (confidence) MUST precede Phase 3 (DOCX quality) — DOCX renders confidence badges
- Phase 3 (DOCX quality) MUST precede Phase 5 (website) — don't distribute unverified documents
- Phase 4 (iframe test) MUST precede Phase 5 (website) — validates deployment architecture
- Phase 7 (hardening) MUST be last — tests the integrated system

**Parallel opportunities:**
- Phase 6 (accessibility) can overlap Phase 5 (website) if features are isolated (accessibility touches specific components: TribeSelector, RegionSelector; download handler is separate)
- Phase 3 (DOCX quality) and Phase 4 (iframe test) are independent and can run simultaneously

**Time pressure mitigation:**
- Phase 4 (iframe test) is a 2-hour task but HIGH RISK — do it first thing to avoid late-breaking architecture pivot
- Phases 1-3 (data reliability → confidence → DOCX quality) are the "trustworthiness pipeline" — these can ship BEFORE the website if needed
- Phase 5 (website) P0 fixes (real downloads, 592 coverage, Vite base path) are ~1-2 days; the remaining 44 issues are P1-P3 and can defer
- Phase 6 (accessibility) critical fixes (ARIA roles, keyboard nav, skip link) are ~1 day; full WCAG audit can defer to post-launch
- Phase 7 (hardening) can be condensed to: data sovereignty audit (2 hours) + download flow smoke test (1 hour) + go/no-go decision (30 min)

**Grouping rationale:**
- Phases 1-3 form the "backend pipeline" (Python, no frontend changes) — can be developed/tested in isolation
- Phases 4-6 form the "frontend deployment" (React, website, accessibility) — separate testing environment
- Phase 7 is "integration validation" (everything working together)

**Avoids pitfalls:**
- Early iframe test (Phase 4) avoids late discovery that embedding is blocked (M-6)
- Scraper pagination before confidence (Phases 1 → 2) avoids computing confidence on truncated data (C-4)
- DOCX quality before website (Phases 3 → 5) avoids distributing documents with fake confidence scores or visual regressions (M-3)
- Accessibility as dedicated phase (Phase 6) avoids the "ship now, fix accessibility later" trap that leads to permanent WCAG failures (M-1)
- Data sovereignty audit in hardening (Phase 7) catches third-party tracking before production (C-6)

### Research Flags

**Phases likely needing deeper research during planning:**

- **Phase 4 (SquareSpace iframe test):** GitHub Pages `X-Frame-Options` behavior is documented but varies by repository configuration. SquareSpace sandbox attribute control is a known limitation (may not support `allow-downloads` on all plan tiers). Empirical testing required. If embedding fails, need alternative hosting research (Cloudflare Pages, Vercel, Netlify) with custom header support.

- **Phase 3 (DOCX visual QA):** LibreOffice headless + Playwright integration on GitHub Actions `ubuntu-latest` needs validation. Installation commands (`apt-get install libreoffice-writer-nogui`, `playwright install chromium --with-deps`) and CI workflow timeout/memory limits need testing with actual DOCX corpus (992 files). May hit runner resource limits.

**Phases with standard patterns (skip research-phase):**

- **Phase 1 (scraper pagination):** Pattern already exists in `usaspending.py`. APIs are well-documented (Congress.gov GitHub repo, Federal Register developer docs, Grants.gov wiki). No niche domain knowledge required.

- **Phase 2 (confidence scoring):** Deterministic computation on known inputs. No ML, no external services, no API calls. Standard implementation phase.

- **Phase 5 (website launch):** React/Vite deployment to GitHub Pages is extensively documented. Fuse.js API is straightforward. The 47 known issues are cataloged with clear fixes. Standard frontend development.

- **Phase 6 (accessibility):** WCAG 2.1 AA is a well-established standard. WAI-ARIA Combobox Pattern is documented with examples. Radix UI provides accessible components. Standard compliance work.

- **Phase 7 (production hardening):** Standard testing and validation. GitHub Pages limits are documented. Data sovereignty audit is a checklist. No research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All stack decisions verified against PyPI/npm registries (versions confirmed), official API docs (pagination mechanisms verified), and codebase inspection (existing patterns identified). React 18 / Vite 6 stability confirmed. Playwright/LibreOffice/Pillow verified on GitHub Actions ubuntu-latest. |
| Features | HIGH | Feature prioritization based on: codebase inspection (47 known website issues cataloged), Tribal advocacy domain expertise (table stakes vs differentiators), and production readiness criteria (accessibility, performance, data sovereignty). MVP recommendation (P0 fixes today, P1 within 24 hours) is time-pressure aware. |
| Architecture | HIGH | Integration points verified via direct file inspection (95 Python source files, 2 GitHub Actions workflows, React website draft). Data flow traced from scrapers → cache → packets → website → GitHub Pages → SquareSpace. Anti-patterns identified from real pitfalls (404.html hack breaks DOCX serving, Blob downloads vs URL downloads). |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls (C-1 through C-6) verified against: codebase inspection (fake download handler in `TribeSelector.tsx` lines 38-51, unpaginated scrapers), browser security specs (iframe sandbox `allow-downloads`), Indigenous data governance frameworks (CARE Principles, OCAP), WCAG 2.1 AA spec. Moderate pitfalls (M-1 through M-6) sourced from: community knowledge (Vite base path, GitHub Pages MIME types), accessibility standards (WAI-ARIA), and research on AI confidence calibration. |

**Overall confidence:** HIGH

Findings are anchored in:
1. **Direct codebase inspection** — 95 Python files, React website draft, GitHub Actions workflows
2. **Verified external sources** — Official API documentation (Congress.gov GitHub, Federal Register docs, Grants.gov wiki), package registries (PyPI, npm), browser specs (MDN iframe sandbox), accessibility standards (WCAG 2.1 AA, WAI-ARIA APG)
3. **Domain expertise** — Tribal advocacy context (data sovereignty constraints, trust requirements), policy intelligence domain (confidence scoring practices from IC Standard ICD 203)
4. **Empirical validation opportunities** — Most pitfalls can be detected via testing (download a file, check Network tab, test with keyboard-only, verify in SquareSpace iframe)

The MEDIUM confidence area is pitfalls that depend on empirical testing in production conditions (SquareSpace iframe sandbox behavior, GitHub Pages MIME type handling for DOCX, concurrent user performance at 200 users). These cannot be fully validated until deployed.

### Gaps to Address

**SquareSpace iframe embedding behavior** — Research found that `allow-downloads` sandbox attribute is required (Chrome 83+), but SquareSpace's default embed blocks and plan-tier restrictions are not fully documented. The official SquareSpace help docs say Code Blocks support iframes on Business+ plans, but do not specify whether `sandbox` attribute is user-controllable. **Mitigation:** Phase 4 (iframe test) validates this empirically in actual SquareSpace environment before building Phase 5 (website). Fallback: direct link instead of embed.

**GitHub Pages MIME type handling for DOCX** — Community sources report that DOCX files may be served as `application/octet-stream` or `application/zip` instead of the correct `application/vnd.openxmlformats-officedocument.wordprocessingml.document`. Official GitHub Pages docs do not specify MIME type behavior for DOCX. **Mitigation:** Test actual DOCX download from GitHub Pages on Chrome/Firefox/Safari/Edge + iOS/Android during Phase 5 deployment. Fallback: JavaScript-mediated download with explicit Content-Type (fetch as Blob, set type, trigger download via `URL.createObjectURL()`).

**Repository size approaching GitHub Pages 1GB limit** — 992 DOCX files at ~500KB avg = ~1.1GB total, exceeding the 1GB site size recommendation. Git history accumulates all versions even when files are overwritten. **Mitigation:** Monitor repository size after each batch generation (`git count-objects -vH`). If approaching 1GB, enable Git LFS for `*.docx` files (`.gitattributes`: `*.docx filter=lfs diff=lfs merge=lfs -text`) or move DOCX storage to GitHub Releases (2GB per file limit, no total limit). Defer to Phase 7 monitoring.

**Confidence score calibration vs developer assumptions** — The proposed confidence scoring uses source tier assignments (T1=1.00, T2=0.95) that reflect developer assumptions about source reliability, not empirical validation against known outcomes. Research on AI confidence calibration warns that uncalibrated scores create overconfidence bias. **Mitigation:** Phase 2 uses qualitative labels ("HIGH"/"MEDIUM"/"LOW") NOT numeric scores. Add disclaimers explaining what "HIGH" means. Defer numeric scores to v2+ after empirical calibration (compare USASpending award data against known Tribal government award announcements).

**LibreOffice headless + Playwright resource limits on GitHub Actions** — Converting 992 DOCX → PDF → screenshots may exceed runner memory limits or timeout. Ubuntu runners have 7GB RAM and 6-hour timeout, but LibreOffice conversion + Chromium screenshot pipeline is memory-intensive. **Mitigation:** Phase 3 QA automation samples representative documents (e.g., 10 Tribes per region = 80 documents) rather than processing all 992. Full-corpus validation defers to local testing or dedicated CI infrastructure. Structural validation (python-docx checks) can run on all 992 without resource concerns.

## Sources

### Primary (HIGH confidence)

**API Documentation:**
- [Congress.gov API GitHub Repository](https://github.com/LibraryOfCongress/api.congress.gov) — BillEndpoint.md (sub-endpoints: actions, cosponsors, summaries), README.md (rate limit 5000/hr, offset max 250, pagination.next)
- [Federal Register API v1](https://www.federalregister.gov/developers/documentation/api/v1) — pagination fields (next_page_url, total_pages, per_page max 50), 2000-result ceiling
- [Grants.gov Simpler API](https://wiki.simpler.grants.gov/product/api/search-opportunities) — search2 endpoint, startRecordNum/rows pagination, 10K result limit
- [GitHub Pages Limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) — 1GB site size, 100GB/month bandwidth, no documented per-second rate limits

**Package Registries:**
- [Playwright Python 1.58.0 on PyPI](https://pypi.org/project/playwright/) — Released 2026-01-30, Python 3.9-3.13 support
- [Fuse.js 7.1.0 on npm](https://www.npmjs.com/package/fuse.js) — Lightweight fuzzy search (7KB gzipped), 592 items benchmark
- [Tailwind CSS 4.1.x on npm](https://www.npmjs.com/package/tailwindcss) — v4 syntax with Vite plugin
- [React 19.2.4 on npm](https://www.npmjs.com/package/react) — Current latest (NOT recommended; stay on 18.3.1)
- [Vite 7.3.1 on npm](https://www.npmjs.com/package/vite) — Current latest (NOT recommended; stay on 6.x)

**Standards & Specifications:**
- [WCAG 2.1 AA Specification](https://www.w3.org/WAI/WCAG21/quickref/?currentsidebar=%23col_customize&levels=aaa) — Accessibility criteria 1.3.1, 1.4.3, 2.1.1, 2.4.1, 2.4.7, 4.1.2
- [WAI-ARIA Combobox Pattern (W3C APG)](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) — Required roles, states, keyboard navigation
- [MDN: iframe sandbox attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe) — allow-downloads, allow-scripts, allow-same-origin, allow-popups
- [Chrome Platform Status: Downloads in Sandboxed Iframes](https://chromestatus.com/feature/5706745674465280) — Chrome 83+ blocks downloads without allow-downloads

**Codebase Inspection:**
- `F:\tcr-policy-scanner\src\scrapers\` (4 scrapers: base.py, federal_register.py, grants_gov.py, congress_gov.py, usaspending.py)
- `F:\tcr-policy-scanner\src\packets\` (orchestrator.py, context.py, docx_engine.py, docx_sections.py, quality_review.py)
- `F:\tcr-policy-scanner\.planning\website\src\` (TribeSelector.tsx lines 38-51, mockData.ts, App.tsx, vite.config.ts)
- `F:\tcr-policy-scanner\.github\workflows\` (daily-scan.yml, generate-packets.yml)

### Secondary (MEDIUM confidence)

**Indigenous Data Governance:**
- [CARE Principles for Indigenous Data Governance](https://datascience.codata.org/articles/dsj-2020-043) — Collective Benefit, Authority to Control, Responsibility, Ethics
- [FNIGC OCAP Principles](https://fnigc.ca/ocap-training/) — Ownership, Control, Access, Possession (First Nations Information Governance Centre)
- Tribal Sovereignty Data Framework (TSDF) — T0-T5 classification (referenced in codebase docs/concepts/)

**Deployment & Embedding:**
- [SquareSpace Embed Blocks Help](https://support.squarespace.com/hc/en-us/articles/206543617-Embed-blocks) — iframe support, Business plan requirement for Code Blocks
- [Deploy Vite React to GitHub Pages](https://paulserban.eu/blog/post/deploy-vite-react-with-react-router-app-to-github-pages/) — Base path configuration, 404.html SPA hack
- [GitHub Pages CORS discussion](https://github.com/orgs/community/discussions/22399) — Access-Control-Allow-Origin: * for public repos
- [LibreOffice headless conversion guide](https://michalzalecki.com/converting-docx-to-pdf-using-python/) — soffice --headless --convert-to pdf

**Confidence Scoring:**
- [CIS Words of Estimative Probability](https://www.cisecurity.org/ms-isac/services/words-of-estimative-probability-analytic-confidences-and-structured-analytic-techniques) — HIGH/MODERATE/LOW framework
- [Analytic Confidence - Wikipedia](https://en.wikipedia.org/wiki/Analytic_confidence) — ICD 203 reference (Intelligence Community Directive)
- Research on AI confidence calibration (arXiv, multiple papers) — Overconfidence bias when users see numeric scores

### Tertiary (LOW confidence — needs validation)

**Performance & Infrastructure:**
- GitHub Pages undocumented per-second rate limits — official docs say "may enforce rate limits" with 429 responses, but no specifics on thresholds
- DOCX MIME type behavior on GitHub Pages — community reports of `application/zip` misidentification, but no official confirmation
- SquareSpace Code Block sandbox attribute control — help docs confirm iframe support on Business+ plans but do not specify sandbox attribute editability
- Concurrent user performance at 200 users on GitHub Pages — no published benchmarks; 100GB/month limit is documented but real-world CDN behavior under burst load is unspecified

---

*Research completed: 2026-02-12*
*Ready for roadmap: yes*
