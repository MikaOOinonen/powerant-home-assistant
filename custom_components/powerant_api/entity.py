"""Base entity for PowerAnt API."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PowerAntCoordinator


def get_price_unit(country_area: str) -> str:
    """Return the PowerAnt price unit for an area."""

    area = country_area.lower()

    if (
        area.startswith("sweden-")
        or area.startswith("norway-")
        or area.startswith("denmark-")
    ):
        return "öre/kWh"

    if (
        area.startswith("uk-")
        or area.startswith("uk_")
    ):
        return "p/kWh"

    if (
        area.startswith("poland-")
        or area.startswith("poland_")
    ):
        return "zł/kWh"

    return "¢/kWh"


class PowerAntEntity(
    CoordinatorEntity[PowerAntCoordinator],
):
    """Base class for PowerAnt entities."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return PowerAnt device information."""

        data = self.coordinator.data

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self.coordinator.product_key,
                )
            },
            name=data.get(
                "device_name",
                "PowerAnt",
            ),
            manufacturer="PowerAnt",
            model=data.get("device_model"),
            sw_version=(
                str(data["firmware_version"])
                if data.get("firmware_version") is not None
                else None
            ),
        )


