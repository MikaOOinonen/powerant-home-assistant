"""PowerAnt device data extraction helpers."""

from __future__ import annotations


def _get_device_settings(
    device: dict,
) -> tuple[str, float, float, int]:
    """Extract scheduling settings from a PowerAnt device."""

    mode = device.get("mode", "")

    cheapest_hours = float(
        device.get("cheapest_hours") or 0
    )

    price_trigger = float(
        device.get("price_trigger") or 0
    )

    time_slots = int(
        float(device.get("time_slots") or 1)
    )

    return (
        mode,
        cheapest_hours,
        price_trigger,
        time_slots,
    )
