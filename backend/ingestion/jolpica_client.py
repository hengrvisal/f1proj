"""Rate-limited Jolpica (Ergast-compatible) API client."""

import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1"
MIN_INTERVAL = 1.5  # seconds between requests


class JolpicaClient:
    def __init__(self):
        self._client = httpx.Client(timeout=30.0)
        self._last_request_time = 0.0

    def _rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get(self, path: str, params: dict | None = None) -> dict:
        self._rate_limit()
        url = f"{BASE_URL}/{path}"
        logger.debug("GET %s", url)
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_all(self, path: str, limit: int = 100) -> list[dict]:
        """Fetch all pages from a paginated endpoint."""
        results = []
        offset = 0
        while True:
            data = self.get(path, params={"limit": limit, "offset": offset})
            mr = data["MRData"]
            table_key = [k for k in mr.keys() if k.endswith("Table")][0]
            list_key = [k for k in mr[table_key].keys() if isinstance(mr[table_key][k], list)][0]
            items = mr[table_key][list_key]
            results.extend(items)
            total = int(mr["total"])
            offset += limit
            if offset >= total:
                break
        return results

    # --- Convenience methods ---

    def circuits(self, year: int) -> list[dict]:
        return self.get_all(f"{year}/circuits.json")

    def drivers(self, year: int) -> list[dict]:
        return self.get_all(f"{year}/drivers.json")

    def constructors(self, year: int) -> list[dict]:
        return self.get_all(f"{year}/constructors.json")

    def races(self, year: int) -> list[dict]:
        return self.get_all(f"{year}.json")

    def race_results(self, year: int, round_num: int) -> list[dict]:
        data = self.get(f"{year}/{round_num}/results.json", params={"limit": 100})
        races = data["MRData"]["RaceTable"]["Races"]
        if not races:
            return []
        return races[0].get("Results", [])

    def qualifying_results(self, year: int, round_num: int) -> list[dict]:
        data = self.get(f"{year}/{round_num}/qualifying.json", params={"limit": 100})
        races = data["MRData"]["RaceTable"]["Races"]
        if not races:
            return []
        return races[0].get("QualifyingResults", [])

    def pit_stops(self, year: int, round_num: int) -> list[dict]:
        """Pit stops are nested under Races[0].PitStops — need custom pagination."""
        all_stops = []
        offset = 0
        limit = 100
        while True:
            data = self.get(f"{year}/{round_num}/pitstops.json", params={"limit": limit, "offset": offset})
            mr = data["MRData"]
            races = mr.get("RaceTable", {}).get("Races", [])
            if not races:
                break
            stops = races[0].get("PitStops", [])
            all_stops.extend(stops)
            total = int(mr.get("total", 0))
            offset += limit
            if offset >= total:
                break
        return all_stops

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
