"""
Extracts electricity usage data from a photo of a utility bill using Claude's vision API.
"""
import base64
import json
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from anthropic import Anthropic

client = Anthropic()

ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

BILL_SCHEMA = {
    "type": "object",
    "properties": {
        "provider": {
            "type": ["string", "null"],
            "description": "Utility provider name, e.g. Enmax, Atco, or Epcor — or null if not identifiable",
        },
        "period_start": {
            "type": ["string", "null"],
            "description": "Billing period start date in ISO format YYYY-MM-DD, or null if not visible",
        },
        "period_end": {
            "type": ["string", "null"],
            "description": "Billing period end date in ISO format YYYY-MM-DD, or null if not visible",
        },
        "usage_kwh": {
            "type": ["number", "null"],
            "description": "Total electricity usage in kWh for the billing period shown on the bill, or null if not found",
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "notes": {
            "type": "string",
            "description": "Brief note about anything unclear or ambiguous; empty string if none",
        },
    },
    "required": ["provider", "period_start", "period_end", "usage_kwh", "confidence", "notes"],
    "additionalProperties": False,
}

EXTRACTION_PROMPT = (
    "This is a photo of a Canadian residential electricity bill (likely from Enmax, "
    "Atco, or Epcor). Extract the provider name, the billing period start and end "
    "dates, and the total electricity usage in kWh for that billing period. If any "
    "field is not visible or you are unsure, use null for it and lower your confidence."
)


class BillExtractionError(Exception):
    pass


def _annualize(usage_kwh, period_start, period_end):
    if usage_kwh is None or not period_start or not period_end:
        return None
    try:
        start = date.fromisoformat(period_start)
        end = date.fromisoformat(period_end)
    except ValueError:
        return None
    days = (end - start).days
    if days <= 0:
        return None
    return round(usage_kwh / days * 365)


def extract_bill_usage(image_bytes: bytes, media_type: str) -> dict:
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise BillExtractionError(
            "Unsupported image type. Please upload a JPEG, PNG, WEBP, or GIF photo of your bill."
        )

    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=1024,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": BILL_SCHEMA},
            },
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": encoded},
                        },
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
        )
    except Exception as e:
        raise BillExtractionError(
            "Could not read the bill image. Please try again or enter your usage manually."
        ) from e

    if response.stop_reason == "refusal":
        raise BillExtractionError(
            "Could not process this image. Please try again or enter your usage manually."
        )

    text_block = next((b.text for b in response.content if b.type == "text"), None)
    if not text_block:
        raise BillExtractionError("Could not read any data from the bill. Please enter your usage manually.")

    data = json.loads(text_block)
    annual_usage_kwh = _annualize(data["usage_kwh"], data["period_start"], data["period_end"])

    return {
        "provider": data["provider"],
        "period_start": data["period_start"],
        "period_end": data["period_end"],
        "usage_kwh": data["usage_kwh"],
        "annual_usage_kwh": annual_usage_kwh,
        "confidence": data["confidence"],
        "notes": data["notes"],
    }
