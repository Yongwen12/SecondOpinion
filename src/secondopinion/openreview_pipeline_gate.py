from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from .batch_review_scoring import DEFAULT_BATCH_MODEL
from .openreview_auth_check import run_openreview_auth_check
from .openreview_client import OpenReviewClient
from .openreview_ingestion_plan import build_ingestion_plan, render_ingestion_plan_markdown
from .openreview_plan_runner import run_plan_steps, select_plan_steps
from .openreview_scope_audit import audit_openreview_scope, render_scope_audit_markdown
from .openreview_scope_matrix import build_scope_matrix, render_scope_matrix_markdown
from .openreview_secret_check import run_openreview_secret_check
from .openreview_venue_inventory import (
    load_venue_specs,
    render_venue_inventory_markdown,
    run_openreview_venue_inventory,
)


PIPELINE_GATE_SCHEMA_VERSION = "openreview-pipeline-gate-v0.1"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def gate_status(auth: dict[str, Any], plan: dict[str, Any] | None) -> tuple[str, str]:
    if not auth.get("ok"):
        status = str(auth.get("status") or "")
        if status in {"challenge_required", "auth_required"}:
            return "blocked_openreview_auth", "Set OPENREVIEW_COOKIE or OPENREVIEW_TOKEN, then rerun this gate."
        return "blocked_auth_check", str(auth.get("recommendation") or "inspect_auth_check")
    if not plan:
        return "blocked_missing_plan", "Inventory did not produce a plan."
    summary = plan.get("summary") or {}
    ready = summary.get("ready") or []
    blocked_auth = summary.get("blocked_openreview_auth") or []
    needs_manual = summary.get("needs_manual_inspection") or []
    if ready:
        return "ready_for_safe_runner_execute", "Run the generated plan runner through pull/quality/ingest/build/split first; submit OpenAI batch only after cost review."
    if blocked_auth:
        return "blocked_openreview_auth", "Inventory still sees OpenReview auth/challenge gating."
    if needs_manual:
        return "needs_manual_inspection", "Inspect venue invitations or review coverage before scoring."
    return "no_ready_venues", "No venues are ready for pull and score."


def run_openreview_pipeline_gate(
    *,
    venue_specs: list[dict[str, Any]],
    auth_client: OpenReviewClient | None = None,
    inventory_client: OpenReviewClient | None = None,
    auth_invitation: str = "ICLR.cc/2025/Conference/-/Submission",
    sample_limit: int = 50,
    details: str = "replies",
    min_review_coverage: float = 0.5,
    model: str = DEFAULT_BATCH_MODEL,
    pull_limit: int | None = None,
    run_inventory_when_auth_blocked: bool = False,
    secret_check: dict[str, Any] | None = None,
    max_submit_cost_usd: float | None = 25.0,
) -> dict[str, Any]:
    secret_check = secret_check if secret_check is not None else run_openreview_secret_check()
    client = auth_client or OpenReviewClient()
    auth = run_openreview_auth_check(invitation=auth_invitation, sample_limit=1, details=details, client=client)
    inventory = None
    plan = None
    runner = None
    should_run_inventory = bool(auth.get("ok")) or run_inventory_when_auth_blocked
    if should_run_inventory:
        inventory = run_openreview_venue_inventory(
            specs=venue_specs,
            sample_limit=sample_limit,
            details=details,
            client=inventory_client or client,
            min_review_coverage=min_review_coverage,
        )
        plan = build_ingestion_plan(inventory, model=model, pull_limit=pull_limit)
        steps = select_plan_steps(plan)
        runner = run_plan_steps(
            steps,
            skip_existing=True,
            check_inputs=True,
            max_submit_cost_usd=max_submit_cost_usd,
        )
    status, recommendation = gate_status(auth, plan)
    scope_matrix = build_scope_matrix(venues=venue_specs, inventory=inventory)
    scope_audit = audit_openreview_scope(venues=venue_specs, inventory=inventory, plan=plan)
    return {
        "schema_version": PIPELINE_GATE_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "recommendation": recommendation,
        "secret_check": secret_check,
        "auth": auth,
        "inventory_summary": (inventory or {}).get("summary", {}),
        "plan_summary": (plan or {}).get("summary", {}),
        "runner_status_counts": (runner or {}).get("status_counts", {}),
        "scope_matrix_summary": scope_matrix.get("summary", {}),
        "scope_audit_status": scope_audit.get("status", ""),
        "scope_audit_errors": scope_audit.get("errors", []),
        "scope_audit_warnings": scope_audit.get("warnings", []),
        "scope_audit": scope_audit,
        "scope_matrix": scope_matrix,
        "max_submit_cost_usd": max_submit_cost_usd,
        "pull_limit": pull_limit,
        "ran_inventory": inventory is not None,
        "ran_runner_dry_run": runner is not None,
        "inventory": inventory,
        "plan": plan,
        "runner": runner,
    }


def join_values(values: list[Any] | tuple[Any, ...] | None) -> str:
    return ", ".join(str(value) for value in values or []) or "-"


def render_pipeline_gate_markdown(result: dict[str, Any]) -> str:
    secret = result.get("secret_check") or {}
    cookie = secret.get("cookie") or {}
    token = secret.get("token") or {}
    auth = result.get("auth") or {}
    plan_summary = result.get("plan_summary") or {}
    inventory_summary = result.get("inventory_summary") or {}
    scope_matrix = result.get("scope_matrix_summary") or {}
    max_cost = result.get("max_submit_cost_usd", 25)
    lines = [
        "# OpenReview Pipeline Gate",
        "",
        f"- Created: `{result.get('created_at', '')}`",
        f"- Status: `{result.get('status', '')}`",
        f"- Recommendation: {result.get('recommendation', '')}",
        f"- Max submit cost USD: `{max_cost}`",
        f"- Pull limit: `{result.get('pull_limit', None)}`",
        "",
        "## Current Gate",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
        f"| Local secret | `{bool(secret.get('ok'))}` | `{secret.get('recommendation', '')}` |",
        f"| OpenReview auth | `{auth.get('status', '')}` | `{auth.get('recommendation', '')}` |",
        f"| Inventory ran | `{bool(result.get('ran_inventory'))}` | Ready: `{join_values(plan_summary.get('ready'))}` |",
        f"| Runner dry-run | `{bool(result.get('ran_runner_dry_run'))}` | Counts: `{result.get('runner_status_counts', {})}` |",
        f"| Scope matrix | `{join_values(scope_matrix.get('target_or_probe'))}` | Excluded: `{join_values(scope_matrix.get('excluded'))}` |",
        f"| Scope audit | `{result.get('scope_audit_status', '')}` | Errors: `{len(result.get('scope_audit_errors') or [])}`, warnings: `{len(result.get('scope_audit_warnings') or [])}` |",
        "",
        "## Secret",
        "",
        f"- Cookie source: `{cookie.get('source', '') or '-'}`",
        f"- Cookie format: `{cookie.get('format', '') or '-'}`",
        f"- Cookie names: `{join_values(cookie.get('cookie_names'))}`",
        f"- Token source: `{token.get('source', '') or '-'}`",
        "",
        "## Venue Summaries",
        "",
        f"- Inventory ready: `{join_values(inventory_summary.get('ready_to_pull_and_score'))}`",
        f"- Needs OpenReview auth: `{join_values(inventory_summary.get('needs_openreview_auth'))}`",
        f"- Plan ready: `{join_values(plan_summary.get('ready'))}`",
        f"- Plan blocked auth: `{join_values(plan_summary.get('blocked_openreview_auth'))}`",
        "",
        "## Next Commands",
        "",
        "```powershell",
    ]
    if not secret.get("ok"):
        lines.extend(
            [
                "python -m secondopinion.tools.openreview_auth_setup --cookie-file path\\to\\browser-cookies.txt",
                "python -m secondopinion.tools.openreview_secret_check --out data/validation/openreview_secret_check.json",
                "python -m secondopinion.tools.openreview_scope_matrix --venues data/config/openreview_venues_2025.json --out data/validation/openreview_scope_matrix_2025.json --markdown reports/validation/openreview_scope_matrix_2025.md",
                "python -m secondopinion.tools.openreview_pipeline_gate --venues data/config/openreview_venues_2025.json --out data/validation/openreview_pipeline_gate.json",
                "python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json",
            ]
        )
    elif result.get("status") == "ready_for_safe_runner_execute":
        lines.extend(
            [
                f"python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue ICLR --execute-safe --max-submit-cost-usd {max_cost} --batch-cost-limit-usd {max_cost}",
                f"python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --execute-safe --max-submit-cost-usd {max_cost} --batch-cost-limit-usd {max_cost}",
                "python -m secondopinion.tools.openreview_scope_matrix --venues data/config/openreview_venues_2025.json --inventory data/validation/openreview_venue_inventory_2025.json --out data/validation/openreview_scope_matrix_2025.json --markdown reports/validation/openreview_scope_matrix_2025.md",
                f"python -m secondopinion.tools.batch_cost_review --manifest data/batch/**/*_manifest.json --out data/validation/batch_cost_review.json --markdown reports/validation/batch_cost_review.md --max-total-cost-usd {max_cost}",
            ]
        )
    else:
        lines.append(
            "python -m secondopinion.tools.openreview_pipeline_gate --venues data/config/openreview_venues_2025.json --out data/validation/openreview_pipeline_gate.json"
        )
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the OpenReview auth/inventory/plan/runner gate.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--auth-out", default="data/validation/openreview_auth_check.json")
    parser.add_argument("--inventory-out", default="data/validation/openreview_venue_inventory_2025.json")
    parser.add_argument("--inventory-markdown", default="reports/validation/openreview_venue_inventory_2025.md")
    parser.add_argument("--plan-out", default="data/validation/openreview_ingestion_plan_2025.json")
    parser.add_argument("--plan-markdown", default="reports/validation/openreview_ingestion_plan_2025.md")
    parser.add_argument("--runner-out", default="data/validation/openreview_plan_runner_last.json")
    parser.add_argument("--scope-audit-out", default="data/validation/openreview_scope_audit_2025.json")
    parser.add_argument("--scope-audit-markdown", default="reports/validation/openreview_scope_audit_2025.md")
    parser.add_argument("--scope-matrix-out", default="data/validation/openreview_scope_matrix_2025.json")
    parser.add_argument("--scope-matrix-markdown", default="reports/validation/openreview_scope_matrix_2025.md")
    parser.add_argument("--out", default="data/validation/openreview_pipeline_gate.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_pipeline_gate.md")
    parser.add_argument("--auth-invitation", default="ICLR.cc/2025/Conference/-/Submission")
    parser.add_argument("--sample-limit", type=int, default=50)
    parser.add_argument("--details", default="replies")
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--min-review-coverage", type=float, default=0.5)
    parser.add_argument("--model", default=os.environ.get("SECONDOPINION_BATCH_MODEL", DEFAULT_BATCH_MODEL))
    parser.add_argument("--pull-limit", type=int, default=None)
    parser.add_argument("--probe-when-auth-blocked", action="store_true")
    parser.add_argument("--max-submit-cost-usd", type=float, default=25.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    client = OpenReviewClient(base_url=args.api_base, timeout=args.timeout)
    result = run_openreview_pipeline_gate(
        venue_specs=load_venue_specs(args.venues),
        auth_client=client,
        auth_invitation=args.auth_invitation,
        sample_limit=args.sample_limit,
        details=args.details,
        min_review_coverage=args.min_review_coverage,
        model=args.model,
        pull_limit=args.pull_limit,
        run_inventory_when_auth_blocked=args.probe_when_auth_blocked,
        max_submit_cost_usd=args.max_submit_cost_usd,
    )
    write_json(args.auth_out, result["auth"])
    if result.get("inventory"):
        write_json(args.inventory_out, result["inventory"])
        write_text(args.inventory_markdown, render_venue_inventory_markdown(result["inventory"]))
    if result.get("plan"):
        write_json(args.plan_out, result["plan"])
        write_text(args.plan_markdown, render_ingestion_plan_markdown(result["plan"]))
    if result.get("runner"):
        write_json(args.runner_out, result["runner"])
    if result.get("scope_audit"):
        write_json(args.scope_audit_out, result["scope_audit"])
        write_text(args.scope_audit_markdown, render_scope_audit_markdown(result["scope_audit"]))
    if result.get("scope_matrix"):
        write_json(args.scope_matrix_out, result["scope_matrix"])
        write_text(args.scope_matrix_markdown, render_scope_matrix_markdown(result["scope_matrix"]))
    slim = {key: value for key, value in result.items() if key not in {"inventory", "plan", "runner", "scope_audit", "scope_matrix"}}
    write_json(args.out, slim)
    write_text(args.markdown, render_pipeline_gate_markdown(slim))
    print(json.dumps(slim, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
