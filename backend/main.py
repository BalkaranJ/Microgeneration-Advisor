"""
FastAPI backend — exposes three endpoints:
  POST /geocode        address string -> lat/lon/display_name
  POST /assess         full project inputs -> scored results
  POST /extract-bill   utility bill photo -> extracted usage data
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from advisor import (
    MicrogenerationProject,
    ReadinessAdvisor,
    InvalidProjectInputError,
)
from weather import geocode, fetch_weather
from bill_extractor import extract_bill_usage, BillExtractionError

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


class AssessRequest(BaseModel):
    address: str
    annual_usage_kwh: float
    system_size_kw: float
    customer_type: str


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
        geo = await geocode(body.address)
        weather = await fetch_weather(geo["lat"], geo["lon"], geo["display_name"])

        project = MicrogenerationProject(
            location=geo["display_name"],
            annual_usage_kwh=body.annual_usage_kwh,
            system_size_kw=body.system_size_kw,
            customer_type=body.customer_type,
        )

        advisor = ReadinessAdvisor()
        result = advisor.assess(project, weather)
        result["location"] = geo["display_name"]
        result["coordinates"] = {"lat": geo["lat"], "lon": geo["lon"]}
        return result

    except InvalidProjectInputError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong on our end.")


@app.post("/extract-bill")
async def extract_bill(file: UploadFile = File(...)):
    image_bytes = await file.read()
    if len(image_bytes) > MAX_BILL_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large. Please upload a photo under 10MB.")

    try:
        return extract_bill_usage(image_bytes, file.content_type)
    except BillExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
