# Counterfactual Rebuttal Pilot Report

## Summary

- Claims: 1
- Generations: 3
- Pairwise judgments: 4
- Generator model: `gpt-5-mini`
- Judge model: `gpt-5`
- Sample addressability: `{"structurally_unresolvable": 1}`
- Sample importance: `{"major": 1}`

## Arm Length

`{"avoid": {"count": 1, "max_words": 57, "mean_words": 57.0, "min_words": 57}, "engage": {"count": 1, "max_words": 140, "mean_words": 140.0, "min_words": 140}, "polished_avoid": {"count": 1, "max_words": 124, "mean_words": 124.0, "min_words": 124}}`

## Stable Pairwise Results

- Pair summary: `{"engage_vs_avoid": {"engage": 1}, "engage_vs_polished_avoid": {"engage": 1}}`
- By addressability: `{"engage_vs_avoid": {"structurally_unresolvable": {"engage": 1}}, "engage_vs_polished_avoid": {"structurally_unresolvable": {"engage": 1}}}`

## Hypothesis Readout

`{"H1_engage_over_avoid": {"counts": {"engage": 1}, "stable_total": 1, "winner_count": 1, "winner_rate": 1.0}, "H2_engage_over_polished_avoid": {"counts": {"engage": 1}, "stable_total": 1, "winner_count": 1, "winner_rate": 1.0}, "H3_by_addressability": {"engage_vs_avoid": {"structurally_unresolvable": {"engage": 1}}, "engage_vs_polished_avoid": {"structurally_unresolvable": {"engage": 1}}}}`

## Caveat

This is an LLM-AC counterfactual experiment, not direct evidence of human reviewer score movement.
