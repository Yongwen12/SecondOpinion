from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterable


NORMALIZED_FILTER_VERSION = "normalized-filter-v0.1"
SUPPORTED_YEAR_FILTERS = {"activity_year", "decision_or_activity_year", "decision_year"}


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_datetime(value: Any) -> dt.datetime | None:
    if value in {None, ""}:
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw = raw / 1000
        return dt.datetime.fromtimestamp(raw, tz=dt.timezone.utc)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def timestamps_from_item(item: dict[str, Any]) -> list[dt.datetime]:
    values: list[Any] = []
    timestamps = item.get("openreview_timestamps")
    if isinstance(timestamps, dict):
        values.extend(
            [
                timestamps.get("created_at"),
                timestamps.get("modified_at"),
                timestamps.get("created_ms"),
                timestamps.get("modified_ms"),
            ]
        )
    values.append(item.get("snapshot_time"))
    return [parsed for parsed in (parse_datetime(value) for value in values) if parsed is not None]


def decision_timestamps(paper: dict[str, Any]) -> list[dt.datetime]:
    values: list[dt.datetime] = []
    for decision in paper.get("decisions") or []:
        if isinstance(decision, dict):
            values.extend(timestamps_from_item(decision))
    return values


def activity_timestamps(paper: dict[str, Any]) -> list[dt.datetime]:
    values = timestamps_from_item(paper)
    for key in ("reviews", "rebuttals", "decisions"):
        for item in paper.get(key) or []:
            if isinstance(item, dict):
                values.extend(timestamps_from_item(item))
    return values


def any_year(values: Iterable[dt.datetime], year: int) -> bool:
    return any(value.year == year for value in values)


def paper_matches_year(paper: dict[str, Any], *, year: int, mode: str) -> bool:
    if mode not in SUPPORTED_YEAR_FILTERS:
        raise ValueError(f"Unsupported year filter mode: {mode}")
    decisions = decision_timestamps(paper)
    if mode == "decision_year":
        return any_year(decisions, year)
    activity = activity_timestamps(paper)
    if mode == "activity_year":
        return any_year(activity, year)
    return any_year(decisions, year) if decisions else any_year(activity, year)


def paper_is_accepted(paper: dict[str, Any]) -> bool:
    text = str(paper.get("decision") or "")
    for decision in paper.get("decisions") or []:
        if isinstance(decision, dict):
            text += " " + str(decision.get("text") or "")
    lowered = text.lower()
    if re.search(r"\breject(?:ed|ion)?\b", lowered):
        return False
    return bool(re.search(r"\baccept(?:ed|ance)?\b|\bcertif(?:y|ied|ication)\b|\bpublished\b", lowered))


def filter_normalized_dataset(
    payload: dict[str, Any],
    *,
    year: int,
    mode: str = "decision_or_activity_year",
    accepted_only: bool = False,
) -> dict[str, Any]:
    papers = []
    dropped_year = 0
    dropped_decision = 0
    for paper in payload.get("papers", []):
        if not isinstance(paper, dict):
            continue
        if not paper_matches_year(paper, year=year, mode=mode):
            dropped_year += 1
            continue
        if accepted_only and not paper_is_accepted(paper):
            dropped_decision += 1
            continue
        papers.append(paper)

    filtered = dict(payload)
    filtered["year"] = year
    filtered["papers"] = papers
    filtered["paper_count"] = len(papers)
    filtered["review_count"] = sum(len(paper.get("reviews", [])) for paper in papers)
    filtered["filter_metadata"] = {
        "schema_version": NORMALIZED_FILTER_VERSION,
        "year": year,
        "mode": mode,
        "accepted_only": accepted_only,
        "input_paper_count": len(payload.get("papers", [])),
        "dropped_wrong_year_count": dropped_year,
        "dropped_decision_count": dropped_decision,
        "output_paper_count": len(papers),
        "output_review_count": filtered["review_count"],
    }
    return filtered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Filter normalized OpenReview datasets by year and decision.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--mode", choices=sorted(SUPPORTED_YEAR_FILTERS), default="decision_or_activity_year")
    parser.add_argument("--accepted-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    filtered = filter_normalized_dataset(
        read_json(args.input),
        year=args.year,
        mode=args.mode,
        accepted_only=args.accepted_only,
    )
    write_json(args.out, filtered)
    print(json.dumps(filtered["filter_metadata"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
