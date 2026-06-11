# Addressability Test 4 GPT-5 Interpretation

## What Changed

This rerun used the same 232 main candidates as v0.1 and the same no-leakage setup: the prompt included only paper title/abstract and the reviewer concern. It did not include rebuttal text, existing response/effect labels, or the importance proxy.

Changes from v0.1:

- model: `gpt-5` instead of `gpt-5-nano`
- prompt: stronger instruction against using `unclear` as a hedge
- prompt: presentation/writing/figure/table/notation/appendix-placement issues are explicitly `answerable_fixable`
- added rationale/label consistency scan

So the result tests robustness under a stronger model plus a corrected prompt. It is not a pure model-only ablation.

## Main 232 Claims

Tri-state split:

- fixable: 224 / 232 = 96.5%
- true not-fixable: 6 / 232 = 2.6%
- unclear: 2 / 232 = 0.9%

Four-way labels:

- `answerable_fixable`: 224
- `structurally_unresolvable`: 6
- `requires_concession`: 0
- `unclear`: 2

Not-fixable subtype:

- novelty/significance/framing verdict: 6
- other/requires-concession: 0

## Headline Cell

Among high-importance-proxy + unresolved/partial claims:

- total: 155
- fixable: 151 / 155 = 97.4%
- true not-fixable: 4 / 155 = 2.6%
- unclear: 0 / 155 = 0.0%

Four-way labels:

- `answerable_fixable`: 151
- `structurally_unresolvable`: 4
- `requires_concession`: 0
- `unclear`: 0

Not-fixable subtype:

- novelty/significance/framing verdict: 4
- other/requires-concession: 0

## Model Robustness vs Nano v0.1

Paired main candidates: 232.

Tri-state counts:

- nano v0.1: fixable 131, not-fixable 47, unclear 54
- GPT-5 v0.2: fixable 224, not-fixable 6, unclear 2

Agreement:

- tri-state exact agreement: 136 / 232 = 58.6%
- binary agreement on pairs where both runs were determinate: 135 / 177 = 76.3%

Fixable-rate movement:

- all 232 claims: 56.5% -> 96.5%, delta +40.1pp
- excluding unclear: 73.6% -> 97.4%, delta +23.8pp

Interpretation: the high-level direction survives the stronger run. The previous `unclear` and not-fixable mass was mostly model/prompt noise, not evidence that many concerns are true dead ends.

## Controls

Resolved/effect control:

- total: 8
- fixable: 8
- not-fixable: 0
- unclear: 0

Specifically-addressed control:

- total: 63
- fixable: 62
- not-fixable: 1
- unclear: 0

The controls look healthier than v0.1: the classifier no longer misuses `unclear` for engaged/resolved claims.

## Self-Consistency

30 sampled claims, 3 reworded-prompt reruns each:

- exact 4-way agreement with main pass: 79 / 90 = 87.8%
- binary fixable-vs-not agreement with main pass: 84 / 90 = 93.3%
- within-rerun exact unanimity by claim: 26 / 30 = 86.7%
- within-rerun binary unanimity by claim: 27 / 30 = 90.0%

This improves substantially over nano v0.1's binary agreement with main pass of 75.6%.

## Rationale/Label Consistency Scan

- checked: 232
- mismatches: 1
- mismatch rate: 0.4%

The remaining example is a benign edge case: the rationale says the concern is too vague, but contains the phrase "could be addressed" while explaining that concrete issues are missing. The scan is close to zero, so the previous rationale/label inconsistency problem is effectively fixed.

## Product Read

The robust story is now stronger:

1. Most unresolved high-importance-proxy concerns are not dead ends. They are intrinsically addressable, meaning a product can help authors produce a more substantive rebuttal.
2. A small minority are genuine framing/novelty/significance dead ends. These should not be treated as "write a better answer"; the product should advise reframing, narrowing scope, or accepting that this point is hard to reverse.
3. This removes the "weak model produced too many unclear/not-fixable labels" caveat for addressability. It does not remove the separate materiality caveat: `importance` is still an unvalidated proxy and still needs the IAA pilot.
