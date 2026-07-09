from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any

from .normalize import normalize_openreview_notes
from .openreview_client import OpenReviewClient


RAW_SNAPSHOT_SCHEMA_VERSION = "raw-snapshot-v0.2"


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


def snapshot_manifest(
    *,
    client: OpenReviewClient,
    source: str,
    venue: str,
    year: int,
    snapshot: str,
    created_at: str,
    invitation: str,
    details: str,
    limit: int | None,
    page_size: int,
    polite_delay: float,
    raw_files: list[str],
    paper_count: int,
    reply_count: int,
    complete: bool,
    resumed: bool,
    failed: bool = False,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": RAW_SNAPSHOT_SCHEMA_VERSION,
        "source": source,
        "venue": venue,
        "year": year,
        "snapshot_id": snapshot,
        "created_at": created_at,
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "api": client.base_url,
        "query": {
            "path": "/notes",
            "invitation": invitation,
            "details": details,
            "limit": limit,
            "page_size": page_size,
            "polite_delay": polite_delay,
        },
        "paper_count": paper_count,
        "reply_count": reply_count,
        "raw_files": raw_files,
        "complete": complete,
        "failed": failed,
        "error": error or {},
        "resumed": resumed,
        "next_offset": paper_count,
    }


def load_existing_snapshot_state(snapshot_dir: Path) -> dict[str, Any]:
    manifest_path = snapshot_dir / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        raw_files = [str(item) for item in manifest.get("raw_files", []) if item]
    else:
        raw_files = sorted(path.name for path in snapshot_dir.glob("notes_page_*.json"))
        manifest = {}
    paper_count = 0
    reply_count = 0
    valid_files: list[str] = []
    for raw_file in raw_files:
        path = snapshot_dir / raw_file
        if not path.exists():
            continue
        payload = read_json(path)
        notes = list(payload.get("notes", []))
        valid_files.append(raw_file)
        paper_count += len(notes)
        reply_count += sum(count_replies(note) for note in notes)
    return {
        "manifest": manifest,
        "raw_files": valid_files,
        "paper_count": paper_count,
        "reply_count": reply_count,
        "page_index": len(valid_files),
        "offset": paper_count,
    }


def save_openreview_snapshot(
    client: OpenReviewClient,
    *,
    venue: str,
    year: int,
    invitation: str,
    details: str = "replies",
    limit: int | None = None,
    page_size: int = 100,
    polite_delay: float = 0.1,
    root: str | Path = "data/raw",
    source: str = "openreview",
    snapshot: str | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    snapshot = snapshot or snapshot_id()
    snapshot_dir = Path(root) / source / slug(venue) / str(year) / snapshot
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    raw_files: list[str] = []
    paper_count = 0
    reply_count = 0
    offset = 0
    page_index = 0
    resumed = False
    if resume:
        state = load_existing_snapshot_state(snapshot_dir)
        raw_files = state["raw_files"]
        paper_count = state["paper_count"]
        reply_count = state["reply_count"]
        offset = state["offset"]
        page_index = state["page_index"]
        created_at = str(state.get("manifest", {}).get("created_at") or created_at)
        resumed = bool(raw_files)

    complete = False
    while True:
        remaining = None if limit is None else max(limit - paper_count, 0)
        if remaining == 0:
            complete = True
            break
        batch_size = min(page_size, remaining) if remaining is not None else page_size
        try:
            payload = client.get_notes(invitation, limit=batch_size, offset=offset, details=details)
        except Exception as exc:
            write_json(
                snapshot_dir / "manifest.json",
                snapshot_manifest(
                    client=client,
                    source=source,
                    venue=venue,
                    year=year,
                    snapshot=snapshot,
                    created_at=created_at,
                    invitation=invitation,
                    details=details,
                    limit=limit,
                    page_size=page_size,
                    polite_delay=polite_delay,
                    raw_files=raw_files,
                    paper_count=paper_count,
                    reply_count=reply_count,
                    complete=False,
                    failed=True,
                    error={"type": type(exc).__name__, "message": str(exc), "offset": offset},
                    resumed=resumed,
                ),
            )
            raise
        notes = list(payload.get("notes", []))
        if not notes:
            complete = True
            break

        file_name = f"notes_page_{page_index:04d}.json"
        write_json(snapshot_dir / file_name, payload)
        raw_files.append(file_name)
        paper_count += len(notes)
        reply_count += sum(count_replies(note) for note in notes)
        write_json(
            snapshot_dir / "manifest.json",
            snapshot_manifest(
                client=client,
                source=source,
                venue=venue,
                year=year,
                snapshot=snapshot,
                created_at=created_at,
                invitation=invitation,
                details=details,
                limit=limit,
                page_size=page_size,
                polite_delay=polite_delay,
                raw_files=raw_files,
                paper_count=paper_count,
                reply_count=reply_count,
                complete=False,
                resumed=resumed,
            ),
        )

        if len(notes) < batch_size:
            complete = True
            break
        offset += len(notes)
        page_index += 1
        sleep = getattr(client, "sleep_func", time.sleep)
        sleep(max(polite_delay, 0.0))

    manifest = snapshot_manifest(
        client=client,
        source=source,
        venue=venue,
        year=year,
        snapshot=snapshot,
        created_at=created_at,
        invitation=invitation,
        details=details,
        limit=limit,
        page_size=page_size,
        polite_delay=polite_delay,
        raw_files=raw_files,
        paper_count=paper_count,
        reply_count=reply_count,
        complete=complete,
        resumed=resumed,
    )
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
