# SecondOpinion Non-IAA Fast Track Plan

IAA pilot is temporarily paused. The goal is to keep moving on work that does not require expert annotators, while protecting the product direction: author-facing rebuttal triage and pressure testing, not journal audit and not acceptance prediction.

## Product Core To Preserve

SecondOpinion should help authors answer two immediate rebuttal-stage questions:

1. Which reviewer concerns deserve scarce rebuttal effort?
2. Does the rebuttal substantively address each concern, or only respond at the surface level?

External datasets and proxy analyses can support components, but they do not replace the core labels: substantive resolution and core materiality.

## Immediate Workstreams

### 1. Consensus De-Proxy

Status: completed for the current ICLR sample.

Output:

- `reports/validation/consensus_recalibration_v0.1.md`
- `data/validation/consensus_recalibration_v0.1.json`

Current finding:

- LLM-labeled consensus claims: 120
- Proxy says partial/strong: 80.0%
- Strict same-concern support: 6.7%
- Related-but-different demotions: 69 / 120
- On the labeled subset, strict consensus lowers lifecycle by 5.7pp and changes 20.8% of labels.

Interpretation:

Consensus should not be presented as broad topical agreement. For author-facing triage, it should mean a stricter thing: another reviewer raised substantially the same concern. Related-but-different is useful context, not independent support.

Next step:

Use ContraSciView / RevCI as the external benchmark target for consensus once the data is downloaded. These are the cleanest external resources because they are ICLR/NeurIPS-native and directly address reviewer agreement/contradiction.

ContraSciView status: first external benchmark completed.

Outputs:

- `data/validation/contrasciview_majority_baseline_v0.1.jsonl`
- `data/validation/contrasciview_polarity_baseline_v0.1.jsonl`
- `data/validation/contrasciview_polarity_overlap_0p10_v0.1.jsonl`
- `reports/validation/contrasciview_majority_benchmark_v0.1.md`
- `reports/validation/contrasciview_polarity_benchmark_v0.1.md`
- `reports/validation/contrasciview_polarity_overlap_0p10_benchmark_v0.1.md`

ContraSciView baseline findings:

- Records: 47,975 review-comment pairs.
- Gold contradiction rate: 11.9% (`contradiction`: 5,725; `not_contradiction`: 42,250).
- Majority baseline: accuracy 88.1%, balanced accuracy 50.0%, macro-F1 46.8%.
- Polarity-only baseline: accuracy 11.9%, balanced accuracy 50.0%, macro-F1 10.7%.
- Polarity + token-overlap baseline at 0.10 Jaccard: accuracy 85.9%, balanced accuracy 52.3%, macro-F1 52.2%; contradiction recall only 8.1%.

Interpretation:

Opposite review sentiment is not enough to infer contradiction, and lexical overlap adds only a weak signal. This externally supports the internal finding that cross-reviewer consensus/contradiction needs semantic modeling; it should not be approximated by topical overlap or polarity.

### 2. Rebuttal Alignment And Response Type Benchmark

Goal:

Build an external benchmark harness for comment-to-rebuttal matching and response action classification.

Status: benchmark runner implemented.

Output:

- `src/secondopinion/component_benchmark.py`
- `tests/test_component_benchmark.py`

Command pattern:

```powershell
python -m secondopinion.component_benchmark --input data/validation/<normalized_external_component>.jsonl --task-type classification --out data/validation/<name>.json --markdown reports/validation/<name>.md
python -m secondopinion.component_benchmark --input data/validation/<normalized_external_alignment>.jsonl --task-type alignment --out data/validation/<name>.json --markdown reports/validation/<name>.md
```

Datasets:

- APE: review argument to rebuttal response pairing.
- DISAPERE: review/rebuttal discourse actions and stance.
- RbtAct: concrete revision/plan vs defense-style responses.
- DEFEND: rebuttal-action labels and gold rebuttal-segment mapping.
- Re2: large full-stage review/rebuttal base with before/after scores.

What this can validate:

- Did the system find the right rebuttal span for a reviewer concern?
- Did the system classify the response type correctly?
- Did the system distinguish concrete revision/plan from generic defense?

What this cannot validate:

- Whether the rebuttal substantively resolves the concern. That remains an IAA label.

### 3. Adjacent Priority Signal Benchmark

Goal:

Benchmark components that contribute to comment priority without pretending they are core materiality.

Status: benchmark runner implemented; dataset adapters still pending.

Datasets:

- ReAct: actionability.
- BetterPR: constructiveness.
- SubstanReview: substantiation / evidence attached to review claims.
- ReviewCritique: deficiencies and explanations.

What this can validate:

- Whether a comment is actionable.
- Whether it is specific and reasoned rather than vague.
- Whether it contains a concrete deficiency.
- Whether it is useful/constructive.

What this cannot validate:

- Whether the concern hits the paper's core contribution or decision-critical claim. That is core materiality and still needs the paused IAA pilot.

### 4. Author-Facing Demo Reframe

Goal:

Make the demo reflect the author product, not the old journal-audit lifecycle framing.

Primary UI cards should be:

- Reviewer concern.
- Priority-adjacent signals: actionability, specificity, substantiation, reviewer conviction.
- Cross-reviewer status: same concern / related context / contradiction.
- Rebuttal coverage: matched span, missing span, generic response, concrete response.
- Resolution risk note: unresolved / partially addressed / likely addressed, clearly marked as model judgment until IAA validates it.

Avoid:

- Composite lifecycle score as the main product output.
- RAG as a prediction claim.
- Meta-review uptake as a primary signal.
- Reviewer reputation scoring across papers, unless real reviewer identity is available.

### 5. Prediction Track, Only If Revived Later

Current state:

Meta-review uptake and RAG prediction should stay out of the main pitch.

If prediction is revived:

- Use reviewer score change after rebuttal as the target.
- Candidate data: Re2 and "Does my rebuttal matter?"
- Requirement: beat majority/random baselines before mentioning this in a pitch.

## Suggested Execution Order

1. Finish consensus de-proxy report. Done.
2. Add a generic component-benchmark runner: precision/recall/F1 for alignment, response type, actionability, and substantiation. Done.
3. Add benchmark adapters for APE / DISAPERE / RbtAct style data schemas.
4. Download one clean external dataset at a time and run smoke evaluations.
5. Reframe the demo around author rebuttal triage and coverage checks.
6. Keep IAA pilot paused until the non-IAA components are ready, but do not claim core materiality/resolution is externally validated.
