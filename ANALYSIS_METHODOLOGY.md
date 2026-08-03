# Analysis Methodology

This document explains exactly how the Analysis Report is calculated — every data source, formula, and disclosed assumption — so the numbers in the app are traceable rather than a black box. It's meant to be kept in sync with `backend/solar.py` (and its neighbours) whenever a formula or constant changes; if you're changing one, update this too.

**Core principle:** every number that isn't directly measured is a disclosed, sourced assumption — never a fabricated one. This app deliberately does *not* invent things like vendor names/contact info or CO₂-equivalency metrics ("X trees planted") where no verifiable source exists. Where a genuine industry figure is used (e.g. installed cost per watt, panel warranty length), it's cited below.

---

## 1. Data sources

| Source | What it provides | Real / measured, or modeled? |
|---|---|---|
| **Google Solar API** (`buildingInsights:findClosest`, `backend/solar.py`) | Roof geometry, a series of buildable panel-layout configs (`solarPanelConfigs`) each with a location-specific production estimate, and the local grid's carbon intensity factor | Real — aerial-imagery-derived, shading/tilt/orientation-aware, specific to this exact roof |
| **NASA POWER** (`temporal/daily/point`, `backend/irradiance.py`) | Real historical daily solar irradiance for the exact lat/lon, trailing 365 days | Real, measured |
| **Nominatim** (`backend/weather.py`) | Geocodes a free-text address to lat/lon | Real |
| **Claude vision OCR** (`backend/bill_extractor.py`) | Reads usage (kWh), cost ($), and monthly history directly off a photo of the user's own utility bill | Real (as legible on the bill) |
| **Google Static Maps** (`backend/roof_image.py`) | Satellite image shown in the "Location confirmed" card | Real imagery, informational only — not used in any calculation |

Everything below this line is either a direct pass-through of the above, or a disclosed formula/assumption applied to it.

---

## 2. Sizing: how many panels, how big a system

Google returns `solarPanelConfigs` as a **cumulative series**, ordered by increasing `panelsCount` — each entry is Google's optimal panel layout for that count, built by adding the roof's next-best-yield spot onto the previous config. In other words, the list is already ordered best-facing-segment-first.

- **`size_to_recommended_system()`** — the primary sizer, and what drives the headline report. Picks the **smallest** config whose production reaches a target offset (`target_offset_pct`, default **100%**) of the customer's annual usage. Because the config series is best-segment-first, this naturally mirrors how a real installer sizes a system to the customer's actual need, using the best-facing side(s) of the roof first — rather than defaulting to the whole roof. Falls back to the single largest config if even the whole roof can't reach the target (flagged via `recommended_meets_target: false`).
- **`size_to_max_roof_capacity()`** — kept as informational context only (`max_roof_capacity` in the response): the roof's absolute ceiling if every buildable segment were used.
- **`LEADING_PANEL_WATTS = 440`** — Google's own `panelCapacityWatts` reflects an assumption baked into its imagery model and is often a lower, older figure (400W has been observed live). Instead, Google's per-config production (`yearlyEnergyDcKwh`) — which already accounts for this specific roof's shading, tilt, and orientation — is rescaled by the ratio `440 / google_panel_capacity_watts`, rather than discarding Google's location-specific number in favor of a flat kWh/kW/year rule of thumb.

### No-roof-data fallback

When Google has no coverage for an address (or the key isn't configured, or the request fails), `advisor.py`'s `estimate_target_system_size_kw()` takes over: a flat rule of thumb targeting **~80% offset** of annual usage at a conservative Alberta-wide yield assumption of **1,300 kWh/kW/year**. This is intentionally more conservative than the roof-based 100% target, since it has no roof-specific data to work from.

---

## 3. Verdict thresholds

`classify_verdict()` buckets the resulting offset percentage (production ÷ annual usage) into three plain-language tiers:

| Verdict | Threshold | Meaning |
|---|---|---|
| `full_coverage` | offset ≥ **100%** | Covers your entire annual usage, credit to spare |
| `partial_coverage` | **25%** ≤ offset < 100% | Covers part of your bill |
| `too_small` | offset < 25% | Not enough to make a real dent |

These thresholds are arbitrary-but-disclosed choices, not derived from any external standard.

Because sizing already targets 100% offset by default (§2), `full_coverage` is the common outcome whenever the roof is capable of it — often landing slightly *above* 100% ("credit to spare") since Google's config granularity is coarse (panel counts jump in fixed increments, so the smallest config clearing the target can overshoot it a little). `partial_coverage` and `too_small` now specifically flag the case where **even the whole roof** (`max_roof_capacity`) can't reach full coverage.

---

## 4. Savings

- **`effective_rate_per_kwh()`** — the user's own $/kWh rate, computed as this billing period's electricity charge (incl. GST) ÷ the metered usage for that same period. Both numbers come straight off the user's uploaded bill (via Claude vision OCR) — nothing is looked up from a generic utility rate table.
- **`build_comparison()`** — savings are conservative: only *self-consumed* kWh (`min(production, usage)`) are credited at that rate. Any surplus exported to the grid is **not** credited, since this app doesn't collect the user's specific net-metering / export-credit terms — that's flagged explicitly in `Vendors & Next Steps` as something to confirm with the utility.

---

## 5. Financial: installation cost & payback

New in this pass. `build_financials()` computes rough cost/payback/lifetime-savings figures for the **recommended** (not whole-roof-max) system size, deliberately kept simple and undiscounted — no rate inflation, no panel output degradation modeled — matching this app's existing flat/linear approach elsewhere (e.g. `build_comparison()`, the monthly breakdown).

| Constant | Value | Source / reasoning |
|---|---|---|
| `INSTALLED_COST_PER_WATT_CAD` | **$3.00/W CAD** | Web-verified against current (2026) Alberta-specific residential solar-contractor pricing: cited ranges include $2.40–$3.01/W and $2.80–$3.40/W, with $2.50–$3.50/W cited as the general small-residential range. $3.00/W sits centrally in that band — a round, disclosed planning-stage placeholder, not a real quote. ([getenergy.ca](https://getenergy.ca/solar-panel-cost-alberta/), [fortmcmurraysolar.ca](https://fortmcmurraysolar.ca/blog/how-much-do-solar-panels-cost-in-alberta)) |
| `PANEL_LIFESPAN_YEARS` | **25 years** | The near-universal industry-standard manufacturer *performance* warranty term across Tier-1 panel makers (distinct from the older, shorter product/workmanship warranty). ([energysage.com](https://www.energysage.com/solar/solar-panel-warranties/), [solarreviews.com](https://www.solarreviews.com/blog/guide-to-solar-panel-warranties)) |

Formulas:
- **Installed cost** = `system_size_kw × 1000 × INSTALLED_COST_PER_WATT_CAD`
- **Payback period (years)** = installed cost ÷ estimated annual savings (`None` if savings aren't known or are zero — the app never divides by zero)
- **Lifetime net savings** (25yr) = `annual_savings × 25 − installed cost` (undiscounted; `None` under the same condition as payback)

**Explicitly not modeled**, and disclosed as such in the UI's `financials.note`:
- Government grants/rebates (e.g. federal or provincial programs) — none are applied
- Financing costs (loan interest, etc.)
- Panel output degradation over the 25-year period
- Future utility rate changes (inflation)

These are omitted deliberately to keep the estimate simple and conservative rather than falsely precise — a homeowner should treat this as a rough planning number and get a real quote, not a financial projection.

---

## 6. Environmental impact (CO₂ offset)

Also new in this pass. `build_carbon_offset()` uses Google's own **location-specific** `carbonOffsetFactorKgPerMwh` (the CO₂ intensity of the electricity this specific system would displace, based on the local grid) — never a generic national/global factor. If Google doesn't return one for a given location, the section is simply omitted (`carbon_offset: null`) rather than substituting a guessed number.

- **Annual CO₂ offset (kg)** = `(estimated_annual_production_kwh / 1000) × carbon_offset_factor_kg_per_mwh`
- **Lifetime CO₂ offset (tonnes)** = `annual_co2_offset_kg × 25 / 1000`

No equivalency metrics (e.g. "X trees planted," "X km not driven") are included — those require their own separately-sourced conversion factors, and none are used here without a citable source, per the same no-fabrication principle as the vendors section.

---

## 7. Monthly production vs. usage

`_build_monthly_breakdown()` fetches real daily irradiance from NASA POWER for the exact coordinates over the trailing 365 days, aggregates it into real calendar-month buckets, and distributes the annual production estimate across those months **proportionally to each month's real irradiance share** — not a generic seasonal curve. This is then left-joined (by `YYYY-MM`) against the user's own bill-extracted monthly usage/cost history, when available, so the chart compares real production timing against the user's real historical usage.

---

## 8. Disclaimer & graceful degradation

Every report — regardless of whether Google Solar data is available — carries this disclaimer:

> "This is a pre-application estimate only, not an engineered solar proposal. Actual production depends on the specific equipment installed, mounting angle, real-world shading, and your utility's interconnection and rate terms — confirm all of this with a qualified installer before proceeding."

`get_building_solar_summary()` never raises: if Google has no imagery for an address, the API key isn't configured, or the request fails for any reason, the endpoint degrades to `{"available": false, "reason": ..., "message": ...}` and the app falls back to the usage-based rule-of-thumb sizing (§2) instead of breaking the flow.
