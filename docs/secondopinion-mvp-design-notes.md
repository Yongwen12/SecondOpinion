# SecondOpinion MVP Design Notes

Last updated: 2026-05-22

This document captures the current product and implementation decisions for the SecondOpinion MVP. It is intentionally written as a working design note: enough structure to guide implementation, but not a frozen spec.

## Product Positioning

SecondOpinion is not a replacement reviewer and does not decide whether a paper should be accepted. The MVP should behave like an evidence-grounded review audit and rebuttal strategy assistant.

The product has two user-facing jobs:

1. **Review Assessment**
   Evaluate the quality and validity of reviewer points: whether they are specific, fair, manuscript-grounded, actionable, professional, and decision-relevant.

2. **Rebuttal Guidance**
   Help authors decide how to respond: what to cite, what to clarify, what to concede, what experiment or explanation might help, and which points deserve priority.

The main trust principle is:

> Do not ask users to trust the LLM. Ask users to trust a transparent process: reviewer quote, manuscript evidence, stated stance, confidence, and a clear rationale.

## MVP Architecture

The current direction is a simple, composable workflow rather than a heavy multi-agent system.

```text
Raw OpenReview / PDF data
  -> Raw snapshot
  -> Normalized paper / review / rebuttal / decision schema
  -> Review point extraction + classification
  -> Local evidence retrieval from manuscript / rebuttal / decision
  -> Evidence-grounded LLM judge
  -> Local reliability checks
  -> JSON / Markdown / HTML report
  -> Annotation tasks for human + LLM calibration
```

Conceptually there are multiple responsibilities, but the MVP should avoid turning every responsibility into a separate API call.

Default execution should stay close to:

```text
per review:
  1 call: extract + classify review points
  1 call target: batch audit all review points
  local: retrieve evidence and verify quotes
```

The current implementation still judges review points one by one; batching the judge per review is a high-priority optimization.

## External Evidence Requirement

External evidence is a required part of the target product, not an optional enhancement.

Both **Review Assessment** and **Rebuttal Guidance** should use external evidence when judging substantive reviewer points. Manuscript-only evidence is not enough for claims about novelty, related work, baseline choice, experimental sufficiency, method validity, or field norms.

Minimum external evidence sources:

- related papers from arXiv, Semantic Scholar, OpenAlex, or equivalent scholarly indexes;
- venue guidelines, scoring rubrics, and review instructions;
- benchmark or baseline conventions when relevant to the claim;
- field-level context needed to judge novelty, significance, or experimental adequacy.

The system should keep internal and external evidence separate in the data model and UI. A reviewer score or final decision can help prioritize issues, but it is not external evidence and should not be treated as ground truth.

Next implementation should focus on a smart, fast, and low-cost external evidence path:

- use metadata-first retrieval before downloading full papers;
- search only for claim types that need field context, such as novelty, related work, baselines, experiments, and method validity;
- cache search results, paper metadata, abstracts, PDFs, and summaries by stable IDs;
- use abstracts and venue guidelines first, then full-paper summaries only for high-priority or ambiguous claims;
- batch related claims from the same paper or review to avoid repeated searches;
- reserve stronger models for high-impact claims or final assessment writing.

## Temporal Evidence Boundary

SecondOpinion should separate review-time assessment from post-review assistance.

For **Review Assessment**, the system should evaluate whether a reviewer point was fair and well grounded at the time the review was written. This stage must not use author responses, final decisions, meta-reviews, or later PDF revisions as evidence for scoring the reviewer. It may use:

- the submitted manuscript;
- submitted appendices and PDF evidence chunks;
- review text, rating, and confidence;
- venue guidelines and external literature that would have been available at review time.

For **Rebuttal Guidance**, the system may use post-review materials, including author responses, reviewer follow-ups, meta-reviews, and revised manuscript text. These materials help decide how authors should respond, but they should not retroactively lower or raise the reviewer's assessment score.

This boundary is important for cases where the author response says a concern has been addressed in a new PDF. That response can support rebuttal strategy, but it should not be treated as manuscript evidence when judging whether the original reviewer critique was reasonable.

## Data Strategy

For research use, data retention should be maximal.

- Save full raw OpenReview snapshots first.
- Derive normalized schema from raw data.
- Store large artifacts in Google Drive or another external storage root, not in GitHub.
- Keep raw data venue-specific; keep normalized data cross-venue.

Different venues will have different raw shapes. That is acceptable as long as:

- raw is preserved without forcing uniformity;
- normalization is explicit and versioned;
- derived artifacts can be regenerated.

## Claim / Review Point Extraction

The extractor should primarily extract negative or actionable review points:

- criticisms
- questions
- suggestions
- score justifications

It should not extract:

- paper summaries
- praise
- neutral descriptions
- generic background

Example input:

```text
The method section is vague and does not explain the graph topology.
What is the rationale for using a GNN on such a simple graph?
The paper would benefit from an ablation comparing against a non-GNN baseline.
```

Expected review points:

```json
[
  {
    "review_point_type": "comment",
    "claim_type": "methodology",
    "claim_text": "The method section is vague and does not explain the graph topology."
  },
  {
    "review_point_type": "question",
    "claim_type": "methodology",
    "claim_text": "What is the rationale for using a GNN on such a simple graph?"
  },
  {
    "review_point_type": "suggestion",
    "claim_type": "experiment",
    "claim_text": "The paper would benefit from an ablation comparing against a non-GNN baseline."
  }
]
```

Known issue: the extractor can still occasionally pull in neutral summary statements. MVP cleanup should tighten extraction to weaknesses and questions by default, and only include strengths or summary text when they contain an explicit limitation or contrast such as "however" or "but".

## Evidence Chunks And Retrieval

PDF chunking is handled by local code, not by the LLM.

Purpose:

- split long papers into retrievable evidence units;
- preserve page and section metadata;
- avoid sending the full paper into every LLM call;
- support traceable manuscript quotes in the report.

Current retrieval is local `section-aware-bm25-v0.2`.

It chooses top manuscript passages using:

- token overlap with the review point;
- source type;
- section-aware weighting;
- claim-type hints.

This is not final proof. It is the best retrieved manuscript context for the judge. Later upgrades can add embedding retrieval, hybrid retrieval, or LLM reranking.

## Unified Stance

For MVP display, all reviewer points should use one primary user-facing attitude scale:

```text
Strongly disagree
Disagree
Mixed
Agree
Strongly agree
```

Meaning:

- **Strongly agree**: SecondOpinion thinks the reviewer point is clearly valid and important.
- **Agree**: mostly valid, with reasonable manuscript support.
- **Mixed**: partly valid, evidence-limited, ambiguous, or too broad.
- **Disagree**: overstated, weakly grounded, or not well supported by the supplied evidence.
- **Strongly disagree**: manuscript evidence clearly answers, weakens, or undermines the reviewer point.

Internal scores such as `support_score`, `answer_coverage_score`, and `question_value_score` can remain in JSON for sorting, debugging, and calibration. The HTML report should lead with stance, not raw percentages.

## Take Writing

The SecondOpinion take should be written in a consistent evidence-first order:

```text
Reviewer argues: "..."
The manuscript states: "..."
SecondOpinion concludes: ...
```

This makes the output more persuasive and easier to audit. The take should not expose developer-facing labels such as prompt version, fallback logic, or "human check" in the main UI.

## Rebuttal Guidance

The MVP should add a second output block under each review point:

```text
Review Assessment
  What SecondOpinion thinks about the reviewer point.

Rebuttal Guidance
  What the author should do next.
```

Suggested schema direction:

```json
{
  "review_assessment": {
    "stance": "mixed",
    "confidence": "medium",
    "assessment_text": "Reviewer argues ... The manuscript states ... SecondOpinion concludes ..."
  },
  "rebuttal_guidance": {
    "priority": "high",
    "strategy": "acknowledge_and_clarify",
    "suggested_response": "Acknowledge the concern, cite Section 2.2, and clarify why the graph construction is appropriate.",
    "evidence_to_cite": ["Section 2.2", "Appendix B.1"],
    "risks_to_avoid": ["Do not simply say the reviewer is wrong."]
  }
}
```

This is likely the strongest MVP demo value: users do not only see whether a review point is valid; they see how to respond.

## Cross-Review Signal

Reviewer agreement is not evidence that a reviewer point is true. Multiple reviewers can share the same misunderstanding.

However, agreement and disagreement across reviewers are valuable process signals.

Use cross-review signal for triage, not proof:

- high overlap + high severity -> escalate as a high-priority issue;
- high disagreement -> mark as contested and lower confidence;
- AC / meta-review alignment -> raise decision relevance;
- paper already answers + many reviewers still ask -> likely communication gap;
- single vague reviewer point -> keep lightweight unless it affects the decision.

In early MVP, `high overlap` and `high disagreement` can share the same handling:

```text
high-value or high-risk issue
  -> stronger model or deeper prompt
  -> more cautious conclusion
  -> stronger rebuttal guidance
```

## Model Strategy

Default strategy is cheap-first.

- Use the cheapest capable model to run the full workflow.
- Upgrade only the bottleneck step when quality issues are observed.
- Use stronger models for important demo runs, high-risk issues, or final take writing.

Current default:

```text
claim extraction: gpt-5-nano
review point judge: gpt-5-nano
annotation labeler: gpt-5-nano
reasoning effort: minimal
```

These defaults can be overridden with environment variables or CLI flags.

## Reliability And Calibration

The MVP should not rely on one LLM output as truth.

Minimal reliability checks:

- quoted manuscript evidence should come from retrieved evidence;
- neutral or praise-only review points should be filtered;
- evidence-limited conclusions should not be high confidence;
- report copy should be user-facing, not developer-facing;
- stance should be consistent with the take.

Calibration plan:

- every audit run can export annotation tasks;
- human labels and LLM labels are generated independently;
- comparison reports become a calibration dataset;
- high-confidence model decisions should be checked against human labels over time.
- next expert annotation should stay small and low burden: select a few dozen papers, show claim-level reviewer points, ask experts for a simple 1-5 agreement score, and measure correlation with SecondOpinion stance.
- primary early metrics should be AI-expert correlation, human-human correlation when two labels are available, and rebuttal usefulness score.

## External References

External references are required for the target product, especially for:

- novelty;
- field consensus;
- venue-specific expectations;
- experimental sufficiency relative to similar papers.

Until external references are added, novelty and deep field claims should use cautious language and confidence downgrades.

## MVP Demo Priorities

The fastest path to a credible demo is:

1. **Low-cost external evidence**
   Add metadata-first related paper and venue-guideline retrieval for substantive reviewer points.

2. **Small expert annotation run**
   Select a few dozen papers and ask experts for simple 1-5 agreement scores on reviewer points. Use correlation as the first quantitative signal.

3. **Report redesign**
   User-facing structure: paper summary, review landscape, key issues, per-review assessment, rebuttal guidance, evidence appendix.

4. **Rebuttal guidance**
   Add priority, strategy, suggested response, evidence to cite, and risks to avoid.

5. **Claim extractor cleanup**
   Avoid neutral summaries and praise. Extract only auditable negative/actionable points.

6. **Batch judge per review**
   Reduce runtime and API calls.

7. **Minimal reliability gate**
   Verify quotes and prevent overconfident conclusions.

8. **Three-paper demo packet**
   Use real ICLR 2024 samples across different topics. Show real reviews, PDFs, evidence, stance, and rebuttal guidance.

## References We Discussed

- Anthropic: Building effective agents
- ICLR 2025 Review Feedback Agent
- RAGAS / RAG evaluation ideas
- Self-RAG
- DSPy

The main lesson from these references is not to build a complicated agent system first. The better starting point is a simple workflow with narrow LLM tasks, structured outputs, evidence grounding, verification, and evaluation.
