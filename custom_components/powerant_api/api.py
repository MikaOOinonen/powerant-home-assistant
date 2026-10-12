"""PowerAnt API client."""

from __future__ import annotations

import aiohttp

from .const import API_URL, PRICE_BASE_URL


class PowerAntApiError(Exception):
    """Base exception for PowerAnt API errors."""


class PowerAntAuthError(PowerAntApiError):
    """PowerAnt API authentication failed."""


class PowerAntDeviceNotFoundError(PowerAntApiError):
    """PowerAnt device was not found."""


class PowerAntApiClient:
    """Client for the official PowerAnt Share device API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
    ) -> None:
        self._session = session
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        """Return authentication headers."""
        return {
            "X-API-Key": self._api_key,
        }


    async def async_get_device(
        self,
        product_key: str,
    ) -> dict:
        """Get a PowerAnt device including device type metadata."""

        url = (
            f"{API_URL}/api/collections/"
            f"devices/records/{product_key}"
            f"?expand=device_type"
        )

        async with self._session.get(
            url,
            headers=self._headers,
        ) as response:

            if response.status in (401, 403):
                raise PowerAntAuthError(
                    "PowerAnt API authentication failed"
                )

            if response.status == 404:
                raise PowerAntDeviceNotFoundError(
                    f"PowerAnt device not found: {product_key}"
                )

            response.raise_for_status()
            return await response.json()


    async def async_update_device(
        self,
        product_key: str,
        data: dict,
    ) -> dict:
        """Update PowerAnt device settings."""

        url = (
            f"{API_URL}/api/collections/"
            f"devices/records/{product_key}"
        )

        async with self._session.patch(
            url,
            headers=self._headers,
            json=data,
        ) as response:

            if response.status in (401, 403):
                raise PowerAntAuthError(
                    "PowerAnt API authentication failed"
                )

            if response.status == 404:
                raise PowerAntDeviceNotFoundError(
                    f"PowerAnt device not found: {product_key}"
                )

            response.raise_for_status()
            return await response.json()


    async def async_get_prices(
        self,
        country_area: str,
    ) -> dict:
        """Get PowerAnt electricity prices for an area."""

        url = f"{PRICE_BASE_URL}/{country_area}.json"

        async with self._session.get(url) as response:
            response.raise_for_status()
            return await response.json()



