"""Pydantic v2 schema models for TCR Policy Scanner data validation.

Provides strict validation models for all core data structures:
- FundingRecord: USAspending award data per Tribe
- TribeRecord: EPA/BIA Tribal registry records
- ProgramRecord: Federal program inventory entries
- PolicyPosition: Policy tracking positions with CI scoring
- HazardProfile: FEMA NRI + USFS wildfire hazard data per Tribe
- CongressionalDelegate: 119th Congress member records
- CongressionalDelegation: Per-Tribe congressional mapping
- VulnerabilityProfile: Composite vulnerability assessment per Tribe (v1.4)

All models use Pydantic v2 strict validation with field descriptions
and examples. Schema violations are bugs, not warnings.
"""

from src.schemas.models import (
    AwardCacheFile,
    CFDASummaryEntry,
    CommitteeAssignment,
    CongressionalDelegate,
    CongressionalDelegation,
    DistrictMapping,
    ExtensibleFields,
    FiscalYearRange,
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
from src.schemas.vulnerability import (
    CompositeComponent,
    CompositeScore,
    DataGapType,
    InvestmentPriorityTier,
    NRIExpanded,
    SVIProfile,
    SVITheme,
    VulnerabilityProfile,
)

__all__ = [
    # Core models (models.py)
    "AwardCacheFile",
    "CFDASummaryEntry",
    "CommitteeAssignment",
    "CongressionalDelegate",
    "CongressionalDelegation",
    "DistrictMapping",
    "ExtensibleFields",
    "FiscalYearRange",
    "FundingRecord",
    "HazardDetail",
    "HazardProfile",
    "HotSheetsStatus",
    "NRIComposite",
    "NRISource",
    "PolicyPosition",
    "ProgramRecord",
    "TribeRecord",
    # Vulnerability models (vulnerability.py) - v1.4
    "CompositeComponent",
    "CompositeScore",
    "DataGapType",
    "InvestmentPriorityTier",
    "NRIExpanded",
    "SVIProfile",
    "SVITheme",
    "VulnerabilityProfile",
]
