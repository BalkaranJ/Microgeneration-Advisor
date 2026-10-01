# Architecture

A walkthrough of how SolarFit is put together. For how every number is calculated and sourced, see [ANALYSIS_METHODOLOGY.md](ANALYSIS_METHODOLOGY.md).

## Classification & bottom line: `backend/advisor.py`

- `MicrogenerationProject`: bundles and validates the user's inputs (location, energy usage, system size). Validation failures raise a custom `InvalidProjectInputError`, which the API layer turns into a friendly 422 response instead of a crash.
- `estimate_target_system_size_kw()`: a rule-of-thumb sizing function: targets a conservative ~80% offset of annual usage at an assumed Alberta-wide yield (1,300 kWh/kW/year). Used only as the fallback size when Google Solar roof data isn't available. See `solar.py` below for the primary, roof-based sizing.
- `ProjectClassifier`: categorises the project as small (≤10 kW), medium (≤150 kW), or large/out-of-scope, and builds a fuller label like "Small solar microgeneration concept."
- `ReadinessAdvisor`: a lean facade. One method, `assess()`, classifies the project and builds a single verdict-driven "bottom line" (a `tone`, a headline, one line of reasoning tied to the actual numbers, and a next action: get quotes, or skip it for now), from the same roof/verdict data `solar.py` already computed. The actual production/offset verdict lives entirely in `solar.py`'s report, not here (a generic weather-based suitability score used to live here too, but was dropped in favor of that more concrete, roof-specific verdict).

## Geocoding: `backend/weather.py`

`geocode()` resolves a free-text address to coordinates via Nominatim. The frontend calls this directly (via `/geocode`) as an address-confirmation step before submitting the full assessment.

## Roof-based sizing & verdict: `backend/solar.py`

Calls Google's Solar API (`buildingInsights:findClosest`) for the confirmed coordinates and, defensively, pulls out roof/production data. `size_to_recommended_system()` is the primary sizer: since Google returns its panel-layout configs (`solarPanelConfigs`) as a cumulative series ordered best-facing-segment-first, picking the smallest config that reaches a target offset (100% by default) of the user's actual usage mirrors how a real installer would size a system, using the roof's best side(s) first, not maxing out every facet. `size_to_max_roof_capacity()` is kept alongside it purely as informational context (the roof's whole-buildable-area ceiling). Both re-rate Google's per-config production to a disclosed "leading panel wattage" assumption (440W, vs. Google's own often-lower per-panel assumption), keeping Google's own shading/tilt/orientation-aware production estimate and scaling it by the wattage ratio rather than using a flat rule of thumb. `build_comparison()` weighs the recommended system's production against the bill-derived `annual_usage_kwh` (using a $/kWh rate computed from the bill's own charge and metered usage) to get an offset percentage and rough annual savings; `classify_verdict()` turns the offset into one of three plain verdicts: full coverage (≥100%), partial coverage (25-99%), or too small to make a dent (<25%), thresholds documented alongside `OFFSET_FULL_COVERAGE_PCT`/`OFFSET_PARTIAL_COVERAGE_PCT`. `build_financials()` and `build_carbon_offset()` add a rough installed-cost/payback estimate and an estimated CO₂ offset. See [ANALYSIS_METHODOLOGY.md](ANALYSIS_METHODOLOGY.md) for the full breakdown and sourcing of every constant used here. Entirely best-effort: if Google has no imagery for an address, the key isn't configured, or the request fails for any reason, `get_building_solar_summary()` returns an `"available": False` result instead of raising, so `/assess` always falls back cleanly to a rough usage-based size estimate.

## The API: `backend/main.py`

A thin FastAPI layer with three endpoints: `/geocode` (address string → resolved coordinates, called by the frontend's address-confirmation step), `/assess` (confirmed coordinates + usage → scored results, including a calculated `recommended_system_size_kw`), and `/extract-bill`. Wires the above pieces together and translates exceptions into proper HTTP error responses.

## The UI: `frontend/`

Built with React + Vite. `App.jsx` drives a conversational, one-question-at-a-time flow, just address and annual usage now (see `components/Step.jsx` and `components/AddressConfirm.jsx`), then calls `/assess` and renders the result via `components/Results.jsx`, which composes `RoofSolarCard.jsx` (the sizing/verdict/assumptions report) and `BottomLine.jsx` (the single verdict-colored headline/reasoning/action card). The address step calls `/geocode` first and requires the user to confirm the resolved address before continuing, since free-text geocoding can occasionally resolve to the wrong building on ambiguously-named streets.
