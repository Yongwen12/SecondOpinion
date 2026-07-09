from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .batch_cost_review import review_batch_costs, render_batch_cost_review_markdown, write_json as write_batch_json, write_markdown as write_batch_markdown
from .openreview_batch_submit_preflight import build_batch_submit_preflight, render_batch_submit_preflight_markdown
from .openreview_cookie_handoff import build_cookie_handoff, render_cookie_handoff_markdown
from .openreview_cookie_preflight import build_cookie_preflight, render_cookie_preflight_markdown
from .openreview_data_minimization_audit import build_data_minimization_audit, render_data_minimization_audit_markdown
from .openreview_invitation_audit import audit_invitation_candidates, load_venues, render_invitation_audit_markdown
from .openreview_probe_queue import build_probe_queue, render_probe_queue_markdown
from .openreview_probe_queue_runner import render_probe_queue_runner_markdown, run_probe_queue
from .openreview_probe_results import resolve_probe_results, render_probe_results_markdown
from .openreview_resolved_inventory import build_resolved_inventory, render_resolved_inventory_markdown
from .openreview_resolved_pipeline import run_openreview_resolved_pipeline
from .openreview_readiness_dashboard import build_openreview_readiness_dashboard, render_openreview_readiness_dashboard_markdown
from .openreview_report_consistency import check_openreview_report_consistency, render_report_consistency_markdown
from .openreview_scale_estimate import build_openreview_scale_estimate, read_json_if_exists, render_openreview_scale_estimate_markdown, write_json, write_text
from .openreview_scope_audit import audit_openreview_scope, render_scope_audit_markdown
from .openreview_snapshot_recovery import build_openreview_snapshot_recovery_report, render_openreview_snapshot_recovery_markdown

LOCAL_REFRESH_SCHEMA_VERSION = "openreview-local-refresh-v0.1"


def refresh_openreview_local_reports(
    *,
    inventory_path: str = "data/validation/openreview_venue_inventory_2025.json",
    venues_path: str = "data/config/openreview_venues_2025.json",
    snapshot_root: str = "data/raw/openreview",
    raw_root: str = "data/raw",
    batch_manifest_patterns: list[str] | None = None,
    probe_result_patterns: list[str] | None = None,
    data_minimization_normalized_patterns: list[str] | None = None,
    data_minimization_batch_patterns: list[str] | None = None,
    max_total_cost_usd: float = 25.0,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    paths = {
        "invitation_audit_out": "data/validation/openreview_invitation_audit_2025.json",
        "invitation_audit_markdown": "reports/validation/openreview_invitation_audit_2025.md",
        "probe_queue_out": "data/validation/openreview_probe_queue_2025.json",
        "probe_queue_markdown": "reports/validation/openreview_probe_queue_2025.md",
        "probe_queue_runner_out": "data/validation/openreview_probe_queue_runner.json",
        "probe_queue_runner_markdown": "reports/validation/openreview_probe_queue_runner.md",
        "challenge_resume_out": "data/validation/openreview_challenge_resume.json",
        "cookie_handoff_out": "data/validation/openreview_cookie_handoff.json",
        "cookie_preflight_out": "data/validation/openreview_cookie_preflight.json",
        "cookie_preflight_markdown": "reports/validation/openreview_cookie_preflight.md",
        "cookie_handoff_markdown": "reports/validation/openreview_cookie_handoff.md",
        "scope_audit_out": "data/validation/openreview_scope_audit_2025.json",
        "scope_audit_markdown": "reports/validation/openreview_scope_audit_2025.md",
        "data_minimization_out": "data/validation/openreview_data_minimization_audit.json",
        "data_minimization_markdown": "reports/validation/openreview_data_minimization_audit.md",
        "probe_results_out": "data/validation/openreview_probe_results_2025.json",
        "probe_results_markdown": "reports/validation/openreview_probe_results_2025.md",
        "resolved_inventory_out": "data/validation/openreview_resolved_inventory_2025.json",
        "resolved_inventory_markdown": "reports/validation/openreview_resolved_inventory_2025.md",
        "resolved_pipeline_out": "data/validation/openreview_resolved_pipeline.json",
        "resolved_pipeline_markdown": "reports/validation/openreview_resolved_pipeline.md",
        "resolved_plan_out": "data/validation/openreview_resolved_ingestion_plan_2025.json",
        "resolved_plan_markdown": "reports/validation/openreview_resolved_ingestion_plan_2025.md",
        "resolved_runner_out": "data/validation/openreview_resolved_runner_last.json",
        "resolved_runner_markdown": "reports/validation/openreview_resolved_runner_last.md",
        "snapshot_recovery_out": "data/validation/openreview_snapshot_recovery.json",
        "snapshot_recovery_markdown": "reports/validation/openreview_snapshot_recovery.md",
        "batch_cost_out": "data/validation/batch_cost_review.json",
        "batch_cost_markdown": "reports/validation/batch_cost_review.md",
        "scale_estimate_out": "data/validation/openreview_scale_estimate.json",
        "scale_estimate_markdown": "reports/validation/openreview_scale_estimate.md",
        "dashboard_out": "data/validation/openreview_readiness_dashboard.json",
        "dashboard_markdown": "reports/validation/openreview_readiness_dashboard.md",
        "consistency_out": "data/validation/openreview_report_consistency.json",
        "consistency_markdown": "reports/validation/openreview_report_consistency.md",
        "submit_preflight_out": "data/validation/openreview_batch_submit_preflight.json",
        "submit_preflight_markdown": "reports/validation/openreview_batch_submit_preflight.md",
        "refresh_out": "data/validation/openreview_local_refresh.json",
        **(paths or {}),
    }
    venues = load_venues(venues_path)
    invitation_audit = audit_invitation_candidates(venues)
    write_json(paths["invitation_audit_out"], invitation_audit)
    write_text(paths["invitation_audit_markdown"], render_invitation_audit_markdown(invitation_audit))

    probe_queue = build_probe_queue(venues=venues)
    write_json(paths["probe_queue_out"], probe_queue)
    write_text(paths["probe_queue_markdown"], render_probe_queue_markdown(probe_queue))

    existing_probe_queue_runner = read_json_if_exists(paths["probe_queue_runner_out"])
    if existing_probe_queue_runner.get("execute") is True:
        probe_queue_runner = existing_probe_queue_runner
    else:
        probe_queue_runner = run_probe_queue(queue=probe_queue, execute=False)
        write_json(paths["probe_queue_runner_out"], probe_queue_runner)
        write_text(paths["probe_queue_runner_markdown"], render_probe_queue_runner_markdown(probe_queue_runner))

    cookie_handoff = build_cookie_handoff(
        secret_check=read_json_if_exists("data/validation/openreview_secret_check.json"),
        challenge_resume=read_json_if_exists(paths["challenge_resume_out"]),
    )
    write_json(paths["cookie_handoff_out"], cookie_handoff)
    write_text(paths["cookie_handoff_markdown"], render_cookie_handoff_markdown(cookie_handoff))

    cookie_preflight = build_cookie_preflight()
    write_json(paths["cookie_preflight_out"], cookie_preflight)
    write_text(paths["cookie_preflight_markdown"], render_cookie_preflight_markdown(cookie_preflight))

    scope_audit = audit_openreview_scope(
        venues=venues,
        inventory=read_json_if_exists(inventory_path),
        plan=read_json_if_exists("data/validation/openreview_ingestion_plan_2025.json"),
    )
    write_json(paths["scope_audit_out"], scope_audit)
    write_text(paths["scope_audit_markdown"], render_scope_audit_markdown(scope_audit))

    data_minimization = build_data_minimization_audit(
        normalized_patterns=data_minimization_normalized_patterns,
        batch_patterns=data_minimization_batch_patterns,
    )
    write_json(paths["data_minimization_out"], data_minimization)
    write_text(paths["data_minimization_markdown"], render_data_minimization_audit_markdown(data_minimization))

    probe_results = resolve_probe_results(patterns=probe_result_patterns or ["data/validation/openreview_probe_*_c*_*.json"], queue=probe_queue)
    write_json(paths["probe_results_out"], probe_results)
    write_text(paths["probe_results_markdown"], render_probe_results_markdown(probe_results))

    resolved_inventory = build_resolved_inventory(venue_specs=venues, probe_results=probe_results)
    write_json(paths["resolved_inventory_out"], resolved_inventory)
    write_text(paths["resolved_inventory_markdown"], render_resolved_inventory_markdown(resolved_inventory))

    resolved_pipeline = run_openreview_resolved_pipeline(
        resolved_inventory=resolved_inventory,
        execute_safe=False,
        pull_limit=50,
        paths={
            "plan_out": paths["resolved_plan_out"],
            "plan_markdown": paths["resolved_plan_markdown"],
            "runner_out": paths["resolved_runner_out"],
            "runner_markdown": paths["resolved_runner_markdown"],
            "summary_out": paths["resolved_pipeline_out"],
            "summary_markdown": paths["resolved_pipeline_markdown"],
        },
    )

    snapshot_recovery = build_openreview_snapshot_recovery_report(root=snapshot_root, raw_root=raw_root)
    write_json(paths["snapshot_recovery_out"], snapshot_recovery)
    write_text(paths["snapshot_recovery_markdown"], render_openreview_snapshot_recovery_markdown(snapshot_recovery))

    batch_cost = review_batch_costs(
        patterns=batch_manifest_patterns or ["data/batch/**/*_manifest.json"],
        max_total_cost_usd=max_total_cost_usd,
    )
    write_batch_json(paths["batch_cost_out"], batch_cost)
    write_batch_markdown(paths["batch_cost_markdown"], render_batch_cost_review_markdown(batch_cost))

    scale_estimate = build_openreview_scale_estimate(
        inventory=read_json_if_exists(inventory_path),
        batch_cost=batch_cost,
        max_total_cost_usd=max_total_cost_usd,
    )
    write_json(paths["scale_estimate_out"], scale_estimate)
    write_text(paths["scale_estimate_markdown"], render_openreview_scale_estimate_markdown(scale_estimate))

    dashboard = build_openreview_readiness_dashboard(
        paths={
            "invitation_audit": paths["invitation_audit_out"],
            "probe_queue": paths["probe_queue_out"],
            "probe_queue_runner": paths["probe_queue_runner_out"],
            "challenge_resume": paths["challenge_resume_out"],
            "cookie_preflight": paths["cookie_preflight_out"],
            "scope_audit": paths["scope_audit_out"],
            "data_minimization": paths["data_minimization_out"],
            "probe_results": paths["probe_results_out"],
            "resolved_inventory": paths["resolved_inventory_out"],
            "resolved_pipeline": paths["resolved_pipeline_out"],
            "snapshot_recovery": paths["snapshot_recovery_out"],
            "batch_cost": paths["batch_cost_out"],
            "scale_estimate": paths["scale_estimate_out"],
        }
    )
    write_json(paths["dashboard_out"], dashboard)
    write_text(paths["dashboard_markdown"], render_openreview_readiness_dashboard_markdown(dashboard))

    consistency = check_openreview_report_consistency(
        dashboard_path=paths["dashboard_out"],
        batch_cost_path=paths["batch_cost_out"],
        scale_estimate_path=paths["scale_estimate_out"],
    )
    write_json(paths["consistency_out"], consistency)
    write_text(paths["consistency_markdown"], render_report_consistency_markdown(consistency))

    submit_preflight = build_batch_submit_preflight(
        consistency_path=paths["consistency_out"],
        batch_cost_path=paths["batch_cost_out"],
        max_total_cost_usd=max_total_cost_usd,
    )
    write_json(paths["submit_preflight_out"], submit_preflight)
    write_text(paths["submit_preflight_markdown"], render_batch_submit_preflight_markdown(submit_preflight))

    dashboard = build_openreview_readiness_dashboard(
        paths={
            "invitation_audit": paths["invitation_audit_out"],
            "probe_queue": paths["probe_queue_out"],
            "probe_queue_runner": paths["probe_queue_runner_out"],
            "challenge_resume": paths["challenge_resume_out"],
            "cookie_preflight": paths["cookie_preflight_out"],
            "scope_audit": paths["scope_audit_out"],
            "data_minimization": paths["data_minimization_out"],
            "probe_results": paths["probe_results_out"],
            "resolved_inventory": paths["resolved_inventory_out"],
            "resolved_pipeline": paths["resolved_pipeline_out"],
            "snapshot_recovery": paths["snapshot_recovery_out"],
            "batch_cost": paths["batch_cost_out"],
            "scale_estimate": paths["scale_estimate_out"],
            "submit_preflight": paths["submit_preflight_out"],
        }
    )
    write_json(paths["dashboard_out"], dashboard)
    write_text(paths["dashboard_markdown"], render_openreview_readiness_dashboard_markdown(dashboard))

    consistency = check_openreview_report_consistency(
        dashboard_path=paths["dashboard_out"],
        batch_cost_path=paths["batch_cost_out"],
        scale_estimate_path=paths["scale_estimate_out"],
    )
    write_json(paths["consistency_out"], consistency)
    write_text(paths["consistency_markdown"], render_report_consistency_markdown(consistency))

    summary = {
        "invitation_audit_needs_attention": (invitation_audit.get("summary") or {}).get("needs_attention", []),
        "probe_queue_count": (probe_queue.get("summary") or {}).get("probe_count", 0),
        "probe_queue_runner_counts": probe_queue_runner.get("status_counts", {}),
        "challenge_resume_status": (read_json_if_exists(paths["challenge_resume_out"]) or {}).get("status", "missing"),
        "cookie_handoff_status": cookie_handoff.get("status", "missing"),
        "cookie_preflight_status": cookie_preflight.get("status", "missing"),
        "scope_audit_status": scope_audit.get("status", "missing"),
        "scope_target_count": (scope_audit.get("completeness") or {}).get("target_count", 0),
        "data_minimization_status": data_minimization.get("status", "missing"),
        "data_minimization_batch_request_count": (data_minimization.get("summary") or {}).get("batch_request_count", 0),
        "probe_results_selected": (probe_results.get("summary") or {}).get("selected_for_scoring", []),
        "probe_results_blocked_auth": (probe_results.get("summary") or {}).get("blocked_auth", []),
        "probe_results_missing": (probe_results.get("summary") or {}).get("missing_results", []),
        "probe_results_needs_larger_probe": (probe_results.get("summary") or {}).get("needs_larger_probe", []),
        "resolved_ready_to_pull": (resolved_inventory.get("summary") or {}).get("ready_to_pull_and_score", []),
        "resolved_blocked_auth": (resolved_inventory.get("summary") or {}).get("blocked_openreview_auth", []),
        "resolved_needs_probe_results": (resolved_inventory.get("summary") or {}).get("needs_probe_results", []),
        "resolved_needs_larger_probe": (resolved_inventory.get("summary") or {}).get("needs_larger_probe", []),
        "resolved_pipeline_action": resolved_pipeline.get("action", ""),
        "resolved_pipeline_runner_counts": resolved_pipeline.get("runner_status_counts", {}),
        "snapshot_recoverable_count": (snapshot_recovery.get("summary") or {}).get("recoverable_count", 0),
        "batch_estimated_cost_usd": (batch_cost.get("summary") or {}).get("estimated_batch_cost_usd", 0),
        "scale_estimate_status": scale_estimate.get("status", ""),
        "dashboard_status": dashboard.get("status", ""),
        "dashboard_stale_reports": (dashboard.get("freshness") or {}).get("stale_reports", []),
        "consistency_status": consistency.get("status", ""),
        "consistency_error_count": (consistency.get("summary") or {}).get("error_count", 0),
        "submit_preflight_status": submit_preflight.get("status", ""),
    }
    report = {
        "schema_version": LOCAL_REFRESH_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "network_used": False,
        "openai_submit_used": False,
        "summary": summary,
        "paths": paths,
    }
    write_json(paths["refresh_out"], report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh local-only OpenReview validation reports without network or OpenAI submit.")
    parser.add_argument("--inventory", default="data/validation/openreview_venue_inventory_2025.json")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--snapshot-root", default="data/raw/openreview")
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--batch-manifest", action="append", default=[])
    parser.add_argument("--probe-result", action="append", default=[], help="Probe result JSON glob. Repeatable.")
    parser.add_argument("--data-minimization-normalized", action="append", default=[], help="Normalized JSON glob for data minimization audit. Repeatable.")
    parser.add_argument("--data-minimization-batch", action="append", default=[], help="Batch JSONL glob for data minimization audit. Repeatable.")
    parser.add_argument("--max-total-cost-usd", type=float, default=25.0)
    parser.add_argument("--out", default="data/validation/openreview_local_refresh.json")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = refresh_openreview_local_reports(
        inventory_path=args.inventory,
        venues_path=args.venues,
        snapshot_root=args.snapshot_root,
        raw_root=args.raw_root,
        batch_manifest_patterns=args.batch_manifest or None,
        probe_result_patterns=args.probe_result or None,
        data_minimization_normalized_patterns=args.data_minimization_normalized or None,
        data_minimization_batch_patterns=args.data_minimization_batch or None,
        max_total_cost_usd=args.max_total_cost_usd,
        paths={"refresh_out": args.out},
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
