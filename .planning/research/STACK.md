# Technology Stack: v1.3 Production Launch

**Project:** TCR Policy Scanner v1.3
**Researched:** 2026-02-12
**Scope:** Stack additions for 7 new capabilities: scraper pagination, bill detail fetching, production website, SquareSpace iframe embedding, DOCX visual QA automation, confidence scoring, production monitoring
**Confidence:** HIGH (verified against PyPI, npm, official API docs, codebase analysis)

---

## Existing Stack (DO NOT CHANGE)

Already validated across v1.0-v1.2. Listed for integration context only:

| Technology | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime |
| aiohttp | >=3.9.0 | Async HTTP client (BaseScraper pattern) |
| python-dateutil | >=2.8.0 | Date parsing |
| jinja2 | >=3.1.0 | Template rendering |
| pytest | (dev) | Test framework |
| python-docx | >=1.1.0 | DOCX generation |
| rapidfuzz | >=3.14.0 | Fuzzy name matching |
| openpyxl | >=3.1.0 | XLSX parsing |
| pyyaml | >=6.0.0 | YAML support |
| pydantic | >=2.0.0 | Data validation |
| geopandas | >=1.0.0 | Geospatial (build-time) |
| GitHub Actions | ubuntu-latest | CI/CD |
| GitHub Pages | N/A | Static hosting |

---

## Feature 1: Scraper Pagination (NO NEW DEPENDENCIES)

### Problem

Three of four scrapers silently truncate results because they fetch only the first page:

| Scraper | Current Behavior | API Pagination Mechanism | Data Loss Risk |
|---|---|---|---|
| Federal Register | `per_page=50`, no page iteration | `next_page_url` in response, `page` query param, `total_pages` field | MEDIUM: 50 results of potentially 10,000+ matches |
| Grants.gov | `rows=50`/`rows=25`, no offset | `startRecordNum` offset + `rows` count, `hitCount` in response | HIGH: CFDA queries return 25, keyword queries return 50 |
| USASpending (scan) | `limit=10, page=1`, no iteration | `page_metadata.hasNext`, `page` field in payload | HIGH: Only 10 of potentially hundreds of awards per CFDA |
| Congress.gov | `limit=50`, no offset | `offset` and `limit` params (max 250), `pagination.next` URL | MEDIUM: 50 bills per query |

**Note:** USASpending already has full pagination in `fetch_tribal_awards_for_cfda()` (lines 115-193 of usaspending.py). The `scan()` method at line 84 does NOT paginate -- it uses `limit=10`. The pagination pattern already exists in the same file and should be copied.

### Recommendation: No new libraries. Pure logic changes.

All four federal APIs use standard pagination patterns. The existing `_request_with_retry()` method handles HTTP resilience. Pagination is a loop around it.

#### Federal Register API Pagination

Verified response structure from live API query:

```json
{
  "count": 10000,
  "total_pages": 50,
  "next_page_url": "https://www.federalregister.gov/api/v1/documents?...&page=2&per_page=200",
  "results": [...]
}
```

**Implementation pattern:**

```python
async def _search_paginated(self, session, query: str, start_date: str) -> list[dict]:
    """Fetch all pages for a search query."""
    params = {
        "conditions[term]": query,
        "conditions[publication_date][gte]": start_date,
        "conditions[type][]": DOC_TYPES,
        "per_page": 200,  # Increase from 50 to API practical max
        "order": "newest",
        "fields[]": [...],
    }
    url = f"{self.base_url}/documents.json?{urlencode(params, doseq=True)}"
    all_results = []
    max_pages = 10  # Safety cap: 200 * 10 = 2,000 results

    for page_num in range(1, max_pages + 1):
        data = await self._request_with_retry(session, "GET", url)
        results = data.get("results", [])
        all_results.extend(results)

        next_url = data.get("next_page_url")
        if not next_url or not results:
            break
        url = next_url
        await asyncio.sleep(0.5)  # Rate limit courtesy

    return [self._normalize(item) for item in all_results]
```

#### Grants.gov search2 Pagination

Verified from official Grants.gov API documentation:

- `startRecordNum`: 0-based offset
- `rows`: results per page
- Response includes `hitCount` for total matches

```python
async def _search_paginated(self, session, query: str) -> list[dict]:
    """Fetch all pages for a keyword search."""
    rows = 100  # Increase from 50
    start = 0
    all_results = []
    max_records = 1000  # Safety cap

    while start < max_records:
        payload = {
            "keyword": query,
            "oppStatuses": "forecasted|posted",
            "sortBy": "openDate|desc",
            "rows": rows,
            "startRecordNum": start,
        }
        resp = await self._request_with_retry(session, "POST", url, json=payload)
        data = resp.get("data", resp)
        results = data.get("oppHits", [])
        all_results.extend(results)

        hit_count = data.get("hitCount", 0)
        start += rows
        if not results or start >= hit_count:
            break
        await asyncio.sleep(0.3)

    return [self._normalize(item) for item in all_results]
```

#### USASpending scan() Pagination

The pattern already exists at line 136 of usaspending.py. Copy the `while True` / `page_metadata.hasNext` loop from `fetch_tribal_awards_for_cfda()` into `_fetch_obligations()`:

```python
# Change limit from 10 to 100, add page iteration
payload["limit"] = 100
# ... while True loop with page_metadata.hasNext check
```

#### Congress.gov Pagination

Verified from official GitHub documentation: max `limit=250`, `offset` parameter for starting record.

```python
async def _search_congress_paginated(self, session, term, bill_type, congress):
    all_bills = []
    offset = 0
    limit = 250  # API maximum

    while True:
        params = {"query": term, "limit": limit, "offset": offset, ...}
        data = await self._request_with_retry(session, "GET", url)
        bills = data.get("bills", [])
        all_bills.extend(bills)

        pagination = data.get("pagination", {})
        if not pagination.get("next") or not bills:
            break
        offset += limit
        await asyncio.sleep(0.3)  # Respect 5000 req/hr rate limit

    return [self._normalize(bill) for bill in all_bills]
```

### Confidence: HIGH

All pagination patterns verified against live API responses or official documentation. No libraries needed.

### Sources

- [Federal Register API v1 Documentation](https://www.federalregister.gov/developers/documentation/api/v1) -- pagination fields verified via live API response
- [Grants.gov search2 API](https://www.grants.gov/api/common/search2) -- startRecordNum/rows/hitCount verified
- [Congress.gov API GitHub - BillEndpoint.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/BillEndpoint.md) -- offset/limit/250 max verified
- Codebase: `src/scrapers/usaspending.py` lines 115-193 -- existing pagination pattern

---

## Feature 2: Congress.gov Bill Detail Fetching (NO NEW DEPENDENCIES)

### Problem

The Congress.gov scraper currently collects bill listings but does NOT fetch detail sub-endpoints. Each bill listing contains only: title, latest action, bill type/number/congress. Missing: full text URLs, cosponsors, all actions, summaries, subjects, committee assignments.

### API Sub-Endpoints (Verified)

| Sub-endpoint | URL Pattern | Returns |
|---|---|---|
| Text | `/v3/bill/{congress}/{type}/{number}/text` | Text version URLs (PDF, HTML, XML) |
| Cosponsors | `/v3/bill/{congress}/{type}/{number}/cosponsors` | Cosponsor list with party, state, date |
| Actions | `/v3/bill/{congress}/{type}/{number}/actions` | Full action history with dates and codes |
| Summaries | `/v3/bill/{congress}/{type}/{number}/summaries` | CRS analyst summaries |
| Subjects | `/v3/bill/{congress}/{type}/{number}/subjects` | Legislative subject terms |
| Committees | `/v3/bill/{congress}/{type}/{number}/committees` | Committee assignments |

### Recommendation: Add detail-fetching methods to existing CongressGovScraper

No new dependencies. Add methods that call sub-endpoints using existing `_request_with_retry()`. Rate limit is 5,000 requests/hour -- with 11 legislative queries returning maybe 50-100 unique bills, fetching 3-4 sub-endpoints per bill is ~300-400 requests. Well within limits.

### Implementation Pattern

```python
async def fetch_bill_details(self, session, bill: dict) -> dict:
    """Enrich a bill listing with detail sub-endpoints."""
    congress = bill.get("congress", 119)
    bill_type = bill.get("bill_type", "").lower()
    number = bill.get("bill_number", "")
    base = f"{self.base_url}/bill/{congress}/{bill_type}/{number}"

    # Fetch sub-endpoints in parallel (3 most valuable)
    tasks = {
        "actions": self._request_with_retry(session, "GET", f"{base}/actions?limit=250"),
        "cosponsors": self._request_with_retry(session, "GET", f"{base}/cosponsors?limit=250"),
        "summaries": self._request_with_retry(session, "GET", f"{base}/summaries"),
    }
    # Use asyncio.gather with return_exceptions for resilience
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    enriched = dict(bill)
    for key, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            logger.warning("Failed to fetch %s for %s: %s", key, bill["source_id"], result)
            enriched[key] = []
        else:
            enriched[key] = result.get(key, [])

    return enriched
```

### Key Decision: Which sub-endpoints to fetch?

**Fetch these (HIGH value for advocacy packets):**
- `actions` -- Shows legislative progress (committee referral, floor votes, etc.)
- `cosponsors` -- Shows political support breadth
- `summaries` -- CRS summaries are authoritative plain-English descriptions

**Skip these (LOW value, adds request volume):**
- `text` -- URLs to full text; most bills are too long for packet use
- `subjects` -- Subject tags; we already filter by search terms
- `committees` -- Committee info is in actions

### Confidence: HIGH

Sub-endpoints verified via official GitHub documentation. API key already available in CI secrets.

### Sources

- [Congress.gov API BillEndpoint.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/BillEndpoint.md) -- sub-endpoint URLs and response formats
- [Congress.gov API README](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/README.md) -- rate limit 5000/hr, offset/limit params

---

## Feature 3: Production Website (React + Vite + Tailwind)

### Current Draft State

The website draft at `.planning/website/` has significant issues identified in the LAUNCH-SWARM.md review plan:
- 46 mock Tribe names (need 592)
- Fake text blob downloads (need real DOCX from GitHub Pages)
- Pre-compiled Tailwind CSS in index.css (1424 lines of compiled output)
- 30+ unused Radix/shadcn components
- Vite 6.3.5 (current stable is 7.3.1)
- React 18.3.1 (current stable is 19.2.4)

### Recommended Stack (Website)

| Technology | Version | Purpose | Rationale |
|---|---|---|---|
| React | ^18.3.1 | UI framework | **Stay on React 18.** React 19's Server Components and use() hook provide zero value for a static GitHub Pages SPA. Upgrading risks breaking shadcn/Radix components. |
| Vite | ^6.4.0 | Build tool | **Stay on Vite 6 LTS.** Vite 7 introduces breaking changes (Rolldown bundler). The draft's `vite.config.ts` works on v6. Upgrade to latest v6 patch only. |
| Tailwind CSS | ^4.1.0 | Styling | **Already using v4 syntax** (`@import "tailwindcss"` in globals.css). Update to 4.1.x for latest utilities. |
| @tailwindcss/vite | ^4.1.0 | Vite plugin | **Required for Tailwind v4.** Replaces the PostCSS plugin approach. Already implied by globals.css `@import "tailwindcss"`. |
| Fuse.js | ^7.1.0 | Fuzzy search | **For 592-Tribe autocomplete.** Lightweight (7KB gzipped), excellent fuzzy matching. 592 items is trivially fast. Simpler API than FlexSearch. |
| lucide-react | ^0.487.0 | Icons | **Already in draft.** Keep. |

### What to REMOVE from Draft

| Package | Why Remove |
|---|---|
| embla-carousel-react | Not used in any component |
| react-day-picker | Not used (no date picker needed) |
| react-hook-form | Not used (no forms with validation) |
| react-resizable-panels | Not used |
| recharts | Not used (no charts needed) |
| next-themes | Not used (single dark theme, no toggle) |
| input-otp | Not used |
| cmdk | Not used (Fuse.js replaces command palette search) |
| ~25 unused @radix-ui/* | Audit: only accordion, dialog, select, scroll-area, tooltip are used |

**Estimated bundle reduction:** Removing unused packages should cut initial bundle from ~250KB+ to ~80-100KB gzipped.

### What to ADD to Draft

| Package | Version | Purpose | Why |
|---|---|---|---|
| fuse.js | ^7.1.0 | 592-Tribe fuzzy search autocomplete | Purpose-built for client-side fuzzy search. Better typo tolerance than native `.filter().includes()`. 592 items loads in <1ms. |
| @tailwindcss/vite | ^4.1.0 | Tailwind v4 Vite integration | Required to process `@import "tailwindcss"` at build time. Eliminates the pre-compiled CSS problem. |

### Website Dev Dependencies

| Package | Version | Purpose | Why |
|---|---|---|---|
| typescript | ^5.7.0 | Type checking | Already implied by .tsx files; needs explicit dependency |
| vitest | ^4.0.0 | Unit testing | Native Vite integration, 10-20x faster than Jest. Jest-compatible API. |
| @testing-library/react | ^16.0.0 | Component testing | Standard React testing library. Works with Vitest. |
| @testing-library/jest-dom | ^6.0.0 | DOM assertions | Custom matchers for DOM state |

### Critical: Real Data Pipeline (NO library needed)

The TribeSelector currently generates fake text blobs. The fix is architectural, not a library:

1. `scripts/build_web_index.py` already produces `docs/web/data/tribes.json` with 592 Tribes
2. Generate-packets workflow already copies DOCX files to `docs/web/tribes/`
3. GitHub Pages serves these as static files
4. Website fetches `tribes.json` at startup, Fuse.js indexes it, TribeSelector links to real DOCX URLs

```typescript
// Replace mock data import with live data fetch
const [tribes, setTribes] = useState<Tribe[]>([]);
useEffect(() => {
  fetch('/data/tribes.json')
    .then(r => r.json())
    .then(data => setTribes(data.tribes));
}, []);

const fuse = useMemo(() => new Fuse(tribes, {
  keys: ['name', 'states'],
  threshold: 0.3,
}), [tribes]);
```

### Vite Config Cleanup

The draft's `vite.config.ts` has 26 bizarre version-pinned aliases (e.g., `'@radix-ui/react-tooltip@1.1.8': '@radix-ui/react-tooltip'`). These are Figma export artifacts and should all be removed. The `@` path alias is the only one to keep.

```typescript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: '/TCR-policy-scanner/',  // GitHub Pages repo path
  build: {
    target: 'es2020',  // Browser compat for SquareSpace iframe
    outDir: 'build',
  },
});
```

### Confidence: HIGH

React 18/Vite 6 versions verified as still supported. Fuse.js 7.1.0 verified on npm. Tailwind v4 `@import` syntax confirmed working in draft's globals.css.

### Sources

- [React 19.2 release blog](https://react.dev/blog/2025/10/01/react-19-2) -- Server Components focus, not relevant for static SPA
- [Vite 7 announcement](https://vite.dev/blog/announcing-vite7) -- Rolldown bundler migration, breaking changes
- [Tailwind CSS v4 Vite plugin](https://www.npmjs.com/package/@tailwindcss/vite) -- Official Vite integration for v4
- [Fuse.js documentation](https://www.fusejs.io/) -- Lightweight fuzzy search, 7.1.0 latest
- [Vitest 4.0](https://vitest.dev/blog/vitest-4) -- Browser mode, visual regression
- Codebase: `.planning/website/package.json`, `vite.config.ts`, `globals.css`, `mockData.ts`

---

## Feature 4: SquareSpace Iframe Embedding (NO NEW DEPENDENCIES)

### Architecture Decision

**Use iframe embedding via SquareSpace Code Block.** This is the simplest approach with the cleanest boundary:

| Approach | Complexity | Maintenance | Risk |
|---|---|---|---|
| iframe in Code Block | LOW | Zero SquareSpace maintenance | Cross-origin isolation is a feature, not a bug |
| Code Injection (JS/CSS) | HIGH | Breaks on SquareSpace template updates | Fragile, unsupported |
| SquareSpace Developer Mode | MEDIUM | Requires Business plan or higher | Template lock-in |

### Requirements for iframe Compatibility

**Website build must:**
1. Set `base: '/TCR-policy-scanner/'` in Vite config (GitHub Pages subpath)
2. Serve over HTTPS (GitHub Pages does this automatically)
3. NOT use `X-Frame-Options: DENY` (GitHub Pages does not set this)
4. Support responsive sizing within iframe container
5. Use `loading="lazy"` on the iframe tag in SquareSpace

**SquareSpace Code Block:**

```html
<div style="width:100%; max-width:1200px; margin:0 auto;">
  <iframe
    src="https://atniclimate.github.io/TCR-policy-scanner/"
    width="100%"
    height="800"
    style="border:none; border-radius:8px;"
    loading="lazy"
    title="TCR Policy Scanner - Tribal Climate Resilience Document Portal"
    allow="downloads"
  ></iframe>
</div>
```

**Key detail:** The `allow="downloads"` attribute is needed for DOCX file downloads to work from within the iframe. Without it, browsers may block the download.

### Responsive iframe Height

Add a `postMessage` resize pattern (no library needed):

```typescript
// In the React app (inside iframe)
useEffect(() => {
  const observer = new ResizeObserver(() => {
    window.parent.postMessage({
      type: 'tcr-resize',
      height: document.body.scrollHeight,
    }, '*');
  });
  observer.observe(document.body);
  return () => observer.disconnect();
}, []);
```

```html
<!-- In SquareSpace Code Block -->
<script>
window.addEventListener('message', (e) => {
  if (e.data?.type === 'tcr-resize') {
    document.querySelector('iframe[src*="TCR-policy-scanner"]').height = e.data.height;
  }
});
</script>
```

### SquareSpace Plan Requirement

**Business plan or higher is required** for Code Blocks with custom HTML/iframe embeds. This is a SquareSpace limitation, not a technical one.

### Confidence: HIGH

GitHub Pages iframe embedding is well-documented. SquareSpace Code Blocks support iframes on Business+ plans.

### Sources

- [SquareSpace Embed Blocks documentation](https://support.squarespace.com/hc/en-us/articles/206543617-Embed-blocks)
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) -- 100GB/month bandwidth, 1GB site size
- [SquareSpace iframe embedding guides](https://whatsquare.space/blog/squarespace-embed-iframe)

---

## Feature 5: DOCX Visual QA Automation (NEW DEPENDENCIES)

### Problem

992 DOCX documents generated. Currently no automated way to verify visual rendering quality (page breaks, table alignment, font rendering, image placement). Manual review does not scale to 592 Tribes x 4 document types.

### Recommended Stack

| Technology | Version | Purpose | Why |
|---|---|---|---|
| playwright (Python) | >=1.58.0 | Browser automation, screenshots | Only browser automation tool with Python async support and headless Chromium. Captures page screenshots for visual comparison. |
| LibreOffice | >=24.2 (system) | DOCX-to-PDF conversion | Headless mode converts DOCX to PDF/images. Free, cross-platform. Only reliable DOCX renderer outside Microsoft Office. |
| Pillow | >=11.0.0 | Image comparison | Compare QA screenshots against baselines. Pixel-diff for visual regression detection. |

### Why NOT Other Options

| Option | Why Not |
|---|---|
| python-pptx visual tests | Wrong format (PPTX, not DOCX) |
| docx2pdf (pip) | Wrapper around LibreOffice/Word; adds dependency without value |
| WeasyPrint | HTML-to-PDF; cannot render DOCX |
| pdf2image + poppler | Adds C dependency (poppler); LibreOffice can render directly |
| Selenium | Playwright is faster, more reliable, better async support |
| pytest-playwright | Playwright's Python package already includes pytest plugin |

### Implementation Pipeline

```
DOCX -> LibreOffice headless -> PDF -> Playwright screenshot -> Pillow pixel-diff -> Pass/Fail
```

#### Step 1: LibreOffice Headless Conversion

```python
import subprocess

def docx_to_pdf(docx_path: str, output_dir: str) -> str:
    """Convert DOCX to PDF using LibreOffice headless."""
    subprocess.run([
        "soffice", "--headless", "--convert-to", "pdf",
        "--outdir", output_dir, docx_path
    ], check=True, timeout=60)
    return str(Path(output_dir) / Path(docx_path).with_suffix(".pdf").name)
```

#### Step 2: Playwright PDF Screenshot

```python
from playwright.async_api import async_playwright

async def screenshot_pdf(pdf_path: str, output_path: str) -> None:
    """Open PDF in Chromium and capture full-page screenshot."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file://{pdf_path}")
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()
```

#### Step 3: Visual Comparison

```python
from PIL import Image
import math

def images_similar(img1_path: str, img2_path: str, threshold: float = 0.02) -> bool:
    """Compare two images. Returns True if pixel difference < threshold."""
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    if img1.size != img2.size:
        return False
    pixels1 = list(img1.getdata())
    pixels2 = list(img2.getdata())
    diff = sum(
        math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
        for p1, p2 in zip(pixels1, pixels2)
    )
    max_diff = math.sqrt(255**2 * 3) * len(pixels1)
    return (diff / max_diff) < threshold
```

### GitHub Actions Integration

LibreOffice and Playwright both work on `ubuntu-latest`:

```yaml
- name: Install LibreOffice
  run: sudo apt-get install -y libreoffice-writer-nogui

- name: Install Playwright browsers
  run: |
    pip install playwright>=1.58.0
    playwright install chromium --with-deps
```

### Confidence: HIGH

Playwright 1.58.0 verified on PyPI (supports Python 3.9-3.13). LibreOffice headless is standard on Ubuntu CI runners. Pillow is a mature library with no compatibility concerns.

### Sources

- [Playwright Python on PyPI](https://pypi.org/project/playwright/) -- v1.58.0, released 2026-01-30
- [Playwright Python screenshots](https://playwright.dev/python/docs/screenshots) -- full_page, element, clip options
- [LibreOffice headless conversion](https://ask.libreoffice.org/t/convert-files-to-pdf-a-on-command-line-headless-mode/821) -- soffice --headless --convert-to pdf
- [Pillow documentation](https://pillow.readthedocs.io/) -- Image comparison capabilities

---

## Feature 6: Confidence Scoring (NO NEW DEPENDENCIES)

### Problem

Intelligence products (advocacy packets) have no machine-readable reliability indicator. A packet with 5 verified data sources should rank higher than one with 1 stale scraper result and no award data.

### Recommendation: Hand-Rolled Weighted Scoring

**Do NOT add scikit-learn, ydata-quality, or any ML library.** This is not a machine learning problem. It is a deterministic data quality assessment with known inputs.

### Scoring Dimensions

| Dimension | Weight | Input | Score Range |
|---|---|---|---|
| Data freshness | 0.25 | Days since last scan per source | 1.0 (today) to 0.0 (>30 days) |
| Source coverage | 0.30 | How many of 4 scrapers returned data | 0.25 per source |
| Award data quality | 0.20 | Has USASpending award matches | 1.0 (matched), 0.5 (CFDA only), 0.0 (none) |
| Hazard data completeness | 0.15 | NRI + USFS data present | 1.0 (both), 0.5 (one), 0.0 (neither) |
| Legislative relevance | 0.10 | Congress.gov bills with recent actions | 1.0 (active bill), 0.5 (stale), 0.0 (none) |

### Implementation Pattern

```python
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class ConfidenceScore:
    """Per-Tribe confidence score for advocacy packet quality."""
    overall: float          # Weighted composite 0.0-1.0
    freshness: float        # Data age score
    source_coverage: float  # How many sources contributed
    award_quality: float    # Award match quality
    hazard_completeness: float  # NRI + USFS data
    legislative_relevance: float  # Active bill coverage
    label: str              # "HIGH" / "MEDIUM" / "LOW"

    @classmethod
    def compute(cls, tribe_data: dict) -> "ConfidenceScore":
        freshness = cls._score_freshness(tribe_data)
        source_coverage = cls._score_sources(tribe_data)
        award_quality = cls._score_awards(tribe_data)
        hazard = cls._score_hazards(tribe_data)
        legislative = cls._score_legislative(tribe_data)

        overall = (
            0.25 * freshness +
            0.30 * source_coverage +
            0.20 * award_quality +
            0.15 * hazard +
            0.10 * legislative
        )
        label = "HIGH" if overall >= 0.7 else "MEDIUM" if overall >= 0.4 else "LOW"

        return cls(
            overall=round(overall, 3),
            freshness=round(freshness, 3),
            source_coverage=round(source_coverage, 3),
            award_quality=round(award_quality, 3),
            hazard_completeness=round(hazard, 3),
            legislative_relevance=round(legislative, 3),
            label=label,
        )
```

### Integration Points

- Compute per-Tribe confidence during packet generation (`src/packets/orchestrator.py`)
- Store in `tribes.json` for website display (`scripts/build_web_index.py`)
- Include confidence badge in DOCX packet cover page (`src/packets/docx_sections.py`)
- Display as color-coded indicator on website (green/amber/red)

### Confidence: HIGH

This is a straightforward weighted scoring system with known inputs. No ML or external libraries needed.

---

## Feature 7: Production Monitoring (100-200 Concurrent Users)

### Architecture Assessment

The website is a static SPA on GitHub Pages. There is no backend server to monitor at request time. Monitoring needs are:

| What | Scope | Tool |
|---|---|---|
| Website uptime | Is GitHub Pages serving? | GitHub Actions cron health check |
| Scraper health | Are daily scans succeeding? | GitHub Actions workflow status |
| Packet generation | Are weekly packets generating? | GitHub Actions workflow status |
| User analytics | Page views, downloads, search queries | Lightweight client-side analytics |
| Error tracking | JavaScript errors in production | Client-side error boundary |

### GitHub Pages Performance Assessment (100-200 Concurrent Users)

| Metric | GitHub Pages Limit | Our Expected Load | Verdict |
|---|---|---|---|
| Bandwidth | 100 GB/month (soft) | ~592 DOCX files * ~500KB avg = ~290MB total. Even if every user downloads, 200 users * 1MB = 200MB/day = 6GB/month | SAFE |
| Site size | 1 GB max | 592 * 4 DOCX types * ~500KB = ~1.1GB. **Tight.** May need to compress or use GitHub Releases for DOCX storage. | MONITOR |
| Concurrent connections | No stated limit (CDN-backed) | 100-200 concurrent | SAFE |
| Rate limiting | Possible 429 on high traffic | Unlikely at 200 users | LOW RISK |

**Critical finding:** 592 Tribes * 4 document types * ~500KB = ~1.1GB, which exceeds GitHub Pages' 1GB site size limit. **Mitigation options:**

1. **Recommended: Store DOCX files in GitHub Releases** (15GB per release). Website links to Release assets instead of Pages-hosted files.
2. Alternative: Compress DOCX files (already ZIP format internally, limited gains).
3. Alternative: Host only per-Tribe packets (2 types), put regional packets in Releases.

### Recommended Monitoring Stack

| Tool | Purpose | Implementation | New Dependency? |
|---|---|---|---|
| GitHub Actions health check | Uptime monitoring | Cron workflow that curl's the site | No |
| Workflow status badges | Scraper/packet pipeline health | README badges linking to Actions | No |
| Plausible Analytics | Privacy-first user analytics | Script tag, no cookies, GDPR-compliant | Script tag only (no npm) |
| React Error Boundary | Client-side error capture | Built-in React pattern | No |

### Why Plausible (Not Google Analytics)

| Criteria | Plausible | Google Analytics |
|---|---|---|
| Privacy | No cookies, GDPR-compliant | Requires cookie consent |
| Tribal data sovereignty | No user tracking, aggregate only | Individual user profiles |
| Size | 1KB script tag | 45KB+ gtag.js |
| Setup | One `<script>` tag | Requires consent banner |
| Cost | Free for open source | Free |
| TSDF alignment | T0-compatible (no PII collection) | T1+ (collects user behavior data) |

**Plausible is critical for TSDF compliance.** The Tribal Sovereignty Data Framework requires minimizing data collection about Tribal Nation users. Google Analytics collects IP addresses, browser fingerprints, and behavior patterns that create a T1 data classification. Plausible collects only aggregate page views with no PII.

```html
<!-- In index.html -->
<script defer data-domain="atniclimate.github.io" src="https://plausible.io/js/script.js"></script>
```

### Health Check Workflow

```yaml
name: Site Health Check
on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - name: Check website
        run: |
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://atniclimate.github.io/TCR-policy-scanner/)
          if [ "$STATUS" != "200" ]; then
            echo "::error::Website returned HTTP $STATUS"
            exit 1
          fi
      - name: Check tribes.json
        run: |
          curl -sf https://atniclimate.github.io/TCR-policy-scanner/data/tribes.json | python3 -c "
          import json, sys
          data = json.load(sys.stdin)
          tribes = data.get('total_tribes', 0)
          if tribes < 500:
              print(f'::warning::Only {tribes} tribes in index (expected 592)')
          else:
              print(f'Health check passed: {tribes} tribes')
          "
```

### Confidence: HIGH

GitHub Pages limits are well-documented. Plausible is a known open-source analytics tool. The 1GB site size limit is the only risk requiring mitigation via GitHub Releases.

### Sources

- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) -- 100GB bandwidth, 1GB site size
- [Plausible Analytics](https://plausible.io/) -- Privacy-first, GDPR-compliant
- [GitHub Releases file limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) -- 2GB per file, no total limit documented

---

## Summary: All Stack Changes

### ADD to requirements.txt (Production)

No production Python dependencies needed. All Python-side changes are logic-only (pagination, bill detail fetching, confidence scoring).

### ADD to requirements-dev.txt (Python Dev)

| Package | Version | Purpose |
|---|---|---|
| playwright | >=1.58.0 | DOCX visual QA screenshots |
| Pillow | >=11.0.0 | Visual comparison for QA |

### ADD to Website package.json

| Package | Version | Purpose | Section |
|---|---|---|---|
| fuse.js | ^7.1.0 | 592-Tribe fuzzy search | dependencies |
| @tailwindcss/vite | ^4.1.0 | Tailwind v4 Vite plugin | dependencies |
| typescript | ^5.7.0 | Type checking | devDependencies |
| vitest | ^4.0.0 | Unit testing | devDependencies |
| @testing-library/react | ^16.0.0 | Component testing | devDependencies |
| @testing-library/jest-dom | ^6.0.0 | DOM matchers | devDependencies |

### REMOVE from Website package.json

| Package | Why |
|---|---|
| embla-carousel-react | Unused |
| react-day-picker | Unused |
| react-hook-form | Unused |
| react-resizable-panels | Unused |
| recharts | Unused |
| next-themes | Unused (single theme) |
| input-otp | Unused |
| cmdk | Unused (replaced by Fuse.js) |
| ~20 @radix-ui/* packages | Unused (keep only: accordion, dialog, select, scroll-area, tooltip, slot, separator) |

### SYSTEM DEPENDENCIES (GitHub Actions only)

| Tool | Version | Install Method | Purpose |
|---|---|---|---|
| LibreOffice | >=24.2 | `apt-get install libreoffice-writer-nogui` | DOCX-to-PDF conversion |
| Chromium | (bundled) | `playwright install chromium --with-deps` | PDF screenshots |

### DO NOT ADD

| Library/Tool | Why Not |
|---|---|
| React 19 | Server Components not needed for static SPA; risks breaking shadcn/Radix |
| Vite 7 | Breaking changes (Rolldown bundler); v6 is stable and supported |
| Next.js | Overkill for a static SPA on GitHub Pages |
| Google Analytics | Violates TSDF data sovereignty principles; collects PII |
| Sentry | Overkill for a static SPA with no backend |
| DataDog / New Relic | No backend to monitor; SPA + GitHub Pages |
| scikit-learn | Confidence scoring is deterministic weighting, not ML |
| docx2pdf | Thin wrapper around LibreOffice; adds dependency without value |
| FlexSearch | Overkill for 592 items; Fuse.js is simpler with better fuzzy matching |
| Algolia / Meilisearch | Server-side search; 592 items do not need a search service |

---

## Installation Commands

### Python (Dev)

```bash
# Visual QA automation (dev only)
pip install playwright>=1.58.0 Pillow>=11.0.0
playwright install chromium --with-deps
```

### Website

```bash
cd website/

# Clean install (remove problematic Figma-exported deps)
rm -rf node_modules package-lock.json

# Install production deps
npm install react@^18.3.1 react-dom@^18.3.1
npm install fuse.js@^7.1.0
npm install @tailwindcss/vite@^4.1.0 tailwindcss@^4.1.0
npm install lucide-react@^0.487.0
npm install class-variance-authority@^0.7.1 clsx tailwind-merge
npm install @radix-ui/react-accordion @radix-ui/react-dialog @radix-ui/react-select @radix-ui/react-scroll-area @radix-ui/react-tooltip @radix-ui/react-slot @radix-ui/react-separator

# Install dev deps
npm install -D @vitejs/plugin-react-swc@^3.10.0 vite@^6.4.0
npm install -D typescript@^5.7.0
npm install -D vitest@^4.0.0 @testing-library/react@^16.0.0 @testing-library/jest-dom@^6.0.0
npm install -D @types/node@^20.10.0
```

---

## Phase Ordering Recommendation (Stack Perspective)

Based on dependency analysis between features:

1. **Scraper pagination** -- Independent. Fix silent data truncation first because all downstream features depend on complete data.
2. **Congress.gov bill detail fetching** -- Depends on Congress.gov pagination being correct. Small addition to existing scraper.
3. **Confidence scoring** -- Depends on complete scraper data (pagination must be fixed first). Produces data that website and packets consume.
4. **Website (real data pipeline)** -- Depends on `tribes.json` being populated with confidence scores and complete data. Largest single feature.
5. **SquareSpace iframe embedding** -- Depends on website being deployed to GitHub Pages.
6. **DOCX visual QA** -- Independent. Can run in parallel with website work. Tests existing DOCX output.
7. **Production monitoring** -- Last. Monitors everything else.

---

## Critical Architecture Decisions

### Decision 1: DOCX Storage Location

**Problem:** 592 Tribes * 4 doc types * ~500KB = ~1.1GB. Exceeds GitHub Pages 1GB limit.

**Recommendation:** Use GitHub Releases for DOCX files. Website `tribes.json` links to Release asset URLs instead of Pages-relative paths.

**Impact:** Requires modifying `scripts/build_web_index.py` to generate Release asset URLs, and the generate-packets workflow to create/update a Release.

### Decision 2: React Version

**Recommendation:** Stay on React 18. React 19's headline features (Server Components, `use()` hook, Actions) are designed for server-rendered apps. This is a static SPA. Upgrading risks shadcn/Radix compatibility issues with zero benefit.

### Decision 3: Vite Version

**Recommendation:** Stay on Vite 6.x. Vite 7 migrated to Rolldown (replacing esbuild+Rollup). While Rolldown is faster, it introduces breaking changes in plugin compatibility. The draft's Figma-generated `vite.config.ts` needs cleanup regardless -- do that cleanup on stable Vite 6 rather than debugging Vite 7 migration simultaneously.

---

## Sources

### API Documentation (Verified, HIGH Confidence)

- [Federal Register API v1](https://www.federalregister.gov/developers/documentation/api/v1) -- Pagination fields verified via live API response
- [Grants.gov search2 API](https://www.grants.gov/api/common/search2) -- startRecordNum/rows/hitCount pagination documented
- [Congress.gov API BillEndpoint.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/BillEndpoint.md) -- Sub-endpoints for text, cosponsors, actions, summaries
- [Congress.gov API README](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/README.md) -- Rate limit 5000/hr, offset max 250
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) -- 100GB/mo bandwidth, 1GB site size

### Package Registry (Verified, HIGH Confidence)

- [Playwright Python 1.58.0 on PyPI](https://pypi.org/project/playwright/) -- Released 2026-01-30, Python 3.9-3.13
- [Fuse.js 7.1.0 on npm](https://www.npmjs.com/package/fuse.js) -- Lightweight fuzzy search
- [Tailwind CSS 4.1.18 on npm](https://www.npmjs.com/package/tailwindcss) -- Latest v4 with Vite plugin
- [React 19.2.4 on npm](https://www.npmjs.com/package/react) -- Current latest (NOT recommended for this project)
- [Vite 7.3.1 on npm](https://www.npmjs.com/package/vite) -- Current latest (NOT recommended; stay on v6)
- [Vitest 4.0.18 on npm](https://www.npmjs.com/package/vitest) -- Jest-compatible, Vite-native testing

### Embedding & Analytics

- [SquareSpace embed blocks](https://support.squarespace.com/hc/en-us/articles/206543617-Embed-blocks) -- iframe via Code Block
- [SquareSpace iframe best practices](https://whatsquare.space/blog/squarespace-embed-iframe) -- HTTPS, lazy loading, sandbox
- [Plausible Analytics](https://plausible.io/) -- Privacy-first, no cookies, GDPR-compliant

### Codebase Analysis

- `src/scrapers/federal_register.py` -- per_page=50, no pagination loop
- `src/scrapers/grants_gov.py` -- rows=50/25, no startRecordNum offset
- `src/scrapers/usaspending.py` -- scan() uses limit=10 page=1; but fetch_tribal_awards_for_cfda() already paginates correctly (lines 115-193)
- `src/scrapers/congress_gov.py` -- limit=50, no offset parameter
- `src/scrapers/base.py` -- _request_with_retry() handles HTTP resilience, circuit breaker integrated
- `.planning/website/package.json` -- 30+ Radix deps, most unused
- `.planning/website/vite.config.ts` -- 26 bizarre version-pinned aliases (Figma artifacts)
- `.planning/website/src/data/mockData.ts` -- 46 hardcoded Tribes (need 592)
- `.planning/website/src/components/TribeSelector.tsx` -- generates fake text blobs
- `scripts/build_web_index.py` -- already produces tribes.json with 592 Tribes
- `.github/workflows/generate-packets.yml` -- already copies DOCX to docs/web/
