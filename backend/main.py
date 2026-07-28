"""
FastAPI backend — exposes three endpoints:
  POST /geocode        address string -> lat/lon/display_name
  POST /assess         full project inputs -> scored results
  POST /extract-bill   utility bill photo -> extracted usage data
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from advisor import (
    MicrogenerationProject,
    ReadinessAdvisor,
    InvalidProjectInputError,
    estimate_target_system_size_kw,
)
from weather import geocode
from bill_extractor import extract_bill_usage, BillExtractionError
from solar import get_building_solar_summary, effective_rate_per_kwh
from roof_image import fetch_roof_image, RoofImageError

MAX_BILL_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GeocodeRequest(BaseModel):
    address: str


class MonthlyHistoryItem(BaseModel):
    month: str
    kwh: float | None = None
    cost: float | None = None


class AssessRequest(BaseModel):
    location: str
    lat: float
    lon: float
    annual_usage_kwh: float
    electricity_charge_incl_gst: float | None = None
    bill_period_usage_kwh: float | None = None
    monthly_usage_history: list[MonthlyHistoryItem] | None = None


@app.post("/geocode")
async def geocode_address(body: GeocodeRequest):
    try:
        result = await geocode(body.address)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail="Geocoding service unavailable.")


@app.post("/assess")
async def assess(body: AssessRequest):
    try:
        usage_based_fallback_kw = estimate_target_system_size_kw(body.annual_usage_kwh)
        rate_per_kwh = effective_rate_per_kwh(
            body.electricity_charge_incl_gst, body.bill_period_usage_kwh
        )

        monthly_usage_history = (
            [item.model_dump() for item in body.monthly_usage_history]
            if body.monthly_usage_history else None
        )
        roof_solar_potential = await get_building_solar_summary(
            body.lat, body.lon, body.annual_usage_kwh, rate_per_kwh, monthly_usage_history
        )

        if roof_solar_potential.get("available"):
            effective_system_size_kw = roof_solar_potential["system_size_kw"]
            system_size_basis = "roof_matched"
        else:
            effective_system_size_kw = usage_based_fallback_kw
            system_size_basis = "usage_estimate"

        project = MicrogenerationProject(
            location=body.location,
            annual_usage_kwh=body.annual_usage_kwh,
            system_size_kw=effective_system_size_kw,
        )

        result = ReadinessAdvisor().assess(project)
        result["location"] = body.location
        result["coordinates"] = {"lat": body.lat, "lon": body.lon}
        result["roof_solar_potential"] = roof_solar_potential
        result["recommended_system_size_kw"] = effective_system_size_kw
        result["system_size_basis"] = system_size_basis
        return result

    except InvalidProjectInputError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong on our end.")


@app.get("/roof-image")
async def roof_image(lat: float, lon: float):
    try:
        image_bytes = await fetch_roof_image(lat, lon)
    except RoofImageError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return Response(content=image_bytes, media_type="image/png")


@app.post("/extract-bill")
async def extract_bill(file: UploadFile = File(...)):
    image_bytes = await file.read()
    if len(image_bytes) > MAX_BILL_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large. Please upload a photo under 10MB.")

    try:
        return extract_bill_usage(image_bytes, file.content_type)
    except BillExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
