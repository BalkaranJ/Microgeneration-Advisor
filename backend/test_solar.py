"""
Unit tests for backend/solar.py — Google Solar API integration. No live API
key is used anywhere here; all HTTP calls are faked/mocked.
"""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

import solar
from solar import (
    SolarApiNoCoverage,
    SolarApiNotConfigured,
    SolarApiRequestError,
    azimuth_to_compass,
    build_carbon_offset,
    build_comparison,
    build_financials,
    classify_verdict,
    effective_rate_per_kwh,
    estimate_installed_cost_cad,
    fetch_building_insights,
    get_building_solar_summary,
    parse_solar_potential,
    size_to_max_roof_capacity,
    size_to_recommended_system,
    summarize_roof_orientation,
)

MID_CONFIG_ROOF_SEGMENT_SUMMARIES = [   # sums to the 16-panel config exactly
    {"pitchDegrees": 20, "azimuthDegrees": 180, "panelsCount": 14, "yearlyEnergyDcKwh": 6620.0, "segmentIndex": 0},
    {"pitchDegrees": 20, "azimuthDegrees": 270, "panelsCount": 2, "yearlyEnergyDcKwh": 940.8, "segmentIndex": 1},
]
LARGE_CONFIG_ROOF_SEGMENT_SUMMARIES = [  # sums to the 20-panel config exactly
    {"pitchDegrees": 20, "azimuthDegrees": 180, "panelsCount": 14, "yearlyEnergyDcKwh": 6620.0, "segmentIndex": 0},
    {"pitchDegrees": 20, "azimuthDegrees": 270, "panelsCount": 6, "yearlyEnergyDcKwh": 2831.0, "segmentIndex": 1},
]
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
            {
                "panelsCount": 16,
                "yearlyEnergyDcKwh": 7560.8,
                "roofSegmentSummaries": MID_CONFIG_ROOF_SEGMENT_SUMMARIES,
            },
            {
                "panelsCount": 20,
                "yearlyEnergyDcKwh": 9451.0,
                "roofSegmentSummaries": LARGE_CONFIG_ROOF_SEGMENT_SUMMARIES,
            },
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


class TestSizeToRecommendedSystem(unittest.TestCase):
    def setUp(self):
        self.parsed = parse_solar_potential(SAMPLE_BUILDING_INSIGHTS)

    def test_picks_smallest_config_meeting_target_offset(self):
        # usage 9000, target 100% -> 16-panel (8316.9 kWh) falls short, 20-panel (10396.1) clears it
        sized = size_to_recommended_system(self.parsed, annual_usage_kwh=9000)
        self.assertEqual(sized["panels_count"], 20)
        self.assertEqual(sized["system_size_kw"], round(20 * 440 / 1000, 2))
        self.assertEqual(sized["estimated_annual_production_kwh"], round(9451.0 * 440 / 400, 1))
        self.assertTrue(sized["target_met"])

    def test_falls_back_to_max_config_when_target_unreachable(self):
        sized = size_to_recommended_system(self.parsed, annual_usage_kwh=100_000)
        self.assertEqual(sized["panels_count"], 24)
        self.assertFalse(sized["target_met"])

    def test_custom_target_offset_pct_picks_smaller_config(self):
        # 50% of 9000 = 4500 -> 4-panel falls short, 10-panel (5198.05) clears it
        sized = size_to_recommended_system(self.parsed, annual_usage_kwh=9000, target_offset_pct=50)
        self.assertEqual(sized["panels_count"], 10)

    def test_handles_unsorted_configs_defensively(self):
        parsed = {
            "panel_capacity_watts": 400,
            "solar_panel_configs": [
                {"panelsCount": 20, "yearlyEnergyDcKwh": 9451.0},
                {"panelsCount": 4, "yearlyEnergyDcKwh": 1890.2},
                {"panelsCount": 16, "yearlyEnergyDcKwh": 7560.8},
                {"panelsCount": 10, "yearlyEnergyDcKwh": 4725.5},
                {"panelsCount": 24, "yearlyEnergyDcKwh": 11341.2},
            ],
        }
        sized = size_to_recommended_system(parsed, annual_usage_kwh=9000)
        self.assertEqual(sized["panels_count"], 20)

    def test_roof_segment_summaries_from_chosen_config_not_max(self):
        sized = size_to_recommended_system(self.parsed, annual_usage_kwh=9000)
        self.assertEqual(sized["roof_segment_summaries"], LARGE_CONFIG_ROOF_SEGMENT_SUMMARIES)

    def test_none_when_no_configs(self):
        parsed = parse_solar_potential({"solarPotential": {"panelCapacityWatts": 400}})
        self.assertIsNone(size_to_recommended_system(parsed, annual_usage_kwh=9000))

    def test_none_when_no_panel_capacity(self):
        parsed = parse_solar_potential({
            "solarPotential": {"solarPanelConfigs": [{"panelsCount": 4, "yearlyEnergyDcKwh": 100}]}
        })
        self.assertIsNone(size_to_recommended_system(parsed, annual_usage_kwh=9000))

    def test_zero_usage_picks_smallest_config(self):
        sized = size_to_recommended_system(self.parsed, annual_usage_kwh=0)
        self.assertEqual(sized["panels_count"], 4)
        self.assertTrue(sized["target_met"])


class TestBuildFinancials(unittest.TestCase):
    def test_computes_installed_cost_from_system_size(self):
        result = build_financials(8.8, estimated_annual_savings_cad=1350.0)
        self.assertEqual(result["estimated_installed_cost_cad"], round(8.8 * 1000 * solar.INSTALLED_COST_PER_WATT_CAD, 2))

    def test_payback_period_when_savings_known(self):
        result = build_financials(8.8, estimated_annual_savings_cad=1350.0)
        cost = result["estimated_installed_cost_cad"]
        self.assertEqual(result["payback_period_years"], round(cost / 1350.0, 1))

    def test_payback_none_when_savings_none(self):
        result = build_financials(8.8, estimated_annual_savings_cad=None)
        self.assertIsNone(result["payback_period_years"])
        self.assertIsNone(result["lifetime_net_savings_cad"])

    def test_payback_none_when_savings_zero(self):
        result = build_financials(8.8, estimated_annual_savings_cad=0)
        self.assertIsNone(result["payback_period_years"])

    def test_lifetime_net_savings_over_default_lifespan(self):
        result = build_financials(8.8, estimated_annual_savings_cad=1350.0)
        cost = result["estimated_installed_cost_cad"]
        self.assertEqual(result["lifetime_net_savings_cad"], round(1350.0 * 25 - cost, 2))

    def test_custom_cost_per_watt_and_lifespan(self):
        result = build_financials(10.0, 1000.0, cost_per_watt_cad=3.5, lifespan_years=20)
        self.assertEqual(result["estimated_installed_cost_cad"], 35000.0)
        self.assertEqual(result["panel_lifespan_years"], 20)


class TestBuildCarbonOffset(unittest.TestCase):
    def test_computes_annual_and_lifetime_offset(self):
        result = build_carbon_offset(10396.1, carbon_offset_factor_kg_per_mwh=428.9)
        expected_annual = round((10396.1 / 1000) * 428.9, 1)
        self.assertEqual(result["annual_co2_offset_kg"], expected_annual)
        self.assertEqual(result["lifetime_co2_offset_tonnes"], round(expected_annual * 25 / 1000, 2))

    def test_none_when_factor_missing(self):
        self.assertIsNone(build_carbon_offset(10396.1, None))


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
        self.assertEqual(summary["panels_count"], 20)
        self.assertEqual(summary["system_size_kw"], 8.8)
        self.assertEqual(summary["estimated_annual_production_kwh"], round(9451.0 * 440 / 400, 1))
        self.assertIn(summary["verdict"], {"full_coverage", "partial_coverage", "too_small"})
        self.assertNotIn("assumptions", summary)
        self.assertIsNotNone(summary["disclaimer"])
        self.assertIsNotNone(summary["comparison"]["estimated_annual_savings_cad"])
        self.assertEqual(summary["target_offset_pct"], 100)
        self.assertTrue(summary["recommended_meets_target"])
        self.assertIn("max_roof_capacity", summary)
        self.assertEqual(summary["max_roof_capacity"]["panels_count"], 24)
        self.assertIn("financials", summary)
        self.assertIn("carbon_offset", summary)

    async def test_roof_orientation_grouped_from_recommended_config(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        directions = {r["direction"] for r in summary["roof_orientation"]}
        self.assertEqual(directions, {"S", "W"})

    async def test_recommended_falls_back_to_max_when_target_unreachable(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, annual_usage_kwh=100_000)
        self.assertEqual(summary["panels_count"], summary["max_roof_capacity"]["panels_count"])
        self.assertFalse(summary["recommended_meets_target"])

    async def test_financials_use_recommended_system_size(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000, rate_per_kwh=0.15)
        expected_cost = round(summary["system_size_kw"] * 1000 * solar.INSTALLED_COST_PER_WATT_CAD, 2)
        self.assertEqual(summary["financials"]["estimated_installed_cost_cad"], expected_cost)

    async def test_carbon_offset_present_when_factor_available(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=SAMPLE_BUILDING_INSIGHTS)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertIsNotNone(summary["carbon_offset"])
        self.assertEqual(summary["carbon_offset"]["carbon_offset_factor_kg_per_mwh"], 428.9)

    async def test_carbon_offset_none_when_factor_missing(self):
        raw = {**SAMPLE_BUILDING_INSIGHTS}
        raw["solarPotential"] = {**raw["solarPotential"]}
        raw["solarPotential"].pop("carbonOffsetFactorKgPerMwh")
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=raw)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertTrue(summary["available"])
        self.assertIsNone(summary["carbon_offset"])

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
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=SolarApiNoCoverage("nope"))), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "no_coverage")

    async def test_not_configured_degrades_gracefully(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=SolarApiNotConfigured("no key"))), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "not_configured")

    async def test_request_error_collapses_to_error(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=SolarApiRequestError("bad key"))), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "error")

    async def test_unexpected_exception_collapses_to_error(self):
        with patch("solar.fetch_building_insights", new=AsyncMock(side_effect=RuntimeError("boom"))), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "error")

    async def test_no_panel_data_when_configs_missing(self):
        malformed = {"solarPotential": {}}
        with patch("solar.fetch_building_insights", new=AsyncMock(return_value=malformed)), \
             patch("solar.fetch_daily_irradiance", new=AsyncMock(return_value=FAKE_DAILY_IRRADIANCE)):
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
        self.assertFalse(summary["available"])
        self.assertEqual(summary["reason"], "no_panel_data")

    async def test_irradiance_fetch_runs_concurrently_with_building_insights(self):
        """
        Verifies the two independent external calls actually run in parallel
        (asyncio.gather), not one after another: each mock sleeps 0.2s, so a
        sequential await chain would take >=0.4s while a concurrent one stays
        near 0.2s.
        """
        async def slow_insights(*_args, **_kwargs):
            await asyncio.sleep(0.2)
            return SAMPLE_BUILDING_INSIGHTS

        async def slow_irradiance(*_args, **_kwargs):
            await asyncio.sleep(0.2)
            return FAKE_DAILY_IRRADIANCE

        with patch("solar.fetch_building_insights", new=slow_insights), \
             patch("solar.fetch_daily_irradiance", new=slow_irradiance):
            start = time.perf_counter()
            summary = await get_building_solar_summary(51.05, -114.07, 9000)
            elapsed = time.perf_counter() - start

        self.assertTrue(summary["available"])
        self.assertLess(elapsed, 0.35)


if __name__ == "__main__":
    unittest.main()
