from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any


class OpenReviewClient:
    """Small stdlib-only client for public OpenReview API v2 note reads."""

    def __init__(self, base_url: str = "https://api2.openreview.net", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}{path}?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "SecondOpinion-MVP/0.1",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_notes(
        self,
        invitation: str,
        *,
        limit: int = 50,
        details: str | None = "replies",
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.get_json(
            "/notes",
            {
                "invitation": invitation,
                "details": details,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_all_notes(
        self,
        invitation: str,
        *,
        limit: int | None = None,
        page_size: int = 100,
        details: str | None = "replies",
        polite_delay: float = 0.1,
    ) -> list[dict[str, Any]]:
        notes: list[dict[str, Any]] = []
        offset = 0
        while True:
            remaining = None if limit is None else max(limit - len(notes), 0)
            if remaining == 0:
                break
            batch_size = min(page_size, remaining) if remaining is not None else page_size
            payload = self.get_notes(invitation, limit=batch_size, offset=offset, details=details)
            batch = list(payload.get("notes", []))
            if not batch:
                break
            notes.extend(batch)
            if len(batch) < batch_size:
                break
            offset += len(batch)
            if polite_delay:
                time.sleep(polite_delay)
        return notes

    def get_iclr_submissions(self, year: int, *, limit: int | None = None) -> list[dict[str, Any]]:
        invitation = f"ICLR.cc/{year}/Conference/-/Submission"
        return self.get_all_notes(invitation, limit=limit, details="replies")
