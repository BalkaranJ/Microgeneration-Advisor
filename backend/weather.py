"""
External API calls — Nominatim for geocoding.
"""

import httpx


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


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
