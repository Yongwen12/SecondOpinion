# SecondOpinion Progress Checkpoint - 2026-06-03

Archived on: 2026-06-11

Work window covered: 2026-06-01 to 2026-06-03

## Executive Summary

This checkpoint captures the large early-June push that moved SecondOpinion from a broad reviewer-quality audit prototype toward a sharper author-facing reviewer-claim lifecycle triage system.

The important strategic change is that the project now separates two constructs:

- Construct A: claim epistemic quality. This asks whether a reviewer criticism is objectively well-founded, material, fair, and useful. It requires expert gold labels.
- Construct B: claim lifecycle influence. This asks whether a reviewer concern survives the review lifecycle: appears in the original review, is supported by other reviewers, is not resolved by rebuttal, persists after rebuttal, and is reflected in meta-review. This can be measured from OpenReview lifecycle data.

The near-term product direction is now Construct B: help authors identify which reviewer claims are evidence-grounded, unresolved, addressable, and likely to matter during rebuttal. Construct A remains the longer-term review-quality audit goal, but it should wait for expert IAA validation before being used as the main external claim.

## Product Direction

The recommended near-term positioning is:

> SecondOpinion helps authors triage reviewer claims by estimating which concerns are evidence-grounded, unresolved, addressable, and likely to matter in the review lifecycle.

The project should avoid overclaiming:

> We can objectively score reviewer quality.

That stronger claim depends on expert agreement for normative claim quality. The current data supports lifecycle triage more cleanly than objective reviewer-quality scoring.

## New Strategy And Annotation Artifacts

Two major planning documents were added:

- `docs/验证策略与并行工作计划.md`
- `docs/标注手册.md`

The validation strategy document defines the A/B construct split, recommends author-facing lifecycle triage as the short-term target, and lays out a practical validation roadmap.

The annotation codebook defines an IAA pilot for expert labels on:

- grounding accuracy
- materiality
- holistic claim quality
- rebuttal resolution
- recommended author action
- annotator confidence

The pilot design hides meta-review, final decision, other-reviewer support, and system scores from annotators to avoid leakage. The proposed calibration round is 2-3 papers, followed by a scored pilot of 15-20 papers with 3 expert annotators and full overlap.

## Validation Results

### Lifecycle Proxy Ablation

Report: `reports/validation/lifecycle_proxy_ablation_v0.1.md`

Scope:

- Claims: 854
- Claims with LLM rebuttal labels: 240
- Claims with LLM consensus labels: 120
- Claims with any LLM label: 323
- Claims with both LLM labels: 37

Key result: lexical proxy risk is real and measurable.

Rebuttal resolution diagnostics:

- Proxy says addressed/resolved: 78.8%
- LLM says specifically addressed/resolved: 27.1%
- LLM says resolved/weakened: 3.3%
- Lexical false-positive candidates among proxy-addressed claims: 128, or 67.7%

Consensus diagnostics:

- Proxy says partial/strong: 80.0%
- LLM says related/same: 64.2%
- LLM says same concern: 6.7%
- Lexical false-positive candidates among proxy-positive claims: 27, or 28.1%

Interpretation: the original lifecycle logic was directionally useful but too dependent on lexical overlap. LLM-calibrated legs are necessary for any external-facing claim.

### Semantic Meta-Review Recalibration

Report: `reports/validation/semantic_meta_lifecycle_v0.1.md`

Scope:

- Claims: 854
- Claims with semantic meta-review records: 500
- Claims with decisive semantic meta-review labels: 421
- High-confidence decisive semantic labels: 155
- Semantic/proxy exact agreement: 74.6%

Semantic label counts:

- not_found: 134
- partial: 280
- survived: 7
- unsure: 79

Interpretation: semantic meta-review labels moderately agree with the proxy, but they also expose proxy false positives and false negatives. This makes meta-review uptake a useful lifecycle leg, but it should be presented as a calibrated signal rather than ground truth.

### Consensus Recalibration

Report: `reports/validation/consensus_recalibration_v0.1.md`

Scope:

- Claims: 854
- Claims with LLM consensus labels: 120

Key result:

- Current related/same support rate: 64.2%
- Strict same-concern support rate: 6.7%
- Related-but-different demotions: 69, or 57.5%

Interpretation: many reviewer comments are thematically related without being the same concern. Treating all related concerns as consensus support inflates robustness. The product should distinguish same-concern support from related-context support.

### Presentation P0 Checks

Report: `reports/validation/presentation_p0_checks_v0.1.md`

Scope:

- Papers: 80
- Reviews: 205
- Claims: 854
- LLM-labeled rebuttal claims: 240

Key result:

- High-importance and unresolved/partial-effect claims: 155, or 64.6% of LLM-labeled rebuttal claims.
- Specifically addressed but still unresolved/partial effect: 57, or 23.8%.
- Grounding validation raw pass rate: 89.7%.
- Grounding validation final pass rate: 100.0%.

Interpretation: a large share of important reviewer concerns are not substantively resolved by rebuttal, even when the response looks topically related. This supports the author-facing triage story.

### Addressability Classification

Reports:

- `reports/validation/addressability_test4_report_v0.1.md`
- `reports/validation/addressability_test4_gpt5_report_v0.2.md`

GPT-5 v0.2 result:

- Classified unique claims: 240
- Main unresolved/generic candidate claims: 232
- Resolved/effect control claims: 8
- Specifically addressed control claims: 63

Main distribution:

- answerable_fixable: 224
- structurally_unresolvable: 6
- unclear: 2
- overall fixable rate: 96.6%
- determinate fixable rate excluding unclear: 97.4%

Headline cell:

- High-importance unresolved/partial claims: 155
- Fixable high-importance unresolved/partial claims: 151
- Fixable rate in this cell: 97.4%

Self-consistency:

- Exact agreement with main labels: 87.8%
- Fixable agreement with main labels: 93.3%

Interpretation: most high-priority unresolved reviewer concerns appear addressable by rebuttal or revision. This is one of the strongest current product signals because it converts risk detection into author action.

## External Dataset Map

Document: `docs/secondopinion_dataset_map_v0.1.md`

The dataset map verifies public peer-review datasets and organizes them by which part of the SecondOpinion system they can validate:

- rebuttal alignment and response structure
- substantive resolution
- comment priority and actionability
- evidence and substantiation
- tone and confidence
- cross-reviewer agreement and contradiction
- revision or outcome targets
- argument structure and claim extraction

Important conclusion: no public dataset replaces the core expert label for substantive resolution plus materiality. External datasets can benchmark components, bootstrap mappings, and reduce risk, but the core gold label still requires the IAA pilot.

## Engineering Work

New or expanded modules include:

- `src/secondopinion/lifecycle_ablation.py`
- `src/secondopinion/semantic_lifecycle.py`
- `src/secondopinion/consensus_recalibration.py`
- `src/secondopinion/external_dataset_adapters.py`
- `src/secondopinion/component_benchmark.py`
- `src/secondopinion/presentation_checks.py`
- `src/secondopinion/addressability_tasks.py`
- `src/secondopinion/addressability_classification.py`
- `src/secondopinion/counterfactual_rebuttal.py`
- `src/secondopinion/evidence_chain.py`

Expanded existing modules include:

- `src/secondopinion/annotation.py`
- `src/secondopinion/cli.py`
- `src/secondopinion/llm_client.py`
- `src/secondopinion/rag_validation.py`

New or expanded tests include:

- `tests/test_lifecycle_ablation.py`
- `tests/test_semantic_lifecycle.py`
- `tests/test_consensus_recalibration.py`
- `tests/test_external_dataset_adapters.py`
- `tests/test_component_benchmark.py`
- `tests/test_presentation_checks.py`
- `tests/test_addressability_tasks.py`
- `tests/test_addressability_classification.py`
- `tests/test_counterfactual_rebuttal.py`
- `tests/test_evidence_chain.py`
- expanded annotation and RAG validation tests

Current verification:

- `python -m pytest`
- Result: 124 passed

## Current System Interpretation

The strongest validated story is not yet "objective reviewer scoring." The stronger and safer story is:

1. Split reviews into concrete reviewer claims.
2. Ground each claim back to the original review.
3. Attach manuscript, rebuttal, consensus, and meta-review evidence.
4. Detect when a claim is important but unresolved.
5. Classify whether the concern is answerable or structurally hard to fix.
6. Help the author prioritize rebuttal and revision effort.

This gives SecondOpinion a practical author-facing workflow while preserving a path toward deeper reviewer-quality auditing after expert validation.

## Risks And Caveats

1. Lexical proxies can overstate rebuttal resolution and inter-reviewer consensus.
2. Current materiality is still a system/LLM proxy, not expert gold.
3. Meta-review uptake is useful but should not be treated as equivalent to claim correctness.
4. Public OpenReview data supports reproducible validation, but private in-review use will need a strict privacy and data-retention design.
5. Large validation artifacts are useful for reproducibility but should remain curated so the repository does not become hard to clone.

## Recommended Next Steps

1. Treat Construct B, author-facing lifecycle triage, as the demo and investor-facing target.
2. Run the IAA calibration round with 2-3 papers and 3 annotators.
3. Use the calibration round to refine the annotation codebook to v0.2.
4. Replace or downweight lexical consensus with ContraSciView or another stronger agreement/contradiction benchmark.
5. Build a clean demo around one paper that shows:
   - reviewer claim
   - evidence chain
   - rebuttal resolution
   - lifecycle influence
   - addressability
   - recommended author action
6. Keep objective reviewer-quality scoring as a future claim until expert agreement is demonstrated.

