from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .batch_review_scoring import DEFAULT_BATCH_MODEL
from .openreview_venue_inventory import load_venue_specs

RUNBOOK_SCHEMA_VERSION = "openreview-execution-runbook-v0.1"
DEFAULT_SAMPLE_LIMIT = 50


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def venue_id(spec: dict[str, Any]) -> str:
    return str(spec.get("venue_id") or "").upper()


def scope_decision(spec: dict[str, Any]) -> str:
    return str(spec.get("scope_decision") or "")


def priority(spec: dict[str, Any]) -> int:
    return int(spec.get("priority") or 99)


def target_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        spec
        for spec in sorted(specs, key=lambda item: (priority(item), venue_id(item)))
        if scope_decision(spec) in {"score_public_reviews", "probe_then_score_if_public"}
    ]


def core_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [spec for spec in target_specs(specs) if scope_decision(spec) == "score_public_reviews"]


def probe_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [spec for spec in target_specs(specs) if scope_decision(spec) == "probe_then_score_if_public"]


def excluded_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        spec
        for spec in sorted(specs, key=lambda item: (priority(item), venue_id(item)))
        if scope_decision(spec).startswith("exclude") or spec.get("include_in_inventory") is False
    ]


def safe_pipeline_command(
    *,
    venues_path: str,
    venue: str | None = None,
    pull_limit: int | None = None,
    execute_safe: bool = False,
    probe_when_auth_blocked: bool = False,
    cookie_file_placeholder: str = "path\\to\\browser-cookies.txt",
    max_submit_cost_usd: float = 25.0,
    batch_cost_limit_usd: float = 25.0,
) -> str:
    parts = ["python -m secondopinion.tools.openreview_safe_pipeline", "--venues", venues_path]
    if venue:
        parts.extend(["--venue", venue])
    if pull_limit is not None:
        parts.extend(["--pull-limit", str(pull_limit)])
    if cookie_file_placeholder:
        parts.extend(["--cookie-file", cookie_file_placeholder])
    if execute_safe:
        parts.append("--execute-safe")
    if probe_when_auth_blocked:
        parts.append("--probe-when-auth-blocked")
    parts.extend(["--max-submit-cost-usd", str(max_submit_cost_usd)])
    parts.extend(["--batch-cost-limit-usd", str(batch_cost_limit_usd)])
    return " ".join(parts)


def build_openreview_execution_runbook(
    *,
    venue_specs: list[dict[str, Any]],
    venues_path: str = "data/config/openreview_venues_2025.json",
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
    model: str = DEFAULT_BATCH_MODEL,
    max_submit_cost_usd: float = 25.0,
    batch_cost_limit_usd: float = 25.0,
) -> dict[str, Any]:
    core = core_specs(venue_specs)
    probes = probe_specs(venue_specs)
    excluded = excluded_specs(venue_specs)
    pilot_venues = [venue_id(spec) for spec in core]
    probe_venues = [venue_id(spec) for spec in probes]
    phases = [
        {
            "phase": "install_cookie_and_probe_inventory",
            "purpose": "Install a browser-verified OpenReview cookie, then confirm which 2025 venues expose public reviews.",
            "commands": [
                "python -m secondopinion.tools.openreview_challenge_resume --cookie-file path\\to\\browser-cookies.txt --execute-probe --skip-existing --pull-limit "
                + str(sample_limit),
                "python -m secondopinion.tools.openreview_secret_check --out data/validation/openreview_secret_check.json",
                "python -m secondopinion.tools.openreview_local_refresh --max-total-cost-usd " + str(batch_cost_limit_usd),
            ],
            "success_gate": "openreview_resolved_inventory.ready_to_pull_and_score contains venues confirmed by candidate-level public-review probes",
        },
        {
            "phase": "priority1_pilots",
            "purpose": "Run safe pull/build stages for core 2025 venues with a small paper limit before any full crawl.",
            "venues": pilot_venues,
            "commands": [
                safe_pipeline_command(
                    venues_path=venues_path,
                    venue=value,
                    pull_limit=sample_limit,
                    execute_safe=True,
                    cookie_file_placeholder="path\\to\\browser-cookies.txt",
                    max_submit_cost_usd=max_submit_cost_usd,
                    batch_cost_limit_usd=batch_cost_limit_usd,
                )
                for value in pilot_venues
            ],
            "success_gate": "openreview_pilot_readiness returns ready_for_full_pull for each selected venue; interrupted pulls leave manifest.failed=true and can be rerun with --resume",
        },
        {
            "phase": "priority1_full_pull_and_batch_build",
            "purpose": "Promote core venues to full safe pull/build only after their pilots pass readiness checks.",
            "venues": pilot_venues,
            "commands": [
                safe_pipeline_command(
                    venues_path=venues_path,
                    venue=value,
                    execute_safe=True,
                    cookie_file_placeholder="path\\to\\browser-cookies.txt",
                    max_submit_cost_usd=max_submit_cost_usd,
                    batch_cost_limit_usd=batch_cost_limit_usd,
                )
                for value in pilot_venues
            ],
            "success_gate": "batch_cost_review is under budget and no submit_batch has been run; interrupted pulls leave manifest.next_offset for --resume",
        },
        {
            "phase": "priority2_public_review_probe",
            "purpose": "Only pull and score candidate venues after inventory confirms public official-review coverage.",
            "venues": probe_venues,
            "commands": [
                safe_pipeline_command(
                    venues_path=venues_path,
                    venue=value,
                    pull_limit=sample_limit,
                    execute_safe=True,
                    cookie_file_placeholder="path\\to\\browser-cookies.txt",
                    max_submit_cost_usd=max_submit_cost_usd,
                    batch_cost_limit_usd=batch_cost_limit_usd,
                )
                for value in probe_venues
            ],
            "success_gate": "score only venues whose sample quality shows non-empty public reviews",
        },
        {
            "phase": "batch_submit_after_cost_review",
            "purpose": "Submit OpenAI Batch jobs only after manifests exist and total estimated cost is acceptable.",
            "commands": [
                "python -m secondopinion.tools.batch_cost_review --manifest data/batch/**/*_manifest.json --out data/validation/batch_cost_review.json --markdown reports/validation/batch_cost_review.md --max-total-cost-usd "
                + str(batch_cost_limit_usd),
                "python -m secondopinion.tools.openreview_plan_runner --plan data/validation/openreview_ingestion_plan_2025.json --include-costly --stage submit_batch --max-submit-cost-usd "
                + str(max_submit_cost_usd),
            ],
            "success_gate": "human approval for OpenAI spend; submit_batch is intentionally separate from safe pipeline",
        },
    ]
    return {
        "schema_version": RUNBOOK_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "venues_path": venues_path,
        "model": model,
        "sample_limit": sample_limit,
        "max_submit_cost_usd": max_submit_cost_usd,
        "batch_cost_limit_usd": batch_cost_limit_usd,
        "summary": {
            "core_priority1": pilot_venues,
            "probe_priority2": probe_venues,
            "excluded": [venue_id(spec) for spec in excluded],
            "phase_count": len(phases),
        },
        "phases": phases,
    }


def render_openreview_execution_runbook_markdown(runbook: dict[str, Any]) -> str:
    summary = runbook.get("summary") or {}
    lines = [
        "# OpenReview 2025 Execution Runbook",
        "",
        f"- Created: `{runbook.get('created_at', '')}`",
        f"- Model: `{runbook.get('model', '')}`",
        f"- Pilot sample limit: `{runbook.get('sample_limit', '')}`",
        f"- Core priority 1: `{', '.join(summary.get('core_priority1') or []) or '-'}`",
        f"- Probe priority 2: `{', '.join(summary.get('probe_priority2') or []) or '-'}`",
        f"- Excluded: `{', '.join(summary.get('excluded') or []) or '-'}`",
        "",
    ]
    for phase in runbook.get("phases", []):
        lines.extend([
            f"## {phase.get('phase', '')}",
            "",
            str(phase.get("purpose", "")),
            "",
            f"- Venues: `{', '.join(phase.get('venues') or []) or '-'}`",
            f"- Success gate: {phase.get('success_gate', '')}",
            "- Resume note: pull commands include `--resume`; if a network/API error interrupts a crawl, inspect the raw snapshot `manifest.json` for `failed`, `error`, and `next_offset`, then rerun the same command.",
            "",
            "```powershell",
        ])
        lines.extend(str(command) for command in phase.get("commands", []))
        lines.extend(["```", ""])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the staged OpenReview 2025 cookie/pilot/full/batch runbook.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--out", default="data/validation/openreview_execution_runbook_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_execution_runbook_2025.md")
    parser.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    parser.add_argument("--model", default=DEFAULT_BATCH_MODEL)
    parser.add_argument("--max-submit-cost-usd", type=float, default=25.0)
    parser.add_argument("--batch-cost-limit-usd", type=float, default=25.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    runbook = build_openreview_execution_runbook(
        venue_specs=load_venue_specs(args.venues),
        venues_path=args.venues,
        sample_limit=args.sample_limit,
        model=args.model,
        max_submit_cost_usd=args.max_submit_cost_usd,
        batch_cost_limit_usd=args.batch_cost_limit_usd,
    )
    write_json(args.out, runbook)
    write_text(args.markdown, render_openreview_execution_runbook_markdown(runbook))
    print(json.dumps(runbook["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
