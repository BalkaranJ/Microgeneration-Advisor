import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import main
from ratelimit import ALL_LIMITERS, RateLimiter


class RateLimitingTests(unittest.TestCase):
    def setUp(self):
        self._env = patch.dict(os.environ, {"RATE_LIMITS_ENABLED": "true"})
        self._env.start()
        for limiter in ALL_LIMITERS:
            limiter.reset()
        self.client = TestClient(main.app)

    def tearDown(self):
        self._env.stop()
        for limiter in ALL_LIMITERS:
            limiter.reset()

    def test_per_ip_limit_returns_429(self):
        body = {"address": "Calgary, AB"}
        with patch("main.geocode", new=AsyncMock(return_value={"lat": 1, "lon": 2, "display_name": "x"})):
            with patch.dict(os.environ, {"RATE_LIMIT_GEOCODE_PER_IP": "2"}):
                self.assertEqual(self.client.post("/geocode", json=body).status_code, 200)
                self.assertEqual(self.client.post("/geocode", json=body).status_code, 200)
                response = self.client.post("/geocode", json=body)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

    def test_global_daily_cap_returns_503(self):
        limiter = RateLimiter("probe", per_ip=100, per_ip_window_s=3600, global_cap=1)
        request = type("R", (), {"client": type("C", (), {"host": "1.2.3.4"})(), "headers": {}})()
        limiter(request)
        with self.assertRaises(Exception) as ctx:
            limiter(request)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_disabling_limits_allows_unlimited_requests(self):
        body = {"address": "Calgary, AB"}
        with patch.dict(os.environ, {"RATE_LIMITS_ENABLED": "false", "RATE_LIMIT_GEOCODE_PER_IP": "1"}):
            with patch("main.geocode", new=AsyncMock(return_value={"lat": 1, "lon": 2, "display_name": "x"})):
                for _ in range(5):
                    self.assertEqual(self.client.post("/geocode", json=body).status_code, 200)


class DeploySwitchTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_health_endpoint(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_bill_upload_disabled_returns_503_without_calling_extractor(self):
        with patch.dict(os.environ, {"ENABLE_BILL_UPLOAD": "false"}):
            with patch("main.extract_bill_usage") as mock_extract:
                response = self.client.post("/extract-bill", files={"file": ("b.png", b"x", "image/png")})
        self.assertEqual(response.status_code, 503)
        mock_extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
