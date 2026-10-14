"""PowerAnt electricity price savings calculation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def calculate_savings(
    schedule: Sequence[Mapping[str, Any]],
) -> float | None:
    """Calculate estimated savings percentage from a daily schedule.

    Matches the PowerAnt web application's switch-device calculation.
    Uses spot prices and final ON/OFF states.
    """

    if not schedule:
        return None

    prices = [float(period["price"]) for period in schedule]

    on_prices = [
        float(period["price"])
        for period in schedule
        if period["is_on"]
    ]

    average_price = sum(prices) / len(prices)

    your_average_price = (
        sum(on_prices) / len(on_prices)
        if on_prices
        else 0.0
    )

    if average_price == 0:
        return 0.0

    return min(
        ((average_price - your_average_price) / average_price) * 100,
        100.0,
    )
