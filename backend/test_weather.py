import unittest
from unittest.mock import AsyncMock, patch

import httpx

import weather

GOOD = {"lat": 51.0, "lon": -114.0, "display_name": "x"}


class GeocodeFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_nominatim_when_it_succeeds(self):
        with patch("weather._nominatim", new=AsyncMock(return_value=GOOD)), \
             patch("weather._photon", new=AsyncMock(side_effect=AssertionError)):
            self.assertEqual(await weather.geocode("a"), GOOD)

    async def test_falls_back_to_photon_when_nominatim_errors(self):
        with patch("weather._nominatim", new=AsyncMock(side_effect=httpx.ConnectError("blocked"))), \
             patch("weather._photon", new=AsyncMock(return_value=GOOD)):
            self.assertEqual(await weather.geocode("a"), GOOD)

    async def test_falls_back_to_photon_when_nominatim_finds_nothing(self):
        with patch("weather._nominatim", new=AsyncMock(return_value=None)), \
             patch("weather._photon", new=AsyncMock(return_value=GOOD)):
            self.assertEqual(await weather.geocode("a"), GOOD)

    async def test_not_found_everywhere_raises_value_error(self):
        with patch("weather._nominatim", new=AsyncMock(return_value=None)), \
             patch("weather._photon", new=AsyncMock(return_value=None)):
            with self.assertRaises(ValueError):
                await weather.geocode("a")

    async def test_both_providers_failing_raises_http_error(self):
        err = httpx.ConnectError("down")
        with patch("weather._nominatim", new=AsyncMock(side_effect=err)), \
             patch("weather._photon", new=AsyncMock(side_effect=err)):
            with self.assertRaises(httpx.HTTPError):
                await weather.geocode("a")

    def test_photon_display_name_formats_address(self):
        props = {"housenumber": "135", "street": "Taracove Landing NE", "city": "Calgary",
                 "state": "Alberta", "postcode": "T3J 0H5", "country": "Canada"}
        self.assertEqual(
            weather._photon_display_name(props),
            "135 Taracove Landing NE, Calgary, Alberta, T3J 0H5, Canada",
        )


if __name__ == "__main__":
    unittest.main()
