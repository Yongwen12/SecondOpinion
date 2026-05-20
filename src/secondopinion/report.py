from __future__ import annotations

import html
import re
import statistics
from pathlib import Path
from typing import Any


CLAIM_TYPE_LABELS = {
    "ablation": "Ablation concern: the reviewer says an experiment or component analysis is missing.",
    "baseline": "Baseline concern: the reviewer says comparisons to prior methods are missing or weak.",
    "experiment": "Experiment concern: the reviewer questions the evaluation setup, data, or metrics.",
    "methodology": "Methodology concern: the reviewer questions the method design or technical description.",
    "theory": "Theory concern: the reviewer questions assumptions, proofs, or formal claims.",
    "novelty": "Novelty concern: the reviewer questions whether the contribution is new.",
    "clarity": "Clarity concern: the reviewer says the paper is unclear, underspecified, or hard to follow.",
    "writing": "Writing concern: the reviewer comments on presentation, grammar, or readability.",
    "ethics": "Ethics concern: the reviewer raises ethics, privacy, safety, or broader impact issues.",
    "tone": "Tone concern: the extracted claim is about reviewer language or professionalism.",
    "general": "General concern: the claim does not fit a more specific category.",
}

VERDICT_LABELS = {
    "supported": "Evidence appears to support the reviewer's criticism.",
    "partially_supported": "Evidence partially supports the criticism, but the match is incomplete.",
    "insufficient": "Retrieved evidence is not enough to verify the criticism.",
    "possibly_contradicted": "Retrieved paper evidence may contradict or weaken the criticism.",
    "vague_or_not_checkable": "The criticism is too broad or vague to check against the retrieved evidence.",
    "needs_human_check": "This claim needs human or domain-expert judgment.",
}

FLAG_LABELS = {
    "possibly-contradicted-by-paper": "The paper may contain evidence that weakens this reviewer criticism.",
    "unsupported-major-claim": "A major criticism did not retrieve enough supporting evidence.",
    "vague-or-not-checkable": "The criticism is too broad or underspecified for automatic checking.",
    "vague-criticism": "The criticism lacks concrete detail.",
    "unprofessional-tone": "The reviewer wording may fall below professional tone standards.",
    "missing-actionable-suggestions": "The criticism does not give the authors a clear next step.",
    "requires-human-expert-check": "This point needs human or domain-expert review.",
    "llm-judge-failed": "The LLM judge failed, so the system used the fallback verdict.",
}

SOURCE_FIELD_LABELS = {
    "summary": "reviewer summary",
    "strengths": "reviewer strengths",
    "weaknesses": "reviewer weaknesses",
    "questions": "reviewer questions",
    "review_text": "review body",
}


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
        f"- Claim extraction: `{audit_result.get('claim_extraction_version', 'unknown')}`",
        f"- Claim model: `{audit_result.get('claim_model', 'unknown')}`",
        f"- Judge: `{audit_result.get('judge_version', 'unknown')}`",
        f"- Judge model: `{audit_result.get('judge_model', 'rule-baseline') or 'rule-baseline'}`",
        f"- Evidence retrieval: `{audit_result.get('retrieval_version', 'unknown')}`",
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
                f"- Reviewer rating: {review_rating_label(audit)}",
                f"- Reviewer confidence: {reviewer_confidence_label(audit)}",
                f"- Final decision: {audit.get('decision') or 'Unknown'}",
                f"- RQS: **{audit.get('rqs_score')}**",
                f"- Confidence: `{audit.get('audit_confidence')}`",
                f"- Flags: {flags}",
                f"- Summary: {audit.get('summary')}",
                "",
                "| Claim | Reviewer source | Category | System assessment | Top evidence | Flags |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for claim in audit.get("claims", []):
            evidence = claim.get("evidence", [])
            top_evidence = evidence_label(evidence[0]) if evidence else "none"
            claim_flags = "; ".join(flag_label(flag) for flag in claim.get("issue_flags", [])) or "none"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(claim.get("claim_text", "")),
                        _md_cell(claim_source_label(claim)),
                        _md_cell(claim_type_label(claim.get("claim_type", ""))),
                        _md_cell(claim_assessment_text(claim)),
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
        f"<li><code>{_h(flag)}</code><span>{count}</span></li>"
        for flag, count in summary["flags"].items()
    ) or "<li>No issue flags<span>0</span></li>"
    cards = []
    for audit in audit_result.get("audits", []):
        claims = []
        for claim in audit.get("claims", []):
            evidence = claim.get("evidence") or []
            top = evidence[0] if evidence else None
            top_label = evidence_label(top) if top else ""
            evidence_html = (
                f"""
                <section class="evidence-block">
                  <h3>Top retrieved evidence</h3>
                  <blockquote>
                    <b>{_h(top_label)}</b>
                    <span>{_h(evidence_verdict_label(top.get('verdict', '')))}</span>
                    <p>{_h(top['text'])}</p>
                  </blockquote>
                </section>
                """
                if top
                else """
                <section class="evidence-block">
                  <h3>Top retrieved evidence</h3>
                  <blockquote>No evidence retrieved.</blockquote>
                </section>
                """
            )
            flags = " ".join(
                f"<span title=\"{_h(flag)}\">{_h(flag_label(flag))}</span>"
                for flag in claim.get("issue_flags", [])
            )
            if not flags:
                flags = "<span>No issue flags for this claim.</span>"
            assessment = claim_assessment_text(claim)
            claims.append(
                f"""
                <details>
                  <summary>{_h(claim.get('claim_text', ''))}</summary>
                  <div class="claim-facts">
                    <div>
                      <span>Reviewer source</span>
                      <p>{_h(claim_source_label(claim))}</p>
                    </div>
                    <div>
                      <span>Claim category</span>
                      <p>{_h(claim_type_label(claim.get('claim_type', '')))}</p>
                    </div>
                    <div>
                      <span>System verdict</span>
                      <p>{_h(verdict_label(claim.get('verdict', '')))}</p>
                    </div>
                    <div>
                      <span>Judge</span>
                      <p>{_h(judge_label(claim))}</p>
                    </div>
                  </div>
                  <section class="source-block">
                    <h3>Reviewer text used for this claim</h3>
                    <p>{_h(claim.get('source_sentence', '') or 'No source sentence recorded.')}</p>
                  </section>
                  {evidence_html}
                  <section class="assessment">
                    <h3>System assessment</h3>
                    <p>{_h(assessment)}</p>
                  </section>
                  <div class="flags">{flags}</div>
                </details>
                """
            )
        flags = " ".join(
            f"<span title=\"{_h(flag)}\">{_h(flag_label(flag))}</span>"
            for flag in audit.get("issue_flags", [])
        )
        cards.append(
            f"""
            <article class="audit-card">
              <div class="card-top">
                <div>
                  <h2>Review {_h(audit.get('review_id', ''))}</h2>
                  <p>{_h(audit.get('summary', ''))}</p>
                </div>
                <div class="score">{audit.get('rqs_score')}</div>
              </div>
              <div class="meta">
                <code>{_h(audit.get('paper_id', ''))}</code>
                <code>{_h(audit.get('audit_confidence', ''))}</code>
              </div>
              <div class="review-context">
                <div>
                  <span>Reviewer rating</span>
                  <p>{_h(review_rating_label(audit))}</p>
                </div>
                <div>
                  <span>Reviewer confidence</span>
                  <p>{_h(reviewer_confidence_label(audit))}</p>
                </div>
                <div>
                  <span>Final decision</span>
                  <p>{_h(audit.get('decision') or 'Unknown')}</p>
                </div>
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
        .review-context {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
          gap: 10px;
          margin: 12px 0;
        }}
        .review-context div {{
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #f8fafb;
          padding: 10px 12px;
        }}
        .review-context span {{
          display: block;
          margin: 0 0 6px;
          color: var(--muted);
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0;
        }}
        .review-context p {{
          margin: 0;
          color: var(--ink);
          line-height: 1.45;
        }}
        .claim-facts {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
          gap: 10px;
          margin: 12px 0;
        }}
        .claim-facts div, .source-block, .assessment, .evidence-block {{
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fff;
          padding: 10px 12px;
        }}
        .claim-facts span, .source-block h3, .assessment h3, .evidence-block h3 {{
          display: block;
          margin: 0 0 6px;
          color: var(--muted);
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0;
        }}
        .claim-facts p, .source-block p, .assessment p, .evidence-block p {{
          margin: 0;
          color: var(--ink);
          line-height: 1.5;
        }}
        .source-block, .assessment, .evidence-block {{
          margin-top: 10px;
        }}
        .assessment {{
          border-color: #bae6fd;
          background: #f0f9ff;
        }}
        blockquote {{
          margin: 10px 0 0;
          padding: 10px 12px;
          border-left: 3px solid var(--accent);
          background: #f0fdfa;
          color: #334155;
          line-height: 1.5;
        }}
        blockquote b {{ display: block; margin-bottom: 6px; }}
        blockquote span {{
          display: inline-block;
          margin-bottom: 8px;
          color: var(--muted);
          font-size: 13px;
        }}
      </style>
    </head>
    <body>
      <header>
        <h1>SecondOpinion MVP Audit Report</h1>
        <p>Dataset <code>{_h(audit_result.get('dataset', 'unknown'))}</code> audited with <code>{_h(audit_result.get('model_version', ''))}</code>, <code>{_h(audit_result.get('claim_extraction_version', ''))}</code>, <code>{_h(audit_result.get('claim_model', ''))}</code>, <code>{_h(audit_result.get('judge_version', ''))}</code>, <code>{_h(audit_result.get('judge_model', '') or 'rule-baseline')}</code>, and <code>{_h(audit_result.get('retrieval_version', ''))}</code>.</p>
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
    return _display_text(value).replace("|", "\\|").replace("\n", " ")


def _display_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _h(value: Any) -> str:
    return html.escape(_display_text(value))


def evidence_label(evidence: dict[str, Any]) -> str:
    source_type = str(evidence.get("source_type") or "paper")
    section = str(evidence.get("section") or "unknown")
    if source_type == "rebuttal":
        label = f"Author response / rebuttal - {section}"
    elif section == "title":
        label = "Paper title"
    elif section == "abstract":
        label = "Paper abstract"
    else:
        label = f"PDF evidence - Section {section}"
    if evidence.get("page"):
        label = f"{label} p.{evidence['page']}"
    if evidence.get("score") is not None:
        label = f"{label} score={float(evidence['score']):.2f}"
    return label


def claim_source_label(claim: dict[str, Any]) -> str:
    source = str(claim.get("source_field") or "review")
    source = SOURCE_FIELD_LABELS.get(source, source.replace("_", " "))
    index = claim.get("source_sentence_index")
    if index is None:
        return source
    try:
        return f"{source}, sentence {int(index) + 1}"
    except (TypeError, ValueError):
        return source


def claim_type_label(claim_type: str) -> str:
    return CLAIM_TYPE_LABELS.get(str(claim_type), f"Unmapped category: {claim_type}")


def verdict_label(verdict: str) -> str:
    return VERDICT_LABELS.get(str(verdict), f"Unmapped verdict: {verdict}")


def evidence_verdict_label(verdict: str) -> str:
    labels = {
        "supporting_candidate": "This retrieved passage is a candidate supporting match.",
        "partial_candidate": "This retrieved passage is a partial match.",
        "possibly_contradicting_candidate": "This retrieved passage may contradict the review claim.",
    }
    return labels.get(str(verdict), f"Evidence match label: {verdict}")


def flag_label(flag: str) -> str:
    return FLAG_LABELS.get(str(flag), str(flag).replace("-", " "))


def review_rating_label(audit: dict[str, Any]) -> str:
    raw = _display_text(audit.get("rating_raw"))
    normalized = audit.get("rating_normalized")
    if raw and normalized is not None:
        return f"{raw} (normalized: {normalized})"
    if raw:
        return raw
    if normalized is not None:
        return f"Normalized rating: {normalized}"
    return "Not available"


def reviewer_confidence_label(audit: dict[str, Any]) -> str:
    raw = _display_text(audit.get("reviewer_confidence_raw"))
    normalized = audit.get("reviewer_confidence_normalized")
    if raw and normalized is not None:
        return f"{raw} (normalized: {normalized})"
    if raw:
        return raw
    if normalized is not None:
        return f"Normalized confidence: {normalized}"
    return "Not available"


def judge_label(claim: dict[str, Any]) -> str:
    judge_version = str(claim.get("judge_version") or "unknown")
    model = str(claim.get("judge_model") or "")
    if judge_version.startswith("llm-rag-judge"):
        suffix = f" using {model}" if model else ""
        if "+fallback" in judge_version:
            return f"LLM judge attempted{suffix}; fallback verdict used."
        return f"LLM judge{suffix}."
    if judge_version.startswith("rule-baseline"):
        return "Rule-based evidence matcher; no LLM judge was run for this claim."
    return judge_version


def claim_assessment_text(claim: dict[str, Any]) -> str:
    verdict = verdict_label(str(claim.get("verdict") or ""))
    confidence = str(claim.get("audit_confidence") or "unknown")
    rationale = str(claim.get("judge_rationale") or "").strip()
    judge_version = str(claim.get("judge_version") or "")
    evidence = claim.get("evidence") or []
    top = evidence[0] if evidence else None

    if judge_version.startswith("llm-rag-judge") and rationale and "fallback" not in judge_version:
        return f"{verdict} Confidence: {confidence}. LLM rationale: {rationale}"

    if "fallback" in judge_version:
        fallback = rationale or "The LLM judge failed, so the fallback verdict was used."
        return f"{verdict} Confidence: {confidence}. {fallback}"

    if top:
        evidence_part = f"Top evidence: {evidence_label(top)}."
    else:
        evidence_part = "No evidence passage was retrieved."
    return (
        f"{verdict} Confidence: {confidence}. "
        "This is a rule-based evidence-matching assessment, not an LLM judge evaluation. "
        f"{evidence_part}"
    )
