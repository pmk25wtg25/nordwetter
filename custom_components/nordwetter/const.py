"""Constants and input validation for Nordwetter."""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import quote

DOMAIN = "nordwetter"
CONF_LOCATION = "location"
API_URL = "https://wttr.in/{location}?format=j1"
API_TIMEOUT = 15
UPDATE_INTERVAL = timedelta(hours=1)
MAX_LOCATION_LENGTH = 200


def normalize_location(value: object) -> str:
    """Validate and normalize a location entered by a user."""
    if not isinstance(value, str):
        raise ValueError("invalid_location")

    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("invalid_location")

    location = " ".join(value.strip().split())
    if not location:
        raise ValueError("empty_location")
    if len(location) > MAX_LOCATION_LENGTH:
        raise ValueError("location_too_long")
    return location


def validate_location(value: object) -> str | None:
    """Return a config-flow error key, or None for a valid location."""
    try:
        normalize_location(value)
    except ValueError as error:
        return str(error)
    return None


def build_endpoint(location: str) -> str:
    """Build the wttr.in JSON endpoint without allowing URL parameters."""
    return API_URL.format(location=quote(normalize_location(location), safe=""))
