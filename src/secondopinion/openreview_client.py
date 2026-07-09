from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .llm_client import load_dotenv

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class OpenReviewClient:
    """Small stdlib-only client for public OpenReview API v2 note reads."""

    def __init__(
        self,
        base_url: str = "https://api2.openreview.net",
        timeout: int = 30,
        *,
        cookie: str | None = None,
        token: str | None = None,
        cookie_file: str | os.PathLike[str] | None = None,
        token_file: str | os.PathLike[str] | None = None,
        user_agent: str | None = None,
        max_retries: int | None = None,
        retry_backoff: float | None = None,
        urlopen_func: Callable[..., Any] | None = None,
        sleep_func: Callable[[float], None] | None = None,
    ):
        load_dotenv()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookie = resolve_secret(
            explicit=cookie,
            file_path=cookie_file,
            env_value="OPENREVIEW_COOKIE",
            env_file="OPENREVIEW_COOKIE_FILE",
        )
        self.token = resolve_secret(
            explicit=token,
            file_path=token_file,
            env_value="OPENREVIEW_TOKEN",
            env_file="OPENREVIEW_TOKEN_FILE",
        )
        self.user_agent = user_agent or os.environ.get("OPENREVIEW_USER_AGENT", "SecondOpinion-MVP/0.1")
        self.max_retries = int(max_retries if max_retries is not None else os.environ.get("OPENREVIEW_MAX_RETRIES", "3"))
        self.retry_backoff = float(
            retry_backoff if retry_backoff is not None else os.environ.get("OPENREVIEW_RETRY_BACKOFF", "1.0")
        )
        self.urlopen_func = urlopen_func or urllib.request.urlopen
        self.sleep_func = sleep_func or time.sleep

    def get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}{path}?{query}"
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        attempts = max(0, self.max_retries) + 1
        last_error: OpenReviewAPIError | None = None
        for attempt_index in range(attempts):
            try:
                with self.urlopen_func(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_error = OpenReviewAPIError(exc.code, body, url, retry_after=retry_after_seconds(exc))
                if not should_retry(last_error, attempt_index=attempt_index, attempts=attempts):
                    raise last_error from exc
            except urllib.error.URLError as exc:
                last_error = OpenReviewAPIError(0, str(exc), url)
                if not should_retry(last_error, attempt_index=attempt_index, attempts=attempts):
                    raise last_error from exc
            self.sleep_func(retry_delay(last_error, attempt_index=attempt_index, retry_backoff=self.retry_backoff))
        if last_error is not None:
            raise last_error
        raise OpenReviewAPIError(0, "Unknown OpenReview API error", url)

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
                self.sleep_func(polite_delay)
        return notes

    def get_iclr_submissions(self, year: int, *, limit: int | None = None) -> list[dict[str, Any]]:
        invitation = f"ICLR.cc/{year}/Conference/-/Submission"
        return self.get_all_notes(invitation, limit=limit, details="replies")


class OpenReviewAPIError(RuntimeError):
    def __init__(self, status_code: int, body: str, url: str, *, retry_after: float | None = None):
        self.status_code = status_code
        self.body = body
        self.url = url
        self.retry_after = retry_after
        super().__init__(f"OpenReview API request failed ({status_code}): {body[:500]}")

    def as_dict(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.body)
        except json.JSONDecodeError:
            payload = {"message": self.body}
        return {
            "status_code": self.status_code,
            "url": self.url,
            "payload": payload,
            "retry_after": self.retry_after,
        }


def resolve_secret(
    *,
    explicit: str | None,
    file_path: str | os.PathLike[str] | None,
    env_value: str,
    env_file: str,
) -> str:
    if explicit is not None:
        return explicit.strip()
    env_direct = os.environ.get(env_value, "").strip()
    if env_direct:
        return env_direct
    path_value = str(file_path or os.environ.get(env_file, "")).strip()
    if not path_value:
        return ""
    try:
        return parse_cookie_file_text(Path(path_value).read_text(encoding="utf-8")) if env_value == "OPENREVIEW_COOKIE" else Path(path_value).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def parse_cookie_file_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    jar_cookie = parse_netscape_cookie_jar(stripped)
    if jar_cookie:
        return jar_cookie
    return stripped


def parse_netscape_cookie_jar(text: str) -> str:
    pairs: list[str] = []
    saw_cookie_line = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            return ""
        saw_cookie_line = True
        domain, _include_subdomains, _path, _secure, _expires, name, value = parts
        if "openreview.net" not in domain.lower():
            continue
        if name and value:
            pairs.append(f"{name}={value}")
    return "; ".join(pairs) if saw_cookie_line else ""


def should_retry(error: OpenReviewAPIError, *, attempt_index: int, attempts: int) -> bool:
    if attempt_index >= attempts - 1:
        return False
    return error.status_code == 0 or error.status_code in RETRYABLE_STATUS_CODES


def retry_delay(error: OpenReviewAPIError | None, *, attempt_index: int, retry_backoff: float) -> float:
    if error and error.retry_after is not None:
        return max(0.0, error.retry_after)
    return max(0.0, retry_backoff) * (2**attempt_index)


def retry_after_seconds(exc: urllib.error.HTTPError) -> float | None:
    value = exc.headers.get("Retry-After") if exc.headers else None
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
