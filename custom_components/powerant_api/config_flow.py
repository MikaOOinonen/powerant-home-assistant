from __future__ import annotations

import asyncio
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    PowerAntApiClient,
    PowerAntAuthError,
    PowerAntDeviceNotFoundError,
)

from .const import (
    CONF_API_KEY,
    CONF_PRODUCT_KEY,
    DOMAIN,
)


class PowerAntConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    VERSION = 1

    async def async_step_user(
        self,
        user_input=None,
    ):
        errors = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            product_key = user_input[CONF_PRODUCT_KEY].strip()

            #
            # Product key identifies the PowerAnt device.
            #
            await self.async_set_unique_id(product_key)
            self._abort_if_unique_id_configured()

            #
            # Test the official PowerAnt API before creating
            # the Home Assistant config entry.
            #
            session = async_get_clientsession(self.hass)

            client = PowerAntApiClient(
                session,
                api_key,
            )

            try:
                device = await client.async_get_device(
                    product_key
                )

                device_name = device.get(
                    "device_name",
                    "PowerAnt",
                )

                return self.async_create_entry(
                    title=device_name,
                    data={
                        CONF_API_KEY: api_key,
                        CONF_PRODUCT_KEY: product_key,
                    },
                )

            except (
                PowerAntAuthError,
                PowerAntDeviceNotFoundError,
            ):
                errors["base"] = "invalid_auth"

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ):
                errors["base"] = "cannot_connect"


        schema = vol.Schema(
            {
                vol.Required(CONF_PRODUCT_KEY): str,
                vol.Required(CONF_API_KEY): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


    async def async_step_reauth(
        self,
        entry_data,
    ):
        """Handle reauthentication."""

        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        return await self.async_step_reauth_confirm()


    async def async_step_reauth_confirm(
        self,
        user_input=None,
    ):
        """Confirm reauthentication."""

        errors = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()

            product_key = self._reauth_entry.data[
                CONF_PRODUCT_KEY
            ]

            session = async_get_clientsession(self.hass)

            client = PowerAntApiClient(
                session,
                api_key,
            )

            try:
                await client.async_get_device(
                    product_key
                )

            except (
                PowerAntAuthError,
                PowerAntDeviceNotFoundError,
            ):
                errors["base"] = "invalid_auth"

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ):
                errors["base"] = "cannot_connect"

            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={
                        CONF_API_KEY: api_key,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )



