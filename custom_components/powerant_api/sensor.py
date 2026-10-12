from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
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
    coordinator: PowerAntCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PowerAntCurrentPriceSensor(coordinator),
        PowerAntCurrentPeriodSensor(coordinator),
        PowerAntNextChangeSensor(coordinator),
        PowerAntScheduleSensor(coordinator),
    ]

    async_add_entities(entities)

class PowerAntCurrentPriceSensor(
    PowerAntEntity,
    SensorEntity,
):
    _attr_has_entity_name = True
    _attr_translation_key = "current_price"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.product_key}_current_price"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("current_price")

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the price unit for the selected area."""

        return get_price_unit(
            self.coordinator.data.get("country_area", "")
        )


class PowerAntCurrentPeriodSensor(
    PowerAntEntity,
    SensorEntity,
):
    _attr_has_entity_name = True
    _attr_translation_key = "current_period"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.product_key}_current_period"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("current_period")


class PowerAntNextChangeSensor(
    PowerAntEntity,
    SensorEntity,
):
    _attr_has_entity_name = True
    _attr_translation_key = "next_change"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.product_key}_next_change"
        )

    @property
    def native_value(self):
        next_change = self.coordinator.data.get("next_change")

        if not next_change:
            return "No scheduled change"

        state = "ON" if next_change["state"] else "OFF"

        return f'{next_change["time"]} -> {state}'


class PowerAntScheduleSensor(
    PowerAntEntity,
    SensorEntity,
):
    """PowerAnt calculated schedule sensor."""
    _attr_has_entity_name = True
    _attr_translation_key = "calculated_schedule"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_calculated_schedule"
        )

    @property
    def native_value(self):
        """Return number of calculated periods."""

        schedule = self.coordinator.data.get(
            "schedule",
            [],
        )

        return len(schedule)

    @property
    def extra_state_attributes(self):
        """Return calculated schedule data."""

        schedule = self.coordinator.data.get(
            "schedule",
            [],
        )

        tomorrow_schedule = self.coordinator.data.get(
            "tomorrow_schedule",
            [],
        )

        return {
            "schedule": schedule,
            "tomorrow_schedule": tomorrow_schedule,
        }


