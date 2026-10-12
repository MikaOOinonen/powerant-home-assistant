"""Select entities for PowerAnt API."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    POWERANT_COUNTRY_AREAS,
    POWERANT_MODES,
    POWERANT_PRICE_RESOLUTIONS,
)
from .coordinator import PowerAntCoordinator
from .entity import PowerAntEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerAnt select entities."""

    coordinator: PowerAntCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    mode = coordinator.data.get("mode")

    if mode not in (None, ""):
        entities.append(
            PowerAntModeSelect(coordinator)
        )

    country_area = coordinator.data.get(
        "country_area"
    )

    if country_area not in (None, ""):
        entities.extend(
            [
                PowerAntPriceAreaSelect(coordinator),
                PowerAntPriceResolutionSelect(coordinator),
            ]
        )

    if coordinator.data.get("tariffs") is not None:
        entities.extend(
            PowerAntTariffSelect(
                coordinator,
                hour,
            )
            for hour in range(24)
        )

    async_add_entities(entities)


def _format_price_area(area: str) -> str:
    """Format a PowerAnt price area for display."""

    if "-" not in area:
        return area

    country, area_code = area.rsplit("-", 1)

    return (
        f"{country.replace('_', ' ').title()} "
        f"{area_code.upper()}"
    )


POWERANT_MODE_DISPLAY = {
    "time": "Cheapest time",
    "time_slots": "Cheapest time per time slot",
    "trigger": "Price trigger",
    "time_and_trigger": "Cheapest time AND price trigger",
    "time_or_trigger": "Cheapest time OR price trigger",
    "reverse_or": "Reverse",
    "on": "On/Off switch",
    "off": "On/Off switch",
}


class PowerAntModeSelect(
    PowerAntEntity,
    SelectEntity,
):
    """PowerAnt operating mode selector."""

    _attr_has_entity_name = True
    _attr_translation_key = "operating_mode"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_mode_select"
        )

        self._attr_options = list(
            dict.fromkeys(
                POWERANT_MODE_DISPLAY[mode]
                for mode in POWERANT_MODES
                if mode in POWERANT_MODE_DISPLAY
            )
        )

    @property
    def current_option(self) -> str | None:
        """Return the current operating mode."""

        mode = self.coordinator.data.get("mode")

        return POWERANT_MODE_DISPLAY.get(mode)

    async def async_select_option(
        self,
        option: str,
    ) -> None:
        """Set the operating mode."""

        if option == "On/Off switch":
            mode = "off"
        else:
            mode = next(
                (
                    api_mode
                    for api_mode, display_name
                    in POWERANT_MODE_DISPLAY.items()
                    if display_name == option
                ),
                None,
            )

        if mode is None:
            raise ValueError(
                f"Unsupported PowerAnt operating mode: {option}"
            )

        await self.coordinator.async_set_mode(
            mode
        )


class PowerAntPriceAreaSelect(
    PowerAntEntity,
    SelectEntity,
):
    """PowerAnt electricity price area selector."""

    _attr_has_entity_name = True
    _attr_translation_key = "price_area"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_price_area_select"
        )

        self._area_to_display = {
            area: _format_price_area(area)
            for area in POWERANT_COUNTRY_AREAS
        }

        self._display_to_area = {
            display: area
            for area, display in self._area_to_display.items()
        }

        self._attr_options = list(
            self._display_to_area.keys()
        )

    @property
    def current_option(self) -> str | None:
        """Return the current price area."""

        country_area = self.coordinator.data.get(
            "country_area",
            "",
        )

        base_area = country_area.removesuffix("_15m")

        return self._area_to_display.get(
            base_area
        )

    async def async_select_option(
        self,
        option: str,
    ) -> None:
        """Set the electricity price area."""

        base_area = self._display_to_area.get(
            option
        )

        if base_area is None:
            raise ValueError(
                f"Unsupported PowerAnt price area: {option}"
            )

        await self.coordinator.async_set_price_area(
            base_area
        )


class PowerAntPriceResolutionSelect(
    PowerAntEntity,
    SelectEntity,
):
    """PowerAnt electricity price resolution selector."""

    _attr_has_entity_name = True
    _attr_translation_key = "price_resolution"
    _attr_options = POWERANT_PRICE_RESOLUTIONS

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_price_resolution_select"
        )

    @property
    def current_option(self) -> str | None:
        """Return the current price resolution."""

        country_area = self.coordinator.data.get(
            "country_area",
            "",
        )

        if not country_area:
            return None

        if country_area.endswith("_15m"):
            return "15 min"

        return "60 min"

    async def async_select_option(
        self,
        option: str,
    ) -> None:
        """Set the electricity price resolution."""

        await self.coordinator.async_set_price_resolution(
            option
        )


class PowerAntTariffSelect(
    PowerAntEntity,
    SelectEntity,
):
    """PowerAnt hourly tariff rule selector."""

    _attr_has_entity_name = True
    _attr_translation_key = "tariff"
    _attr_options = [
        "-",
        "Transmission fee",
        "Power on",
        "Power off",
    ]

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
        hour: int,
    ) -> None:
        super().__init__(coordinator)

        self._hour = hour
        next_hour = (hour + 1) % 24

        self._attr_translation_placeholders = {
            "start": f"{hour:02d}",
            "end": f"{next_hour:02d}",
        }

        self._attr_unique_id = (
            f"{coordinator.product_key}_"
            f"tariff_{hour:02d}_select"
        )

    @property
    def current_option(self) -> str:
        """Return the current tariff rule."""

        value = self.coordinator.data.get(
            "tariffs",
            {},
        ).get(self._hour, "")

        text = str(
            "" if value is None else value
        ).strip().lower()

        if text == "on":
            return "Power on"

        if text == "off":
            return "Power off"

        if text:
            return "Transmission fee"

        return "-"

    async def async_select_option(
        self,
        option: str,
    ) -> None:
        """Set the tariff rule."""

        values = {
            "-": "",
            "Power on": "on",
            "Power off": "off",
        }

        if option == "Transmission fee":
            await self.coordinator.async_set_tariff(
                self._hour,
                0.0,
            )
            return

        if option not in values:
            raise ValueError(
                f"Unsupported PowerAnt tariff rule: {option}"
            )

        await self.coordinator.async_set_tariff(
            self._hour,
            values[option],
        )


