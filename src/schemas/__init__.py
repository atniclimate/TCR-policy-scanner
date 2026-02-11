"""Pydantic v2 schema models for TCR Policy Scanner data validation.

Provides strict validation models for all core data structures:
- FundingRecord: USAspending award data per Tribe
- TribeRecord: EPA/BIA Tribal registry records
- ProgramRecord: Federal program inventory entries
- PolicyPosition: Policy tracking positions with CI scoring
- HazardProfile: FEMA NRI + USFS wildfire hazard data per Tribe
- CongressionalDelegate: 119th Congress member records
- CongressionalDelegation: Per-Tribe congressional mapping

All models use Pydantic v2 strict validation with field descriptions
and examples. Schema violations are bugs, not warnings.
"""

from src.schemas.models import (
    AwardCacheFile,
    CommitteeAssignment,
    CongressionalDelegate,
    CongressionalDelegation,
    DistrictMapping,
    ExtensibleFields,
    FundingRecord,
    HazardDetail,
    HazardProfile,
    HotSheetsStatus,
    NRIComposite,
    NRISource,
    PolicyPosition,
    ProgramRecord,
    TribeRecord,
)

__all__ = [
    "AwardCacheFile",
    "CommitteeAssignment",
    "CongressionalDelegate",
    "CongressionalDelegation",
    "DistrictMapping",
    "ExtensibleFields",
    "FundingRecord",
    "HazardDetail",
    "HazardProfile",
    "HotSheetsStatus",
    "NRIComposite",
    "NRISource",
    "PolicyPosition",
    "ProgramRecord",
    "TribeRecord",
]
