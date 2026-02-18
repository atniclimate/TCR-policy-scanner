"""Tests for sovereignty-first vocabulary constants module.

Validates all 9 constant groups in src/packets/vocabulary.py for:
- Completeness (all expected keys/fields present)
- Immutability (frozen dataclasses cannot be mutated)
- Sovereignty framing (no raw 'vulnerability' in headings/labels)
- Air gap integrity (forbidden terms not in section headings)
- Content correctness (gap messages frame federal infrastructure failures)
"""

import re

import pytest

from src.packets.vocabulary import (
    COMPOSITE_METHODOLOGY_BRIEF,
    CONTEXT_SENSITIVE_TERMS,
    EXPOSURE_CONTEXT,
    FORBIDDEN_DOC_B_TERMS,
    GAP_MESSAGES,
    INLINE_GAP,
    INLINE_PARTIAL,
    RATING_LABEL,
    SECTION_HEADINGS,
    SVI_THEME3_EXCLUSION_NOTE,
    SVI_THEME3_SHORT,
    TIER_DISPLAYS,
    SectionHeadings,
    TierDisplay,
)


# ---------------------------------------------------------------------------
# TestSectionHeadings
# ---------------------------------------------------------------------------


class TestSectionHeadings:
    """Tests for SECTION_HEADINGS frozen dataclass singleton."""

    def test_all_five_doc_types_have_headings(self):
        """All five document types (A-E) have non-empty heading strings."""
        assert isinstance(SECTION_HEADINGS.doc_a_main, str)
        assert len(SECTION_HEADINGS.doc_a_main) > 0
        assert isinstance(SECTION_HEADINGS.doc_b_main, str)
        assert len(SECTION_HEADINGS.doc_b_main) > 0
        assert isinstance(SECTION_HEADINGS.doc_c_main, str)
        assert len(SECTION_HEADINGS.doc_c_main) > 0
        assert isinstance(SECTION_HEADINGS.doc_d_main, str)
        assert len(SECTION_HEADINGS.doc_d_main) > 0
        assert isinstance(SECTION_HEADINGS.doc_e_main, str)
        assert len(SECTION_HEADINGS.doc_e_main) > 0

    def test_headings_are_frozen(self):
        """SectionHeadings dataclass is immutable."""
        with pytest.raises((AttributeError, TypeError)):
            SECTION_HEADINGS.doc_a_main = "Modified"  # type: ignore[misc]

    def test_no_vulnerability_in_headings(self):
        """No heading string contains 'vulnerability' (DEC-05 framing)."""
        headings = [
            SECTION_HEADINGS.doc_a_main,
            SECTION_HEADINGS.doc_b_main,
            SECTION_HEADINGS.doc_c_main,
            SECTION_HEADINGS.doc_d_main,
            SECTION_HEADINGS.doc_e_main,
        ]
        for heading in headings:
            assert "vulnerability" not in heading.lower(), (
                f"Heading contains forbidden word 'vulnerability': {heading}"
            )

    def test_headings_instance_is_section_headings(self):
        """SECTION_HEADINGS is an instance of SectionHeadings."""
        assert isinstance(SECTION_HEADINGS, SectionHeadings)

    def test_doc_a_is_investment_profile(self):
        """Doc A heading uses 'Investment Profile' framing."""
        assert "Investment Profile" in SECTION_HEADINGS.doc_a_main

    def test_doc_b_is_data_summary(self):
        """Doc B heading uses 'Data Summary' framing (facts only)."""
        assert "Data Summary" in SECTION_HEADINGS.doc_b_main

    def test_doc_e_is_assessment(self):
        """Doc E heading uses 'Assessment' framing."""
        assert "Assessment" in SECTION_HEADINGS.doc_e_main


# ---------------------------------------------------------------------------
# TestRatingLabel
# ---------------------------------------------------------------------------


class TestRatingLabel:
    """Tests for RATING_LABEL constant."""

    def test_rating_label_value(self):
        """RATING_LABEL has the approved value."""
        assert RATING_LABEL == "Resilience Investment Priority"

    def test_rating_label_no_vulnerability(self):
        """RATING_LABEL does not contain 'vulnerability'."""
        assert "vulnerability" not in RATING_LABEL.lower()

    def test_rating_label_is_string(self):
        """RATING_LABEL is a string."""
        assert isinstance(RATING_LABEL, str)


# ---------------------------------------------------------------------------
# TestTierDisplays
# ---------------------------------------------------------------------------


class TestTierDisplays:
    """Tests for TIER_DISPLAYS dictionary of TierDisplay dataclasses."""

    EXPECTED_TIERS = {"Critical", "High", "Elevated", "Moderate", "Low"}

    def test_all_five_tiers_present(self):
        """All five investment priority tiers are present."""
        assert set(TIER_DISPLAYS.keys()) == self.EXPECTED_TIERS

    def test_tier_colors_are_valid_hex(self):
        """Each tier color_hex is a valid 7-character hex color string."""
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for tier_name, tier in TIER_DISPLAYS.items():
            assert hex_pattern.match(tier.color_hex), (
                f"Tier '{tier_name}' has invalid color: {tier.color_hex}"
            )

    def test_tier_displays_are_frozen(self):
        """TierDisplay instances are immutable."""
        tier = TIER_DISPLAYS["Critical"]
        with pytest.raises((AttributeError, TypeError)):
            tier.label = "Modified"  # type: ignore[misc]

    def test_tier_descriptions_non_empty(self):
        """All tier descriptions are non-empty strings."""
        for tier_name, tier in TIER_DISPLAYS.items():
            assert isinstance(tier.description, str)
            assert len(tier.description) > 0, (
                f"Tier '{tier_name}' has empty description"
            )

    def test_tier_labels_match_keys(self):
        """Each TierDisplay label matches its dictionary key."""
        for tier_name, tier in TIER_DISPLAYS.items():
            assert tier.label == tier_name

    def test_tier_is_tier_display_instance(self):
        """All tier values are TierDisplay instances."""
        for tier in TIER_DISPLAYS.values():
            assert isinstance(tier, TierDisplay)

    def test_critical_is_red(self):
        """Critical tier uses red color."""
        assert TIER_DISPLAYS["Critical"].color_hex == "#DC2626"

    def test_low_is_green(self):
        """Low tier uses green color."""
        assert TIER_DISPLAYS["Low"].color_hex == "#16A34A"


# ---------------------------------------------------------------------------
# TestGapMessages
# ---------------------------------------------------------------------------


class TestGapMessages:
    """Tests for GAP_MESSAGES data gap framing dictionary."""

    EXPECTED_KEYS = {
        "MISSING_SVI",
        "PARTIAL_NRI",
        "ZERO_AREA_WEIGHT",
        "ALASKA_PARTIAL",
        "NO_COASTAL_DATA",
        "SOURCE_UNAVAILABLE",
    }

    def test_all_six_gap_types_present(self):
        """All 6 gap message types are present."""
        assert set(GAP_MESSAGES.keys()) == self.EXPECTED_KEYS

    def test_missing_svi_message_content(self):
        """MISSING_SVI references CDC Social Vulnerability Index."""
        assert "CDC Social Vulnerability Index" in GAP_MESSAGES["MISSING_SVI"]

    def test_partial_nri_message_content(self):
        """PARTIAL_NRI references FEMA National Risk Index."""
        assert "FEMA National Risk Index" in GAP_MESSAGES["PARTIAL_NRI"]

    def test_zero_area_weight_frames_as_federal_gap(self):
        """ZERO_AREA_WEIGHT frames gap as federal infrastructure issue."""
        msg = GAP_MESSAGES["ZERO_AREA_WEIGHT"]
        assert "federal data infrastructure gap" in msg

    def test_alaska_partial_has_placeholder(self):
        """ALASKA_PARTIAL contains {available_sources} placeholder."""
        assert "{available_sources}" in GAP_MESSAGES["ALASKA_PARTIAL"]

    def test_no_coastal_data_is_empty(self):
        """NO_COASTAL_DATA is an empty string (no message needed)."""
        assert GAP_MESSAGES["NO_COASTAL_DATA"] == ""

    def test_source_unavailable_has_placeholder(self):
        """SOURCE_UNAVAILABLE contains {source_name} placeholder."""
        assert "{source_name}" in GAP_MESSAGES["SOURCE_UNAVAILABLE"]

    def test_gap_messages_are_strings(self):
        """All gap messages are strings."""
        for key, msg in GAP_MESSAGES.items():
            assert isinstance(msg, str), f"GAP_MESSAGES['{key}'] is not a string"


# ---------------------------------------------------------------------------
# TestInlineMarkers
# ---------------------------------------------------------------------------


class TestInlineMarkers:
    """Tests for INLINE_PARTIAL and INLINE_GAP constants."""

    def test_inline_partial_value(self):
        """INLINE_PARTIAL has the expected value."""
        assert INLINE_PARTIAL == "[partial coverage]"

    def test_inline_gap_value(self):
        """INLINE_GAP has the expected value."""
        assert INLINE_GAP == "[federal data gap]"

    def test_inline_gap_frames_federal(self):
        """INLINE_GAP references federal responsibility."""
        assert "federal" in INLINE_GAP.lower()


# ---------------------------------------------------------------------------
# TestSVITheme3Notes
# ---------------------------------------------------------------------------


class TestSVITheme3Notes:
    """Tests for SVI Theme 3 exclusion notes."""

    def test_full_note_contains_sovereignty(self):
        """Full exclusion note invokes Tribal sovereignty framing."""
        assert "sovereignty" in SVI_THEME3_EXCLUSION_NOTE.lower()

    def test_full_note_mentions_three_themes(self):
        """Full note references three CDC SVI themes."""
        assert "three" in SVI_THEME3_EXCLUSION_NOTE.lower()

    def test_full_note_mentions_exclusion(self):
        """Full note explicitly states intentional exclusion."""
        assert "intentionally excluded" in SVI_THEME3_EXCLUSION_NOTE

    def test_full_note_mentions_theme_3(self):
        """Full note references Theme 3 by name."""
        assert "Theme 3" in SVI_THEME3_EXCLUSION_NOTE

    def test_short_note_is_brief(self):
        """Short note is under 50 characters."""
        assert len(SVI_THEME3_SHORT) < 50

    def test_short_note_mentions_three_themes(self):
        """Short note contains '3 CDC SVI themes'."""
        assert "3 CDC SVI themes" in SVI_THEME3_SHORT


# ---------------------------------------------------------------------------
# TestForbiddenTerms
# ---------------------------------------------------------------------------


class TestForbiddenTerms:
    """Tests for FORBIDDEN_DOC_B_TERMS frozenset."""

    def test_forbidden_set_is_frozenset(self):
        """FORBIDDEN_DOC_B_TERMS is a frozenset."""
        assert isinstance(FORBIDDEN_DOC_B_TERMS, frozenset)

    def test_contains_strategy_terms(self):
        """Frozenset contains 'strategic' and 'strategy'."""
        assert "strategic" in FORBIDDEN_DOC_B_TERMS
        assert "strategy" in FORBIDDEN_DOC_B_TERMS

    def test_contains_leverage_terms(self):
        """Frozenset contains 'leverage' and 'leveraging'."""
        assert "leverage" in FORBIDDEN_DOC_B_TERMS
        assert "leveraging" in FORBIDDEN_DOC_B_TERMS

    def test_contains_talking_points(self):
        """Frozenset contains talking point variants."""
        assert "talking point" in FORBIDDEN_DOC_B_TERMS
        assert "talking points" in FORBIDDEN_DOC_B_TERMS

    def test_minimum_term_count(self):
        """At least 10 forbidden terms are defined."""
        assert len(FORBIDDEN_DOC_B_TERMS) >= 10

    def test_contains_advocacy_terms(self):
        """Frozenset contains advocacy-related terms."""
        assert "advocacy lever" in FORBIDDEN_DOC_B_TERMS
        assert "member approach" in FORBIDDEN_DOC_B_TERMS


# ---------------------------------------------------------------------------
# TestContextSensitiveTerms
# ---------------------------------------------------------------------------


class TestContextSensitiveTerms:
    """Tests for CONTEXT_SENSITIVE_TERMS mapping."""

    def test_vulnerability_has_proper_noun_contexts(self):
        """'vulnerability' key exists with at least 2 context entries."""
        assert "vulnerability" in CONTEXT_SENSITIVE_TERMS
        assert len(CONTEXT_SENSITIVE_TERMS["vulnerability"]) >= 2

    def test_vulnerable_has_proper_noun_contexts(self):
        """'vulnerable' key exists with context entries."""
        assert "vulnerable" in CONTEXT_SENSITIVE_TERMS
        assert len(CONTEXT_SENSITIVE_TERMS["vulnerable"]) >= 1

    def test_all_contexts_are_proper_nouns(self):
        """Each context string starts with an uppercase letter."""
        for term, contexts in CONTEXT_SENSITIVE_TERMS.items():
            for context in contexts:
                assert context[0].isupper(), (
                    f"Context for '{term}' is not a proper noun: '{context}'"
                )

    def test_contexts_are_non_empty_strings(self):
        """All context values are non-empty strings."""
        for term, contexts in CONTEXT_SENSITIVE_TERMS.items():
            for context in contexts:
                assert isinstance(context, str)
                assert len(context) > 0


# ---------------------------------------------------------------------------
# TestExplanatoryFraming
# ---------------------------------------------------------------------------


class TestExplanatoryFraming:
    """Tests for EXPOSURE_CONTEXT and COMPOSITE_METHODOLOGY_BRIEF."""

    def test_exposure_context_value(self):
        """EXPOSURE_CONTEXT has the expected framing text."""
        assert EXPOSURE_CONTEXT == "disproportionate exposure to climate hazards"

    def test_composite_methodology_references_sources(self):
        """COMPOSITE_METHODOLOGY_BRIEF references all three data sources."""
        assert "FEMA National Risk Index" in COMPOSITE_METHODOLOGY_BRIEF
        assert "CDC Social Vulnerability Index" in COMPOSITE_METHODOLOGY_BRIEF
        assert "resilience capacity" in COMPOSITE_METHODOLOGY_BRIEF

    def test_composite_methodology_is_brief(self):
        """Methodology brief is reasonably concise (under 300 chars)."""
        assert len(COMPOSITE_METHODOLOGY_BRIEF) < 300


# ---------------------------------------------------------------------------
# TestAirGapIntegrity
# ---------------------------------------------------------------------------


class TestAirGapIntegrity:
    """Cross-cutting tests for vocabulary air gap enforcement."""

    def test_section_headings_no_strategy_language(self):
        """Section headings do not use strategy/advocacy language.

        FORBIDDEN_DOC_B_TERMS includes 'investment profile' and 'investment
        priority' because those phrases are banned from Doc B *body text*.
        However, they ARE the DEC-05 approved heading/label terms used by
        the rendering system. This test checks for the genuinely forbidden
        strategy terms (strategy, leverage, assertive, etc.) in headings.
        """
        # Strategy terms that should never appear in any heading
        strategy_terms = frozenset({
            "strategic", "strategy", "leverage", "leveraging",
            "approach", "messaging", "talking point", "talking points",
            "assertive", "advocacy lever", "member approach",
        })
        headings = [
            SECTION_HEADINGS.doc_a_main,
            SECTION_HEADINGS.doc_b_main,
            SECTION_HEADINGS.doc_c_main,
            SECTION_HEADINGS.doc_d_main,
            SECTION_HEADINGS.doc_e_main,
        ]
        for heading in headings:
            heading_lower = heading.lower()
            for term in strategy_terms:
                assert term not in heading_lower, (
                    f"Heading '{heading}' contains strategy term '{term}'"
                )

    def test_gap_messages_sovereignty_framing(self):
        """Gap messages about geographic/assessment failures frame as federal.

        MISSING_SVI, PARTIAL_NRI, ZERO_AREA_WEIGHT, and ALASKA_PARTIAL all
        describe federal data infrastructure gaps and must contain 'federal'.
        SOURCE_UNAVAILABLE is a generic availability message (any source) and
        NO_COASTAL_DATA is empty -- neither requires federal framing.
        """
        federal_framing_keys = {
            "MISSING_SVI",
            "PARTIAL_NRI",
            "ZERO_AREA_WEIGHT",
            "ALASKA_PARTIAL",
        }
        for key in federal_framing_keys:
            msg = GAP_MESSAGES[key]
            assert "federal" in msg.lower(), (
                f"GAP_MESSAGES['{key}'] does not frame gap as federal "
                f"infrastructure issue"
            )

    def test_rating_label_no_strategy_language(self):
        """RATING_LABEL does not contain strategy/advocacy language.

        'investment priority' is the DEC-05 approved label term, so it is
        not checked here. This test verifies the label does not contain
        genuinely forbidden strategy terms.
        """
        strategy_terms = frozenset({
            "strategic", "strategy", "leverage", "leveraging",
            "approach", "messaging", "talking point", "assertive",
            "advocacy lever", "member approach",
        })
        label_lower = RATING_LABEL.lower()
        for term in strategy_terms:
            assert term not in label_lower, (
                f"RATING_LABEL contains strategy term '{term}'"
            )

    def test_no_vulnerability_in_non_proper_noun_constants(self):
        """'vulnerability' does not appear outside federal proper nouns.

        Checks SECTION_HEADINGS, RATING_LABEL, INLINE markers, and
        SVI_THEME3_SHORT -- constants that should never contain the word.
        """
        safe_constants = [
            ("SECTION_HEADINGS.doc_a_main", SECTION_HEADINGS.doc_a_main),
            ("SECTION_HEADINGS.doc_b_main", SECTION_HEADINGS.doc_b_main),
            ("SECTION_HEADINGS.doc_c_main", SECTION_HEADINGS.doc_c_main),
            ("SECTION_HEADINGS.doc_d_main", SECTION_HEADINGS.doc_d_main),
            ("SECTION_HEADINGS.doc_e_main", SECTION_HEADINGS.doc_e_main),
            ("RATING_LABEL", RATING_LABEL),
            ("INLINE_PARTIAL", INLINE_PARTIAL),
            ("INLINE_GAP", INLINE_GAP),
            ("SVI_THEME3_SHORT", SVI_THEME3_SHORT),
        ]
        for name, value in safe_constants:
            assert "vulnerability" not in value.lower(), (
                f"{name} contains 'vulnerability': {value}"
            )
