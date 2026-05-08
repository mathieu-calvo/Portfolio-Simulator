"""Currency display helpers."""

from __future__ import annotations

_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CHF": "CHF ",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
}


def currency_symbol(code: str | None) -> str:
    """Return a display symbol for a currency code.

    Falls back to the code itself with a trailing space when unknown so the
    caller can still produce a sensible label like "XYZ 1,000".
    """
    if not code:
        return "$"
    code = str(code).upper()
    return _SYMBOLS.get(code, f"{code} ")


def format_amount(value: float, code: str | None, decimals: int = 0) -> str:
    """Format a numeric amount with the right currency symbol."""
    sym = currency_symbol(code)
    return f"{sym}{value:,.{decimals}f}"
