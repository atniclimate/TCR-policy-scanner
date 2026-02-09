"""Multi-factor relevance scorer.

Scores each collected policy item against the ATNI program inventory using
five weighted factors: program match, Tribal keyword density, recency,
source authority, and action relevance.

Enhanced with:
- Tribal eligibility override: Grants.gov items with Tribal government
  eligibility codes are force-included above threshold
- ICR/guidance document subtype detection for bureaucratic friction signals
"""

import logging
from datetime import datetime, timezone

from dateutil import parser as dateparser

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Scores policy items for relevance to Tribal Climate Resilience programs."""

    def __init__(self, config: dict, programs: list[dict]):
        self.weights = config["scoring"]["weights"]
        self.critical_boost = config["scoring"]["critical_boost"]
        self.threshold = config["scoring"]["relevance_threshold"]
        self.tribal_keywords = [kw.lower() for kw in config.get("tribal_keywords", [])]
        self.action_keywords = [kw.lower() for kw in config.get("action_keywords", [])]
        self.programs = programs
        self.eligibility_override = config["scoring"].get("tribal_eligibility_override", True)

    def score_items(self, items: list[dict]) -> list[dict]:
        """Score all items and return those above the relevance threshold."""
        scored = []
        for item in items:
            result = self._score_item(item)
            if result["relevance_score"] >= self.threshold:
                scored.append(result)

        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        logger.info("Scored %d items; %d above threshold %.2f", len(items), len(scored), self.threshold)
        return scored

    def _score_item(self, item: dict) -> dict:
        """Compute the composite relevance score for a single item."""
        text = f"{item.get('title', '')} {item.get('abstract', '')}".lower()

        program_score, matched_programs = self._program_match(text, item)
        keyword_score = self._tribal_keyword_density(text)
        recency_score = self._recency(item.get("published_date", ""))
        authority_score = item.get("authority_weight", 0.5)
        action_score = self._action_relevance(text)

        w = self.weights
        composite = (
            w["program_match"] * program_score
            + w["tribal_keyword_density"] * keyword_score
            + w["recency"] * recency_score
            + w["source_authority"] * authority_score
            + w["action_relevance"] * action_score
        )

        # Apply critical-priority boost
        has_critical = any(p["priority"] == "critical" for p in matched_programs)
        if has_critical:
            composite = min(1.0, composite + self.critical_boost)

        # Tribal eligibility override: force-include grants where Tribal
        # governments are listed as eligible applicants even when keyword
        # density is low (catches "generic" titled resilience grants)
        eligibility_override = False
        if (self.eligibility_override
                and item.get("tribal_eligible")
                and item.get("tribal_eligibility_override")
                and composite < self.threshold):
            composite = max(composite, self.threshold + 0.05)
            eligibility_override = True

        # ICR/guidance subtype boost: information collection requests and
        # significant guidance documents are bureaucratic friction signals
        doc_subtype = item.get("document_subtype", "")
        if doc_subtype in ("icr", "guidance", "rfi", "anprm"):
            composite = min(1.0, composite + 0.05)

        item_scored = dict(item)
        item_scored.update({
            "relevance_score": round(composite, 4),
            "matched_programs": [p["id"] for p in matched_programs],
            "matched_program_names": [p["name"] for p in matched_programs],
            "score_breakdown": {
                "program_match": round(program_score, 4),
                "tribal_keyword_density": round(keyword_score, 4),
                "recency": round(recency_score, 4),
                "source_authority": round(authority_score, 4),
                "action_relevance": round(action_score, 4),
                "critical_boost_applied": has_critical,
                "eligibility_override": eligibility_override,
                "subtype_boost": doc_subtype if doc_subtype else None,
            },
        })
        return item_scored

    def _program_match(self, text: str, item: dict | None = None) -> tuple[float, list[dict]]:
        """Score based on matches to tracked program keywords and CFDA lookups."""
        matched = []
        total_hits = 0

        # Check for CFDA-based direct match from Grants.gov scraper
        cfda_match_id = (item or {}).get("cfda_program_match", "")
        if cfda_match_id:
            for program in self.programs:
                if program["id"] == cfda_match_id:
                    matched.append(program)
                    total_hits += 3  # CFDA match = strong signal
                    break

        for program in self.programs:
            if program in matched:
                continue
            hits = sum(1 for kw in program["keywords"] if kw.lower() in text)
            # Also check scanner_trigger_keywords if present
            trigger_kws = program.get("scanner_trigger_keywords", [])
            hits += sum(1 for kw in trigger_kws if kw.lower() in text)
            if hits > 0:
                matched.append(program)
                total_hits += hits

        if not matched:
            return 0.0, []
        # Normalize: 1 hit = 0.5, 3+ hits = 1.0
        return min(1.0, 0.3 + total_hits * 0.233), matched

    def _tribal_keyword_density(self, text: str) -> float:
        """Score based on concentration of Tribal-relevant terms."""
        words = text.split()
        if not words:
            return 0.0
        hits = sum(1 for kw in self.tribal_keywords if kw in text)
        density = hits / max(len(words), 1)
        # Normalize: map density to 0-1 score (cap at 10% density = 1.0)
        return min(1.0, density * 10)

    def _recency(self, date_str: str) -> float:
        """Score based on how recent the publication date is."""
        if not date_str:
            return 0.3  # default for missing dates
        try:
            pub_date = dateparser.parse(date_str)
            now = datetime.now(timezone.utc)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            days_old = (now - pub_date).days
            if days_old <= 1:
                return 1.0
            elif days_old <= 7:
                return 0.9
            elif days_old <= 14:
                return 0.75
            elif days_old <= 30:
                return 0.6
            elif days_old <= 60:
                return 0.4
            else:
                return 0.25
        except (ValueError, TypeError):
            return 0.3

    def _action_relevance(self, text: str) -> float:
        """Score based on presence of actionable policy signals."""
        hits = sum(1 for kw in self.action_keywords if kw in text)
        if hits == 0:
            return 0.0
        return min(1.0, hits * 0.25)
