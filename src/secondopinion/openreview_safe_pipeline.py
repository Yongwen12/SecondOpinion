from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .batch_cost_review import review_batch_costs, render_batch_cost_review_markdown
from .batch_review_scoring import DEFAULT_BATCH_MODEL
from .openreview_auth_setup import install_openreview_cookie
from .openreview_client import OpenReviewClient
from .openreview_pipeline_gate import (
    render_pipeline_gate_markdown,
    run_openreview_pipeline_gate,
    write_json,
    write_text,
)
from .openreview_pilot_readiness import build_openreview_pilot_readiness, render_pilot_readiness_markdown
from .openreview_plan_runner import render_plan_runner_markdown, run_plan_steps, select_plan_steps
from .openreview_scale_estimate import build_openreview_scale_estimate, render_openreview_scale_estimate_markdown
from .openreview_scope_audit import render_scope_audit_markdown
from .openreview_scope_matrix import render_scope_matrix_markdown
from .openreview_venue_inventory import load_venue_specs, render_venue_inventory_markdown
from .openreview_ingestion_plan import render_ingestion_plan_markdown


SAFE_PIPELINE_VERSION = "openreview-safe-pipeline-v0.1"
SAFE_STAGES = ["pull", "filter_normalized", "quality", "ingest", "build_batch", "split_batch"]


def stage_list(value: list[str] | None = None) -> list[str]:
    return list(value or SAFE_STAGES)


def status_counts(items: list[dict[str, Any]], key: str = "status") -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get(key) or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def write_gate_artifacts(result: dict[str, Any], *, paths: dict[str, str]) -> None:
    write_json(paths["auth_out"], result["auth"])
    if result.get("inventory"):
        write_json(paths["inventory_out"], result["inventory"])
        write_text(paths["inventory_markdown"], render_venue_inventory_markdown(result["inventory"]))
    if result.get("plan"):
        write_json(paths["plan_out"], result["plan"])
        write_text(paths["plan_markdown"], render_ingestion_plan_markdown(result["plan"]))
    if result.get("runner"):
        write_json(paths["runner_out"], result["runner"])
        write_text(paths["runner_markdown"], render_plan_runner_markdown(result["runner"]))
    if result.get("scope_audit"):
        write_json(paths["scope_audit_out"], result["scope_audit"])
        write_text(paths["scope_audit_markdown"], render_scope_audit_markdown(result["scope_audit"]))
    if result.get("scope_matrix"):
        write_json(paths["scope_matrix_out"], result["scope_matrix"])
        write_text(paths["scope_matrix_markdown"], render_scope_matrix_markdown(result["scope_matrix"]))
    slim = {key: value for key, value in result.items() if key not in {"inventory", "plan", "runner", "scope_audit", "scope_matrix"}}
    write_json(paths["gate_out"], slim)
    write_text(paths["gate_markdown"], render_pipeline_gate_markdown(slim))


def default_paths() -> dict[str, str]:
    return {
        "auth_out": "data/validation/openreview_auth_check.json",
        "inventory_out": "data/validation/openreview_venue_inventory_2025.json",
        "inventory_markdown": "reports/validation/openreview_venue_inventory_2025.md",
        "plan_out": "data/validation/openreview_ingestion_plan_2025.json",
        "plan_markdown": "reports/validation/openreview_ingestion_plan_2025.md",
        "runner_out": "data/validation/openreview_plan_runner_last.json",
        "runner_markdown": "reports/validation/openreview_plan_runner_last.md",
        "scope_audit_out": "data/validation/openreview_scope_audit_2025.json",
        "scope_audit_markdown": "reports/validation/openreview_scope_audit_2025.md",
        "scope_matrix_out": "data/validation/openreview_scope_matrix_2025.json",
        "scope_matrix_markdown": "reports/validation/openreview_scope_matrix_2025.md",
        "gate_out": "data/validation/openreview_pipeline_gate.json",
        "gate_markdown": "reports/validation/openreview_pipeline_gate.md",
        "safe_runner_out": "data/validation/openreview_safe_runner_last.json",
        "safe_runner_markdown": "reports/validation/openreview_safe_runner_last.md",
        "cost_out": "data/validation/batch_cost_review.json",
        "cost_markdown": "reports/validation/batch_cost_review.md",
        "summary_out": "data/validation/openreview_safe_pipeline.json",
        "summary_markdown": "reports/validation/openreview_safe_pipeline.md",
        "auth_setup_out": "data/validation/openreview_auth_setup.json",
        "pilot_readiness_out": "data/validation/openreview_pilot_readiness.json",
        "pilot_readiness_markdown": "reports/validation/openreview_pilot_readiness.md",
        "scale_estimate_out": "data/validation/openreview_scale_estimate.json",
        "scale_estimate_markdown": "reports/validation/openreview_scale_estimate.md",
    }


def run_openreview_safe_pipeline(
    *,
    venue_specs: list[dict[str, Any]],
    auth_client: OpenReviewClient | None = None,
    inventory_client: OpenReviewClient | None = None,
    cookie: str = "",
    cookie_file: str = "",
    out_cookie: str | Path = "data/secrets/openreview.cookie",
    env_path: str | Path = ".env",
    execute_safe: bool = False,
    venues: list[str] | None = None,
    stages: list[str] | None = None,
    max_submit_cost_usd: float | None = 25.0,
    batch_cost_limit_usd: float | None = 25.0,
    batch_manifest_patterns: list[str] | None = None,
    model: str = DEFAULT_BATCH_MODEL,
    pull_limit: int | None = None,
    probe_when_auth_blocked: bool = False,
    api_base: str = "https://api2.openreview.net",
    timeout: int = 60,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    paths = {**default_paths(), **(paths or {})}
    selected_stages = stage_list(stages)
    auth_setup = None
    if cookie.strip() or cookie_file.strip():
        auth_setup = install_openreview_cookie(
            cookie=cookie,
            cookie_file=cookie_file,
            out_cookie=out_cookie,
            env_path=env_path,
        )
        write_json(paths["auth_setup_out"], auth_setup)
        if not auth_setup.get("ok"):
            summary = blocked_auth_setup_summary(
                auth_setup=auth_setup,
                execute_safe=execute_safe,
                venues=venues,
                pull_limit=pull_limit,
                selected_stages=selected_stages,
                paths=paths,
            )
            write_json(paths["summary_out"], summary)
            write_text(paths["summary_markdown"], render_safe_pipeline_markdown(summary))
            return summary
    if auth_client is None:
        auth_client = OpenReviewClient(base_url=api_base, timeout=timeout)
    gate = run_openreview_pipeline_gate(
        venue_specs=venue_specs,
        auth_client=auth_client,
        inventory_client=inventory_client,
        model=model,
        pull_limit=pull_limit,
        run_inventory_when_auth_blocked=probe_when_auth_blocked,
        max_submit_cost_usd=max_submit_cost_usd,
    )
    write_gate_artifacts(gate, paths=paths)

    cost_review = review_batch_costs(
        patterns=batch_manifest_patterns or ["data/batch/**/*_manifest.json"],
        max_total_cost_usd=batch_cost_limit_usd,
    )
    write_json(paths["cost_out"], cost_review)
    write_text(paths["cost_markdown"], render_batch_cost_review_markdown(cost_review))
    scale_estimate = build_openreview_scale_estimate(
        inventory=gate.get("inventory") or {"venues": []},
        batch_cost=cost_review,
        max_total_cost_usd=batch_cost_limit_usd or 25.0,
    )
    write_json(paths["scale_estimate_out"], scale_estimate)
    write_text(paths["scale_estimate_markdown"], render_openreview_scale_estimate_markdown(scale_estimate))

    safe_runner = None
    pilot_readiness = None
    action = "blocked_before_safe_execute"
    plan = gate.get("plan")
    if gate.get("status") == "ready_for_safe_runner_execute" and plan:
        steps = select_plan_steps(
            plan,
            venues=venues,
            stages=selected_stages,
            include_blocked=False,
            include_costly=False,
        )
        safe_runner = run_plan_steps(
            steps,
            execute=execute_safe,
            skip_existing=True,
            check_inputs=True,
            max_submit_cost_usd=max_submit_cost_usd,
        )
        write_json(paths["safe_runner_out"], safe_runner)
        write_text(paths["safe_runner_markdown"], render_plan_runner_markdown(safe_runner))
        action = "executed_safe_stages" if execute_safe else "dry_run_safe_stages"
        if venues:
            pilot_readiness = build_openreview_pilot_readiness(plan=plan, venue_id=venues[0])
            write_json(paths["pilot_readiness_out"], pilot_readiness)
            write_text(paths["pilot_readiness_markdown"], render_pilot_readiness_markdown(pilot_readiness))

    summary = {
        "schema_version": SAFE_PIPELINE_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "action": action,
        "execute_safe": execute_safe,
        "auth_setup": auth_setup or {},
        "selected_venues": [value.upper() for value in venues or []],
        "pull_limit": pull_limit,
        "safe_stages": selected_stages,
        "gate_status": gate.get("status", ""),
        "gate_recommendation": gate.get("recommendation", ""),
        "ran_inventory": bool(gate.get("ran_inventory")),
        "ran_runner_dry_run": bool(gate.get("ran_runner_dry_run")),
        "inventory_summary": gate.get("inventory_summary", {}),
        "plan_summary": gate.get("plan_summary", {}),
        "scope_matrix_summary": gate.get("scope_matrix_summary", {}),
        "safe_runner_status_counts": (safe_runner or {}).get("status_counts", {}),
        "batch_cost_summary": (cost_review or {}).get("summary", {}),
        "scale_estimate_status": (scale_estimate or {}).get("status", ""),
        "scale_estimate_summary": (scale_estimate or {}).get("summary", {}),
        "pilot_readiness_status": (pilot_readiness or {}).get("status", ""),
        "pilot_readiness_errors": (pilot_readiness or {}).get("errors", []),
        "paths": paths,
    }
    write_json(paths["summary_out"], summary)
    write_text(paths["summary_markdown"], render_safe_pipeline_markdown(summary))
    return summary



def blocked_auth_setup_summary(
    *,
    auth_setup: dict[str, Any],
    execute_safe: bool,
    venues: list[str] | None,
    pull_limit: int | None,
    selected_stages: list[str],
    paths: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": SAFE_PIPELINE_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "action": "blocked_auth_setup_failed",
        "execute_safe": execute_safe,
        "auth_setup": auth_setup,
        "selected_venues": [value.upper() for value in venues or []],
        "pull_limit": pull_limit,
        "safe_stages": selected_stages,
        "gate_status": "not_run",
        "gate_recommendation": "Fix --cookie or --cookie-file, then rerun safe pipeline.",
        "ran_inventory": False,
        "ran_runner_dry_run": False,
        "inventory_summary": {},
        "plan_summary": {},
        "scope_matrix_summary": {},
        "safe_runner_status_counts": {},
        "batch_cost_summary": {},
        "scale_estimate_status": "",
        "scale_estimate_summary": {},
        "pilot_readiness_status": "",
        "pilot_readiness_errors": [],
        "paths": paths,
    }


def render_safe_pipeline_markdown(summary: dict[str, Any]) -> str:
    scope = summary.get("scope_matrix_summary") or {}
    plan = summary.get("plan_summary") or {}
    cost = summary.get("batch_cost_summary") or {}
    scale = summary.get("scale_estimate_summary") or {}
    auth_setup = summary.get("auth_setup") or {}
    auth_cookie = auth_setup.get("cookie") or {}
    lines = [
        "# OpenReview Safe Pipeline",
        "",
        f"- Created: `{summary.get('created_at', '')}`",
        f"- Action: `{summary.get('action', '')}`",
        f"- Execute safe stages: `{summary.get('execute_safe', False)}`",
        f"- Auth setup: `{auth_setup.get('recommendation', '-')}`",
        f"- Auth cookie names: `{', '.join(auth_cookie.get('cookie_names') or []) or '-'}`",
        f"- Selected venues: `{', '.join(summary.get('selected_venues') or []) or 'all ready venues'}`",
        f"- Pull limit: `{summary.get('pull_limit', None)}`",
        f"- Gate status: `{summary.get('gate_status', '')}`",
        f"- Recommendation: {summary.get('gate_recommendation', '')}",
        f"- Inventory probe ran: `{summary.get('ran_inventory', False)}`",
        f"- Runner dry-run ran: `{summary.get('ran_runner_dry_run', False)}`",
        f"- Target/probe venues: `{', '.join(scope.get('target_or_probe') or []) or '-'}`",
        f"- Excluded venues: `{', '.join(scope.get('excluded') or []) or '-'}`",
        f"- Plan ready: `{', '.join(plan.get('ready') or []) or '-'}`",
        f"- Plan blocked auth: `{', '.join(plan.get('blocked_openreview_auth') or []) or '-'}`",
        f"- Safe runner counts: `{summary.get('safe_runner_status_counts', {})}`",
        f"- Estimated batch cost USD: `{cost.get('estimated_batch_cost_usd', '-')}`",
        f"- Scale estimate: `{summary.get('scale_estimate_status', '-')}`",
        f"- Scale blocked venues: `{', '.join(scale.get('blocked_venues') or []) or '-'}`",
        f"- Pilot readiness: `{summary.get('pilot_readiness_status', '-')}`",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OpenReview 2025 gate, inventory reports, optional safe pull/build stages, and cost review.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--cookie", default="", help="Raw Cookie header. Prefer --cookie-file to avoid shell history.")
    parser.add_argument("--cookie-file", default="", help="Raw Cookie header file or Netscape cookie jar export; installed before gate runs.")
    parser.add_argument("--out-cookie", default="data/secrets/openreview.cookie")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--execute-safe", action="store_true", help="Execute only safe non-OpenAI-submit stages after gate is ready.")
    parser.add_argument("--venue", action="append", default=[], help="Venue id to execute after inventory is ready. Repeatable. Defaults to all ready venues.")
    parser.add_argument("--stage", action="append", default=[], help="Safe stage to run. Defaults to pull/filter/quality/ingest/build/split.")
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--model", default=DEFAULT_BATCH_MODEL)
    parser.add_argument("--pull-limit", type=int, default=None, help="Limit papers per venue pull for small pilot runs.")
    parser.add_argument("--probe-when-auth-blocked", action="store_true", help="Still probe each venue when the initial OpenReview auth check is challenged.")
    parser.add_argument("--max-submit-cost-usd", type=float, default=25.0)
    parser.add_argument("--batch-cost-limit-usd", type=float, default=25.0)
    parser.add_argument("--batch-manifest", action="append", default=[], help="Batch manifest glob/path for cost review. Repeatable.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    summary = run_openreview_safe_pipeline(
        venue_specs=load_venue_specs(args.venues),
        cookie=args.cookie,
        cookie_file=args.cookie_file,
        out_cookie=args.out_cookie,
        env_path=args.env,
        execute_safe=args.execute_safe,
        venues=args.venue or None,
        stages=args.stage or None,
        max_submit_cost_usd=args.max_submit_cost_usd,
        batch_cost_limit_usd=args.batch_cost_limit_usd,
        batch_manifest_patterns=args.batch_manifest or None,
        model=args.model,
        pull_limit=args.pull_limit,
        probe_when_auth_blocked=args.probe_when_auth_blocked,
        api_base=args.api_base,
        timeout=args.timeout,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
