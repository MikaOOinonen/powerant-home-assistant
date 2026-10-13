"""PowerAnt device data extraction helpers."""

from __future__ import annotations

from .helpers import (
    _as_bool_or_none,
    _as_float_or_none,
    _as_int_or_none,
)

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


def _get_device_metadata(
    device: dict,
) -> tuple:
    """Extract device metadata from PowerAnt API response."""

    expanded_device_type = (
        device.get("expand", {}).get("device_type", {})
    )

    device_model = expanded_device_type.get("device_name")

    firmware_version = expanded_device_type.get("version")

    capabilities = expanded_device_type.get(
        "device_capabilities",
        [],
    )

    if not isinstance(capabilities, list):
        capabilities = []

    country_area = device.get(
        "country_area",
        "finland-fi1_15m",
    )

    return (
        device_model,
        firmware_version,
        capabilities,
        country_area,
    )


def _build_coordinator_data(
    device: dict,
    metadata: dict,
    settings: dict,
    calculated: dict,
) -> dict:
    """Build the Home Assistant coordinator data."""

    current = calculated["current"]

    return {
        "device": device,
        "device_name": device.get(
            "device_name",
            "PowerAnt",
        ),
        "device_model": metadata["device_model"],
        "firmware_version": metadata["firmware_version"],
        "capabilities": metadata["capabilities"],
        "product_key": metadata["product_key"],
        "mode": settings["mode"],
        "cheapest_hours": settings["cheapest_hours"],
        "cheapest_hours_value": _as_float_or_none(
            device.get("cheapest_hours")
        ),
        "price_trigger_value": _as_float_or_none(
            device.get("price_trigger")
        ),
        "time_slots": settings["time_slots"],
        "time_slots_value": _as_int_or_none(
            device.get("time_slots")
        ),
        "uses_tariffs_value": _as_bool_or_none(
            device.get("uses_tariffs")
        ),
        "tariffs": {
            hour: device.get(f"tariff_{hour}", "")
            for hour in range(24)
        },
        "schedule": calculated["schedule"],
        "tomorrow_schedule": calculated["tomorrow_schedule"],
        "child_lock_value": _as_bool_or_none(
            device.get("child_lock")
        ),
        "country_area": metadata["country_area"],
        "is_on": current["is_on"],
        "current_price": current["price"],
        "current_period": calculated["current_period"],
        "next_change": calculated["next_change"],
    }
