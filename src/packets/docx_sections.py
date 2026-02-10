"""Document section renderers for Tribal advocacy packets.

Provides cover page, table of contents, and appendix section renderers
that are called by DocxEngine.generate() to assemble the full document.

Each function renders directly into the provided python-docx Document,
adding paragraphs and page breaks. No new Word sections are created
(all content shares the same header/footer).
"""

import logging

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from src.packets.context import TribePacketContext
from src.packets.docx_styles import (
    CI_STATUS_LABELS,
    COLORS,
    StyleManager,
    add_status_badge,
)

logger = logging.getLogger("tcr_scanner.packets.docx_sections")


def render_cover_page(
    document: Document,
    context: TribePacketContext,
    style_manager: StyleManager,
) -> None:
    """Render the cover page with Tribe identity and metadata.

    Adds title, Tribe name, delegation summary, geographic info,
    congressional session, generation date, and confidentiality notice.
    Ends with a page break.

    Args:
        document: python-docx Document to render into.
        context: TribePacketContext with all Tribe data.
        style_manager: StyleManager with registered custom styles.
    """
    # Top spacing
    document.add_paragraph("")

    # Main title
    document.add_paragraph(
        "FY26 Climate Resilience Program Priorities",
        style="Heading 1",
    )

    # Tribe name subtitle
    document.add_paragraph(context.tribe_name, style="HS Title")

    # Delegation summary
    num_senators = len(context.senators) if context.senators else 0
    num_reps = len(context.representatives) if context.representatives else 0
    delegation_parts = []
    if num_senators:
        delegation_parts.append(
            f"{num_senators} Senator{'s' if num_senators != 1 else ''}"
        )
    if num_reps:
        delegation_parts.append(
            f"{num_reps} Representative{'s' if num_reps != 1 else ''}"
        )
    delegation_summary = ", ".join(delegation_parts) if delegation_parts else "No delegation data"

    document.add_paragraph(
        f"Prepared for the offices of: {delegation_summary}",
        style="HS Body",
    )

    # Geographic and session metadata
    states_str = ", ".join(context.states) if context.states else "N/A"
    document.add_paragraph(f"State(s): {states_str}", style="HS Body")

    ecoregions_str = ", ".join(context.ecoregions) if context.ecoregions else "N/A"
    document.add_paragraph(f"Ecoregion(s): {ecoregions_str}", style="HS Body")

    document.add_paragraph(
        f"Congressional Session: {context.congress_session}",
        style="HS Body",
    )

    # Generation date (date portion only)
    gen_date = context.generated_at[:10] if context.generated_at else "N/A"
    document.add_paragraph(f"Generated: {gen_date}", style="HS Body")

    # Confidentiality notice (centered, small)
    conf_para = document.add_paragraph(
        "CONFIDENTIAL -- For Congressional Office Use Only",
        style="HS Small",
    )
    conf_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Page break after cover
    document.add_page_break()

    logger.debug("Rendered cover page for %s", context.tribe_name)


def render_table_of_contents(
    document: Document,
    programs: list[dict],
    context: TribePacketContext,
    style_manager: StyleManager,
) -> None:
    """Render a table of contents listing program Hot Sheets.

    Lists each program with a numbered entry and inline CI status badge.
    Ends with a page break.

    Args:
        document: python-docx Document to render into.
        programs: List of relevant program dicts (already sorted by relevance).
        context: TribePacketContext for the Tribe name reference.
        style_manager: StyleManager with registered custom styles.
    """
    document.add_paragraph("Program Hot Sheets", style="Heading 2")

    for i, program in enumerate(programs, 1):
        name = program.get("name", "Unknown Program")
        ci_status = program.get("ci_status", "")

        entry_para = document.add_paragraph(style="HS Body")
        entry_para.add_run(f"{i}. {name}")

        if ci_status:
            # Add space then inline badge
            entry_para.add_run("  ")
            label = CI_STATUS_LABELS.get(ci_status, ci_status)
            badge_run = entry_para.add_run(f"[{label}]")
            badge_run.font.size = Pt(8)
            badge_run.font.color.rgb = COLORS.muted

    # Summary note
    document.add_paragraph(
        f"This packet contains {len(programs)} program analyses tailored "
        f"to {context.tribe_name}'s climate risk profile and geographic context.",
        style="HS Body",
    )

    # Page break after TOC
    document.add_page_break()

    logger.debug(
        "Rendered table of contents with %d programs for %s",
        len(programs),
        context.tribe_name,
    )


def render_appendix(
    document: Document,
    omitted_programs: list[dict],
    context: TribePacketContext,
    style_manager: StyleManager,
) -> None:
    """Render the appendix listing omitted (lower-priority) programs.

    If no programs were omitted, adds a brief note and returns.
    Otherwise lists each omitted program with description, access/funding
    type, and CI status.

    Args:
        document: python-docx Document to render into.
        omitted_programs: List of program dicts not included in Hot Sheets.
        context: TribePacketContext for Tribe name reference.
        style_manager: StyleManager with registered custom styles.
    """
    document.add_paragraph("Appendix: Additional Programs", style="Heading 2")

    if not omitted_programs:
        document.add_paragraph(
            "All tracked programs are included in this packet.",
            style="HS Body",
        )
        logger.debug("Appendix: no omitted programs for %s", context.tribe_name)
        return

    # Intro paragraph
    document.add_paragraph(
        f"The following programs were assessed as lower priority for "
        f"{context.tribe_name} based on hazard profile and geographic "
        f"relevance. They may still be relevant for specific project needs.",
        style="HS Body",
    )

    for program in omitted_programs:
        name = program.get("name", "Unknown Program")
        ci_status = program.get("ci_status", "")
        description = program.get("description", "")
        access_type = program.get("access_type", "")
        funding_type = program.get("funding_type", "")
        agency = program.get("agency", "the administering agency")

        # Program name (bold) + CI status inline
        name_para = document.add_paragraph(style="HS Body")
        name_run = name_para.add_run(name)
        name_run.bold = True

        if ci_status:
            label = CI_STATUS_LABELS.get(ci_status, ci_status)
            name_para.add_run(f"  [{label}]")

        # Description
        if description:
            document.add_paragraph(description, style="HS Body")

        # Access type and funding type
        meta_parts = []
        if access_type:
            meta_parts.append(
                f"Access: {access_type.replace('_', ' ').title()}"
            )
        if funding_type:
            meta_parts.append(f"Funding: {funding_type}")
        if meta_parts:
            document.add_paragraph(" | ".join(meta_parts), style="HS Small")

        # Contact info
        document.add_paragraph(
            f"Learn more: Contact your program specialist or visit "
            f"{agency} for current application information.",
            style="HS Small",
        )

    logger.debug(
        "Rendered appendix with %d omitted programs for %s",
        len(omitted_programs),
        context.tribe_name,
    )
