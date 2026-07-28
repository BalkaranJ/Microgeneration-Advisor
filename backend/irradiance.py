"""
NASA POWER API integration — free, no-key historical daily solar
irradiance for any lat/lon. Used to distribute Google Solar's annual
production estimate across months using this specific site's real sun
exposure for the trailing year, instead of a generic seasonal curve.
"""
from datetime import date, timedelta
from typing import Optional

import httpx

POWER_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
REQUEST_TIMEOUT = 20
IRRADIANCE_PARAMETER = "ALLSKY_SFC_SW_DWN"  # all-sky surface shortwave downward irradiance, kWh/m^2/day
MISSING_VALUE_SENTINEL = -999  # NASA POWER's marker for a missing daily reading


class IrradianceApiError(Exception):
    pass


async def fetch_daily_irradiance(lat: float, lon: float, end: Optional[date] = None) -> dict:
    """
    Returns {YYYYMMDD: kWh/m^2/day} for the trailing 365 days ending `end`
    (defaults to today). Raises IrradianceApiError on any failure —
    callers should treat this as best-effort and degrade gracefully.
    """
    end = end or date.today()
    start = end - timedelta(days=365)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                POWER_API_URL,
                params={
                    "parameters": IRRADIANCE_PARAMETER,
                    "community": "RE",
                    "longitude": lon,
                    "latitude": lat,
                    "start": start.strftime("%Y%m%d"),
                    "end": end.strftime("%Y%m%d"),
                    "format": "JSON",
                },
                timeout=REQUEST_TIMEOUT,
            )
    except httpx.RequestError as e:
        raise IrradianceApiError(str(e)) from e

    if response.status_code != 200:
        raise IrradianceApiError(f"NASA POWER request failed with status {response.status_code}.")

    data = response.json()
    try:
        return data["properties"]["parameter"][IRRADIANCE_PARAMETER]
    except (KeyError, TypeError) as e:
        raise IrradianceApiError("Unexpected NASA POWER response shape.") from e


def aggregate_monthly_irradiance(daily_values: dict) -> dict:
    """
    Sums {YYYYMMDD: kWh/m^2} into real calendar-month buckets
    {"YYYY-MM": total_kwh_per_m2}, filtering NASA's -999 missing-data
    sentinel. Real YYYY-MM keys (not a generic Jan-Dec cycle) are what let
    this line up directly with a bill's own monthly_history entries, which
    use the same YYYY-MM format.
    """
    monthly = {}
    for date_str, value in (daily_values or {}).items():
        if value is None or value <= MISSING_VALUE_SENTINEL:
            continue
        key = f"{date_str[:4]}-{date_str[4:6]}"
        monthly[key] = monthly.get(key, 0.0) + value
    return monthly


def distribute_annual_production(monthly_irradiance: dict, annual_production_kwh: float) -> list:
    """
    Scales the roof's annual production estimate by each month's share of
    the trailing-year irradiance total. Returns [] if there's no usable
    irradiance total to share against.
    """
    total = sum(monthly_irradiance.values())
    if total <= 0:
        return []
    return [
        {"month": month, "estimated_production_kwh": round(annual_production_kwh * kwh_m2 / total, 1)}
        for month, kwh_m2 in sorted(monthly_irradiance.items())
    ]
