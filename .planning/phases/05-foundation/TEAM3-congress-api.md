# Team 3: Congress.gov API Members & Committees - Research

**Researched:** 2026-02-10
**Domain:** Congress.gov API v3 (Member & Committee endpoints), unitedstates/congress-legislators dataset
**Confidence:** HIGH (member endpoints), MEDIUM (committee membership strategy)

---

## Summary

The Congress.gov API v3 (`https://api.congress.gov/v3`) provides comprehensive endpoints for listing and filtering congressional members by congress number, state, and district. However, the API **does NOT provide an endpoint to list members of a specific committee**. Committee membership data must come from the `unitedstates/congress-legislators` GitHub dataset, which maintains a `committee-membership-current.yaml` file mapping committee IDs to member bioguide IDs with rank and role information.

The recommended strategy is a **two-source approach**: use the Congress.gov API for member biographical/contact data, and the `unitedstates/congress-legislators` dataset for committee assignment mappings. Both datasets share the `bioguideId` key for cross-referencing.

**Primary recommendation:** Fetch all 119th Congress members from `/member/congress/119` (3 pages at limit=250), then enrich with committee membership from the `unitedstates/congress-legislators` `committee-membership-current.yaml` file.

---

## Member Endpoints

### List All Members of a Congress
```
GET /v3/member/congress/119?limit=250&offset=0&currentMember=true
```
- Returns all senators AND representatives for the 119th Congress
- **Pagination:** Default 20 results, max 250 per page
- **Total members:** ~541 (100 senators + 435 reps + 6 delegates/commissioners)
- **Pages needed:** 3 requests at limit=250 (0, 250, 500)
- **Key query params:** `currentMember=true` for active members only, `limit`, `offset`

**Confidence:** HIGH - Verified from official GitHub documentation

### Members by State
```
GET /v3/member/congress/119/{stateCode}
```
- Returns all members (senators + reps) from a specific state in the 119th Congress
- `stateCode` = two-letter postal abbreviation (e.g., "AZ", "AK")
- Useful for Tribe delegation lookups: given a Tribe's state, get all its senators plus relevant reps

**Note:** This endpoint exists as `/v3/member/{stateCode}` (all congresses) and as `/v3/member/congress/119/{stateCode}` (congress-filtered). Use the congress-filtered version.

### Members by State and District
```
GET /v3/member/congress/119/{stateCode}/{district}?currentMember=true
```
- Returns the specific representative for a district
- `district=0` indicates at-large (states with 1 representative: AK, WY, VT, etc.)
- Always use `currentMember=true` to avoid historical members from redistricting

**Confidence:** HIGH - Verified from official documentation with example URLs

### Individual Member Detail
```
GET /v3/member/{bioguideId}
```
- Returns full biographical and contact data for one member
- Fields NOT available at list level but available here:
  - `addressInformation`: DC office address, phone number, zip code
  - `depiction`: portrait `imageUrl` and `attribution`
  - `leadership`: positions held (type, congress, current status)
  - `officialUrl`: member's website

**Confidence:** HIGH - Verified complete field list from official docs

### Member List-Level Response Fields

```json
{
  "members": [
    {
      "bioguideId": "M001153",
      "name": "Murkowski, Lisa",
      "state": "Alaska",
      "district": null,
      "partyName": "Republican",
      "terms": {
        "item": [
          {
            "chamber": "Senate",
            "congress": 119,
            "memberType": "Senator",
            "startYear": 2023,
            "stateCode": "AK"
          }
        ]
      },
      "depiction": {
        "imageUrl": "https://...",
        "attribution": "..."
      },
      "url": "https://api.congress.gov/v3/member/M001153"
    }
  ],
  "pagination": {
    "count": 541,
    "next": "https://api.congress.gov/v3/member/congress/119?offset=250&limit=250"
  }
}
```

### Member Detail Response Fields (Complete)

| Field | Type | Notes |
|-------|------|-------|
| `bioguideId` | string | Primary key, e.g., "M001153" |
| `firstName` | string | |
| `middleName` | string | Optional |
| `lastName` | string | |
| `suffixName` | string | Optional (Jr., III, etc.) |
| `directOrderName` | string | "Lisa Murkowski" |
| `invertedOrderName` | string | "Murkowski, Lisa" |
| `honorificName` | string | "Ms.", "Mr.", etc. |
| `nickName` | string | Optional |
| `party` | string | "Republican", "Democrat", "Independent" |
| `state` | string | Full name: "Alaska" |
| `district` | int/null | House district number, null for senators |
| `currentMember` | bool | Active status |
| `birthYear` | string | Year of birth |
| `officialUrl` | string | Member's website URL |
| `depiction.imageUrl` | string | Portrait photo URL |
| `depiction.attribution` | string | Photo credit |
| `addressInformation.officeAddress` | string | DC office |
| `addressInformation.phoneNumber` | string | DC phone |
| `addressInformation.city` | string | "Washington" |
| `addressInformation.zipCode` | string | |
| `terms` | array | Service history across congresses |
| `terms[].memberType` | string | "Senator", "Representative", "Delegate" |
| `terms[].chamber` | string | "Senate", "House of Representatives" |
| `terms[].congress` | int | Congress number |
| `terms[].stateCode` | string | Two-letter state code |
| `terms[].startYear` | int | |
| `terms[].endYear` | int | |
| `terms[].partyName` | string | Party during that term |
| `terms[].partyCode` | string | "R", "D", "I" |
| `leadership` | array | Leadership positions |
| `sponsoredLegislation.count` | int | Number of sponsored bills |
| `cosponsoredLegislation.count` | int | Number of cosponsored bills |
| `previousNames` | array | Historical name changes |

**IMPORTANT:** The member detail endpoint does NOT return committee assignments. Committee data must come from a separate source.

**Confidence:** HIGH - Verified from raw MemberEndpoint.md in official repo

---

## Committee Endpoints

### Committee Listing
```
GET /v3/committee/119/senate
GET /v3/committee/119/house
```
- Returns committees for a specific congress and chamber
- Includes `systemCode`, `name`, `isCurrent`, subcommittee list, `committeeWebsiteUrl`

### Committee Detail
```
GET /v3/committee/senate/{systemCode}
GET /v3/committee/house/{systemCode}
```
- Returns committee metadata, subcommittees, and counts for reports/bills/nominations
- **Does NOT return committee member roster**

### What the Committee Endpoint CANNOT Do

The Congress.gov API committee endpoints provide committee metadata, associated bills, reports, nominations, and communications. They do **NOT** provide:
- List of members on a committee
- Member rank/seniority on a committee
- Member role (chair, ranking member) on a committee

**Confidence:** HIGH - Verified by checking all documented endpoints and the ChangeLog through January 2026. No committee membership endpoint has been added.

### Target Committee System Codes

These are the Congress.gov API `systemCode` values (from the committees-current.yaml cross-referenced with Congress.gov URLs):

| Committee | systemCode | Chamber | thomas_id |
|-----------|-----------|---------|-----------|
| Senate Indian Affairs | slia00 | senate | SLIA |
| House Natural Resources | hsii00 | house | HSII |
| House Natural Resources - Indian and Insular Affairs Subcommittee | hsii24 | house | HSII24 |
| Senate Energy and Natural Resources | sseg00 | senate | SSEG |
| Senate Appropriations | ssap00 | senate | SSAP |
| House Appropriations | hsap00 | house | HSAP |

**Confidence:** HIGH for SLIA (verified via Congress.gov URL `/committee/senate-indian-affairs/slia00`). MEDIUM for others (cross-referenced from `unitedstates/congress-legislators` committees-current.yaml).

---

## Committee Membership: The unitedstates/congress-legislators Dataset

Since the Congress.gov API lacks committee membership endpoints, use the community-maintained `unitedstates/congress-legislators` dataset.

### Repository
- **GitHub:** https://github.com/unitedstates/congress-legislators
- **License:** Public domain
- **Maintained by:** Community (originally Sunlight Foundation, now @unitedstates project)
- **Update frequency:** Periodically scraped from official House/Senate committee pages

### Key Files

| File | Purpose | Format |
|------|---------|--------|
| `committee-membership-current.yaml` | Maps committee IDs to member lists | YAML |
| `committees-current.yaml` | Committee metadata (names, subcommittees) | YAML |
| `legislators-current.yaml` | All current legislators with bioguide IDs | YAML |

JSON versions are available on the `gh-pages` branch.

### Committee Membership Data Structure

```yaml
SLIA:  # Senate Indian Affairs (thomas_id)
  - name: Lisa Murkowski
    party: majority
    rank: 1
    title: Chairman
    bioguide: M001153
  - name: John Hoeven
    party: majority
    rank: 2
    bioguide: H001061
  # ... more majority members
  - name: Brian Schatz
    party: minority
    rank: 1
    title: Vice Chairman
    bioguide: S001194
  # ... more minority members

HSII24:  # House Natural Resources - Indian and Insular Affairs
  - name: Harriet Hageman
    party: majority
    rank: 1
    title: Chairman
    bioguide: H001096
  # ... etc
```

### Member Fields in Committee Membership

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | Member name (for debugging; use bioguide for joins) |
| `bioguide` | string | Cross-reference key to Congress.gov API and legislators-current |
| `party` | string | "majority" or "minority" (not party name) |
| `rank` | int | Seniority within party; 1 = chair/ranking member |
| `title` | string | Optional: "Chairman", "Ranking Member", "Vice Chairman", "Ex Officio" |
| `chamber` | string | Only for joint committees; indicates "house" or "senate" |

### Subcommittee IDs

Subcommittee IDs are formed by concatenating the parent committee's `thomas_id` with the subcommittee's `thomas_id`:
- `SLIA` = full Senate Indian Affairs committee
- `HSII24` = House Natural Resources subcommittee on Indian and Insular Affairs
- `SSEG` = full Senate Energy and Natural Resources committee

**Confidence:** HIGH - Verified from README and actual YAML data in repository

---

## 119th Congress Handling

### Filtering to Current Congress
- Use `/member/congress/119` endpoint (not `/member` which returns all-time)
- Add `currentMember=true` query parameter
- The 119th Congress: January 3, 2025 - January 3, 2027

### Total Members
- 100 Senators (2 per state)
- 435 Representatives
- 6 Non-voting delegates/commissioners (DC, PR, GU, AS, VI, MP)
- **Total: ~541** (may vary slightly with vacancies)

### Vacancies and Special Elections
- Per CONTEXT.md decision: "Keep last-known member until next full refresh -- packets are point-in-time snapshots"
- The API returns `currentMember=true/false` -- members who leave mid-session will flip to false
- Strategy: Cache at build time, include a `cache_date` timestamp for staleness detection
- Tag all cached data with `congress: 119` per CONTEXT.md

### Senate vs House Differences
- Senators: identified by `stateCode` + `class` (1, 2, or 3); no district
- Representatives: identified by `stateCode` + `district` number
- At-large reps: `district=0` (AK, WY, VT, ND, SD, MT, DE)
- Delegates: `memberType="Delegate"` or `"Resident Commissioner"` (non-voting)

**Confidence:** HIGH

---

## Rate Limits & Pagination

### Rate Limits
- **5,000 requests per hour** (confirmed from changelog March 2024 and README)
- Authentication via `X-Api-Key` header (already used in existing codebase)
- The API returns 429 on rate limit exceeded (existing BaseScraper handles this)

### Pagination
- **Default:** 20 results per request
- **Maximum:** 250 results per request (`limit=250`)
- **Offset-based:** use `offset` parameter to page through results
- Response includes `pagination.count` (total) and `pagination.next` (URL for next page)

### API Call Budget for Full Cache Build

| Operation | Calls | Notes |
|-----------|-------|-------|
| All 119th Congress members (list) | 3 | 541 members / 250 per page |
| Member details (contact info, photo) | 541 | One per member for addressInformation |
| Committee metadata | ~10 | 5-6 target committees + subcommittees |
| **Total** | **~554** | Well within 5,000/hour limit |

### Optimal Batch Strategy

```
Phase 1: Bulk list (3 calls)
  GET /member/congress/119?limit=250&offset=0
  GET /member/congress/119?limit=250&offset=250
  GET /member/congress/119?limit=250&offset=500

Phase 2: Detail enrichment (541 calls, throttled)
  For each bioguideId:
    GET /member/{bioguideId}
  # Add 0.3s delay between calls (matches existing pattern)
  # Total time: ~3 minutes

Phase 3: Committee membership (0 API calls)
  Download committee-membership-current.yaml from GitHub
  Parse locally, no API needed
```

**Alternative: Skip Phase 2 for non-target members.** Since we only need contact details for members in a Tribe's delegation, we could lazily fetch member details only when assembling a packet. But the CONTEXT.md says to pre-cache all data, so fetch all 541 upfront.

**Confidence:** HIGH

---

## Caching Strategy

### Cache TTL
Congressional membership changes infrequently:
- **Full term:** 2 years for the 119th Congress (Jan 2025 - Jan 2027)
- **Mid-session changes:** Rare (deaths, resignations, special elections, maybe 2-5 per Congress)
- **Committee reassignments:** Typically only at start of Congress; occasional mid-session reshuffles
- **Recommended TTL:** 30 days for the cache file, with manual refresh capability
- **Staleness marker:** Include `cache_date` and `congress` fields at root level

### Data Volume Estimate

| Data | Size Estimate |
|------|---------------|
| 541 member records (list-level) | ~500 KB JSON |
| 541 member detail records | ~2-3 MB JSON |
| Committee membership mappings | ~50 KB JSON |
| Tribe-to-district mappings | ~100 KB JSON |
| **Total cache file** | **~3-4 MB** |

### Cache File Structure

Per CONTEXT.md: "Single `congressional_cache.json` with all members, committees, and Tribe-to-district mappings."

```json
{
  "meta": {
    "congress": 119,
    "cache_date": "2026-02-10T00:00:00Z",
    "member_count": 541,
    "source_versions": {
      "congress_api": "v3",
      "congress_legislators_commit": "abc1234"
    }
  },
  "members": {
    "M001153": {
      "bioguide_id": "M001153",
      "first_name": "Lisa",
      "last_name": "Murkowski",
      "party": "Republican",
      "state": "AK",
      "chamber": "Senate",
      "district": null,
      "official_url": "https://...",
      "phone": "202-224-6665",
      "office_address": "522 Hart Senate Office Building",
      "photo_url": "https://...",
      "leadership_roles": [],
      "committees": ["SLIA", "SSEG", "SSAP"]
    }
  },
  "committees": {
    "SLIA": {
      "name": "Senate Committee on Indian Affairs",
      "chamber": "senate",
      "system_code": "slia00",
      "url": "https://www.congress.gov/committee/senate-indian-affairs/slia00",
      "members": [
        {
          "bioguide_id": "M001153",
          "rank": 1,
          "party_role": "majority",
          "title": "Chairman"
        }
      ],
      "subcommittees": []
    },
    "HSII": {
      "name": "House Committee on Natural Resources",
      "chamber": "house",
      "system_code": "hsii00",
      "subcommittees": ["HSII24"]
    },
    "HSII24": {
      "name": "Indian and Insular Affairs",
      "chamber": "house",
      "system_code": "hsii24",
      "parent": "HSII",
      "members": []
    }
  }
}
```

**Confidence:** MEDIUM - Structure is recommended based on CONTEXT.md requirements; actual implementation may vary

---

## Delegation Assembly Pattern

### Problem Statement
Given a Tribe with:
- `state`: e.g., "AZ"
- `districts`: e.g., [1, 7] (from CRS R48107 mapping)

Assemble the complete congressional delegation:
- 2 Senators for the state
- N Representatives for the specific districts

### Algorithm

```python
def assemble_delegation(tribe_state: str, tribe_districts: list[int], cache: dict) -> dict:
    """Assemble a Tribe's congressional delegation from cached data."""
    delegation = {
        "senators": [],
        "representatives": [],
        "key_committees": []
    }

    # 1. Find senators: filter members by state + chamber=Senate
    for member in cache["members"].values():
        if member["state"] == tribe_state and member["chamber"] == "Senate":
            delegation["senators"].append(member)

    # 2. Find representatives: filter by state + district
    for district in tribe_districts:
        for member in cache["members"].values():
            if (member["state"] == tribe_state
                and member["chamber"] == "House"
                and member["district"] == district):
                delegation["representatives"].append(member)

    # 3. Annotate committee memberships for each delegation member
    target_committees = ["SLIA", "HSII", "HSII24", "SSEG", "SSAP", "HSAP"]
    for member in delegation["senators"] + delegation["representatives"]:
        for comm_id in target_committees:
            comm = cache["committees"].get(comm_id, {})
            for cm in comm.get("members", []):
                if cm["bioguide_id"] == member["bioguide_id"]:
                    delegation["key_committees"].append({
                        "member": member["bioguide_id"],
                        "committee": comm_id,
                        "committee_name": comm["name"],
                        "role": cm.get("title", "Member"),
                        "rank": cm["rank"]
                    })

    return delegation
```

### Alaska At-Large Handling
- Alaska has 1 at-large representative (district=0)
- 2 senators (Murkowski, Sullivan)
- All Alaska Native Tribes get the same delegation: 2 senators + 1 rep
- No special code needed; district=0 works in the same lookup

### Multi-State Tribes
- Some reservations span multiple states (e.g., Navajo Nation in AZ, NM, UT)
- Each state contributes its 2 senators + relevant district reps
- Per CONTEXT.md: "Senator deduplication: Show senators once per state (not repeated per district)"
- The CRS mapping (Team 2) provides the state-to-district data; this system just looks up the members

### Display Format (per CONTEXT.md)
```
Sen. Lisa Murkowski (R-AK) - Chair, Senate Indian Affairs Committee
Sen. Dan Sullivan (R-AK)
Rep. Mary Peltola (D-AK-AL) - House Natural Resources Committee
```

**Confidence:** HIGH for the pattern; MEDIUM for specific member names (may change)

---

## Recommendations

### 1. Two-Source Strategy (Use This)
- **Congress.gov API** for member biographical data, contact info, photos
- **unitedstates/congress-legislators** for committee assignments
- Cross-reference via `bioguideId` (shared primary key)

### 2. Cache Build Sequence
```
Step 1: Download committee-membership-current.yaml from GitHub
Step 2: Download committees-current.yaml from GitHub
Step 3: Fetch /member/congress/119?limit=250 (3 pages)
Step 4: For each member, fetch /member/{bioguideId} for contact details
Step 5: Merge: member data + committee assignments -> congressional_cache.json
Step 6: Write cache with metadata (congress, date, source versions)
```

### 3. Throttling
- Use existing `BaseScraper._request_with_retry` for Congress.gov API calls
- Use existing 0.3s inter-request delay pattern
- For GitHub YAML downloads: simple HTTP GET, no throttling needed (2 files)

### 4. Error Handling
- If Congress.gov API is down: fail gracefully, report which members were missed
- If unitedstates repo is unavailable: committee assignments will be empty in cache
- If a specific member detail fetch fails: include list-level data without contact details

### 5. Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Committee membership mapping | Custom scraper for Senate/House committee pages | unitedstates/congress-legislators YAML |
| Member photo URLs | Custom bioguide scraper | `depiction.imageUrl` from member detail API |
| Congressional district lookups | Custom geographic mapping | CRS R48107 data (Team 2) |
| Party affiliation history | Custom tracking | `terms[].partyName` from API |
| YAML parsing | Custom parser | PyYAML (`pip install pyyaml`) |

### 6. Key Committees for Tribal Affairs

**Primary (highest relevance):**
- `SLIA` - Senate Indian Affairs: Primary jurisdiction over all tribal legislation
- `HSII24` - House Natural Resources, Indian and Insular Affairs Subcommittee

**Secondary (funding/authorization relevance):**
- `SSEG` - Senate Energy and Natural Resources (tribal energy, trust lands)
- `SSAP` - Senate Appropriations (tribal funding)
- `HSAP` - House Appropriations (tribal funding)
- `HSII` - House Natural Resources (parent committee)

---

## Confidence Level

| Area | Level | Reason |
|------|-------|--------|
| Member endpoints | HIGH | Verified from official GitHub docs (MemberEndpoint.md) |
| Member response fields | HIGH | Complete field list verified from raw documentation |
| Committee metadata endpoints | HIGH | Verified from official GitHub docs (CommitteeEndpoint.md) |
| Committee membership gap | HIGH | Confirmed no endpoint exists; verified through ChangeLog Jan 2026 |
| unitedstates/congress-legislators | HIGH | Repository verified, data structure confirmed from README and YAML |
| Committee system codes | HIGH for SLIA | Verified via Congress.gov URL; MEDIUM for others (from YAML) |
| Rate limits | HIGH | 5,000/hour confirmed from README and March 2024 changelog |
| Pagination | HIGH | 250 max confirmed from multiple sources |
| Cache structure | MEDIUM | Recommended based on CONTEXT.md; not externally validated |
| API call budget | MEDIUM | Based on 541 member estimate; actual count may differ slightly |

---

## Open Questions

1. **Member detail: is it worth 541 API calls?**
   - Contact info (phone, address) is only in the detail endpoint
   - Could lazy-fetch only when assembling a specific Tribe's packet
   - CONTEXT.md says "pre-cache" so the answer is probably yes
   - **Recommendation:** Pre-fetch all 541 details during cache build

2. **unitedstates/congress-legislators freshness**
   - The YAML is community-maintained; it could lag behind actual committee assignments
   - For the 119th Congress (started Jan 2025), assignments should be settled by now
   - **Recommendation:** Download at cache build time, include the Git commit SHA in metadata

3. **Photo URLs durability**
   - `depiction.imageUrl` from the API may change or break
   - **Recommendation:** Download and store photos locally during cache build if DOCX packets need them

4. **Non-voting delegates**
   - DC, PR, GU, AS, VI, MP have non-voting delegates
   - Some Tribes are in territories (e.g., Guam Chamorro)
   - **Recommendation:** Include delegates in cache; filter at display time if needed

5. **Party independent caucusing**
   - Some members are "Independent" but caucus with Democrats (e.g., Bernie Sanders, Angus King)
   - API returns `party: "Independent"` but unitedstates repo has `caucus: "Democrat"`
   - **Recommendation:** Store both party and caucus if available

---

## Sources

### Primary (HIGH confidence)
- [LibraryOfCongress/api.congress.gov - MemberEndpoint.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md) - Complete member endpoint documentation
- [LibraryOfCongress/api.congress.gov - CommitteeEndpoint.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/CommitteeEndpoint.md) - Committee endpoint documentation
- [LibraryOfCongress/api.congress.gov - README.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/README.md) - Rate limits, pagination, auth
- [LibraryOfCongress/api.congress.gov - ChangeLog.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/ChangeLog.md) - API changes through Jan 2026
- [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) - Committee membership data
- [Congress.gov - Senate Indian Affairs](https://www.congress.gov/committee/senate-indian-affairs/slia00) - Committee system code verification
- [api.congress.gov](https://api.congress.gov) - OpenAPI specification, endpoint listing

### Secondary (MEDIUM confidence)
- [christophertkenny/congress R package](https://christophertkenny.com/congress/reference/index.html) - API wrapper confirming endpoint inventory
- [congress R package docs](https://cran.r-project.org/web/packages/congress/congress.pdf) - API field descriptions

### Tertiary (LOW confidence)
- None relied upon for this research

---

## Metadata

**Research date:** 2026-02-10
**Valid until:** 2026-03-12 (30 days - congressional data is stable within a session)
**Key dependency:** The `unitedstates/congress-legislators` repository must have 119th Congress committee data available. As of Feb 2026, the 119th Congress has been in session for over a year, so this data should be well-established.
