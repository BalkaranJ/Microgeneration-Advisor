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

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_MEDIA_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf"}

MONTHLY_HISTORY_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "month": {
            "type": "string",
            "description": (
                "The month this data point represents, in YYYY-MM format (e.g. 2025-06). "
                "Bar charts often label only a month abbreviation — infer the calendar year "
                "from the bill date and the sequence of surrounding months."
            ),
        },
        "kwh": {"type": ["number", "null"], "description": "kWh usage for that month, or null if not legible"},
        "cost": {
            "type": ["number", "null"],
            "description": (
                "Dollar amount billed for that month, or null if not legible. Many bills' "
                "history graphs only plot kWh (no accompanying monthly dollar figure) — "
                "null is expected and fine in that case."
            ),
        },
    },
    "required": ["month", "kwh", "cost"],
    "additionalProperties": False,
}

BILL_SCHEMA = {
    "type": "object",
    "properties": {
        "provider": {
            "type": ["string", "null"],
            "description": "Utility provider name, e.g. Enmax, Atco, or Epcor — or null if not identifiable",
        },
        "bill_date": {
            "type": ["string", "null"],
            "description": "The bill's issue/statement date (often labelled 'Bill Date'), in ISO format YYYY-MM-DD, or null",
        },
        "period_start": {
            "type": ["string", "null"],
            "description": "Current billing period start date in ISO format YYYY-MM-DD, or null if not visible",
        },
        "period_end": {
            "type": ["string", "null"],
            "description": "Current billing period end date in ISO format YYYY-MM-DD, or null if not visible",
        },
        "usage_kwh": {
            "type": ["number", "null"],
            "description": (
                "The metered electricity usage in kWh for the current billing period, from the "
                "meter reading table (often labeled 'USE(kWh)'). Do not use the (usually larger) "
                "kWh figure quoted on the Energy Charge line itself, which may include additional "
                "unaccounted-for energy/line-loss kWh added on top of the meter reading."
            ),
        },
        "avg_cost_per_day": {
            "type": ["number", "null"],
            "description": (
                "The average cost per day (e.g. 'Avg. Cost/Day' or 'AV COST / DAY') found "
                "specifically within the ELECTRICITY section of the bill, near the electricity "
                "usage history graph. Bills that combine multiple utilities (electricity, water, "
                "wastewater, stormwater, waste/recycling) often print a similar avg-cost-per-day "
                "figure for each utility separately — ignore any that are not under the electricity "
                "section."
            ),
        },
        "electricity_charge_excl_gst": {
            "type": ["number", "null"],
            "description": (
                "The 'Electricity' charge line item (usually under an ENMAX/Electricity charges "
                "section), BEFORE GST/tax — this is normally the number printed directly next to "
                "'Electricity' (e.g. 'Electricity ....(GST: $7.47) $149.42' — extract 149.42 here)."
            ),
        },
        "electricity_charge_gst": {
            "type": ["number", "null"],
            "description": (
                "The GST/tax dollar amount tied to the electricity charge, often shown in "
                "parentheses right next to the Electricity line (e.g. 'Electricity ....(GST: "
                "$7.47) $149.42' — extract 7.47 here). This GST is usually added on top of the "
                "electricity charge separately, not already folded into it."
            ),
        },
        "monthly_history": {
            "type": "array",
            "description": (
                "Data points read from the monthly consumption history graph/chart on the bill "
                "(commonly showing roughly the last 12-13 months of $ and kWh side by side). "
                "One entry per visible month bar. Empty array if no such graph is present."
            ),
            "items": MONTHLY_HISTORY_ITEM_SCHEMA,
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "notes": {
            "type": "string",
            "description": "Brief note about anything unclear or ambiguous; empty string if none",
        },
    },
    "required": [
        "provider",
        "bill_date",
        "period_start",
        "period_end",
        "usage_kwh",
        "avg_cost_per_day",
        "electricity_charge_excl_gst",
        "electricity_charge_gst",
        "monthly_history",
        "confidence",
        "notes",
    ],
    "additionalProperties": False,
}

EXTRACTION_PROMPT = (
    "This is a photo or PDF of a Canadian residential utilities bill (likely from Enmax, Atco, "
    "or Epcor). Some of these bills combine multiple services on one statement — electricity, "
    "water, wastewater, stormwater, waste/recycling, natural gas — sometimes across several "
    "pages, with the electricity usage details and history graph on a different page than the "
    "billing summary. Only extract data from the ELECTRICITY section; ignore charges, usage "
    "figures, and avg-cost-per-day values that belong to water or any other non-electricity "
    "service.\n\n"
    "Extract the following:\n"
    "1. The provider name.\n"
    "2. The bill's issue/statement date (often labelled 'Bill Date' or 'Current Bill Date', "
    "sometimes printed like '2026 June 15' — convert to ISO YYYY-MM-DD).\n"
    "3. The current billing period's start/end dates (from the meter reading table's "
    "'Previous Reading Date' / 'Present Reading Date' — these are frequently printed WITHOUT "
    "a year, e.g. 'APR 29' / 'MAY 27'; infer the year from the bill's issue date) and the "
    "metered usage in kWh for that period (the 'USE(kWh)' meter reading, not the — usually "
    "larger — kWh figure on the Energy Charge line, which may include extra unaccounted-for "
    "energy/line-loss kWh).\n"
    "4. The average cost per day, specifically from the electricity section (see field "
    "description).\n"
    "5. The 'Electricity' charge line, split into its pre-GST amount and its GST amount — these "
    "are usually printed together on one line, e.g. 'Electricity ....(GST: $7.47) $149.42', "
    "where $149.42 is BEFORE GST and $7.47 is the GST added on top (see field descriptions).\n"
    "6. Every data point from the electricity usage history graph/bar chart, if present "
    "(commonly showing roughly the last 12-13 months of kWh, sometimes with a matching dollar "
    "figure per month, sometimes kWh-only). Estimate each bar's kWh value against the graph's "
    "printed y-axis gridlines if there is no numeric label directly on the bar, and lower your "
    "confidence accordingly. Infer the calendar year for each month from context — bars are "
    "often labeled with just a month abbreviation (sometimes with small year markers like "
    "\"'25\"/\"'26\" beneath the axis) — use YYYY-MM format for each month.\n\n"
    "If any field is not visible, belongs to a different utility, or you are unsure, use null "
    "for it (or an empty array for the history) and lower your confidence."
)


class BillExtractionError(Exception):
    pass


def _parse_month(month_str):
    try:
        year_str, month_num_str = month_str.split("-")
        return int(year_str), int(month_num_str)
    except (ValueError, AttributeError, TypeError):
        return None


def _annual_from_history(monthly_history, bill_date):
    """Sum (or extrapolate from) the monthly history graph, anchored at the bill date."""
    by_month = {}
    for entry in monthly_history:
        ym = _parse_month(entry.get("month"))
        if ym is None or entry.get("kwh") is None:
            continue
        by_month.setdefault(ym, entry["kwh"])  # keep first reading of a repeated month

    if bill_date:
        try:
            parsed = date.fromisoformat(bill_date)
            cutoff = (parsed.year, parsed.month)
            by_month = {ym: kwh for ym, kwh in by_month.items() if ym <= cutoff}
        except ValueError:
            pass

    latest_months = sorted(by_month.items(), reverse=True)[:12]

    if len(latest_months) >= 12:
        total = round(sum(kwh for _, kwh in latest_months))
        return total, "monthly_history", len(latest_months)
    if len(latest_months) >= 3:
        avg = sum(kwh for _, kwh in latest_months) / len(latest_months)
        return round(avg * 12), "monthly_history_estimated", len(latest_months)
    return None, None, 0


def _annual_from_current_period(usage_kwh, period_start, period_end):
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
            "Unsupported file type. Please upload a JPEG, PNG, WEBP, or GIF photo of your "
            "bill, or a PDF of your e-bill."
        )

    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")

    if media_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": encoded},
        }
    else:
        content_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }

    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=2048,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": BILL_SCHEMA},
            },
            messages=[
                {
                    "role": "user",
                    "content": [
                        content_block,
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

    annual_usage_kwh, annual_source, months_used = _annual_from_history(
        data["monthly_history"], data["bill_date"]
    )
    if annual_usage_kwh is None:
        annual_usage_kwh = _annual_from_current_period(
            data["usage_kwh"], data["period_start"], data["period_end"]
        )
        annual_source = "current_period_extrapolated" if annual_usage_kwh is not None else None

    excl_gst = data["electricity_charge_excl_gst"]
    gst = data["electricity_charge_gst"]
    incl_gst = round(excl_gst + gst, 2) if excl_gst is not None and gst is not None else None

    return {
        "provider": data["provider"],
        "bill_date": data["bill_date"],
        "period_start": data["period_start"],
        "period_end": data["period_end"],
        "usage_kwh": data["usage_kwh"],
        "avg_cost_per_day": data["avg_cost_per_day"],
        "electricity_charge_excl_gst": excl_gst,
        "electricity_charge_gst": gst,
        "electricity_charge_incl_gst": incl_gst,
        "monthly_history": data["monthly_history"],
        "annual_usage_kwh": annual_usage_kwh,
        "annual_source": annual_source,
        "annual_source_months": months_used,
        "confidence": data["confidence"],
        "notes": data["notes"],
    }
