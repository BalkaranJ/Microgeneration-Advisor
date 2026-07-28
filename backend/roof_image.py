"""
Google Static Maps API — a satellite image centered on the assessed
property. Fetched server-side (never returned to the browser as a raw
URL) so GOOGLE_SOLAR_API_KEY is never exposed to the client.
"""
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

STATIC_MAPS_URL = "https://maps.googleapis.com/maps/api/staticmap"
REQUEST_TIMEOUT = 15
IMAGE_ZOOM = 20
IMAGE_SIZE = "640x400"
IMAGE_SCALE = 2


class RoofImageError(Exception):
    pass


async def fetch_roof_image(lat: float, lon: float, api_key: Optional[str] = None) -> bytes:
    """GETs a satellite PNG centered on lat/lon. Raises RoofImageError on any failure."""
    key = api_key or os.getenv("GOOGLE_SOLAR_API_KEY")
    if not key:
        raise RoofImageError("Roof imagery isn't configured for this deployment.")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                STATIC_MAPS_URL,
                params={
                    "center": f"{lat},{lon}",
                    "zoom": IMAGE_ZOOM,
                    "size": IMAGE_SIZE,
                    "scale": IMAGE_SCALE,
                    "maptype": "satellite",
                    "key": key,
                },
                timeout=REQUEST_TIMEOUT,
            )
    except httpx.RequestError as e:
        raise RoofImageError(str(e)) from e

    if response.status_code != 200:
        raise RoofImageError(f"Static Maps request failed with status {response.status_code}.")
    return response.content
