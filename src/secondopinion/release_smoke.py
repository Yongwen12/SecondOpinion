from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RELEASE_SMOKE_SCHEMA_VERSION = "release-smoke-v0.1"
DEFAULT_SEARCH_QUERY = "CrossSpectra"
DEFAULT_SCORECARD_ID = "Ni4jNyroJZ"
EXPECTED_STATS = {
    "paper_count": 26749,
    "review_count": 128723,
    "scored_review_count": 99671,
    "audited_count": 99671,
}


@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: int = 0


def http_get(url: str, *, timeout: float = 20.0) -> HttpResponse:
    import time

    started = time.perf_counter()
    request = Request(url, headers={"User-Agent": "SecondOpinion-release-smoke/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - release smoke checks configured URLs.
            body = response.read()
            status = int(getattr(response, "status", 200))
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
    except HTTPError as exc:
        body = exc.read()
        status = int(exc.code)
        headers = {str(k).lower(): str(v) for k, v in exc.headers.items()}
    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    return HttpResponse(status=status, body=body, headers=headers, elapsed_ms=elapsed_ms)


def json_body(response: HttpResponse) -> Any:
    return json.loads(response.body.decode("utf-8"))


def add_check(checks: list[dict[str, Any]], *, name: str, ok: bool, message: str, **extra: Any) -> None:
    checks.append({"name": name, "ok": bool(ok), "message": message, **extra})


def with_query(url: str, params: dict[str, Any]) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(params)}"


def join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def run_release_smoke(
    *,
    frontend_url: str,
    api_url: str,
    search_query: str = DEFAULT_SEARCH_QUERY,
    scorecard_id: str = DEFAULT_SCORECARD_ID,
    timeout: float = 20.0,
    getter=http_get,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    frontend_response = getter(frontend_url, timeout=timeout)
    frontend_text = frontend_response.body.decode("utf-8", errors="replace")
    add_check(
        checks,
        name="frontend_status",
        ok=frontend_response.status == 200,
        message=f"Frontend returned HTTP {frontend_response.status}",
        elapsed_ms=frontend_response.elapsed_ms,
    )
    add_check(
        checks,
        name="frontend_coverage_copy",
        ok="ICLR, ICML, NeurIPS, TMLR, COLM, and MIDL" in frontend_text
        and "99,671 scored official reviews" in frontend_text,
        message="Frontend contains 2025 V1 coverage copy",
    )
    add_check(
        checks,
        name="frontend_api_default",
        ok="https://secondopinion.smartselling.work" in frontend_text,
        message="Frontend default API base is production API",
    )

    health_response = getter(join_url(api_url, "/health"), timeout=timeout)
    health_ok = False
    try:
        health_ok = health_response.status == 200 and json_body(health_response).get("status") == "ok"
    except Exception:
        health_ok = False
    add_check(
        checks,
        name="api_health",
        ok=health_ok,
        message=f"API health returned HTTP {health_response.status}",
        elapsed_ms=health_response.elapsed_ms,
    )

    home_url = with_query(join_url(api_url, "/api/home"), {"year": 2025, "limit": 12})
    home_response = getter(home_url, timeout=timeout)
    home: dict[str, Any] = {}
    try:
        home = json_body(home_response)
    except Exception:
        home = {}
    home_stats = home.get("stats") or {}
    add_check(
        checks,
        name="api_home_static",
        ok=home_response.status == 200 and home.get("source") == "static_home_2025",
        message=f"Home returned HTTP {home_response.status} source={home.get('source')}",
        elapsed_ms=home_response.elapsed_ms,
    )
    add_check(
        checks,
        name="api_home_stats",
        ok=all(int(home_stats.get(key) or 0) == value for key, value in EXPECTED_STATS.items()),
        message="Home stats match 2025 V1 release counts",
        stats=home_stats,
    )
    boards = home.get("leaderboards") or {}
    add_check(
        checks,
        name="api_home_boards",
        ok=all(len(boards.get(key) or []) >= 8 for key in ("overall", "toxic", "helpful")),
        message="Home leaderboards include publishable rows",
        board_counts={key: len(value or []) for key, value in boards.items()},
    )

    search_url = with_query(join_url(api_url, "/api/papers"), {"query": search_query, "year": 2025, "limit": 3})
    search_response = getter(search_url, timeout=timeout)
    try:
        search = json_body(search_response)
    except Exception:
        search = {}
    search_items = search.get("items") or []
    add_check(
        checks,
        name="api_global_search",
        ok=search_response.status == 200 and len(search_items) > 0,
        message=f"Global search returned {len(search_items)} items for {search_query!r}",
        elapsed_ms=search_response.elapsed_ms,
    )

    scorecard_response = getter(join_url(api_url, f"/api/papers/{scorecard_id}/scorecard"), timeout=timeout)
    try:
        scorecard = json_body(scorecard_response)
    except Exception:
        scorecard = {}
    reviewers = scorecard.get("reviewers") or []
    comments = scorecard.get("comments") or []
    add_check(
        checks,
        name="api_scorecard",
        ok=scorecard_response.status == 200 and len(reviewers) > 0 and len(comments) > 0,
        message=f"Scorecard {scorecard_id} returned {len(reviewers)} reviewers and {len(comments)} comments",
        elapsed_ms=scorecard_response.elapsed_ms,
    )

    failed = [check for check in checks if not check["ok"]]
    return {
        "schema_version": RELEASE_SMOKE_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "failed" if failed else "passed",
        "frontend_url": frontend_url,
        "api_url": api_url,
        "summary": {"check_count": len(checks), "failed_count": len(failed)},
        "checks": checks,
    }


def render_release_smoke_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SecondOpinion Release Smoke",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Frontend: `{report.get('frontend_url', '')}`",
        f"- API: `{report.get('api_url', '')}`",
        "",
        "## Checks",
        "",
        "| Check | OK | Message |",
        "| --- | ---: | --- |",
    ]
    for check in report.get("checks") or []:
        lines.append(f"| `{check.get('name')}` | `{check.get('ok')}` | {check.get('message', '')} |")
    return "\n".join(lines) + "\n"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the SecondOpinion 2025 V1 frontend and API release.")
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--search-query", default=DEFAULT_SEARCH_QUERY)
    parser.add_argument("--scorecard-id", default=DEFAULT_SCORECARD_ID)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--out", default="data/validation/release_smoke_2025.json")
    parser.add_argument("--markdown", default="reports/validation/release_smoke_2025.md")
    args = parser.parse_args(argv)

    report = run_release_smoke(
        frontend_url=args.frontend_url,
        api_url=args.api_url,
        search_query=args.search_query,
        scorecard_id=args.scorecard_id,
        timeout=args.timeout,
    )
    write_json(args.out, report)
    write_text(args.markdown, render_release_smoke_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
