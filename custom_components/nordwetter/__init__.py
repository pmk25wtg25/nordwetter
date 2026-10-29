"""Nordwetter Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import NordwetterCoordinator

PLATFORMS: list[Platform] = [Platform.WEATHER]


async def async_setup(_hass: HomeAssistant, _config: dict) -> bool:
    """Set up Nordwetter from the configuration entry flow."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nordwetter from a config entry."""
    coordinator = NordwetterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Nordwetter config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
