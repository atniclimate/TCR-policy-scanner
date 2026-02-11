# Federal API Reference for TCR Policy Scanner

## API Priority Stack

| Priority | API | Auth | Rate Limit | Key ALNs |
|----------|-----|------|------------|----------|
| 1 | USAspending.gov | None | Undocumented | 15.156, 97.047, 97.039 |
| 2 | OpenFEMA | None | 10K records/call | N/A (disaster-based) |
| 3 | Congress.gov | Free key | 5,000/hour | N/A (bill-based) |
| 4 | Grants.gov | Free key | Undocumented | Search by category |
| 5 | Federal Register | None | Undocumented | N/A (notice-based) |
| 6 | SAM.gov | Free key | 10/day (non-fed) | "2X" business type |
| 7 | NOAA NCEI/NWS | None | Undocumented | N/A (climate data) |

## Cross-System Join Keys
- **ALN** (Assistance Listing Number): Grants.gov <-> USAspending <-> SAM.gov
- **UEI** (Unique Entity Identifier): SAM.gov <-> USAspending <-> all spending DBs
- **FIPS**: FEMA <-> NOAA <-> EPA <-> Census geographic data
- **Congressional District**: USAspending <-> Congress.gov legislative tracking

## The 16 Tracked Programs and Their ALNs
See `data/program_inventory.json` for the canonical list.

Key ALNs to monitor:
- **15.156**: BIA Tribal Climate Resilience (CRITICAL)
- **97.047**: FEMA BRIC (CRITICAL)
- **97.039**: FEMA HMGP (HIGH)
- **66.926**: EPA Indian Environmental General Assistance (GAP) (HIGH)
- **81.104**: DOE Office of Indian Energy (HIGH)

## Existing Scrapers (src/scrapers/)

| Scraper | API Base | Auth | Key Patterns |
|---------|----------|------|--------------|
| federal_register.py | federalregister.gov/api/v1/ | None | conditions[term] search |
| grants_gov.py | api.grants.gov/v1/api/search2 | SAM_API_KEY | fundingCategories, eligibilities |
| congress_gov.py | api.data.gov/congress/v3 | CONGRESS_API_KEY | bill tracking, committee actions |
| usaspending.py | api.usaspending.gov/api/v2/ | None | POST spending_by_award, recipient_type |

## Data Cache Architecture

Pre-cached data (zero API calls during DOCX generation):
- `data/tribal_registry.json` — 592 Tribes with BIA codes, states, name variants
- `data/congressional_cache.json` — 538 members with committee assignments per Tribe
- `data/tribal_aliases.json` — 3,751 USASpending name aliases for two-tier matching
- `data/award_cache/*.json` — per-Tribe USASpending award histories (592 files)
- `data/hazard_profiles/*.json` — per-Tribe FEMA NRI + USFS hazard profiles (592 files)
