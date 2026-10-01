import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def limits_enabled() -> bool:
    return os.environ.get("RATE_LIMITS_ENABLED", "true").lower() != "false"


def client_ip(request: Request) -> str:
    if os.environ.get("TRUST_PROXY", "false").lower() == "true":
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, name: str, per_ip: int, per_ip_window_s: int, global_cap: int, global_window_s: int = 86400):
        self.name = name
        self.per_ip = per_ip
        self.per_ip_window_s = per_ip_window_s
        self.global_cap = global_cap
        self.global_window_s = global_window_s
        self._hits: dict[str, deque] = defaultdict(deque)
        self._global: deque = deque()
        self._lock = threading.Lock()

    def _limits(self) -> tuple[int, int]:
        key = self.name.upper()
        return (
            _env_int(f"RATE_LIMIT_{key}_PER_IP", self.per_ip),
            _env_int(f"RATE_LIMIT_{key}_GLOBAL_DAILY", self.global_cap),
        )

    @staticmethod
    def _trim(window: deque, cutoff: float) -> None:
        while window and window[0] <= cutoff:
            window.popleft()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._global.clear()

    def __call__(self, request: Request) -> None:
        if not limits_enabled():
            return
        per_ip, global_cap = self._limits()
        now = time.monotonic()
        ip = client_ip(request)
        with self._lock:
            self._trim(self._global, now - self.global_window_s)
            if len(self._global) >= global_cap:
                raise HTTPException(
                    status_code=503,
                    detail="This free demo has hit its daily limit. Please try again tomorrow.",
                )
            hits = self._hits[ip]
            self._trim(hits, now - self.per_ip_window_s)
            if len(hits) >= per_ip:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests from your connection. Please try again later.",
                    headers={"Retry-After": str(self.per_ip_window_s)},
                )
            hits.append(now)
            self._global.append(now)
            if len(self._hits) > 10000:
                for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - self.per_ip_window_s]:
                    del self._hits[key]


geocode_limiter = RateLimiter("geocode", per_ip=60, per_ip_window_s=3600, global_cap=5000)
assess_limiter = RateLimiter("assess", per_ip=10, per_ip_window_s=3600, global_cap=300)
roof_image_limiter = RateLimiter("roof_image", per_ip=20, per_ip_window_s=3600, global_cap=300)
extract_bill_limiter = RateLimiter("extract_bill", per_ip=3, per_ip_window_s=86400, global_cap=50)

ALL_LIMITERS = [geocode_limiter, assess_limiter, roof_image_limiter, extract_bill_limiter]
