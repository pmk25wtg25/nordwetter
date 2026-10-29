"""Pure parsing and weather-condition mapping for wttr.in responses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import math
import unicodedata


class WeatherApiError(Exception):
    """Base error for an unavailable or invalid wttr.in response."""


class WeatherDataError(WeatherApiError):
    """Raised when a response does not contain the required weather data."""


VALID_WEATHER_CONDITIONS = frozenset(
    {
        "clear-night",
        "cloudy",
        "exceptional",
        "fog",
        "hail",
        "lightning",
        "lightning-rainy",
        "partlycloudy",
        "pouring",
        "rainy",
        "snowy",
        "snowy-rainy",
        "sunny",
        "windy",
        "windy-variant",
    }
)

PRECIPITATION_PROBABILITY_FIELDS = (
    "chanceofrain",
    "chanceofsnow",
    "chanceofthunder",
)


@dataclass(frozen=True, slots=True)
class CurrentWeather:
    """Current weather values in wttr.in native units."""

    condition: str
    temperature: float
    apparent_temperature: float | None
    humidity: float | None
    pressure: float | None
    precipitation: float | None
    uv_index: float | None
    visibility: float | None
    wind_bearing: float | str | None
    wind_speed: float | None


@dataclass(frozen=True, slots=True)
class WeatherData:
    """Parsed current conditions and daily forecast."""

    location: str
    country: str | None
    current: CurrentWeather
    forecast: list[dict[str, object]]


def map_condition(description: str) -> str:
    """Map a wttr.in description to a Home Assistant weather condition."""
    text = (
        unicodedata.normalize("NFKD", description)
        .encode("ascii", "ignore")
        .decode()
    )
    text = " ".join(text.lower().split())

    if not text:
        return "cloudy"
    if "thunder" in text or "lightning" in text:
        if any(word in text for word in ("rain", "shower", "drizzle")):
            return "lightning-rainy"
        return "lightning"
    if "hail" in text:
        return "hail"
    if any(word in text for word in ("sleet", "ice pellet", "freezing rain")):
        return "snowy-rainy"
    if "snow" in text or "blizzard" in text:
        return "snowy"
    if any(word in text for word in ("fog", "mist", "haze")):
        return "fog"
    if any(
        word in text for word in ("torrential", "downpour", "pouring", "heavy rain")
    ):
        return "pouring"
    if any(word in text for word in ("rain", "drizzle", "shower")):
        return "rainy"
    if any(word in text for word in ("partly", "mostly cloudy", "patchy cloud")):
        return "partlycloudy"
    if any(word in text for word in ("overcast", "cloudy", "cloud")):
        return "cloudy"
    if any(word in text for word in ("gale", "windy", "strong wind")):
        return "windy"
    if "clear" in text and "night" in text:
        return "clear-night"
    if "clear" in text:
        # wttr.in does not provide a day/night flag with every description.
        return "sunny"
    if "sun" in text:
        return "sunny"
    return "cloudy"


def parse_weather_data(payload: object, requested_location: str) -> WeatherData:
    """Parse the fields used by the Nordwetter weather entity."""
    root = _mapping(payload, "response")
    current_items = _sequence(root.get("current_condition"), "current_condition")
    forecast_items = _sequence(root.get("weather"), "weather")
    if not current_items:
        raise WeatherDataError("missing current conditions")
    if not forecast_items:
        raise WeatherDataError("missing daily forecast")

    current = _mapping(current_items[0], "current_condition[0]")
    description = _description(current.get("weatherDesc"))
    temperature = _number(current.get("temp_C"))
    if description is None or temperature is None:
        raise WeatherDataError("missing current temperature or condition")

    area = _first_mapping(root.get("nearest_area"))
    location = _description(area.get("areaName")) if area else None
    country = _description(area.get("country")) if area else None

    wind_bearing = _number(current.get("winddirDegree"))
    if wind_bearing is None:
        wind_bearing = _description(current.get("winddir16Point"))

    current_weather = CurrentWeather(
        condition=map_condition(description),
        temperature=temperature,
        apparent_temperature=_number(current.get("FeelsLikeC")),
        humidity=_number(current.get("humidity")),
        pressure=_number(current.get("pressure")),
        precipitation=_number(current.get("precipMM")),
        uv_index=_number(current.get("uvIndex")),
        visibility=_number(current.get("visibility")),
        wind_bearing=wind_bearing,
        wind_speed=_number(current.get("windspeedKmph")),
    )

    forecast = []
    for item in forecast_items:
        day = _mapping(item, "weather[]")
        day_date = _date(day.get("date"))
        if day_date is None:
            continue

        hourly_items = _sequence_or_empty(day.get("hourly"))
        sample = _mapping(
            hourly_items[len(hourly_items) // 2], "hourly[]"
        ) if hourly_items else {}
        day_description = (
            _description(sample.get("weatherDesc"))
            or _description(day.get("weatherDesc"))
            or description
        )
        entry: dict[str, object] = {
            "datetime": _forecast_datetime(day_date),
            "condition": map_condition(day_description),
        }
        high = _number(day.get("maxtempC"))
        low = _number(day.get("mintempC"))
        precipitation = _number(day.get("totalprecip_mm"))
        uv_index = _number(day.get("uvIndex"))
        chance = _max_precipitation_probability(hourly_items)

        if high is not None:
            entry["native_temperature"] = high
        if low is not None:
            entry["native_templow"] = low
        if precipitation is not None:
            entry["native_precipitation"] = precipitation
        if uv_index is not None:
            entry["uv_index"] = uv_index
        if chance is not None:
            entry["precipitation_probability"] = chance
        forecast.append(entry)

    if not forecast:
        raise WeatherDataError("missing valid forecast days")

    return WeatherData(
        location=location or requested_location,
        country=country,
        current=current_weather,
        forecast=forecast,
    )


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise WeatherDataError(f"{field} is not an object")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise WeatherDataError(f"{field} is not an array")
    return value


def _sequence_or_empty(value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return value


def _first_mapping(value: object) -> Mapping[str, object] | None:
    items = _sequence_or_empty(value)
    if not items or not isinstance(items[0], Mapping):
        return None
    return items[0]


def _description(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        return _description(value.get("value"))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return _description(value[0]) if value else None
    return None


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _forecast_datetime(day: date) -> str:
    """Return a stable RFC-3339 timestamp for a date-only wttr.in forecast."""
    return (
        datetime.combine(day, time(hour=12), tzinfo=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _max_precipitation_probability(items: Sequence[object]) -> int | None:
    """Return the highest probability of any supported precipitation type."""
    chances = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        for field in PRECIPITATION_PROBABILITY_FIELDS:
            chance = _number(item.get(field))
            if chance is not None:
                chances.append(max(0, min(100, round(chance))))
    return max(chances) if chances else None
