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

from .schedule import _calculate_status, _find_next_change
from .prices import _build_price_entries

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

        (
            device_model,
            firmware_version,
            capabilities,
            country_area,
        ) = _get_device_metadata(device)

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

        now_utc = datetime.now(timezone.utc)

        (
            now_local,
            day_prefix,
            tomorrow_prefix,
            is_15_minute,
            period_minutes,
            timestamp_format,
        ) = _get_price_period_context(
            prices,
            country_area,
            now_utc,
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
        (
            mode,
            cheapest_hours,
            price_trigger,
            time_slots,
        ) = _get_device_settings(device)

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

        current_period = _get_current_period_range(
            current["timestamp"],
            timestamp_format,
            period_minutes,
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

            "firmware_version": firmware_version,

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

            "current_period": current_period,

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



