# Architecture Delta Report
## Phase 18.5 | TCR Policy Scanner v1.4 Climate Vulnerability Intelligence

**Compiled:** 2026-02-17
**Agents:** Sovereignty Scout, Fire Keeper, River Runner, Horizon Walker
**Decision:** GO with 8 corrections

---

## SECTION 1: DATA SOURCE STATUS

| Source | Architecture Assumption | Actual Status | Action |
|--------|------------------------|---------------|--------|
| FEMA NRI expanded fields | `RISK_NPCTL` exists | **DOES NOT EXIST** -- only `RISK_SPCTL` (state percentile) | Compute national percentile from `RISK_SCORE` at build time |
| FEMA NRI EAL components | `EAL_VALB/P/A` exist | **CONFIRMED** in NRI v1.20 | No change |
| FEMA NRI demographics | `POPULATION`, `BUILDVALUE`, `AREA` | **CONFIRMED** | No change |
| CDC SVI 2022 | Current release, RPL_THEMES usable | **SVI 2022 CONFIRMED current** but `RPL_THEMES` includes excluded Theme 3 | Compute custom 3-theme composite from Themes 1+2+4 |
| USGS LOCA2 | NetCDF county summaries | **CONFIRMED but DEFERRED to v1.5+** -- CSV alternative exists in Thresholds dataset | Deferral validated; eliminates xarray/netCDF4 dependency |
| FEMA FRI | Archived, do not use | **CONFIRMED UNAVAILABLE** since Feb 2025 | No change needed |
| OpenFEMA NFIP (FLOOD-01) | Available | **CONFIRMED** -- free API, no key | No change |
| OpenFEMA Disasters (FLOOD-02) | Available | **CONFIRMED** -- free API | No change |
| FEMA NFHL (FLOOD-03) | Available | **CONFIRMED** with WFS 1000-feature limit | Reduce scope to county-level summaries |
| USGS Water Services (FLOOD-04) | `waterservices.usgs.gov` | **MIGRATING** -- decommission early 2027 | Build against NEW API: `api.waterdata.usgs.gov` |
| NOAA Atlas 14 (FLOOD-05) | Current | **BEING SUPERSEDED** -- Atlas 15 in peer review 2026 | Build against Atlas 14, document Atlas 15 migration |
| NOAA CO-OPS (FLOOD-06) | Available | **CONFIRMED** -- recently migrated to cloud | No change |
| US Drought Monitor (CLIM-01) | Available | **CONFIRMED** -- county-level, weekly | No change |
| NOAA NCEI CDO (CLIM-02) | CDO API v2 | **DEPRECATED** -- new endpoint available | Use `ncei.noaa.gov/access/services/data/v1` |
| NWS API (CLIM-03) | Available | **CONFIRMED** | No change |
| WA DNR Landslide (GEO-01) | Available | **CONFIRMED** -- ESRI geodatabase format | Consider deferring (WA/OR only) |
| USGS 3DEP (GEO-02) | Available | **CONFIRMED** but requires research-grade processing | **RECOMMEND DEFER to v1.5+** |
| DHS HIFLD (INFRA-01) | Available | **CONFIRMED** -- open datasets freely available | Use open datasets only (T0 boundary) |

**Summary:** 15 CONFIRMED, 1 CONFIRMED DEFERRED (LOCA2), 1 CONFIRMED UNAVAILABLE (FRI). Core pipeline (NRI + SVI + composite) is go.

---

## SECTION 2: CODEBASE PATTERN CONFORMANCE

| Pattern | Status | Details |
|---------|--------|---------|
| HazardProfileBuilder template | **MATCHES** | 9-step sequence fully documented: init -> crosswalk -> area weights -> CSV parse -> aggregation -> override -> atomic write -> path guard -> coverage report |
| `_safe_float()` NaN/Inf guard | **MATCHES** | Returns default for None, "", NaN, Inf. VulnerabilityProfileBuilder MUST reuse or replicate |
| Area-weighted crosswalk | **MATCHES** | `tribal_county_area_weights.json` reusable for all county-keyed data sources |
| Rating derivation | **MATCHES** | Ratings RE-DERIVED from weighted scores, never averaged from source strings |
| Atomic JSON write | **MATCHES** | `tempfile.mkstemp()` + `os.replace()` + cleanup in except. Mandatory for all new writers |
| Path traversal guard | **MATCHES** | `Path(tribe_id).name` + reject `..`. Mandatory for all new writers |
| TribePacketContext | **MATCHES** | Adding `vulnerability_profile: dict` creates zero collisions. ~15 MB memory for 592-Tribe batch |
| Renderer signatures | **MATCHES** | `(document, context, style_manager, doc_type_config=None) -> None` is universal |
| DocxEngine render sequence | **MATCHES** | Vulnerability inserts between step 7 (hazard summary) and step 8 (structural asks) |
| DocumentTypeConfig | **MATCHES** | Frozen dataclass. DOC_E follows DOC_A-D pattern. `include_vulnerability: bool = False` is safe |
| Orchestrator cache loading | **MATCHES** | `_load_tribe_cache()` generic loader handles all per-Tribe JSON. Zero new infrastructure |
| Path constants | **MATCHES** | 6 new constants + 1 helper needed (SVI_DIR, SVI_COUNTY_PATH, CLIMATE_DIR, CLIMATE_SUMMARY_PATH, VULNERABILITY_PROFILES_DIR, CLIMATE_RAW_DIR) |
| FY26 hardcoding | **DRIFT** | 22 instances across 8 files. `doc_types.py` (8), `docx_engine.py` (2), `docx_template.py` (1) are highest priority |

---

## SECTION 3: SCHEMA RECOMMENDATIONS

| Model | Status | Notes |
|-------|--------|-------|
| `SVIProfile` (3 themes, not 4) | **APPROVED** | Theme 3 excluded. Custom `tribal_svi_composite` from Themes 1+2+4 average |
| `NRIExpandedProfile` | **NEEDS REVISION** | Use computed national percentile, not `RISK_NPCTL`. Store as `risk_national_percentile` |
| `ClimateProjectionProfile` | **APPROVED (placeholder)** | Structurally present, zeroed in v1.4. Deferred to v1.5+ |
| `CompositeVulnerability` | **NEEDS REVISION** | 3-component formula (0.40/0.35/0.25), not 4-component. `data_completeness_factor` for partial data |
| `VulnerabilityProfile` | **APPROVED** | Top-level container with metadata and coverage flags |
| Flood models (6) | **APPROVED** | Phase 20 schemas ready |
| Climate/weather models (4) | **APPROVED** | Phase 21 schemas ready |
| Infrastructure models (4) | **APPROVED** | Phase 21 schemas ready |

**Total: 37 Pydantic v2 models across 4 schema modules.**

### Composite Score Formula (Revised for v1.4)

**v1.4 (3-component, LOCA2 deferred):**
```
Composite = 0.40 * hazard_exposure + 0.35 * social_vulnerability + 0.25 * adaptive_capacity_deficit
```

- **Hazard Exposure (0.40):** Computed national percentile from NRI `RISK_SCORE` rank across ~3,200 counties
- **Social Vulnerability (0.35):** Custom Tribal SVI = average(RPL_THEME1, RPL_THEME2, RPL_THEME4)
- **Adaptive Capacity Deficit (0.25):** 1 - (NRI `RESL_SCORE` / 100)

**v1.5+ (4-component, with LOCA2):**
```
Composite = 0.30 * hazard + 0.25 * social + 0.25 * climate + 0.20 * adaptive_deficit
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| Missing SVI data | Use 2-component score (hazard + adaptive), set `data_completeness_factor = 0.67` |
| NRI sentinel values (-999) | `_safe_float()` returns 0.0; flag in coverage report |
| Alaska Tribe with partial coverage | Compute from available components; explicit `coverage_status: "partial"` |
| Zero area weight for all counties | Do NOT compute score; `coverage_status: "unavailable"` |
| Multi-county conflicting ratings | Weighted average of scores; re-derive rating (never average rating strings) |

---

## SECTION 4: NARRATIVE FRAMING DECISIONS

### Primary Recommendation: Option D (Hybrid Approach)

| Context | Framing |
|---------|---------|
| Section headings | "Climate Resilience Investment Profile" |
| Rating label | "Resilience Investment Priority: High" |
| Explanatory text | "disproportionate exposure to climate hazards" |
| Federal methodology references | "vulnerability" only inside proper nouns (CDC SVI, FEMA NRI) |
| Caveat integration | Integrated into narrative flow, not footnoted |
| Doc B air gap | Composite rating + source table only. Zero strategy language, zero SVI decomposition |

### Alaska Narrative Strategy (229 Tribes, 38.7%)

- **Never** use "data not available" -- every Tribe sees meaningful content
- **Three tiers:** Full data, partial data, minimal data
- **Data gaps framed as federal infrastructure failures**, not Tribal data limitations
- **Template language:** "Federal climate projection datasets do not yet provide county-level coverage for Alaska. This is a federal data gap, not a reflection of your community's climate exposure."

### REG-04 Vocabulary Module

- Context-sensitive replacement engine (not simple word-swap)
- "vulnerability" allowed only in federal proper nouns
- Approved headings: "Climate Resilience Investment Profile", "Disproportionate Climate Exposure Assessment"
- Forbidden in Doc B: SVI theme decomposition, strategy language, organizational names, resilience framing

---

## SECTION 5: PHASE 19-24 MODIFICATIONS

| Phase | Status | Changes |
|-------|--------|---------|
| **19: Schema & Core Data** | **MODIFY** | (1) Compute national percentile from RISK_SCORE, not RISK_NPCTL. (2) Custom 3-theme Tribal SVI, not RPL_THEMES. (3) 3-component composite formula. (4) Fix 22 FY26 hardcodings before defining DOC_E |
| **20: Flood & Water** | **MODIFY** | (1) FLOOD-03 NFHL: reduce to county-level summaries. (2) FLOOD-04: build against NEW USGS API. (3) FLOOD-05: document Atlas 15 migration |
| **21: Climate & Geologic** | **MODIFY** | (1) CLIM-02: use new NCEI endpoint. (2) GEO-02 3DEP: **DEFER to v1.5+**. (3) Consider deferring GEO-01 landslides (WA/OR only serves limited subset) |
| **22: Vulnerability Profiles** | **MODIFY** | (1) 3-component composite. (2) Coverage report must flag Alaska partial coverage. (3) Add data source health-check script |
| **23: Document Rendering** | **MODIFY** | (1) Adopt Option D hybrid framing. (2) Extend Doc B air gap for vulnerability. (3) Alaska 3-tier narrative |
| **24: Website & Delivery** | **MODIFY** | (1) Horizontal bar charts, not radar. (2) Colorblind-safe palette. (3) Handle partial data gracefully |

### Pre-Phase 19 Technical Debt (DO FIRST)

1. Fix 22 hardcoded "FY26" strings -- especially `doc_types.py` (8 instances) and `docx_engine.py` (2 instances)
2. Add `vulnerability_profile: dict = field(default_factory=dict)` to `TribePacketContext`
3. Add 6 path constants + 1 helper to `src/paths.py`

### Deferrals to v1.5+

- USGS LOCA2 climate projections (Alaska gap + complexity) -- CSV Thresholds path identified for when ready
- USGS 3DEP terrain data (requires research-grade geospatial processing)
- HDD/CDD energy burden metrics (not in LOCA2 Thresholds; source from NOAA Climate Normals in v1.5+)
- Additional state landslide inventories beyond WA/OR

---

## SECTION 6: GO/REVISE DECISION

### **GO** -- with 8 corrections applied

The v1.4 architecture is sound. The core pipeline (NRI expansion + SVI integration + composite scoring + document rendering + website) is validated against the actual codebase and current data sources. The 6-phase build plan (19-24) can proceed with the corrections documented above.

**What makes this a GO:**

1. **The codebase is pattern-consistent.** HazardProfileBuilder provides a complete, tested template. VulnerabilityProfileBuilder follows it step-for-step.
2. **The crosswalk is reusable.** All new data sources key by county FIPS and flow through the existing area-weighted crosswalk. Zero new geographic infrastructure.
3. **The schema architecture is defined.** 37 Pydantic v2 models across 4 modules, with edge case handling for every known gap.
4. **The framing is sovereignty-first.** Option D (Hybrid) centers action over label, preserves federal credibility, and passes the Tribal Leader test.
5. **The Alaska strategy is honest.** 229 Tribes get meaningful content even with partial data. Gaps are named as federal failures, not Tribal limitations.

**What the corrections ensure:**

1. No silent data errors (RISK_NPCTL -> computed national percentile)
2. No Theme 3 tautology (custom 3-theme Tribal SVI)
3. No deprecated APIs (USGS Water, NOAA NCEI)
4. No technical debt inheritance (FY26 hardcoding fixed before DOC_E)
5. No deficit narratives (hybrid framing vocabulary)

### Test Target

| Phase | New Tests | Running Total |
|-------|-----------|---------------|
| 19 | ~60 | ~1,024 |
| 20 | ~50 | ~1,074 |
| 21 | ~40 | ~1,114 |
| 22 | ~50 | ~1,164 |
| 23 | ~30 | ~1,194 |
| 24 | ~20 | ~1,214 |

---

## Agent Deliverables

| Agent | Report | Lines | Key Contribution |
|-------|--------|-------|-----------------|
| Sovereignty Scout | `sovereignty-scout-report.md` | 405 | 8 architecture corrections, Alaska coverage analysis, 17 data sources validated |
| Fire Keeper | `fire-keeper-report.md` | 917 | 9-step builder template, 10-renderer catalog, 22 FY26 debt instances, dependency matrix |
| River Runner | `river-runner-report.md` | ~2,258 | 37 Pydantic models, 3-component composite formula, edge case matrix, test architecture |
| Horizon Walker | `horizon-walker-report.md` | ~1,080 | 4 framing options with example paragraphs, Alaska narrative strategy, REG-04 vocabulary spec |

---

*Architecture Delta Report | Phase 18.5 | 2026-02-17*
*Every correction serves the Tribal Leader who will hold this document.*
*Sovereignty is the innovation. Relatives, not resources.*
