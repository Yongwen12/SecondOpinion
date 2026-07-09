from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

REPORT_CONSISTENCY_SCHEMA_VERSION = "openreview-report-consistency-v0.1"


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


def add_issue(issues: list[dict[str, Any]], *, severity: str, code: str, message: str) -> None:
    issues.append({"severity": severity, "code": code, "message": message})


def check_openreview_report_consistency(
    *,
    dashboard_path: str = "data/validation/openreview_readiness_dashboard.json",
    batch_cost_path: str = "data/validation/batch_cost_review.json",
    scale_estimate_path: str = "data/validation/openreview_scale_estimate.json",
    batch_root: str = "data/batch",
) -> dict[str, Any]:
    dashboard = read_json_if_exists(dashboard_path)
    batch_cost = read_json_if_exists(batch_cost_path)
    scale_estimate = read_json_if_exists(scale_estimate_path)
    issues: list[dict[str, Any]] = []

    if not dashboard:
        add_issue(issues, severity="error", code="missing_dashboard", message=f"Missing {dashboard_path}")
    if not batch_cost:
        add_issue(issues, severity="error", code="missing_batch_cost", message=f"Missing {batch_cost_path}")
    if not scale_estimate:
        add_issue(issues, severity="error", code="missing_scale_estimate", message=f"Missing {scale_estimate_path}")

    freshness = dashboard.get("freshness") or {}
    stale = list(freshness.get("stale_reports") or [])
    missing = list(freshness.get("missing_reports") or [])
    if stale:
        add_issue(issues, severity="error", code="stale_reports", message="Stale reports: " + ", ".join(stale))
    if missing:
        add_issue(issues, severity="error", code="missing_reports", message="Missing reports: " + ", ".join(missing))

    dashboard_cost = float((dashboard.get("batch_cost") or {}).get("estimated_batch_cost_usd") or 0.0)
    report_cost = float((batch_cost.get("summary") or {}).get("estimated_batch_cost_usd") or 0.0)
    if dashboard and batch_cost and round(dashboard_cost, 4) != round(report_cost, 4):
        add_issue(
            issues,
            severity="error",
            code="batch_cost_mismatch",
            message=f"Dashboard cost {dashboard_cost:.4f} != batch report cost {report_cost:.4f}",
        )

    dashboard_scale_status = str((dashboard.get("scale_estimate") or {}).get("status") or "")
    report_scale_status = str(scale_estimate.get("status") or "")
    if dashboard and scale_estimate and dashboard_scale_status != report_scale_status:
        add_issue(
            issues,
            severity="error",
            code="scale_status_mismatch",
            message=f"Dashboard scale status {dashboard_scale_status} != scale report status {report_scale_status}",
        )

    suspicious = sorted(Path(batch_root).glob("**/*sample50*manifest.json")) if Path(batch_root).exists() else []
    for path in suspicious:
        payload = read_json_if_exists(path)
        if payload.get("request_count") and not payload.get("dataset") and not payload.get("normalized_path"):
            add_issue(
                issues,
                severity="error",
                code="suspicious_test_manifest",
                message=f"Suspicious fixed-path sample50 manifest without dataset metadata: {path}",
            )

    errors = [issue for issue in issues if issue["severity"] == "error"]
    return {
        "schema_version": REPORT_CONSISTENCY_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "failed" if errors else "ok",
        "summary": {
            "issue_count": len(issues),
            "error_count": len(errors),
            "warning_count": len(issues) - len(errors),
        },
        "issues": issues,
    }


def render_report_consistency_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# OpenReview Report Consistency",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Errors: `{summary.get('error_count', 0)}`",
        f"- Warnings: `{summary.get('warning_count', 0)}`",
        "",
        "## Issues",
        "",
    ]
    if not report.get("issues"):
        lines.append("- None")
    else:
        for issue in report.get("issues", []):
            lines.append(f"- `{issue.get('severity')}` `{issue.get('code')}`: {issue.get('message')}")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check local OpenReview validation reports for stale or inconsistent state.")
    parser.add_argument("--out", default="data/validation/openreview_report_consistency.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_report_consistency.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = check_openreview_report_consistency()
    write_json(args.out, report)
    write_text(args.markdown, render_report_consistency_markdown(report))
    print(json.dumps({"status": report["status"], **report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
