"""Home Assistant weather entity for Nordwetter."""

from __future__ import annotations

from typing import cast

from homeassistant.components.weather import (
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import WeatherData
from .const import DOMAIN
from .coordinator import NordwetterCoordinator


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry[NordwetterCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nordwetter weather entity."""
    coordinator: NordwetterCoordinator = entry.runtime_data
    async_add_entities([NordwetterWeatherEntity(coordinator, entry.entry_id)])


class NordwetterWeatherEntity(SingleCoordinatorWeatherEntity):
    """Expose wttr.in current conditions and daily forecasts."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_attribution = "Daten von wttr.in"

    def __init__(self, coordinator: NordwetterCoordinator, entry_id: str) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"Nordwetter {coordinator.location}",
            manufacturer="wttr.in",
            model="Public weather service",
        )

    @property
    def _weather(self) -> WeatherData | None:
        return self.coordinator.data

    @property
    def condition(self) -> str | None:
        return self._weather.current.condition if self._weather else None

    @property
    def native_temperature(self) -> float | None:
        return self._weather.current.temperature if self._weather else None

    @property
    def native_apparent_temperature(self) -> float | None:
        return (
            self._weather.current.apparent_temperature if self._weather else None
        )

    @property
    def humidity(self) -> float | None:
        return self._weather.current.humidity if self._weather else None

    @property
    def native_pressure(self) -> float | None:
        return self._weather.current.pressure if self._weather else None

    @property
    def native_visibility(self) -> float | None:
        return self._weather.current.visibility if self._weather else None

    @property
    def native_wind_speed(self) -> float | None:
        return self._weather.current.wind_speed if self._weather else None

    @property
    def wind_bearing(self) -> float | str | None:
        return self._weather.current.wind_bearing if self._weather else None

    @property
    def uv_index(self) -> float | None:
        return self._weather.current.uv_index if self._weather else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose current precipitation absent from WeatherEntity's standard fields."""
        attributes = dict(super().extra_state_attributes or {})
        if self._weather and self._weather.current.precipitation is not None:
            attributes["current_precipitation"] = self._weather.current.precipitation
            attributes["current_precipitation_unit"] = (
                UnitOfPrecipitationDepth.MILLIMETERS
            )
        return attributes

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the cached daily forecast in native units."""
        if not self._weather:
            return None
        return cast(list[Forecast], self._weather.forecast)
