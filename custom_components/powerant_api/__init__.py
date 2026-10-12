from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_API_KEY,
    CONF_PRODUCT_KEY,
    DOMAIN,
)
from .coordinator import PowerAntCoordinator


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    coordinator = PowerAntCoordinator(
        hass,
        api_key=entry.data[CONF_API_KEY],
        product_key=entry.data[CONF_PRODUCT_KEY],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = coordinator

    coordinator.start_quarter_updates()

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(
            entry.entry_id
        )

        coordinator.stop_quarter_updates()

    return unload_ok
