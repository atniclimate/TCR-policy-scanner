# Architecture Patterns: v1.3 Production Launch Integration

**Domain:** Tribal Climate Resilience policy intelligence pipeline -- production deployment
**Researched:** 2026-02-12
**Confidence:** HIGH (based on direct codebase inspection + verified external sources)

---

## System Overview: Current State (v1.2)

```
                              EXISTING ARCHITECTURE
                              ====================

Pipeline Plane (Python 3.12 async)
===================================
                                                          outputs/
  4 Scrapers ──> Normalize ──> Graph ──> 5 Monitors ──>  LATEST-RESULTS.json
  (Fed Reg,      (standard     Builder   (IIJA,           LATEST-GRAPH.json
   Grants.gov,    schema)                 Reconciliation,  LATEST-MONITOR-DATA.json
   Congress.gov,                          DHS, Tribal      .ci_history.json
   USASpending)                           Consult, Hot     archive/
                                          Sheets)
                                              |
                                         Decision Engine
                                         (5 rules)
                                              |
                                         14-section Briefing


Packet Plane (Python 3.12 synchronous)
=======================================
  CLI (--prep-packets)
       |
       v
  PacketOrchestrator
       |
       +---> TribalRegistry (592 Tribes from tribal_registry.json)
       +---> CongressionalMapper (congressional_cache.json)
       +---> EcoregionMapper (ecoregion_config.json)
       +---> Award cache (592 JSON files, data/award_cache/)
       +---> Hazard profiles (592 JSON files, data/hazard_profiles/)
       +---> EconomicImpactCalculator
       +---> ProgramRelevanceFilter (8-12 programs per Tribe)
       +---> DocxEngine + StyleManager + HotSheetRenderer
       |
       v
  outputs/packets/
       +-- internal/          (Doc A: 384 per-Tribe DOCX)
       +-- congressional/     (Doc B: 592 per-Tribe DOCX)
       +-- regional/internal/ (Doc C: 8 regional DOCX)
       +-- regional/congressional/ (Doc D: 8 regional DOCX)
       +-- STRATEGIC-OVERVIEW.docx

Distribution Plane (Static Files)
==================================
  build_web_index.py ──> docs/web/data/tribes.json
                              |
  generate-packets.yml ──> docs/web/tribes/{internal,congressional,regional}/
                              |
  GitHub Pages ──> atniclimate.github.io/TCR-policy-scanner/
                              |
  SquareSpace ──> <iframe> embed (existing search widget: 15KB vanilla JS)
```

---

## System Overview: v1.3 Target State

```
                              v1.3 ARCHITECTURE
                              =================

Pipeline Plane (MODIFIED)
==========================
  4 Scrapers ──> Normalize ──> Graph ──> Monitors ──> Decision Engine ──> Briefing
       |
       +-- [NEW] Pagination loops in FederalRegister, GrantsGov, CongressGov
       +-- [NEW] Congress.gov bill detail fetching (second API call per bill)
       +-- [EXISTING] USASpending already paginates correctly


Packet Plane (MODIFIED)
=========================
  PacketOrchestrator
       |
       +---> [NEW] ConfidenceScorer (computes per-section confidence)
       |         |
       |         +-- data_completeness (award count, hazard source count)
       |         +-- data_recency (cache age vs generation time)
       |         +-- source_diversity (number of distinct API sources)
       |         +-- match_confidence (fuzzy match scores from registry/awards)
       |
       +---> DocxEngine
       |         |
       |         +-- [NEW] Confidence badges in section headers
       |         +-- [NEW] Source citations per data point
       |
       v
  outputs/packets/ (unchanged structure)


Distribution Plane (REPLACED for website, EXTENDED for serving)
================================================================
  [EXISTING] build_web_index.py ──> tribes.json (manifest)
       |
  [EXISTING] generate-packets.yml
       +-- [MODIFIED] copies DOCX to docs/web/tribes/
       +-- [NEW] builds manifest.json with tribe->URL mapping
       +-- [CONDITIONAL] optionally publishes to GitHub Releases
       |
  [REPLACED] React+Vite website (from .planning/website/)
       |    replaces vanilla JS widget at docs/web/
       |    must be built and output placed into docs/web/
       |
  [EXISTING] GitHub Pages ──> serves both website + DOCX files
       |
  [EXISTING] SquareSpace ──> <iframe> embed
       |    must include sandbox="allow-downloads allow-same-origin allow-scripts"


QA Automation Plane (NEW)
===========================
  [NEW] qa_screenshot.py
       |
       +---> LibreOffice headless: DOCX --> PDF
       +---> Playwright: PDF --> page screenshots (PNG)
       +---> HTML gallery for visual review
       |
  outputs/docx_qa/
       +-- structural_audit.json
       +-- visual_samples/{tribe}/{doc_type}/page_{n}.png
       +-- visual_gallery.html
```

---

## Component Responsibilities

### Existing Components (Modified)

| Component | Current Responsibility | v1.3 Modification | Files Affected |
|-----------|----------------------|-------------------|----------------|
| `BaseScraper` | Retry + circuit breaker | No changes needed -- subclasses add pagination | `src/scrapers/base.py` (unchanged) |
| `FederalRegisterScraper` | Single-page fetch (per_page=50) | Add pagination loop using `next_page_url` from response | `src/scrapers/federal_register.py` |
| `GrantsGovScraper` | Single-page fetch (rows=25/50) | Add pagination using `offset` parameter | `src/scrapers/grants_gov.py` |
| `CongressGovScraper` | Single-page fetch (limit=50) | Add pagination using `offset` parameter; add bill detail fetch | `src/scrapers/congress_gov.py` |
| `PacketOrchestrator` | Assemble context + generate DOCX | Integrate confidence scorer into context | `src/packets/orchestrator.py` |
| `DocxEngine` | Render DOCX sections | Add confidence badge rendering, source citations | `src/packets/docx_engine.py`, `src/packets/docx_sections.py` |
| `build_web_index.py` | Generate tribes.json | Already supports all 4 doc types; may need URL format changes | `scripts/build_web_index.py` |
| `generate-packets.yml` | Weekly packet generation | Add manifest.json build step, DOCX deployment verification | `.github/workflows/generate-packets.yml` |

### New Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `ConfidenceScorer` | Compute per-section confidence levels based on data completeness, recency, and source diversity | `src/packets/confidence.py` (new) |
| `qa_screenshot.py` | DOCX-to-PDF-to-screenshot pipeline for visual QA | `scripts/qa_screenshot.py` (new) |
| React website | Production frontend replacing vanilla JS widget | `.planning/website/` --> built output to `docs/web/` |
| `manifest.json` | Machine-readable mapping of Tribe ID to DOCX download URLs | Generated by `build_web_index.py` (enhancement, not new file) |

---

## Integration Point Analysis

### 1. Scraper Pagination Integration

**Current state:** Three of four scrapers silently truncate results at 50 items. Only USASpending paginates correctly (via `page_metadata.hasNext`).

**Integration pattern:** Pagination loops inside each scraper's `_search` methods, following the existing `BaseScraper._request_with_retry` pattern.

```
FederalRegisterScraper._search()
  CURRENT:  Single request, per_page=50, return results
  TARGET:   Loop while response has next_page_url or count > offset
            Federal Register API returns total_count and supports page=N param
            Cap at 2000 results (API hard limit per their docs)

GrantsGovScraper._search_cfda() / _search()
  CURRENT:  Single request, rows=25/50, return oppHits
  TARGET:   Loop with incrementing offset param
            Grants.gov search2 API supports startRecordNum/rows pagination
            Stop when oppHits < rows (last page)

CongressGovScraper._search_congress() / _search()
  CURRENT:  Single request, limit=50, return bills
  TARGET:   Loop using offset parameter (default 0, increment by limit)
            Congress.gov API supports offset (starting record) up to 250 per page
            Response includes pagination.next URL when more results exist
            Stop when pagination.next is absent
```

**Design constraint:** All pagination loops MUST respect the existing circuit breaker. The circuit breaker wraps the retry loop in `BaseScraper._request_with_retry`, so each paginated request naturally gets retry protection. No changes to `base.py` needed.

**Design constraint:** Rate limiting between paginated requests. Each scraper already has `asyncio.sleep(0.3-0.5)` between queries. Pagination loops should add the same inter-page delay.

**Estimated scope:** 3 files modified, ~30-50 lines per scraper. Low risk because USASpending already demonstrates the correct pattern.

### 2. Website Deployment Architecture

**Current state:** A 15KB vanilla JS widget at `docs/web/` with Awesomplete autocomplete. Served via GitHub Pages at `atniclimate.github.io/TCR-policy-scanner/`. Embeddable in SquareSpace via iframe.

**Draft state:** A React+Vite+Tailwind+shadcn/ui application in `.planning/website/` with 47 known issues including fake downloads (text blobs, not real DOCX) and mock data (46 Tribes / 29 fake regions instead of 592 / 8).

**Integration architecture:**

```
Build Pipeline:
  .planning/website/src/  --[vite build]--> docs/web/  (replaces vanilla widget)

Data Pipeline:
  tribal_registry.json + outputs/packets/ --[build_web_index.py]--> docs/web/data/tribes.json

DOCX Serving:
  outputs/packets/{internal,congressional,regional}/ --[cp]--> docs/web/tribes/

GitHub Pages Deployment:
  docs/web/ --[git push]--> GitHub Pages CDN --[HTTPS]--> atniclimate.github.io

SquareSpace Integration:
  <iframe src="https://atniclimate.github.io/TCR-policy-scanner/"
          sandbox="allow-scripts allow-same-origin allow-downloads allow-popups"
          width="100%" height="700">
```

**Critical architectural decisions:**

**Decision 1: GitHub Pages serves DOCX directly (not GitHub Releases).**
- Rationale: The existing `generate-packets.yml` already copies DOCX files to `docs/web/tribes/`. This pipeline works. GitHub Releases would add complexity (API calls to create releases, different URL patterns) for no benefit.
- GitHub Pages serves .docx with correct MIME type (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`) via mime-db.
- CORS: GitHub Pages sets `Access-Control-Allow-Origin: *` on public repos, so SquareSpace iframe can fetch files.
- Confidence: HIGH (verified against GitHub community discussions on CORS behavior for public Pages).

**Decision 2: React app builds into `docs/web/` replacing vanilla widget.**
- Rationale: The Vite build output goes to a `build/` directory by default. Configure `vite.config.ts` to output to `../../docs/web/` (relative to `.planning/website/`), or use a build script that copies.
- The React app replaces `index.html`, `js/`, `css/` but must NOT clobber `data/tribes.json` or `tribes/` (DOCX files).
- Build artifacts: The React app is a SPA. Vite outputs `index.html` + `assets/` with hashed filenames.

**Decision 3: SquareSpace iframe MUST use `allow-downloads` sandbox attribute.**
- The iframe `sandbox` attribute controls what the embedded content can do. Without `allow-downloads`, Chrome blocks file downloads from within the iframe.
- Required: `sandbox="allow-scripts allow-same-origin allow-downloads allow-popups"`
- Without `allow-same-origin`, the iframe cannot read `tribes.json` from the same origin.
- Confidence: HIGH (verified via MDN and caniuse.com for `allow-downloads` browser support).

**Decision 4: React app fetches `data/tribes.json` at runtime, not at build time.**
- The mock data in `mockData.ts` (46 fake Tribes, 29 fake regions) must be replaced with a runtime `fetch('/data/tribes.json')` call.
- This decouples the website build from the packet generation. The website can be built once and deployed, then `tribes.json` and DOCX files update independently via `generate-packets.yml`.

### 3. DOCX Serving Pipeline

**Data flow:**

```
Pipeline generates:
  outputs/packets/internal/{tribe_id}.docx        (384 files)
  outputs/packets/congressional/{tribe_id}.docx   (592 files)
  outputs/packets/regional/internal/{region}.docx  (8 files)
  outputs/packets/regional/congressional/{region}.docx (8 files)

build_web_index.py generates:
  docs/web/data/tribes.json
    {
      tribes: [
        {
          id: "epa_123",
          name: "Navajo Nation",
          states: ["AZ", "NM", "UT"],
          ecoregion: "southwest",
          documents: {
            internal_strategy: "internal/epa_123.docx",
            congressional_overview: "congressional/epa_123.docx"
          },
          has_complete_data: true
        }, ...
      ],
      regions: [
        {
          region_id: "southwest",
          region_name: "Southwest",
          documents: {
            internal_strategy: "regional/internal/southwest.docx",
            congressional_overview: "regional/congressional/southwest.docx"
          }
        }, ...
      ]
    }

generate-packets.yml copies DOCX to:
  docs/web/tribes/internal/{tribe_id}.docx
  docs/web/tribes/congressional/{tribe_id}.docx
  docs/web/tribes/regional/internal/{region}.docx
  docs/web/tribes/regional/congressional/{region}.docx

React app downloads from:
  https://atniclimate.github.io/TCR-policy-scanner/tribes/internal/{tribe_id}.docx
  (relative URL: tribes/internal/{tribe_id}.docx from app root)
```

**The tribes.json IS the manifest.** No separate `manifest.json` file is needed. The existing `build_web_index.py` already generates the mapping of Tribe ID to relative document paths. The React app loads `tribes.json`, finds the matching Tribe, and constructs the download URL from the `documents` object.

**Repository size concern:** 992 DOCX files committed to `docs/web/tribes/`. Typical DOCX size is 30-80 KB. Total: ~30-80 MB. This is within GitHub's recommended repository size (stay under 1 GB). If sizes grow, consider `.gitattributes` with Git LFS for `*.docx` files, but this is not needed at current scale.

### 4. Confidence Scoring Integration

**Current state:** The decision engine already produces `confidence` fields ("HIGH", "MEDIUM", "LOW") per program classification. The relevance scorer produces `score_breakdown` with 5 factor scores. However, there is no per-section confidence scoring in the DOCX packets.

**Architecture for confidence scoring:**

```
New module: src/packets/confidence.py

class ConfidenceScorer:
    def score_tribe_context(self, context: TribePacketContext) -> dict:
        """Compute per-section confidence levels."""
        return {
            "overall": self._overall_confidence(context),
            "congressional": self._congressional_confidence(context),
            "awards": self._awards_confidence(context),
            "hazards": self._hazard_confidence(context),
            "economic": self._economic_confidence(context),
        }

    def _awards_confidence(self, context) -> dict:
        """Score based on:
        - Has any awards? (base requirement)
        - Award cache age (days since last population)
        - Number of matched programs
        - Match method (exact alias vs fuzzy -- from match metadata)
        """
        ...

    def _hazard_confidence(self, context) -> dict:
        """Score based on:
        - FEMA NRI data present?
        - USFS wildfire data present?
        - Number of counties in area-weighted crosswalk
        - Composite risk score populated?
        """
        ...
```

**Integration points:**

1. `PacketOrchestrator._build_context()` -- Compute confidence AFTER assembling context, BEFORE DOCX generation. Store in `context.confidence_scores`.
2. `TribePacketContext` dataclass -- Add `confidence_scores: dict = field(default_factory=dict)` field.
3. `DocxEngine.generate()` / `docx_sections.py` -- Render confidence indicators in section headers (e.g., "Data Confidence: HIGH" in small text below section title).
4. `tribes.json` -- Optionally expose overall confidence in the web index so the React app can display it.

**Design constraint:** Confidence scoring must NOT require any API calls. All data needed is already in the TribePacketContext (awards list, hazard_profile dict, delegation lists). This is purely a computation on already-cached data.

**Suggested confidence levels:**

| Level | Meaning | Visual |
|-------|---------|--------|
| HIGH | Multiple verified data sources, recent data, exact matches | Green indicator or no badge (default) |
| MEDIUM | Some data available, some gaps, or data older than 30 days | Yellow indicator |
| LOW | Minimal data, many gaps, or data older than 90 days | Orange indicator with disclaimer |
| INSUFFICIENT | Critical data missing | Red indicator, section renders with "Data Unavailable" |

### 5. QA Automation Integration

**Pipeline:**

```
DOCX files (outputs/packets/)
      |
      v
LibreOffice headless (soffice --headless --convert-to pdf)
      |
      v
PDF files (outputs/docx_qa/pdfs/)
      |
      v
Playwright (pdf.goto('file:///...') + page.screenshot())
      |
      v
PNG screenshots (outputs/docx_qa/visual_samples/{tribe}/{doc_type}/page_{n}.png)
      |
      v
HTML gallery (outputs/docx_qa/visual_gallery.html)
```

**Integration with existing architecture:**

- QA automation is a READ-ONLY consumer of the packet output. It does not modify any source files or pipeline components.
- It runs AFTER `generate-packets.yml` completes (or after local `--prep-packets` run).
- LibreOffice must be installed (available in GitHub Actions `ubuntu-latest` via `apt-get install libreoffice`).
- Playwright requires `npx playwright install chromium` (or use the Python `playwright` package).

**Structural validation script:**

```python
# scripts/validate_docx_structure.py
# Reads every DOCX in outputs/packets/ and checks:
# - Expected heading hierarchy per doc type (A/B/C/D)
# - Tables have data (no empty cells where expected)
# - No placeholder text ("TODO", "TBD", "PLACEHOLDER", "INSERT")
# - Font consistency (Lexend body, League Spartan headings)
# - Tribal Nation name in title/header
# Output: outputs/docx_qa/structural_audit.json
```

This script uses `python-docx` (already a dependency) to inspect document structure programmatically. No new dependencies required for structural validation.

---

## Architectural Patterns

### Pattern 1: Cache-First, Zero-API Document Generation

**What:** All data needed for DOCX generation is pre-cached in JSON files. The PacketOrchestrator makes zero API calls during document construction.

**Why this matters for v1.3:** Confidence scoring and source citations can be computed purely from cached data. No need to add API calls to the rendering pipeline.

**Implication:** Any new data source (e.g., bill detail text from Congress.gov) must be cached BEFORE DOCX generation, not fetched during rendering.

### Pattern 2: Atomic File Writes

**What:** Both the pipeline and packet generator use temp files + `os.replace()` for atomic writes. Prevents corruption from interrupted writes.

**Already implemented in:** `build_web_index.py`, `PacketOrchestrator._generate_regional_doc()`, CFDA tracker save.

**Implication:** New file generation (manifest, QA reports) should follow the same pattern.

### Pattern 3: BaseScraper Inheritance for Resilience

**What:** All scrapers inherit `BaseScraper` which provides retry, circuit breaker, and rate limiting. Scraper subclasses only implement business logic.

**Implication for pagination:** Pagination loops call `self._request_with_retry()` for each page, getting retry + circuit breaker protection for free. No changes to `BaseScraper` needed.

### Pattern 4: Config-Driven Behavior

**What:** Scanner behavior is configured via `config/scanner_config.json`, not hardcoded. Scoring weights, scan windows, source URLs are all configurable.

**Implication:** Pagination limits, confidence thresholds, and QA parameters should also be config-driven rather than magic numbers.

### Pattern 5: Centralized Path Constants

**What:** All file paths are defined in `src/paths.py` (25 constants). No ad-hoc `Path(...)` construction in business logic.

**Implication:** New paths for confidence scoring output, QA output, or manifest files must be added to `src/paths.py`. New paths needed:

```python
# Suggested additions to src/paths.py
QA_OUTPUT_DIR: Path = OUTPUTS_DIR / "docx_qa"
MANIFEST_PATH: Path = WEB_DATA_DIR / "manifest.json"  # if separate from tribes.json
```

---

## Data Flow Changes for v1.3

### Scraper Data Flow (Modified)

```
BEFORE (v1.2):
  FederalRegister._search(query) --> 1 request, max 50 results
  GrantsGov._search_cfda(cfda) --> 1 request, max 25 results
  CongressGov._search_congress(term) --> 1 request, max 50 results

AFTER (v1.3):
  FederalRegister._search(query) --> N requests, up to 2000 results (API limit)
  GrantsGov._search_cfda(cfda) --> N requests, until oppHits < rows
  CongressGov._search_congress(term) --> N requests, until no pagination.next
  CongressGov._fetch_bill_detail(bill_url) --> 1 request per bill (NEW)
```

### Confidence Data Flow (New)

```
  TribePacketContext (assembled)
       |
       v
  ConfidenceScorer.score_tribe_context()
       |
       v
  context.confidence_scores = {
    "overall": "HIGH",
    "sections": {
      "congressional": {"level": "HIGH", "factors": {...}},
      "awards": {"level": "MEDIUM", "factors": {"count": 3, "recency_days": 45}},
      "hazards": {"level": "HIGH", "factors": {"nri": true, "usfs": true}},
      "economic": {"level": "MEDIUM", "factors": {"multiplier_source": "published"}}
    }
  }
       |
       v
  DocxEngine renders confidence badges per section
```

### Website Data Flow (New)

```
  [Build time -- one-time or per-release]
  .planning/website/src/ --[npm run build]--> docs/web/ (HTML+JS+CSS)

  [Weekly -- generate-packets.yml]
  Pipeline generates DOCX --> outputs/packets/
  build_web_index.py --> docs/web/data/tribes.json
  cp DOCX files --> docs/web/tribes/
  git push --> GitHub Pages auto-deploys

  [Runtime -- user visits website]
  Browser loads SPA from GitHub Pages
  SPA fetches /data/tribes.json (relative URL)
  User searches, selects Tribe
  SPA constructs download URL: /tribes/{doc_type}/{tribe_id}.docx
  Browser downloads DOCX via standard <a download> mechanism
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Building DOCX URLs at Build Time

**What:** Hardcoding absolute URLs (e.g., `https://atniclimate.github.io/TCR-policy-scanner/tribes/...`) in the React app source code.

**Why bad:** Makes the app non-portable. Cannot test locally or in staging. URL changes break the app.

**Instead:** Use relative URLs. The React app and DOCX files are co-hosted on the same GitHub Pages domain. Use `tribes/internal/{tribe_id}.docx` as a relative URL.

### Anti-Pattern 2: Generating DOCX Inside the Website Build

**What:** Having the Vite build process invoke Python to generate DOCX files.

**Why bad:** Couples the website build to the Python pipeline. The React app should be a pure static frontend that consumes pre-generated data.

**Instead:** Keep the pipeline and website as separate build stages. The `generate-packets.yml` workflow handles DOCX generation and deployment. The website build only produces HTML/JS/CSS.

### Anti-Pattern 3: Fetching Tribe Data from GitHub API

**What:** Using the GitHub API (or REST calls to the raw content API) to fetch tribes.json or DOCX files instead of serving from GitHub Pages.

**Why bad:** GitHub API has rate limits (60/hour unauthenticated). 200 concurrent users would exhaust limits immediately.

**Instead:** Serve everything as static files via GitHub Pages CDN. No API calls. No rate limits on static file serving.

### Anti-Pattern 4: Storing DOCX in GitHub Releases for Download

**What:** Using GitHub Releases as the DOCX distribution mechanism instead of GitHub Pages.

**Why bad:** Release asset download URLs are GitHub API endpoints with rate limiting. GitHub Pages is a CDN designed for static file serving. Releases also require API calls to create, adding complexity to the workflow.

**Instead:** Keep DOCX files in `docs/web/tribes/` and serve via GitHub Pages. Simpler pipeline, better performance.

### Anti-Pattern 5: Per-Request Confidence Computation in the Website

**What:** Computing confidence scores in the React frontend by analyzing tribes.json metadata.

**Why bad:** Confidence scoring requires access to cache file metadata (ages, match scores) that should not be exposed to the frontend. Duplicates logic between Python and TypeScript.

**Instead:** Compute confidence in Python during DOCX generation. Include the result in tribes.json as a simple string field ("HIGH"/"MEDIUM"/"LOW") for display purposes only.

---

## Scaling Considerations

| Concern | Current (v1.2) | v1.3 Target (100-200 users) | Future (1000+ users) |
|---------|----------------|----------------------------|---------------------|
| DOCX file serving | GitHub Pages CDN | GitHub Pages CDN (sufficient) | Consider external CDN or blob storage |
| tribes.json size | ~150 KB (592 Tribes) | ~200 KB with confidence fields | Acceptable; could split by region if needed |
| Repository size | ~50 MB with 992 DOCX | ~80 MB after re-generation | Git LFS for *.docx if exceeds 500 MB |
| Scraper API limits | ~100 requests/scan | ~300-500 requests/scan (with pagination) | Add request pooling, consider caching |
| DOCX generation time | ~5 min for 992 docs | ~5-6 min (confidence adds ~10%) | Parallelize across regions |
| GitHub Actions minutes | ~10 min/week | ~15 min/week | Within free tier limits |

---

## Suggested Build Order

Based on dependency analysis of integration points:

### Phase 1: Scraper Pagination (Foundation -- no downstream dependencies)

**Rationale:** Pagination fixes are independent of all other v1.3 features. They improve data quality which benefits every downstream component. Fix data input before improving data output.

**Scope:**
- Modify 3 scraper files (federal_register.py, grants_gov.py, congress_gov.py)
- Add Congress.gov bill detail fetching
- Test with live APIs
- No changes to base.py, orchestrator, or website

### Phase 2: Confidence Scoring (Depends on: accurate data from Phase 1)

**Rationale:** Confidence scoring is a computation layer between data assembly and DOCX rendering. Build it before modifying the DocxEngine to render badges.

**Scope:**
- New file: src/packets/confidence.py
- Modify: TribePacketContext (add field)
- Modify: PacketOrchestrator (integrate scorer)
- Tests for confidence computation

### Phase 3: DOCX Quality (Depends on: confidence scoring from Phase 2)

**Rationale:** DOCX improvements (confidence badges, source citations, visual fixes) should happen BEFORE the website ships them to users.

**Scope:**
- Modify: docx_engine.py, docx_sections.py (render confidence)
- New: scripts/qa_screenshot.py (visual QA automation)
- New: scripts/validate_docx_structure.py (structural validation)
- Run full re-generation, inspect output

### Phase 4: Website Launch (Depends on: verified DOCX from Phase 3)

**Rationale:** The website is a delivery mechanism for DOCX packets. Launch it only after packets are verified correct.

**Scope:**
- Fix 47 known issues in .planning/website/
- Replace mockData.ts with runtime tribes.json fetch
- Replace fake download handler with real DOCX URL construction
- Build React app to docs/web/ (replacing vanilla widget)
- Configure SquareSpace iframe with sandbox attributes
- Test end-to-end: search -> select -> download -> open DOCX

### Phase 5: Production Hardening (Depends on: deployed website from Phase 4)

**Rationale:** Stress testing requires a deployed system to test against.

**Scope:**
- Bug hunt agent swarm against live deployment
- Merge-sort QA strategy (atomic -> pairs -> chains -> stress)
- Performance testing (200 concurrent users simulation)
- Final go/no-go decision

---

## Integration Points Summary

| Integration Point | Upstream Component | Downstream Component | Data Format | Confidence |
|-------------------|--------------------|---------------------|-------------|------------|
| Scraper pagination | 3 scraper subclasses | Normalize (existing) | list[dict] -- same schema | HIGH |
| Bill detail fetch | CongressGovScraper | Normalize + DOCX rendering | Added `bill_text` field to normalized dict | MEDIUM |
| Confidence scoring | TribePacketContext | DocxEngine + tribes.json | `dict` with levels per section | HIGH |
| DOCX -> GitHub Pages | generate-packets.yml | React app download handler | .docx files at relative URLs | HIGH |
| tribes.json manifest | build_web_index.py | React app TribeSelector/RegionSelector | JSON with documents.{type}: path | HIGH |
| React app -> docs/web/ | Vite build | GitHub Pages deployment | Static HTML+JS+CSS assets | HIGH |
| iframe embed | GitHub Pages | SquareSpace Code Block | `<iframe>` with sandbox attrs | HIGH |
| QA screenshots | LibreOffice + Playwright | Human review via HTML gallery | PNG images in gallery HTML | HIGH |

---

## Project Structure: Key Files for v1.3

```
F:\tcr-policy-scanner\
|
+-- src/
|   +-- scrapers/
|   |   +-- base.py              (unchanged -- BaseScraper + CircuitBreaker)
|   |   +-- federal_register.py  (MODIFIED -- add pagination loop)
|   |   +-- grants_gov.py        (MODIFIED -- add pagination loop)
|   |   +-- congress_gov.py      (MODIFIED -- add pagination + bill detail)
|   |   +-- usaspending.py       (unchanged -- already paginates)
|   |
|   +-- packets/
|   |   +-- orchestrator.py      (MODIFIED -- integrate ConfidenceScorer)
|   |   +-- context.py           (MODIFIED -- add confidence_scores field)
|   |   +-- confidence.py        (NEW -- ConfidenceScorer class)
|   |   +-- docx_engine.py       (MODIFIED -- render confidence badges)
|   |   +-- docx_sections.py     (MODIFIED -- confidence in section headers)
|   |   +-- (all others unchanged)
|   |
|   +-- paths.py                 (MODIFIED -- add QA_OUTPUT_DIR)
|
+-- scripts/
|   +-- build_web_index.py       (MODIFIED -- add confidence to index)
|   +-- validate_docx_structure.py (NEW -- structural DOCX validation)
|   +-- qa_screenshot.py         (NEW -- DOCX->PDF->PNG pipeline)
|
+-- .github/workflows/
|   +-- daily-scan.yml           (unchanged)
|   +-- generate-packets.yml     (MODIFIED -- add website build step)
|
+-- .planning/website/           (draft React app -- to be fixed then built)
|   +-- src/
|   |   +-- data/mockData.ts     (DELETED -- replaced with runtime fetch)
|   |   +-- components/TribeSelector.tsx  (MODIFIED -- real download)
|   |   +-- components/RegionSelector.tsx (MODIFIED -- real download)
|   +-- vite.config.ts           (MODIFIED -- clean up aliases, output dir)
|   +-- package.json             (MODIFIED -- remove unused deps)
|
+-- docs/web/                    (GitHub Pages served directory)
|   +-- index.html               (REPLACED by React build output)
|   +-- assets/                  (NEW from Vite build)
|   +-- data/tribes.json         (existing, updated weekly)
|   +-- tribes/                  (existing DOCX files)
|
+-- outputs/
    +-- packets/                 (existing DOCX output)
    +-- docx_qa/                 (NEW -- QA automation output)
```

---

## Sources

**Direct codebase inspection (HIGH confidence):**
- `src/scrapers/base.py` -- BaseScraper pattern, circuit breaker integration
- `src/scrapers/federal_register.py` -- Current pagination (per_page=50, no loop)
- `src/scrapers/grants_gov.py` -- Current pagination (rows=25, no loop)
- `src/scrapers/congress_gov.py` -- Current pagination (limit=50, no loop)
- `src/scrapers/usaspending.py` -- Correct pagination pattern (page_metadata.hasNext)
- `src/packets/orchestrator.py` -- PacketOrchestrator assembly + generation flow
- `src/packets/context.py` -- TribePacketContext dataclass
- `src/paths.py` -- 25 centralized path constants
- `scripts/build_web_index.py` -- Existing manifest generation
- `.github/workflows/generate-packets.yml` -- Existing DOCX deployment pipeline
- `docs/web/index.html` -- Existing vanilla JS widget
- `.planning/website/src/` -- Draft React app with mock data

**Verified external sources (MEDIUM-HIGH confidence):**
- [GitHub Pages CORS discussion](https://github.com/orgs/community/discussions/22399) -- Access-Control-Allow-Origin: * for public repos
- [GitHub Pages CORS headers limitation](https://github.com/orgs/community/discussions/157852) -- No custom header configuration
- [GitHub MIME types on Pages](https://help.github.com/en/articles/mime-types-on-github-pages) -- mime-db based, supports 750+ MIME types
- [iframe sandbox allow-downloads (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe) -- Required for download from sandboxed iframe
- [iframe sandbox allow-downloads (caniuse)](https://caniuse.com/mdn-html_elements_iframe_sandbox_allow-downloads) -- Browser support verification
- [SquareSpace iframe embedding guide](https://www.silvabokis.com/squarespace-coding-customization/how-to-embed-an-iframe-on-squarespace) -- Code block approach for iframe
- [Congress.gov API pagination](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/README.md) -- offset + limit, up to 250 per page, pagination.next
- [Federal Register API](https://www.federalregister.gov/reader-aids/developer-resources/rest-api) -- per_page, page parameter, 2000 result limit
- [LibreOffice headless DOCX->PDF](https://michalzalecki.com/converting-docx-to-pdf-using-python/) -- soffice --headless --convert-to pdf

---

*Architecture research completed 2026-02-12. Findings based on direct inspection of 95 Python source files, 2 GitHub Actions workflows, and the draft React website code.*
