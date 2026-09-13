import json
import tempfile
import unittest
from unittest.mock import patch

from ai_mechanic.regcheck import (
    VehicleLookupError,
    extract_plate_from_image,
    lookup_australia,
    normalize_registration,
    vehicle_context,
    vehicle_summary,
)


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return self.body


class RegCheckTests(unittest.TestCase):
    def test_normalizes_registration(self):
        self.assertEqual(normalize_registration(" abc-123 "), "ABC123")

    def test_rejects_bad_state(self):
        with self.assertRaises(VehicleLookupError):
            lookup_australia("ABC123", "XX", "user")

    @patch("ai_mechanic.regcheck.urlopen")
    def test_parses_vehicle_json_and_sends_expected_parameters(self, mocked_open):
        vehicle = {
            "Description": "2010 Toyota RAV4",
            "VIN": "JTMBE33V001234567",
            "CarMake": {"CurrentTextValue": "Toyota"},
            "CarModel": {"CurrentTextValue": "RAV4"},
        }
        xml = (
            '<Vehicle xmlns="http://regcheck.org.uk"><vehicleJson>'
            + json.dumps(vehicle).replace("&", "&amp;")
            + "</vehicleJson></Vehicle>"
        ).encode()
        mocked_open.return_value = FakeResponse(xml)

        result = lookup_australia("abc 123", "vic", "server-user")

        self.assertEqual(result["VIN"], "JTMBE33V001234567")
        self.assertEqual(result["RegistrationNumber"], "ABC123")
        requested_url = mocked_open.call_args.args[0].full_url
        self.assertIn("RegistrationNumber=ABC123", requested_url)
        self.assertIn("State=VIC", requested_url)
        self.assertIn("username=server-user", requested_url)

    def test_vehicle_context_is_compact(self):
        context = vehicle_context(
            {
                "RegistrationNumber": "ABC123",
                "State": "VIC",
                "VIN": "JTMBE33V001234567",
                "CarMake": {"CurrentTextValue": "Toyota"},
                "CarModel": {"CurrentTextValue": "RAV4"},
            }
        )
        self.assertIn("VIN: JTMBE33V001234567", context)
        self.assertIn("make: Toyota", context)

    def test_summary_discloses_missing_vin(self):
        summary = vehicle_summary(
            {"RegistrationNumber": "ABC123", "State": "VIC"}
        )
        self.assertIn("VIN was not supplied", summary)

    @patch("ai_mechanic.regcheck._request_json")
    def test_extracts_plate_and_state_from_image_response(self, mocked_request):
        mocked_request.return_value = {
            "choices": [
                {"message": {"content": '{"registration":"abc 123","state":"VIC"}'}}
            ]
        }
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image:
            image.write(b"test-image")
            image.flush()
            reading = extract_plate_from_image(image.name, "server-api-key")

        self.assertEqual(reading.registration, "ABC123")
        self.assertEqual(reading.state, "VIC")


if __name__ == "__main__":
    unittest.main()
