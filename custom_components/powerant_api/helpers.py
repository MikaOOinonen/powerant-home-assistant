"""Shared PowerAnt helper functions."""

from __future__ import annotations


def _as_bool_or_none(value):
    """Return a PowerAnt boolean API value or None."""
    if isinstance(value, bool):
        return value

    return None


def _as_float_or_none(value):
    """Convert a PowerAnt numeric API value to float or None."""
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
