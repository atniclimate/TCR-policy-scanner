# Feature Landscape: v1.3 Production Launch

**Domain:** Tribal advocacy packet distribution system (production readiness)
**Researched:** 2026-02-12
**Confidence:** HIGH for web/accessibility/pagination; MEDIUM for DOCX QA automation and confidence scoring
**Context:** 992 documents (384 Doc A + 592 Doc B + 8 Doc C + 8 Doc D) serving 592 Tribal Nations. Peak usage: 100-200 concurrent users over 48 hours (Feb 12-13, 2026). 47 known issues across P0-P3 severity.

---

## Overview

v1.3 transforms a functional document generation pipeline into a production-ready distribution system. The feature landscape spans seven domains: scraper pagination (API completeness), Congress.gov bill detail enrichment, website production readiness, DOCX visual QA automation, confidence scoring for intelligence products, WCAG 2.1 AA accessibility, and SquareSpace iframe embedding. Each domain has distinct table stakes that users and Tribal advocates expect, differentiators that elevate trust and professionalism, and anti-features that would waste effort or introduce risk.

---

## Table Stakes

Features users expect. Missing = product feels incomplete or untrustworthy for production use.

### TS-01: Real Document Downloads (P0 Fix)

**Why Expected:** Downloads currently serve fake text blobs. Users clicking "Download" expect an actual DOCX document. This is the single most critical production blocker.
**Complexity:** Medium
**What "Done" Looks Like:**
- All 992 DOCX files served from `docs/web/tribes/` directory via GitHub Pages
- tribes.json references correct file paths for each Tribe's Doc A and Doc B
- Download links verified to return valid DOCX files, not placeholder text
- File sizes are reasonable (50-200 KB per DOCX, not 0 bytes or multi-MB)
**Dependencies:** Existing `build_web_index.py`, existing `DocxEngine` output, existing GitHub Pages deployment

---

### TS-02: Full 592-Tribe Coverage in Web Index (P0 Fix)

**Why Expected:** Currently serving 46 Tribes vs 592. Users for the vast majority of Tribal Nations find nothing. An advocacy distribution system that covers 8% of its target audience is not production-ready.
**Complexity:** Low (build_web_index.py already supports 592; this is a data pipeline execution issue)
**What "Done" Looks Like:**
- tribes.json contains all 592 federally recognized Tribal Nations
- All 592 Doc B (congressional overview) files present and downloadable
- 384 Doc A (internal strategy) files present for Tribes with complete data
- Remaining 208 Tribes show "Congressional Overview available" (not "Documents not yet available")
**Dependencies:** Completed v1.2 batch generation (992 docs already generated)

---

### TS-03: WCAG 2.1 AA Accessibility Compliance

**Why Expected:** ADA Title II requires WCAG 2.1 AA by April 24, 2026 for entities serving 50,000+. While Tribal advocacy organizations may not be directly subject to Title II, their congressional audiences (government offices) expect accessible content. More importantly: 1 in 4 adults has a disability; excluding them from policy advocacy tools is antithetical to the project's values. The existing site has known failures: no ARIA landmarks beyond basic roles, no focus trap on card display, contrast issues on some elements, and no skip navigation.
**Complexity:** Medium
**What "Done" Looks Like:**

| WCAG Criterion | Requirement | Current Status | Fix |
|----------------|-------------|----------------|-----|
| 1.1.1 Non-text | Alt text for images | No images in current UI | N/A |
| 1.3.1 Info & Relationships | ARIA landmarks, heading hierarchy | Partial (has role="banner", role="main") | Add skip nav, verify heading levels |
| 1.4.3 Contrast (Min) | 4.5:1 for text, 3:1 for large text | Known contrast issues on muted text | Audit all color combinations |
| 2.1.1 Keyboard | All functionality via keyboard | Partial (Awesomplete supports keyboard) | Verify full keyboard flow |
| 2.1.2 No Keyboard Trap | Focus can always escape | No focus trap implemented (good) | Verify Escape key behavior |
| 2.4.1 Skip Navigation | Skip to main content link | Missing | Add skip link |
| 2.4.3 Focus Order | Logical tab sequence | Unknown | Test and fix |
| 2.4.7 Focus Visible | Visible focus indicator | Has outline styles | Verify all interactive elements |
| 3.2.1 On Focus | No context change on focus | OK | Verify |
| 4.1.2 Name, Role, Value | ARIA for custom widgets | Partial (combobox role exists, aria-expanded) | Complete ARIA for Awesomplete |

**Dependencies:** Existing CSS (style.css), existing JS (app.js), existing HTML (index.html)

---

### TS-04: Scraper Pagination for Complete Results

**Why Expected:** Current scrapers fetch one page of results (25-50 items) but do not paginate. For a production intelligence system, missing the second page of Federal Register results means missing regulatory actions. Incomplete data = unreliable intelligence.
**Complexity:** Medium

**Federal Register API Pagination:**
- Uses `page` parameter (1-indexed) with `per_page` (max 50, currently set to 50)
- Returns `total_pages` and `count` in response metadata
- Hard limit: only first 2,000 results accessible via pagination (use date filters for larger sets)
- Current scraper: fetches page 1 only -- no pagination loop
- Fix: Add pagination loop until `page >= total_pages` or results exhausted, respecting the 2,000 ceiling

**Grants.gov API Pagination:**
- Uses `page_offset` (1-indexed) and `page_size` (max 100, currently set to 25/50)
- Returns `pagination_info` with `total_pages`, `total_records`
- Hard limit: 10,000 results maximum per query (add filters to narrow if hit)
- Current scraper: fetches page 1 only for CFDA and keyword searches
- Fix: Loop incrementing `page_offset` until `page_offset > total_pages`

**Congress.gov API Pagination:**
- Uses `offset` parameter (0-based) with `limit` (max 250, currently set to 50)
- Returns `pagination` with `count` and `next` URL
- Rate limit: 5,000 requests/hour (generous)
- Current scraper: fetches first page only
- Fix: Follow `next` URLs or increment offset until all results retrieved

**USASpending API Pagination:**
- Uses `page` parameter (1-indexed) with `limit`
- Returns `page_metadata` with `hasNext`, `page`, `total`
- Current scraper (awards.py): already paginates correctly via CFDA batch approach
- Fix: Verify and document existing pagination behavior

**What "Done" Looks Like:**
- All 4 scrapers paginate through all available results (within API ceiling limits)
- Pagination respects rate limits (0.3-0.5s delays between pages)
- Pagination stops correctly (not infinite looping on empty pages)
- Circuit breaker still protects paginated loops (trips after N consecutive failures)
- Total items collected per scan increases measurably (log before/after counts)

**Dependencies:** Existing `BaseScraper._request_with_retry()`, existing circuit breaker

---

### TS-05: Congress.gov Bill Detail Enrichment

**Why Expected:** Current Congress.gov scraper fetches bill list data but not detail data. The list endpoint returns only: title, type, number, congress, latestAction, updateDate. For a policy intelligence product, users need cosponsors (who supports this?), subjects (what policy area?), and summaries (what does it do?). Without these, the 5-factor relevance scorer operates on incomplete data.
**Complexity:** Medium-High

**Congress.gov Bill API Sub-Endpoints:**
Each bill has sub-endpoints accessible at `/bill/{congress}/{billType}/{billNumber}/{sub}`:

| Sub-Endpoint | Key Data | Value for TCR |
|--------------|----------|---------------|
| `/actions` | Legislative steps with dates, types, committees | Track bill progress toward passage |
| `/cosponsors` | Member name, party, state, bioguideId | Identify congressional champions for Tribal climate |
| `/subjects` | CRS subject terms, policy area | Improve relevance scoring with subject matching |
| `/summaries` | CRS-written bill analysis | Richer abstract for relevance scoring and briefings |
| `/text` | Bill text versions with dates | Full text for keyword analysis (optional, large) |
| `/titles` | Official and short titles | Better display names |
| `/committees` | Committee referrals and activities | Track committee action |
| `/relatedbills` | Related legislation links | Cross-reference with other bills in pipeline |

**What "Done" Looks Like:**
- After fetching bill list, scraper fetches detail sub-endpoints for each relevant bill
- Normalized schema includes: `cosponsors_count`, `cosponsor_names`, `policy_area`, `subjects`, `crs_summary`, `committee_referrals`, `latest_action_type`
- Rate limiting respected: 0.3s between sub-endpoint calls, 5,000/hour limit
- Sub-endpoint failures degrade gracefully (bill still included with partial data)
- Detail fetching is optional (can be disabled via config for faster scans)

**Dependencies:** Existing `CongressGovScraper`, Congress.gov API key

---

### TS-06: Website Performance for 100-200 Concurrent Users

**Why Expected:** GitHub Pages serves static files via Fastly CDN. For 100-200 concurrent users, the site must load quickly and downloads must succeed without timeouts. The P0 issue is that downloads are fake text blobs (not large DOCX files). With real DOCX files (50-200 KB each), download performance becomes relevant.
**Complexity:** Low-Medium
**What "Done" Looks Like:**
- tribes.json loads in under 2 seconds (should be ~150-300 KB for 592 entries)
- DOCX file downloads complete in under 5 seconds per file
- No JavaScript errors under concurrent usage
- Search/autocomplete remains responsive with 592 entries
- Awesomplete handles 592 items without UI lag (currently configured for maxItems:15, which is correct)
- GitHub Pages bandwidth limits not exceeded (100 GB/month soft limit; 992 DOCX files at 100KB each = ~100 MB total, well within limits)

**Dependencies:** GitHub Pages hosting, Fastly CDN (automatic)

---

### TS-07: SquareSpace Iframe Embedding

**Why Expected:** The website is designed to embed in a SquareSpace site via iframe. Existing comment in index.html shows the embed code. For production, this must actually work.
**Complexity:** Low
**What "Done" Looks Like:**
- Iframe embed code works on SquareSpace Business plan or higher
- Widget renders correctly within constrained width (max-width: 800px)
- Widget height either fixed at 700px or uses postMessage for dynamic resizing
- Downloads work from within iframe (download attribute honored, no X-Frame-Options blocking)
- Widget is self-contained (no external dependencies that break in iframe context)
- Cross-origin considerations documented (same-origin vs cross-origin download behavior)
- title attribute on iframe present for WCAG 2.1 AA (already in embed comment)

**iframe Implementation Pattern:**
```html
<!-- In SquareSpace Code Block -->
<div style="width:100%;max-width:800px;margin:0 auto;">
  <iframe
    src="https://atniclimate.github.io/TCR-policy-scanner/"
    width="100%" height="700" frameborder="0"
    style="border:1px solid #e0e0e0;border-radius:8px;"
    title="Tribal Climate Resilience - Program Priorities"
    loading="lazy">
  </iframe>
</div>
```

**Cross-Origin Download Behavior:**
- DOCX downloads from GitHub Pages should work within SquareSpace iframe because the download attribute triggers browser-native download behavior
- If cross-origin restrictions block download, fallback: open in new tab via `target="_blank"` instead of `download` attribute
- Test in actual SquareSpace environment before peak usage

**Dependencies:** SquareSpace Business plan, existing index.html embed comment, GitHub Pages CORS headers

---

## Differentiators

Features that set the product apart. Not expected, but elevate trust, professionalism, and advocacy effectiveness.

### DF-01: Confidence Scoring for Policy Intelligence Products

**Value Proposition:** Intelligence products without confidence indicators are opinion, not analysis. The US intelligence community uses a standardized three-tier confidence framework (High/Moderate/Low) paired with Words of Estimative Probability. Applying this to Tribal policy intelligence would make TCR Policy Scanner's products more credible and professional than typical advocacy materials.
**Complexity:** Medium
**How Other Intelligence Tools Handle This:**

**US Intelligence Community Standard (ICD 203):**
- **High Confidence:** Judgments based on high-quality information from multiple sources, minimal conflict
- **Moderate Confidence:** Credibly sourced and plausible, but insufficient quality or corroboration for higher confidence
- **Low Confidence:** Source credibility or plausibility uncertain; scant, questionable, or fragmented information

**Factors to Assess:**
1. **Source diversity:** How many independent sources support this assessment? (Federal Register + Congress.gov + Grants.gov = multi-source)
2. **Source quality:** Authoritative government sources (HIGH) vs. inferred from keyword matching (LOW)
3. **Temporal currency:** Recent data (< 30 days) = higher confidence than stale data
4. **Corroboration:** Do multiple sources agree? Conflicting signals lower confidence
5. **Completeness:** Full data (awards + hazards + congressional) = higher confidence than partial

**Application to TCR:**
- Each Tribe's advocacy packet could include a data confidence indicator
- "Funding Analysis Confidence: HIGH -- based on 3 verified USASpending records and FEMA NRI county data"
- "Legislative Outlook Confidence: MODERATE -- based on bill text keyword matching; cosponsor analysis pending"
- Confidence drives prioritization: Tribes with HIGH confidence data get richer analysis

**Open Source Implementation (OpenCTI MISP Taxonomy):**
- Fuses source reliability with analytic confidence
- Tags: `estimative-language:confidence-in-analytic-judgment="high"` etc.
- TCR could adopt a simpler 3-tier model without the full taxonomy

**What "Done" Looks Like:**
- Each document section has a confidence indicator (HIGH/MODERATE/LOW)
- Confidence computed from: source count, data freshness, data completeness
- Displayed in DOCX output as a subtle indicator (e.g., colored sidebar or footnote)
- Web widget shows per-Tribe data quality indicator

**Dependencies:** Existing scoring engine, existing data coverage tracking (validate_coverage.py)

---

### DF-02: DOCX Visual QA Automation

**Value Proposition:** 992 documents cannot be manually reviewed. The existing `DocumentQualityReviewer` checks text content (audience leakage, air gap, placeholders) but does not check visual formatting (correct heading styles, table structure, font consistency, page count accuracy). Automated visual QA catches formatting regressions that text-only checks miss.
**Complexity:** Medium-High

**What Exists (quality_review.py):**
- Text-based checks: audience leakage (19 patterns), air gap (12 patterns), placeholder detection (6 patterns)
- Structural checks: confidential marking, minimum paragraph count, executive summary presence, page break count
- Batch review with markdown report generation
- Already integrated into the pipeline

**What to Add (Visual/Structural QA):**

| Check | How to Implement | Library |
|-------|-----------------|---------|
| Heading hierarchy (H1 -> H2 -> H3) | python-docx: iterate paragraphs, verify style names follow hierarchy | python-docx (existing) |
| Table presence per section | python-docx: count tables, verify minimum per doc type | python-docx (existing) |
| Font consistency | python-docx: verify all runs use expected font family/size | python-docx (existing) |
| Page count accuracy | python-docx: count section breaks + page breaks (already partial) | python-docx (existing) |
| Style name validation | python-docx: verify all paragraph styles match expected set | python-docx (existing) |
| Table column count | python-docx: verify tables have expected column counts | python-docx (existing) |
| Image presence (if applicable) | python-docx: check for inline shapes | python-docx (existing) |
| DOCX-to-PDF render comparison | Convert to PDF via LibreOffice CLI, compare screenshots | LibreOffice + Pillow (new) |

**Recommended Approach:**
- Extend existing `DocumentQualityReviewer` with structural checks (no new dependencies)
- python-docx can inspect heading levels, table dimensions, run fonts, and style names programmatically
- Skip DOCX-to-PDF visual regression (too complex for the timeline, requires LibreOffice install)
- Focus on structural invariants that can be checked via the python-docx object model

**What "Done" Looks Like:**
- quality_review.py has 5+ new structural checks
- Batch review catches: broken heading hierarchy, missing tables, wrong fonts, unexpected styles
- Structural checks are warnings (not critical), since they do not affect content accuracy
- Report includes structural issues alongside existing text-based issues

**Dependencies:** Existing `quality_review.py`, existing python-docx dependency

---

### DF-03: "Action Center" Landing Page

**Value Proposition:** Beyond document downloads, the website could include pre-written email templates, elected official directories, and talking points. This transforms a document distribution site into an advocacy platform.
**Complexity:** High
**Notes:** Defer to post-v1.3. The immediate need is document distribution, not advocacy orchestration. However, the web architecture should not preclude adding this later.
**Dependencies:** Would require significant new HTML/JS/CSS development

---

### DF-04: Freshness Indicators and Last-Updated Timestamps

**Value Proposition:** Users need to know when data was last refreshed. Showing "Data as of: Feb 11, 2026" builds trust. Without it, users cannot assess whether the policy intelligence is current.
**Complexity:** Low
**What "Done" Looks Like:**
- tribes.json includes `"generated_at": "2026-02-11T..."` metadata
- Web widget displays "Data as of: [date]" in footer or header
- Each Tribe card shows when its data was last updated
- Documents include generation date in header/footer

**Dependencies:** Existing `build_web_index.py` (already includes metadata generation timestamp)

---

### DF-05: Download Analytics (Basic)

**Value Proposition:** Knowing which Tribes' documents are being downloaded tells the organization where its advocacy efforts are landing. Even basic analytics (total downloads, most-downloaded Tribes) are valuable.
**Complexity:** Medium (if using GitHub Pages, client-side only; server-side not possible)
**What "Done" Looks Like:**
- Client-side download counter using localStorage or a lightweight analytics service
- Or: use GitHub's built-in traffic analytics (Settings > Traffic) for page views
- No server-side tracking needed for MVP
- Privacy-respecting: no PII collection, no cookies

**Dependencies:** Client-side JavaScript, GitHub traffic data

---

## Anti-Features

Features to explicitly NOT build for v1.3. Common mistakes in this domain that would waste time or introduce risk.

### AF-01: User Authentication or Login System

**Why Avoid:** The documents are advocacy materials meant for broad distribution. Adding authentication creates a barrier to access and contradicts the purpose. Doc B (congressional) documents are explicitly designed for sharing. Doc A (internal strategy) documents have "CONFIDENTIAL" markings but are distributed by Tribal leadership, not locked behind logins.
**What to Do Instead:** Use the existing air gap enforcement (no attribution, no tool names) and confidential markings. Trust Tribal leadership to manage distribution of their own materials.

---

### AF-02: Server-Side Rendering or Dynamic Backend

**Why Avoid:** GitHub Pages is static-only. Adding a backend (Flask, Express, etc.) changes the hosting model, adds cost, adds maintenance burden, and introduces failure modes. The 100-200 concurrent user target is easily handled by static files on CDN.
**What to Do Instead:** Keep everything static. Pre-generate all documents. Pre-build tribes.json. Let CDN do the heavy lifting. If dynamic features are ever needed, consider serverless functions (Cloudflare Workers, Netlify Functions) as a layer on top, not a replacement.

---

### AF-03: Full-Text Search Across Document Contents

**Why Avoid:** Searching within 992 DOCX files requires either a search index (adds build complexity) or server-side processing (breaks static hosting). The Awesomplete autocomplete on Tribe names is sufficient for finding specific Tribes. Users come looking for their Tribe, not searching for keywords.
**What to Do Instead:** Keep Tribe name autocomplete. If keyword search is ever needed, pre-build a search index as a JSON file and use lunr.js or fuse.js client-side.

---

### AF-04: Real-Time Data Refresh or Live API Connections in the Website

**Why Avoid:** The website should serve pre-generated, reviewed documents. Real-time API connections from the client would expose API keys, bypass quality review, and produce unreviewed content. The pipeline's value is in the human-reviewed, quality-checked output.
**What to Do Instead:** Regenerate documents on a schedule (weekly or as needed). Update tribes.json. Redeploy. The generation pipeline handles freshness; the website handles distribution.

---

### AF-05: PDF Conversion of DOCX Files

**Why Avoid:** Converting 992 DOCX files to PDF adds a build step (requires LibreOffice or Aspose), doubles storage (992 DOCX + 992 PDF), and DOCX is the standard format for congressional offices (they annotate and share Word documents). PDF is less useful for advocacy workflows.
**What to Do Instead:** Serve DOCX files only. If specific users need PDF, they can open in Word/Google Docs and export. Consider PDF as a post-v1.3 enhancement if user feedback demands it.

---

### AF-06: Complex Client-Side Filtering (By State, Ecoregion, Document Type)

**Why Avoid:** With 592 Tribes, users know which Tribe they want. Filtering by state or ecoregion adds UI complexity, increases JavaScript payload, and serves a minority use case. The regional documents (Doc C/D) already handle geographic aggregation.
**What to Do Instead:** Keep the single search input. It already narrows to 15 results with 2 characters. Add the 8 regional documents as a second section (already done in current UI). If filtering is needed later, add it as an enhancement.

---

### AF-07: Custom CMS for Document Management

**Why Avoid:** Documents are generated by the pipeline, not authored manually. A CMS adds overhead for uploading, organizing, and managing documents that are already managed by the generation pipeline. The pipeline IS the CMS.
**What to Do Instead:** Use the existing `build_web_index.py` to regenerate tribes.json whenever documents are updated. The script already handles file discovery, metadata extraction, and index generation.

---

### AF-08: Multi-Language Translation

**Why Avoid:** Policy advocacy documents contain highly specific legal and regulatory terminology. Machine translation of terms like "IIJA sunset provisions" or "FEMA BRIC Hazard Mitigation" would be inaccurate and misleading. Professional translation of 992 documents is infeasible for v1.3.
**What to Do Instead:** Serve documents in English (the language of federal policy). If specific Tribal Nations request translations, handle as individual requests outside the pipeline.

---

## Feature Dependencies

```
Critical Path (must be done in order):
  TS-01 (real downloads) + TS-02 (592 coverage) --> TS-06 (performance)
  These three form the "website actually works" cluster.
  Real downloads require real files deployed to GitHub Pages.
  Performance testing requires real files to be present.

Parallel Track A: API Enrichment
  TS-04 (scraper pagination) --> TS-05 (bill detail enrichment)
  Pagination completes the data; bill details enrich it.
  Can run in parallel with website fixes.

Parallel Track B: Quality & Compliance
  TS-03 (WCAG accessibility) -- independent, CSS/HTML/JS only
  DF-02 (DOCX visual QA) -- independent, python only

Parallel Track C: Trust Indicators
  DF-01 (confidence scoring) -- depends on TS-04 + TS-05 for enriched data
  DF-04 (freshness indicators) -- independent, low complexity

Standalone:
  TS-07 (SquareSpace embed) -- independent, verify and document

Dependency Graph:
  TS-01 (real downloads) ----+
                              |--> TS-06 (performance testing)
  TS-02 (592 Tribe coverage) +

  TS-04 (pagination) --> TS-05 (bill details) --> DF-01 (confidence scoring)

  TS-03 (WCAG) -- standalone
  TS-07 (iframe) -- standalone
  DF-02 (DOCX QA) -- standalone
  DF-04 (freshness) -- standalone
  DF-05 (analytics) -- standalone, defer to post-launch
```

---

## MVP Recommendation

Given the time pressure (peak usage Feb 12-13, 2026 -- TODAY AND TOMORROW), prioritize ruthlessly:

### Must-Ship Today (P0)

1. **TS-01: Real Document Downloads** -- Deploy actual DOCX files to GitHub Pages. Without this, the site is non-functional.
2. **TS-02: Full 592-Tribe Coverage** -- Run `build_web_index.py` with all 992 documents, deploy updated tribes.json.

### Must-Ship Within 24 Hours (P1)

3. **TS-03: Critical WCAG Fixes** -- Skip nav link, contrast fixes, focus management. Not full WCAG audit, just the P1 accessibility issues.
4. **TS-07: SquareSpace Embed Verification** -- Test iframe in actual SquareSpace environment.

### Should-Ship This Week (P2)

5. **TS-06: Performance Verification** -- Load test with 100+ concurrent downloads.
6. **DF-04: Freshness Indicators** -- Add "Data as of" timestamp to web widget.
7. **TS-04: Scraper Pagination** -- Complete data collection for next refresh cycle.

### Should-Ship Within 2 Weeks (P3)

8. **TS-05: Congress.gov Bill Details** -- Enrich legislative data.
9. **DF-02: DOCX Visual QA** -- Automated structural checks for next batch generation.
10. **DF-01: Confidence Scoring** -- Add trust indicators to documents.

### Defer to Post-v1.3

- DF-03: Action Center Landing Page
- DF-05: Download Analytics (beyond GitHub traffic)
- AF-05: PDF conversion (if user feedback demands it)

---

## Feature Prioritization Matrix

| Feature | Priority | Complexity | Impact | Dependencies | Timeline |
|---------|----------|------------|--------|-------------|----------|
| TS-01 Real Downloads | P0 | Medium | CRITICAL | build_web_index.py | Today |
| TS-02 592 Coverage | P0 | Low | CRITICAL | v1.2 batch output | Today |
| TS-03 WCAG Fixes | P1 | Medium | HIGH | CSS/HTML/JS only | 24 hours |
| TS-04 Pagination | P2 | Medium | HIGH | BaseScraper | This week |
| TS-05 Bill Details | P3 | Med-High | MEDIUM | Congress API key | 2 weeks |
| TS-06 Performance | P2 | Low | MEDIUM | TS-01 + TS-02 done | This week |
| TS-07 SquareSpace | P1 | Low | HIGH | GitHub Pages URL | 24 hours |
| DF-01 Confidence | P3 | Medium | MEDIUM | TS-04 + TS-05 | 2 weeks |
| DF-02 DOCX QA | P3 | Med-High | MEDIUM | quality_review.py | 2 weeks |
| DF-03 Action Center | Defer | High | LOW (for now) | New development | Post-v1.3 |
| DF-04 Freshness | P2 | Low | MEDIUM | build_web_index.py | This week |
| DF-05 Analytics | Defer | Medium | LOW | JS only | Post-v1.3 |

---

## Federal API Pagination Reference

### Federal Register API

| Parameter | Value | Notes |
|-----------|-------|-------|
| Endpoint | `GET /documents.json` | No auth required |
| Pagination param | `page` (1-indexed) | Default: 1 |
| Page size param | `per_page` | Max: 50 (current setting) |
| Response metadata | `total_pages`, `count` | In root response |
| Hard ceiling | 2,000 results | Use date range filters for larger sets |
| Rate limit | None documented | Courtesy delay: 0.5s between pages |

### Grants.gov API (Simpler)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Endpoint | `POST /api/search2` | No auth required |
| Pagination param | `page_offset` (1-indexed) inside `pagination` object | |
| Page size param | `page_size` | Max: 100, range: 1-100 |
| Response metadata | `pagination_info.total_pages`, `pagination_info.total_records` | |
| Hard ceiling | 10,000 results | Add filters to narrow |
| Rate limit | None documented | Courtesy delay: 0.3s between pages |

### Congress.gov API

| Parameter | Value | Notes |
|-----------|-------|-------|
| Endpoint | `GET /bill/{congress}` | API key required |
| Pagination param | `offset` (0-based) | Default: 0 |
| Page size param | `limit` | Max: 250 (currently using 50) |
| Response metadata | `pagination.count`, `pagination.next` | Follow `next` URL |
| Hard ceiling | None documented | All results accessible |
| Rate limit | 5,000 requests/hour | Generous for batch operations |

### USASpending API

| Parameter | Value | Notes |
|-----------|-------|-------|
| Endpoint | `POST /api/v2/search/spending_by_award/` | No auth required |
| Pagination param | `page` (1-indexed) | |
| Page size param | `limit` | |
| Response metadata | `page_metadata.hasNext`, `page_metadata.page`, `page_metadata.total` | |
| Existing pagination | YES (awards.py already paginates) | Verify only |

---

## Congress.gov Bill Detail Data Reference

### Available Sub-Endpoints

| Sub-Endpoint | URL Pattern | Key Fields | TCR Value |
|--------------|-------------|------------|-----------|
| Actions | `/bill/{c}/{type}/{num}/actions` | actionDate, text, type, sourceSystem | Track legislative progress |
| Cosponsors | `/bill/{c}/{type}/{num}/cosponsors` | count, bioguideId, fullName, party, state | Identify Tribal champions |
| Subjects | `/bill/{c}/{type}/{num}/subjects` | policyArea, legislativeSubjects | Improve relevance scoring |
| Summaries | `/bill/{c}/{type}/{num}/summaries` | text, actionDate, versionCode | Richer briefing content |
| Text | `/bill/{c}/{type}/{num}/text` | date, formats, type | Full text analysis (optional) |
| Titles | `/bill/{c}/{type}/{num}/titles` | title, titleType | Better display names |
| Committees | `/bill/{c}/{type}/{num}/committees` | name, chamber, activities | Track committee referrals |
| Related Bills | `/bill/{c}/{type}/{num}/relatedbills` | title, number, type, relationship | Cross-reference bills |

### Recommended Enrichment Priority

1. **Cosponsors** (highest value: identifies congressional champions)
2. **Subjects** (improves relevance scoring accuracy)
3. **Summaries** (enriches briefing content)
4. **Actions** (tracks legislative progress)
5. Committees (contextual value)
6. Related Bills (cross-reference value)
7. Titles (display improvement)
8. Text (full text is large; defer unless needed for keyword analysis)

---

## WCAG 2.1 AA Compliance Checklist (Relevant Criteria)

### Current Site Assessment

| Category | Criterion | Status | Issue | Fix |
|----------|-----------|--------|-------|-----|
| Perceivable | 1.3.1 Info & Relationships | PARTIAL | Missing skip navigation link | Add `<a class="skip-link" href="#tribe-search">Skip to search</a>` |
| Perceivable | 1.4.3 Contrast | UNKNOWN | Muted text (#6c757d on #f8f9fa) = 4.6:1 (passes AA) but verify all states | Audit all color combinations |
| Perceivable | 1.4.11 Non-text Contrast | PARTIAL | Button focus outlines use rgba(.3 opacity) | Verify 3:1 contrast for UI components |
| Operable | 2.1.1 Keyboard | PARTIAL | Awesomplete has keyboard support; verify "Download Both" sequential downloads | Test full keyboard flow |
| Operable | 2.4.1 Bypass Blocks | FAIL | No skip navigation link | Add skip link |
| Operable | 2.4.3 Focus Order | UNKNOWN | Need to verify tab order when card appears | Test tab sequence |
| Operable | 2.4.7 Focus Visible | PARTIAL | Has outline styles in CSS, but need to verify all elements | Audit all interactive elements |
| Robust | 4.1.2 Name/Role/Value | PARTIAL | Combobox role present, but aria-expanded not updated dynamically | Fix JS to toggle aria-expanded |

### Required Fixes (Minimum for Production)

1. Add skip navigation link (visible on focus)
2. Verify all color contrast ratios meet 4.5:1 (text) and 3:1 (UI components)
3. Ensure aria-expanded updates when Awesomplete dropdown opens/closes
4. Verify keyboard-only navigation works for: search -> select -> download
5. Ensure Escape key closes card and returns focus to search input (partially implemented)
6. Add aria-label to regional document section cards

---

## DOCX Visual QA Automation Reference

### Existing Quality Checks (quality_review.py)

| Check | Type | Severity | Status |
|-------|------|----------|--------|
| Audience leakage (19 patterns) | Text | Critical | IMPLEMENTED |
| Air gap violations (12 patterns) | Text | Critical | IMPLEMENTED |
| Placeholder detection (6 patterns) | Text | Warning | IMPLEMENTED |
| Confidential marking | Structural | Warning/Critical | IMPLEMENTED |
| Minimum paragraph count (20+) | Structural | Warning | IMPLEMENTED |
| Executive summary presence | Text | Warning | IMPLEMENTED |
| Page count estimation | Structural | Warning | IMPLEMENTED |

### Recommended Additional Checks (python-docx native)

| Check | Implementation | Severity | Complexity |
|-------|---------------|----------|------------|
| Heading hierarchy valid (H1->H2->H3) | Iterate paragraph.style.name, verify no H3 before H2 | Warning | Low |
| All tables have header row | Check table.rows[0] bold/style | Warning | Low |
| Font consistency (all body text same font) | Check run.font.name across paragraphs | Warning | Low |
| No empty sections (heading with no content before next heading) | Detect consecutive headings | Warning | Low |
| Table column count matches expected | Count table.columns per doc type | Warning | Medium |
| Style names in expected set | Verify paragraph.style.name against whitelist | Warning | Low |
| No orphaned runs (runs with no text) | Filter runs where text.strip() == "" | Info | Low |

### Tools Evaluated and Rejected

| Tool | Why Rejected |
|------|-------------|
| Aspose.Words for Python | Commercial license; overkill for structural checks |
| docx-compare (GitHub) | Designed for comparing two documents, not validating one against rules |
| LibreOffice CLI + screenshot comparison | Requires LibreOffice install; too complex for CI/CD pipeline |
| validocx (GitHub) | Validates style XML, not content structure |

**Recommendation:** Extend existing `DocumentQualityReviewer` with python-docx structural checks. No new dependencies needed. The existing python-docx library already provides access to paragraph styles, table dimensions, run fonts, and document structure. All new checks should be `warning` severity (not `critical`), since formatting issues do not affect content accuracy.

---

## SquareSpace Iframe Embedding Reference

### Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| SquareSpace Business plan or higher | REQUIRED | iframes disabled on Personal plans |
| title attribute on iframe | PRESENT | In existing embed comment, WCAG compliant |
| Responsive width | PRESENT | width="100%" in embed code |
| Fixed height | PRESENT | height="700" -- adequate for search + card + regions |
| Cross-origin downloads | NEEDS TESTING | DOCX download attribute may not work cross-origin |
| loading="lazy" | PRESENT | Defers iframe load until visible |

### Dynamic Height Resizing (Optional Enhancement)

If fixed height (700px) is insufficient (e.g., regional documents section extends below fold), implement postMessage-based resizing:

**In embedded page (index.html):**
```javascript
// Send height to parent on content change
function notifyHeight() {
  var height = document.body.scrollHeight;
  window.parent.postMessage({ type: 'resize', height: height }, '*');
}
// Call after card show, region render
```

**In SquareSpace code injection (or Code Block):**
```javascript
window.addEventListener('message', function(e) {
  if (e.data && e.data.type === 'resize') {
    document.querySelector('iframe').style.height = e.data.height + 'px';
  }
});
```

**Recommendation:** Start with fixed height (700px). Add postMessage resizing only if users report content being cut off. The current UI with search + card + 8 regions fits within 700px on desktop.

---

## Confidence Scoring Framework Reference

### Intelligence Community Standard (Adapted for TCR)

| Level | Label | Criteria for TCR | Display |
|-------|-------|-----------------|---------|
| HIGH | High Confidence | 3+ data sources present (awards + hazards + congressional); data < 30 days old; no placeholder warnings | Green indicator |
| MODERATE | Moderate Confidence | 2 data sources present; data < 60 days old; some placeholder warnings | Yellow indicator |
| LOW | Low Confidence | 1 or fewer data sources; data > 60 days old; significant placeholders | Red indicator or "Limited Data" label |

### Per-Section Scoring

| Document Section | Confidence Inputs | Weight |
|-----------------|-------------------|--------|
| Funding Landscape | USASpending award count, CFDA match count | 30% |
| Hazard Profile | NRI data completeness, USFS override availability | 25% |
| Legislative Outlook | Congress.gov bill count, cosponsor data richness | 20% |
| Economic Impact | Award total, multiplier confidence | 15% |
| Strategic Recommendations | Composite of all above | 10% |

### Implementation Approach

```python
def compute_confidence(tribe_context: dict) -> str:
    """Compute confidence level for a Tribe's advocacy packet."""
    score = 0
    # Source count
    if tribe_context.get("awards"): score += 30
    if tribe_context.get("hazards"): score += 25
    if tribe_context.get("congressional"): score += 20
    if tribe_context.get("economic_impact"): score += 15
    # Freshness
    if data_age_days < 30: score += 10
    elif data_age_days < 60: score += 5

    if score >= 80: return "HIGH"
    elif score >= 50: return "MODERATE"
    else: return "LOW"
```

---

## Sources

### HIGH Confidence (Official Documentation)

- [Federal Register API Documentation](https://www.federalregister.gov/developers/documentation/api/v1) -- pagination parameters, field selection, rate limits
- [Congress.gov API Bill Endpoint](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/BillEndpoint.md) -- sub-endpoints, data fields, pagination structure
- [Congress.gov API GitHub Repository](https://github.com/LibraryOfCongress/api.congress.gov) -- v3 API documentation, rate limits
- [Grants.gov Simpler API - Search Opportunities](https://wiki.simpler.grants.gov/product/api/search-opportunities) -- pagination parameters, 10K ceiling, response structure
- [ADA Title II Web Accessibility Requirements](https://www.ada.gov/resources/2024-03-08-web-rule/) -- WCAG 2.1 AA requirement, April 2026 deadline
- [Squarespace Embed Blocks Help](https://support.squarespace.com/hc/en-us/articles/206543617-Embed-blocks) -- iframe support, plan requirements
- [WCAG 2.1 AA Focus Management](https://www.a11y-collective.com/blog/modal-accessibility/) -- dialog patterns, focus trap, keyboard navigation
- [python-docx Styles Documentation](https://python-docx.readthedocs.io/en/latest/user/styles-using.html) -- style objects, heading validation

### MEDIUM Confidence (Verified Community Sources)

- [CIS Words of Estimative Probability](https://www.cisecurity.org/ms-isac/services/words-of-estimative-probability-analytic-confidences-and-structured-analytic-techniques) -- confidence level definitions, analytic standards
- [Analytic Confidence - Wikipedia](https://en.wikipedia.org/wiki/Analytic_confidence) -- HIGH/MODERATE/LOW framework, ICD 203 reference
- [OpenCTI Reliability and Confidence](https://docs.opencti.io/latest/usage/reliability-confidence/) -- open-source confidence scoring taxonomy
- [MISP Estimative Language](https://github.com/MISP/best-practices-in-threat-intelligence/blob/master/best-practices/expressing-confidence.adoc) -- standardized confidence tags
- [GitHub Pages Performance (Fastly CDN)](https://www.fastly.com/customers/github) -- CDN infrastructure, global distribution
- [SquareSpace iframe Responsive Resize](https://forum.squarespace.com/topic/191637-resizing-iframe-in-squarespace-to-match-window-height-dynamically/) -- postMessage pattern for dynamic height

### LOW Confidence (Single Source / Unverified)

- DOCX visual regression testing landscape -- limited tooling found; recommendation to extend existing python-docx checks is based on capability assessment rather than established best practice
- Download analytics for GitHub Pages -- client-side only; no server-side analytics possible; approach based on platform limitations rather than proven pattern

### Direct Code Verification (Highest Confidence)

- `F:/tcr-policy-scanner/src/scrapers/congress_gov.py` -- current pagination: single page (limit=50), no offset loop
- `F:/tcr-policy-scanner/src/scrapers/federal_register.py` -- current pagination: single page (per_page=50), no page parameter
- `F:/tcr-policy-scanner/src/scrapers/grants_gov.py` -- current pagination: single page (rows=25/50), no page_offset
- `F:/tcr-policy-scanner/src/packets/quality_review.py` -- 7 existing checks, extensible architecture
- `F:/tcr-policy-scanner/docs/web/index.html` -- current HTML structure, ARIA attributes, embed comment
- `F:/tcr-policy-scanner/docs/web/js/app.js` -- current JS functionality, Awesomplete integration
- `F:/tcr-policy-scanner/docs/web/css/style.css` -- current CSS, color values, responsive design

---

*Research completed: 2026-02-12*
*Mode: Ecosystem (Feature Landscape)*
*Ready for requirements definition: YES*
