"""PowerAnt scheduling calculations."""

from __future__ import annotations


def _apply_cheapest_time(
    entries: list[dict],
    cheapest_hours: float,
    period_minutes: int,
) -> None:
    """Apply PowerAnt cheapest time scheduling."""

    for entry in entries:
        entry["is_on"] = False

    total_intervals = len(entries)
    cheapest_hours = max(0, float(cheapest_hours or 0))

    if not total_intervals or cheapest_hours <= 0:
        return

    intervals_per_hour = 60 / period_minutes

    wanted_intervals = min(
        total_intervals,
        round(cheapest_hours * intervals_per_hour),
    )

    if wanted_intervals <= 0:
        return

    candidates = sorted(
        (entry for entry in entries if entry["rule"] != "ON"),
        key=lambda entry: (
            entry["effective"],
            entry["timestamp"],
        ),
    )

    for entry in candidates[:wanted_intervals]:
        entry["is_on"] = True
