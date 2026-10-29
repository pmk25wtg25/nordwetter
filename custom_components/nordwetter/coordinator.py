"""Data update coordinator and wttr.in client for Nordwetter."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WeatherApiError, WeatherData, parse_weather_data
from .const import API_TIMEOUT, UPDATE_INTERVAL, build_endpoint

_LOGGER = logging.getLogger(__name__)


async def async_fetch_weather(hass: HomeAssistant, location: str) -> WeatherData:
    """Fetch and validate one wttr.in response."""
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(API_TIMEOUT):
            async with session.get(
                build_endpoint(location),
                headers={"Accept": "application/json"},
            ) as response:
                if response.status >= 400:
                    raise WeatherApiError(f"wttr.in returned HTTP {response.status}")
                payload = await response.json(content_type=None)
    except WeatherApiError:
        raise
    except (TimeoutError, aiohttp.ClientError, ValueError, UnicodeError) as error:
        raise WeatherApiError("unable to fetch or decode wttr.in response") from error

    return parse_weather_data(payload, location)


class NordwetterCoordinator(DataUpdateCoordinator[WeatherData]):
    """Coordinate one location's current weather and daily forecast."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.location = entry.data["location"]
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"Nordwetter {self.location}",
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> WeatherData:
        """Fetch the configured location."""
        try:
            return await async_fetch_weather(self.hass, self.location)
        except WeatherApiError as error:
            raise UpdateFailed(str(error)) from error
