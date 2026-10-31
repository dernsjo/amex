from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Characters banks use for "minus" besides ASCII '-': U+2212 MINUS SIGN, en dash.
_MINUS_SIGNS = ("−", "–")
# Thousand separators seen in Swedish exports: space, no-break space, narrow no-break space.
_GROUP_SEPARATORS = (" ", " ", " ")


def parse_amount(raw: str | int | float | Decimal) -> int:
    """Parse a bank amount into integer minor units (öre).

    Accepts "1 234,56", "−12,30" (Unicode minus), "-12.30", "500.0" and numbers.
    Raises ValueError on anything else instead of silently returning 0.
    """
    if isinstance(raw, (int, Decimal)):
        return to_minor(Decimal(raw))
    if isinstance(raw, float):
        return to_minor(Decimal(str(raw)))

    text = raw.strip()
    for sign in _MINUS_SIGNS:
        text = text.replace(sign, "-")
    for sep in _GROUP_SEPARATORS:
        text = text.replace(sep, "")
    if "," in text and "." in text:
        raise ValueError(f"Ambiguous amount {raw!r}: contains both ',' and '.'")
    text = text.replace(",", ".")

    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"Not a valid amount: {raw!r}") from None
    if not value.is_finite():
        raise ValueError(f"Not a valid amount: {raw!r}")
    return to_minor(value)


def to_minor(value: Decimal) -> int:
    """Convert a major-unit Decimal (kronor) to minor units, rounding half up."""
    return int((value * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def format_minor(minor: int) -> Decimal:
    """Convert minor units back to a 2-decimal major-unit Decimal."""
    return (Decimal(minor) / 100).quantize(Decimal("0.01"))
