import httpx

from framework import config


class RestClient:
    def __init__(self, base_url=config.REST_URL, timeout=5):
        self.http = httpx.Client(base_url=base_url, timeout=timeout)

    def get_venues(self) -> httpx.Response:
        return self.http.get("/api/venues")

    def get_listings(self) -> httpx.Response:
        return self.http.get("/api/listings")

    def close(self):
        self.http.close()
