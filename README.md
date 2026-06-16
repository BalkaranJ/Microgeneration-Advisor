# Microgeneration Readiness Advisor

**by Balkaran Singh Jaswal**

---

## Why this exists

If you've ever tried to figure out whether solar or wind is actually worth it for your property in Alberta, you know the drill — you end up with like 15 tabs open. One site has the utility rules, another has the weather data, another has some government PDF from 2019 that may or may not still apply. It's a lot, and most of it isn't written for regular people.

This app tries to be the starting point that pulls that thinking together in one place. You're not going to walk away with a permit or an engineer's sign-off — that's not what this is. But you *will* get a clear, plain-language read on whether your location even makes sense for solar or wind before you go spend money finding out the hard way.

It's early-stage. The weather data is baked in (not live yet). But the concept works, and that's the point.

---

## What it does

You plug in your location (Alberta cities only for now), pick whether you're thinking solar, wind, or want to compare both, tell it your rough energy usage and proposed system size, and it spits out:

- A suitability score for solar and wind at your location
- A plain-language recommendation based on those scores
- A readiness checklist of things to sort out before you go any further

Simple. That's the whole idea.

---

## How to run it

```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest test_app.py -v
```

Your browser should pop open automatically. If it doesn't, just go to `http://localhost:8501`.

---

## How the code is put together

Here's a plain walkthrough of what's actually happening under the hood — no CS degree required.

### The data

At the top of `app.py` there's a dictionary called `ALBERTA_WEATHER_DATA`. It holds sample solar and wind numbers for six Alberta cities (Calgary, Edmonton, Lethbridge, Red Deer, Medicine Hat, Grande Prairie). In a real version, this would come from a live weather or solar API — but for now it's hardcoded so the app runs without any external dependencies.

### The project object — `MicrogenerationProject`

When you hit "Run assessment," your inputs (location, technology type, energy usage, system size, customer type) get bundled into a `MicrogenerationProject` object. This class also validates your inputs right away — if you put in zero for energy usage, it raises a custom error (`InvalidProjectInputError`) and the app catches it and shows you a friendly message instead of crashing.

### The weather profile — `WeatherProfile`

Once we know your location, the app grabs the matching entry from the data dictionary and wraps it in a `WeatherProfile` object. This just gives the rest of the code a clean, consistent way to ask for weather values — `get_solar_indicator()`, `get_wind_indicator()`, etc. — rather than poking around in raw dictionaries everywhere.

### The scorers — `SolarSuitabilityScorer` and `WindSuitabilityScorer`

These two classes each do one job: take a weather profile and return a score out of 100. Solar scoring weighs sunlight and subtracts a cloud penalty. Wind scoring combines wind speed and wind consistency. Both inherit from an abstract base class (`SuitabilityScorer`) which means they're interchangeable — the app can loop over both of them and call the same methods without knowing or caring which one it's talking to. That's polymorphism doing its thing.

### The classifier — `ProjectClassifier`

This looks at your proposed system size and categorises the project as small (≤10 kW), medium (≤150 kW), or large/out-of-scope. It also builds a fuller label like "Small residential solar microgeneration concept" by combining the size, customer type, and technology type.

### The facade — `ReadinessAdvisor`

This is the class the UI actually talks to. You hand it a `MicrogenerationProject` and call `.assess()` — and it handles everything else: loading the weather, running both scorers, classifying the project, building the recommendation text, and returning a tidy results dictionary. The UI doesn't need to know any of the steps; it just asks and gets an answer. That's the Facade pattern — one clean entry point that hides all the moving parts.

### The UI — `main()`

Built with [Streamlit](https://streamlit.io/). The inputs are laid out in a two-column form. When you click "Run assessment," it builds the project object, hands it to `ReadinessAdvisor`, and then renders the results — classification, scores (as metrics), recommendation (as an info box), and a readiness checklist (as interactive checkboxes). Any input validation errors get caught and shown as a red error banner instead of blowing up the page.

---

## Status

MVP. Proves the concept. No live data yet, Alberta only, no mobile optimization. More coming if there's interest.

---

*Built in Calgary, Alberta.*
