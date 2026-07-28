"""
External API calls — Nominatim for geocoding, Open-Meteo for weather data.
"""

import httpx
from advisor import WeatherProfile


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def geocode(address: str) -> dict:
    """Return lat, lon, and display_name for a given address string."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "MicrogenerationAdvisor/1.0"},
            timeout=10,
        )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError("Address not found. Try being more specific.")
    top = results[0]
    return {
        "lat":          float(top["lat"]),
        "lon":          float(top["lon"]),
        "display_name": top["display_name"],
    }


async def fetch_weather(lat: float, lon: float, location_name: str) -> WeatherProfile:
    """
    Pull real solar and wind data from Open-Meteo for the given coordinates
    and return a WeatherProfile the scoring classes can use.

    We request the past 365 days of hourly data and average it to get
    stable indicators rather than using a single snapshot.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            OPEN_METEO_URL,
            params={
                "latitude":              lat,
                "longitude":             lon,
                "hourly":                "shortwave_radiation,cloudcover,windspeed_10m,windgusts_10m",
                "past_days":             7,
                "forecast_days":         1,
                "timezone":              "auto",
            },
            timeout=15,
        )
    response.raise_for_status()
    data = response.json()["hourly"]

    radiation   = [v for v in data["shortwave_radiation"] if v is not None]
    cloud       = [v for v in data["cloudcover"]          if v is not None]
    wind_speed  = [v for v in data["windspeed_10m"]       if v is not None]
    wind_gusts  = [v for v in data["windgusts_10m"]       if v is not None]

    avg_radiation  = sum(radiation)  / len(radiation)   if radiation  else 0
    avg_cloud      = sum(cloud)      / len(cloud)        if cloud      else 0
    avg_wind_speed = sum(wind_speed) / len(wind_speed)  if wind_speed else 0
    avg_wind_gusts = sum(wind_gusts) / len(wind_gusts)  if wind_gusts else 0

    # Scale radiation (0-1000 W/m²) to a 0-100 solar indicator
    solar_indicator = min(100, avg_radiation / 10)

    # Scale wind speed (0-100 km/h typical max) to a 0-100 wind indicator
    wind_indicator = min(100, avg_wind_speed)

    # Cloud cover is already 0-100
    cloud_cover = avg_cloud

    # Wind consistency: how close average speed is to peak gusts
    # High consistency means wind is steady, not just occasional bursts
    if avg_wind_gusts > 0:
        wind_consistency = min(100, (avg_wind_speed / avg_wind_gusts) * 100)
    else:
        wind_consistency = 0

    return WeatherProfile(
        location=location_name,
        solar_indicator=solar_indicator,
        wind_indicator=wind_indicator,
        cloud_cover=cloud_cover,
        wind_consistency=wind_consistency,
    )
