# Lifecycle Proxy Ablation

## Scope

- Claims: 854
- Claims with LLM rebuttal labels: 240
- Claims with LLM consensus labels: 120
- Claims with any LLM label: 323
- Claims with both LLM labels: 37

## Mode Summary

| Mode | Claims | Mean lifecycle | Median lifecycle | High | Medium | Low | LLM rebuttal coverage | LLM consensus coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `proxy_only` | 854 | 56.5% | 55.2% | 76 | 652 | 126 | 28.1% | 14.1% |
| `hybrid` | 854 | 57.5% | 56.5% | 97 | 650 | 107 | 28.1% | 14.1% |
| `llm_calibrated_only` | 323 | 58.4% | 58.7% | 43 | 239 | 41 | 74.3% | 37.1% |
| `strict_both_llm` | 37 | 59.0% | 59.0% | 3 | 31 | 3 | 100.0% | 100.0% |

## Mean Signal Scores

### `proxy_only`
- `grounding`: 100.0%
- `specificity`: 77.0%
- `consensus`: 56.2%
- `rebuttal_robustness`: 53.6%
- `discussion_followup`: 10.2%
- `meta_review_uptake`: 28.3%

### `hybrid`
- `grounding`: 100.0%
- `specificity`: 77.0%
- `consensus`: 53.3%
- `rebuttal_robustness`: 59.8%
- `discussion_followup`: 10.2%
- `meta_review_uptake`: 28.3%

### `llm_calibrated_only`
- `grounding`: 100.0%
- `specificity`: 76.4%
- `consensus`: 49.0%
- `rebuttal_robustness`: 66.1%
- `discussion_followup`: 10.8%
- `meta_review_uptake`: 29.0%

### `strict_both_llm`
- `grounding`: 100.0%
- `specificity`: 74.9%
- `consensus`: 42.3%
- `rebuttal_robustness`: 73.2%
- `discussion_followup`: 11.3%
- `meta_review_uptake`: 30.3%

## Comparisons

### `hybrid_vs_proxy_all_claims`

- Claims compared: 854
- Mean score delta: +1.0%
- Mean absolute score delta: 2.2%
- Label changes: 82 (9.6%)
- Label-change counts: `{"high->medium": 10, "low->medium": 30, "medium->high": 31, "medium->low": 11}`
- Mean signal deltas: `{"consensus": -0.0299, "discussion_followup": 0.0, "grounding": 0.0, "meta_review_uptake": 0.0, "rebuttal_robustness": 0.0617, "specificity": 0.0}`

### `llm_subset_hybrid_vs_proxy`

- Claims compared: 323
- Mean score delta: +2.6%
- Mean absolute score delta: 5.9%
- Label changes: 82 (25.4%)
- Label-change counts: `{"high->medium": 10, "low->medium": 30, "medium->high": 31, "medium->low": 11}`
- Mean signal deltas: `{"consensus": -0.0789, "discussion_followup": 0.0, "grounding": 0.0, "meta_review_uptake": 0.0, "rebuttal_robustness": 0.163, "specificity": 0.0}`

### `strict_both_llm_hybrid_vs_proxy`

- Claims compared: 37
- Mean score delta: +1.8%
- Mean absolute score delta: 6.0%
- Label changes: 10 (27.0%)
- Label-change counts: `{"high->medium": 3, "low->medium": 4, "medium->high": 2, "medium->low": 1}`
- Mean signal deltas: `{"consensus": -0.2257, "discussion_followup": 0.0, "grounding": 0.0, "meta_review_uptake": 0.0, "rebuttal_robustness": 0.2338, "specificity": 0.0}`

## Lexical Proxy Diagnostics

### Rebuttal Resolution

- LLM-labeled claims: 240
- Proxy says addressed/resolved: 78.8%
- LLM says specifically addressed/resolved: 27.1%
- LLM says resolved/weakened: 3.3%
- Lexical false-positive candidates among proxy-addressed claims: 128 (67.7%)
- Proxy labels: `{"addressed_unclear_resolution": 131, "likely_resolved_or_answered": 58, "not_addressed": 51}`
- LLM response labels: `{"generic_or_unclear": 70, "likely_resolved": 2, "not_addressed": 105, "specifically_addressed": 63}`
- LLM effect labels: `{"does_not_address": 128, "partially_addresses": 73, "resolved_or_weakened": 8, "unclear": 31}`

### Inter-Reviewer Consensus

- LLM-labeled claims: 120
- Proxy says partial/strong: 80.0%
- LLM says related/same: 64.2%
- LLM says same concern: 6.7%
- Lexical false-positive candidates among proxy-positive claims: 27 (28.1%)
- Proxy labels: `{"none": 24, "partial": 54, "strong": 42}`
- LLM labels: `{"not_same_concern": 42, "related_but_different": 69, "same_concern": 8, "unsure": 1}`

## Notes

- `proxy_only` uses deterministic lexical-overlap labels for consensus, rebuttal, and meta-review uptake.
- `hybrid` mirrors the current lifecycle logic: LLM labels are used for rebuttal/consensus when available, with proxy fallback otherwise.
- `llm_calibrated_only` restricts analysis to claims with at least one LLM rebuttal or consensus label; uncalibrated components still use proxy fallback to keep the lifecycle formula comparable.
- `strict_both_llm` is the small high-precision subset where both rebuttal and consensus have LLM labels. Meta-review uptake is still proxy-based in all modes.
