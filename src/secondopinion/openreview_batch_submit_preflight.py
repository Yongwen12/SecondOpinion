from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


BATCH_SUBMIT_PREFLIGHT_VERSION = "0.1"


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def build_batch_submit_preflight(
    *,
    consistency_path: str | Path,
    batch_cost_path: str | Path,
    max_total_cost_usd: float,
    allow_submit: bool = False,
) -> dict[str, Any]:
    consistency = read_json(consistency_path)
    batch_cost = read_json(batch_cost_path)
    summary = batch_cost.get("summary") or {}
    cost = float(summary.get("estimated_batch_cost_usd") or 0.0)
    request_count = int(summary.get("request_count") or 0)
    manifest_count = int(summary.get("included_manifest_count") or summary.get("manifest_count") or 0)

    issues: list[dict[str, Any]] = []
    if consistency.get("status") != "ok":
        issues.append({"code": "consistency_failed", "status": consistency.get("status")})
    if batch_cost.get("status") == "blocked_cost_limit":
        issues.append({"code": "batch_cost_review_limit", "status": batch_cost.get("status")})
    if cost > max_total_cost_usd:
        issues.append(
            {
                "code": "cost_limit",
                "estimated_batch_cost_usd": cost,
                "max_total_cost_usd": max_total_cost_usd,
            }
        )
    if request_count <= 0 or manifest_count <= 0:
        issues.append({"code": "no_batch_manifests", "request_count": request_count, "manifest_count": manifest_count})
    if not allow_submit:
        issues.append({"code": "explicit_approval_required"})

    status = "ready_for_submit"
    if any(issue["code"] == "consistency_failed" for issue in issues):
        status = "blocked_consistency_failed"
    elif any(issue["code"] in {"batch_cost_review_limit", "cost_limit"} for issue in issues):
        status = "blocked_cost_limit"
    elif any(issue["code"] == "no_batch_manifests" for issue in issues):
        status = "blocked_no_batch_manifests"
    elif any(issue["code"] == "explicit_approval_required" for issue in issues):
        status = "blocked_explicit_approval_required"

    next_commands = [
        "python -m secondopinion.tools.openreview_report_consistency",
        "python -m secondopinion.tools.batch_cost_review --max-total-cost-usd "
        + f"{max_total_cost_usd:g}",
    ]
    if status == "ready_for_submit":
        next_commands.append(
            "python -m secondopinion.tools.openreview_plan_runner --plan data/validation/openreview_ingestion_plan.json "
            "--include-costly --stage submit_batch --execute --max-submit-cost-usd "
            + f"{max_total_cost_usd:g}"
        )
    else:
        next_commands.append(
            "python -m secondopinion.tools.openreview_batch_submit_preflight --allow-submit "
            + f"--max-total-cost-usd {max_total_cost_usd:g}"
        )

    return {
        "schema_version": BATCH_SUBMIT_PREFLIGHT_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "openai_submit_used": False,
        "checks": {
            "consistency_status": consistency.get("status"),
            "batch_cost_status": batch_cost.get("status"),
            "estimated_batch_cost_usd": cost,
            "request_count": request_count,
            "manifest_count": manifest_count,
            "max_total_cost_usd": max_total_cost_usd,
            "allow_submit": allow_submit,
        },
        "issues": issues,
        "next_commands": next_commands,
    }


def render_batch_submit_preflight_markdown(report: dict[str, Any]) -> str:
    checks = report.get("checks") or {}
    lines = [
        "# OpenReview Batch Submit Preflight",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- OpenAI submit used: `{report.get('openai_submit_used', False)}`",
        f"- Consistency status: `{checks.get('consistency_status', '')}`",
        f"- Batch cost status: `{checks.get('batch_cost_status', '')}`",
        f"- Request count: `{checks.get('request_count', 0)}`",
        f"- Manifest count: `{checks.get('manifest_count', 0)}`",
        f"- Estimated batch cost USD: `{float(checks.get('estimated_batch_cost_usd') or 0):.4f}`",
        f"- Max total cost USD: `{checks.get('max_total_cost_usd', None)}`",
        f"- Allow submit: `{checks.get('allow_submit', False)}`",
        "",
        "## Issues",
        "",
    ]
    issues = report.get("issues") or []
    if not issues:
        lines.append("- none")
    else:
        for issue in issues:
            lines.append(f"- `{issue.get('code', '')}`")
    lines.extend(["", "## Next Commands", ""])
    for command in report.get("next_commands", []):
        lines.append(f"- `{command}`")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preflight OpenAI batch submit readiness without submitting anything.")
    parser.add_argument("--consistency", default="data/validation/openreview_report_consistency.json")
    parser.add_argument("--batch-cost", default="data/validation/batch_cost_review.json")
    parser.add_argument("--out", default="data/validation/openreview_batch_submit_preflight.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_batch_submit_preflight.md")
    parser.add_argument("--max-total-cost-usd", type=float, default=25.0)
    parser.add_argument("--allow-submit", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_batch_submit_preflight(
        consistency_path=args.consistency,
        batch_cost_path=args.batch_cost,
        max_total_cost_usd=args.max_total_cost_usd,
        allow_submit=args.allow_submit,
    )
    write_json(args.out, report)
    write_markdown(args.markdown, render_batch_submit_preflight_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
