from __future__ import annotations

import html
import re
import statistics
from pathlib import Path
from typing import Any


CLAIM_TYPE_LABELS = {
    "ablation": "Ablation: critique about missing or weak component analysis.",
    "baseline": "Baselines: critique about comparisons to prior methods.",
    "experiment": "Experiments: critique about evaluation setup, data, or metrics.",
    "methodology": "Methodology: critique about method design or technical description.",
    "theory": "Theory: critique about assumptions, proofs, or formal claims.",
    "novelty": "Novelty: critique about whether the contribution is new.",
    "clarity": "Clarity: critique about unclear, underspecified, or hard-to-follow writing.",
    "writing": "Writing: comment about presentation, grammar, or readability.",
    "ethics": "Ethics: concern about privacy, safety, fairness, or broader impact.",
    "tone": "Tone: comment about the professionalism of the review language.",
    "general": "General: broader review point.",
}

VERDICT_LABELS = {
    "supported": "The critique appears well grounded in the manuscript.",
    "partially_supported": "The critique is partly grounded, but the evidence is incomplete.",
    "insufficient": "The available manuscript evidence is not enough to support the critique.",
    "possibly_contradicted": "The manuscript appears to answer or weaken this critique.",
    "vague_or_not_checkable": "The critique is too broad to evaluate precisely from the manuscript.",
    "needs_human_check": "This point depends on specialist context beyond the retrieved passage.",
}

FLAG_LABELS = {
    "possibly-contradicted-by-paper": "Manuscript may already address this critique.",
    "unsupported-major-claim": "Major critique has weak manuscript support.",
    "vague-or-not-checkable": "Critique is too broad to evaluate precisely.",
    "vague-criticism": "The criticism lacks concrete detail.",
    "unprofessional-tone": "The reviewer wording may fall below professional tone standards.",
    "missing-actionable-suggestions": "Critique gives limited guidance for improvement.",
    "requires-human-expert-check": "Specialist context is needed.",
    "llm-judge-failed": "Automated assessment used a fallback method.",
}

STANCE_LABELS = {
    "strongly_disagree": "Strongly disagree",
    "disagree": "Disagree",
    "mixed": "Mixed",
    "agree": "Agree",
    "strongly_agree": "Strongly agree",
}

LEGACY_STANCE_MAP = {
    "well_supported": "agree",
    "partially_supported": "mixed",
    "weakly_supported": "disagree",
    "answered_or_contradicted": "strongly_disagree",
    "not_enough_context": "mixed",
    "too_broad_or_unclear": "mixed",
}

SOURCE_FIELD_LABELS = {
    "summary": "Summary section",
    "strengths": "Strengths section",
    "weaknesses": "Weaknesses section",
    "questions": "Questions section",
    "review_text": "Main review text",
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
        "# SecondOpinion Review Quality Report",
        "",
        f"- Dataset: `{audit_result.get('dataset', 'unknown')}`",
        f"- Papers: {audit_result.get('paper_count', 0)}",
        f"- Reviews audited: {summary['audit_count']}",
        f"- Average Review Quality Score: {summary['average_rqs']}",
        f"- Review Quality Score range: {summary['min_rqs']} - {summary['max_rqs']}",
        "",
        "## Potential Review Issues",
        "",
    ]
    if summary["flags"]:
        for flag, count in summary["flags"].items():
            lines.append(f"- {flag_label(flag)}: {count}")
    else:
        lines.append("- No recurring issues detected.")

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
                f"- Review Quality Score: **{audit.get('rqs_score')}**",
                f"- Assessment confidence: `{audit.get('audit_confidence')}`",
                f"- Notes: {flags}",
                f"- Summary: {audit.get('summary')}",
                "",
                "| Review point | SecondOpinion stance | SecondOpinion take | Most relevant passage | Notes |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for claim in audit.get("claims", []):
            evidence = claim.get("evidence", [])
            top_evidence = evidence_label(evidence[0]) if evidence else "none"
            claim_flags = "; ".join(flag_label(flag) for flag in claim.get("issue_flags", [])) or "None"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(claim.get("claim_text", "")),
                        _md_cell(stance_label(claim)),
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
        f"<li><span>{_h(flag_label(flag))}</span><b>{count}</b></li>"
        for flag, count in summary["flags"].items()
    ) or "<li>No recurring issues detected.<b>0</b></li>"
    cards = []
    for audit in audit_result.get("audits", []):
        claims = []
        for claim in audit.get("claims", []):
            evidence = claim.get("evidence") or []
            top = evidence[0] if evidence else None
            top_label = evidence_label(top) if top else ""
            evidence_html = (
                f"""
                <section class="evidence-block compact">
                  <h4>Manuscript reference</h4>
                  <blockquote>
                    <b>{_h(top_label)}</b>
                    <p>{_h(top['text'])}</p>
                  </blockquote>
                </section>
                """
                if top
                else """
                <section class="evidence-block compact">
                  <h4>Manuscript reference</h4>
                  <blockquote>No clearly relevant manuscript passage was found.</blockquote>
                </section>
                """
            )
            flags = " ".join(
                f"<span title=\"{_h(flag)}\">{_h(flag_label(flag))}</span>"
                for flag in claim.get("issue_flags", [])
            )
            if not flags:
                flags = "<span>No additional notes.</span>"
            assessment = claim_assessment_text(claim)
            stance = stance_value(claim)
            claims.append(
                f"""
                <details>
                  <summary>{_h(claim.get('claim_text', ''))}</summary>
                  <section class="take-card">
                    <div class="take-top">
                      <div>
                        <h3>SecondOpinion take</h3>
                        <p>{_h(assessment)}</p>
                      </div>
                      <div class="stance-badge {stance_class(stance)}">
                        <b>{_h(stance_label(claim))}</b>
                        <span>SecondOpinion stance</span>
                      </div>
                    </div>
                    <div class="take-meta">
                      <span>{_h(short_claim_type_label(claim.get('claim_type', '')))}</span>
                      <span>{_h(confidence_label(claim.get('audit_confidence', '')))}</span>
                    </div>
                  </section>
                  <details class="reference-materials">
                    <summary>Reference material</summary>
                    <section class="source-block compact">
                      <h4>Reviewer wording</h4>
                      <p>{_h(claim.get('source_sentence', '') or 'No source sentence recorded.')}</p>
                    </section>
                    {evidence_html}
                  </details>
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
      <title>SecondOpinion Review Quality Report</title>
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
        .flag-list li {{ display: flex; justify-content: space-between; gap: 16px; border-top: 1px solid var(--line); padding: 8px 0; }}
        .flag-list b {{ font-size: 16px; }}
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
        .take-card {{
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #f0f9ff;
          padding: 14px;
          margin-top: 12px;
        }}
        .take-top {{
          display: grid;
          grid-template-columns: minmax(0, 1fr) 150px;
          gap: 14px;
          align-items: start;
        }}
        .take-card h3 {{
          margin: 0;
          font-size: 14px;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0;
        }}
        .take-card p {{
          margin: 8px 0 0;
          color: var(--ink);
          font-size: 17px;
          line-height: 1.55;
        }}
        .stance-badge {{
          border-radius: 8px;
          color: #fff;
          padding: 10px;
          text-align: center;
        }}
        .stance-strongly-agree {{ background: #047857; }}
        .stance-agree {{ background: #0f766e; }}
        .stance-mixed {{ background: #b45309; }}
        .stance-disagree {{ background: #b91c1c; }}
        .stance-strongly-disagree {{ background: #7f1d1d; }}
        .stance-badge b {{
          display: block;
          font-size: 18px;
          line-height: 1.15;
        }}
        .stance-badge span {{
          display: block;
          margin-top: 4px;
          font-size: 12px;
        }}
        .take-meta {{
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 12px;
        }}
        .take-meta span {{
          border: 1px solid #bae6fd;
          border-radius: 999px;
          background: #fff;
          color: #0369a1;
          padding: 4px 8px;
          font-size: 12px;
        }}
        .reference-materials {{
          border-top: 0;
          margin-top: 10px;
          padding: 0;
        }}
        .reference-materials > summary {{
          color: var(--muted);
          font-size: 13px;
          font-weight: 600;
        }}
        .source-block, .evidence-block {{
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fff;
          padding: 10px 12px;
          margin-top: 8px;
        }}
        .source-block.compact p, .evidence-block.compact p {{
          margin: 0;
          color: var(--muted);
          font-size: 13px;
          line-height: 1.45;
        }}
        .source-block h4, .evidence-block h4 {{
          margin: 0 0 6px;
          color: var(--muted);
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0;
        }}
        blockquote {{
          margin: 0;
          padding: 8px 10px;
          border-left: 3px solid var(--accent);
          background: #f0fdfa;
          color: #334155;
          line-height: 1.5;
        }}
        blockquote b {{
          display: block;
          margin-bottom: 6px;
          color: var(--muted);
          font-size: 12px;
        }}
      </style>
    </head>
    <body>
      <header>
        <h1>SecondOpinion Review Quality Report</h1>
        <p>Evidence-grounded assessment of reviewer comments, manuscript support, specificity, tone, and usefulness for authors.</p>
      </header>
      <main>
        <section class="summary">
          <div class="metric"><b>{summary['audit_count']}</b><span>Reviews assessed</span></div>
          <div class="metric"><b>{summary['average_rqs']}</b><span>Average Review Quality Score</span></div>
          <div class="metric"><b>{summary['min_rqs']}-{summary['max_rqs']}</b><span>Review Quality Score range</span></div>
          <div class="metric"><b>{audit_result.get('paper_count', 0)}</b><span>Papers</span></div>
        </section>
        <section class="flag-list">
          <h2>Potential Review Issues</h2>
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
        label = "Author response"
    elif section == "title":
        label = "Paper title"
    elif section == "abstract":
        label = "Paper abstract"
    else:
        label = f"Manuscript section {section}"
    if evidence.get("page"):
        label = f"{label} p.{evidence['page']}"
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
        "supporting_candidate": "This passage is relevant to the review point.",
        "partial_candidate": "This passage is related, but does not fully settle the point.",
        "possibly_contradicting_candidate": "This passage may weaken the review point.",
    }
    return labels.get(str(verdict), "This passage is included as supporting context.")


def flag_label(flag: str) -> str:
    return FLAG_LABELS.get(str(flag), str(flag).replace("-", " "))


def short_claim_type_label(claim_type: str) -> str:
    labels = {
        "ablation": "Ablation",
        "baseline": "Baselines",
        "experiment": "Experiments",
        "methodology": "Methodology",
        "theory": "Theory",
        "novelty": "Novelty",
        "clarity": "Clarity",
        "writing": "Writing",
        "ethics": "Ethics",
        "tone": "Tone",
        "general": "General",
    }
    return labels.get(str(claim_type), "General")


def confidence_label(confidence: Any) -> str:
    value = str(confidence or "").strip().lower()
    if value == "high":
        return "High confidence"
    if value == "medium":
        return "Medium confidence"
    if value == "low":
        return "Low confidence"
    return "Confidence not available"


def support_percent(claim: dict[str, Any]) -> int:
    explicit = claim.get("support_score")
    if isinstance(explicit, (int, float)):
        return int(max(0, min(100, explicit)))
    verdict = str(claim.get("verdict") or "")
    if verdict == "supported":
        base = 85
    elif verdict == "partially_supported":
        base = 58
    elif verdict == "insufficient":
        base = 30
    elif verdict == "possibly_contradicted":
        base = 18
    elif verdict == "vague_or_not_checkable":
        base = 40
    elif verdict == "needs_human_check":
        base = 50
    else:
        base = 50

    evidence_support = claim.get("evidence_support")
    if verdict in {"supported", "partially_supported", "insufficient"} and isinstance(evidence_support, (int, float)):
        base = round((base + max(0, min(3, float(evidence_support))) / 3 * 100) / 2)
    return int(max(0, min(100, base)))


def support_class(score: int) -> str:
    if score >= 70:
        return "support-high"
    if score >= 45:
        return "support-mid"
    return "support-low"


def stance_value(claim: dict[str, Any]) -> str:
    stance = str(claim.get("stance") or "").strip()
    if stance in STANCE_LABELS:
        return stance
    if stance in LEGACY_STANCE_MAP:
        return LEGACY_STANCE_MAP[stance]
    score = support_percent(claim)
    if score >= 82:
        return "strongly_agree"
    if score >= 62:
        return "agree"
    if score >= 40:
        return "mixed"
    if score >= 20:
        return "disagree"
    return "strongly_disagree"


def stance_label(claim: dict[str, Any]) -> str:
    return STANCE_LABELS[stance_value(claim)]


def stance_class(stance: str) -> str:
    if stance not in STANCE_LABELS:
        stance = "mixed"
    return f"stance-{stance.replace('_', '-')}"


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
    if judge_version.startswith(("llm-rag-judge", "review-point-judge")):
        if "+fallback" in judge_version:
            return "SecondOpinion fallback assessment."
        return "SecondOpinion expert assessment."
    if judge_version.startswith("rule-baseline"):
        return "SecondOpinion evidence screen."
    return "SecondOpinion assessment."


def claim_assessment_text(claim: dict[str, Any]) -> str:
    explicit_take = _display_text(claim.get("second_opinion_take"))
    if explicit_take:
        return explicit_take
    rationale = str(claim.get("judge_rationale") or "").strip()
    judge_version = str(claim.get("judge_version") or "")
    evidence = claim.get("evidence") or []
    top = evidence[0] if evidence else None
    quote = evidence_quote(top)
    verdict = str(claim.get("verdict") or "")

    if verdict == "supported":
        take = "SecondOpinion finds this review point well supported."
        if quote:
            take += f" The manuscript backs it up with: \"{quote}\""
    elif verdict == "partially_supported":
        take = "SecondOpinion finds this review point only partly supported."
        if quote:
            take += f" The closest manuscript evidence is: \"{quote}\""
    elif verdict == "possibly_contradicted":
        take = "SecondOpinion finds this review point weakly supported."
        if quote:
            take += f" The manuscript appears to address it directly: \"{quote}\""
    elif verdict == "insufficient":
        take = "SecondOpinion finds too little manuscript support for this review point."
        if quote:
            take += f" The closest passage is related but not decisive: \"{quote}\""
    elif verdict == "vague_or_not_checkable":
        take = "SecondOpinion finds this review point too broad to evaluate cleanly from the manuscript."
        if quote:
            take += f" The closest relevant passage is: \"{quote}\""
    elif verdict == "needs_human_check":
        take = "SecondOpinion finds this point dependent on specialist context beyond the retrieved passage."
        if quote:
            take += f" The closest passage is: \"{quote}\""
    else:
        take = verdict_label(verdict)
        if quote:
            take += f" Relevant manuscript text: \"{quote}\""

    if judge_version.startswith(("llm-rag-judge", "review-point-judge")) and rationale and "fallback" not in judge_version:
        take += f" Rationale: {rationale}"
    return take


def evidence_quote(evidence: dict[str, Any] | None, max_chars: int = 220) -> str:
    if not evidence:
        return ""
    text = _display_text(evidence.get("text"))
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."
