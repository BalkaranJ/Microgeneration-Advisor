"""
Google Solar API integration — building/roof-level solar potential data.

Best-effort: get_building_solar_summary() never raises; any failure
degrades to {"available": False, "reason": ..., "message": ...} so
/assess can always fall back to a rough usage-based size estimate even
when Google has no imagery for an address, the key isn't configured, or
the request otherwise fails.
"""
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

SOLAR_API_URL = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
REQUEST_TIMEOUT = 15

LEADING_PANEL_WATTS = 440          # current leading high-efficiency residential panel
                                    # (vs. Google's own often-lower panelCapacityWatts, e.g. 400W observed live)
OFFSET_FULL_COVERAGE_PCT = 100     # >= 100% -> "covers everything, credit to spare"
OFFSET_PARTIAL_COVERAGE_PCT = 25   # >= 25% (and < 100%) -> "covers part"; below -> "too small to matter"

DISCLAIMER_TEXT = (
    "This is a pre-application estimate only, not an engineered solar proposal. "
    "Actual production depends on the specific equipment installed, mounting angle, "
    "real-world shading, and your utility's interconnection and rate terms — confirm "
    "all of this with a qualified installer before proceeding."
)


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


def size_to_max_roof_capacity(parsed: dict, leading_panel_watts: float = LEADING_PANEL_WATTS) -> Optional[dict]:
    """
    Sizes the system to this roof's maximum buildable panel count (the
    largest panelsCount entry in solarPanelConfigs) using a disclosed
    "leading panel wattage" assumption instead of Google's own (often
    lower) panel_capacity_watts. Google's own location-specific
    yearlyEnergyDcKwh for that max-panel config — already accounting for
    this roof's shading/tilt/orientation — is kept and scaled by the
    wattage ratio, rather than falling back to a flat kWh/kW/year rule
    of thumb. Returns None if there's no usable config/capacity data.
    """
    google_panel_capacity_watts = parsed.get("panel_capacity_watts")
    configs = parsed.get("solar_panel_configs") or []
    valid = [
        c for c in configs
        if c.get("panelsCount") is not None and c.get("yearlyEnergyDcKwh") is not None
    ]
    if not valid or not google_panel_capacity_watts:
        return None

    max_config = max(valid, key=lambda c: c["panelsCount"])
    wattage_ratio = leading_panel_watts / google_panel_capacity_watts

    return {
        "panels_count": max_config["panelsCount"],
        "panel_watts_assumed": leading_panel_watts,
        "google_panel_capacity_watts": google_panel_capacity_watts,
        "system_size_kw": round(max_config["panelsCount"] * leading_panel_watts / 1000, 2),
        "estimated_annual_production_kwh": round(max_config["yearlyEnergyDcKwh"] * wattage_ratio, 1),
    }


def classify_verdict(offset_pct: Optional[float]) -> dict:
    """Three-tier verdict on the roof-sized system's offset % of annual usage."""
    if offset_pct is None:
        return {"verdict": "unknown", "verdict_message": "Offset couldn't be calculated for this roof."}
    if offset_pct >= OFFSET_FULL_COVERAGE_PCT:
        return {
            "verdict": "full_coverage",
            "verdict_message": "This roof can cover your entire annual usage, with credit to spare.",
        }
    if offset_pct >= OFFSET_PARTIAL_COVERAGE_PCT:
        return {"verdict": "partial_coverage", "verdict_message": "This roof can cover part of your annual bill."}
    return {"verdict": "too_small", "verdict_message": "This roof is too small to make a real dent in your usage."}


def build_assumptions(panel_watts_assumed: float, google_panel_capacity_watts: float) -> list:
    return [
        "Sized to this roof's maximum buildable panel count from Google Solar imagery — not a usage-targeted size.",
        f"Assumes {panel_watts_assumed:.0f}W panels (a current leading high-efficiency residential panel), "
        f"vs. Google's own {google_panel_capacity_watts:.0f}W modeling assumption for this roof — annual "
        "production is scaled by that wattage ratio.",
        "Annual production reuses Google Solar's shading/tilt/orientation-aware model for this roof's max-panel configuration.",
        f"Verdict bands: {OFFSET_FULL_COVERAGE_PCT}%+ offset = full coverage, "
        f"{OFFSET_PARTIAL_COVERAGE_PCT}-{OFFSET_FULL_COVERAGE_PCT - 1}% = partial, "
        f"below {OFFSET_PARTIAL_COVERAGE_PCT}% = too small to matter.",
        "Savings only credit energy generated and used on-site at your bill's effective rate; grid-exported "
        "surplus isn't credited here.",
    ]


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
        sized = size_to_max_roof_capacity(parsed)
        if sized is None:
            return {
                "available": False,
                "reason": "no_panel_data",
                "message": "This roof doesn't have enough usable panel configuration data.",
            }

        comparison = build_comparison(sized["estimated_annual_production_kwh"], annual_usage_kwh, rate_per_kwh)
        verdict = classify_verdict(comparison["offset_pct"])

        return {
            "available": True,
            "reason": None,
            "imagery_quality": parsed["imagery_quality"],
            "imagery_date": parsed["imagery_date"],
            "whole_roof_area_m2": parsed["whole_roof_area_m2"],
            "max_sunshine_hours_per_year": parsed["max_sunshine_hours_per_year"],
            "carbon_offset_factor_kg_per_mwh": parsed["carbon_offset_factor_kg_per_mwh"],
            "panels_count": sized["panels_count"],
            "panel_watts_assumed": sized["panel_watts_assumed"],
            "google_panel_capacity_watts": sized["google_panel_capacity_watts"],
            "system_size_kw": sized["system_size_kw"],
            "estimated_annual_production_kwh": sized["estimated_annual_production_kwh"],
            "comparison": comparison,
            "verdict": verdict["verdict"],
            "verdict_message": verdict["verdict_message"],
            "assumptions": build_assumptions(sized["panel_watts_assumed"], sized["google_panel_capacity_watts"]),
            "disclaimer": DISCLAIMER_TEXT,
        }
    except Exception:
        return {
            "available": False,
            "reason": "error",
            "message": "Couldn't process roof solar data for this address.",
        }
