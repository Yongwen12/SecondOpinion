from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .openreview_client import OpenReviewAPIError, OpenReviewClient
from .openreview_venue_inventory import classify_openreview_error


AUTH_CHECK_SCHEMA_VERSION = "openreview-auth-check-v0.1"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_openreview_auth_check(
    *,
    invitation: str = "ICLR.cc/2025/Conference/-/Submission",
    sample_limit: int = 1,
    details: str = "replies",
    client: OpenReviewClient | None = None,
) -> dict[str, Any]:
    client = client or OpenReviewClient()
    started_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    env = {
        "cookie_set": bool(getattr(client, "cookie", "")),
        "token_set": bool(getattr(client, "token", "")),
        "user_agent": str(getattr(client, "user_agent", "")),
        "api_base": str(getattr(client, "base_url", "")),
    }
    try:
        payload = client.get_notes(invitation, limit=sample_limit, offset=0, details=details)
    except OpenReviewAPIError as exc:
        status = classify_openreview_error(exc)
        return {
            "schema_version": AUTH_CHECK_SCHEMA_VERSION,
            "checked_at": started_at,
            "ok": False,
            "status": status,
            "recommendation": recommendation_for_status(status, env),
            "invitation": invitation,
            "sample_limit": sample_limit,
            "environment": env,
            "error": redact_error(exc),
        }
    notes = [note for note in payload.get("notes", []) if isinstance(note, dict)]
    return {
        "schema_version": AUTH_CHECK_SCHEMA_VERSION,
        "checked_at": started_at,
        "ok": True,
        "status": "ok",
        "recommendation": "run_inventory",
        "invitation": invitation,
        "sample_limit": sample_limit,
        "environment": env,
        "api_note_count": len(notes),
    }


def recommendation_for_status(status: str, env: dict[str, Any]) -> str:
    if status == "challenge_required":
        return "set_openreview_cookie_after_browser_challenge"
    if status == "auth_required":
        return "refresh_openreview_cookie_or_token" if env.get("cookie_set") or env.get("token_set") else "set_openreview_cookie"
    if status == "not_found":
        return "verify_probe_invitation"
    if status == "network_error":
        return "retry_network"
    return "inspect_error"


def redact_error(exc: OpenReviewAPIError) -> dict[str, Any]:
    payload = exc.as_dict().get("payload", {})
    if not isinstance(payload, dict):
        payload = {}
    return {
        "status_code": exc.status_code,
        "name": payload.get("name", ""),
        "message": payload.get("message", "") or str(payload)[:240],
        "challenge_url_present": bool(payload.get("challengeUrl")),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check whether OpenReview API auth/challenge state is ready for ingestion.")
    parser.add_argument("--invitation", default="ICLR.cc/2025/Conference/-/Submission")
    parser.add_argument("--sample-limit", type=int, default=1)
    parser.add_argument("--details", default="replies")
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--out", default="data/validation/openreview_auth_check.json")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    client = OpenReviewClient(base_url=args.api_base, timeout=args.timeout)
    result = run_openreview_auth_check(
        invitation=args.invitation,
        sample_limit=args.sample_limit,
        details=args.details,
        client=client,
    )
    write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
