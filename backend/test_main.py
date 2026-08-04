"""
Integration tests for backend/main.py's /assess endpoint — verifies the
Google-Solar-API wiring and the graceful-degradation contract end-to-end.
External calls (get_building_solar_summary) are mocked; no live services
are hit.
"""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

import main
import solar

client = TestClient(main.app)

ASSESS_BODY = {
    "location": "Calgary, Alberta, Canada",
    "lat": 51.05,
    "lon": -114.07,
    "annual_usage_kwh": 9000,
}

AVAILABLE_ROOF_SOLAR = {
    "available": True,
    "reason": None,
    "imagery_quality": "HIGH",
    "imagery_date": "2022-08-01",
    "whole_roof_area_m2": 62.4,
    "max_sunshine_hours_per_year": 1857.9,
    "carbon_offset_factor_kg_per_mwh": 428.9,
    "panels_count": 24,
    "panel_watts_assumed": 440,
    "google_panel_capacity_watts": 400,
    "system_size_kw": 10.56,
    "estimated_annual_production_kwh": 12475.3,
    "comparison": {
        "annual_usage_kwh": 9000,
        "offset_pct": 138.6,
        "surplus_kwh": 3475.3,
        "rate_per_kwh_cad": None,
        "estimated_annual_savings_cad": None,
        "savings_note": None,
    },
    "verdict": "full_coverage",
    "verdict_message": "This roof can cover your entire annual usage, with credit to spare.",
    "target_offset_pct": 100,
    "recommended_meets_target": True,
    "max_roof_capacity": {"panels_count": 24, "system_size_kw": 10.56, "estimated_annual_production_kwh": 12475.3},
    "financials": {
        "estimated_installed_cost_cad": 31680.0,   # 10.56 * 1000 * 3.00
        "cost_per_watt_cad_assumed": 3.00,
        "payback_period_years": None,              # no rate in this fixture -> no savings -> no payback
        "panel_lifespan_years": 25,
        "lifetime_net_savings_cad": None,
        "note": (
            "Rough planning-stage estimate only — excludes any government grants/rebates and "
            "financing costs, and doesn't model panel output degradation or future utility rate "
            "changes over the system's lifetime."
        ),
    },
    "carbon_offset": {
        "carbon_offset_factor_kg_per_mwh": 428.9,
        "annual_co2_offset_kg": 5350.7,             # 12.4753 * 428.9
        "lifetime_co2_offset_tonnes": 133.77,
    },
    "roof_orientation": [
        {"direction": "S", "panels_count": 14, "estimated_annual_production_kwh": 7282.0},
        {"direction": "W", "panels_count": 7, "estimated_annual_production_kwh": 3520.0},
        {"direction": "E", "panels_count": 3, "estimated_annual_production_kwh": 1673.3},
    ],
    "monthly_breakdown": [
        {
            "month": "2026-06", "estimated_production_kwh": 900.0, "estimated_production_value_cad": 135.0,
            "actual_usage_kwh": 900.0, "actual_cost_cad": 150.0,
        },
        {
            "month": "2026-07", "estimated_production_kwh": 600.0, "estimated_production_value_cad": 90.0,
            "actual_usage_kwh": None, "actual_cost_cad": None,
        },
    ],
    "disclaimer": "This is a pre-application estimate only, not an engineered solar proposal.",
}

UNAVAILABLE_ROOF_SOLAR = {
    "available": False,
    "reason": "no_coverage",
    "message": "High-resolution roof imagery isn't available for this address yet.",
}


class TestAssessEndpoint(unittest.TestCase):
    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_happy_path_includes_roof_solar_potential(self, mock_get_solar):
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["location"], ASSESS_BODY["location"])
        self.assertNotIn("solar", data)
        self.assertNotIn("recommendation", data)
        self.assertEqual(data["roof_solar_potential"], AVAILABLE_ROOF_SOLAR)
        self.assertEqual(data["recommended_system_size_kw"], 10.56)
        self.assertEqual(data["system_size_basis"], "roof_matched")

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_degraded_solar_summary_still_returns_200(self, mock_get_solar):
        mock_get_solar.return_value = UNAVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn("solar", data)
        self.assertFalse(data["roof_solar_potential"]["available"])
        self.assertEqual(data["roof_solar_potential"]["reason"], "no_coverage")
        self.assertEqual(data["recommended_system_size_kw"], 5.54)
        self.assertEqual(data["system_size_basis"], "usage_estimate")

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_bill_fields_pass_through_as_rate(self, mock_get_solar):
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        body = {**ASSESS_BODY, "electricity_charge_incl_gst": 150.0, "bill_period_usage_kwh": 900.0}
        response = client.post("/assess", json=body)

        self.assertEqual(response.status_code, 200)
        # get_building_solar_summary(lat, lon, annual_usage_kwh, rate_per_kwh)
        called_args = mock_get_solar.call_args.args
        self.assertAlmostEqual(called_args[3], 150.0 / 900.0, places=4)

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_no_bill_data_passes_none_rate(self, mock_get_solar):
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertEqual(response.status_code, 200)
        called_args = mock_get_solar.call_args.args
        self.assertIsNone(called_args[3])

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_available_roof_solar_has_no_fallback_cost_estimate(self, mock_get_solar):
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertIsNone(response.json()["fallback_cost_estimate_cad"])

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_degraded_solar_summary_includes_fallback_cost_estimate(self, mock_get_solar):
        mock_get_solar.return_value = UNAVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)
        data = response.json()

        # 5.54 kW is the existing fallback-size fixture value for 9000 kWh usage (see test above)
        expected = round(5.54 * 1000 * solar.INSTALLED_COST_PER_WATT_CAD, 2)
        self.assertAlmostEqual(data["fallback_cost_estimate_cad"], expected, places=2)

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_invalid_annual_usage_returns_422_without_calling_solar(self, mock_get_solar):
        body = {**ASSESS_BODY, "annual_usage_kwh": 0}
        response = client.post("/assess", json=body)

        self.assertEqual(response.status_code, 422)
        mock_get_solar.assert_not_called()

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_monthly_usage_history_passes_through_as_dicts(self, mock_get_solar):
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        body = {**ASSESS_BODY, "monthly_usage_history": [{"month": "2026-06", "kwh": 900.0, "cost": 150.0}]}
        response = client.post("/assess", json=body)

        self.assertEqual(response.status_code, 200)
        called_args = mock_get_solar.call_args.args
        self.assertEqual(called_args[4], [{"month": "2026-06", "kwh": 900.0, "cost": 150.0}])

    @patch("main.get_building_solar_summary", new_callable=AsyncMock)
    def test_no_monthly_usage_history_passes_none(self, mock_get_solar):
        mock_get_solar.return_value = AVAILABLE_ROOF_SOLAR

        response = client.post("/assess", json=ASSESS_BODY)

        self.assertEqual(response.status_code, 200)
        called_args = mock_get_solar.call_args.args
        self.assertIsNone(called_args[4])


class TestRoofImageEndpoint(unittest.TestCase):
    @patch("main.fetch_roof_image", new_callable=AsyncMock)
    def test_success_returns_image_bytes(self, mock_fetch):
        mock_fetch.return_value = b"\x89PNG\r\n"

        response = client.get("/roof-image", params={"lat": 51.05, "lon": -114.07})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"\x89PNG\r\n")
        self.assertEqual(response.headers["content-type"], "image/png")

    @patch("main.fetch_roof_image", new_callable=AsyncMock)
    def test_failure_returns_502(self, mock_fetch):
        from roof_image import RoofImageError
        mock_fetch.side_effect = RoofImageError("not configured")

        response = client.get("/roof-image", params={"lat": 51.05, "lon": -114.07})

        self.assertEqual(response.status_code, 502)


class TestExtractBillEndpoint(unittest.TestCase):
    @patch("main.extract_bill_usage")
    def test_success_returns_extracted_data(self, mock_extract):
        mock_extract.return_value = {"provider": "Enmax", "annual_usage_kwh": 9000}

        response = client.post(
            "/extract-bill", files={"file": ("bill.jpg", b"fake-image-bytes", "image/jpeg")}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["provider"], "Enmax")

    @patch("main.extract_bill_usage")
    def test_extraction_failure_returns_422(self, mock_extract):
        from bill_extractor import BillExtractionError
        mock_extract.side_effect = BillExtractionError("could not read bill")

        response = client.post(
            "/extract-bill", files={"file": ("bill.jpg", b"fake-image-bytes", "image/jpeg")}
        )

        self.assertEqual(response.status_code, 422)

    def test_oversized_file_returns_413_without_calling_extractor(self):
        oversized = b"0" * (10 * 1024 * 1024 + 1)

        response = client.post(
            "/extract-bill", files={"file": ("bill.jpg", oversized, "image/jpeg")}
        )

        self.assertEqual(response.status_code, 413)


class TestExtractBillDoesNotBlockEventLoop(unittest.IsolatedAsyncioTestCase):
    async def test_slow_bill_extraction_runs_off_the_event_loop(self):
        """
        extract_bill_usage() is a synchronous, blocking call (real network I/O
        to Claude). Regression test: it must run via asyncio.to_thread so a
        slow extraction can't stall other requests on the event loop.
        Simulated with a real time.sleep() inside the (mocked) extractor — if
        it ran directly on the event loop instead of a worker thread, the
        concurrent /geocode request below would be forced to wait behind it.
        """
        def slow_extract(_image_bytes, _content_type):
            time.sleep(0.3)
            return {"provider": "Enmax", "annual_usage_kwh": 9000}

        async def fast_geocode(_address):
            return {"lat": 51.05, "lon": -114.07, "display_name": "Calgary, AB"}

        with patch("main.extract_bill_usage", new=slow_extract), \
             patch("main.geocode", new=fast_geocode):
            transport = ASGITransport(app=main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                bill_task = asyncio.create_task(
                    ac.post("/extract-bill", files={"file": ("bill.jpg", b"x", "image/jpeg")})
                )
                await asyncio.sleep(0.05)  # let the slow request start first

                geocode_start = time.perf_counter()
                geocode_response = await ac.post("/geocode", json={"address": "123 Main St"})
                geocode_elapsed = time.perf_counter() - geocode_start

                bill_response = await bill_task

        self.assertEqual(bill_response.status_code, 200)
        self.assertEqual(geocode_response.status_code, 200)
        self.assertLess(geocode_elapsed, 0.2)


if __name__ == "__main__":
    unittest.main()
