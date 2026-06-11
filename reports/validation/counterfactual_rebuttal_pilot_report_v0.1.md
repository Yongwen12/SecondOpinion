# Counterfactual Rebuttal Pilot Report

## Summary

- Claims: 30
- Generations: 90
- Pairwise judgments: 360
- Generator model: `gpt-5-mini`
- Judge model: `gpt-5`
- Sample addressability: `{"answerable_fixable": 22, "structurally_unresolvable": 6, "unclear": 2}`
- Sample importance: `{"major": 13, "medium": 7, "minor": 8, "question": 2}`

## Arm Length

`{"avoid": {"count": 30, "max_words": 64, "mean_words": 53.3, "min_words": 38}, "engage": {"count": 30, "max_words": 134, "mean_words": 117.33, "min_words": 101}, "polished_avoid": {"count": 30, "max_words": 127, "mean_words": 105.23, "min_words": 87}}`

## Length Control

`{"engage_polished_pairs": 30, "max_relative_word_diff": 0.1463, "mean_relative_word_diff": 0.1036, "over_15pct_diff_count": 0, "polished_retry_count": 9}`

## Judge Diagnostics

`{"by_pair": {"engage_vs_avoid": {"confidence": {"high": 172, "medium": 8}, "judgment_count": 180, "winner_arm": {"engage": 180}}, "engage_vs_polished_avoid": {"confidence": {"high": 129, "low": 1, "medium": 50}, "judgment_count": 180, "winner_arm": {"engage": 180}}}, "confidence": {"high": 301, "low": 1, "medium": 58}, "engage_vs_polished_by_addressability_deltas": {"answerable_fixable": {"claim_count_estimate": 22.0, "judgment_count": 132, "mean_engage_helpfulness": 3.947, "mean_engage_resolution": 1.5985, "mean_helpfulness_delta": 0.697, "mean_polished_helpfulness": 3.25, "mean_polished_resolution": 0.6212, "mean_resolution_delta": 0.9773}, "structurally_unresolvable": {"claim_count_estimate": 6.0, "judgment_count": 36, "mean_engage_helpfulness": 3.9444, "mean_engage_resolution": 1.25, "mean_helpfulness_delta": 0.6111, "mean_polished_helpfulness": 3.3333, "mean_polished_resolution": 0.5, "mean_resolution_delta": 0.75}, "unclear": {"claim_count_estimate": 2.0, "judgment_count": 12, "mean_engage_helpfulness": 4.6667, "mean_engage_resolution": 1.0, "mean_helpfulness_delta": 2.5, "mean_polished_helpfulness": 2.1667, "mean_polished_resolution": 0.0, "mean_resolution_delta": 1.0}}, "winner_arm": {"engage": 360}}`

## Stable Pairwise Results

- Pair summary: `{"engage_vs_avoid": {"engage": 30}, "engage_vs_polished_avoid": {"engage": 30}}`
- By addressability: `{"engage_vs_avoid": {"answerable_fixable": {"engage": 22}, "structurally_unresolvable": {"engage": 6}, "unclear": {"engage": 2}}, "engage_vs_polished_avoid": {"answerable_fixable": {"engage": 22}, "structurally_unresolvable": {"engage": 6}, "unclear": {"engage": 2}}}`

## Hypothesis Readout

`{"H1_engage_over_avoid": {"counts": {"engage": 30}, "stable_total": 30, "winner_count": 30, "winner_rate": 1.0}, "H2_engage_over_polished_avoid": {"counts": {"engage": 30}, "stable_total": 30, "winner_count": 30, "winner_rate": 1.0}, "H3_by_addressability": {"engage_vs_avoid": {"answerable_fixable": {"engage": 22}, "structurally_unresolvable": {"engage": 6}, "unclear": {"engage": 2}}, "engage_vs_polished_avoid": {"answerable_fixable": {"engage": 22}, "structurally_unresolvable": {"engage": 6}, "unclear": {"engage": 2}}}}`

## Caveat

This is an LLM-AC counterfactual experiment, not direct evidence of human reviewer score movement.
