"""Australian registration lookup and number-plate image extraction."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree


REGCHECK_ENDPOINT = "https://www.regcheck.org.uk/api/reg.asmx/CheckAustralia"
OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
AUSTRALIAN_STATES = ("VIC", "NSW", "QLD", "SA", "WA", "TAS", "ACT", "NT")


class VehicleLookupError(RuntimeError):
    """A safe, user-facing vehicle lookup failure."""


@dataclass(frozen=True)
class PlateReading:
    registration: str
    state: str | None


def normalize_registration(value: str) -> str:
    registration = re.sub(r"[^A-Z0-9]", "", (value or "").upper())
    if not 2 <= len(registration) <= 8:
        raise VehicleLookupError("Enter a valid Australian registration number.")
    return registration


def normalize_state(value: str) -> str:
    state = (value or "").strip().upper()
    if state not in AUSTRALIAN_STATES:
        raise VehicleLookupError("Select an Australian state or territory.")
    return state


def _request_json(request: Request, timeout: int = 30) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise VehicleLookupError(f"Lookup service returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise VehicleLookupError("Lookup service is currently unreachable.") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise VehicleLookupError("Lookup service returned an invalid response.") from exc


def lookup_australia(
    registration: str,
    state: str,
    username: str,
    *,
    timeout: int = 30,
) -> dict[str, Any]:
    """Return RegCheck's Australian vehicle JSON using server-side credentials."""
    registration = normalize_registration(registration)
    state = normalize_state(state)
    if not username:
        raise VehicleLookupError("RegCheck is not configured on the server.")

    query = urlencode(
        {
            "RegistrationNumber": registration,
            "State": state,
            "username": username,
        }
    )
    request = Request(f"{REGCHECK_ENDPOINT}?{query}", headers={"Accept": "text/xml"})
    try:
        with urlopen(request, timeout=timeout) as response:
            xml_payload = response.read()
    except HTTPError as exc:
        raise VehicleLookupError(f"RegCheck returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise VehicleLookupError("RegCheck is currently unreachable.") from exc

    try:
        root = ElementTree.fromstring(xml_payload)
        node = root.find("{http://regcheck.org.uk}vehicleJson")
        if node is None or not node.text:
            message = root.findtext("{http://regcheck.org.uk}Error")
            raise VehicleLookupError(message or "No vehicle was returned for that registration.")
        vehicle = json.loads(node.text)
    except (ElementTree.ParseError, json.JSONDecodeError) as exc:
        raise VehicleLookupError("RegCheck returned an invalid vehicle response.") from exc

    if not isinstance(vehicle, dict) or vehicle.get("Error"):
        raise VehicleLookupError(str(vehicle.get("Error") or "Vehicle lookup failed."))

    vehicle["RegistrationNumber"] = registration
    vehicle["State"] = state
    return vehicle


def extract_plate_from_image(
    image_path: str,
    api_key: str,
    *,
    model: str = "gpt-4o-mini",
    timeout: int = 30,
) -> PlateReading:
    """Read one Australian registration plate and optional state from an image."""
    if not api_key:
        raise VehicleLookupError("OpenAI image reading is not configured on the server.")
    path = Path(image_path)
    if not path.is_file():
        raise VehicleLookupError("The number-plate image could not be read.")

    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Read the single Australian registration plate in this image. "
                            "Return JSON only: registration (letters/numbers, no spaces) and "
                            "state (VIC, NSW, QLD, SA, WA, TAS, ACT, NT, or null). "
                            "If uncertain, return an empty registration."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{encoded}"},
                    },
                ],
            }
        ],
    }
    request = Request(
        OPENAI_CHAT_ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    response = _request_json(request, timeout=timeout)
    try:
        result = json.loads(response["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise VehicleLookupError("The plate could not be read confidently.") from exc

    registration = result.get("registration", "")
    if not registration:
        raise VehicleLookupError("The plate could not be read confidently; enter it manually.")
    detected_state = result.get("state")
    return PlateReading(
        registration=normalize_registration(registration),
        state=normalize_state(detected_state) if detected_state else None,
    )


def _text_value(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("CurrentTextValue") or value.get("CurrentValue") or "")
    return str(value or "")


def vehicle_context(vehicle: dict[str, Any]) -> str:
    """Create compact grounding context for subsequent mechanical questions."""
    fields = {
        "registration": vehicle.get("RegistrationNumber"),
        "state": vehicle.get("State"),
        "VIN": vehicle.get("VIN") or vehicle.get("Vin"),
        "description": vehicle.get("Description"),
        "make": _text_value(vehicle.get("CarMake") or vehicle.get("MakeDescription")),
        "model": _text_value(vehicle.get("CarModel") or vehicle.get("ModelDescription")),
        "year": vehicle.get("RegistrationYear") or vehicle.get("ManufactureYearFrom"),
        "engine": _text_value(vehicle.get("EngineSize")),
        "engine code": _text_value(vehicle.get("EngineCode")),
        "transmission": _text_value(vehicle.get("Transmission")),
        "fuel": _text_value(vehicle.get("FuelType")),
    }
    return "; ".join(f"{key}: {value}" for key, value in fields.items() if value)


def vehicle_summary(vehicle: dict[str, Any]) -> str:
    context = vehicle_context(vehicle)
    vin = vehicle.get("VIN") or vehicle.get("Vin")
    vin_note = "" if vin else "\n\n_VIN was not supplied by RegCheck for this lookup._"
    return (
        f"**Vehicle selected:** {context}{vin_note}"
        if context
        else f"**Vehicle selected.**{vin_note}"
    )
