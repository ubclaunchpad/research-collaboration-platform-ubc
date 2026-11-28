"""Small OpenAlex API client."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

BASE_URL = "https://api.openalex.org"
# stay well under OpenAlex's request rate limit
MIN_INTERVAL = 0.12
MAX_RETRIES = 4

Fetch = Callable[[str], dict]


class OpenAlexClient:
    def __init__(self, mailto: str, fetch: Fetch | None = None):
        if not mailto:
            raise ValueError("a contact email is required for the polite pool")
        self.mailto = mailto
        self._fetch = fetch or self._http_fetch
        self._last_call = 0.0

    def get(self, path: str, **params: str | int) -> dict:
        query = urllib.parse.urlencode({**params, "mailto": self.mailto})
        return self._fetch(f"{BASE_URL}/{path}?{query}")

    def _http_fetch(self, url: str) -> dict:
        for attempt in range(MAX_RETRIES):
            wait = MIN_INTERVAL - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as err:
                if err.code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(2**attempt)
        raise RuntimeError(f"OpenAlex request kept failing: {url}")
