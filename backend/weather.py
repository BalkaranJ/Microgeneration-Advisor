"""
External API calls: Nominatim for geocoding, with Photon as a fallback.
"""

import os

import httpx


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
CANADA_BBOX = "-141,41,-52,84"


def _user_agent() -> str:
    contact = os.environ.get("GEOCODER_CONTACT", "").strip()
    return f"SolarFit/1.0 ({contact})" if contact else "SolarFit/1.0"


async def _nominatim(address: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": _user_agent()},
            timeout=10,
        )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    top = results[0]
    return {
        "lat":          float(top["lat"]),
        "lon":          float(top["lon"]),
        "display_name": top["display_name"],
    }


def _photon_display_name(props: dict) -> str:
    street = " ".join(p for p in (props.get("housenumber"), props.get("street")) if p)
    parts = [
        props.get("name") if props.get("name") and props.get("name") != street else None,
        street or None,
        props.get("city") or props.get("district"),
        props.get("state"),
        props.get("postcode"),
        props.get("country"),
    ]
    return ", ".join(p for p in parts if p)


async def _photon(address: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            PHOTON_URL,
            params={"q": address, "limit": 1, "lang": "en", "bbox": CANADA_BBOX},
            headers={"User-Agent": _user_agent()},
            timeout=10,
        )
    response.raise_for_status()
    features = response.json().get("features") or []
    if not features:
        return None
    top = features[0]
    lon, lat = top["geometry"]["coordinates"]
    return {
        "lat":          float(lat),
        "lon":          float(lon),
        "display_name": _photon_display_name(top.get("properties", {})),
    }


async def geocode(address: str) -> dict:
    """Return lat, lon, and display_name for a given address string."""
    result = None
    last_error = None
    for provider in (_nominatim, _photon):
        try:
            result = await provider(address)
        except (httpx.HTTPError, KeyError, ValueError) as e:
            last_error = e
            continue
        if result:
            return result
    if last_error is not None:
        raise last_error
    raise ValueError("Address not found. Try being more specific.")
