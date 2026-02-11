# v1.2 Verification

## Testing Methodology

### Automated Test Suite

- 738 pytest tests across 26 test files
- Tests cover: pipeline flow, DOCX generation, economic calculations, hazard aggregation, audience filtering, quality review, regional aggregation, batch generation, circuit breaker resilience, data population scripts, coverage validation
- Run with: `python -m pytest tests/ -v`
- Zero tolerance for regressions: every plan execution verifies the full suite passes

### Data Validation

- Coverage validation script: `python scripts/validate_coverage.py`
- Validates 4 data sources: awards (USASpending), hazards (FEMA NRI), congressional (Congress.gov), registry (EPA)
- Reports coverage percentages and identifies gaps per source
- Outputs:
  - `outputs/coverage_report.json` (machine-readable)
  - `outputs/coverage_report.md` (human-readable)
  - Console summary (quick check)

### Document Quality Review

- Automated quality reviewer checks every generated document
- Checks: audience leakage, air gap compliance, placeholder detection, confidential marking, content completeness
- Quality report: `outputs/packets/quality_report.md`
- Target: 95%+ pass rate, zero critical audience leakage
- See `src/packets/quality_review.py` for implementation

## Data Sources

| Source | Description | Freshness | Coverage |
|--------|-------------|-----------|----------|
| USASpending | Federal award data per Tribe per CFDA | FY2022--FY2026 | 451/592 Tribes (76.2%) |
| FEMA NRI | National Risk Index county-level hazard scores | v1.20 | 592/592 Tribes (100.0%) |
| USFS | Wildfire Risk to Communities dataset | 2023 | 0/592 Tribes (data download pending) |
| Congress.gov | 119th Congress delegation + committee assignments | 2025--2026 | 501/592 Tribes (84.6%) |
| EPA | Tribal Names Service (registry) | 2026 | 592/592 Tribes (100.0%) |

### Data Pipeline

1. **Registry** (EPA Tribal Names Service): 592 federally recognized Tribes with BIA codes, states, alternate names
2. **Awards** (USASpending API): Per-Tribe federal award history across 16 tracked CFDA programs
3. **Hazards** (FEMA NRI + USFS): County-level hazard risk scores area-weighted to Tribal boundaries
4. **Congressional** (Congress.gov + Census AIANNH): Delegation mapping via AIANNH-to-district geographic crosswalk

## Document Types

| Type | Audience | Scope | Content | Classification |
|------|----------|-------|---------|----------------|
| Doc A | Internal (Tribal leadership) | Per-Tribe | Strategy + leverage + messaging | CONFIDENTIAL |
| Doc B | Congressional offices | Per-Tribe | Evidence-only, program data | For Congressional Office Use |
| Doc C | Internal (InterTribal) | Per-Region | Coordinated strategy, coverage gaps | CONFIDENTIAL |
| Doc D | Congressional offices | Per-Region | Regional evidence synthesis | For Congressional Office Use |

### Document Generation Requirements

- **Doc A + Doc B**: Generated for Tribes with complete data (awards + hazards + delegation)
- **Doc B only**: Generated for Tribes with partial data (awards + delegation, or delegation only)
- **Doc C + Doc D**: Generated per region (8 regions defined in `data/regional_config.json`)
- **Strategic Overview**: Single document covering all 16 programs and 7 ecoregions

## Audience Differentiation Verification

Documents are classified by audience with strict content separation:

- **Internal docs (A/C)**: Contain strategic leverage, approach recommendations, messaging frameworks, sequencing strategy, member-specific voting analysis
- **Congressional docs (B/D)**: Contain only factual evidence, program data, economic impact with methodology citations, committee assignments

### Content Classification Line

**Internal only (never in congressional docs):**
- Leverage analysis and strategic positioning
- Approach strategy and recommended messaging framework
- Member-specific recommendations and advocacy tactics
- Voting record analysis and political context
- Sequencing strategy and timeline recommendations
- Change tracking (new/changed items between generations)

**Congressional safe (appears in all doc types):**
- Committee assignments and subcommittee memberships
- Appropriations amounts and program budget status
- Program descriptions and eligibility criteria
- Award history with obligation amounts
- Hazard scores and risk ratings with source citations
- Economic impact analysis with BEA/BLS methodology references

### Automated Audience Leakage Detection

The quality review system (`src/packets/quality_review.py`) scans every generated document for:
- Internal keywords appearing in congressional documents
- Confidential markings appearing in wrong document types
- Organizational references violating air gap
- Placeholder text that was not replaced

## Economic Impact Methodology

All economic impact calculations use publicly documented federal methodologies:

- **Multipliers:** BEA RIMS II regional input-output (output multiplier range 1.8--2.4x)
- **Employment:** BLS employment requirements (8--15 jobs per $1M federal spending)
- **Mitigation ROI:** FEMA/NIBS MitSaves ($4 return per $1 invested, for mitigation programs only)
- **Per-district allocation:** Proportional to congressional district overlap percentage
- **Real award data:** Used for all Tribes with USASpending records
- **No synthetic estimates:** Tribes without award data receive no economic impact section

### Citation Practice

Every economic figure in generated documents includes a methodology citation:
- BEA RIMS II source for multiplier ranges
- BLS employment requirements for job estimates
- FEMA/NIBS for mitigation return ratios

## Known Coverage Gaps

### Awards (141 Tribes at 0%)

- Primarily small Tribes, state-recognized Tribes, and Tribes with housing authority naming patterns not yet mapped
- Housing authority alias mapping (Phase 12-04) improved coverage from 418 to 451 Tribes
- Remaining gap: housing authority names with non-standard naming patterns, consortium recipients, regional authorities serving multiple Nations

### Hazards

- FEMA NRI: 592/592 Tribes (100%) -- all Tribes have area-weighted county-level hazard scores
- USFS Wildfire Risk to Communities: 0/592 (download pending) -- USFS XLSX first sheet is README format, override logic ready but data extraction deferred
- Alaska Native villages: NRI coverage relies on county-level data; some villages span very few counties

### Congressional (91 Tribes unmapped)

- 501/592 Tribes mapped to congressional districts via Census AIANNH-to-district crosswalk
- 91 Tribes without Census AIANNH geographic boundaries cannot be mapped to congressional districts
- These are primarily state-recognized Tribes and small land-base Tribes without Census-defined boundaries

### Registry

- 592/592 Tribes from EPA Tribal Names Service
- 353/592 have BIA codes assigned (239 marked "TBD")
- 592/592 have state assignments

### Cross-Source Completeness

- **Complete data (all 3 sources):** 384/592 Tribes (64.9%)
- **Partial (awards + delegation):** 67 Tribes
- **Award only:** 0 Tribes
- **Delegation only:** 117 Tribes
- **Hazard only:** 24 Tribes
- **None:** 0 Tribes

## Sample Validation

For manual spot-checking, review 5 Tribes per ecoregion (35 total):

1. **Compare Doc A and Doc B** for the same Tribe to verify audience differentiation
   - Doc A should contain leverage analysis; Doc B should not
   - Both should contain identical award amounts and hazard scores
2. **Verify award amounts** match USASpending API data for the relevant CFDA programs
3. **Verify hazard scores** match FEMA NRI source data (county-weighted composite scores)
4. **Verify delegation members** match Congress.gov 119th Congress roster
5. **Verify economic impact** calculations use documented multiplier ranges

### Spot-Check Process

```
# Generate documents for a sample Tribe
python -m src.main --prep-packets --tribe epa_100000001

# Compare against source data
python -c "import json; print(json.dumps(json.load(open('data/award_cache/epa_100000001.json')), indent=2))"
python -c "import json; print(json.dumps(json.load(open('data/hazard_profiles/epa_100000001.json')), indent=2))"
```

## Air Gap Verification

No document surface (header, footer, cover page, body text, metadata) contains:

- Organizational names or entity references
- Tool attribution or generation signatures
- Author names or contact information
- Logos or organizational branding

**Verification approach:**
- Automated: `src/packets/quality_review.py` scans all generated DOCX files
- Pattern list: maintained in quality review module, covers known organizational names
- Federal data sources are cited explicitly and specifically (e.g., "Source: USASpending.gov, FY2022-FY2026")

## Reproducibility

To regenerate all documents from source data:

```bash
# 1. Download FEMA NRI source data (county-level shapefiles + CSV)
python scripts/download_nri_data.py

# 2. Download USFS wildfire risk data (optional, pending extraction)
python scripts/download_usfs_data.py

# 3. Build area-weighted AIANNH-to-county crosswalk
python scripts/build_area_crosswalk.py

# 4. Populate hazard profiles from NRI data
python scripts/populate_hazards.py

# 5. Populate award caches from USASpending API
python scripts/populate_awards.py

# 6. Build congressional delegation cache
python scripts/build_congress_cache.py

# 7. Generate all documents (all Tribes + regional)
python -m src.main --prep-packets --all-tribes

# 8. Validate coverage
python scripts/validate_coverage.py

# 9. Run test suite
python -m pytest tests/ -v
```

### Environment Requirements

- Python 3.12+
- Dependencies: `pip install -r requirements.txt`
- No external API keys required for document generation (only for data population steps 1--6)
- Data files are not committed to git; regenerate from source APIs

---
*v1.2 Verification document*
*Generated: 2026-02-11*
