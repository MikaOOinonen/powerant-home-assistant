"""PowerAnt electricity price processing."""

from __future__ import annotations

from datetime import datetime, timedelta

from .helpers import _as_bool_or_none


def _is_price_key(key: str) -> bool:
    return isinstance(key, str) and key.isdigit() and len(key) in (10, 12)


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


def _find_current_period(
    entries: list[dict],
    now_local: datetime,
    is_15_minute: bool,
) -> tuple[int | None, str]:
    """Find the current electricity price period."""

    if is_15_minute:
        minute = (
            now_local.minute // 15
        ) * 15

        current_key = (
            now_local.strftime("%Y%m%d%H")
            + f"{minute:02d}"
        )
    else:
        current_key = now_local.strftime(
            "%Y%m%d%H"
        )

    current_index = next(
        (
            index
            for index, entry in enumerate(entries)
            if entry["timestamp"] == current_key
        ),
        None,
    )

    return current_index, current_key


def _get_price_period_context(
    prices: dict,
    country_area: str,
    now_utc: datetime,
) -> tuple[datetime, str, str, bool, int, str]:
    """Build date and resolution context for price periods."""

    offset_hours = float(
        prices.get("offset_hour", 0)
    )

    now_local = now_utc + timedelta(
        hours=offset_hours
    )

    day_prefix = now_local.strftime("%Y%m%d")

    tomorrow_prefix = (
        now_local + timedelta(days=1)
    ).strftime("%Y%m%d")

    is_15_minute = country_area.endswith("_15m")
    period_minutes = 15 if is_15_minute else 60

    timestamp_format = (
        "%Y%m%d%H%M"
        if is_15_minute
        else "%Y%m%d%H"
    )

    return (
        now_local,
        day_prefix,
        tomorrow_prefix,
        is_15_minute,
        period_minutes,
        timestamp_format,
    )


def _get_current_period_range(
    timestamp: str,
    timestamp_format: str,
    period_minutes: int,
) -> str:
    """Return the current price period as HH:MM-HH:MM."""

    start = datetime.strptime(
        timestamp,
        timestamp_format,
    )

    end = start + timedelta(
        minutes=period_minutes
    )

    return f"{start:%H:%M}-{end:%H:%M}"
