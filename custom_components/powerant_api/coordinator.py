from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    PowerAntApiClient,
    PowerAntAuthError,
)

from .const import (
    API_URL,
    POWERANT_COUNTRY_AREAS,
    POWERANT_MODES,
    PRICE_BASE_URL,
    UPDATE_INTERVAL_MINUTES,
)


_LOGGER = logging.getLogger(__name__)


def _as_float_or_none(value):
    """Convert a PowerAnt numeric API value to float or None."""
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int_or_none(value):
    """Convert a PowerAnt integer API value to int or None."""
    if value in (None, ""):
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_bool_or_none(value):
    """Return a PowerAnt boolean API value or None."""
    if isinstance(value, bool):
        return value

    return None


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


def _apply_time_slots(
    entries: list[dict],
    cheapest_hours: float,
    time_slots: int,
    period_minutes: int,
) -> None:
    """Apply PowerAnt time slots scheduling."""

    for entry in entries:
        entry["is_on"] = False

    total_intervals = len(entries)
    cheapest_hours = max(
        0,
        float(cheapest_hours or 0),
    )
    raw_slots = int(time_slots or 0)

    if (
        not total_intervals
        or not raw_slots
        or cheapest_hours <= 0
    ):
        return

    num_slots = max(
        1,
        min(raw_slots, 24),
    )

    intervals_per_hour = 60 / period_minutes

    wanted_intervals = min(
        total_intervals,
        round(
            cheapest_hours * intervals_per_hour
        ),
    )

    if wanted_intervals <= 0:
        return

    #
    # 15-minute prices
    #
    # Divide the requested periods as evenly as possible
    # between the slots. Any remainder starts from Slot 1.
    #
    if period_minutes == 15:

        base_slot_size = (
            total_intervals // num_slots
        )

        extra_periods = (
            total_intervals % num_slots
        )

        base_wanted = (
            wanted_intervals // num_slots
        )

        extra_wanted = (
            wanted_intervals % num_slots
        )

        start_index = 0

        for slot_index in range(num_slots):

            slot_size = base_slot_size

            if slot_index < extra_periods:
                slot_size += 1

            end_index = (
                start_index + slot_size
            )

            slot_entries = entries[
                start_index:end_index
            ]

            slot_wanted = base_wanted

            if slot_index < extra_wanted:
                slot_wanted += 1

            candidates = sorted(
                (
                    entry
                    for entry in slot_entries
                    if entry["rule"] != "ON"
                ),
                key=lambda entry: (
                    entry["effective"],
                    entry["timestamp"],
                ),
            )

            for entry in candidates[:slot_wanted]:
                entry["is_on"] = True

            start_index = end_index

        return

    #
    # 60-minute prices
    #
    # Selection happens in rounds:
    #
    #   Round 1 -> cheapest hour from every slot
    #   Round 2 -> second cheapest hour from every slot
    #   ...
    #
    # Within each round the candidates are compared by price.
    #
    if period_minutes == 60:

        slot_candidates = {}

        for slot_number in range(num_slots):

            candidates = []

            for entry in entries:

                timestamp = entry["timestamp"]
                hour = int(timestamp[8:10])

                slot_index = min(
                    int(
                        hour * num_slots / 24
                    ),
                    num_slots - 1,
                )

                if (
                    slot_index == slot_number
                    and entry["rule"] != "ON"
                ):
                    candidates.append(entry)

            candidates.sort(
                key=lambda entry: (
                    entry["effective"],
                    entry["timestamp"],
                )
            )

            slot_candidates[
                slot_number
            ] = candidates

        remaining = wanted_intervals
        round_index = 0

        while remaining > 0:

            round_candidates = []

            for candidates in slot_candidates.values():

                if round_index < len(candidates):

                    entry = candidates[
                        round_index
                    ]

                    round_candidates.append(entry)

            if not round_candidates:
                break

            round_candidates.sort(
                key=lambda entry: (
                    entry["effective"],
                    entry["timestamp"],
                )
            )

            for entry in round_candidates:

                if remaining <= 0:
                    break

                entry["is_on"] = True
                remaining -= 1

            round_index += 1

        return


def _apply_cheapest_time(
    entries: list[dict],
    cheapest_hours: float,
    period_minutes: int,
) -> None:
    """Apply PowerAnt cheapest time scheduling."""

    for entry in entries:
        entry["is_on"] = False

    total_intervals = len(entries)

    cheapest_hours = max(
        0,
        float(cheapest_hours or 0),
    )

    if not total_intervals or cheapest_hours <= 0:
        return

    intervals_per_hour = 60 / period_minutes

    wanted_intervals = min(
        total_intervals,
        round(
            cheapest_hours * intervals_per_hour
        ),
    )

    if wanted_intervals <= 0:
        return

    candidates = sorted(
        (
            entry
            for entry in entries
            if entry["rule"] != "ON"
        ),
        key=lambda entry: (
            entry["effective"],
            entry["timestamp"],
        ),
    )

    for entry in candidates[:wanted_intervals]:
        entry["is_on"] = True


def _calculate_status(
    entries: list[dict],
    mode: str,
    cheapest_hours: float,
    price_trigger: float,
    time_slots: int,
    period_minutes: int,
) -> None:
    """Calculate PowerAnt control state for all price periods."""

    mode = str(mode or "").upper()

    #
    # First calculate the normal scheduling logic.
    #
    if mode == "ON":

        for entry in entries:
            entry["is_on"] = True

    elif mode == "OFF":

        for entry in entries:
            entry["is_on"] = False

    elif mode == "TIME":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

    elif mode == "TRIGGER":

        for entry in entries:
            entry["is_on"] = (
                entry["effective"] < price_trigger
            )

    elif mode == "TIME_AND_TRIGGER":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

        for entry in entries:
            entry["is_on"] = (
                entry["is_on"]
                and entry["effective"] < price_trigger
            )

    elif mode == "TIME_OR_TRIGGER":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

        for entry in entries:
            entry["is_on"] = (
                entry["is_on"]
                or entry["effective"] < price_trigger
            )

    elif mode == "REVERSE_OR":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

        for entry in entries:
            entry["is_on"] = (
                entry["is_on"]
                or entry["effective"] < price_trigger
            )

    elif mode == "TIME_SLOTS":

        _apply_time_slots(
            entries,
            cheapest_hours,
            time_slots,
            period_minutes,
        )

    else:

        for entry in entries:
            entry["is_on"] = False

    #
    # Apply tariff ON/OFF after normal scheduling.
    #
    # ON  -> force logical state ON
    # OFF -> force logical state OFF
    #
    for entry in entries:

        if entry["rule"] == "ON":
            entry["is_on"] = True

        elif entry["rule"] == "OFF":
            entry["is_on"] = False

    #
    # Reverse mode reverses the final relay output.
    #
    if mode == "REVERSE_OR":

        for entry in entries:
            entry["is_on"] = not entry["is_on"]


def _find_next_change(
    entries: list[dict],
    tomorrow_entries: list[dict],
    current_index: int,
    timestamp_format: str,
) -> dict | None:
    """Find the next ON/OFF state change."""

    current = entries[current_index]

    future_entries = (
        entries[current_index + 1:]
        + tomorrow_entries
    )

    for entry in future_entries:

        if entry["is_on"] != current["is_on"]:

            change = datetime.strptime(
                entry["timestamp"],
                timestamp_format,
            )

            return {
                "time": change.strftime("%H:%M"),
                "state": entry["is_on"],
            }

    return None


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


class PowerAntCoordinator(DataUpdateCoordinator[dict]):

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        product_key: str,
    ) -> None:

        super().__init__(
            hass,
            _LOGGER,
            name="PowerAnt API",
            update_interval=timedelta(
                minutes=UPDATE_INTERVAL_MINUTES
            ),
        )

        self.product_key = product_key

        self.api = PowerAntApiClient(
            async_get_clientsession(hass),
            api_key,
        )

        self._unsub_quarter_update = None

    def start_quarter_updates(self) -> None:

        if self._unsub_quarter_update is not None:
            return

        async def _quarter_refresh(now) -> None:
            await self.async_request_refresh()

        self._unsub_quarter_update = (
            async_track_time_change(
                self.hass,
                _quarter_refresh,
                minute=[0, 15, 30, 45],
                second=10,
            )
        )


    def stop_quarter_updates(self) -> None:

        if self._unsub_quarter_update is not None:
            self._unsub_quarter_update()
            self._unsub_quarter_update = None


    async def _async_update_data(self) -> dict:

        #
        # Official PowerAnt Share device / API
        #
        try:
            device = await self.api.async_get_device(
                self.product_key
            )

        except PowerAntAuthError as err:
            raise ConfigEntryAuthFailed(
                "PowerAnt API authentication failed"
            ) from err

        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error communicating with PowerAnt device API: {err}"
            ) from err

        expanded_device_type = (
            device.get("expand", {}).get("device_type", {})
        )

        device_model = expanded_device_type.get("device_name")

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

        #
        # Price data
        #
        try:
            prices = await self.api.async_get_prices(
                country_area
            )

        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error fetching PowerAnt price data: {err}"
            ) from err

        _LOGGER.debug(
            "PowerAnt price data: device=%s country_area=%s "
            "offset_hour=%s",
            device.get("device_name", "PowerAnt"),
            country_area,
            prices.get("offset_hour"),
        )

        offset_hours = float(
            prices.get("offset_hour", 0)
        )

        now_utc = datetime.now(timezone.utc)
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

        entries = _build_price_entries(
            prices,
            device,
            day_prefix,
            is_15_minute,
        )

        if not entries:
            raise UpdateFailed(
                "No PowerAnt price data for today"
            )

        tomorrow_entries = _build_price_entries(
            prices,
            device,
            tomorrow_prefix,
            is_15_minute,
        )

        #
        # Device settings
        #
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

        _calculate_status(
            entries,
            mode,
            cheapest_hours,
            price_trigger,
            time_slots,
            period_minutes,
        )

        if tomorrow_entries:
            _calculate_status(
                tomorrow_entries,
                mode,
                cheapest_hours,
                price_trigger,
                time_slots,
                period_minutes,
            )

        #
        # Current price period
        #
        current_index, current_key = _find_current_period(
            entries,
            now_local,
            is_15_minute,
        )

        if current_index is None:
            raise UpdateFailed(
                f"Current PowerAnt period "
                f"{current_key} not found"
            )

        current = entries[current_index]

        _LOGGER.debug(
            "PowerAnt current period: device=%s mode=%s "
            "timestamp=%s spot=%s tariff=%s effective=%s "
            "rule=%s is_on=%s",
            device.get("device_name", "PowerAnt"),
            mode,
            current.get("timestamp"),
            current.get("price"),
            current.get("tariff"),
            current.get("effective"),
            current.get("rule"),
            current.get("is_on"),
        )

        start = datetime.strptime(
            current["timestamp"],
            timestamp_format,
        )

        end = start + timedelta(
            minutes=period_minutes
        )

        #
        # Find next ON/OFF change
        #
        next_change = _find_next_change(
            entries,
            tomorrow_entries,
            current_index,
            timestamp_format,
        )

        return {
            "device": device,

            "device_name": device.get(
                "device_name",
                "PowerAnt",
            ),

            "device_model": device_model,

            "firmware_version": expanded_device_type.get(
                "version"
            ),

            "capabilities": capabilities,

            "product_key": self.product_key,

            "mode": mode,
            "cheapest_hours": cheapest_hours,
            "cheapest_hours_value": _as_float_or_none(
                device.get("cheapest_hours")
            ),

            "price_trigger_value": _as_float_or_none(
                device.get("price_trigger")
            ),

            "time_slots": time_slots,
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

            "schedule": entries,

            "tomorrow_schedule": tomorrow_entries,

            "child_lock_value": _as_bool_or_none(
                device.get("child_lock")
            ),

            "country_area": country_area,

            "is_on": current["is_on"],
            "current_price": current["price"],

            "current_period": (
                f"{start:%H:%M}-{end:%H:%M}"
            ),

            "next_change": next_change,
        }


    async def async_set_cheapest_hours(
        self,
        value: float,
    ) -> None:
        """Set the PowerAnt cheapest hours setting."""

        number = float(value)

        if number.is_integer():
            api_value = int(number)
        else:
            api_value = number

        old_value = self.data.get("cheapest_hours_value")

        # Update Home Assistant immediately.
        self.data["cheapest_hours_value"] = api_value
        self.async_update_listeners()

        try:
            # Update PowerAnt.
            await self.api.async_update_device(
                self.product_key,
                {
                    "cheapest_hours": api_value,
                },
            )

        except Exception:
            # Restore the previous value if the update fails.
            self.data["cheapest_hours_value"] = old_value
            self.async_update_listeners()
            raise

        # Confirm the value from the API.
        await self.async_request_refresh()


    async def async_set_price_trigger(
        self,
        value: float,
    ) -> None:
        """Set the PowerAnt price trigger setting."""

        number = float(value)

        if number.is_integer():
            api_value = int(number)
        else:
            api_value = number

        old_value = self.data.get("price_trigger_value")

        # Update Home Assistant immediately.
        self.data["price_trigger_value"] = api_value
        self.async_update_listeners()

        try:
            # Update PowerAnt.
            await self.api.async_update_device(
                self.product_key,
                {
                    "price_trigger": api_value,
                },
            )

        except Exception:
            # Restore the previous value if the update fails.
            self.data["price_trigger_value"] = old_value
            self.async_update_listeners()
            raise

        # Confirm the value from the API.
        await self.async_request_refresh()


    async def async_set_country_area(
        self,
        country_area: str,
    ) -> None:
        """Set the PowerAnt country area."""

        old_country_area = self.data.get("country_area")

        # Update Home Assistant immediately.
        self.data["country_area"] = country_area
        self.async_update_listeners()

        try:
            # Update PowerAnt.
            await self.api.async_update_device(
                self.product_key,
                {
                    "country_area": country_area,
                },
            )

        except Exception:
            # Restore the previous area if the update fails.
            self.data["country_area"] = old_country_area
            self.async_update_listeners()
            raise

        # Confirm the value from the API.
        await self.async_request_refresh()


    async def async_set_price_area(
        self,
        base_area: str,
    ) -> None:
        """Set price area while preserving price resolution."""

        if base_area not in POWERANT_COUNTRY_AREAS:
            raise ValueError(
                f"Unsupported PowerAnt price area: {base_area}"
            )

        current_area = self.data.get(
            "country_area",
            "",
        )

        is_15_minute = current_area.endswith("_15m")

        country_area = (
            f"{base_area}_15m"
            if is_15_minute
            else base_area
        )

        await self.async_set_country_area(
            country_area
        )


    async def async_set_price_resolution(
        self,
        resolution: str,
    ) -> None:
        """Set price resolution while preserving price area."""

        current_area = self.data.get(
            "country_area",
            "",
        )

        base_area = current_area.removesuffix("_15m")

        if base_area not in POWERANT_COUNTRY_AREAS:
            raise ValueError(
                f"Unsupported PowerAnt price area: {current_area}"
            )

        if resolution == "15 min":
            country_area = f"{base_area}_15m"
        elif resolution == "60 min":
            country_area = base_area
        else:
            raise ValueError(
                f"Unsupported PowerAnt price resolution: {resolution}"
            )

        await self.async_set_country_area(
            country_area
        )


    async def async_set_time_slots(
        self,
        value: float,
    ) -> None:
        """Set the PowerAnt time slots setting."""

        api_value = int(value)
        old_value = self.data.get("time_slots_value")

        # Update Home Assistant immediately.
        self.data["time_slots_value"] = api_value
        self.async_update_listeners()

        try:
            # Update PowerAnt.
            await self.api.async_update_device(
                self.product_key,
                {
                    "time_slots": api_value,
                },
            )

        except Exception:
            # Restore the previous value if the update fails.
            self.data["time_slots_value"] = old_value
            self.async_update_listeners()
            raise

        # Confirm the value from the API.
        await self.async_request_refresh()


    async def async_set_uses_tariffs(
        self,
        value: bool,
    ) -> None:
        """Enable or disable PowerAnt tariffs."""

        api_value = bool(value)
        old_value = self.data.get("uses_tariffs_value")

        # Update Home Assistant immediately.
        self.data["uses_tariffs_value"] = api_value
        self.async_update_listeners()

        try:
            await self.api.async_update_device(
                self.product_key,
                {
                    "uses_tariffs": api_value,
                },
            )

        except Exception:
            # Restore old value if PowerAnt update fails.
            self.data["uses_tariffs_value"] = old_value
            self.async_update_listeners()
            raise

        await self.async_request_refresh()


    async def async_set_tariff(
        self,
        hour: int,
        value,
    ) -> None:
        """Set one PowerAnt hourly tariff or schedule value."""

        if not 0 <= hour <= 23:
            raise ValueError(
                f"Unsupported PowerAnt tariff hour: {hour}"
            )

        field = f"tariff_{hour}"

        if isinstance(value, str):
            tariff_value = value.strip().lower()

            if tariff_value not in ("", "on", "off"):
                try:
                    tariff_value = float(tariff_value)
                except ValueError as err:
                    raise ValueError(
                        f"Unsupported PowerAnt tariff value: {value}"
                    ) from err
        else:
            tariff_value = float(value)

        old_value = self.data.get(
            "tariffs",
            {},
        ).get(hour)

        # Update Home Assistant immediately.
        self.data.setdefault(
            "tariffs",
            {},
        )[hour] = tariff_value

        self.async_update_listeners()

        try:
            await self.api.async_update_device(
                self.product_key,
                {
                    field: tariff_value,
                },
            )

        except Exception:
            # Restore the previous value if the update fails.
            self.data.setdefault(
                "tariffs",
                {},
            )[hour] = old_value

            self.async_update_listeners()
            raise

        # Confirm the value from the API.
        await self.async_request_refresh()


    async def async_set_mode(
        self,
        value: str,
    ) -> None:
        """Set the PowerAnt operating mode."""

        mode = str(value).lower()

        if mode not in POWERANT_MODES:
            raise ValueError(
                f"Unsupported PowerAnt mode: {value}"
            )

        old_mode = self.data.get("mode")

        # Update Home Assistant immediately.
        self.data["mode"] = mode
        self.async_update_listeners()

        try:
            # Update PowerAnt.
            await self.api.async_update_device(
                self.product_key,
                {
                    "mode": mode,
                },
            )

        except Exception:
            # Restore the previous mode if the update fails.
            self.data["mode"] = old_mode
            self.async_update_listeners()
            raise

        # Confirm the value from the API.
        await self.async_request_refresh()



