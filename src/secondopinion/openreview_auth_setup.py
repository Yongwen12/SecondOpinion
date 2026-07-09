from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .openreview_client import parse_cookie_file_text, parse_netscape_cookie_jar
from .openreview_secret_check import cookie_diagnostics, cookie_names


AUTH_SETUP_SCHEMA_VERSION = "openreview-auth-setup-v0.1"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_cookie_source(*, cookie: str = "", cookie_file: str = "") -> tuple[str, str]:
    if cookie.strip():
        return cookie.strip(), "raw_header"
    if not cookie_file.strip():
        return "", ""
    text = Path(cookie_file).read_text(encoding="utf-8")
    jar_header = parse_netscape_cookie_jar(text.strip())
    if jar_header:
        return jar_header, "netscape_cookie_jar"
    return parse_cookie_file_text(text), "raw_header"


def update_env_file(path: str | Path, updates: dict[str, str]) -> None:
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue
        key, _sep, _value = line.partition("=")
        key = key.strip()
        if key in updates:
            output.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={value}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def install_openreview_cookie(
    *,
    cookie: str = "",
    cookie_file: str = "",
    out_cookie: str | Path = "data/secrets/openreview.cookie",
    env_path: str | Path = ".env",
) -> dict[str, Any]:
    header, source_format = normalize_cookie_source(cookie=cookie, cookie_file=cookie_file)
    if not header:
        return {
            "schema_version": AUTH_SETUP_SCHEMA_VERSION,
            "ok": False,
            "recommendation": "provide_cookie_or_cookie_file",
            "cookie": {
                "set": False,
                "source_format": source_format,
                "cookie_count": 0,
                "cookie_names": [],
                "byte_length": 0,
            },
        }
    out_path = Path(out_cookie)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header.strip() + "\n", encoding="utf-8")
    update_env_file(env_path, {"OPENREVIEW_COOKIE_FILE": str(out_path)})
    names = cookie_names(header)
    diagnostics = cookie_diagnostics(header)
    recommendation = "refresh_browser_cookie_missing_openreview_login" if "missing_openreview_login_cookie" in diagnostics.get("warnings", []) else "run_openreview_pipeline_gate"
    return {
        "schema_version": AUTH_SETUP_SCHEMA_VERSION,
        "ok": True,
        "recommendation": recommendation,
        "cookie": {
            "set": True,
            "source_format": source_format,
            "out_cookie": str(out_path),
            "env_path": str(env_path),
            "cookie_count": len(names),
            "cookie_names": names,
            "byte_length": len(header.encode("utf-8")),
            "diagnostics": diagnostics,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install a browser-verified OpenReview cookie safely for local ingestion.")
    parser.add_argument("--cookie", default="", help="Raw Cookie header. Prefer --cookie-file to avoid shell history.")
    parser.add_argument("--cookie-file", default="", help="Raw Cookie header file or Netscape cookie jar export.")
    parser.add_argument("--out-cookie", default="data/secrets/openreview.cookie")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--out", default="data/validation/openreview_auth_setup.json")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = install_openreview_cookie(
        cookie=args.cookie,
        cookie_file=args.cookie_file,
        out_cookie=args.out_cookie,
        env_path=args.env,
    )
    write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
