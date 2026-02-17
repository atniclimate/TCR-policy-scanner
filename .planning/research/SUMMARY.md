# Research Summary: TCR Policy Scanner v1.4 — Climate Vulnerability Intelligence

**Synthesized:** 2026-02-17
**Synthesizer:** gsd-research-synthesizer
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Overall confidence:** MEDIUM-HIGH
**Ready for roadmap:** YES

---

## Executive Summary

TCR Policy Scanner v1.4 adds climate vulnerability intelligence to a mature, battle-tested pipeline that already produces briefing packets for 592 federally recognized Tribal Nations. The milestone integrates three new federal data sources — CDC/ATSDR Social Vulnerability Index 2022 (SVI), expanded FEMA NRI fields (EAL breakdowns, national percentiles), and USGS CMIP6-LOCA2 county-level climate projections — into the existing pre-cache architecture without changing any fundamental patterns. The result: per-Tribe vulnerability profiles that transform existing hazard data from "what hazards exist" into "how vulnerable is this community and how will that change." A new standalone vulnerability document (Doc E) joins Doc A–D, and vulnerability data surfaces on the website and within existing documents.

The technical approach is conservative by design. Two new libraries (xarray, netCDF4) handle the only genuinely new format — NetCDF climate projection files. Everything else — CSV parsing, area-weighted aggregation via the existing county crosswalk, JSON caching, Pydantic models, DOCX rendering — reuses proven infrastructure from Phases 12–16. The critical path is: expand NRI extraction -> integrate SVI -> build composite vulnerability profiles -> render in documents -> update website. NOAA climate projections (LOCA2) are architecturally sound but carry the highest technical risk due to NetCDF complexity and Alaska coverage gaps; they should be treated as a conditional component of Phase 19 that may slip to v1.5 if the NetCDF validation reveals unexpected complexity.

The most important non-technical constraints are sovereignty-first framing and the audience air gap. Vulnerability data inherently risks deficit framing of Tribal Nations — presenting communities as "at-risk" rather than as sovereign governments facing disproportionate hazard exposure. Every renderer must use approved framing vocabulary before any code ships. The existing Doc A/B air gap must extend to vulnerability sections: SVI theme decompositions (poverty rate, disability rate) belong only in internal documents (Doc A/C), not congressional documents (Doc B/D). These are not polish concerns — they are architectural requirements that must be decided in Phase 19 and enforced through existing audience-filtering tests.

---

## Key Findings

### Stack (from STACK.md)

**Two new libraries only:**
- `xarray >= 2025.12.0` — reads USGS LOCA2 county NetCDF climate files
- `netCDF4 >= 1.7.3` — HDF5 backend required by xarray

Both are build-time only (parallel to existing geopandas pattern). The main pipeline, DocxEngine, and test suite never import them. Both have pre-built Windows wheels and are fully Python 3.12 compatible. Version compatibility is clean: xarray requires pandas >= 2.2 and numpy >= 1.26, both already satisfied via geopandas.

**Three data sources, one pattern:**

| Source | Format | Download | Key Field | Status |
|--------|--------|----------|-----------|--------|
| USGS CMIP6-LOCA2 | NetCDF (~2.17 GB) | HTTPS from ScienceBase (DOI: 10.5066/P1N9IRWC) | `GEOID` (county FIPS) | Not integrated — highest risk |
| CDC/ATSDR SVI 2022 | CSV (~15 MB) | Manual download from svi.cdc.gov | `FIPS` (county) | Not integrated — medium risk |
| FEMA NRI expanded | Same CSV already in data/nri/ | None (already downloaded) | `STCOFIPS` | Partial — lowest risk |

All three join via the existing `tribal_county_area_weights.json` crosswalk. County FIPS is the universal join key across every source.

**Do NOT integrate:**
- FEMA Future Risk Index (removed from FEMA website February 2025, archived by third parties only — politically uncertain)
- NOAA SLR projections (not county-level; use NRI CFLD fields as coastal flooding proxy unless a differentiator is specifically requested)
- Raw LOCA2 gridded 6km data (~100+ GB; county-level summaries already exist)

**Critical version note:** FEMA NRI v1.20 (December 2025) migrates toward RAPT, Connecticut replaced county FIPS with 8 planning regions, and social vulnerability methodology changed at v1.19 to use CDC SVI. Both version-related changes must be handled in Phase 19.

---

### Features (from FEATURES.md)

**Table stakes — must ship in v1.4:**

| ID | Feature | Priority | Complexity |
|----|---------|----------|------------|
| TS-2 | Expanded NRI risk metrics (EAL by consequence type, national percentiles) | P0 — do first | LOW |
| TS-1 | CDC/ATSDR SVI integration (4-theme social vulnerability) | P0 — do first | MEDIUM |
| TS-3 | Composite vulnerability score (0–1, 5 rating tiers, FEMA methodology) | P0 — after TS-1/2 | MEDIUM |
| TS-5 | Data provenance and citation metadata in all outputs | P0 — thread through | LOW |
| TS-4 | Vulnerability section in Doc A and Doc B | P1 — after data pipeline | MEDIUM |
| TS-6 | Vulnerability display on website (tribe card badges) | P2 — after documents | MEDIUM-HIGH |

**Differentiators — high value, ship in v1.4 if feasible:**

| ID | Feature | Priority | Complexity |
|----|---------|----------|------------|
| DF-7 | EAL breakdown by consequence type in DOCX (buildings/population/agriculture) | P1 — with TS-4, data from TS-2 | LOW |
| DF-2 | Grant-ready vulnerability narrative paragraphs | P1 — after TS-4 | MEDIUM |
| DF-5 | Comparative peer context (percentile among 592 Tribes, ecoregion group) | P1 — after TS-3 | LOW-MEDIUM |
| DF-6 | Web visualization (Chart.js radar + SVI bar charts) | P2 — after TS-6 | MEDIUM-HIGH |
| DF-1 | NOAA climate projections (LOCA2 mid-century vs baseline) | P3 — conditional, may slip to v1.5 | HIGH |

**Explicitly defer to v1.5+:**
- DF-3: Hazard trend indicators (needs DF-1 for forward trajectory; historical-only version is partial)
- DF-4: BRIC resilience sub-indicators (verify if NRI CSV has sub-scores — LOW confidence item)

**Anti-features confirmed — do not build:**
- Real-time climate modeling or simulation (computationally intractable for a policy tool)
- Tribal-specific data collection or surveys (T0 classification boundary)
- Health impact predictions (requires epidemiological expertise not present)
- Census tract granularity in documents (aggregate to Tribal level only via crosswalk)
- Interactive GIS/map interface (incompatible with static GitHub Pages deployment)
- Proprietary vulnerability scoring methodology (federal credibility requires FEMA/CDC methodology citation)
- Climate adaptation recommendations (requires local knowledge outside scope)

**Critical path (feature dependency chain):**
TS-2 (Expanded NRI) + TS-1 (CDC SVI) -> TS-3 (Composite Score) -> TS-4 (DOCX) -> TS-6 (Website) -> DF-6 (Visualization)
DF-1 (NOAA Projections) is an independent track that enriches TS-3 and DF-3 but is not required for any table stakes feature.

---

### Architecture (from ARCHITECTURE.md)

**Core pattern: reuse everything.** The existing `tribal_county_area_weights.json` crosswalk serves all new data sources. The existing `_load_tribe_cache()` method in the orchestrator handles vulnerability cache loading identically to hazards and awards. The existing `HazardProfileBuilder` pattern clones directly to `VulnerabilityProfileBuilder`. The existing `DocumentTypeConfig` frozen dataclass extends cleanly with one new boolean field.

**New files to create (8):**
- `scripts/download_climate_projections.py` — LOCA2 NetCDF download and extraction to county JSON
- `scripts/download_svi_data.py` — SVI CSV download (or documented manual procedure)
- `scripts/populate_vulnerability.py` — orchestrate all sources into 592 vulnerability_profiles/
- `src/packets/vulnerability.py` — VulnerabilityProfileBuilder (mirrors HazardProfileBuilder)
- `src/schemas/vulnerability.py` — Pydantic models for vulnerability profile (DEBT-01 mitigation: schema before implementation)
- `src/packets/docx_vulnerability_sections.py` — 4 vulnerability section renderers
- `docs/web/js/vulnerability.js` — website vulnerability card rendering
- DOC_E definition in `src/packets/doc_types.py`

**Files to modify (10):**
- `src/packets/hazards.py` — expand `_load_nri_county_data()` (EAL_VALB/P/A, RISK_NPCTL, RESL_VALUE)
- `src/paths.py` — add SVI_DIR, CLIMATE_DIR, VULNERABILITY_PROFILES_DIR, helper function
- `src/packets/context.py` — add `vulnerability_profile: dict` field
- `src/packets/orchestrator.py` — load vulnerability cache in `_build_context()`
- `src/packets/docx_engine.py` — import and call vulnerability renderers
- `src/packets/docx_sections.py` — expand hazard summary with EAL consequence breakdown
- `src/packets/doc_types.py` — add DOC_E, add `include_vulnerability: bool = False` flag
- `scripts/build_web_index.py` — include vulnerability summary fields in tribes.json
- `docs/web/js/app.js` — render vulnerability data in Tribe cards
- `docs/web/css/style.css` — vulnerability visualization styles

**Composite vulnerability score formula:**

| Component | Source | Weight |
|-----------|--------|--------|
| Hazard Exposure | NRI RISK_NPCTL / 100 | 0.30 |
| Social Vulnerability | CDC SVI RPL_THEMES (0–1) | 0.25 |
| Climate Trajectory | Normalized LOCA2 severity index | 0.25 |
| Adaptive Capacity Deficit | 1 - (NRI RESL_SCORE / 100) | 0.20 |

Five rating tiers matching NRI methodology: Very High (≥0.80), High (≥0.60), Moderate (≥0.40), Low (≥0.20), Very Low (<0.20).

**Note:** If LOCA2 data is deferred to v1.5, Climate Trajectory weight (0.25) redistributes to Hazard Exposure (0.40) and Social Vulnerability (0.35). The formula degrades gracefully.

**Key architectural decision: separate vulnerability_profiles/ directory.** Do NOT merge into hazard_profiles/. Reasons: different update cadence (SVI biannual, climate static, NRI annual); independent validation and coverage reporting; backward compatibility with 964 existing tests; schema clarity (SVI themes and climate projections are structurally different from NRI hazard arrays). Expanded NRI fields (EAL breakdowns, percentiles) DO go in existing hazard_profiles/ because they extend the same source CSV with the same area-weighting logic.

---

### Pitfalls (from PITFALLS.md)

**Critical pitfalls — recovery cost HIGH or VERY HIGH:**

| ID | Pitfall | Prevention |
|----|---------|------------|
| CRIT-01 | Confusing FEMA NRI SOVI with CDC SVI. As of NRI v1.19+, SOVI_SCORE already IS CDC SVI. Double-counting creates contradictory social vulnerability figures. | Verify NRI version during Phase 19. Treat CDC SVI as enrichment (theme decomposition), not a parallel index. Document the relationship explicitly. |
| CRIT-02 | Deficit framing of Tribal vulnerability. "High vulnerability," "at-risk populations," "low resilience" undermine sovereignty-first posture and make documents unusable for advocacy. | Build `VULNERABILITY_FRAMING` constants module before writing any renderer. "Disproportionate exposure to climate hazards," not "vulnerable." Frame resilience scores as "federal measurement gaps," not deficiencies. |
| CRIT-03 | CDC SVI tribal census tracts are UNRANKED by CDC design. Using tribal tract data produces null percentiles or methodologically invalid rankings. | Use COUNTY-level SVI only, through the existing area-weighted crosswalk. Never use the tribal tract SVI database. |
| CRIT-04 | NRI v1.20 schema instability: RAPT migration may change download URLs; Connecticut replaced county FIPS with 8 planning regions. | Pin NRI version + SHA256 checksum; add CSV schema validation on load; add CT planning region FIPS mapping. |

**High-severity integration pitfalls:**

| ID | Pitfall | Prevention |
|----|---------|------------|
| INT-01 | Extending NRI CSV parser may silently break existing field extraction for 964 tests. | Extend `_load_nri_county_data()` incrementally. Add new fields in a sub-dict. Diff all 592 hazard_profiles/ before/after. Add regression test for existing fields. |
| INT-02 | Pre-cache pattern violation — network imports appearing in src/packets/. | Add compliance test scanning for network imports in src/packets/ (mirrors existing test_xcut_compliance.py). Write it BEFORE writing any new packet code. |
| INT-03 | Area-weighted aggregation invalid for climate extremes. Days above threshold should not be averaged — a Tribe exposed to extreme heat in 40% of its land is not experiencing "moderate" extreme heat. | Per-variable aggregation rules: means use area-weighted average; extremes use area-weighted MAX or worst-case county; counts report both aggregate and range. |
| INT-04 | Audience air gap leakage in vulnerability sections. Strategy language ("leverage this data") or sensitive SVI decomposition leaking into congressional documents. | Update audience filtering tests with vulnerability-specific forbidden words before writing renderers. Write congressional (facts-only) version first. |
| INT-05 | Website tribes.json payload explosion if full climate projection arrays are embedded. Rural Tribal communities often access site on low-bandwidth connections. | Summary indicators only in tribes.json (composite rating, top hazard, SVI overall). Full vulnerability detail in per-Tribe JSON files loaded on-demand. Measure payload; fail build if tribes.json > 1.5 MB. |

**Technical debt patterns to prevent:**

| ID | Pattern | Prevention |
|----|---------|------------|
| DEBT-01 | Climate projection temporal schema complexity. Multi-scenario, multi-period data does not fit flat cache schema; flat key explosion or information loss both occur without planning. | Define JSON schema (Pydantic model in src/schemas/vulnerability.py) BEFORE writing any population script. Use arrays of projection objects, not flattened key names. |
| DEBT-02 | Crosswalk proliferation. Each new data source adding its own geography bridge. | Formalize county FIPS as the universal intermediate layer. All new sources route through existing tribal_county_area_weights.json. One source of geographic truth. |
| DEBT-03 | DocxEngine section creep. Vulnerability sections add N new render calls to generate(), expanding a method already at risk of becoming monolithic. | Treat vulnerability as expansion of the hazard section; use section registry pattern. Keep TribePacketContext extensible by nesting data under existing dict fields where possible. |

---

## Implications for Roadmap

### Recommended Phase Structure

Research strongly indicates a 4-phase structure following the proven layer-by-layer build order from ARCHITECTURE.md. Each phase delivers working, testable output before the next begins. Phase numbers continue from v1.3 (Phases 15–18), starting at Phase 19.

---

**Phase 19: Data Foundation**

Rationale: Everything downstream depends on correct, validated data in caches. Build and validate all data extraction before touching any document rendering. Lowest risk items first (expanded NRI); highest risk (LOCA2 NetCDF) treated as conditional. The Pydantic schema must be written before any population script to prevent DEBT-01.

Deliverables:
- Expanded NRI field extraction in hazards.py (EAL_VALB/P/A, RISK_NPCTL, RESL_VALUE, per-hazard EAL breakdowns) — backward-compatible schema extension
- Regenerated hazard profiles with validation that existing fields are unchanged
- CDC/ATSDR SVI 2022 county CSV downloaded and parsed to per-county JSON
- USGS LOCA2 NetCDF file inspected; extraction script written and validated against real file (conditional: proceed if variable names and dimension structure match CMIP6 assumptions; defer to v1.5 if significantly different)
- `src/schemas/vulnerability.py` Pydantic models defining the full cache schema upfront (DEBT-01 mitigation)
- `scripts/populate_vulnerability.py` producing 592 vulnerability_profiles/ JSON files
- Composite vulnerability score computed per Tribe (FEMA methodology, 5 tiers)
- Vulnerability coverage report (SVI coverage %, climate coverage %, expanded NRI coverage %)
- Data provenance metadata in all cache files (TS-5)
- NRI version pinning + SHA256 checksum validation (CRIT-04 mitigation)
- Connecticut NRI v1.20 planning region mapping (CRIT-04 mitigation)
- VULNERABILITY_FRAMING constants module established (CRIT-02 foundation — must exist before Phase 21)

Features: TS-2, TS-1, TS-3, TS-5
Pitfalls: CRIT-01, CRIT-03, CRIT-04, INT-01, INT-02 (compliance test), DEBT-01, DEBT-02, PERF-01, PERF-02
Research flag: NEEDS phase research for LOCA2 NetCDF before writing extraction code. Inspect file with `xarray.open_dataset(path); print(ds)` to confirm variable names, multi-model mean structure, and dimension layout. Also verify NRI v1.20 CSV headers for new expanded fields and SVI 2022 Theme 3 column names against actual downloads.

---

**Phase 20: Pipeline Integration**

Rationale: Wire vulnerability data into the document context pipeline before writing any renderers. Validate that context is correctly populated for all 592 Tribes before touching DocxEngine. Integration errors caught here are cheap to fix; errors discovered during rendering are expensive.

Deliverables:
- `src/paths.py` new constants (SVI_DIR, CLIMATE_DIR, VULNERABILITY_PROFILES_DIR, vulnerability_profile_path())
- `src/packets/context.py` vulnerability_profile field addition
- `src/packets/orchestrator.py` vulnerability cache loading in _build_context() (identical pattern to hazard/award loading)
- `src/packets/doc_types.py` DOC_E definition + include_vulnerability: bool = False flag (backward-compatible)
- Compliance test: network imports blocked in src/packets/ (INT-02 mitigation — write before Phase 21 begins)
- Audience filtering tests updated with vulnerability-specific forbidden words (INT-04 early setup)
- Integration tests: vulnerability_profile populated correctly for 5 representative Tribes
- CLI display: _display_vulnerability_summary() method mirrors existing _display_hazard_summary()

Features: Infrastructure only (no user-facing features yet)
Pitfalls: INT-02, INT-04 (test setup)
Research flag: Standard patterns from Phases 12–15. No phase research needed.

---

**Phase 21: Document Rendering**

Rationale: Render vulnerability data in documents only after the pipeline is validated end-to-end. Congressional version (facts only) before internal version (strategy framing), per INT-04 mitigation. Doc A/B subsections first (compact vulnerability block within existing hazard section), Doc E standalone second.

Deliverables:
- `src/packets/docx_vulnerability_sections.py` with 4 renderers:
  - `render_vulnerability_overview()` — composite score, rating badge, data source citations with version
  - `render_climate_projections_section()` — temperature/precipitation change table, scenario range (always show range, never single value — SEC-02 mitigation)
  - `render_svi_breakdown()` — 4-theme breakdown (Doc A/C internal only; Doc B/D shows overall SVI composite only — SEC-01 mitigation)
  - `render_vulnerability_synthesis()` — grant-ready narrative paragraph (DF-2)
- Integration into Doc A and Doc B (compact vulnerability subsection after hazard summary) (TS-4)
- EAL consequence-type breakdown table: buildings/population/agriculture per top hazard (DF-7)
- Comparative peer context sentence: percentile among 592 Tribes + ecoregion group (DF-5)
- Doc E standalone vulnerability assessment, full-detail rendering, wired into orchestrator
- Sovereignty framing throughout using VULNERABILITY_FRAMING constants (CRIT-02 completion)
- Structural validator extended to validate Doc E
- Test additions: vulnerability section renderers, Doc E generation, audience air gap enforcement for vulnerability content, temperature unit consistency (Fahrenheit for U.S. audience), dollar formatting via utils.format_dollars() only

Features: TS-4, DF-7, DF-2, DF-5, Doc E
Pitfalls: CRIT-02, INT-03, INT-04, SEC-01, SEC-02, DEBT-03, DONE-02
Research flag: Standard rendering patterns. Review actual FEMA BRIC and EPA Environmental Justice grant application formats during implementation to inform grant narrative templates (DF-2).

---

**Phase 22: Website and Polish**

Rationale: Website changes are additive and lower-risk than document rendering. Build last to avoid coupling web changes to document pipeline. Static site constraint (no server, tribes.json payload budget) drives design choices — the on-demand loading pattern is required, not optional.

Deliverables:
- `scripts/build_web_index.py` extended with vulnerability summary fields (composite rating, top hazard, SVI overall indicator)
- `docs/web/js/app.js` vulnerability badge/summary in Tribe cards (TS-6)
- `docs/web/css/style.css` vulnerability badge styles, color coding, dark mode support
- tribes.json payload size validation: fail build if > 1.5 MB (INT-05 mitigation)
- Per-Tribe detail JSON files for on-demand loading (not embedded in tribes.json)
- Chart.js hazard radar chart and SVI theme bar chart, progressive enhancement (DF-6 — conditional on scope; defer if Phase 21 is large)
- Vulnerability indicators ARIA-compliant, mobile-responsive (rural communities are often mobile-first)
- End-to-end coverage validation: all sources tracked in vulnerability_coverage_report
- DONE-01 through DONE-04 checklist verification from PITFALLS.md

Features: TS-6, DF-6 (conditional)
Pitfalls: INT-05, DONE-04
Research flag: Standard static site patterns. No phase research needed.

---

### Phase Ordering Rationale

The data-first, render-second ordering is not preference — it is the established TCR pattern proven in Phases 12 and 13 for awards and hazards respectively. Attempting to render before caches exist forces mock data that diverges from production JSON structure and produces integration surprises late in the phase.

The INT-02 compliance test (no network imports in src/packets/) must be written at the start of Phase 20, before Phase 21 begins writing renderers. Once Phase 21 renderers exist, a failing compliance test requires refactoring already-written code.

VULNERABILITY_FRAMING constants (CRIT-02 mitigation) must be established in Phase 19, reviewed before Phase 21 begins, and enforced from the first renderer written. Retroactively replacing framing language across all renderers after the fact requires full document re-generation and stakeholder review.

**LOCA2 conditional decision point:** If Phase 19 NetCDF inspection reveals the variable names, multi-model mean structure, or dimension layout are materially different from CMIP6 conventions, climate projections should be descoped from Phase 19 and planned as a standalone v1.5 phase. The composite vulnerability score degrades gracefully (SVI + expanded NRI components only, reweighted). Everything else in v1.4 is fully independent of LOCA2.

**Dependency graph:**
```
Phase 19 (Data Foundation)
  -> Phase 20 (Pipeline Integration)
      -> Phase 21 (Document Rendering)
          -> Phase 22 (Website and Polish)

Phase 21 and Phase 22 can partially overlap if Doc E rendering
completes before website work begins (they touch different files).
```

---

### Research Flags by Phase

| Phase | Research Needed? | Topic |
|-------|-----------------|-------|
| Phase 19 | YES — before writing extraction code | Inspect LOCA2 NetCDF: `xarray.open_dataset(path); print(ds)` to confirm variable names (tasmax, tasmin, pr), whether WMMM is a pre-computed variable or requires model-dimension mean, and dimension structure. |
| Phase 19 | YES — before NRI expansion | Verify NRI v1.20 CSV column headers for expanded fields: EAL_VALB, EAL_VALP, EAL_VALA, RISK_NPCTL, RESL_VALUE, SOVI_VALUE. STACK.md rates these MEDIUM confidence (based on v1.18 naming, not verified against v1.20 CSV). |
| Phase 19 | YES — during SVI download | Verify CDC SVI 2022 column names for Theme 3 (Racial and Ethnic Minority Status — changed from prior SVI years). Must confirm against actual CSV headers before writing parser. |
| Phase 19 | YES — quick check | Confirm whether BRIC sub-category scores exist in NRI v1.20 CSV. If yes, add DF-4 to scope. If no, keep deferred. |
| Phase 20 | NO | Standard orchestrator/context patterns; identical to Phases 12–15 implementation. |
| Phase 21 | NO | Standard DOCX rendering patterns. Review grant application formats during implementation for DF-2 narrative templates. |
| Phase 22 | NO | Standard static site patterns. |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Stack — xarray + netCDF4 | HIGH | Verified PyPI pages; Python 3.12 compatibility confirmed; Windows wheels confirmed; v2026.1.0 current; dependency conflict check clean via existing geopandas |
| Stack — SVI and expanded NRI | HIGH | No new libraries; CDC SVI CSV format verified from official documentation; existing NRI parsing pattern confirmed via codebase inspection |
| Stack — LOCA2 NetCDF specifics | MEDIUM | ScienceBase catalog verified (sizes, GEOID keying, DOI); but variable names (tasmax, tasmin, pr) and multi-model mean structure are assumed from CMIP6 conventions, not verified against actual file |
| Features — table stakes (TS-1 through TS-6) | HIGH | All follow established patterns; data sources confirmed available; dependencies well-understood |
| Features — differentiators (DF-1) | MEDIUM | LOCA2 data confirmed to exist at county level; bulk download workflow needs Phase 19 validation |
| Features — differentiators (DF-4) | LOW | BRIC sub-scores in NRI CSV not confirmed; may require separate USC HVRI data download |
| Architecture — all pipeline patterns | HIGH | Direct codebase inspection of hazards.py, orchestrator.py, docx_engine.py, context.py, paths.py, doc_types.py — all patterns verified from production code |
| Architecture — Doc E | HIGH | Follows DOC_A through DOC_D frozen dataclass pattern exactly; backward-compatible extension verified |
| Pitfalls — CRIT-01/02/03/04 | HIGH | Verified from FEMA NRI v1.19 change notes (official), CDC SVI FAQ (official), direct codebase inspection |
| Pitfalls — Alaska LOCA2 gap | HIGH | LOCA2 CONUS-only coverage is confirmed in USGS documentation |
| Pitfalls — NRI v1.20 CT planning regions | MEDIUM-HIGH | Confirmed from FEMA release notes; impact on existing TCR crosswalk not yet tested against actual data |
| CDC SVI download stability | MEDIUM | URL has been stable since 2014; no programmatic bulk API exists; manual download is required |

**Overall confidence: MEDIUM-HIGH.** Patterns are solid; data sources are confirmed; architecture is a clean extension of Phase 13. The two meaningful uncertainties (LOCA2 NetCDF internal structure; NRI v1.20 expanded field names) are both resolvable within the first hours of Phase 19 by inspecting the actual files. Neither blocks roadmap creation.

---

## Gaps to Address

| Gap | Severity | Resolution |
|-----|----------|-----------|
| LOCA2 NetCDF variable names unconfirmed | HIGH | Phase 19 day 1 — inspect file before writing any xarray extraction code |
| LOCA2 multi-model mean structure unknown | HIGH | Phase 19 day 1 — `print(ds)` reveals whether WMMM is a variable or a model dimension |
| NRI v1.20 expanded field names (EAL_VALB, RISK_NPCTL, etc.) | MEDIUM | Phase 19 start — check CSV headers against assumptions |
| CDC SVI 2022 Theme 3 column names (changed from prior years) | MEDIUM | Phase 19 during SVI download — verify against actual CSV |
| BRIC sub-category score availability in NRI CSV | LOW-MEDIUM | Phase 19 quick scan — determines DF-4 in/out of scope |
| Connecticut NRI v1.20 planning region impact on crosswalk | MEDIUM | Phase 19 — verify CT Tribe crosswalk entries; add FIPS mapping if needed |
| Alaska LOCA2 coverage (CONUS only) | MEDIUM | Phase 19 — accept partial coverage for AK Tribes; flag in vulnerability coverage report; add AK note to Doc E |
| VULNERABILITY_FRAMING approved language | HIGH | Phase 19 design decision (before Phase 21 begins rendering) — must be agreed upon before any renderer is written |
| CDC SVI download is manual (no stable programmatic URL) | LOW | Phase 19 — document the exact download procedure; add URL to config for flexibility |
| Grant narrative templates for DF-2 | LOW | Phase 21 implementation — review FEMA BRIC and EPA EJ grant application formats |

---

## Sources

### Aggregated from Research Files

**HIGH confidence — verified official sources:**
- USGS CMIP6-LOCA2 County Spatial Summaries: https://www.sciencebase.gov/catalog/item/673d0719d34e6b795de6b593
- USGS LOCA2 data page: https://www.usgs.gov/data/cmip6-loca2-spatial-summaries-counties-tiger-2023-1950-2100-contiguous-united-states
- CDC/ATSDR SVI Data Download: https://svi.cdc.gov/dataDownloads/data-download.html
- CDC SVI 2022 Documentation PDF: https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf
- CDC/ATSDR SVI FAQ (tribal tracts unranked): https://www.atsdr.cdc.gov/place-health/php/svi/svi-frequently-asked-questions-faqs.html
- FEMA NRI Data (v1.20 December 2025): https://www.fema.gov/about/openfema/data-sets/national-risk-index-data
- FEMA NRI v1.19 Change Summary (SVI methodology change): https://hazards.fema.gov/nri/change-summary-v119
- xarray on PyPI v2026.1.0: https://pypi.org/project/xarray/
- netCDF4 on PyPI v1.7.4: https://pypi.org/project/netCDF4/
- NOAA CDO API documentation: https://www.ncdc.noaa.gov/cdo-web/webservices/v2
- Existing codebase: `src/packets/hazards.py` (NRI field patterns, area-weighted aggregation, USFS override)
- Existing codebase: `scripts/build_area_crosswalk.py` (crosswalk architecture, dual CRS, atomic writes)
- Existing codebase: `src/packets/orchestrator.py` (_build_context, _load_tribe_cache patterns)
- Existing codebase: `src/packets/context.py` (TribePacketContext structure and field pattern)
- Existing codebase: `src/packets/doc_types.py` (DocumentTypeConfig frozen dataclass, DOC_A–D)
- Existing codebase: `src/paths.py` (35 path constants pattern)
- Existing codebase: `docs/web/js/app.js` (static site, vanilla JS, tribes.json on-load pattern)

**MEDIUM confidence — verified with caveats:**
- NOAA Climate Explorer: https://crt-climate-explorer.nemac.org/about/ (no bulk API confirmed)
- LOCA2 downscaling methodology: https://loca.ucsd.edu/
- U.S. Climate Resilience Toolkit vulnerability framework: https://toolkit.climate.gov/assess-vulnerability-and-risk
- Tribal Climate Adaptation Guidebook: https://tribalclimateadaptationguidebook.org/step-3-assess-vulnerability/
- UW Climate Impacts Group Tribal resources: https://cig.uw.edu/resources/tribal-vulnerability-assessment-resources/
- FEMA NRI Community Resilience (BRIC): https://hazards.fema.gov/nri/community-resilience

**LOW confidence — verify during implementation:**
- NOAA SLR scenario data exact download format (not confirmed)
- FEMA RAPT migration timeline (URL redirects observed; completion date uncertain)
- LOCA2 exact variable names in county NetCDF (assumed from CMIP6 conventions — verify by opening file)
- CDC SVI 2022 Theme 3 exact column names (changed from prior years — verify against CSV)
- NRI v1.20 Connecticut planning region impact on existing crosswalks (inferred from release notes, not tested)
- BRIC sub-category scores in NRI CSV (not confirmed in any documentation)

---

*All research files written 2026-02-17. SUMMARY.md synthesized 2026-02-17.*
*v1.3 baseline: 18 phases, 66 plans, 115 requirements, 964 tests, ~38,300 LOC Python, 102 source files.*
*v1.4 target: Phases 19–22, ~8 new source files, ~10 modified source files, ~1 new document type (Doc E), 592 new vulnerability_profiles/.*
