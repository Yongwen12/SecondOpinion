from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .batch_review_scoring import DEFAULT_BATCH_MODEL
from .openreview_ingestion_plan import build_ingestion_plan, read_json, render_ingestion_plan_markdown, write_json
from .openreview_plan_runner import render_plan_runner_markdown, run_plan_steps, select_plan_steps
from .openreview_safe_pipeline import SAFE_STAGES, stage_list


RESOLVED_PIPELINE_SCHEMA_VERSION = "openreview-resolved-pipeline-v0.1"


def write_text(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def default_paths() -> dict[str, str]:
    return {
        "plan_out": "data/validation/openreview_resolved_ingestion_plan_2025.json",
        "plan_markdown": "reports/validation/openreview_resolved_ingestion_plan_2025.md",
        "runner_out": "data/validation/openreview_resolved_runner_last.json",
        "runner_markdown": "reports/validation/openreview_resolved_runner_last.md",
        "summary_out": "data/validation/openreview_resolved_pipeline.json",
        "summary_markdown": "reports/validation/openreview_resolved_pipeline.md",
    }


def run_openreview_resolved_pipeline(
    *,
    resolved_inventory: dict[str, Any],
    execute_safe: bool = False,
    venues: list[str] | None = None,
    stages: list[str] | None = None,
    pull_limit: int | None = 50,
    model: str = DEFAULT_BATCH_MODEL,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    paths = {**default_paths(), **(paths or {})}
    selected_stages = stage_list(stages or SAFE_STAGES)
    plan = build_ingestion_plan(resolved_inventory, model=model, pull_limit=pull_limit)
    write_json(paths["plan_out"], plan)
    write_text(paths["plan_markdown"], render_ingestion_plan_markdown(plan))
    steps = select_plan_steps(plan, venues=venues, stages=selected_stages, include_blocked=False, include_costly=False)
    runner = run_plan_steps(steps, execute=execute_safe, skip_existing=True, check_inputs=True, max_submit_cost_usd=25.0)
    write_json(paths["runner_out"], runner)
    write_text(paths["runner_markdown"], render_plan_runner_markdown(runner))
    ready = plan.get("summary", {}).get("ready") or []
    action = "executed_safe_stages" if execute_safe and ready else "dry_run_safe_stages" if ready else "blocked_no_resolved_ready_venues"
    summary = {
        "schema_version": RESOLVED_PIPELINE_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "action": action,
        "execute_safe": execute_safe,
        "selected_venues": [value.upper() for value in venues or []],
        "safe_stages": selected_stages,
        "pull_limit": pull_limit,
        "plan_summary": plan.get("summary", {}),
        "runner_status_counts": runner.get("status_counts", {}),
        "openai_submit_used": False,
        "paths": paths,
    }
    write_json(paths["summary_out"], summary)
    write_text(paths["summary_markdown"], render_resolved_pipeline_markdown(summary))
    return summary


def render_resolved_pipeline_markdown(summary: dict[str, Any]) -> str:
    plan = summary.get("plan_summary") or {}
    return "\n".join(
        [
            "# OpenReview Resolved Pipeline",
            "",
            f"- Created: `{summary.get('created_at', '')}`",
            f"- Action: `{summary.get('action', '')}`",
            f"- Execute safe stages: `{summary.get('execute_safe', False)}`",
            f"- Ready venues: `{', '.join(plan.get('ready') or []) or '-'}`",
            f"- Blocked auth: `{', '.join(plan.get('blocked_openreview_auth') or []) or '-'}`",
            f"- Manual inspection: `{', '.join(plan.get('needs_manual_inspection') or []) or '-'}`",
            f"- Excluded: `{', '.join(plan.get('excluded_not_scored') or []) or '-'}`",
            f"- Runner counts: `{summary.get('runner_status_counts', {})}`",
            f"- OpenAI submit used: `{summary.get('openai_submit_used', False)}`",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an ingestion plan from resolved OpenReview inventory using only safe stages by default.")
    parser.add_argument("--resolved-inventory", default="data/validation/openreview_resolved_inventory_2025.json")
    parser.add_argument("--execute-safe", action="store_true")
    parser.add_argument("--venue", action="append", default=[])
    parser.add_argument("--stage", action="append", default=[])
    parser.add_argument("--pull-limit", type=int, default=50)
    parser.add_argument("--model", default=DEFAULT_BATCH_MODEL)
    parser.add_argument("--out", default="data/validation/openreview_resolved_pipeline.json")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    paths = default_paths()
    paths["summary_out"] = args.out
    summary = run_openreview_resolved_pipeline(
        resolved_inventory=read_json(args.resolved_inventory),
        execute_safe=args.execute_safe,
        venues=args.venue or None,
        stages=args.stage or None,
        pull_limit=args.pull_limit,
        model=args.model,
        paths=paths,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
