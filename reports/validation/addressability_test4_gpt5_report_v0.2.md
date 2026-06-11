# Addressability Classification Test 4

## Run Summary

- Classified unique claims: 240
- Main unresolved/generic candidate claims: 232
- Resolved/effect control claims: 8
- Specifically-addressed control claims: 63
- Paper context counts: `{"abstract": 240}`
- No-leakage check: `{"prompt_context": "title + abstract when available; title-only fallback flagged per item", "prompt_includes_existing_response_or_effect_labels": false, "prompt_includes_importance_proxy": false, "prompt_includes_rebuttal_text": false}`

## Main Distribution

- Addressability: `{"answerable_fixable": 224, "requires_concession": 0, "structurally_unresolvable": 6, "unclear": 2}`
- Fixable split: `{"fixable": 224, "fixable_rate": 0.9655, "not_fixable": 8, "not_fixable_rate": 0.0345}`
- Tri-state split: `{"fixable": 224, "fixable_rate": 0.9655, "not_fixable": 6, "not_fixable_rate": 0.0259, "unclear": 2, "unclear_rate": 0.0086}`
- Determinate split excluding unclear: `{"determinate_count": 230, "fixable": 224, "fixable_rate": 0.9739, "not_fixable": 6, "not_fixable_rate": 0.0261}`
- Not-fixable subtypes: `{"novelty_significance_framing_verdict": 6, "other_requires_concession": 0, "true_not_fixable_total": 6}`

## Headline Cell: High-Importance Proxy + Unresolved/Partial

- Claims: 155
- Addressability: `{"answerable_fixable": 151, "requires_concession": 0, "structurally_unresolvable": 4, "unclear": 0}`
- Fixable split: `{"fixable": 151, "fixable_rate": 0.9742, "not_fixable": 4, "not_fixable_rate": 0.0258}`
- Tri-state split: `{"fixable": 151, "fixable_rate": 0.9742, "not_fixable": 4, "not_fixable_rate": 0.0258, "unclear": 0, "unclear_rate": 0.0}`
- Determinate split excluding unclear: `{"determinate_count": 155, "fixable": 151, "fixable_rate": 0.9742, "not_fixable": 4, "not_fixable_rate": 0.0258}`
- Not-fixable subtypes: `{"novelty_significance_framing_verdict": 4, "other_requires_concession": 0, "true_not_fixable_total": 4}`

## Cross-Tabs

- Addressability x importance proxy: `{"answerable_fixable": {"major": 173, "medium": 9, "minor": 32, "question": 10}, "structurally_unresolvable": {"major": 5, "minor": 1}, "unclear": {"minor": 1, "question": 1}}`
- Addressability x current effect: `{"answerable_fixable": {"does_not_address": 123, "partially_addresses": 72, "unclear": 29}, "structurally_unresolvable": {"does_not_address": 4, "partially_addresses": 1, "unclear": 1}, "unclear": {"does_not_address": 1, "unclear": 1}}`
- Addressability x current response: `{"answerable_fixable": {"generic_or_unclear": 67, "not_addressed": 101, "specifically_addressed": 56}, "structurally_unresolvable": {"generic_or_unclear": 2, "not_addressed": 3, "specifically_addressed": 1}, "unclear": {"generic_or_unclear": 1, "not_addressed": 1}}`

## Controls

- Resolved/effect control: `{"claim_count": 8, "distribution": {"answerable_fixable": 8, "requires_concession": 0, "structurally_unresolvable": 0, "unclear": 0}, "fixable_split": {"fixable": 8, "fixable_rate": 1.0, "not_fixable": 0, "not_fixable_rate": 0.0}}`
- Specifically-addressed control: `{"claim_count": 63, "distribution": {"answerable_fixable": 62, "requires_concession": 0, "structurally_unresolvable": 1, "unclear": 0}, "fixable_split": {"fixable": 62, "fixable_rate": 0.9841, "not_fixable": 1, "not_fixable_rate": 0.0159}}`

## Self-Consistency

`{"agreement_with_main_exact_count": 79, "agreement_with_main_exact_rate": 0.8778, "agreement_with_main_fixable_count": 84, "agreement_with_main_fixable_rate": 0.9333, "claim_count": 30, "label_count": 90, "note": "Self-consistency used a reworded prompt variant because the default GPT-5 model path does not expose temperature controls in this client.", "status": "run", "unanimous_exact_claim_count": 26, "unanimous_exact_claim_rate": 0.8667, "unanimous_fixable_claim_count": 27, "unanimous_fixable_claim_rate": 0.9}`

## Model Robustness vs Baseline

`{"baseline_fixable_rate_all": 0.5647, "baseline_fixable_rate_excluding_unclear": 0.736, "baseline_tri_state_counts": {"fixable": 131, "not_fixable": 47, "unclear": 54}, "binary_agreement_count": 135, "binary_agreement_rate": 0.7627, "binary_determinate_pair_count": 177, "current_fixable_rate_all": 0.9655, "current_fixable_rate_excluding_unclear": 0.9739, "current_tri_state_counts": {"fixable": 224, "not_fixable": 6, "unclear": 2}, "fixable_rate_delta_all": 0.4008, "fixable_rate_delta_excluding_unclear": 0.2379, "paired_count": 232, "status": "run", "tri_state_agreement_count": 136, "tri_state_agreement_rate": 0.5862}`

## Rationale / Label Consistency Check

`{"checked_count": 232, "examples": [{"addressability": "unclear", "claim_id": "kmn0BhQk7p:aPvo3w4FSN:3", "current_rebuttal_effect_label": "does_not_address", "fixable": false, "importance_proxy": "question", "rationale": "The request to respond to unspecified weaknesses is too vague to assess and lacks concrete, identifiable issues that could be addressed in a rebuttal."}], "mismatch_count": 1, "mismatch_rate": 0.0043, "mismatch_type_counts": {"rationale_suggests_fixable_label_not_fixable_or_unclear": 1}}`

## Test 1b - Importance / Resolution Independence

- Judgment: `independent_model_calls`
- Same call: `False`
- Same prompt: `False`
- Importance prompt sees rebuttal: `False`
- Discount Test-1 directional: `partially`
- Interpretation: Importance is produced during claim extraction from the original review only. Rebuttal resolution is produced later from reviewer-claim/author-response pairs. The Test-1 cross-tab is not confounded by a single shared model call, but importance remains an unvalidated LLM proxy and should not be treated as human-validated materiality.

## Example Labels

### Not Fixable High Importance Unresolved
- `My7lkRNnL9:RzQfnEwCrf:4` structurally_unresolvable fixable=False importance=major effect=does_not_address: A claim of insufficient empirical or theoretical contribution is a structural judgment about the work’s significance/novelty that cannot be overturned by a rebuttal text alone, absent new results beyond the submission scope.
- `gtkFw6sZGS:5yEYAAadyY:0` structurally_unresolvable fixable=False importance=major effect=partially_addresses: This critiques the work's novelty/significance, which is a structural judgment about contribution value that cannot be overturned by rebuttal text beyond possibly reframing claims.
- `pYmQId95iR:nfcmdmKvik:0` structurally_unresolvable fixable=False importance=major effect=does_not_address: Whether the work must include a new method is a judgment about the paper’s framing/novelty (a benchmark-only contribution), which cannot be fixed by rebuttal text alone without changing the contribution itself.
- `qBL04XXex6:1lDRac9ePM:0` structurally_unresolvable fixable=False importance=major effect=does_not_address: This is a significance/lasting-impact critique about whether prompt engineering offers fundamental insight, which is a structural judgment about the contribution’s worth that cannot be resolved by a rebuttal text alone.

### Fixable High Importance Unresolved
- `10eQ4Cfh8p:S3IqtlOGLT:1` answerable_fixable fixable=True importance=major effect=does_not_address: Authors can add results on additional standard FJSP benchmarks or analyze cross-dataset generalization in rebuttal/appendix to address generalizability concerns.
- `10eQ4Cfh8p:wckxlkPL42:0` answerable_fixable fixable=True importance=major effect=does_not_address: This is a clarity/presentation issue about defining the action space for the improvement policy, which can be addressed by providing precise formal definitions, examples, and possibly pseudocode in a rebuttal and revision.
- `10eQ4Cfh8p:zlSWBdRAhX:2` answerable_fixable fixable=True importance=major effect=does_not_address: Missing baselines and runtime reports can be added or clarified in a rebuttal/supplement with new experiments or previously omitted results, so this is addressable by providing additional comparisons and timings.
- `10eQ4Cfh8p:zlSWBdRAhX:3` answerable_fixable fixable=True importance=major effect=does_not_address: Reporting multiple seeds, standard deviations, and reproducibility details (code, seeds, run counts) can be added in a rebuttal with additional experiments or clarifications, so this is fixable.
- `1FWDEIGm33:MzDh7uJCEU:2` answerable_fixable fixable=True importance=major effect=does_not_address: This is a presentation/clarity issue about defining the main focus and the term, which can be resolved by tightening the definition, refining wording, and adding illustrative examples in the rebuttal and revision.
- `1FWDEIGm33:pfCqf1kmPM:4` answerable_fixable fixable=True importance=major effect=partially_addresses: The reviewer asks for analysis of training data influence, which could be addressed by adding experiments (e.g., comparing models with known/pretrained datasets, ablations, or correlating behaviors with dataset attributes) or by clarifyi...
- `1FWDEIGm33:pfCqf1kmPM:5` answerable_fixable fixable=True importance=major effect=does_not_address: This is a request for clarification of a specific formula and analysis procedure (how outputs are processed and how the mean is computed), which can be addressed by detailing the mathematical definition, preprocessing steps, aggregation,...
- `23OEmHVkpq:8CzSIMq0YG:0` answerable_fixable fixable=True importance=major effect=partially_addresses: This is a presentation/organization request to move and highlight an existing analysis from the appendix to the main paper, which can be addressed by revising the manuscript and clarifying its role in the method.

### Controls Not Fixable
- `gtkFw6sZGS:5yEYAAadyY:0` structurally_unresolvable fixable=False importance=major effect=partially_addresses: This critiques the work's novelty/significance, which is a structural judgment about contribution value that cannot be overturned by rebuttal text beyond possibly reframing claims.
