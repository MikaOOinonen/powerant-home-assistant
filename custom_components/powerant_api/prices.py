"""PowerAnt electricity price processing."""

from __future__ import annotations


def _is_price_key(key: str) -> bool:
    return isinstance(key, str) and key.isdigit() and len(key) in (10, 12)
