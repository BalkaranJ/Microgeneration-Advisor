# Microgeneration Readiness Advisor

**by Balkaran Singh Jaswal**

---

## Why this exists

If you've ever tried to figure out whether solar is actually worth it for your property, you know the drill — you end up with like 15 tabs open. One site has the utility rules, another has the weather data, another has some government PDF from 2019 that may or may not still apply. It's a lot, and most of it isn't written for regular people.

This app tries to be the starting point that pulls that thinking together in one place. You're not going to walk away with a permit or an engineer's sign-off — that's not what this is. But you *will* get a clear, plain-language read on whether your location even makes sense for solar before you go spend money finding out the hard way.

---

## What it does

You plug in your address (confirming the exact resolved location) and your rough annual energy usage, and it spits out:

- A system sized to whatever your roof can actually hold, using a current leading panel wattage (via Google's Solar API when available, or a rough usage-based estimate otherwise)
- The panel count, system size, and estimated yearly production for that roof
- A plain verdict — covers everything with credit to spare, covers part of your bill, or the roof's too small to make a real dent — plus the assumptions behind the numbers and a disclaimer
- A readiness checklist of things to sort out before you go any further, and a (for-now placeholder) vendors/next-steps section

Simple. That's the whole idea.

---

## Architecture

The app is split into two pieces:

- **`backend/`** — a FastAPI service. `main.py` exposes `/geocode` and `/assess` endpoints, `advisor.py` holds the classification/checklist logic, `weather.py` calls out to Nominatim for geocoding, and `solar.py` calls Google's Solar API to size a system from the roof and build the verdict report.
- **`frontend/`** — a React + Vite app that walks the user through a conversational, one-question-at-a-time form and calls the backend to render the results.

## How to run it

```powershell
# from the repo root — starts both servers
.\start.ps1
```

Or manually, in two terminals:

```bash
# backend
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The backend runs on `http://localhost:8000`.

### Setting up Google Solar API (optional — roof-level solar data)

The app works fine without this key; `/assess` just omits the "Roof & Solar
Potential" section. To enable it:

1. In [Google Cloud Console](https://console.cloud.google.com/), create (or pick) a project with billing enabled.
2. Enable the **Solar API** for that project.
3. Create an API key and restrict it (under "API restrictions") to the Solar API only — the key is only ever used server-side, so no HTTP referrer restriction is needed, but consider an IP restriction to your backend host in production.
4. Add it to `backend/.env`:
   ```
   GOOGLE_SOLAR_API_KEY=your-key-here
   ```
5. Coverage isn't global — many rural addresses will return no imagery. Test against a known-covered address (e.g. a major North American downtown core) to confirm the setup works, then test elsewhere to see the graceful "not available for this address" path.

### Running the tests

```bash
cd backend
python -m pytest test_advisor.py test_solar.py test_main.py -v
```

Or via the helper script from the repo root: `bash Phase3/scripts/run_tests.sh`.

---

## How the code is put together

### Classification & checklist — `backend/advisor.py`

- `MicrogenerationProject` — bundles and validates the user's inputs (location, energy usage, system size). Validation failures raise a custom `InvalidProjectInputError`, which the API layer turns into a friendly 422 response instead of a crash.
- `estimate_target_system_size_kw()` — a rule-of-thumb sizing function: targets a conservative ~80% offset of annual usage at an assumed Alberta-wide yield (1,300 kWh/kW/year). Used only as the fallback size when Google Solar roof data isn't available — see `solar.py` below for the primary, roof-based sizing.
- `ProjectClassifier` — categorises the project as small (≤10 kW), medium (≤150 kW), or large/out-of-scope, and builds a fuller label like "Small solar microgeneration concept."
- `ReadinessAdvisor` — a lean facade. One method, `assess()`, classifies the project and returns the readiness checklist. The actual production/offset verdict lives entirely in `solar.py`'s report, not here (a generic weather-based suitability score used to live here too, but was dropped in favor of that more concrete, roof-specific verdict).

### Geocoding — `backend/weather.py`

`geocode()` resolves a free-text address to coordinates via Nominatim. The frontend calls this directly (via `/geocode`) as an address-confirmation step before submitting the full assessment — see below.

### Roof-based sizing & verdict — `backend/solar.py`

Calls Google's Solar API (`buildingInsights:findClosest`) for the confirmed coordinates and, defensively, pulls out roof/production data. `size_to_max_roof_capacity()` sizes the system to this roof's *maximum* buildable panel count, re-rated to a disclosed "leading panel wattage" assumption (440W, vs. Google's own often-lower per-panel assumption) — Google's own shading/tilt/orientation-aware production estimate for that max config is kept and scaled by the wattage ratio rather than using a flat rule of thumb. `build_comparison()` weighs that production against the bill-derived `annual_usage_kwh` (using a $/kWh rate computed from the bill's own charge and metered usage) to get an offset percentage and rough annual savings, and `classify_verdict()` turns the offset into one of three plain verdicts: full coverage (≥100%), partial coverage (25-99%), or too small to make a dent (<25%) — thresholds documented in `build_assumptions()`, shown to the user alongside a disclaimer. Entirely best-effort: if Google has no imagery for an address, the key isn't configured, or the request fails for any reason, `get_building_solar_summary()` returns an `"available": False` result instead of raising, so `/assess` always falls back cleanly to a rough usage-based size estimate.

### The API — `backend/main.py`

A thin FastAPI layer with three endpoints: `/geocode` (address string → resolved coordinates, called by the frontend's address-confirmation step), `/assess` (confirmed coordinates + usage → scored results, including a calculated `recommended_system_size_kw`), and `/extract-bill`. Wires the above pieces together and translates exceptions into proper HTTP error responses.

### The UI — `frontend/`

Built with React + Vite. `App.jsx` drives a conversational, one-question-at-a-time flow — just address and annual usage now — (see `components/Step.jsx`, `components/AddressConfirm.jsx`, and `AnswerBubble.jsx`), then calls `/assess` and renders the result via `components/Results.jsx`, which composes `RoofSolarCard.jsx` (the sizing/verdict/assumptions report), the readiness checklist, and `VendorsNextSteps.jsx` (currently a placeholder — no vendor names yet). The address step calls `/geocode` first and requires the user to confirm the resolved address before continuing, since free-text geocoding can occasionally resolve to the wrong building on ambiguously-named streets.

---

## Status

Working prototype. Uses live geocoding and, where configured, live roof imagery. No mobile optimization yet. More coming if there's interest.

---

*Built in Calgary, Alberta.*
