from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PowerAntCoordinator
from .entity import PowerAntEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PowerAntCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            PowerAntBinarySensor(coordinator),
        ]
    )


class PowerAntBinarySensor(
    PowerAntEntity,
    BinarySensorEntity,
):
    _attr_has_entity_name = True
    _attr_translation_key = "control"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.product_key}_power"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["is_on"])

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        next_change = data.get("next_change")

        return {
            "mode": data.get("mode"),
            "cheapest_hours": data.get("cheapest_hours"),
            "time_slots": data.get("time_slots"),
            "current_price": data.get("current_price"),
            "current_period": data.get("current_period"),
            "next_change": (
                f'{next_change["time"]} -> '
                f'{"ON" if next_change["state"] else "OFF"}'
                if next_change
                else None
            ),
        }



