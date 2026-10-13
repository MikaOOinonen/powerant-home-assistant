"""PowerAnt electricity price processing."""

from __future__ import annotations


def _is_price_key(key: str) -> bool:
    return isinstance(key, str) and key.isdigit() and len(key) in (10, 12)

def _as_bool_or_none(value):
    """Return a PowerAnt boolean API value or None."""
    if isinstance(value, bool):
        return value

    return None


def _build_price_entries(
    prices: dict,
    device: dict,
    prefix: str,
    is_15_minute: bool,
) -> list[dict]:
    """Build PowerAnt price entries for one day."""

    price_key_length = (
        12 if is_15_minute else 10
    )

    uses_tariffs = (
        _as_bool_or_none(
            device.get("uses_tariffs")
        )
        is True
    )

    entries = []

    for key, value in prices.items():

        if (
            _is_price_key(key)
            and len(key) == price_key_length
            and key.startswith(prefix)
        ):
            spot = float(value)

            hour = int(key[8:10])

            tariff_value = ""

            if uses_tariffs:
                tariff_value = device.get(
                    f"tariff_{hour}",
                    "",
                )

            tariff_text = str(
                tariff_value or ""
            ).strip().lower()

            rule = "-"
            tariff = 0.0
            effective = spot

            if tariff_text == "on":
                rule = "ON"

            elif tariff_text == "off":
                rule = "OFF"

            elif tariff_text:
                try:
                    tariff = float(tariff_text)
                    effective = spot + tariff
                    rule = f"+{tariff:g}"

                except ValueError:
                    rule = f"? {tariff_text}"

            entries.append(
                {
                    "timestamp": key,
                    "price": spot,
                    "tariff": tariff,
                    "effective": effective,
                    "rule": rule,
                    "is_on": False,
                }
            )

    entries.sort(
        key=lambda entry: entry["timestamp"]
    )

    return entries
