"""Number entities for PowerAnt API."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PowerAntCoordinator
from .entity import PowerAntEntity, get_price_unit


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerAnt number entities."""

    coordinator: PowerAntCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    cheapest_hours = coordinator.data.get(
        "cheapest_hours_value"
    )

    if cheapest_hours is not None:
        entities.append(
            PowerAntCheapestHoursNumber(coordinator)
        )

    price_trigger = coordinator.data.get(
        "price_trigger_value"
    )

    if price_trigger is not None:
        entities.append(
            PowerAntPriceTriggerNumber(coordinator)
        )

    time_slots = coordinator.data.get(
        "time_slots_value"
    )

    if time_slots is not None:
        entities.append(
            PowerAntTimeSlotsNumber(coordinator)
        )

    if coordinator.data.get("tariffs") is not None:
        entities.extend(
            PowerAntTariffNumber(
                coordinator,
                hour,
            )
            for hour in range(24)
        )

    async_add_entities(entities)


class PowerAntCheapestHoursNumber(
    PowerAntEntity,
    NumberEntity,
):
    """PowerAnt cheapest hours setting."""

    _attr_has_entity_name = True
    _attr_translation_key = "cheapest_hours"
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_unit_of_measurement = "h"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_cheapest_hours_number"
        )

    @property
    def native_value(self) -> float | None:
        """Return current cheapest hours."""
        return self.coordinator.data.get(
            "cheapest_hours_value"
        )

    @property
    def native_step(self) -> float:
        """Return step based on electricity price resolution."""

        country_area = self.coordinator.data.get(
            "country_area",
            "",
        )

        if country_area.endswith("_15m"):
            return 0.25

        return 1.0

    @property
    def available(self) -> bool:
        """Return whether cheapest hours setting is available."""

        return (
            super().available
            and self.coordinator.data.get("mode")
            in (
                "time",
                "time_slots",
                "time_and_trigger",
                "time_or_trigger",
                "reverse_or",
            )
        )

    async def async_set_native_value(
        self,
        value: float,
    ) -> None:
        """Set cheapest hours."""

        await self.coordinator.async_set_cheapest_hours(
            value
        )


class PowerAntPriceTriggerNumber(
    PowerAntEntity,
    NumberEntity,
):
    """PowerAnt price trigger setting."""

    _attr_has_entity_name = True
    _attr_translation_key = "price_trigger"
    _attr_native_min_value = -10000
    _attr_native_max_value = 10000
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_price_trigger_number"
        )

    @property
    def native_value(self) -> float | None:
        """Return current price trigger."""
        return self.coordinator.data.get(
            "price_trigger_value"
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the price unit for the selected area."""

        return get_price_unit(
            self.coordinator.data.get("country_area", "")
        )

    @property
    def available(self) -> bool:
        """Return whether price trigger setting is available."""

        return (
            super().available
            and self.coordinator.data.get("mode")
            in (
                "trigger",
                "time_and_trigger",
                "time_or_trigger",
                "reverse_or",
            )
        )

    async def async_set_native_value(
        self,
        value: float,
    ) -> None:
        """Set price trigger."""

        await self.coordinator.async_set_price_trigger(
            value
        )


class PowerAntTimeSlotsNumber(
    PowerAntEntity,
    NumberEntity,
):
    """PowerAnt time slots setting."""

    _attr_has_entity_name = True
    _attr_translation_key = "time_slots"
    _attr_native_min_value = 1
    _attr_native_max_value = 12
    _attr_native_step = 1

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_time_slots_number"
        )

    @property
    def native_value(self) -> float | None:
        """Return current time slots."""
        return self.coordinator.data.get(
            "time_slots_value"
        )

    @property
    def available(self) -> bool:
        """Return whether time slots setting is available."""

        return (
            super().available
            and self.coordinator.data.get("mode") == "time_slots"
        )

    async def async_set_native_value(
        self,
        value: float,
    ) -> None:
        """Set time slots."""

        await self.coordinator.async_set_time_slots(
            value
        )


class PowerAntTariffNumber(
    PowerAntEntity,
    NumberEntity,
):
    """PowerAnt hourly transmission fee."""

    _attr_has_entity_name = True
    _attr_translation_key = "transmission_fee"
    _attr_native_min_value = -10000
    _attr_native_max_value = 10000
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX

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
            f"tariff_{hour:02d}_number"
        )

    @property
    def native_value(self) -> float | None:
        """Return current transmission fee."""

        value = self.coordinator.data.get(
            "tariffs",
            {},
        ).get(self._hour, "")

        text = str(
            "" if value is None else value
        ).strip().lower()

        if text in ("", "on", "off"):
            return None

        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the price unit for the selected area."""

        return get_price_unit(
            self.coordinator.data.get(
                "country_area",
                "",
            )
        )

    @property
    def available(self) -> bool:
        """Return whether transmission fee is active."""

        if not super().available:
            return False

        value = self.coordinator.data.get(
            "tariffs",
            {},
        ).get(self._hour, "")

        text = str(
            "" if value is None else value
        ).strip().lower()

        if text in ("", "on", "off"):
            return False

        try:
            float(text)
        except (TypeError, ValueError):
            return False

        return True

    async def async_set_native_value(
        self,
        value: float,
    ) -> None:
        """Set transmission fee."""

        await self.coordinator.async_set_tariff(
            self._hour,
            value,
        )


