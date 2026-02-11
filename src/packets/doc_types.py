"""Document type configuration for audience-differentiated advocacy packets.

Defines four document types (A/B/C/D) with distinct audience targeting,
confidentiality markings, content-filter flags, and header/footer templates.

Air gap enforced: no organizational names (ATNI, NCAI, etc.) or tool names
appear in any document configuration. Documents stand on their own as
data-driven outputs.

Document Types:
    DOC_A: Tribal Internal Strategy (confidential, full strategy content)
    DOC_B: Tribal Congressional Overview (public-facing, facts only)
    DOC_C: Regional InterTribal Strategy (confidential, regional scope)
    DOC_D: Regional Congressional Overview (public-facing, regional scope)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentTypeConfig:
    """Configuration for a single document type variant.

    Controls audience targeting, confidentiality, content inclusion flags,
    and header/footer templates for generated DOCX documents.

    Attributes:
        doc_type: Document type identifier ("A", "B", "C", "D").
        audience: Target audience ("internal" or "congressional").
        scope: Geographic scope ("tribal" or "regional").
        title_template: Cover page title text.
        header_template: Per-page header with {tribe_name}/{region_name}
            placeholders for runtime substitution.
        footer_template: Per-page footer text.
        confidential: Whether CONFIDENTIAL banner appears.
        include_strategy: Include leverage, approach, messaging sections.
        include_advocacy_lever: Include per-program advocacy lever text.
        include_member_approach: Include member-specific approach
            recommendations.
        include_messaging_framework: Include audience-calibrated talking
            points section.
        structural_asks_framing: How structural asks are presented
            ("strategic" or "policy_recommendation").
        narrative_voice: Tone of document ("assertive" or "objective").
        filename_suffix: Suffix for generated filenames.
    """

    doc_type: str
    audience: str
    scope: str
    title_template: str
    header_template: str
    footer_template: str
    confidential: bool
    include_strategy: bool
    include_advocacy_lever: bool
    include_member_approach: bool
    include_messaging_framework: bool
    structural_asks_framing: str
    narrative_voice: str
    filename_suffix: str

    @property
    def is_internal(self) -> bool:
        """Whether this document targets an internal audience."""
        return self.audience == "internal"

    @property
    def is_congressional(self) -> bool:
        """Whether this document targets a congressional audience."""
        return self.audience == "congressional"

    @property
    def is_tribal(self) -> bool:
        """Whether this document has Tribal (single-Tribe) scope."""
        return self.scope == "tribal"

    @property
    def is_regional(self) -> bool:
        """Whether this document has regional (multi-Tribe) scope."""
        return self.scope == "regional"

    def format_header(
        self,
        tribe_name: str | None = None,
        region_name: str | None = None,
    ) -> str:
        """Substitute placeholders in header_template.

        Args:
            tribe_name: Tribe name for {tribe_name} placeholder.
            region_name: Region name for {region_name} placeholder.

        Returns:
            Header string with placeholders replaced.
        """
        result = self.header_template
        if tribe_name is not None:
            result = result.replace("{tribe_name}", tribe_name)
        if region_name is not None:
            result = result.replace("{region_name}", region_name)
        return result

    def format_filename(self, slug: str) -> str:
        """Generate a filename from a slug and this config's suffix.

        Args:
            slug: Identifier slug (e.g., tribe_id or region_id).

        Returns:
            Filename string like "{slug}_{suffix}_fy26.docx".
        """
        return f"{slug}_{self.filename_suffix}_fy26.docx"


# ---------------------------------------------------------------------------
# Pre-built document type instances
# ---------------------------------------------------------------------------

DOC_A = DocumentTypeConfig(
    doc_type="A",
    audience="internal",
    scope="tribal",
    title_template="FY26 Federal Funding Overview & Strategy",
    header_template="{tribe_name} | Internal Strategy | CONFIDENTIAL",
    footer_template="Confidential: For Internal Use Only",
    confidential=True,
    include_strategy=True,
    include_advocacy_lever=True,
    include_member_approach=True,
    include_messaging_framework=True,
    structural_asks_framing="strategic",
    narrative_voice="assertive",
    filename_suffix="internal_strategy",
)
"""Tribal Internal Strategy -- full strategy content, confidential."""

DOC_B = DocumentTypeConfig(
    doc_type="B",
    audience="congressional",
    scope="tribal",
    title_template="FY26 Climate Resilience Program Priorities",
    header_template="{tribe_name} | FY26 Climate Resilience Program Priorities",
    footer_template="For Congressional Office Use",
    confidential=False,
    include_strategy=False,
    include_advocacy_lever=False,
    include_member_approach=False,
    include_messaging_framework=False,
    structural_asks_framing="policy_recommendation",
    narrative_voice="objective",
    filename_suffix="congressional_overview",
)
"""Tribal Congressional Overview -- factual, for handoff to offices."""

DOC_C = DocumentTypeConfig(
    doc_type="C",
    audience="internal",
    scope="regional",
    title_template="FY26 InterTribal Climate Resilience Strategy",
    header_template="{region_name} | Regional Strategy | CONFIDENTIAL",
    footer_template="Confidential: For Internal Use Only",
    confidential=True,
    include_strategy=True,
    include_advocacy_lever=True,
    include_member_approach=True,
    include_messaging_framework=False,
    structural_asks_framing="strategic",
    narrative_voice="assertive",
    filename_suffix="intertribal_strategy",
)
"""Regional InterTribal Strategy -- coordinated approach, confidential."""

DOC_D = DocumentTypeConfig(
    doc_type="D",
    audience="congressional",
    scope="regional",
    title_template="FY26 Regional Climate Resilience Overview",
    header_template="{region_name} | FY26 Regional Climate Resilience Overview",
    footer_template="For Congressional Office Use",
    confidential=False,
    include_strategy=False,
    include_advocacy_lever=False,
    include_member_approach=False,
    include_messaging_framework=False,
    structural_asks_framing="policy_recommendation",
    narrative_voice="objective",
    filename_suffix="congressional_overview",
)
"""Regional Congressional Overview -- factual, regional aggregate."""

DOC_TYPES: dict[str, DocumentTypeConfig] = {
    "A": DOC_A,
    "B": DOC_B,
    "C": DOC_C,
    "D": DOC_D,
}
"""Lookup dict for document type configs by type letter."""
