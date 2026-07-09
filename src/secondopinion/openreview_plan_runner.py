from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .llm_client import load_dotenv
from .openreview_secret_check import run_openreview_secret_check

PLAN_RUNNER_VERSION = "openreview-plan-runner-v0.1"
DEFAULT_STOP_BEFORE = {"submit_batch"}
INPUT_FLAGS = {"--input", "--manifest", "--inventory", "--plan", "--snapshot"}
COST_MANIFEST_FLAGS = {"--manifest"}


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_set(values: list[str] | None) -> set[str]:
    return {value.strip().upper() for value in values or [] if value.strip()}


def command_allowed(command: dict[str, Any], *, include_costly: bool) -> bool:
    if include_costly:
        return True
    return str(command.get("name") or "") not in DEFAULT_STOP_BEFORE


def is_path_like(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if stripped.startswith(("-", "YOUR_")):
        return False
    if stripped.isupper() and "/" not in stripped and "\\" not in stripped and "." not in stripped:
        return False
    return "/" in stripped or "\\" in stripped or "." in Path(stripped).name


def resolve_path(value: str, cwd: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(cwd) / path


def existing_outputs(step: dict[str, Any], *, cwd: str | Path = ".") -> list[str]:
    existing: list[str] = []
    for value in step.get("writes", []) or []:
        text = str(value)
        if is_path_like(text) and resolve_path(text, cwd).exists():
            existing.append(text)
    return existing


def all_path_outputs_exist(step: dict[str, Any], *, cwd: str | Path = ".") -> bool:
    outputs = [str(value) for value in step.get("writes", []) or [] if is_path_like(str(value))]
    return bool(outputs) and all(resolve_path(value, cwd).exists() for value in outputs)


def command_flag_values(command: str, flags: set[str]) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    values: list[str] = []
    for index, part in enumerate(parts):
        if part in flags and index + 1 < len(parts):
            values.append(parts[index + 1])
    return values


def command_input_paths(command: str) -> list[str]:
    return [value for value in command_flag_values(command, INPUT_FLAGS) if is_path_like(value)]


def missing_inputs(command: str, *, cwd: str | Path = ".") -> list[str]:
    return [value for value in command_input_paths(command) if not resolve_path(value, cwd).exists()]


def submit_batch_cost(step: dict[str, Any], *, cwd: str | Path = ".") -> tuple[float | None, str]:
    if str(step.get("name") or "") != "submit_batch":
        return None, ""
    manifests = command_flag_values(str(step.get("command") or ""), COST_MANIFEST_FLAGS)
    if not manifests:
        return None, "missing_manifest_flag"
    manifest_path = resolve_path(manifests[0], cwd)
    if not manifest_path.exists():
        return None, "missing_manifest"
    try:
        payload = read_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        return None, "invalid_manifest"
    value = payload.get("estimated_batch_cost_usd")
    if value is None:
        return None, "missing_estimated_batch_cost_usd"
    try:
        return float(value), ""
    except (TypeError, ValueError):
        return None, "invalid_estimated_batch_cost_usd"



def openreview_auth_available() -> bool:
    return bool(run_openreview_secret_check().get("ok"))


def openai_key_available() -> bool:
    load_dotenv()
    return bool(__import__("os").environ.get("OPENAI_API_KEY", "").strip())

def select_plan_steps(
    plan: dict[str, Any],
    *,
    venues: list[str] | None = None,
    stages: list[str] | None = None,
    include_blocked: bool = False,
    include_costly: bool = False,
) -> list[dict[str, Any]]:
    venue_filter = normalize_set(venues)
    stage_filter = {value.strip() for value in stages or [] if value.strip()}
    steps: list[dict[str, Any]] = []
    for venue in plan.get("venues", []):
        venue_id = str(venue.get("venue_id") or "").upper()
        if venue_filter and venue_id not in venue_filter:
            continue
        commands_enabled = bool(venue.get("commands_enabled"))
        if not commands_enabled and not include_blocked:
            steps.append(
                {
                    "venue_id": venue_id,
                    "name": "blocked",
                    "status": "skipped",
                    "reason": venue.get("blocked_reason") or f"readiness={venue.get('readiness')}",
                    "command": "",
                }
            )
            continue
        for command in venue.get("commands", []):
            name = str(command.get("name") or "")
            if stage_filter and name not in stage_filter:
                continue
            if not command_allowed(command, include_costly=include_costly):
                steps.append(
                    {
                        "venue_id": venue_id,
                        "name": name,
                        "status": "skipped",
                        "reason": "costly_step_requires_include_costly",
                        "command": command.get("command", ""),
                    }
                )
                continue
            steps.append(
                {
                    "venue_id": venue_id,
                    "name": name,
                    "status": "pending",
                    "reason": "",
                    "command": command.get("command", ""),
                    "writes": command.get("writes", []),
                    "requires_network": bool(command.get("requires_network")),
                    "requires_openreview_auth": bool(command.get("requires_openreview_auth")),
                    "requires_openai_key": bool(command.get("requires_openai_key")),
                }
            )
    return steps


def run_plan_steps(
    steps: list[dict[str, Any]],
    *,
    execute: bool = False,
    cwd: str | Path = ".",
    skip_existing: bool = False,
    check_inputs: bool = False,
    max_submit_cost_usd: float | None = None,
) -> dict[str, Any]:
    results = []
    for step in steps:
        item = dict(step)
        if step.get("status") == "skipped":
            results.append(item)
            continue
        command = str(step.get("command") or "")
        if not command:
            item["status"] = "skipped"
            item["reason"] = "empty_command"
            results.append(item)
            continue
        if bool(step.get("requires_openreview_auth")) and not openreview_auth_available():
            item["status"] = "blocked_missing_openreview_auth"
            item["reason"] = "missing_openreview_cookie_or_token"
            results.append(item)
            if execute:
                break
            continue
        if bool(step.get("requires_openai_key")) and not openai_key_available():
            item["status"] = "blocked_missing_openai_key"
            item["reason"] = "missing_openai_api_key"
            results.append(item)
            if execute:
                break
            continue
        if skip_existing and all_path_outputs_exist(step, cwd=cwd):
            item["status"] = "skipped_existing"
            item["reason"] = "all_path_outputs_exist"
            item["existing_outputs"] = existing_outputs(step, cwd=cwd)
            results.append(item)
            continue
        if check_inputs:
            missing = missing_inputs(command, cwd=cwd)
            if missing:
                item["status"] = "blocked_missing_input"
                item["reason"] = "missing_input"
                item["missing_inputs"] = missing
                results.append(item)
                if execute:
                    break
                continue
        if max_submit_cost_usd is not None and str(step.get("name") or "") == "submit_batch":
            cost, cost_reason = submit_batch_cost(step, cwd=cwd)
            item["estimated_batch_cost_usd"] = cost
            if cost is None:
                item["status"] = "blocked_cost_unknown"
                item["reason"] = cost_reason
                results.append(item)
                if execute:
                    break
                continue
            if cost > max_submit_cost_usd:
                item["status"] = "blocked_cost_limit"
                item["reason"] = "estimated_batch_cost_exceeds_limit"
                item["max_submit_cost_usd"] = max_submit_cost_usd
                results.append(item)
                if execute:
                    break
                continue
        if not execute:
            item["status"] = "dry_run"
            results.append(item)
            continue
        completed = subprocess.run(shlex.split(command), cwd=str(cwd), text=True, capture_output=True, check=False)
        item["returncode"] = completed.returncode
        item["stdout"] = completed.stdout[-4000:]
        item["stderr"] = completed.stderr[-4000:]
        item["status"] = "completed" if completed.returncode == 0 else "failed"
        results.append(item)
        if completed.returncode != 0:
            break
    counts: dict[str, int] = {}
    for item in results:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "schema_version": PLAN_RUNNER_VERSION,
        "execute": execute,
        "skip_existing": skip_existing,
        "check_inputs": check_inputs,
        "max_submit_cost_usd": max_submit_cost_usd,
        "status_counts": counts,
        "steps": results,
    }


def render_plan_runner_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# OpenReview Plan Runner",
        "",
        f"- Execute: `{result.get('execute', False)}`",
        f"- Skip existing: `{result.get('skip_existing', False)}`",
        f"- Check inputs: `{result.get('check_inputs', False)}`",
        f"- Max submit cost USD: `{result.get('max_submit_cost_usd', None)}`",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in sorted((result.get("status_counts") or {}).items()):
        lines.append(f"| {status} | {count} |")
    lines.extend([
        "",
        "## Steps",
        "",
        "| Venue | Step | Status | Reason | Cost |",
        "| --- | --- | --- | --- | ---: |",
    ])
    for step in result.get("steps", []):
        cost = step.get("estimated_batch_cost_usd")
        cost_text = "" if cost is None else f"{float(cost):.4f}"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(step.get("venue_id", "")),
                    str(step.get("name", "")),
                    str(step.get("status", "")),
                    str(step.get("reason", "")),
                    cost_text,
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run or execute OpenReview ingestion plan commands.")
    parser.add_argument("--plan", default="data/validation/openreview_ingestion_plan_2025.json")
    parser.add_argument("--out", default="data/validation/openreview_plan_runner_last.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_plan_runner_last.md")
    parser.add_argument("--venue", action="append", default=[], help="Venue id to include. Repeatable.")
    parser.add_argument("--stage", action="append", default=[], help="Command stage to include. Repeatable.")
    parser.add_argument("--include-blocked", action="store_true", help="Include commands even when readiness is blocked.")
    parser.add_argument("--include-costly", action="store_true", help="Allow submit_batch execution/listing.")
    parser.add_argument("--execute", action="store_true", help="Actually run selected commands. Default is dry-run.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip steps whose file outputs already exist.")
    parser.add_argument("--check-inputs", action="store_true", help="Block steps whose declared command inputs are missing.")
    parser.add_argument("--max-submit-cost-usd", type=float, default=None, help="Block submit_batch if estimated batch cost exceeds this USD limit.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    plan = read_json(args.plan)
    steps = select_plan_steps(
        plan,
        venues=args.venue,
        stages=args.stage,
        include_blocked=args.include_blocked,
        include_costly=args.include_costly,
    )
    result = run_plan_steps(
        steps,
        execute=args.execute,
        skip_existing=args.skip_existing,
        check_inputs=args.check_inputs,
        max_submit_cost_usd=args.max_submit_cost_usd,
    )
    write_json(args.out, result)
    markdown_path = Path(args.markdown)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_plan_runner_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
