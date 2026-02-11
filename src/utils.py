"""Shared utility functions for TCR Policy Scanner.

Contains the canonical implementations of common formatting functions
used across the codebase. All callsites should import from here
rather than maintaining local copies.
"""


def format_dollars(amount: float) -> str:
    """Format a dollar amount with commas and no decimal places.

    The single source of truth for dollar formatting across all modules.
    Produces output like "$1,234,567" for positive amounts and "-$1,234,567"
    for negative amounts.

    Args:
        amount: Dollar amount as a float or int.

    Returns:
        Formatted string with dollar sign and thousand separators.
    """
    return f"${amount:,.0f}"
