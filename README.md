# Microgeneration Readiness Advisor

**by Balkaran Singh Jaswal**

---

## Why this exists

If you've ever tried to figure out whether solar is actually worth it for your property, you know the drill — you end up with like 15 tabs open. One site has the utility rules, another has the weather data, another has some government PDF from 2019 that may or may not still apply. It's a lot, and most of it isn't written for regular people.

This app tries to be the starting point that pulls that thinking together in one place. You're not going to walk away with a permit or an engineer's sign-off — that's not what this is. But you *will* get a clear, plain-language read on whether your location even makes sense for solar before you go spend money finding out the hard way.

---

## What it does

You plug in your address, tell it your rough energy usage and proposed system size, and it spits out:

- A solar suitability score for your location, based on real weather data
- A plain-language recommendation based on those scores
- A readiness checklist of things to sort out before you go any further

Simple. That's the whole idea.

---

## Architecture

The app is split into two pieces:

- **`backend/`** — a FastAPI service. `main.py` exposes `/geocode` and `/assess` endpoints, `advisor.py` holds the scoring/classification logic, and `weather.py` calls out to Nominatim (geocoding) and Open-Meteo (weather) so scores are based on real data for any address, not a fixed list of cities.
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

### Running the tests

```bash
cd backend
python -m pytest test_advisor.py -v
```

Or via the helper script from the repo root: `bash Phase3/scripts/run_tests.sh`.

---

## How the code is put together

### The scoring logic — `backend/advisor.py`

- `MicrogenerationProject` — bundles and validates the user's inputs (location, energy usage, system size, customer type). Validation failures raise a custom `InvalidProjectInputError`, which the API layer turns into a friendly 422 response instead of a crash.
- `WeatherProfile` — a clean, encapsulated wrapper around the solar indicator for a location.
- `SuitabilityScorer` (abstract) with `SolarSuitabilityScorer` — a scoring strategy that weighs sunlight and subtracts a cloud penalty. Kept as an abstract base for a single concrete strategy, so a future generation type could be reintroduced without touching the facade.
- `ProjectClassifier` — categorises the project as small (≤10 kW), medium (≤150 kW), or large/out-of-scope, and builds a fuller label like "Small residential solar microgeneration concept."
- `ReadinessAdvisor` — the facade. One method, `assess()`, hides all the steps: scoring, classifying the project, building the recommendation text, and returning a tidy results dictionary.

### Real weather data — `backend/weather.py`

`geocode()` resolves a free-text address to coordinates via Nominatim. `fetch_weather()` pulls the past week of hourly solar radiation and cloud cover from Open-Meteo for those coordinates and averages it into the same 0–100 indicator the scorer expects — so any address works, not just a fixed list of Alberta cities.

### The API — `backend/main.py`

A thin FastAPI layer with two endpoints, `/geocode` and `/assess`, that wire the above pieces together and translate exceptions into proper HTTP error responses.

### The UI — `frontend/`

Built with React + Vite. `App.jsx` drives a conversational, one-question-at-a-time flow (see `components/Step.jsx` and `AnswerBubble.jsx`), then calls `/assess` and renders the result via `components/Results.jsx`.

---

## Status

Working prototype. Uses live geocoding and weather data. No mobile optimization yet. More coming if there's interest.

---

*Built in Calgary, Alberta.*
