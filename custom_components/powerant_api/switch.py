"""Switch entities for PowerAnt API."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up PowerAnt switch entities."""

    coordinator: PowerAntCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            PowerAntPowerSwitch(coordinator),
            PowerAntTariffsSwitch(coordinator),
        ]
    )


class PowerAntPowerSwitch(
    PowerAntEntity,
    SwitchEntity,
):
    """PowerAnt manual power switch."""

    _attr_has_entity_name = True
    _attr_translation_key = "power"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_power_switch"
        )

    @property
    def is_on(self) -> bool:
        """Return whether manual power is on."""

        return self.coordinator.data.get("mode") == "on"

    @property
    def available(self) -> bool:
        """Return whether manual power control is available."""

        return (
            super().available
            and self.coordinator.data.get("mode")
            in ("on", "off")
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Turn PowerAnt manually on."""

        await self.coordinator.async_set_mode("on")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn PowerAnt manually off."""

        await self.coordinator.async_set_mode("off")


class PowerAntTariffsSwitch(
    PowerAntEntity,
    SwitchEntity,
):
    """PowerAnt tariff switch."""

    _attr_has_entity_name = True
    _attr_translation_key = "tariffs"

    def __init__(
        self,
        coordinator: PowerAntCoordinator,
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.product_key}_tariffs_switch"
        )

    @property
    def is_on(self) -> bool:
        """Return whether tariffs are enabled."""

        return bool(
            self.coordinator.data.get("uses_tariffs_value")
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Enable PowerAnt tariffs."""

        await self.coordinator.async_set_uses_tariffs(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable PowerAnt tariffs."""

        await self.coordinator.async_set_uses_tariffs(False)


