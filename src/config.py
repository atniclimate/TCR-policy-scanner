"""Dynamic fiscal year configuration for TCR Policy Scanner.

Computes the current federal fiscal year based on the October 1 boundary:
    - Before October 1: current calendar year is the fiscal year
    - October 1 onward: next calendar year is the fiscal year

All fiscal year references in the codebase should import from this module
instead of hardcoding year strings.

Example:
    October 15, 2025 -> FY2026 (FY26)
    September 30, 2025 -> FY2025 (FY25)
"""

from datetime import date
from pathlib import Path


def _compute_fiscal_year(today: date | None = None) -> int:
    """Compute the federal fiscal year for a given date.

    The federal fiscal year starts October 1. A date in October-December
    of calendar year N belongs to fiscal year N+1.

    Args:
        today: Date to compute for. Defaults to today's date.

    Returns:
        Fiscal year as a 4-digit integer (e.g., 2026).
    """
    if today is None:
        today = date.today()
    if today.month >= 10:
        return today.year + 1
    return today.year


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
"""Absolute path to the project root directory (one level above src/)."""

FISCAL_YEAR_INT: int = _compute_fiscal_year()
"""Current fiscal year as integer (e.g., 2026)."""

FISCAL_YEAR_SHORT: str = f"FY{FISCAL_YEAR_INT % 100}"
"""Current fiscal year in short format (e.g., "FY26")."""

FISCAL_YEAR_LONG: str = f"FY{FISCAL_YEAR_INT}"
"""Current fiscal year in long format (e.g., "FY2026")."""

FISCAL_YEAR_END: str = f"{FISCAL_YEAR_INT}-09-30"
"""Last day of the current fiscal year (e.g., "2026-09-30")."""

FISCAL_YEAR_START: str = f"{FISCAL_YEAR_INT - 1}-10-01"
"""First day of the current fiscal year (e.g., "2025-10-01")."""
