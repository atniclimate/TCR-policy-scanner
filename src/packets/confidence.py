"""Confidence scoring for data sections.

Computes confidence scores from source weights and freshness decay
using exponential decay: confidence = source_weight * e^(-lambda * days).

Confidence levels for DOCX display:
- HIGH: >= 0.7 (data fresh and from authoritative source)
- MEDIUM: 0.4 - 0.69
- LOW: < 0.4
"""

import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Source weights matching scanner_config.json authority_weight values
DEFAULT_SOURCE_WEIGHTS: dict[str, float] = {
    "congress_gov": 0.80,
    "federal_register": 0.90,
    "grants_gov": 0.85,
    "usaspending": 0.70,
    "congressional_cache": 0.75,
    "inferred": 0.50,
}


def compute_confidence(
    source_weight: float,
    last_updated: str,
    decay_rate: float = 0.01,
    reference_date: datetime | None = None,
) -> float:
    """Compute confidence score from source weight and freshness.

    Uses exponential decay: confidence = source_weight * e^(-decay_rate * days).
    Default decay_rate of 0.01 gives a half-life of ~69 days, meaning data
    older than ~2 months starts losing confidence rapidly.

    Args:
        source_weight: Source authority weight 0.0-1.0.
        last_updated: ISO date string of last data update.
        decay_rate: Exponential decay rate (default 0.01, half-life ~69 days).
        reference_date: Reference date for staleness calc (default: now UTC).

    Returns:
        Confidence score 0.0-1.0 rounded to 3 decimal places.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)
    try:
        updated = datetime.fromisoformat(last_updated)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        days = max(0, (reference_date - updated).days)
    except (ValueError, TypeError):
        logger.warning("Could not parse last_updated '%s', assuming stale", last_updated)
        days = 365  # Unknown date -> assume very stale
    return round(source_weight * math.exp(-decay_rate * days), 3)


def confidence_level(score: float) -> str:
    """Map numeric confidence score to display level.

    Args:
        score: Confidence score 0.0-1.0.

    Returns:
        "HIGH" (>= 0.7), "MEDIUM" (0.4-0.69), or "LOW" (< 0.4).
    """
    if score >= 0.7:
        return "HIGH"
    elif score >= 0.4:
        return "MEDIUM"
    return "LOW"


def section_confidence(
    source: str,
    last_updated: str,
    decay_rate: float = 0.01,
    reference_date: datetime | None = None,
) -> dict:
    """Compute confidence for a document section.

    Convenience wrapper returning both numeric score and display level.
    Looks up source weight from DEFAULT_SOURCE_WEIGHTS, falling back to
    0.50 for unknown sources.

    Args:
        source: Data source name (key into DEFAULT_SOURCE_WEIGHTS).
        last_updated: ISO date string.
        decay_rate: Decay rate for exponential freshness.
        reference_date: Optional reference date.

    Returns:
        Dict with "score", "level", "source", "last_updated" keys.
    """
    weight = DEFAULT_SOURCE_WEIGHTS.get(source, 0.50)
    score = compute_confidence(weight, last_updated, decay_rate, reference_date)
    return {
        "score": score,
        "level": confidence_level(score),
        "source": source,
        "last_updated": last_updated,
    }
