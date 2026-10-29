"""Tests for Nordwetter's dependency-free parsing and validation logic."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
import unittest

COMPONENT_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(COMPONENT_DIR))

from api import (  # noqa: E402
    VALID_WEATHER_CONDITIONS,
    WeatherDataError,
    map_condition,
    parse_weather_data,
)
from const import build_endpoint, validate_location  # noqa: E402


class SetupContractTests(unittest.TestCase):
    """Check the setup return contract without importing Home Assistant."""

    @staticmethod
    def _function(tree: ast.Module, name: str) -> ast.AsyncFunctionDef:
        return next(
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == name
        )

    @staticmethod
    def _assert_bool_annotation(test: unittest.TestCase, function: ast.AsyncFunctionDef) -> None:
        test.assertIsInstance(function.returns, ast.Name)
        test.assertEqual(function.returns.id, "bool")

    def test_setup_paths_return_success_booleans(self) -> None:
        tree = ast.parse(
            (COMPONENT_DIR / "__init__.py").read_text(encoding="utf-8")
        )
        setup = self._function(tree, "async_setup")
        setup_entry = self._function(tree, "async_setup_entry")
        unload_entry = self._function(tree, "async_unload_entry")

        for function in (setup, setup_entry):
            self._assert_bool_annotation(self, function)
            self.assertTrue(
                any(
                    isinstance(node, ast.Return)
                    and isinstance(node.value, ast.Constant)
                    and node.value.value is True
                    for node in function.body
                )
            )

        self._assert_bool_annotation(self, unload_entry)
        self.assertIsInstance(unload_entry.body[-1], ast.Return)


def sample_payload() -> dict:
    """Return a representative wttr.in j1 response."""
    return {
        "current_condition": [
            {
                "temp_C": "12",
                "FeelsLikeC": "10",
                "weatherDesc": [{"value": "Light rain shower"}],
                "windspeedKmph": "18",
                "winddirDegree": "240",
                "humidity": "76",
                "visibility": "10",
                "pressure": "1012",
                "precipMM": "0.4",
                "uvIndex": "2",
            }
        ],
        "nearest_area": [
            {
                "areaName": [{"value": "Berlin"}],
                "country": [{"value": "Germany"}],
            }
        ],
        "weather": [
            {
                "date": "2026-10-29",
                "maxtempC": "14",
                "mintempC": "8",
                "totalprecip_mm": "2.1",
                "uvIndex": "2",
                "hourly": [
                    {
                        "weatherDesc": [{"value": "Cloudy"}],
                        "chanceofrain": "30",
                        "chanceofsnow": "95",
                    },
                    {
                        "weatherDesc": [{"value": "Moderate rain"}],
                        "chanceofrain": "80",
                        "chanceofthunder": "2",
                    },
                ],
            }
        ],
    }


class ConditionMappingTests(unittest.TestCase):
    """Test valid Home Assistant condition mapping."""

    def test_common_conditions(self) -> None:
        cases = {
            "Sunny": "sunny",
            "Clear": "sunny",
            "Clear night": "clear-night",
            "Partly cloudy": "partlycloudy",
            "Overcast": "cloudy",
            "Light rain shower": "rainy",
            "Torrential rain": "pouring",
            "Thundery outbreaks with rain": "lightning-rainy",
            "Light sleet showers": "snowy-rainy",
            "Freezing fog": "fog",
            "Heavy snow": "snowy",
        }
        for description, expected in cases.items():
            with self.subTest(description=description):
                self.assertEqual(map_condition(description), expected)
                self.assertIn(map_condition(description), VALID_WEATHER_CONDITIONS)

        self.assertIn(
            map_condition("unrecognized weather text"), VALID_WEATHER_CONDITIONS
        )


class ParserTests(unittest.TestCase):
    """Test response parsing and malformed response handling."""

    def test_parses_current_and_daily_forecast(self) -> None:
        result = parse_weather_data(sample_payload(), "Berlin")

        self.assertEqual(result.location, "Berlin")
        self.assertEqual(result.current.condition, "rainy")
        self.assertEqual(result.current.temperature, 12.0)
        self.assertEqual(result.current.precipitation, 0.4)
        self.assertEqual(result.current.wind_bearing, 240.0)
        self.assertEqual(result.forecast[0]["condition"], "rainy")
        self.assertEqual(result.forecast[0]["native_temperature"], 14.0)
        self.assertEqual(result.forecast[0]["native_templow"], 8.0)
        self.assertEqual(result.forecast[0]["precipitation_probability"], 95)
        self.assertEqual(result.forecast[0]["datetime"], "2026-10-29T12:00:00Z")

    def test_ignores_missing_and_invalid_precipitation_probabilities(self) -> None:
        payload = sample_payload()
        hourly = payload["weather"][0]["hourly"]
        for item in hourly:
            item.pop("chanceofrain", None)
            item.pop("chanceofsnow", None)
            item.pop("chanceofthunder", None)
        result = parse_weather_data(payload, "Berlin")
        self.assertNotIn("precipitation_probability", result.forecast[0])

        payload = sample_payload()
        payload["weather"][0]["hourly"][0].update(
            {
                "chanceofrain": "-20",
                "chanceofsnow": "not available",
                "chanceofthunder": "125",
            }
        )
        result = parse_weather_data(payload, "Berlin")
        self.assertEqual(result.forecast[0]["precipitation_probability"], 100)

    def test_rejects_missing_required_data(self) -> None:
        with self.assertRaises(WeatherDataError):
            parse_weather_data({}, "Berlin")

        payload = sample_payload()
        payload["current_condition"][0].pop("temp_C")
        with self.assertRaises(WeatherDataError):
            parse_weather_data(payload, "Berlin")

    def test_keeps_valid_response_when_optional_values_are_invalid(self) -> None:
        payload = sample_payload()
        payload["current_condition"][0]["humidity"] = "not-a-number"
        result = parse_weather_data(payload, "Berlin")
        self.assertIsNone(result.current.humidity)


class ValidationTests(unittest.TestCase):
    """Test location validation and URL construction."""

    def test_location_validation(self) -> None:
        self.assertIsNone(validate_location(" München "))
        self.assertEqual(validate_location("  "), "empty_location")
        self.assertEqual(validate_location("Berlin\n"), "invalid_location")
        self.assertEqual(validate_location("x" * 201), "location_too_long")

    def test_location_is_encoded_as_a_path_segment(self) -> None:
        endpoint = build_endpoint("München/Hauptbahnhof")
        self.assertEqual(
            endpoint,
            "https://wttr.in/M%C3%BCnchen%2FHauptbahnhof?format=j1",
        )


if __name__ == "__main__":
    unittest.main()
