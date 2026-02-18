"""TribePacketContext dataclass for downstream DOCX rendering.

Holds all identity, congressional, award, hazard, and economic data
fields needed to generate a Tribe-specific advocacy packet.
"""

from dataclasses import asdict, dataclass, field


@dataclass
class TribePacketContext:
    """Aggregated context for generating a single Tribe's advocacy packet.

    Groups data from multiple sources (BIA registry, Congress.gov,
    USASpending, hazard profiles) into a single render-ready structure.

    Identity fields (REG-01, REG-03):
        tribe_id: Unique identifier (e.g., "epa_123").
        tribe_name: Official BIA name.
        states: List of state abbreviations where the Tribe has land.
        ecoregions: Ecoregion IDs from EcoregionMapper.classify().
        bia_code: BIA organizational code.
        epa_id: EPA Tribal internal ID.

    Congressional fields (CONG-01, CONG-02):
        districts: Congressional district dicts (e.g., [{"state": "AZ", "district": "01"}]).
        senators: Senator info dicts.
        representatives: Representative info dicts.

    Phase 6 stubs:
        awards: USASpending award records.
        hazard_profile: Aggregated hazard data (FEMA NRI + USFS wildfire).

    Phase 7 stubs:
        economic_impact: Economic multiplier calculations.

    Congressional intelligence (INTEL-06):
        congressional_intel: Dict carrying bill intelligence, enhanced
            delegation, committee activity, appropriations status, scan_date,
            and confidence scores. Populated by PacketOrchestrator from
            congressional_intel.json.

    Metadata:
        generated_at: ISO timestamp of packet generation.
        congress_session: Congressional session (default "119").
    """

    # Identity (REG-01, REG-03)
    tribe_id: str
    tribe_name: str
    states: list[str] = field(default_factory=list)
    ecoregions: list[str] = field(default_factory=list)
    bia_code: str = ""
    epa_id: str = ""

    # Congressional (CONG-01, CONG-02)
    districts: list[dict] = field(default_factory=list)
    senators: list[dict] = field(default_factory=list)
    representatives: list[dict] = field(default_factory=list)

    # Phase 6 stubs
    awards: list[dict] = field(default_factory=list)
    hazard_profile: dict = field(default_factory=dict)

    # Phase 7 stubs
    economic_impact: dict = field(default_factory=dict)

    # Vulnerability profile (Phase 19)
    # Composite vulnerability data combining hazard, social vulnerability,
    # and adaptive capacity metrics. Populated by VulnerabilityProfileBuilder.
    vulnerability_profile: dict = field(default_factory=dict)

    # Congressional intelligence (INTEL-06)
    # Dict carrying bill intelligence, enhanced delegation, committee activity,
    # appropriations status, scan_date, and confidence scores. Populated by
    # PacketOrchestrator from congressional_intel.json.
    congressional_intel: dict = field(default_factory=dict)

    # Metadata
    generated_at: str = ""
    congress_session: str = "119"

    def to_dict(self) -> dict:
        """Return a serializable dict of all fields.

        Uses dataclasses.asdict for deep conversion of nested structures.

        Returns:
            Dict with all field names as keys.
        """
        return asdict(self)
