from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any

RAW_CLEANUP_VERSION = "openreview-raw-cleanup-v0.1"
CONFIRM_TOKEN = "delete-raw-openreview"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def inspect_raw_root(raw_root: str | Path) -> dict[str, Any]:
    root = Path(raw_root)
    if not root.exists():
        return {"root": str(root), "exists": False, "file_count": 0, "raw_note_page_count": 0, "total_bytes": 0, "total_gb": 0.0}
    files = [path for path in root.rglob("*") if path.is_file()]
    raw_pages = [path for path in files if path.name.startswith("notes_page_") and path.suffix.lower() == ".json"]
    total_bytes = sum(path.stat().st_size for path in files)
    return {
        "root": str(root),
        "exists": True,
        "file_count": len(files),
        "raw_note_page_count": len(raw_pages),
        "total_bytes": total_bytes,
        "total_gb": round(total_bytes / 1_000_000_000, 3),
        "sample_files": [str(path) for path in raw_pages[:10]],
    }


def cleanup_raw_openreview(
    *,
    raw_root: str | Path = "data/raw/openreview",
    workspace_root: str | Path = ".",
    execute: bool = False,
    confirm: str = "",
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    root = Path(raw_root)
    resolved = root.resolve()
    expected = (workspace / "data" / "raw" / "openreview").resolve()
    before = inspect_raw_root(root)
    errors: list[str] = []
    if not is_within(resolved, expected):
        errors.append(f"refusing to clean unexpected raw root: {resolved}")
    if execute and confirm != CONFIRM_TOKEN:
        errors.append(f"execute requires --confirm {CONFIRM_TOKEN}")
    deleted = False
    if execute and not errors and root.exists():
        shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text(
            "Raw OpenReview API snapshots were removed after normalization to enforce data minimization. "
            "Future official pulls write minimized normalized JSON by default.\n",
            encoding="utf-8",
        )
        deleted = True
    after = inspect_raw_root(root)
    status = "failed" if errors else "deleted" if deleted else "dry_run"
    return {
        "schema_version": RAW_CLEANUP_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "execute": execute,
        "confirm_token_required": CONFIRM_TOKEN,
        "raw_root": str(root),
        "before": before,
        "after": after,
        "deleted": deleted,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run or explicitly delete raw OpenReview API snapshots after minimized artifacts are verified.")
    parser.add_argument("--raw-root", default="data/raw/openreview")
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--out", default="data/validation/openreview_raw_cleanup.json")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = cleanup_raw_openreview(
        raw_root=args.raw_root,
        workspace_root=args.workspace_root,
        execute=args.execute,
        confirm=args.confirm,
    )
    write_json(args.out, report)
    print(json.dumps({"status": report["status"], "deleted": report["deleted"], "before": report["before"], "after": report["after"], "errors": report["errors"]}, ensure_ascii=False, indent=2))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
