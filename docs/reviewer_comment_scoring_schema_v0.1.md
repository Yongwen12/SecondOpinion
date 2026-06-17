# SecondOpinion Reviewer Comment Scoring Schema v0.1

Date: 2026-06-17

This document defines the current six-dimension reviewer comment scoring schema. It is the product-level scoring engine behind the demo.

Core principle:

> Score reviewer comments first. Triage, rebuttal planning, AC views, and reviewer audit views are downstream workflows built on top of the scores.

## Summary

| Dimension | What It Scores | Current Implementation | Literature / Dataset Sources | Adapter Status | Confidence |
|---|---|---|---|---|---|
| Specificity | Whether the reviewer states a concrete, inspectable claim | Implemented from claim extraction and reviewer calibration specificity signals | ReAct, AMPERE, ASAP-Review / ReviewAdvisor | Not yet fully adapted | Medium |
| Substantiation | Whether the comment gives reasons, evidence, or manuscript anchors | Partly implemented through evidence support, grounding, and evidence-chain scores | SubstanReview, ReviewCritique | Not yet adapted | Medium-low |
| Actionability | Whether the author can understand what response or revision is expected | Implemented in demo from guidance priority and rebuttal guidance; addressability classifier exists | ReAct, BetterPR, RbtAct, ARIES | Partly implemented internally; external adapters pending | Medium |
| Consensus / conflict | Whether other reviewers support, overlap with, or contradict the concern | Implemented as proxy + LLM calibration; lexical proxy risk documented | ContraSciView, RevCI | ContraSciView benchmark adapter exists; scoring integration pending | Medium |
| Rebuttal robustness | Whether the concern still stands after author response | Implemented through rebuttal resolution labels and lifecycle robustness | DISAPERE, APE, RbtAct, Re2, DEFEND | Internal LLM calibration implemented; external adapters pending | Medium |
| Professionalism | Whether the comment is constructive, calibrated, and professional in tone | Basic legacy tone/professionalism fields; mostly display-level today | PolitePEER, HedgePeer, BetterPR | Pending | Low-medium |

## Dimension Definitions

### 1. Specificity

Question:

> Does the reviewer state a concrete, inspectable claim?

High score:

- Names a specific method, experiment, result, formula, baseline, section, claim, or missing analysis.
- Can be checked against paper text or evidence.
- Is separable from generic praise or generic dissatisfaction.

Low score:

- Vague criticism such as "not convincing", "weak novelty", or "needs more experiments" without saying what is missing.
- Pure summary or preference with no concrete target.

Current implementation:

- Claim extraction keeps source field and source sentence.
- Reviewer calibration computes `specificity_score`.
- The current demo displays this as `Specificity`.

Research sources:

- ReAct: review-comment actionability.
- AMPERE: argumentative proposition extraction and typing.
- ASAP-Review / ReviewAdvisor: review aspect and sentiment annotations.

Adapter status:

- No full external-data adapter is wired into the production score yet.
- Existing implementation is usable as a product score, but should be benchmarked against ReAct / AMPERE-style labels.

### 2. Substantiation

Question:

> Does the comment give reasons, evidence, or manuscript anchors?

High score:

- Reviewer explains why the concern matters.
- Reviewer points to a result, method detail, comparison, theorem, experiment, or missing evidence.
- The claim has manuscript/evidence-chain support.

Low score:

- Reviewer asserts a conclusion without supporting reasoning.
- The comment is a bare verdict without explanation.

Current implementation:

- Evidence-chain demo uses `evidence_support` and `grounding` scores.
- Audit and RAG validation provide manuscript and external-evidence support signals.
- This is not yet the same as SubstanReview-style substantiation, because current evidence support partly measures whether SecondOpinion found evidence, not whether the reviewer supplied evidence.

Research sources:

- SubstanReview: reviewer claim-evidence pairs and substantiation.
- ReviewCritique: review-segment deficiency and explanation labels.

Adapter status:

- Pending.
- This should be one of the first external benchmark mappings because it directly supports comment quality scoring.

### 3. Actionability

Question:

> Can the author understand what response or revision is expected?

High score:

- The reviewer request implies a clear action: add baseline, clarify definition, report standard deviation, move analysis, cite related work, run ablation, acknowledge limitation.
- The comment can be routed into a rebuttal or revision plan.

Low score:

- The comment is too vague to answer.
- The concern is a broad taste judgment without an actionable path.

Current implementation:

- Demo derives actionability from `guidancePriority`, rebuttal guidance, and addressability outputs.
- `addressability_classification.py` classifies reviewer claims as:
  - `answerable_fixable`
  - `requires_concession`
  - `structurally_unresolvable`
  - `unclear`

Research sources:

- ReAct: actionability classification.
- BetterPR: constructive vs non-constructive comments.
- RbtAct: rebuttal/revision action supervision.
- ARIES: review comments linked to paper edits.

Adapter status:

- Internal addressability is implemented.
- External adapters are pending.
- ReAct and RbtAct are the most useful first mappings.

### 4. Consensus / Conflict

Question:

> Do other reviewers support, overlap with, or contradict this concern?

High score:

- Another reviewer raises the same concern.
- Multiple reviewers independently identify the same technical issue.

Medium score:

- Other reviewers discuss a related area but not exactly the same concern.

Low score:

- No other reviewer supports the claim.
- Other reviewers contradict it or provide evidence in the opposite direction.

Current implementation:

- Reviewer calibration has lexical overlap proxy.
- LLM consensus calibration distinguishes:
  - `same_concern`
  - `related_but_different`
  - `not_same_concern`
  - `unsure`
- `consensus_recalibration_v0.1` found that same-concern support is much lower than broad related-or-same support.

Research sources:

- ContraSciView: agreement and contradiction between peer reviews.
- RevCI: graded contradiction intensity and evidence pairs.

Adapter status:

- ContraSciView-derived benchmark artifacts exist in `data/validation`.
- Full replacement of lexical consensus scoring is pending.
- This is a high-priority adapter because it directly fixes a known proxy weakness.

### 5. Rebuttal Robustness

Question:

> Does the concern still stand after the author response?

High score:

- The author response does not address the concern.
- The response is generic, partial, or unclear.
- The concern remains important after rebuttal.

Low score:

- The author specifically addresses the concern.
- The response resolves or materially weakens the reviewer claim.

Current implementation:

- Rebuttal resolution labels include:
  - `not_addressed`
  - `generic_or_unclear`
  - `specifically_addressed`
  - `likely_resolved`
- Rebuttal effect labels include:
  - `does_not_address`
  - `partially_addresses`
  - `resolved_or_weakened`
  - `unclear`
- Lifecycle robustness uses rebuttal robustness as one scoring leg.

Research sources:

- DISAPERE: review-rebuttal discourse structure and stance.
- APE: argument pair extraction between reviews and rebuttals.
- RbtAct: rebuttal as supervision for actions/revisions.
- Re2: large full-stage review and rebuttal data.
- DEFEND: rebuttal-action labels and segment mapping.

Adapter status:

- Internal LLM calibration is implemented.
- External mapping is pending.
- RbtAct / DISAPERE / APE are the most practical first adapters.

### 6. Professionalism

Question:

> Is the comment constructive, calibrated, and professional in tone?

High score:

- Clear, respectful, and specific.
- Critical without being dismissive.
- Helps the author understand the reviewer's concern.

Low score:

- Personal, sarcastic, hostile, or dismissive.
- Overconfident without evidence.
- Uses tone that obscures the technical issue.

Current implementation:

- Legacy review-level dimensions include professional tone / professionalism.
- Current scorecard displays professionalism, but it is the least externally calibrated dimension.

Research sources:

- PolitePEER: politeness intensity.
- HedgePeer: hedging and uncertainty cues.
- BetterPR: constructive vs non-constructive peer-review comments.

Adapter status:

- Pending.
- Keep as auxiliary for now. It should not dominate the overall score.

## Current Overall Score Policy

The current product score should be described as:

> A reviewer comment usefulness score derived from specificity, substantiation, actionability, consensus/conflict, rebuttal robustness, and professionalism.

Avoid describing it as:

> An objective truth score for reviewer correctness.

Avoid overclaiming:

- The score does not prove the reviewer is right.
- The score does not predict acceptance.
- The score does not replace expert judgment.
- The score ranks the usefulness and robustness of reviewer comments for audit and response workflows.

## Recommended Weighting For Demo v0.1

For a claim-level score:

```text
20% Specificity
20% Substantiation
20% Actionability
15% Consensus / conflict
20% Rebuttal robustness
 5% Professionalism
```

Rationale:

- Professionalism matters, but the project should not become a tone classifier.
- Consensus is useful, but should not overpower a high-quality isolated concern.
- Rebuttal robustness is central because it tells whether a claim survives author response.

For review-level scoring:

```text
Review comment score =
  mean claim-level score
  + high-value claim ratio
  - vague unsupported claim ratio
  - major claims weakened by rebuttal
  + small professionalism adjustment
```

## Adapter Priority

### P0

1. ContraSciView / RevCI for consensus and conflict.
2. ReAct for actionability.
3. SubstanReview for substantiation.

### P1

4. DISAPERE / APE / RbtAct for rebuttal response mapping.
5. ReviewCritique for broad deficiency / quality labels.
6. ARIES for revision-linked actionability.

### P2

7. PolitePEER / HedgePeer for tone and confidence.
8. ASAP-Review / AMPERE for aspect and proposition typing benchmarks.

## Demo Mapping

The current public demo exposes these dimensions as:

- `Scorecard`: review-level scoring and literature-backed dimension cards.
- `Claim Scores`: claim-level six-dimension score rows.
- `Triage`: downstream prioritization and rebuttal planning after scoring.

The demo should keep this order. Scoring is the engine; triage is the application.

## Implementation Addendum: Short-Term Target 2+3

Date: 2026-06-17

Short-term target 2+3 is now implemented as an external-memory scoring path:

- External datasets are normalized into a shared JSONL schema:
  - `task_id`
  - `dataset`
  - `dimension`
  - `input_text`
  - `context_text`
  - `gold_label`
  - `mapped_score`
  - `metadata`
- `build-scoring-memory --dimension auto` converts the normalized records into scoring-memory examples grouped by each record's `dimension`.
- `score-dimensions-with-memory` returns six-dimensional `hybrid_scores` with:
  - `llm_score`
  - `memory_prior`
  - `final_score`
  - `source`
  - `retrieved_examples`
- `run-scoring-memory-suite` creates the benchmark report and optional guardrail report.

Current smoke coverage:

| Dimension | External memory source in smoke path | Status |
|---|---|---|
| Specificity | ReAct-style specificity fixture | Wired |
| Substantiation | SubstanReview fixture | Wired |
| Actionability | ReAct fixture | Wired |
| Consensus / conflict | ContraSciView adapter exists; not in combined smoke memory yet | Adapter available |
| Rebuttal robustness | DISAPERE + RbtAct fixtures | Wired |
| Professionalism | No P0 memory yet; remains LLM-only in the demo | Deferred |

The demo at `frontend/demos/hybrid_scoring_demo.json` uses backend-shaped `hybrid_scores` and shows final, LLM, memory-prior, and retrieved-example evidence. This is still a smoke integration, not a full external dataset import. Full raw datasets should remain under `data/external/` and out of Git.
