# FY26 Tribal Climate Resilience: Policy Scanner Reference

> **Affiliated Tribes of Northwest Indians (ATNI) | Climate Resilience Committee**
> Current as of February 8, 2026 | For Tribal Leader Use in Congressional Meetings
>
> **Repository:** `github.com/atniclimate/tcr-policy-scanner`

---

## How This Document Works

This reference serves two purposes. First, it is the human-readable policy brief for Tribal leaders preparing for FY26 Congressional advocacy. Second, it is the canonical data source that the TCR Policy Scanner ingests to build and maintain its knowledge graph. Every program entry below is structured so that both a policy staffer reading on screen and a scanner subagent parsing programmatically can extract the same decision-relevant information.

The document distinguishes between two categories of knowledge. **Scenario Facts** are time-bound observations specific to the current legislative and appropriations context (the DHS expiration date, the enacted BIA TCR funding level, the BRIC termination). These facts have expiration dates and must be reassessed on the scanner's update cycle. **Statutory Authorities** are durable legal citations (the Snyder Act, the Stafford Act Section 203, 44 CFR Section 201.7) that persist across fiscal years and anchor the knowledge graph's structural nodes. The scanner treats these two categories differently: scenario facts trigger alerts when conditions change, while statutory authorities anchor the advocacy logic even when programs are created, modified, or terminated.

---

## FY26 Landscape Context

Congress enacted a consolidated FY26 funding package on February 3, 2026 that funds most agencies through September 30, 2026. DHS is funded only through February 13, 2026, creating an immediate risk window for all FEMA mitigation and preparedness functions. The Administration's FY26 discretionary request proposed reductions to climate and environmental justice programs across multiple agencies, including an explicit proposal to eliminate the BIA Tribal Climate Resilience program and a $646 million reduction to non-disaster FEMA grant programs. Congress rejected the TCR elimination and maintained core Tribal environmental capacity lines in the enacted Interior-Environment tables.

The One Big Beautiful Bill Act (Public Law 119-21) modified federal tax credits including clean energy credits, affecting Tribal elective pay pathways. FEMA's BRIC program was terminated in April 2025, though the underlying Stafford Act Section 203 authority for pre-disaster mitigation remains active.

**Scanner Integration Note:** The landscape context above populates the `SCENARIO_CONTEXT` node in the knowledge graph. The scanner should re-validate all scenario facts on a weekly cycle by checking enacted legislation status, continuing resolution expirations, and NOFO announcements against the federal register and Congressional tracking sources.

---

## Program Index

| Program | Agency | FY26 Status | Cluster | Scanner Node ID |
|---------|--------|-------------|---------|-----------------|
| Tribal Climate Resilience (TCR) | BIA | STABLE | A | `BIA_TCR` |
| Tribal Community Resilience Annual Awards | BIA | STABLE | A | `BIA_AWARDS` |
| State & Tribal Assistance Grants (STAG) | EPA | STABLE | A | `EPA_STAG` |
| Indian Environmental GAP | EPA | STABLE | A | `EPA_GAP` |
| Tribal Air Quality Management | EPA | STABLE | A | `EPA_AIR` |
| Indian Housing Block Grant (IHBG) | HUD | STABLE | A | `HUD_IHBG` |
| TTP Safety Fund | FHWA | STABLE | A | `FHWA_TTP` |
| Community Wildfire Defense Grants (CWDG) | USFS | STABLE | A | `USFS_CWDG` |
| Native American Affairs TAP | BOR | STABLE | A | `BOR_TAP` |
| PROTECT Discretionary Grants | DOT | SECURE | A | `DOT_PROTECT` |
| Tribal Mitigation Plans (Eligibility Gate) | FEMA | AT RISK | B | `FEMA_PLANS` |
| Elective Pay (Clean Energy Tax Credits) | IRS | AT RISK | B | `IRS_ELECTIVE` |
| WaterSMART / Drought Response | BOR | UNCERTAIN | B | `BOR_WATER` |
| Office of Indian Energy TA and FOAs | DOE | UNCERTAIN | B | `DOE_ENERGY` |
| NOAA Tribal Grants | NOAA | UNCERTAIN | B | `NOAA_TRIBAL` |
| BRIC (Pre-Disaster Mitigation) | FEMA | TERMINATED | B | `FEMA_BRIC` |

---

*Prepared by ATNI Climate Resilience Committee | February 8, 2026*
*Full program hot sheets and scanner integration architecture in docs/*
