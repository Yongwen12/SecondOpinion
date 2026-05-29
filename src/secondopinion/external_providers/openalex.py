from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from ..text import clean_text


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
OPENALEX_CACHE_VERSION = "openalex-cache-v0.1"


class OpenAlexError(RuntimeError):
    pass


class OpenAlexClient:
    def __init__(
        self,
        *,
        mailto: str = "",
        timeout: int = 30,
        base_url: str = OPENALEX_WORKS_URL,
        cache_root: str | Path | None = "data/cache/openalex",
        refresh_cache: bool = False,
        offline: bool = False,
        urlopen_func: Any = None,
    ) -> None:
        self.mailto = mailto or os.environ.get("SECONDOPINION_OPENALEX_MAILTO", "") or os.environ.get("OPENALEX_MAILTO", "")
        self.timeout = timeout
        self.base_url = base_url
        self.cache_root = Path(cache_root) if cache_root else None
        self.refresh_cache = refresh_cache
        self.offline = offline
        self.urlopen_func = urlopen_func or urllib.request.urlopen
        self.stats: Counter[str] = Counter()

    def search_works(
        self,
        query: str,
        *,
        per_page: int = 5,
        year_lte: int | None = None,
    ) -> list[dict[str, Any]]:
        query = clean_text(query)
        if not query:
            return []
        filters = ["has_abstract:true"]
        if year_lte:
            filters.append(f"to_publication_date:{year_lte}-12-31")
        params = {
            "search": query,
            "per-page": str(max(1, min(per_page, 25))),
            "select": "id,doi,display_name,publication_year,publication_date,abstract_inverted_index,cited_by_count,primary_location",
        }
        if filters:
            params["filter"] = ",".join(filters)
        if self.mailto:
            params["mailto"] = self.mailto
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        payload = self.fetch_json(url, query=query, year_lte=year_lte, per_page=per_page)
        results = payload.get("results", [])
        return [normalize_work(item) for item in results if isinstance(item, dict)]

    def fetch_json(self, url: str, *, query: str, year_lte: int | None, per_page: int) -> dict[str, Any]:
        cached = self.read_cache(url)
        if cached is not None and not self.refresh_cache:
            self.stats["cache_hits"] += 1
            return cached
        if self.offline:
            self.stats["offline_misses"] += 1
            raise OpenAlexError(f"OpenAlex cache miss in offline mode: {url}")

        self.stats["network_requests"] += 1
        request = urllib.request.Request(url, headers={"User-Agent": "SecondOpinion-MVP/0.1"})
        try:
            with self.urlopen_func(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise OpenAlexError(f"OpenAlex request failed: {message}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc
        self.write_cache(
            url,
            payload,
            metadata={
                "query": query,
                "year_lte": year_lte,
                "per_page": per_page,
            },
        )
        return payload

    def read_cache(self, url: str) -> dict[str, Any] | None:
        path = self.cache_path(url)
        if path is None:
            self.stats["cache_disabled"] += 1
            return None
        try:
            exists = path.exists()
        except OSError:
            self.stats["cache_errors"] += 1
            return None
        if not exists:
            self.stats["cache_misses"] += 1
            return None
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.stats["cache_errors"] += 1
            return None
        payload = cached.get("payload")
        if not isinstance(payload, dict):
            self.stats["cache_errors"] += 1
            return None
        return payload

    def write_cache(self, url: str, payload: dict[str, Any], *, metadata: dict[str, Any]) -> None:
        path = self.cache_path(url)
        if path is None:
            return
        cached = {
            "cache_version": OPENALEX_CACHE_VERSION,
            "cached_at": int(time.time()),
            "url": url,
            "metadata": metadata,
            "payload": payload,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cached, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.stats["cache_writes"] += 1
        except OSError:
            self.stats["cache_errors"] += 1

    def cache_path(self, url: str) -> Path | None:
        if self.cache_root is None:
            return None
        digest = urllib.parse.quote_plus(url)
        if len(digest) > 140:
            import hashlib

            digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return self.cache_root / f"{digest}.json"

    def stats_dict(self) -> dict[str, int]:
        return dict(self.stats)


def normalize_work(work: dict[str, Any]) -> dict[str, Any]:
    title = clean_text(work.get("display_name"))
    abstract = abstract_from_inverted_index(work.get("abstract_inverted_index"))
    primary_location = work.get("primary_location") if isinstance(work.get("primary_location"), dict) else {}
    landing_page_url = ""
    if isinstance(primary_location, dict):
        landing_page_url = clean_text(primary_location.get("landing_page_url"))
    return {
        "id": clean_text(work.get("id")),
        "doi": clean_text(work.get("doi")),
        "title": title,
        "abstract": abstract,
        "publication_year": work.get("publication_year"),
        "publication_date": clean_text(work.get("publication_date")),
        "cited_by_count": work.get("cited_by_count") or 0,
        "url": landing_page_url or clean_text(work.get("id")),
    }


def abstract_from_inverted_index(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    positions: list[tuple[int, str]] = []
    for token, raw_indexes in value.items():
        if not isinstance(token, str) or not isinstance(raw_indexes, list):
            continue
        for index in raw_indexes:
            if isinstance(index, int):
                positions.append((index, token))
    if not positions:
        return ""
    return clean_text(" ".join(token for _, token in sorted(positions)))


def works_to_external_records(
    works: list[dict[str, Any]],
    *,
    claim_id: str,
    query: str,
    max_items: int = 3,
) -> list[dict[str, Any]]:
    records = []
    seen = set()
    for work in works:
        title = clean_text(work.get("title"))
        abstract = clean_text(work.get("abstract"))
        stable_id = clean_text(work.get("id") or work.get("doi") or title)
        if not title or not abstract or stable_id in seen:
            continue
        seen.add(stable_id)
        year = work.get("publication_year")
        cited_by_count = work.get("cited_by_count") or 0
        text = f"{title}. {abstract}"
        records.append(
            {
                "source_type": "external_reference",
                "section": f"OpenAlex related paper: {title[:90]}",
                "page": None,
                "text": text,
                "metadata": {
                    "provider": "openalex",
                    "stable_id": stable_id,
                    "doi": clean_text(work.get("doi")),
                    "url": clean_text(work.get("url")),
                    "title": title,
                    "publication_year": year,
                    "publication_date": clean_text(work.get("publication_date")),
                    "cited_by_count": cited_by_count,
                    "query": query,
                    "claim_id": claim_id,
                    "available_at_review_time": True,
                },
            }
        )
        if len(records) >= max_items:
            break
    return records
