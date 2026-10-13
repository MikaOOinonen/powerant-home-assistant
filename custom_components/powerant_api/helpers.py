"""Shared PowerAnt helper functions."""

from __future__ import annotations


def _as_bool_or_none(value):
    """Return a PowerAnt boolean API value or None."""
    if isinstance(value, bool):
        return value

    return None
