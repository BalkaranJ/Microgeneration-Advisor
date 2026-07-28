"""
Unit tests for backend/solar.py — Google Solar API integration. No live API
key is used anywhere here; all HTTP calls are faked/mocked.
"""

import unittest
from unittest.mock import AsyncMock, patch

import solar
from solar import (
    SolarApiNoCoverage,
    SolarApiNotConfigured,
    SolarApiRequestError,
    azimuth_to_compass,
    build_comparison,
    classify_verdict,
    effective_rate_per_kwh,
    fetch_building_insights,
    get_building_solar_summary,
    parse_solar_potential,
    size_to_max_roof_capacity,
    summarize_roof_orientation,
)

MAX_CONFIG_ROOF_SEGMENT_SUMMARIES = [
    {"pitchDegrees": 20, "azimuthDegrees": 180, "panelsCount": 14, "yearlyEnergyDcKwh": 6620.0, "segmentIndex": 0},
    {"pitchDegrees": 20, "azimuthDegrees": 270, "panelsCount": 7, "yearlyEnergyDcKwh": 3200.0, "segmentIndex": 1},
    {"pitchDegrees": 20, "azimuthDegrees": 90, "panelsCount": 3, "yearlyEnergyDcKwh": 1521.2, "segmentIndex": 2},
]

SAMPLE_BUILDING_INSIGHTS = {
    "imageryDate": {"year": 2022, "month": 8, "day": 1},
    "imageryQuality": "HIGH",
    "solarPotential": {
        "maxArrayPanelsCount": 24,
        "maxArrayAreaMeters2": 48.2,
        "maxSunshineHoursPerYear": 1857.9,
        "panelCapacityWatts": 400,
        "carbonOffsetFactorKgPerMwh": 428.9,
        "wholeRoofStats": {"areaMeters2": 62.4},
        "solarPanelConfigs": [
            {"panelsCount": 4, "yearlyEnergyDcKwh": 1890.2},
            {"panelsCount": 10, "yearlyEnergyDcKwh": 4725.5},
            {"panelsCount": 16, "yearlyEnergyDcKwh": 7560.8},
            {"panelsCount": 20, "yearlyEnergyDcKwh": 9451.0},
            {
                "panelsCount": 24,
                "yearlyEnergyDcKwh": 11341.2,
                "roofSegmentSummaries": MAX_CONFIG_ROOF_SEGMENT_SUMMARIES,
            },
        ],
    },
}


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient's `async with ... as client` usage."""

    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


class TestEffectiveRatePerKwh(unittest.TestCase):
    def test_normal_ratio(self):
        self.assertAlmostEqual(effective_rate_per_kwh(150.0, 900.0), 0.1667, places=4)

    def test_none_when_charge_missing(self):
        self.assertIsNone(effective_rate_per_kwh(None, 900.0))

    def test_none_when_usage_missing(self):
        self.assertIsNone(effective_rate_per_kwh(150.0, None))

    def test_none_when_usage_zero(self):
        self.assertIsNone(effective_rate_per_kwh(150.0, 0))

    def test_none_when_usage_negative(self):
        self.assertIsNone(effective_rate_per_kwh(150.0, -10))


class TestParseSolarPotential(unittest.TestCase):
    def test_extracts_known_fields(self):
        parsed = parse_solar_potential(SAMPLE_BUILDING_INSIGHTS)
        self.assertEqual(parsed["imagery_quality"], "HIGH")
        self.assertEqual(parsed["imagery_date"], "2022-08-01")
        self.assertEqual(parsed["max_array_panels_count"], 24)
        self.assertEqual(parsed["panel_capacity_watts"], 400)
        self.assertEqual(parsed["whole_roof_area_m2"], 62.4)
        self.assertEqual(len(parsed["solar_panel_configs"]), 5)

    def test_empty_dict_does_not_raise(self):
        parsed = parse_solar_potential({})
        self.assertIsNone(parsed["max_array_panels_count"])
        self.assertEqual(parsed["solar_panel_configs"], [])

    def test_missing_solar_potential_does_not_raise(self):
        parsed = parse_solar_potential({"imageryQuality": "MEDIUM"})
        self.assertIsNone(parsed["panel_capacity_watts"])

    def test_malformed_imagery_date_returns_none(self):
        parsed = parse_solar_potential({"imageryDate": {"year": 2022}})
        self.assertIsNone(parsed["imagery_date"])


class TestSizeToMaxRoofCapacity(unittest.TestCase):
    def setUp(self):
        self.parsed = parse_solar_potential(SAMPLE_BUILDING_INSIGHTS)

    def test_sizes_to_largest_config_panel_count(self):
        sized = size_to_max_roof_capacity(self.parsed)
        self.assertEqual(sized["panels_count"], 24)

    def test_system_size_uses_leading_panel_watts_not_google_wattage(self):
        sized = size_to_max_roof_capacity(self.parsed, leading_panel_watts=440)
        # 24 panels * 440W / 1000, NOT Google's own 400W (24*400/1000 = 9.6)
        self.assertEqual(sized["system_size_kw"], 10.56)
        self.assertNotEqual(sized["system_size_kw"], 9.6)

    def test_production_scaled_by_wattage_ratio(self):
        sized = size_to_max_roof_capacity(self.parsed, leading_panel_watts=440)
        # 11341.2 * (440/400) = 12475.32 -> rounds to 12475.3
        self.assertEqual(sized["estimated_annual_production_kwh"], 12475.3)

    def test_custom_leading_panel_watts_param(self):
        sized = size_to_max_roof_capacity(self.parsed, leading_panel_watts=350)
        self.assertEqual(sized["system_size_kw"], round(24 * 350 / 1000, 2))
        self.assertEqual(sized["estimated_annual_production_kwh"], round(11341.2 * 350 / 400, 1))

    def test_none_when_no_configs(self):
        parsed = parse_solar_potential({"solarPotential": {"panelCapacityWatts": 400}})
        self.assertIsNone(size_to_max_roof_capacity(parsed))

    def test_none_when_no_panel_capacity(self):
        parsed = parse_solar_potential({
            "solarPotential": {"solarPanelConfigs": [{"panelsCount": 4, "yearlyEnergyDcKwh": 100}]}
        })
        self.assertIsNone(size_to_max_roof_capacity(parsed))

    def test_includes_max_configs_roof_segment_summaries(self):
        sized = size_to_max_roof_capacity(self.parsed)
        self.assertEqual(sized["roof_segment_summaries"], MAX_CONFIG_ROOF_SEGMENT_SUMMARIES)

    def test_roof_segment_summaries_empty_when_absent(self):
        parsed = parse_solar_potential({
            "solarPotential": {
                "panelCapacityWatts": 400,
                "solarPanelConfigs": [{"panelsCount": 4, "yearlyEnergyDcKwh": 100}],
            }
        })
        sized = size_to_max_roof_capacity(parsed)
        self.assertEqual(sized["roof_segment_summaries"], [])


class TestAzimuthToCompass(unittest.TestCase):
    def test_north(self):
        self.assertEqual(azimuth_to_compass(0), "N")

    def test_east(self):
        self.assertEqual(azimuth_to_compass(90), "E")

    def test_south(self):
        self.assertEqual(azimuth_to_compass(180), "S")

    def test_west(self):
        self.assertEqual(azimuth_to_compass(270), "W")

    def test_northeast(self):
        self.assertEqual(azimuth_to_compass(46), "NE")

    def test_wraps_around_to_north(self):
        self.assertEqual(azimuth_to_compass(360), "N")

    def test_northwest(self):
        self.assertEqual(azimuth_to_compass(320), "NW")

    def test_just_below_360_wraps_to_north(self):
        self.assertEqual(azimuth_to_compass(350), "N")


class TestSummarizeRoofOrientation(unittest.TestCase):
    def test_groups_and_scales_by_direction(self):
        result = summarize_roof_orientation(MAX_CONFIG_ROOF_SEGMENT_SUMMARIES, wattage_ratio=1.1)
        by_direction = {r["direction"]: r for r in result}

        self.assertEqual(by_direction["S"]["panels_count"], 14)
        self.assertEqual(by_direction["S"]["estimated_annual_production_kwh"], 7282.0)
        self.assertEqual(by_direction["W"]["panels_count"], 7)
        self.assertEqual(by_direction["W"]["estimated_annual_production_kwh"], 3520.0)
        self.assertEqual(by_direction["E"]["panels_count"], 3)
        self.assertEqual(by_direction["E"]["estimated_annual_production_kwh"], 1673.3)

    def test_sorted_by_panels_count_descending(self):
        result = summarize_roof_orientation(MAX_CONFIG_ROOF_SEGMENT_SUMMARIES, wattage_ratio=1.0)
        self.assertEqual([r["direction"] for r in result], ["S", "W", "E"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(summarize_roof_orientation([], wattage_ratio=1.1), [])

    def test_skips_segments_missing_panels_or_azimuth(self):
        segments = [{"azimuthDegrees": 180, "yearlyEnergyDcKwh": 100}, {"panelsCount": 5, "yearlyEnergyDcKwh": 100}]
        self.assertEqual(summarize_roof_orientation(segments, wattage_ratio=1.0), [])


class TestClassifyVerdict(unittest.TestCase):
    def test_full_coverage_at_boundary(self):
        self.assertEqual(classify_verdict(100)["verdict"], "full_coverage")

    def test_full_coverage_above_boundary(self):
        self.assertEqual(classify_verdict(150.5)["verdict"], "full_coverage")

    def test_partial_coverage_at_boundary(self):
        self.assertEqual(classify_verdict(25)["verdict"], "partial_coverage")

    def test_partial_coverage_just_below_full(self):
        self.assertEqual(classify_verdict(99.9)["verdict"], "partial_coverage")

    def test_too_small_just_below_partial_boundary(self):
        self.assertEqual(classify_verdict(24.9)["verdict"], "too_small")

    def test_too_small_at_zero(self):
        self.assertEqual(classify_verdict(0)["verdict"], "too_small")

    def test_unknown_when_offset_none(self):
        self.assertEqual(classify_verdict(None)["verdict"], "unknown")


class TestBuildComparison(unittest.TestCase):
    def test_offset_over_100_with_savings(self):
        result = build_comparison(9451.0, 9000, rate_per_kwh=0.15)
        self.assertGreater(result["offset_pct"], 100)
        self.assertEqual(result["surplus_kwh"], 451.0)
        # self-consumed = min(9451, 9000) = 9000 -> 9000 * 0.15 = 1350.0
        self.assertEqual(result["estimated_annual_savings_cad"], 1350.0)
        self.assertIsNotNone(result["savings_note"])

    def test_deficit_case(self):
        result = build_comparison(4725.5, 9000, rate_per_kwh=0.15)
        self.assertLess(result["offset_pct"], 100)
        self.assertLess(result["surplus_kwh"], 0)

    def test_no_rate_means_no_savings(self):
        result = build_comparison(9451.0, 9000, rate_per_kwh=None)
        self.assertIsNone(result["estimated_annual_savings_cad"])
        self.assertIsNone(result["savings_note"])


class TestFetchBuildingInsights(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_raises_not_configured_without_http_call(self):
        with patch.object(solar.os, "getenv", return_value=None), \
             patch.object(solar.httpx, "AsyncClient") as mock_client_cls:
            with self.assertRaises(SolarApiNotConfigured):
                await fetch_building_insights(51.05, -114.07, api_key=None)
            mock_client_cls.assert_not_called()

    async def test_200_returns_json(self):
        fake_response = _FakeResponse(200, SAMPLE_BUILDING_INSIGHTS)
        with patch.object(solar.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            data = await fetch_building_insights(51.05, -114.07, api_key="test-key")
        self.assertEqual(data, SAMPLE_BUILDING_INSIGHTS)

    async def test_404_raises_no_coverage(self):
        fake_response = _FakeResponse(404, {})
        with patch.object(solar.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            with self.assertRaises(SolarApiNoCoverage):
                await fetch_building_insights(51.05, -114.07, api_key="test-key")

    async def test_403_raises_request_error(self):
        fake_response = _FakeResponse(403, {})
        with patch.object(solar.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            with self.assertRaises(SolarApiRequestError):
                await fetch_building_insights(51.05, -114.07, api_key="test-key")

    async def test_network_error_raises_request_error(self):
        fake_client = _FakeAsyncClient(exc=solar.httpx.ConnectTimeout("timed out"))
        with patch.object(solar.httpx, "AsyncClient", lambda *a, **kw: fake_client):
            with self.assertRaises(SolarApiRequestError):
                await fetch_building_insights(51.05, -114.07, api_key="test-key")


FAKE_DAILY_IRRADIANCE = {
    "20260601": 4.0,
    "20260602": 4.0,
    "20260701": 6.0,
}


class TestGetBuildingSolarSummary(unittest.IsolatedAsyncioTestCase):
    async def test_success_path(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, annual_usage_kwh=9000, rate_per_kwh=0.15)
        self.assertTrue(summary["available"])
        self.assertEqual(summary["panels_count"], 24)
        self.assertEqual(summary["system_size_kw"], 10.56)
        self.assertEqual(summary["estimated_annual_production_kwh"], 12475.3)
        self.assertIn(summary["verdict"], {"full_coverage", "partial_coverage", "too_small"})
        self.assertNotIn("assumptions", summary)
        self.assertIsNotNone(summary["disclaimer"])
        self.assertIsNotNone(summary["comparison"]["estimated_annual_savings_cad"])

    async def test_roof_orientation_grouped_from_max_config(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        directions = {r["direction"] for r in summary["roof_orientation"]}
        self.assertEqual(directions, {"S", "W", "E"})

    async def test_monthly_breakdown_distributed_by_real_irradiance(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        months = [m["month"] for m in summary["monthly_breakdown"]]
        self.assertEqual(months, ["2026-06", "2026-07"])
        total = sum(m["estimated_production_kwh"] for m in summary["monthly_breakdown"])
        self.assertAlmostEqual(total, summary["estimated_annual_production_kwh"], delta=0.5)

    async def test_monthly_breakdown_joins_bill_usage_history_by_month(self):
        usage_history = [{"month": "2026-06", "kwh": 900.0, "cost": 150.0}]
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(
                51.05, -114.07, 9000, monthly_usage_history=usage_history
            )
        by_month = {m["month"]: m for m in summary["monthly_breakdown"]}
        self.assertEqual(by_month["2026-06"]["actual_usage_kwh"], 900.0)
        self.assertEqual(by_month["2026-06"]["actual_cost_cad"], 150.0)
        self.assertIsNone(by_month["2026-07"]["actual_usage_kwh"])

    async def test_monthly_breakdown_includes_production_value_when_rate_known(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000, rate_per_kwh=0.15)
        by_month = {m["month"]: m for m in summary["monthly_breakdown"]}
        june = by_month["2026-06"]
        self.assertEqual(june["estimated_production_value_cad"], round(june["estimated_production_kwh"] * 0.15, 2))

    async def test_monthly_breakdown_production_value_none_without_rate(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertTrue(all(m["estimated_production_value_cad"] is None for m in summary["monthly_breakdown"]))

    async def test_monthly_breakdown_empty_when_irradiance_fetch_fails(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(side_effect=RuntimeError("boom"))):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertTrue(summary["available"])
        self.assertEqual(summary["monthly_breakdown"], [])

    async def test_no_coverage_degrades_gracefully(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=SolarApiNoCoverage("nope"))):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "no_coverage")

    async def test_not_configured_degrades_gracefully(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=SolarApiNotConfigured("no key"))):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "not_configured")

    async def test_request_error_collapses_to_error(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=SolarApiRequestError("bad key"))):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "error")

    async def test_unexpected_exception_collapses_to_error(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=RuntimeError("boom"))):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "error")

    async def test_no_panel_data_when_configs_missing(self):
        malformed = {"solarPotential": {}}
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=malformed)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "no_panel_data")


if __name__ == "__main__":
    unittest.main()
