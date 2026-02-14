"""Canonical CFDA-to-program mapping for all scrapers.

Maps CFDA (Assistance Listing) numbers to internal program identifiers.
This is the single source of truth -- both grants_gov.py and usaspending.py
import from here instead of maintaining separate copies.

Consolidation: MK-CODE-05 (Phase 18 code hygiene).
"""

# 14 tracked CFDA numbers mapped to program identifiers.
# Used by USASpending (obligation queries) and Grants.gov (opportunity queries).
CFDA_TO_PROGRAM: dict[str, str] = {
    "15.156": "bia_tcr",            # BIA Tribal Climate Resilience
    "15.124": "bia_tcr_awards",     # BIA Tribal Community Resilience Annual Awards
    "97.047": "fema_bric",          # FEMA BRIC / Hazard Mitigation
    "97.039": "fema_bric",          # FEMA Hazard Mitigation Grant Program
    "66.926": "epa_gap",            # EPA Indian Environmental GAP
    "66.468": "epa_stag",           # EPA Drinking Water SRF (Tribal set-aside)
    "20.205": "fhwa_ttp_safety",    # FHWA Highway Planning & Construction (includes TTP)
    "14.867": "hud_ihbg",           # HUD IHBG
    "81.087": "doe_indian_energy",  # DOE Indian Energy
    "10.720": "usda_wildfire",      # USDA Community Wildfire Defense
    "15.507": "usbr_watersmart",    # USBR WaterSMART
    "20.284": "dot_protect",        # DOT PROTECT
    "11.483": "noaa_tribal",        # NOAA Tribal Climate Resilience
    "66.038": "epa_tribal_air",     # EPA Tribal Air Quality
}
