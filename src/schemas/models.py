"""Pydantic v2 validation models for TCR Policy Scanner data structures.

Each model maps directly to a JSON data file or nested structure used
in the pipeline. Strict validation ensures schema violations surface
as errors at ingestion time, not as silent data corruption downstream.

Data sources modeled:
- program_inventory.json -> ProgramRecord
- policy_tracking.json -> PolicyPosition
- tribal_registry.json -> TribeRecord
- award_cache/*.json -> AwardCacheFile (containing FundingRecord items)
- hazard_profiles/*.json -> HazardProfile
- congressional_cache.json -> CongressionalDelegate, CongressionalDelegation
"""

from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums as Literal types for strict validation ──

# Valid CI status values from policy_tracking.json status_definitions
CI_STATUSES = frozenset({
    "SECURE",
    "STABLE",
    "STABLE_BUT_VULNERABLE",
    "AT_RISK",
    "UNCERTAIN",
    "FLAGGED",
    "TERMINATED",
})

# Valid priority levels from program_inventory.json
PRIORITY_LEVELS = frozenset({"critical", "high", "medium", "low"})

# Valid access types from program_inventory.json
ACCESS_TYPES = frozenset({
    "direct",
    "competitive",
    "tribal_set_aside",
    "formula",
})

# Valid funding types from program_inventory.json
FUNDING_TYPES = frozenset({"Discretionary", "Mandatory", "One-Time"})

# FEMA NRI hazard type codes (18 hazard types)
NRI_HAZARD_CODES = frozenset({
    "AVLN",  # Avalanche
    "CFLD",  # Coastal Flooding
    "CWAV",  # Cold Wave
    "DRGT",  # Drought
    "ERQK",  # Earthquake
    "HAIL",  # Hail
    "HWAV",  # Heat Wave
    "HRCN",  # Hurricane
    "ISTM",  # Ice Storm
    "IFLD",  # Inland Flooding (Riverine)
    "LNDS",  # Landslide
    "LTNG",  # Lightning
    "SWND",  # Strong Wind
    "TRND",  # Tornado
    "TSUN",  # Tsunami
    "VLCN",  # Volcanic Activity
    "WFIR",  # Wildfire
    "WNTW",  # Winter Weather
})


# ── Hot Sheets Status ──

class HotSheetsStatus(BaseModel):
    """Program status from Hot Sheets review.

    Tracks the most recent manual review status for each program,
    including when it was last updated and which Hot Sheets version
    was used.
    """

    status: str = Field(
        ...,
        description="CI status from Hot Sheets review (e.g., STABLE, AT_RISK, FLAGGED)",
        examples=["STABLE", "AT_RISK", "FLAGGED"],
    )
    last_updated: str = Field(
        ...,
        description="ISO date of last Hot Sheets sync (YYYY-MM-DD)",
        examples=["2026-02-09"],
    )
    source: str = Field(
        ...,
        description="Hot Sheets version identifier",
        examples=["FY26 Hot Sheets v2"],
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in CI_STATUSES:
            raise ValueError(
                f"Invalid CI status '{v}'. Must be one of: {sorted(CI_STATUSES)}"
            )
        return v


# ── Program Record (program_inventory.json) ──

class ProgramRecord(BaseModel):
    """Federal program tracked by the TCR Policy Scanner.

    Maps to a single entry in program_inventory.json. Each program
    represents a federal funding vehicle relevant to Tribal climate
    resilience advocacy.

    Required fields cover the core identity, scoring, and status.
    Optional fields capture specialist notes and enhanced language
    that may only apply to specific programs.
    """

    id: str = Field(
        ...,
        description="Unique program identifier (snake_case)",
        examples=["bia_tcr", "fema_bric", "dot_protect"],
    )
    name: str = Field(
        ...,
        description="Human-readable program name",
        examples=["BIA Tribal Climate Resilience"],
    )
    agency: str = Field(
        ...,
        description="Responsible federal agency abbreviation",
        examples=["BIA", "FEMA", "EPA"],
    )
    federal_home: str = Field(
        ...,
        description="Full name of the parent federal entity",
        examples=["Bureau of Indian Affairs"],
    )
    priority: str = Field(
        ...,
        description="Advocacy priority level",
        examples=["critical", "high", "medium"],
    )
    keywords: list[str] = Field(
        ...,
        description="Search/match keywords for relevance scoring",
        min_length=1,
    )
    search_queries: list[str] = Field(
        ...,
        description="Queries used by scrapers to find program mentions",
        min_length=1,
    )
    advocacy_lever: str = Field(
        ...,
        description="Primary advocacy action for this program",
        examples=["Protect/expand the line; waived match, multi-year stability"],
    )
    description: str = Field(
        ...,
        description="Brief program description for context",
    )
    access_type: str = Field(
        ...,
        description="How Tribes access this program",
        examples=["direct", "competitive", "tribal_set_aside"],
    )
    funding_type: str = Field(
        ...,
        description="Funding mechanism type",
        examples=["Discretionary", "Mandatory", "One-Time"],
    )
    cfda: Optional[Union[str, list[str]]] = Field(
        default=None,
        description="CFDA/Assistance Listing number(s). Null for programs without CFDA.",
        examples=["15.156", ["97.047", "97.039"]],
    )
    confidence_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence Index score (0.0-1.0) reflecting program stability",
        examples=[0.88, 0.12, 0.55],
    )
    ci_status: str = Field(
        ...,
        description="Current CI status classification",
        examples=["STABLE", "FLAGGED", "AT_RISK"],
    )
    ci_determination: str = Field(
        ...,
        description="Narrative explanation of the CI score and status",
    )
    hot_sheets_status: HotSheetsStatus = Field(
        ...,
        description="Status from most recent Hot Sheets review",
    )

    # Optional fields - present only on specific programs
    tightened_language: Optional[str] = Field(
        default=None,
        description="Refined advocacy language for this program",
    )
    specialist_required: Optional[bool] = Field(
        default=None,
        description="Whether specialist engagement is required",
    )
    specialist_focus: Optional[str] = Field(
        default=None,
        description="Specific focus area for specialist engagement",
    )
    proposed_fix: Optional[str] = Field(
        default=None,
        description="Proposed legislative or administrative fix",
    )
    scanner_trigger_keywords: Optional[list[str]] = Field(
        default=None,
        description="Keywords that trigger scanner alerts for this program",
    )

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PRIORITY_LEVELS:
            raise ValueError(
                f"Invalid priority '{v}'. Must be one of: {sorted(PRIORITY_LEVELS)}"
            )
        return v

    @field_validator("access_type")
    @classmethod
    def validate_access_type(cls, v: str) -> str:
        if v not in ACCESS_TYPES:
            raise ValueError(
                f"Invalid access_type '{v}'. Must be one of: {sorted(ACCESS_TYPES)}"
            )
        return v

    @field_validator("funding_type")
    @classmethod
    def validate_funding_type(cls, v: str) -> str:
        if v not in FUNDING_TYPES:
            raise ValueError(
                f"Invalid funding_type '{v}'. Must be one of: {sorted(FUNDING_TYPES)}"
            )
        return v

    @field_validator("ci_status")
    @classmethod
    def validate_ci_status(cls, v: str) -> str:
        if v not in CI_STATUSES:
            raise ValueError(
                f"Invalid ci_status '{v}'. Must be one of: {sorted(CI_STATUSES)}"
            )
        return v

    @model_validator(mode="after")
    def validate_specialist_fields(self) -> "ProgramRecord":
        """If specialist_required is True, specialist_focus must be provided."""
        if self.specialist_required and not self.specialist_focus:
            raise ValueError(
                f"Program '{self.id}': specialist_required=True but specialist_focus is missing"
            )
        return self


# ── Policy Position (policy_tracking.json) ──

class ExtensibleFields(BaseModel):
    """Extensible metadata fields for a policy position.

    These fields vary by program. All are optional since different
    programs carry different metadata based on their risk profile.
    """

    advocacy_priority: Optional[str] = Field(
        default=None,
        description="Advocacy priority classification",
        examples=["Critical", "High", "Medium"],
    )
    fy26_funding: Optional[str] = Field(
        default=None,
        description="Current fiscal year funding amount string",
        examples=["$34.291M"],
    )
    scanner_trigger_keywords: Optional[list[str]] = Field(
        default=None,
        description="Keywords triggering scanner alerts",
    )
    tightened_language: Optional[str] = Field(
        default=None,
        description="Refined advocacy language",
    )
    termination_date: Optional[str] = Field(
        default=None,
        description="Date program was terminated (YYYY-MM-DD)",
        examples=["2025-04-04"],
    )
    unobligated_funds: Optional[str] = Field(
        default=None,
        description="Amount of unobligated funds",
        examples=["$882M"],
    )
    specialist_focus: Optional[str] = Field(
        default=None,
        description="Focus area for specialist engagement",
    )
    strength_area: Optional[str] = Field(
        default=None,
        description="Areas of program strength to leverage",
    )
    final_rule_date: Optional[str] = Field(
        default=None,
        description="Date of final rule publication (YYYY-MM or YYYY-MM-DD)",
        examples=["2026-01"],
    )
    threat_vector: Optional[str] = Field(
        default=None,
        description="Primary threat to program continuation",
    )
    proposed_fix: Optional[str] = Field(
        default=None,
        description="Proposed legislative or administrative fix",
    )
    tribal_set_aside: Optional[str] = Field(
        default=None,
        description="Tribal set-aside percentage or amount",
        examples=["2%"],
    )

    model_config = {"extra": "allow"}


class PolicyPosition(BaseModel):
    """Policy position for a tracked federal program.

    Maps to a single entry in policy_tracking.json positions array.
    Combines the Confidence Index score with narrative reasoning
    and extensible metadata.
    """

    program_id: str = Field(
        ...,
        description="References ProgramRecord.id",
        examples=["bia_tcr", "fema_bric"],
    )
    program_name: str = Field(
        ...,
        description="Human-readable program name",
    )
    agency: str = Field(
        ...,
        description="Responsible federal agency",
        examples=["BIA", "FEMA"],
    )
    confidence_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence Index score (0.0-1.0)",
    )
    status: str = Field(
        ...,
        description="CI status classification",
        examples=["STABLE", "FLAGGED", "AT_RISK"],
    )
    reasoning: str = Field(
        ...,
        description="Narrative justification for the CI score",
    )
    extensible_fields: ExtensibleFields = Field(
        ...,
        description="Program-specific metadata",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in CI_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {sorted(CI_STATUSES)}"
            )
        return v


# ── Tribe Record (tribal_registry.json) ──

class TribeRecord(BaseModel):
    """Federally recognized Tribal Nation record from EPA registry.

    Maps to a single entry in tribal_registry.json tribes array.
    Source: EPA Tribes Names Service API (cdxapi.epa.gov).
    """

    tribe_id: str = Field(
        ...,
        description="EPA Tribal identifier (format: epa_XXXXXXXXX)",
        examples=["epa_100000001", "epa_100000342"],
    )
    bia_code: str = Field(
        ...,
        description="BIA organizational code. May be 'TBD' for 239 of 592 Tribes.",
        examples=["820", "584", "TBD"],
    )
    name: str = Field(
        ...,
        description="Official BIA name of the Tribal Nation",
        examples=["Absentee-Shawnee Tribe of Indians of Oklahoma"],
    )
    states: list[str] = Field(
        ...,
        description="State abbreviations where the Tribal Nation has land",
        min_length=1,
        examples=[["OK"], ["CA"], ["AZ", "NM"]],
    )
    alternate_names: list[str] = Field(
        default_factory=list,
        description="Historical or alternate names for the Tribal Nation",
    )
    epa_region: str = Field(
        ...,
        description="EPA Region number (1-10)",
        examples=["6", "9", "10"],
    )
    tribal_band_flag: str = Field(
        default="",
        description="Flag indicating Tribal band status (often empty)",
    )
    bia_recognized: bool = Field(
        ...,
        description="Whether the Tribal Nation is BIA-recognized",
    )

    @field_validator("tribe_id")
    @classmethod
    def validate_tribe_id_format(cls, v: str) -> str:
        if not v.startswith("epa_"):
            raise ValueError(
                f"tribe_id must start with 'epa_', got '{v}'"
            )
        numeric_part = v[4:]
        if not numeric_part.isdigit():
            raise ValueError(
                f"tribe_id numeric portion must be all digits, got '{numeric_part}'"
            )
        return v

    @field_validator("epa_region")
    @classmethod
    def validate_epa_region(cls, v: str) -> str:
        if not v.isdigit() or not (1 <= int(v) <= 10):
            raise ValueError(
                f"epa_region must be 1-10, got '{v}'"
            )
        return v


# ── Funding Record (award_cache/*.json) ──

class FundingRecord(BaseModel):
    """Individual USAspending award record for a Tribal Nation.

    Populated by TribalAwardMatcher.match_all_awards() from live
    USAspending API data. Each record represents a single matched
    award with normalized fields.

    Source: USAspending.gov API /api/v2/search/spending_by_award/
    filtered by CFDA numbers and Tribal government recipient type.
    """

    award_id: Optional[str] = Field(
        default=None,
        description="USAspending award ID (e.g., 'A18AP00211')",
    )
    cfda: Optional[str] = Field(
        default=None,
        description="CFDA/Assistance Listing number for the award",
        examples=["15.156", "66.926"],
    )
    program_id: Optional[str] = Field(
        default=None,
        description="Mapped TCR program ID based on CFDA number",
        examples=["bia_tcr", "epa_gap"],
    )
    recipient_name_raw: Optional[str] = Field(
        default=None,
        description="Original recipient name from USAspending (before matching)",
    )
    obligation: float = Field(
        default=0.0,
        description="Total obligation amount in USD",
        examples=[150000.0, 2500000.0],
    )
    description: Optional[str] = Field(
        default=None,
        description="Award description from USAspending",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Award period start date (YYYY-MM-DD)",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Award period end date (YYYY-MM-DD)",
    )
    awarding_agency: Optional[str] = Field(
        default=None,
        description="Name of the awarding federal agency",
    )


class CFDASummaryEntry(BaseModel):
    """Per-CFDA summary statistics within an award cache file."""

    count: int = Field(default=0, ge=0, description="Number of awards for this CFDA")
    total: float = Field(default=0.0, description="Total obligation for this CFDA")


class FiscalYearRange(BaseModel):
    """Fiscal year range for the award cache query window."""

    start: int = Field(..., description="First fiscal year (e.g., 2022)")
    end: int = Field(..., description="Last fiscal year (e.g., 2026)")


class AwardCacheFile(BaseModel):
    """Per-Tribe award cache file structure.

    Maps to a complete award_cache/{tribe_id}.json file.
    Contains the Tribe identity, award records, yearly obligation
    breakdowns, CFDA summaries, and a funding trend indicator.
    """

    tribe_id: str = Field(
        ...,
        description="EPA Tribal identifier",
        examples=["epa_100000001"],
    )
    tribe_name: str = Field(
        ...,
        description="Official Tribal Nation name",
    )
    fiscal_year_range: Optional[FiscalYearRange] = Field(
        default=None,
        description="Fiscal year range of the award query window",
    )
    awards: list[FundingRecord] = Field(
        default_factory=list,
        description="List of matched USAspending award records",
    )
    total_obligation: float = Field(
        default=0.0,
        ge=0.0,
        description="Sum of all award obligations in USD",
    )
    award_count: int = Field(
        default=0,
        ge=0,
        description="Number of awards in the cache",
    )
    cfda_summary: dict[str, CFDASummaryEntry] = Field(
        default_factory=dict,
        description="Per-CFDA award count and obligation total",
    )
    yearly_obligations: Optional[dict[str, float]] = Field(
        default=None,
        description="Obligation totals by fiscal year (string keys)",
    )
    trend: Optional[str] = Field(
        default=None,
        description="Funding trend indicator: none, new, increasing, decreasing, stable",
    )
    no_awards_context: Optional[str] = Field(
        default=None,
        description="Context message when no awards are found (first-time applicant)",
    )

    @field_validator("tribe_id")
    @classmethod
    def validate_tribe_id_format(cls, v: str) -> str:
        if not v.startswith("epa_"):
            raise ValueError(f"tribe_id must start with 'epa_', got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_counts(self) -> "AwardCacheFile":
        """Ensure award_count matches len(awards) and total_obligation is consistent."""
        if self.award_count != len(self.awards):
            raise ValueError(
                f"award_count ({self.award_count}) does not match "
                f"len(awards) ({len(self.awards)})"
            )
        return self


# ── Hazard Profile (hazard_profiles/*.json) ──

class HazardDetail(BaseModel):
    """Individual hazard type risk data from FEMA NRI.

    Each of the 18 NRI hazard types has these five metrics.
    A value of 0.0 with empty risk_rating indicates the hazard
    data has not been loaded (counties_analyzed=0).
    """

    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        description="NRI risk score for this hazard type",
    )
    risk_rating: str = Field(
        default="",
        description="NRI risk rating (e.g., 'Very High', 'Relatively High', 'Relatively Moderate')",
    )
    eal_total: float = Field(
        default=0.0,
        ge=0.0,
        description="Expected Annual Loss total in USD",
    )
    annualized_freq: float = Field(
        default=0.0,
        ge=0.0,
        description="Annualized frequency of hazard events",
    )
    num_events: float = Field(
        default=0.0,
        ge=0.0,
        description="Number of recorded events",
    )


class NRIComposite(BaseModel):
    """Composite risk metrics from FEMA National Risk Index.

    Aggregates risk across all 18 hazard types for a geographic area.
    When counties_analyzed=0, all values will be 0.0 with empty ratings.
    """

    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Composite NRI risk score",
    )
    risk_rating: str = Field(
        default="",
        description="Composite risk rating",
    )
    eal_total: float = Field(
        default=0.0,
        ge=0.0,
        description="Total Expected Annual Loss across all hazards in USD",
    )
    eal_score: float = Field(
        default=0.0,
        ge=0.0,
        description="EAL score (normalized)",
    )
    eal_rating: str = Field(
        default="",
        description="Expected Annual Loss rating",
    )
    sovi_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Social Vulnerability Index score",
    )
    sovi_rating: str = Field(
        default="",
        description="Social Vulnerability rating",
    )
    resl_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Community Resilience score",
    )
    resl_rating: str = Field(
        default="",
        description="Community Resilience rating",
    )


class NRISource(BaseModel):
    """FEMA National Risk Index data source within a hazard profile.

    Contains the NRI version, county analysis count, composite scores,
    top hazards ranking, and per-hazard-type detail records.
    """

    version: str = Field(
        default="",
        description="NRI data version",
        examples=["1.20"],
    )
    counties_analyzed: int = Field(
        default=0,
        ge=0,
        description="Number of counties analyzed. 0 means NRI data not loaded.",
    )
    note: Optional[str] = Field(
        default=None,
        description="Note about data availability (e.g., 'NRI county data not loaded')",
    )
    composite: NRIComposite = Field(
        default_factory=NRIComposite,
        description="Composite risk scores across all hazards",
    )
    top_hazards: list[dict] = Field(
        default_factory=list,
        description="Ranked list of top hazards by risk score",
    )
    all_hazards: dict[str, HazardDetail] = Field(
        default_factory=dict,
        description="Per-hazard-type risk data keyed by NRI hazard code",
    )

    @field_validator("all_hazards")
    @classmethod
    def validate_hazard_codes(cls, v: dict[str, HazardDetail]) -> dict[str, HazardDetail]:
        """Validate that hazard codes are recognized NRI types."""
        unknown = set(v.keys()) - NRI_HAZARD_CODES
        if unknown:
            raise ValueError(
                f"Unknown NRI hazard codes: {sorted(unknown)}. "
                f"Expected codes from: {sorted(NRI_HAZARD_CODES)}"
            )
        return v


class HazardProfile(BaseModel):
    """Per-Tribe hazard profile combining FEMA NRI and USFS wildfire data.

    Maps to a complete hazard_profiles/{tribe_id}.json file.
    Currently, all 592 profiles have counties_analyzed=0 and
    empty USFS wildfire data, indicating the NRI county-to-Tribe
    geocoding pipeline has not yet been executed.
    """

    tribe_id: str = Field(
        ...,
        description="EPA Tribal identifier",
        examples=["epa_100000001"],
    )
    tribe_name: str = Field(
        ...,
        description="Official Tribal Nation name",
    )
    sources: dict = Field(
        ...,
        description="Data source container with fema_nri and usfs_wildfire keys",
    )
    generated_at: str = Field(
        ...,
        description="ISO 8601 timestamp of profile generation",
        examples=["2026-02-10T17:35:21.551454+00:00"],
    )

    @field_validator("sources")
    @classmethod
    def validate_sources_structure(cls, v: dict) -> dict:
        """Ensure sources contains the expected keys."""
        required_keys = {"fema_nri", "usfs_wildfire"}
        missing = required_keys - set(v.keys())
        if missing:
            raise ValueError(
                f"sources missing required keys: {sorted(missing)}. "
                f"Expected: {sorted(required_keys)}"
            )
        return v

    @field_validator("tribe_id")
    @classmethod
    def validate_tribe_id_format(cls, v: str) -> str:
        if not v.startswith("epa_"):
            raise ValueError(f"tribe_id must start with 'epa_', got '{v}'")
        return v

    def get_nri_source(self) -> NRISource:
        """Parse and validate the fema_nri sub-structure."""
        return NRISource(**self.sources.get("fema_nri", {}))

    @property
    def has_nri_data(self) -> bool:
        """Whether NRI county data has been loaded for this Tribe."""
        nri = self.sources.get("fema_nri", {})
        return nri.get("counties_analyzed", 0) > 0

    @property
    def has_usfs_data(self) -> bool:
        """Whether USFS wildfire data has been loaded for this Tribe."""
        usfs = self.sources.get("usfs_wildfire", {})
        return bool(usfs)


# ── Congressional Delegate (congressional_cache.json) ──

class CommitteeAssignment(BaseModel):
    """Congressional committee assignment for a member.

    Tracks committee membership, role, and seniority rank.
    """

    committee_id: str = Field(
        ...,
        description="Committee identifier (e.g., HSAP, SSEG)",
        examples=["HSAP", "SSEG01"],
    )
    committee_name: str = Field(
        ...,
        description="Full committee name",
        examples=["House Committee on Appropriations"],
    )
    role: str = Field(
        default="member",
        description="Member's role on the committee",
        examples=["member", "chair", "ranking_member"],
    )
    title: str = Field(
        default="",
        description="Formal title if leadership role",
        examples=["Chairman", "Ranking Member"],
    )
    rank: int = Field(
        default=0,
        ge=0,
        description="Seniority rank on the committee",
    )


class CongressionalDelegate(BaseModel):
    """119th Congress member record from congressional cache.

    Maps to a single entry in congressional_cache.json members dict.
    Includes biographical data, party, chamber, and committee assignments.
    """

    bioguide_id: str = Field(
        ...,
        description="Biographical Directory of Congress ID",
        examples=["C001120", "M001153"],
    )
    name: str = Field(
        ...,
        description="Member name in Last, First format",
        examples=["Crenshaw, Dan", "Murkowski, Lisa"],
    )
    state: str = Field(
        ...,
        description="Two-letter state abbreviation",
        examples=["TX", "AK", "WA"],
    )
    district: Optional[int] = Field(
        default=None,
        description="Congressional district number. Null for Senators.",
        examples=[2, 1, None],
    )
    party: str = Field(
        ...,
        description="Full party name",
        examples=["Republican", "Democratic"],
    )
    party_abbr: str = Field(
        ...,
        description="Party abbreviation",
        examples=["R", "D", "I"],
    )
    chamber: str = Field(
        ...,
        description="Legislative chamber",
        examples=["House", "Senate"],
    )
    formatted_name: str = Field(
        ...,
        description="Display-ready formatted name with party and district",
        examples=["Rep. Dan Crenshaw (R-TX-02)", "Sen. Lisa Murkowski (R-AK)"],
    )
    url: str = Field(
        default="",
        description="Congress.gov API URL for the member",
    )
    depiction_url: str = Field(
        default="",
        description="URL for the member's official photo",
    )
    office_address: str = Field(
        default="",
        description="DC office address",
    )
    phone: str = Field(
        default="",
        description="DC office phone number",
    )
    committees: list[CommitteeAssignment] = Field(
        default_factory=list,
        description="Committee assignments for the 119th Congress",
    )

    @field_validator("chamber")
    @classmethod
    def validate_chamber(cls, v: str) -> str:
        if v not in {"House", "Senate"}:
            raise ValueError(f"chamber must be 'House' or 'Senate', got '{v}'")
        return v


class DistrictMapping(BaseModel):
    """Mapping of a Tribal Nation area to a congressional district.

    Based on Census Bureau AIANNH-to-CD geographic overlap data.
    Multiple districts may overlap a single Tribal Nation's area.
    """

    district: str = Field(
        ...,
        description="Congressional district code (e.g., AK-AL, AZ-01)",
        examples=["AK-AL", "AZ-01", "WA-03"],
    )
    state: str = Field(
        ...,
        description="Two-letter state abbreviation",
        examples=["AK", "AZ", "WA"],
    )
    aiannh_name: str = Field(
        default="",
        description="Census Bureau AIANNH area name",
        examples=["Akhiok ANVSA", "Navajo Nation Reservation"],
    )
    overlap_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of geographic overlap between Tribal area and district",
    )


class CongressionalDelegation(BaseModel):
    """Per-Tribe congressional delegation from congressional_cache.json.

    Maps to a single entry in the delegations dict. Links a Tribal Nation
    to its congressional districts, senators, and representatives based on
    Census Bureau AIANNH geographic data.

    501 of 592 Tribes currently have delegation mappings. The remaining 91
    are unmapped because Census AIANNH boundaries do not cover all
    federally recognized Tribal Nations.
    """

    tribe_id: str = Field(
        ...,
        description="EPA Tribal identifier",
        examples=["epa_100000342"],
    )
    districts: list[DistrictMapping] = Field(
        default_factory=list,
        description="Congressional districts overlapping Tribal land",
    )
    states: list[str] = Field(
        default_factory=list,
        description="States where the Tribal Nation has representation",
    )
    senators: list[CongressionalDelegate] = Field(
        default_factory=list,
        description="U.S. Senators for the Tribe's state(s)",
    )
    representatives: list[CongressionalDelegate] = Field(
        default_factory=list,
        description="U.S. Representatives for the Tribe's district(s)",
    )

    @field_validator("tribe_id")
    @classmethod
    def validate_tribe_id_format(cls, v: str) -> str:
        if not v.startswith("epa_"):
            raise ValueError(f"tribe_id must start with 'epa_', got '{v}'")
        return v


# ── Congressional Bill Intelligence (INTEL-05) ──

# Valid Congress.gov bill type codes
BILL_TYPE_CODES = frozenset({
    "HR",      # House Bill
    "S",       # Senate Bill
    "HJRES",   # House Joint Resolution
    "SJRES",   # Senate Joint Resolution
    "HCONRES", # House Concurrent Resolution
    "SCONRES", # Senate Concurrent Resolution
    "HRES",    # House Simple Resolution
    "SRES",    # Senate Simple Resolution
})


class BillAction(BaseModel):
    """Single legislative action on a congressional bill.

    Represents one step in a bill's legislative history, such as
    introduction, committee referral, floor vote, or signing.
    """

    action_date: str = Field(
        ...,
        description="Date of action in YYYY-MM-DD format",
        examples=["2025-01-15"],
    )
    text: str = Field(
        ...,
        description="Description of the legislative action taken",
        examples=["Referred to the Committee on Natural Resources."],
    )
    action_type: str = Field(
        default="",
        description="Action type classification",
        examples=["IntroReferral", "Committee", "Floor"],
    )
    chamber: str = Field(
        default="",
        description="Chamber where action occurred",
        examples=["House", "Senate"],
    )


class BillIntelligence(BaseModel):
    """Congressional bill intelligence record for Tribal advocacy.

    Captures bill metadata, sponsorship, committee activity, subjects,
    and relevance scoring for a single bill tracked by the scanner.
    Used by the congressional intelligence pipeline to surface bills
    affecting Tribal climate resilience programs.
    """

    bill_id: str = Field(
        ...,
        description="Composite bill identifier (congress-type-number)",
        examples=["119-HR-1234", "119-S-567"],
    )
    congress: int = Field(
        ...,
        description="Congress number (e.g., 119 for 119th Congress)",
        examples=[119],
    )
    bill_type: str = Field(
        ...,
        description="Bill type code from Congress.gov",
        examples=["HR", "S", "HJRES"],
    )
    bill_number: int = Field(
        ...,
        description="Bill number within its type",
        examples=[1234, 567],
    )
    title: str = Field(
        ...,
        description="Short title or official title of the bill",
    )
    sponsor: Optional[dict] = Field(
        default=None,
        description="Primary sponsor info (bioguide_id, name, party, state)",
    )
    cosponsors: list[dict] = Field(
        default_factory=list,
        description="List of cosponsor info dicts",
    )
    cosponsor_count: int = Field(
        default=0,
        ge=0,
        description="Total number of cosponsors",
    )
    actions: list[BillAction] = Field(
        default_factory=list,
        description="Legislative actions in chronological order",
    )
    latest_action: Optional[BillAction] = Field(
        default=None,
        description="Most recent legislative action on the bill",
    )
    committees: list[dict] = Field(
        default_factory=list,
        description="Committees to which the bill has been referred",
    )
    subjects: list[str] = Field(
        default_factory=list,
        description="Legislative subject terms assigned to the bill",
    )
    policy_area: str = Field(
        default="",
        description="Primary policy area classification",
        examples=["Native Americans", "Environmental Protection"],
    )
    text_url: str = Field(
        default="",
        description="URL to the bill text on Congress.gov",
    )
    congress_url: str = Field(
        default="",
        description="URL to the bill page on Congress.gov",
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Computed relevance to Tribal climate programs (0.0-1.0)",
    )
    matched_programs: list[str] = Field(
        default_factory=list,
        description="TCR program IDs this bill is relevant to",
        examples=[["bia_tcr", "fema_bric"]],
    )
    update_date: str = Field(
        default="",
        description="Last update date from Congress.gov (YYYY-MM-DD)",
    )
    introduced_date: str = Field(
        default="",
        description="Date the bill was introduced (YYYY-MM-DD)",
    )

    @field_validator("bill_type")
    @classmethod
    def validate_bill_type(cls, v: str) -> str:
        if v not in BILL_TYPE_CODES:
            raise ValueError(
                f"Invalid bill_type '{v}'. Must be one of: {sorted(BILL_TYPE_CODES)}"
            )
        return v


class VoteRecord(BaseModel):
    """Congressional vote record linked to a bill.

    Captures roll call vote results including chamber, date,
    outcome, and vote tallies.
    """

    vote_id: str = Field(
        ...,
        description="Unique vote identifier",
        examples=["119-H-42", "119-S-15"],
    )
    bill_id: str = Field(
        default="",
        description="Associated bill identifier (congress-type-number)",
    )
    chamber: str = Field(
        default="",
        description="Chamber where vote occurred",
        examples=["House", "Senate"],
    )
    vote_date: str = Field(
        default="",
        description="Date of the vote (YYYY-MM-DD)",
    )
    result: str = Field(
        default="",
        description="Vote outcome",
        examples=["Passed", "Failed", "Agreed to"],
    )
    yea_count: int = Field(
        default=0,
        description="Number of yea votes",
    )
    nay_count: int = Field(
        default=0,
        description="Number of nay votes",
    )


class Legislator(BaseModel):
    """Congressional member record for bill intelligence context.

    Lightweight legislator reference used within BillIntelligence
    and CongressionalIntelReport for sponsor/cosponsor tracking.
    Distinct from the full CongressionalDelegate model which
    includes committee assignments and contact info.
    """

    bioguide_id: str = Field(
        ...,
        description="Biographical Directory of Congress ID",
        examples=["C001120", "M001153"],
    )
    name: str = Field(
        ...,
        description="Display name",
        examples=["Dan Crenshaw", "Lisa Murkowski"],
    )
    state: str = Field(
        default="",
        description="Two-letter state abbreviation",
    )
    district: str = Field(
        default="",
        description="Congressional district (empty for Senators)",
    )
    party: str = Field(
        default="",
        description="Party affiliation",
        examples=["Republican", "Democratic"],
    )
    chamber: str = Field(
        default="",
        description="Legislative chamber",
        examples=["House", "Senate"],
    )
    committees: list[dict] = Field(
        default_factory=list,
        description="Committee assignments",
    )
    sponsored_bills: list[str] = Field(
        default_factory=list,
        description="Bill IDs sponsored by this member",
    )
    cosponsored_bills: list[str] = Field(
        default_factory=list,
        description="Bill IDs cosponsored by this member",
    )


class CongressionalIntelReport(BaseModel):
    """Aggregated congressional intelligence report for a Tribal Nation.

    Top-level container produced by the Scout agent and consumed by
    Fire Keeper for DOCX rendering. Carries all bill intelligence,
    delegation enhancement status, confidence scores, and scan metadata.
    """

    tribe_id: str = Field(
        ...,
        description="EPA Tribal identifier",
        examples=["epa_100000001"],
    )
    generated_at: str = Field(
        ...,
        description="ISO 8601 timestamp of report generation",
    )
    bills: list[BillIntelligence] = Field(
        default_factory=list,
        description="Bills relevant to this Tribal Nation's programs",
    )
    delegation_enhanced: bool = Field(
        default=False,
        description="Whether delegation data includes committee activity intel",
    )
    confidence: dict = Field(
        default_factory=dict,
        description="Per-section confidence scores (source, score, level)",
    )
    scan_date: str = Field(
        default="",
        description="Date of the congressional scan (YYYY-MM-DD)",
    )

    @field_validator("tribe_id")
    @classmethod
    def validate_tribe_id_format(cls, v: str) -> str:
        if not v.startswith("epa_"):
            raise ValueError(f"tribe_id must start with 'epa_', got '{v}'")
        return v
