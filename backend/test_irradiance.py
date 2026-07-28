"""
Unit tests for backend/irradiance.py — NASA POWER historical solar
irradiance integration. No live API call is made; all HTTP is faked.
"""

import unittest
from unittest.mock import patch

import irradiance
from irradiance import (
    IrradianceApiError,
    aggregate_monthly_irradiance,
    distribute_annual_production,
    fetch_daily_irradiance,
)

SAMPLE_POWER_RESPONSE = {
    "properties": {
        "parameter": {
            "ALLSKY_SFC_SW_DWN": {
                "20260601": 4.0,
                "20260602": 5.0,
                "20260630": -999,  # NASA's missing-data sentinel
                "20260701": 6.0,
            }
        }
    }
}


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
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


class TestFetchDailyIrradiance(unittest.IsolatedAsyncioTestCase):
    async def test_200_returns_daily_values(self):
        fake_response = _FakeResponse(200, SAMPLE_POWER_RESPONSE)
        with patch.object(irradiance.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            data = await fetch_daily_irradiance(51.05, -114.07)
        self.assertEqual(data, SAMPLE_POWER_RESPONSE["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"])

    async def test_non_200_raises(self):
        fake_response = _FakeResponse(500, {})
        with patch.object(irradiance.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            with self.assertRaises(IrradianceApiError):
                await fetch_daily_irradiance(51.05, -114.07)

    async def test_network_error_raises(self):
        fake_client = _FakeAsyncClient(exc=irradiance.httpx.ConnectTimeout("timed out"))
        with patch.object(irradiance.httpx, "AsyncClient", lambda *a, **kw: fake_client):
            with self.assertRaises(IrradianceApiError):
                await fetch_daily_irradiance(51.05, -114.07)

    async def test_unexpected_shape_raises(self):
        fake_response = _FakeResponse(200, {"properties": {}})
        with patch.object(irradiance.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            with self.assertRaises(IrradianceApiError):
                await fetch_daily_irradiance(51.05, -114.07)


class TestAggregateMonthlyIrradiance(unittest.TestCase):
    def test_sums_into_calendar_month_buckets(self):
        daily = SAMPLE_POWER_RESPONSE["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        monthly = aggregate_monthly_irradiance(daily)
        self.assertEqual(monthly, {"2026-06": 9.0, "2026-07": 6.0})

    def test_filters_missing_data_sentinel(self):
        monthly = aggregate_monthly_irradiance({"20260630": -999})
        self.assertEqual(monthly, {})

    def test_empty_input_returns_empty_dict(self):
        self.assertEqual(aggregate_monthly_irradiance({}), {})

    def test_none_values_are_skipped(self):
        monthly = aggregate_monthly_irradiance({"20260601": None, "20260602": 5.0})
        self.assertEqual(monthly, {"2026-06": 5.0})


class TestDistributeAnnualProduction(unittest.TestCase):
    def test_distributes_proportionally_to_irradiance_share(self):
        monthly_irradiance = {"2026-06": 9.0, "2026-07": 6.0}
        result = distribute_annual_production(monthly_irradiance, annual_production_kwh=1500.0)
        by_month = {r["month"]: r["estimated_production_kwh"] for r in result}
        self.assertEqual(by_month["2026-06"], 900.0)   # 9/15 * 1500
        self.assertEqual(by_month["2026-07"], 600.0)   # 6/15 * 1500

    def test_sorted_oldest_first(self):
        monthly_irradiance = {"2026-07": 6.0, "2026-06": 9.0}
        result = distribute_annual_production(monthly_irradiance, annual_production_kwh=1500.0)
        self.assertEqual([r["month"] for r in result], ["2026-06", "2026-07"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(distribute_annual_production({}, 1500.0), [])

    def test_zero_total_irradiance_returns_empty_list(self):
        self.assertEqual(distribute_annual_production({"2026-06": 0.0}, 1500.0), [])


if __name__ == "__main__":
    unittest.main()
