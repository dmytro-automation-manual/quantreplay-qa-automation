"""HTTP transport. Knows nothing about the simulator API: method + path in, response out."""
import json as jsonlib
import logging
from decimal import Decimal

import httpx

log = logging.getLogger("rest")


class HttpClient:
    def __init__(self, base_url: str, timeout: float = 5):
        self._http = httpx.Client(base_url=base_url, timeout=timeout,
                                  headers={"Accept": "application/json"})

    def request(self, method: str, path: str, json: dict | None = None) -> httpx.Response:
        body = jsonlib.dumps(json, default=_number) if json is not None else None
        log.info(">> %s %s %s", method, path, body or "")
        response = self._http.request(method, path, content=body,
                                      headers={"Content-Type": "application/json"} if body else None)
        log.info("<< %s %s", response.status_code, response.text[:2000])
        return response

    def close(self) -> None:
        self._http.close()


def _number(value):
    """Decimal prices / quantities go out as JSON numbers."""
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")
