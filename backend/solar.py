"""
Google Solar API integration — building/roof-level solar potential data.

Best-effort and additive: get_building_solar_summary() never raises; any
failure degrades to {"available": False, "reason": ..., "message": ...}
so /assess can always return the existing weather-based results even when
Google has no imagery for an address, the key isn't configured, or the
request otherwise fails.
"""
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

SOLAR_API_URL = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
REQUEST_TIMEOUT = 15


class SolarApiError(Exception):
    pass


class SolarApiNotConfigured(SolarApiError):
    """GOOGLE_SOLAR_API_KEY isn't set."""


class SolarApiNoCoverage(SolarApiError):
    """Google has no high-quality imagery for this location (HTTP 404)."""


class SolarApiRequestError(SolarApiError):
    """Bad key, API not enabled, or any other request/network failure."""


async def fetch_building_insights(lat: float, lon: float, api_key: Optional[str] = None) -> dict:
    """GET buildingInsights:findClosest and return the parsed JSON on success (200)."""
    key = api_key or os.getenv("GOOGLE_SOLAR_API_KEY")
    if not key:
        raise SolarApiNotConfigured("GOOGLE_SOLAR_API_KEY is not set.")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                SOLAR_API_URL,
                params={
                    "location.latitude": lat,
                    "location.longitude": lon,
                    "requiredQuality": "HIGH",
                    "key": key,
                },
                timeout=REQUEST_TIMEOUT,
            )
    except httpx.RequestError as e:
        raise SolarApiRequestError(str(e)) from e

    if response.status_code == 200:
        return response.json()
    if response.status_code == 404:
        raise SolarApiNoCoverage("No high-quality solar imagery for this location.")
    raise SolarApiRequestError(f"Solar API request failed with status {response.status_code}.")


def effective_rate_per_kwh(
    electricity_charge_incl_gst: Optional[float],
    bill_period_usage_kwh: Optional[float],
) -> Optional[float]:
    """
    $/kWh derived from the user's own bill: this billing period's electricity
    charge (incl. GST) divided by the metered usage for that same period.
    None if either input is missing or usage is non-positive.
    """
    if not electricity_charge_incl_gst or not bill_period_usage_kwh or bill_period_usage_kwh <= 0:
        return None
    return round(electricity_charge_incl_gst / bill_period_usage_kwh, 4)


def _format_imagery_date(d: Optional[dict]) -> Optional[str]:
    try:
        return "%04d-%02d-%02d" % (d["year"], d["month"], d["day"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_solar_potential(raw: dict) -> dict:
    """
    Pull only the fields this app needs out of the raw buildingInsights
    response, defensively — Google's returned fields vary with imagery
    quality/coverage, so every access here tolerates missing data.
    """
    solar_potential = raw.get("solarPotential") or {}
    whole_roof_stats = solar_potential.get("wholeRoofStats") or {}
    return {
        "imagery_quality": raw.get("imageryQuality"),
        "imagery_date": _format_imagery_date(raw.get("imageryDate")),
        "max_array_panels_count": solar_potential.get("maxArrayPanelsCount"),
        "max_array_area_m2": solar_potential.get("maxArrayAreaMeters2"),
        "max_sunshine_hours_per_year": solar_potential.get("maxSunshineHoursPerYear"),
        "panel_capacity_watts": solar_potential.get("panelCapacityWatts"),
        "carbon_offset_factor_kg_per_mwh": solar_potential.get("carbonOffsetFactorKgPerMwh"),
        "whole_roof_area_m2": whole_roof_stats.get("areaMeters2"),
        "solar_panel_configs": solar_potential.get("solarPanelConfigs") or [],
    }


def select_closest_config(parsed: dict, system_size_kw: float) -> Optional[dict]:
    """
    solarPanelConfigs[] is Google's list of {panelsCount, yearlyEnergyDcKwh}
    options, ascending by panel count. Convert the requested kW to a target
    panel count via panelCapacityWatts and pick the config whose panel count
    is closest to it. Returns None if there's no usable config/capacity data.
    """
    panel_capacity_watts = parsed.get("panel_capacity_watts")
    configs = parsed.get("solar_panel_configs") or []
    valid = [
        c for c in configs
        if c.get("panelsCount") is not None and c.get("yearlyEnergyDcKwh") is not None
    ]
    if not valid or not panel_capacity_watts:
        return None

    target_panels = (system_size_kw * 1000) / panel_capacity_watts
    best = min(valid, key=lambda c: abs(c["panelsCount"] - target_panels))
    max_available_panels = max(c["panelsCount"] for c in valid)

    return {
        "requested_system_size_kw": round(system_size_kw, 2),
        "panel_capacity_watts": panel_capacity_watts,
        "panels_count": best["panelsCount"],
        "matched_system_size_kw": round(best["panelsCount"] * panel_capacity_watts / 1000, 2),
        "estimated_annual_production_kwh": round(best["yearlyEnergyDcKwh"], 1),
        "roof_capacity_exceeded": target_panels > max_available_panels,
    }


def build_comparison(
    estimated_annual_production_kwh: float,
    annual_usage_kwh: float,
    rate_per_kwh: Optional[float],
) -> dict:
    """
    Compares Google's production estimate against the bill-derived annual
    usage. Savings are conservative: only self-consumed kWh
    (min(production, usage)) are credited at the bill's effective rate —
    surplus exported to the grid isn't credited, since this app doesn't
    collect export/net-metering rates.
    """
    offset_pct = (
        round(estimated_annual_production_kwh / annual_usage_kwh * 100, 1)
        if annual_usage_kwh else None
    )
    surplus_kwh = (
        round(estimated_annual_production_kwh - annual_usage_kwh, 1)
        if annual_usage_kwh is not None else None
    )

    result = {
        "annual_usage_kwh": annual_usage_kwh,
        "offset_pct": offset_pct,
        "surplus_kwh": surplus_kwh,
        "rate_per_kwh_cad": rate_per_kwh,
        "estimated_annual_savings_cad": None,
        "savings_note": None,
    }
    if rate_per_kwh is not None and annual_usage_kwh:
        self_consumed_kwh = min(estimated_annual_production_kwh, annual_usage_kwh)
        result["estimated_annual_savings_cad"] = round(self_consumed_kwh * rate_per_kwh, 2)
        result["savings_note"] = (
            "Assumes energy you generate and use on-site is offset at your bill's "
            "effective $/kWh rate; surplus exported to the grid isn't credited here "
            "since export/net-metering rates weren't provided."
        )
    return result


async def get_building_solar_summary(
    lat: float,
    lon: float,
    system_size_kw: float,
    annual_usage_kwh: float,
    rate_per_kwh: Optional[float] = None,
    api_key: Optional[str] = None,
) -> dict:
    """
    Never raises. Returns the dict embedded as /assess's
    "roof_solar_potential" field — either {"available": True, ...} or
    {"available": False, "reason": ..., "message": ...}.
    """
    try:
        raw = await fetch_building_insights(lat, lon, api_key)
    except SolarApiNotConfigured:
        return {
            "available": False,
            "reason": "not_configured",
            "message": "Roof-level solar data isn't configured for this deployment.",
        }
    except SolarApiNoCoverage:
        return {
            "available": False,
            "reason": "no_coverage",
            "message": "High-resolution roof imagery isn't available for this address yet.",
        }
    except Exception:
        return {
            "available": False,
            "reason": "error",
            "message": "Roof-level solar data is temporarily unavailable.",
        }

    try:
        parsed = parse_solar_potential(raw)
        config = select_closest_config(parsed, system_size_kw)
        if config is None:
            return {
                "available": False,
                "reason": "no_panel_data",
                "message": "This roof doesn't have enough usable panel configuration data.",
            }

        return {
            "available": True,
            "reason": None,
            "imagery_quality": parsed["imagery_quality"],
            "imagery_date": parsed["imagery_date"],
            "max_array_panels_count": parsed["max_array_panels_count"],
            "max_array_area_m2": parsed["max_array_area_m2"],
            "max_sunshine_hours_per_year": parsed["max_sunshine_hours_per_year"],
            "whole_roof_area_m2": parsed["whole_roof_area_m2"],
            "carbon_offset_factor_kg_per_mwh": parsed["carbon_offset_factor_kg_per_mwh"],
            "matched_config": config,
            "comparison": build_comparison(
                config["estimated_annual_production_kwh"], annual_usage_kwh, rate_per_kwh
            ),
        }
    except Exception:
        return {
            "available": False,
            "reason": "error",
            "message": "Couldn't process roof solar data for this address.",
        }
