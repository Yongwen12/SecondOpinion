from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from .normalize import normalize_openreview_notes
from .openreview_client import OpenReviewClient


def snapshot_id(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc).replace(microsecond=0)
    return now.strftime("%Y%m%dT%H%M%SZ")


def slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def count_replies(note: dict[str, Any]) -> int:
    details = note.get("details") or {}
    replies = details.get("replies") or details.get("directReplies") or []
    return len(replies) if isinstance(replies, list) else 0


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def save_openreview_snapshot(
    client: OpenReviewClient,
    *,
    venue: str,
    year: int,
    invitation: str,
    details: str = "replies",
    limit: int | None = None,
    page_size: int = 100,
    root: str | Path = "data/raw",
    source: str = "openreview",
    snapshot: str | None = None,
) -> dict[str, Any]:
    snapshot = snapshot or snapshot_id()
    snapshot_dir = Path(root) / source / slug(venue) / str(year) / snapshot
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    raw_files: list[str] = []
    paper_count = 0
    reply_count = 0
    offset = 0
    page_index = 0
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    while True:
        remaining = None if limit is None else max(limit - paper_count, 0)
        if remaining == 0:
            break
        batch_size = min(page_size, remaining) if remaining is not None else page_size
        payload = client.get_notes(invitation, limit=batch_size, offset=offset, details=details)
        notes = list(payload.get("notes", []))
        if not notes:
            break

        file_name = f"notes_page_{page_index:04d}.json"
        write_json(snapshot_dir / file_name, payload)
        raw_files.append(file_name)
        paper_count += len(notes)
        reply_count += sum(count_replies(note) for note in notes)

        if len(notes) < batch_size:
            break
        offset += len(notes)
        page_index += 1

    manifest = {
        "schema_version": "raw-snapshot-v0.1",
        "source": source,
        "venue": venue,
        "year": year,
        "snapshot_id": snapshot,
        "created_at": created_at,
        "api": client.base_url,
        "query": {
            "path": "/notes",
            "invitation": invitation,
            "details": details,
            "limit": limit,
            "page_size": page_size,
        },
        "paper_count": paper_count,
        "reply_count": reply_count,
        "raw_files": raw_files,
    }
    write_json(snapshot_dir / "manifest.json", manifest)
    return {"snapshot_dir": str(snapshot_dir), "manifest": manifest}


def load_snapshot_notes(snapshot_dir: str | Path) -> list[dict[str, Any]]:
    snapshot_dir = Path(snapshot_dir)
    manifest = read_json(snapshot_dir / "manifest.json")
    notes: list[dict[str, Any]] = []
    for raw_file in manifest.get("raw_files", []):
        payload = read_json(snapshot_dir / raw_file)
        notes.extend(payload.get("notes", []))
    return notes


def normalize_snapshot(snapshot_dir: str | Path, *, venue: str | None = None, year: int | None = None) -> dict[str, Any]:
    snapshot_dir = Path(snapshot_dir)
    manifest = read_json(snapshot_dir / "manifest.json")
    notes = load_snapshot_notes(snapshot_dir)
    normalized = normalize_openreview_notes(
        notes,
        venue=venue or manifest["venue"],
        year=year or int(manifest["year"]),
    )
    normalized["source_snapshot"] = {
        "snapshot_id": manifest["snapshot_id"],
        "source": manifest["source"],
        "venue": manifest["venue"],
        "year": manifest["year"],
        "snapshot_dir": str(snapshot_dir),
    }
    return normalized

