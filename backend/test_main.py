"""
Integration tests for backend/main.py's /assess endpoint — verifies the
weather + Google-Solar-API wiring (asyncio.gather) and the graceful-
degradation contract end-to-end. External calls (geocode, fetch_weather,
get_building_solar_summary) are mocked; no live services are hit.
"""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import main
from advisor import WeatherProfile

client = TestClient(main.app)

FAKE_GEO = {"lat": 51.05, "lon": -114.07, "display_name": "Calgary, Alberta, Canada"}
FAKE_WEATHER = WeatherProfile(location=FAKE_GEO["display_name"], solar_indicator=78, cloud_cover=30)

ASSESS_BODY = {
    "address": "123 Main St, Calgary, AB",
    "annual_usage_kwh": 9000,
    "system_size_kw": 8.0,
    "customer_type": "Residential",
}

AVAILABLE_ROOF_SOLAR = {
    "available": True,
    "reason": None,
    "imagery_quality": "HIGH",
    "imagery_date": "2022-08-01",
    "max_array_panels_count": 24,
    "max_array_area_m2": 48.2,
    "max_sunshine_hours_per_year": 1857.9,
    "whole_roof_area_m2": 62.4,
    "carbon_offset_factor_kg_per_mwh": 428.9,
    "matched_config": {
        "requested_system_size_kw": 8.0,
        "panel_capacity_watts": 400,
        "panels_count": 20,
        "matched_system_size_kw": 8.0,
        "estimated_annual_production_kwh": 9451.0,
        "roof_capacity_exceeded": False,
    },
    "comparison": {
        "annual_usage_kwh": 9000,
        "offset_pct": 105.0,
        "surplus_kwh": 451.0,
        "rate_per_kwh_cad": None,
        "estimated_annual_savings_cad": None,
        "savings_note": None,
    },
}

UNAVAILABLE_ROOF_SOLAR = {
    "available": False,
    "reason": "no_coverage",
    "message": "High-resolution roof imagery isn't available for this address yet.",
}


class TestAssessEndpoint(unittest.TestCase):
    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    @patch("main.fetch_weather", new_callable=AsyncMock)
    @patch("main.geocode", new_callable=AsyncMock)
    def test_happy_path_includes_roof_solar_potential(self, mock_geocode, mock_fetch_weather, mock_get_solar):
        mock_geocode.return_value = FAKE_GEO
        mock_fetch_weather.return_value = FAKE_WEATHER
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["location"], FAKE_GEO["display_name"])
        self.assertIn("solar", data)  # existing weather-based score untouched
        self.assertEqual(data["roof_solar_potential"], AVAILABLE_ROOF_SOLAR)

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    @patch("main.fetch_weather", new_callable=AsyncMock)
    @patch("main.geocode", new_callable=AsyncMock)
    def test_degraded_solar_summary_still_returns_200(self, mock_geocode, mock_fetch_weather, mock_get_solar):
        mock_geocode.return_value = FAKE_GEO
        mock_fetch_weather.return_value = FAKE_WEATHER
        mock_get_solar.return_value = UNAVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Existing weather-based results are intact even though Google Solar has no data
        self.assertIn("solar", data)
        self.assertEqual(data["solar"]["rating"], "Strong")
        self.assertFalse(data["roof_solar_potential"]["available"])
        self.assertEqual(data["roof_solar_potential"]["reason"], "no_coverage")

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    @patch("main.fetch_weather", new_callable=AsyncMock)
    @patch("main.geocode", new_callable=AsyncMock)
    def test_bill_fields_pass_through_as_rate(self, mock_geocode, mock_fetch_weather, mock_get_solar):
        mock_geocode.return_value = FAKE_GEO
        mock_fetch_weather.return_value = FAKE_WEATHER
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        body = {**ASSESS_BODY, "electricity_charge_incl_gst": 150.0, "bill_period_usage_kwh": 900.0}
        response = client.post("/assess", json=body)

        self.assertEqual(response.status_code, 200)
        # get_building_solar_summary(lat, lon, system_size_kw, annual_usage_kwh, rate_per_kwh)
        called_args = mock_get_solar.call_args.args
        self.assertAlmostEqual(called_args[4], 150.0 / 900.0, places=4)

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    @patch("main.fetch_weather", new_callable=AsyncMock)
    @patch("main.geocode", new_callable=AsyncMock)
    def test_no_bill_data_passes_none_rate(self, mock_geocode, mock_fetch_weather, mock_get_solar):
        mock_geocode.return_value = FAKE_GEO
        mock_fetch_weather.return_value = FAKE_WEATHER
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertEqual(response.status_code, 200)
        called_args = mock_get_solar.call_args.args
        self.assertIsNone(called_args[4])

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    @patch("main.fetch_weather", new_callable=AsyncMock)
    @patch("main.geocode", new_callable=AsyncMock)
    def test_invalid_system_size_returns_422_without_calling_weather_or_solar(
        self, mock_geocode, mock_fetch_weather, mock_get_solar
    ):
        mock_geocode.return_value = FAKE_GEO

        body = {**ASSESS_BODY, "system_size_kw": 0}
        response = client.post("/assess", json=body)

        self.assertEqual(response.status_code, 422)
        mock_fetch_weather.assert_not_called()
        mock_get_solar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
