from __future__ import annotations

import html
import statistics
from pathlib import Path
from typing import Any


def summarize(audit_result: dict[str, Any]) -> dict[str, Any]:
    audits = audit_result.get("audits", [])
    scores = [audit["rqs_score"] for audit in audits]
    flags: dict[str, int] = {}
    for audit in audits:
        for flag in audit.get("issue_flags", []):
            flags[flag] = flags.get(flag, 0) + 1
    return {
        "audit_count": len(audits),
        "average_rqs": round(statistics.mean(scores), 1) if scores else 0,
        "min_rqs": min(scores) if scores else 0,
        "max_rqs": max(scores) if scores else 0,
        "flags": dict(sorted(flags.items(), key=lambda item: (-item[1], item[0]))),
    }


def write_markdown_report(audit_result: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize(audit_result)
    lines = [
        "# SecondOpinion MVP Audit Report",
        "",
        f"- Dataset: `{audit_result.get('dataset', 'unknown')}`",
        f"- Papers: {audit_result.get('paper_count', 0)}",
        f"- Reviews audited: {summary['audit_count']}",
        f"- Average RQS: {summary['average_rqs']}",
        f"- RQS range: {summary['min_rqs']} - {summary['max_rqs']}",
        f"- Auditor: `{audit_result.get('model_version')}`",
        "",
        "## Issue Flags",
        "",
    ]
    if summary["flags"]:
        for flag, count in summary["flags"].items():
            lines.append(f"- `{flag}`: {count}")
    else:
        lines.append("- No issue flags.")

    lines.extend(["", "## Review Audits", ""])
    for audit in audit_result.get("audits", []):
        flags = ", ".join(f"`{flag}`" for flag in audit.get("issue_flags", [])) or "None"
        lines.extend(
            [
                f"### Review `{audit.get('review_id')}`",
                "",
                f"- Paper: `{audit.get('paper_id')}`",
                f"- RQS: **{audit.get('rqs_score')}**",
                f"- Confidence: `{audit.get('audit_confidence')}`",
                f"- Flags: {flags}",
                f"- Summary: {audit.get('summary')}",
                "",
                "| Claim | Type | Verdict | Evidence | Flags |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for claim in audit.get("claims", []):
            evidence = claim.get("evidence", [])
            top_evidence = evidence[0]["section"] if evidence else "none"
            claim_flags = ", ".join(claim.get("issue_flags", [])) or "none"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(claim.get("claim_text", "")),
                        _md_cell(claim.get("claim_type", "")),
                        _md_cell(claim.get("verdict", "")),
                        _md_cell(top_evidence),
                        _md_cell(claim_flags),
                    ]
                )
                + " |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_html_report(audit_result: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize(audit_result)
    flag_items = "".join(
        f"<li><code>{html.escape(flag)}</code><span>{count}</span></li>"
        for flag, count in summary["flags"].items()
    ) or "<li>No issue flags<span>0</span></li>"
    cards = []
    for audit in audit_result.get("audits", []):
        claims = []
        for claim in audit.get("claims", []):
            evidence = claim.get("evidence") or []
            top = evidence[0] if evidence else None
            evidence_html = (
                f"<blockquote><b>{html.escape(top['source_type'])}/{html.escape(top['section'])}</b>: "
                f"{html.escape(top['text'])}</blockquote>"
                if top
                else "<blockquote>No evidence retrieved.</blockquote>"
            )
            flags = " ".join(f"<span>{html.escape(flag)}</span>" for flag in claim.get("issue_flags", []))
            claims.append(
                f"""
                <details>
                  <summary>{html.escape(claim.get('claim_text', ''))}</summary>
                  <div class="claim-meta">
                    <code>{html.escape(claim.get('claim_type', ''))}</code>
                    <code>{html.escape(claim.get('verdict', ''))}</code>
                    <code>{html.escape(claim.get('audit_confidence', ''))}</code>
                  </div>
                  {evidence_html}
                  <div class="flags">{flags}</div>
                </details>
                """
            )
        flags = " ".join(f"<span>{html.escape(flag)}</span>" for flag in audit.get("issue_flags", []))
        cards.append(
            f"""
            <article class="audit-card">
              <div class="card-top">
                <div>
                  <h2>Review {html.escape(audit.get('review_id', ''))}</h2>
                  <p>{html.escape(audit.get('summary', ''))}</p>
                </div>
                <div class="score">{audit.get('rqs_score')}</div>
              </div>
              <div class="meta">
                <code>{html.escape(audit.get('paper_id', ''))}</code>
                <code>{html.escape(audit.get('audit_confidence', ''))}</code>
              </div>
              <div class="flags">{flags}</div>
              <div class="claims">{''.join(claims)}</div>
            </article>
            """
        )
    document = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>SecondOpinion MVP Audit Report</title>
      <style>
        :root {{
          color-scheme: light;
          --ink: #172026;
          --muted: #5b6670;
          --line: #d8dee4;
          --panel: #ffffff;
          --soft: #f5f7f8;
          --accent: #0f766e;
          --warn: #b45309;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: var(--ink);
          background: var(--soft);
        }}
        header {{
          padding: 32px clamp(20px, 5vw, 64px);
          background: #ffffff;
          border-bottom: 1px solid var(--line);
        }}
        h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
        h2 {{ margin: 0; font-size: 18px; letter-spacing: 0; }}
        p {{ color: var(--muted); line-height: 1.55; }}
        main {{ padding: 24px clamp(20px, 5vw, 64px) 48px; }}
        .summary {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 12px;
          margin-bottom: 20px;
        }}
        .metric, .audit-card {{
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
        }}
        .metric {{ padding: 16px; }}
        .metric b {{ display: block; font-size: 26px; }}
        .metric span {{ color: var(--muted); font-size: 13px; }}
        .flag-list {{
          background: #fff;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 16px 18px;
          margin-bottom: 20px;
        }}
        .flag-list ul {{ list-style: none; padding: 0; margin: 8px 0 0; }}
        .flag-list li {{ display: flex; justify-content: space-between; border-top: 1px solid var(--line); padding: 8px 0; }}
        .audit-card {{ padding: 18px; margin-bottom: 16px; }}
        .card-top {{ display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; }}
        .score {{
          min-width: 64px;
          height: 64px;
          border-radius: 8px;
          background: var(--accent);
          color: #fff;
          display: grid;
          place-items: center;
          font-size: 24px;
          font-weight: 700;
        }}
        .meta, .claim-meta, .flags {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
        code, .flags span {{
          border: 1px solid var(--line);
          border-radius: 6px;
          padding: 3px 7px;
          background: #f8fafb;
          color: var(--muted);
          font-size: 12px;
        }}
        .flags span {{ color: var(--warn); background: #fff7ed; border-color: #fed7aa; }}
        details {{ border-top: 1px solid var(--line); padding: 12px 0; }}
        summary {{ cursor: pointer; font-weight: 600; line-height: 1.4; }}
        blockquote {{
          margin: 10px 0 0;
          padding: 10px 12px;
          border-left: 3px solid var(--accent);
          background: #f0fdfa;
          color: #334155;
          line-height: 1.5;
        }}
      </style>
    </head>
    <body>
      <header>
        <h1>SecondOpinion MVP Audit Report</h1>
        <p>Dataset <code>{html.escape(audit_result.get('dataset', 'unknown'))}</code> audited with <code>{html.escape(audit_result.get('model_version', ''))}</code>.</p>
      </header>
      <main>
        <section class="summary">
          <div class="metric"><b>{summary['audit_count']}</b><span>Reviews audited</span></div>
          <div class="metric"><b>{summary['average_rqs']}</b><span>Average RQS</span></div>
          <div class="metric"><b>{summary['min_rqs']}-{summary['max_rqs']}</b><span>RQS range</span></div>
          <div class="metric"><b>{audit_result.get('paper_count', 0)}</b><span>Papers</span></div>
        </section>
        <section class="flag-list">
          <h2>Issue Flags</h2>
          <ul>{flag_items}</ul>
        </section>
        {''.join(cards)}
      </main>
    </body>
    </html>
    """
    path.write_text(document, encoding="utf-8")


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")

