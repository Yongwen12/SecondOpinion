from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from .llm_client import load_dotenv
from .openreview_client import parse_cookie_file_text, parse_netscape_cookie_jar


SECRET_CHECK_SCHEMA_VERSION = "openreview-secret-check-v0.1"
OPENREVIEW_COOKIE_NAMES = {"openreview_session", "openreview.sid", "openreview_token", "openreview.accessToken"}
CLEARANCE_COOKIE_NAMES = {"cf_clearance", "openreview.clearanceToken"}


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cookie_names(cookie_header: str) -> list[str]:
    names = []
    for part in cookie_header.split(";"):
        name, sep, _value = part.strip().partition("=")
        if sep and name:
            names.append(name)
    return names



def netscape_cookie_meta(text: str, *, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    rows = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            continue
        domain, _include_subdomains, _path, _secure, expires, name, _value = parts
        if "openreview.net" not in domain.lower() or not name:
            continue
        try:
            expires_at = int(expires)
        except ValueError:
            expires_at = 0
        rows.append({"name": name, "expires_at": expires_at})
    expired = [row["name"] for row in rows if row["expires_at"] and row["expires_at"] < now]
    session = [row["name"] for row in rows if not row["expires_at"]]
    return {
        "openreview_domain_cookie_count": len(rows),
        "expired_cookie_names": sorted(set(expired)),
        "session_cookie_names": sorted(set(session)),
    }


def cookie_diagnostics(cookie_header: str, *, jar_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    names = set(cookie_names(cookie_header))
    warnings = []
    has_openreview_login_cookie = bool(names & OPENREVIEW_COOKIE_NAMES)
    has_clearance_cookie = bool(names & CLEARANCE_COOKIE_NAMES)
    if names and not has_openreview_login_cookie:
        warnings.append("missing_openreview_login_cookie")
    if names and not has_clearance_cookie:
        warnings.append("missing_cf_clearance_cookie")
    meta = jar_meta or {}
    expired_names = list(meta.get("expired_cookie_names") or [])
    if expired_names:
        warnings.append("netscape_cookie_jar_contains_expired_openreview_cookies")
    return {
        "has_openreview_login_cookie": has_openreview_login_cookie,
        "has_clearance_cookie": has_clearance_cookie,
        "expected_login_cookie_names": sorted(OPENREVIEW_COOKIE_NAMES),
        "expected_clearance_cookie_names": sorted(CLEARANCE_COOKIE_NAMES),
        "warnings": warnings,
        **meta,
    }


def inspect_cookie_source(cookie: str = "", cookie_file: str = "") -> dict[str, Any]:
    if cookie.strip():
        header = cookie.strip()
        return {
            "set": True,
            "source": "OPENREVIEW_COOKIE",
            "format": "raw_header",
            "cookie_count": len(cookie_names(header)),
            "cookie_names": cookie_names(header),
            "byte_length": len(header.encode("utf-8")),
            "diagnostics": cookie_diagnostics(header),
        }
    if not cookie_file.strip():
        return {"set": False, "source": "", "format": "", "cookie_count": 0, "cookie_names": [], "byte_length": 0}
    path = Path(cookie_file)
    if not path.exists():
        return {
            "set": False,
            "source": "OPENREVIEW_COOKIE_FILE",
            "format": "missing_file",
            "path": str(path),
            "cookie_count": 0,
            "cookie_names": [],
            "byte_length": 0,
        }
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    jar_header = parse_netscape_cookie_jar(stripped)
    header = jar_header or parse_cookie_file_text(text)
    fmt = "netscape_cookie_jar" if jar_header else "raw_header"
    jar_meta = netscape_cookie_meta(stripped) if jar_header else {}
    return {
        "set": bool(header),
        "source": "OPENREVIEW_COOKIE_FILE",
        "format": fmt if header else "empty_file",
        "path": str(path),
        "cookie_count": len(cookie_names(header)),
        "cookie_names": cookie_names(header),
        "byte_length": len(header.encode("utf-8")),
        "diagnostics": cookie_diagnostics(header, jar_meta=jar_meta) if header else {},
    }


def inspect_token_source(token: str = "", token_file: str = "") -> dict[str, Any]:
    if token.strip():
        value = token.strip()
        return {"set": True, "source": "OPENREVIEW_TOKEN", "byte_length": len(value.encode("utf-8"))}
    if not token_file.strip():
        return {"set": False, "source": "", "byte_length": 0}
    path = Path(token_file)
    if not path.exists():
        return {"set": False, "source": "OPENREVIEW_TOKEN_FILE", "format": "missing_file", "path": str(path), "byte_length": 0}
    value = path.read_text(encoding="utf-8").strip()
    return {"set": bool(value), "source": "OPENREVIEW_TOKEN_FILE", "path": str(path), "byte_length": len(value.encode("utf-8"))}


def recommendation(cookie_info: dict[str, Any], token_info: dict[str, Any]) -> str:
    if token_info.get("set"):
        return "run_openreview_pipeline_gate"
    if cookie_info.get("set"):
        warnings = set((cookie_info.get("diagnostics") or {}).get("warnings") or [])
        if "missing_openreview_login_cookie" in warnings:
            return "refresh_browser_cookie_missing_openreview_login"
        if "netscape_cookie_jar_contains_expired_openreview_cookies" in warnings:
            return "refresh_browser_cookie_expired_entries"
        return "run_openreview_pipeline_gate"
    if cookie_info.get("format") == "missing_file" or token_info.get("format") == "missing_file":
        return "fix_secret_file_path"
    return "set_openreview_cookie_file_or_token"


def run_openreview_secret_check(
    *,
    cookie: str | None = None,
    cookie_file: str | None = None,
    token: str | None = None,
    token_file: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    cookie_info = inspect_cookie_source(
        cookie=os.environ.get("OPENREVIEW_COOKIE", "") if cookie is None else cookie,
        cookie_file=os.environ.get("OPENREVIEW_COOKIE_FILE", "") if cookie_file is None else cookie_file,
    )
    token_info = inspect_token_source(
        token=os.environ.get("OPENREVIEW_TOKEN", "") if token is None else token,
        token_file=os.environ.get("OPENREVIEW_TOKEN_FILE", "") if token_file is None else token_file,
    )
    return {
        "schema_version": SECRET_CHECK_SCHEMA_VERSION,
        "ok": bool(cookie_info.get("set") or token_info.get("set")),
        "recommendation": recommendation(cookie_info, token_info),
        "cookie": cookie_info,
        "token": token_info,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect OpenReview auth secrets without printing secret values.")
    parser.add_argument("--cookie-file", default="")
    parser.add_argument("--token-file", default="")
    parser.add_argument("--out", default="data/validation/openreview_secret_check.json")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = run_openreview_secret_check(
        cookie_file=args.cookie_file or None,
        token_file=args.token_file or None,
    )
    write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
