"""Config flow for the Nordwetter integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import TextSelector

from .api import WeatherApiError, WeatherDataError
from .const import CONF_LOCATION, DOMAIN, normalize_location
from .coordinator import async_fetch_weather

_LOGGER = logging.getLogger(__name__)


class NordwetterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle configuration of Nordwetter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user configuration step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                location = normalize_location(user_input.get(CONF_LOCATION))
            except ValueError as error:
                errors["location"] = str(error)
            else:
                await self.async_set_unique_id(location.casefold())
                self._abort_if_unique_id_configured()
                try:
                    await async_fetch_weather(self.hass, location)
                except WeatherDataError:
                    errors["base"] = "invalid_response"
                except WeatherApiError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error validating Nordwetter location")
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title=location,
                        data={CONF_LOCATION: location},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_LOCATION): TextSelector()}
            ),
            errors=errors,
        )
