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

from irradiance import aggregate_monthly_irradiance, distribute_annual_production, fetch_daily_irradiance

load_dotenv()

SOLAR_API_URL = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
REQUEST_TIMEOUT = 15

LEADING_PANEL_WATTS = 440          # current leading high-efficiency residential panel
                                    # (vs. Google's own often-lower panelCapacityWatts, e.g. 400W observed live)
OFFSET_FULL_COVERAGE_PCT = 100     # >= 100% -> "covers everything, credit to spare"
OFFSET_PARTIAL_COVERAGE_PCT = 25   # >= 25% (and < 100%) -> "covers part"; below -> "too small to matter"

INSTALLED_COST_PER_WATT_CAD = 3.00   # rough turnkey residential installed cost per watt (CAD),
                                      # before any grants/rebates — a round, disclosed planning-
                                      # stage placeholder. Web-verified against current Alberta-
                                      # specific solar-contractor pricing (2026): commonly cited
                                      # ranges are $2.40-$3.01/W and $2.80-$3.40/W, with $2.50-
                                      # $3.50/W cited as the general small-residential range —
                                      # $3.00/W sits centrally in that band. Same spirit as
                                      # LEADING_PANEL_WATTS above: a disclosed assumption, not a
                                      # real quote. Sources: getenergy.ca/solar-panel-cost-alberta,
                                      # fortmcmurraysolar.ca/blog/how-much-do-solar-panels-cost-in-alberta
PANEL_LIFESPAN_YEARS = 25            # industry-standard manufacturer *performance* warranty term
                                      # (distinct from the older, shorter product/workmanship
                                      # warranty) — near-universal across Tier-1 panel makers per
                                      # EnergySage/SolarReviews; used for lifetime savings/CO2
                                      # figures. Sources: energysage.com/solar/solar-panel-warranties,
                                      # solarreviews.com/blog/guide-to-solar-panel-warranties

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


def _valid_configs(configs: list) -> list:
    """solarPanelConfigs entries usable for sizing (has panelsCount + yearlyEnergyDcKwh)."""
    return [
        c for c in configs
        if c.get("panelsCount") is not None and c.get("yearlyEnergyDcKwh") is not None
    ]


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

    This is the whole-roof *ceiling*, kept for informational context — see
    size_to_recommended_system() below for the usage-sized recommendation
    that actually drives the headline report.
    """
    google_panel_capacity_watts = parsed.get("panel_capacity_watts")
    valid = _valid_configs(parsed.get("solar_panel_configs") or [])
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
        "roof_segment_summaries": max_config.get("roofSegmentSummaries") or [],
    }


def size_to_recommended_system(
    parsed: dict,
    annual_usage_kwh: float,
    leading_panel_watts: float = LEADING_PANEL_WATTS,
    target_offset_pct: float = OFFSET_FULL_COVERAGE_PCT,
) -> Optional[dict]:
    """
    Sizes the system the way a real installer actually would: picks the
    SMALLEST solarPanelConfigs entry (by panelsCount) whose wattage-rescaled
    yearlyEnergyDcKwh reaches target_offset_pct of the customer's usage.
    Google's solarPanelConfigs is a cumulative series ordered from the
    roof's single best-yield spot upward, so this naturally prefers the
    best-facing side(s) first instead of maxing out the whole roof like
    size_to_max_roof_capacity() does. Configs are defensively re-sorted by
    panelsCount rather than trusting Google's order. Falls back to the
    single largest config (same tie-break as size_to_max_roof_capacity())
    if even the whole roof can't reach the target — "target_met" flags
    which happened. Returns None under the same conditions as
    size_to_max_roof_capacity().
    """
    google_panel_capacity_watts = parsed.get("panel_capacity_watts")
    valid = _valid_configs(parsed.get("solar_panel_configs") or [])
    if not valid or not google_panel_capacity_watts:
        return None

    wattage_ratio = leading_panel_watts / google_panel_capacity_watts
    target_kwh = annual_usage_kwh * (target_offset_pct / 100)

    sorted_by_panels = sorted(valid, key=lambda c: c["panelsCount"])
    chosen = next(
        (c for c in sorted_by_panels if c["yearlyEnergyDcKwh"] * wattage_ratio >= target_kwh),
        None,
    )
    target_met = chosen is not None
    if chosen is None:
        chosen = max(valid, key=lambda c: c["panelsCount"])

    return {
        "panels_count": chosen["panelsCount"],
        "panel_watts_assumed": leading_panel_watts,
        "google_panel_capacity_watts": google_panel_capacity_watts,
        "system_size_kw": round(chosen["panelsCount"] * leading_panel_watts / 1000, 2),
        "estimated_annual_production_kwh": round(chosen["yearlyEnergyDcKwh"] * wattage_ratio, 1),
        "roof_segment_summaries": chosen.get("roofSegmentSummaries") or [],
        "target_met": target_met,
    }


COMPASS_BOUNDARIES = [
    (22.5, "N"), (67.5, "NE"), (112.5, "E"), (157.5, "SE"),
    (202.5, "S"), (247.5, "SW"), (292.5, "W"), (337.5, "NW"),
]
COMPASS_ORDER = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def azimuth_to_compass(azimuth_degrees: float) -> str:
    """
    Buckets a roof segment's azimuth into an 8-point compass direction.
    Google's azimuthDegrees convention: 0=N, 90=E, 180=S, 270=W.
    """
    az = azimuth_degrees % 360
    for boundary, label in COMPASS_BOUNDARIES:
        if az < boundary:
            return label
    return "N"


def summarize_roof_orientation(roof_segment_summaries: list, wattage_ratio: float) -> list:
    """
    Groups a panel config's per-segment roofSegmentSummaries by compass
    direction, summing panel count and (wattage-ratio-scaled, so it stays
    consistent with the headline production number) yearly production per
    direction. Lets a user see e.g. "11 panels fit on the south side" —
    useful for reconciling Google's whole-roof max against a real
    installer's quote, which typically only uses the best-facing segments.
    Returns [] if there's no usable per-segment data.
    """
    by_direction = {}
    for seg in roof_segment_summaries or []:
        panels = seg.get("panelsCount")
        azimuth = seg.get("azimuthDegrees")
        if panels is None or azimuth is None:
            continue
        direction = azimuth_to_compass(azimuth)
        entry = by_direction.setdefault(direction, {"direction": direction, "panels_count": 0, "estimated_annual_production_kwh": 0.0})
        entry["panels_count"] += panels
        entry["estimated_annual_production_kwh"] += (seg.get("yearlyEnergyDcKwh") or 0.0) * wattage_ratio

    result = [by_direction[d] for d in COMPASS_ORDER if d in by_direction]
    for entry in result:
        entry["estimated_annual_production_kwh"] = round(entry["estimated_annual_production_kwh"], 1)
    result.sort(key=lambda e: e["panels_count"], reverse=True)
    return result


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


def estimate_installed_cost_cad(
    system_size_kw: float,
    cost_per_watt_cad: float = INSTALLED_COST_PER_WATT_CAD,
) -> float:
    """Rough turnkey installed cost for a system of this size, before any grants/rebates."""
    return round(system_size_kw * 1000 * cost_per_watt_cad, 2)


def build_financials(
    system_size_kw: float,
    estimated_annual_savings_cad: Optional[float],
    cost_per_watt_cad: float = INSTALLED_COST_PER_WATT_CAD,
    lifespan_years: int = PANEL_LIFESPAN_YEARS,
) -> dict:
    """
    Rough cost/payback/lifetime-savings figures for the recommended system.
    Deliberately simple and undiscounted — no rate inflation, no panel
    output degradation modeled — matching this app's existing flat/linear
    approach (build_comparison(), _build_monthly_breakdown()). Payback and
    lifetime savings are None when annual savings aren't known or are zero,
    since cost / 0 is undefined.
    """
    cost = estimate_installed_cost_cad(system_size_kw, cost_per_watt_cad)

    payback_period_years = None
    lifetime_net_savings_cad = None
    if estimated_annual_savings_cad:
        payback_period_years = round(cost / estimated_annual_savings_cad, 1)
        lifetime_net_savings_cad = round(estimated_annual_savings_cad * lifespan_years - cost, 2)

    return {
        "estimated_installed_cost_cad": cost,
        "cost_per_watt_cad_assumed": cost_per_watt_cad,
        "payback_period_years": payback_period_years,
        "panel_lifespan_years": lifespan_years,
        "lifetime_net_savings_cad": lifetime_net_savings_cad,
        "note": (
            "Rough planning-stage estimate only — excludes any government grants/rebates and "
            "financing costs, and doesn't model panel output degradation or future utility rate "
            "changes over the system's lifetime."
        ),
    }


def build_carbon_offset(
    estimated_annual_production_kwh: float,
    carbon_offset_factor_kg_per_mwh: Optional[float],
    lifespan_years: int = PANEL_LIFESPAN_YEARS,
) -> Optional[dict]:
    """
    Converts annual production into an estimated CO2 offset using Google's
    own location-specific grid carbon-intensity factor — never a generic
    invented factor. Returns None if Google didn't return a factor for this
    location (occasionally absent), so the frontend can just hide the section.
    """
    if carbon_offset_factor_kg_per_mwh is None:
        return None
    annual_co2_offset_kg = round((estimated_annual_production_kwh / 1000) * carbon_offset_factor_kg_per_mwh, 1)
    return {
        "carbon_offset_factor_kg_per_mwh": carbon_offset_factor_kg_per_mwh,
        "annual_co2_offset_kg": annual_co2_offset_kg,
        "lifetime_co2_offset_tonnes": round(annual_co2_offset_kg * lifespan_years / 1000, 2),
    }


async def _build_monthly_breakdown(
    lat: float,
    lon: float,
    estimated_annual_production_kwh: float,
    monthly_usage_history: Optional[list],
    rate_per_kwh: Optional[float],
) -> list:
    """
    Best-effort: fetches real historical solar irradiance for this exact
    location over the trailing 365 days and uses it to distribute the
    roof's annual production estimate across actual calendar months, then
    left-joins the user's own bill-extracted monthly usage/cost history
    (matched by YYYY-MM). Never raises — [] on any failure, so the
    frontend can just hide this section.
    """
    try:
        daily = await fetch_daily_irradiance(lat, lon)
        monthly_irradiance = aggregate_monthly_irradiance(daily)
        monthly_production = distribute_annual_production(monthly_irradiance, estimated_annual_production_kwh)
    except Exception:
        return []

    usage_by_month = {m["month"]: m for m in (monthly_usage_history or []) if m.get("month")}
    breakdown = []
    for p in monthly_production:
        usage_entry = usage_by_month.get(p["month"])
        breakdown.append({
            "month": p["month"],
            "estimated_production_kwh": p["estimated_production_kwh"],
            "estimated_production_value_cad": (
                round(p["estimated_production_kwh"] * rate_per_kwh, 2) if rate_per_kwh is not None else None
            ),
            "actual_usage_kwh": usage_entry.get("kwh") if usage_entry else None,
            "actual_cost_cad": usage_entry.get("cost") if usage_entry else None,
        })
    return breakdown


async def get_building_solar_summary(
    lat: float,
    lon: float,
    annual_usage_kwh: float,
    rate_per_kwh: Optional[float] = None,
    monthly_usage_history: Optional[list] = None,
    api_key: Optional[str] = None,
    target_offset_pct: float = OFFSET_FULL_COVERAGE_PCT,
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
        max_capacity = size_to_max_roof_capacity(parsed)
        if max_capacity is None:
            return {
                "available": False,
                "reason": "no_panel_data",
                "message": "This roof doesn't have enough usable panel configuration data.",
            }

        # Passes the same validity gate max_capacity just passed above
        # (_valid_configs + panel_capacity_watts), so this can't be None here.
        recommended = size_to_recommended_system(parsed, annual_usage_kwh, target_offset_pct=target_offset_pct)

        comparison = build_comparison(recommended["estimated_annual_production_kwh"], annual_usage_kwh, rate_per_kwh)
        verdict = classify_verdict(comparison["offset_pct"])
        wattage_ratio = recommended["panel_watts_assumed"] / recommended["google_panel_capacity_watts"]
        roof_orientation = summarize_roof_orientation(recommended["roof_segment_summaries"], wattage_ratio)
        monthly_breakdown = await _build_monthly_breakdown(
            lat, lon, recommended["estimated_annual_production_kwh"], monthly_usage_history, rate_per_kwh
        )
        financials = build_financials(recommended["system_size_kw"], comparison["estimated_annual_savings_cad"])
        carbon_offset = build_carbon_offset(
            recommended["estimated_annual_production_kwh"], parsed["carbon_offset_factor_kg_per_mwh"]
        )

        return {
            "available": True,
            "reason": None,
            "imagery_quality": parsed["imagery_quality"],
            "imagery_date": parsed["imagery_date"],
            "whole_roof_area_m2": parsed["whole_roof_area_m2"],
            "max_sunshine_hours_per_year": parsed["max_sunshine_hours_per_year"],
            "carbon_offset_factor_kg_per_mwh": parsed["carbon_offset_factor_kg_per_mwh"],
            "panels_count": recommended["panels_count"],
            "panel_watts_assumed": recommended["panel_watts_assumed"],
            "google_panel_capacity_watts": recommended["google_panel_capacity_watts"],
            "system_size_kw": recommended["system_size_kw"],
            "estimated_annual_production_kwh": recommended["estimated_annual_production_kwh"],
            "target_offset_pct": target_offset_pct,
            "recommended_meets_target": recommended["target_met"],
            "max_roof_capacity": {
                "panels_count": max_capacity["panels_count"],
                "system_size_kw": max_capacity["system_size_kw"],
                "estimated_annual_production_kwh": max_capacity["estimated_annual_production_kwh"],
            },
            "comparison": comparison,
            "verdict": verdict["verdict"],
            "verdict_message": verdict["verdict_message"],
            "roof_orientation": roof_orientation,
            "monthly_breakdown": monthly_breakdown,
            "financials": financials,
            "carbon_offset": carbon_offset,
            "disclaimer": DISCLAIMER_TEXT,
        }
    except Exception:
        return {
            "available": False,
            "reason": "error",
            "message": "Couldn't process roof solar data for this address.",
        }
