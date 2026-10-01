# Microgeneration Readiness Advisor

**by Balkaran Singh Jaswal**

---

## Why this exists

If you've ever tried to figure out whether solar is actually worth it for your property, you know the drill: you end up with like 15 tabs open. One site has the utility rules, another has the weather data, another has some government PDF from 2019 that may or may not still apply. It's a lot, and most of it isn't written for regular people.

This app tries to be the starting point that pulls that thinking together in one place. You're not going to walk away with a permit or an engineer's sign-off. That's not what this is. But you *will* get a clear, plain-language read on whether your location even makes sense for solar before you go spend money finding out the hard way.

---

## What it does

You plug in your address (confirming the exact resolved location) and your rough annual energy usage, and it spits out:

- A system sized to your actual usage using your roof's best-facing side(s) first (not maxed out to the whole roof), with a current leading panel wattage (via Google's Solar API when available, or a rough usage-based estimate otherwise)
- The panel count, system size, and estimated yearly production for that roof, plus the roof's whole-buildable-area ceiling shown separately for context
- A plain verdict (covers everything with credit to spare, covers part of your bill, or the roof's too small to make a real dent) plus a disclaimer
- Rough installation cost and payback period, and estimated CO₂ offset, both fully sourced. See [ANALYSIS_METHODOLOGY.md](ANALYSIS_METHODOLOGY.md) for exactly how every number here is calculated
- A one-card "bottom line": a verdict-colored headline, one line of reasoning tied to your actual numbers (stale imagery, a fallback estimate with no roof data, an out-of-scope system size), and a single next move: get quotes, or skip it for now

Simple. That's the whole idea.

---

## Architecture

The app is split into two pieces:

- **`backend/`**: a FastAPI service. `main.py` exposes `/geocode` and `/assess` endpoints, `advisor.py` holds the classification/bottom-line logic, `weather.py` calls out to Nominatim for geocoding, and `solar.py` calls Google's Solar API to size a system from the roof and build the verdict report.
- **`frontend/`**: a React + Vite app that walks the user through a conversational, one-question-at-a-time form and calls the backend to render the results.

## How to run it

```powershell
# from the repo root, starts both servers
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

### Setting up Google Solar API (optional, roof-level solar data)

The app works fine without this key; `/assess` just omits the "Roof & Solar
Potential" section. To enable it:

1. In [Google Cloud Console](https://console.cloud.google.com/), create (or pick) a project with billing enabled.
2. Enable the **Solar API** for that project.
3. Create an API key and restrict it (under "API restrictions") to the Solar API only. The key is only ever used server-side, so no HTTP referrer restriction is needed, but consider an IP restriction to your backend host in production.
4. Add it to `backend/.env`:
   ```
   GOOGLE_SOLAR_API_KEY=your-key-here
   ```
5. Coverage isn't global: many rural addresses will return no imagery. Test against a known-covered address (e.g. a major North American downtown core) to confirm the setup works, then test elsewhere to see the graceful "not available for this address" path.

### Running the tests

```bash
cd backend
python -m pytest test_advisor.py test_solar.py test_main.py -v
```

---

## Under the hood

The code walkthrough lives in [ARCHITECTURE.md](ARCHITECTURE.md), and every calculation and data source is documented in [ANALYSIS_METHODOLOGY.md](ANALYSIS_METHODOLOGY.md).

---

## Status

Working prototype. Uses live geocoding and, where configured, live roof imagery. No mobile optimization yet. More coming if there's interest.

---

*Built in Calgary, Alberta.*
