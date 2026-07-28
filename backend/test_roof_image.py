"""
Unit tests for backend/roof_image.py — Google Static Maps proxy. No live
API call is made; all HTTP is faked.
"""

import unittest
from unittest.mock import patch

import roof_image
from roof_image import RoofImageError, fetch_roof_image


class _FakeResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content


class _FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


class TestFetchRoofImage(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_raises_without_http_call(self):
        with patch.object(roof_image.os, "getenv", return_value=None), \
             patch.object(roof_image.httpx, "AsyncClient") as mock_client_cls:
            with self.assertRaises(RoofImageError):
                await fetch_roof_image(51.05, -114.07, api_key=None)
            mock_client_cls.assert_not_called()

    async def test_200_returns_image_bytes(self):
        fake_response = _FakeResponse(200, content=b"\x89PNG\r\n")
        with patch.object(roof_image.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            data = await fetch_roof_image(51.05, -114.07, api_key="test-key")
        self.assertEqual(data, b"\x89PNG\r\n")

    async def test_non_200_raises(self):
        fake_response = _FakeResponse(403)
        with patch.object(roof_image.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(fake_response)):
            with self.assertRaises(RoofImageError):
                await fetch_roof_image(51.05, -114.07, api_key="test-key")

    async def test_network_error_raises(self):
        fake_client = _FakeAsyncClient(exc=roof_image.httpx.ConnectTimeout("timed out"))
        with patch.object(roof_image.httpx, "AsyncClient", lambda *a, **kw: fake_client):
            with self.assertRaises(RoofImageError):
                await fetch_roof_image(51.05, -114.07, api_key="test-key")


if __name__ == "__main__":
    unittest.main()
