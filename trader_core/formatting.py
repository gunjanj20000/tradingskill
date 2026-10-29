"""Formatting utilities for Indian financial markets (INR currency, Lakhs, Crores)."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def format_inr(number, decimals=2) -> str:
    """Format a number according to the Indian numbering system.
    
    Example:
        1234567.89 -> '₹12,34,567.89'
        -50000 -> '-₹50,000.00'
    """
    if number is None:
        return "₹0.00"
    
    try:
        val = Decimal(str(number))
    except (InvalidOperation, TypeError, ValueError):
        return f"₹{number}"

    is_negative = val < 0
    val = abs(val)

    # Round to specified decimals
    quant_str = "0." + "0" * decimals if decimals > 0 else "0"
    rounded = val.quantize(Decimal(quant_str), rounding=ROUND_HALF_UP)
    s = f"{rounded:.{decimals}f}"
    
    if "." in s:
        integer_part, decimal_part = s.split(".")
        decimal_suffix = f".{decimal_part}" if decimals > 0 else ""
    else:
        integer_part = s
        decimal_suffix = ""

    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group remaining digits in pairs of 2 from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ",".join(groups) + "," + last3

    prefix = "-₹" if is_negative else "₹"
    return f"{prefix}{formatted_int}{decimal_suffix}"


def format_lakh_crore(number, decimals=2) -> str:
    """Format large INR numbers in Lakhs (L) and Crores (Cr).
    
    Example:
        15000000 -> '₹1.50 Cr'
        250000 -> '₹2.50 L'
        5000 -> '₹5,000.00'
    """
    if number is None:
        return "₹0.00"
    
    try:
        val = float(number)
    except (TypeError, ValueError):
        return str(number)

    abs_val = abs(val)
    prefix = "-" if val < 0 else ""

    if abs_val >= 10_000_000:  # 1 Crore = 10 Million
        return f"{prefix}₹{abs_val / 10_000_000:.{decimals}f} Cr"
    elif abs_val >= 100_000:   # 1 Lakh = 100 Thousand
        return f"{prefix}₹{abs_val / 100_000:.{decimals}f} L"
    else:
        return format_inr(number, decimals=decimals)


def format_pct(number, decimals=2, show_sign=True) -> str:
    """Format percentage with optional + sign."""
    if number is None:
        return "0.00%"
    try:
        val = float(number)
    except (TypeError, ValueError):
        return f"{number}%"
    sign = "+" if show_sign and val > 0 else ""
    return f"{sign}{val:.{decimals}f}%"
