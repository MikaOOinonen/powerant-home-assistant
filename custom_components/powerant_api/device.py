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
