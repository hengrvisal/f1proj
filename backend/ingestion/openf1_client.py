"""OpenF1 API client."""

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openf1.org/v1"


class OpenF1Client:
    def __init__(self):
        self._client = httpx.Client(timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get(self, endpoint: str, params: dict | None = None) -> list[dict]:
        url = f"{BASE_URL}/{endpoint}"
        logger.debug("GET %s params=%s", url, params)
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def meetings(self, year: int) -> list[dict]:
        return self.get("meetings", {"year": year})

    def sessions(self, meeting_key: int) -> list[dict]:
        return self.get("sessions", {"meeting_key": meeting_key})

    def race_control(self, session_key: int) -> list[dict]:
        return self.get("race_control", {"session_key": session_key})

    def team_radio(self, session_key: int) -> list[dict]:
        return self.get("team_radio", {"session_key": session_key})

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
