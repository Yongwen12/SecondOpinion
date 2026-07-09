from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

READINESS_DASHBOARD_SCHEMA_VERSION = "openreview-readiness-dashboard-v0.1"
DEFAULT_PATHS = {
    "secret": "data/validation/openreview_secret_check.json",
    "auth_check": "data/validation/openreview_auth_check.json",
    "safe_pipeline": "data/validation/openreview_safe_pipeline.json",
    "challenge_resume": "data/validation/openreview_challenge_resume.json",
    "cookie_handoff": "data/validation/openreview_cookie_handoff.json",
    "cookie_preflight": "data/validation/openreview_cookie_preflight.json",
    "scope_audit": "data/validation/openreview_scope_audit_2025.json",
    "data_minimization": "data/validation/openreview_data_minimization_audit.json",
    "invitation_audit": "data/validation/openreview_invitation_audit_2025.json",
    "probe_queue": "data/validation/openreview_probe_queue_2025.json",
    "probe_queue_runner": "data/validation/openreview_probe_queue_runner.json",
    "probe_results": "data/validation/openreview_probe_results_2025.json",
    "resolved_inventory": "data/validation/openreview_resolved_inventory_2025.json",
    "resolved_pipeline": "data/validation/openreview_resolved_pipeline.json",
    "snapshot_recovery": "data/validation/openreview_snapshot_recovery.json",
    "batch_cost": "data/validation/batch_cost_review.json",
    "scale_estimate": "data/validation/openreview_scale_estimate.json",
    "submit_preflight": "data/validation/openreview_batch_submit_preflight.json",
    "runbook": "data/validation/openreview_execution_runbook_2025.json",
    "pilot_readiness_iclr": "data/validation/openreview_pilot_readiness_iclr.json",
    "pilot_readiness_icml": "data/validation/openreview_pilot_readiness_icml.json",
    "pilot_readiness_neurips": "data/validation/openreview_pilot_readiness_neurips.json",
}


def read_json_if_exists(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")



def report_time(report: dict[str, Any]) -> str:
    return str(report.get("checked_at") or report.get("created_at") or "")


def parse_report_time(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def freshness_report(
    reports: dict[str, dict[str, Any]],
    *,
    source_name: str = "auth_check",
    dependent_reports: set[str] | None = None,
) -> dict[str, Any]:
    dependent_reports = dependent_reports or {"safe_pipeline", "batch_cost", "scale_estimate"}
    source_time = parse_report_time(report_time(reports.get(source_name, {})))
    items = {}
    stale = []
    missing = []
    for name, report in reports.items():
        timestamp = report_time(report)
        parsed = parse_report_time(timestamp)
        if not report:
            status = "missing"
            missing.append(name)
        elif name in dependent_reports and source_time and parsed and parsed < source_time and name != source_name:
            status = "stale_vs_auth_check"
            stale.append(name)
        else:
            status = "current"
        items[name] = {"timestamp": timestamp, "status": status}
    return {
        "source": source_name,
        "source_timestamp": report_time(reports.get(source_name, {})),
        "stale_reports": stale,
        "missing_reports": missing,
        "items": items,
    }


def status_counts_from_safe_pipeline(safe: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_status": safe.get("gate_status", "missing"),
        "action": safe.get("action", ""),
        "ran_inventory": bool(safe.get("ran_inventory")),
        "ready_to_pull": (safe.get("scope_matrix_summary") or {}).get("ready_to_pull") or [],
        "blocked_openreview_auth": (safe.get("scope_matrix_summary") or {}).get("blocked_openreview_auth") or [],
        "target_or_probe": (safe.get("scope_matrix_summary") or {}).get("target_or_probe") or [],
        "excluded": (safe.get("scope_matrix_summary") or {}).get("excluded") or [],
    }


def pilot_readiness_summary(pilot_readiness: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for key, report in pilot_readiness.items():
        if not report:
            continue
        fallback_venue = key.removeprefix("pilot_readiness_").upper()
        venue = str(report.get("venue_id") or fallback_venue).upper()
        quality = report.get("quality_summary") or {}
        batch = report.get("batch_summary") or {}
        summary[venue] = {
            "status": report.get("status", "missing"),
            "recommendation": report.get("recommendation", "missing"),
            "paper_count": int(quality.get("paper_count") or 0),
            "review_count": int(quality.get("review_count") or 0),
            "request_count": int(batch.get("request_count") or 0),
            "estimated_batch_cost_usd": float(batch.get("estimated_batch_cost_usd") or 0),
            "errors": list(report.get("errors") or []),
            "warnings": list(report.get("warnings") or []),
        }
    return summary


def pilot_readiness_label(pilot_readiness: dict[str, dict[str, Any]]) -> str:
    return ", ".join(
        f"{venue}={item.get('status', 'missing')}" for venue, item in sorted(pilot_readiness.items())
    ) or "-"


def venue_args(venues: list[str]) -> str:
    return " ".join(f"--venue {venue}" for venue in venues)


def safe_pipeline_command(*, venues: list[str], pull_limit: int | None = None) -> str:
    limit_arg = f" --pull-limit {pull_limit}" if pull_limit is not None else ""
    return (
        "python -m secondopinion.tools.openreview_safe_pipeline "
        "--venues data/config/openreview_venues_2025.json "
        f"{venue_args(venues)}{limit_arg} --execute-safe"
    )
def decide_next_action(
    *,
    secret: dict[str, Any],
    auth_check: dict[str, Any],
    safe: dict[str, Any],
    snapshot_recovery: dict[str, Any],
    batch_cost: dict[str, Any],
    pilot_readiness: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, str, list[str]]:
    if not secret:
        return "missing_secret_report", "Run openreview_secret_check before progressing.", [
            "python -m secondopinion.tools.openreview_secret_check --out data/validation/openreview_secret_check.json"
        ]
    if not secret.get("ok"):
        return "blocked_openreview_auth", "Install a browser-verified OpenReview cookie/token.", [
            "python -m secondopinion.tools.openreview_challenge_resume --cookie-file path\\to\\browser-cookies.txt --execute-probe --skip-existing",
            "python -m secondopinion.tools.openreview_secret_check --out data/validation/openreview_secret_check.json",
        ]
    if not auth_check:
        return "missing_openreview_auth_check", "Local auth secret exists; run the real OpenReview auth check before inventory.", [
            "python -m secondopinion.tools.openreview_auth_check --out data/validation/openreview_auth_check.json"
        ]
    if not auth_check.get("ok"):
        status = str(auth_check.get("status") or "")
        if status in {"challenge_required", "auth_required"}:
            return "blocked_openreview_api_auth", "Local secret exists, but OpenReview API still rejects it; refresh browser cookie/challenge.", [
            "python -m secondopinion.tools.openreview_challenge_resume --cookie-file path\\to\\browser-cookies.txt --execute-probe --skip-existing",
                "python -m secondopinion.tools.openreview_auth_check --out data/validation/openreview_auth_check.json",
            ]
        return "blocked_openreview_auth_check", "OpenReview auth check failed; inspect auth_check error.", [
            "python -m secondopinion.tools.openreview_auth_check --out data/validation/openreview_auth_check.json"
        ]
    recovery_summary = (snapshot_recovery or {}).get("summary") or {}
    if int(recovery_summary.get("recoverable_count") or 0) > 0:
        return "resume_interrupted_snapshots", "Resume interrupted raw OpenReview snapshots before starting new full pulls.", [
            "python -m secondopinion.tools.openreview_snapshot_recovery --root data/raw/openreview --raw-root data/raw"
        ]
    ready = [str(venue).upper() for venue in (((safe.get("scope_matrix_summary") or {}).get("ready_to_pull") or []) if safe else [])]
    pilot_summary = pilot_readiness_summary(pilot_readiness or {})
    ready_pilots = [venue for venue in ready if (pilot_summary.get(venue) or {}).get("status") == "ready_for_full_pull"]
    not_ready_pilots = [venue for venue in ready if venue in pilot_summary and venue not in ready_pilots]
    missing_pilots = [venue for venue in ready if venue not in pilot_summary]
    if ready and ready_pilots and not missing_pilots and not not_ready_pilots:
        return "run_full_pull", "Pilot datasets passed; run full OpenReview pulls for ready venues.", [
            safe_pipeline_command(venues=ready_pilots)
        ]
    if ready:
        pilot_venues = missing_pilots + not_ready_pilots or ready
        return "run_priority1_pilot", "Run safe 50-paper pilots for ready venues, then check pilot readiness.", [
            safe_pipeline_command(venues=pilot_venues, pull_limit=50)
        ]
    gate_status = str(safe.get("gate_status") or "") if safe else ""
    if gate_status in {"blocked_openreview_auth", "blocked_auth_check", ""}:
        return "rerun_inventory_probe", "Auth is present locally; rerun inventory probe to discover public review coverage.", [
            "python -m secondopinion.tools.openreview_challenge_resume --cookie-file path\\to\\browser-cookies.txt --execute-probe --skip-existing"
        ]
    cost_summary = (batch_cost or {}).get("summary") or {}
    if cost_summary.get("estimated_batch_cost_usd") is not None:
        return "review_batch_cost_before_submit", "Batch manifests exist; review cost before any OpenAI submit.", [
            "python -m secondopinion.tools.batch_cost_review --manifest data/batch/**/*_manifest.json --out data/validation/batch_cost_review.json --markdown reports/validation/batch_cost_review.md --max-total-cost-usd 25"
        ]
    return "inspect_reports", "No automatic next action matched; inspect validation reports.", []


def build_openreview_readiness_dashboard(*, paths: dict[str, str] | None = None) -> dict[str, Any]:
    paths = {**DEFAULT_PATHS, **(paths or {})}
    secret = read_json_if_exists(paths["secret"])
    auth_check = read_json_if_exists(paths["auth_check"])
    safe = read_json_if_exists(paths["safe_pipeline"])
    challenge_resume = read_json_if_exists(paths["challenge_resume"])
    cookie_handoff = read_json_if_exists(paths["cookie_handoff"])
    cookie_preflight = read_json_if_exists(paths["cookie_preflight"])
    scope_audit = read_json_if_exists(paths["scope_audit"])
    data_minimization = read_json_if_exists(paths["data_minimization"])
    invitation_audit = read_json_if_exists(paths["invitation_audit"])
    probe_queue = read_json_if_exists(paths["probe_queue"])
    probe_queue_runner = read_json_if_exists(paths["probe_queue_runner"])
    probe_results = read_json_if_exists(paths["probe_results"])
    resolved_inventory = read_json_if_exists(paths["resolved_inventory"])
    resolved_pipeline = read_json_if_exists(paths["resolved_pipeline"])
    snapshot_recovery = read_json_if_exists(paths["snapshot_recovery"])
    batch_cost = read_json_if_exists(paths["batch_cost"])
    scale_estimate = read_json_if_exists(paths["scale_estimate"])
    submit_preflight = read_json_if_exists(paths["submit_preflight"])
    runbook = read_json_if_exists(paths["runbook"])
    pilot_readiness = {
        "ICLR": read_json_if_exists(paths["pilot_readiness_iclr"]),
        "ICML": read_json_if_exists(paths["pilot_readiness_icml"]),
        "NEURIPS": read_json_if_exists(paths["pilot_readiness_neurips"]),
    }
    freshness = freshness_report(
        {
            "secret": secret,
            "auth_check": auth_check,
            "safe_pipeline": safe,
            "challenge_resume": challenge_resume,
            "cookie_handoff": cookie_handoff,
            "cookie_preflight": cookie_preflight,
            "scope_audit": scope_audit,
            "data_minimization": data_minimization,
            "invitation_audit": invitation_audit,
            "probe_queue": probe_queue,
            "probe_queue_runner": probe_queue_runner,
            "probe_results": probe_results,
            "resolved_inventory": resolved_inventory,
            "resolved_pipeline": resolved_pipeline,
            "snapshot_recovery": snapshot_recovery,
            "batch_cost": batch_cost,
            "scale_estimate": scale_estimate,
            "submit_preflight": submit_preflight,
            "runbook": runbook,
            "pilot_readiness_iclr": pilot_readiness.get("ICLR", {}),
            "pilot_readiness_icml": pilot_readiness.get("ICML", {}),
            "pilot_readiness_neurips": pilot_readiness.get("NEURIPS", {}),
        }
    )
    next_action, recommendation, commands = decide_next_action(
        secret=secret,
        auth_check=auth_check,
        safe=safe,
        snapshot_recovery=snapshot_recovery,
        batch_cost=batch_cost,
        pilot_readiness=pilot_readiness,
    )
    if freshness.get("stale_reports"):
        commands = [
            "python -m secondopinion.tools.openreview_local_refresh --max-total-cost-usd 25",
            *commands,
        ]
    return {
        "schema_version": READINESS_DASHBOARD_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": next_action,
        "recommendation": recommendation,
        "next_commands": commands,
        "paths": paths,
        "freshness": freshness,
        "auth": {
            "ok": bool(secret.get("ok")) if secret else False,
            "recommendation": secret.get("recommendation", "missing") if secret else "missing",
            "cookie_names": ((secret.get("cookie") or {}).get("cookie_names") or []) if secret else [],
            "cookie_warnings": (((secret.get("cookie") or {}).get("diagnostics") or {}).get("warnings") or []) if secret else [],
            "api_ok": bool(auth_check.get("ok")) if auth_check else False,
            "api_status": str(auth_check.get("status") or "missing") if auth_check else "missing",
            "api_recommendation": str(auth_check.get("recommendation") or "missing") if auth_check else "missing",
        },
        "pipeline": status_counts_from_safe_pipeline(safe),
        "challenge_resume": {
            "status": challenge_resume.get("status", "missing"),
            "recommendation": challenge_resume.get("recommendation", "missing"),
            "auth_status": ((challenge_resume.get("auth_check") or {}).get("status") or "missing") if challenge_resume else "missing",
            "probe_runner": (challenge_resume.get("probe_runner") or {}) if challenge_resume else {},
            "auth_diagnosis": (challenge_resume.get("auth_diagnosis") or {}) if challenge_resume else {},
        },
        "cookie_handoff": {
            "status": cookie_handoff.get("status", "missing"),
            "diagnosis_reason": cookie_handoff.get("diagnosis_reason", "missing"),
            "cookie_names_seen": cookie_handoff.get("cookie_names_seen", []),
            "cookie_warnings": cookie_handoff.get("cookie_warnings", []),
            "commands": cookie_handoff.get("commands", []),
        },
        "cookie_preflight": {
            "status": cookie_preflight.get("status", "missing"),
            "recommendation": cookie_preflight.get("recommendation", "missing"),
            "blocking_warnings": cookie_preflight.get("blocking_warnings", []),
            "soft_warnings": cookie_preflight.get("soft_warnings", []),
        },
        "scope_audit": {
            "status": scope_audit.get("status", "missing"),
            "target_count": (scope_audit.get("completeness") or {}).get("target_count", 0),
            "excluded_count": (scope_audit.get("completeness") or {}).get("excluded_count", 0),
            "target_venue_ids": (scope_audit.get("completeness") or {}).get("target_venue_ids", []),
            "priority1_core_ids": (scope_audit.get("completeness") or {}).get("priority1_core_ids", []),
            "priority2_probe_ids": (scope_audit.get("completeness") or {}).get("priority2_probe_ids", []),
            "explicitly_excluded_top_journal_ids": (scope_audit.get("completeness") or {}).get("explicitly_excluded_top_journal_ids", []),
            "warnings": scope_audit.get("warnings", []),
            "errors": scope_audit.get("errors", []),
        },
        "data_minimization": {
            "status": data_minimization.get("status", "missing"),
            **((data_minimization.get("summary") or {}) if data_minimization else {}),
        },
        "invitation_audit": (invitation_audit.get("summary") or {}) if invitation_audit else {},
        "probe_queue": (probe_queue.get("summary") or {}) if probe_queue else {},
        "probe_queue_runner": {"execute": probe_queue_runner.get("execute", False), **((probe_queue_runner.get("status_counts") or {}) if probe_queue_runner else {})},
        "probe_results": (probe_results.get("summary") or {}) if probe_results else {},
        "resolved_inventory": (resolved_inventory.get("summary") or {}) if resolved_inventory else {},
        "resolved_pipeline": {"action": resolved_pipeline.get("action", "missing"), **((resolved_pipeline.get("runner_status_counts") or {}) if resolved_pipeline else {})},
        "pilot_readiness": pilot_readiness_summary(pilot_readiness),
        "snapshot_recovery": (snapshot_recovery.get("summary") or {}) if snapshot_recovery else {},
        "batch_cost": (batch_cost.get("summary") or {}) if batch_cost else {},
        "scale_estimate": {"status": scale_estimate.get("status", "missing"), **((scale_estimate.get("summary") or {}) if scale_estimate else {})},
        "submit_preflight": {"status": submit_preflight.get("status", "missing"), **((submit_preflight.get("checks") or {}) if submit_preflight else {})},
        "runbook_summary": (runbook.get("summary") or {}) if runbook else {},
    }


def render_openreview_readiness_dashboard_markdown(report: dict[str, Any]) -> str:
    auth = report.get("auth") or {}
    pipeline = report.get("pipeline") or {}
    challenge_resume = report.get("challenge_resume") or {}
    cookie_handoff = report.get("cookie_handoff") or {}
    cookie_preflight = report.get("cookie_preflight") or {}
    scope_audit = report.get("scope_audit") or {}
    data_minimization = report.get("data_minimization") or {}
    invitation_audit = report.get("invitation_audit") or {}
    probe_queue = report.get("probe_queue") or {}
    probe_queue_runner = report.get("probe_queue_runner") or {}
    probe_results = report.get("probe_results") or {}
    resolved_inventory = report.get("resolved_inventory") or {}
    resolved_pipeline = report.get("resolved_pipeline") or {}
    pilot_readiness = report.get("pilot_readiness") or {}
    recovery = report.get("snapshot_recovery") or {}
    cost = report.get("batch_cost") or {}
    freshness = report.get("freshness") or {}
    scale = report.get("scale_estimate") or {}
    submit_preflight = report.get("submit_preflight") or {}
    runbook = report.get("runbook_summary") or {}
    lines = [
        "# OpenReview Readiness Dashboard",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Recommendation: {report.get('recommendation', '')}",
        "",
        "## Current State",
        "",
        f"- Auth ok: `{auth.get('ok', False)}`",
        f"- Auth recommendation: `{auth.get('recommendation', '')}`",
        f"- Cookie names: `{', '.join(auth.get('cookie_names') or []) or '-'}`",
        f"- Cookie warnings: `{', '.join(auth.get('cookie_warnings') or []) or '-'}`",
        f"- OpenReview API auth ok: `{auth.get('api_ok', False)}`",
        f"- OpenReview API auth status: `{auth.get('api_status', '')}`",
        f"- Gate status: `{pipeline.get('gate_status', '')}`",
        f"- Challenge resume: `{challenge_resume.get('status', 'missing')}`",
        f"- Challenge resume recommendation: `{challenge_resume.get('recommendation', 'missing')}`",
        f"- Auth diagnosis: `{(challenge_resume.get('auth_diagnosis') or {}).get('reason', 'missing')}`",
        f"- Cookie handoff: `{cookie_handoff.get('status', 'missing')}`",
        f"- Cookie handoff warnings: `{', '.join(cookie_handoff.get('cookie_warnings') or []) or '-'}`",
        f"- Cookie preflight: `{cookie_preflight.get('status', 'missing')}`",
        f"- Cookie preflight blocking warnings: `{', '.join(cookie_preflight.get('blocking_warnings') or []) or '-'}`",
        f"- Scope audit: `{scope_audit.get('status', 'missing')}` targets={scope_audit.get('target_count', 0)} excluded={scope_audit.get('excluded_count', 0)}",
        f"- Scope priority 1 core: `{', '.join(scope_audit.get('priority1_core_ids') or []) or '-'}`",
        f"- Scope priority 2 probe: `{', '.join(scope_audit.get('priority2_probe_ids') or []) or '-'}`",
        f"- Scope excluded top journals: `{', '.join(scope_audit.get('explicitly_excluded_top_journal_ids') or []) or '-'}`",
        f"- Data minimization: `{data_minimization.get('status', 'missing')}` batch_requests={data_minimization.get('batch_request_count', 0)}",
        f"- Inventory ran: `{pipeline.get('ran_inventory', False)}`",
        f"- Ready to pull: `{', '.join(pipeline.get('ready_to_pull') or []) or '-'}`",
        f"- Blocked auth venues: `{', '.join(pipeline.get('blocked_openreview_auth') or []) or '-'}`",
        f"- Invitation audit attention: `{', '.join(invitation_audit.get('needs_attention') or []) or '-'}`",
        f"- Invitation probe queue: `{probe_queue.get('probe_count', 0)}` candidates",
        f"- Probe queue runner: `execute={probe_queue_runner.get('execute', False)} counts={{{', '.join(f'{k}: {v}' for k, v in probe_queue_runner.items() if k != 'execute')}}}`",
        f"- Probe results selected: `{', '.join(probe_results.get('selected_for_scoring') or []) or '-'}`",
        f"- Probe results missing: `{', '.join(probe_results.get('missing_results') or []) or '-'}`",
        f"- Probe results need larger sample: `{', '.join(probe_results.get('needs_larger_probe') or []) or '-'}`",
        f"- Resolved ready to pull: `{', '.join(resolved_inventory.get('ready_to_pull_and_score') or []) or '-'}`",
        f"- Resolved needs probe: `{', '.join(resolved_inventory.get('needs_probe_results') or []) or '-'}`",
        f"- Resolved needs larger probe: `{', '.join(resolved_inventory.get('needs_larger_probe') or []) or '-'}`",
        f"- Resolved pipeline: `{resolved_pipeline.get('action', 'missing')}`",
        f"- Pilot readiness: `{pilot_readiness_label(pilot_readiness)}`",
        f"- Snapshot recoverable: `{recovery.get('recoverable_count', 0)}`",
        f"- Existing batch estimated cost USD: `{cost.get('estimated_batch_cost_usd', '-')}`",
        f"- Scale estimate status: `{scale.get('status', 'missing')}`",
        f"- Scale estimate blocked venues: `{', '.join(scale.get('blocked_venues') or []) or '-'}`",
        f"- Scale estimated batch cost USD: `{scale.get('estimated_batch_cost_usd', '-')}`",
        f"- Batch submit preflight: `{submit_preflight.get('status', 'missing')}`",
        f"- Core priority 1: `{', '.join(runbook.get('core_priority1') or []) or '-'}`",
        f"- Probe priority 2: `{', '.join(runbook.get('probe_priority2') or []) or '-'}`",
        "",
        "## Freshness",
        "",
        f"- Source: `{freshness.get('source', '')}` `{freshness.get('source_timestamp', '')}`",
        f"- Stale reports: `{', '.join(freshness.get('stale_reports') or []) or '-'}`",
        f"- Missing reports: `{', '.join(freshness.get('missing_reports') or []) or '-'}`",
        "",
        "## Next Commands",
        "",
        "```powershell",
    ]
    lines.extend(report.get("next_commands") or ["# No automatic command suggested."])
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize OpenReview 2025 ingestion readiness across auth, inventory, snapshots, and batch cost.")
    parser.add_argument("--out", default="data/validation/openreview_readiness_dashboard.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_readiness_dashboard.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_openreview_readiness_dashboard()
    write_json(args.out, report)
    write_text(args.markdown, render_openreview_readiness_dashboard_markdown(report))
    print(json.dumps({"status": report["status"], "recommendation": report["recommendation"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
