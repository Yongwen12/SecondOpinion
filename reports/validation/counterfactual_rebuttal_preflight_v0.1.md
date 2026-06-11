# Counterfactual Rebuttal Experiment Preflight

## Preregistered Hypotheses

- **H1**: Engage beats Avoid: a direct, substantive rebuttal should be preferred over evasive non-response.
- **H2**: Engage beats Polished-avoid: substance should beat polite length when length and tone are controlled.
- **H3**: The Engage advantage should be larger for answerable/fixable concerns and smaller for structural novelty/significance/framing concerns.

## Data Readiness

- Main Test-4 concerns joined: 232 / 232
- Addressability distribution: `{"answerable_fixable": 224, "structurally_unresolvable": 6, "unclear": 2}`
- Importance distribution: `{"major": 178, "medium": 9, "minor": 34, "question": 11}`
- Headline high-importance unresolved cell: `{"addressability_distribution": {"answerable_fixable": 151, "structurally_unresolvable": 4}, "claim_count": 155, "fixable_count": 151, "fixable_rate": 0.9742}`

## Pre/Post Reviewer Score Availability

- Post-rebuttal official review updates: 48
- Updated official reviews with current rating field: 48
- Post-rebuttal reviewer/AC comments: 93
- Rating-ish post-rebuttal comments: 66
- Strict score-change comments: 25
- Strict score-change text inside updated reviews: 2

**Interpretation:** Clean paired pre/post numeric reviewer ratings are not reliably available in this snapshot. Use score movement only as an optional observational appendix; it should not gate the counterfactual experiment.

## Call Budget

- Pilot primary pairs: `{"claim_count": 30, "generation_calls": 90, "judge_calls": 360, "total_calls": 450}`
- Pilot full pairs: `{"claim_count": 30, "generation_calls": 90, "judge_calls": 540, "total_calls": 630}`
- Full primary pairs: `{"claim_count": 232, "generation_calls": 696, "judge_calls": 2784, "total_calls": 3480}`
- Full all pairs: `{"claim_count": 232, "generation_calls": 696, "judge_calls": 4176, "total_calls": 4872}`

## Pilot Sample

- Requested / actual: 30 / 30
- Addressability: `{"answerable_fixable": 22, "structurally_unresolvable": 6, "unclear": 2}`
- Importance: `{"major": 13, "medium": 7, "minor": 8, "question": 2}`

## Guardrails

- `paired_counterfactual`: Hold paper and reviewer concern fixed; only vary rebuttal style.
- `scope`: This measures an LLM-AC judge response, not real reviewer behavior.
- `generator_judge_separation`: Use different model families or at least different prompts for generation and judging.
- `length_control`: Engage and Polished-avoid should be comparable in length.
- `no_fabricated_results`: Generated rebuttals must not invent experiments, numbers, or claims absent from paper context.
- `blind_pairwise_judging`: Judge pairwise with order swaps and repeated runs; count only stable wins.
- `stratification`: Report by addressability x importance_proxy.
