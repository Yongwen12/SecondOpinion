# Addressability Test 4 Interpretation

## Core Counts

- Classified unique claims: 240
- Main unresolved/generic candidate claims: 232
- Resolved/effect control claims: 8
- Specifically-addressed control claims: 63
- Paper context coverage: 240/240 had title + abstract
- No leakage: prompts did not include rebuttal text, existing response/effect labels, or importance proxy.

## Main Candidate Distribution

Across the 232 unresolved/generic candidate claims:

- `answerable_fixable`: 131
- `structurally_unresolvable`: 39
- `requires_concession`: 8
- `unclear`: 54

If `unclear` is counted as not-fixable per the output schema:

- fixable: 131 / 232 = 56.5%
- not-fixable/unclear: 101 / 232 = 43.5%

For product interpretation, `unclear` should be treated as a review-needed bucket rather than merged with true non-fixability. Excluding `unclear`:

- determinate claims: 178
- fixable: 131 / 178 = 73.6%
- true not-fixable: 47 / 178 = 26.4%

## Headline Cell

Among high-importance-proxy + unresolved/partial claims:

- total: 155
- `answerable_fixable`: 95
- `structurally_unresolvable`: 25
- `requires_concession`: 3
- `unclear`: 32

If `unclear` is counted as not-fixable:

- fixable: 95 / 155 = 61.3%
- not-fixable/unclear: 60 / 155 = 38.7%

Excluding `unclear`:

- determinate claims: 123
- fixable: 95 / 123 = 77.2%
- true not-fixable: 28 / 123 = 22.8%

## Controls

Resolved/effect control claims:

- total: 8
- `answerable_fixable`: 5
- `unclear`: 3
- `structurally_unresolvable`: 0
- `requires_concession`: 0

Specifically-addressed control claims:

- total: 63
- `answerable_fixable`: 27
- `structurally_unresolvable`: 13
- `requires_concession`: 2
- `unclear`: 21

The tiny resolved/effect control is acceptable as a sanity check: it does not misclassify actually resolved claims as structurally unresolvable. The specifically-addressed control is noisier, which is expected because "specifically addressed" is engagement, not necessarily resolution.

## Self-Consistency

- 30 sampled claims, 3 reworded-prompt reruns each.
- Exact bucket agreement with the main pass: 56 / 90 = 62.2%
- Fixable-vs-not agreement with the main pass: 68 / 90 = 75.6%
- Within-rerun unanimity by exact bucket: 21 / 30 = 70.0%
- Within-rerun unanimity by fixable-vs-not: 27 / 30 = 90.0%

Interpretation: exact 4-way categories are noisy, but the binary fixable-vs-not split is much more stable. Use the binary split for the headline; treat precise bucket shares as directional.

## Product Read

The result supports a stronger VP2 story than "catch hollow rebuttals." A large share of unresolved high-importance-proxy concerns are intrinsically addressable, meaning the product can help authors write a better substantive response. A smaller but important share is truly not-fixable in rebuttal; for those, the product should advise a different tactic: reframing, narrowing scope, concession, or not wasting credibility on a dead-end.

The remaining caveat is unchanged: `importance` is still a proxy, not validated materiality. This test narrows the second caveat, addressability, but the first caveat still needs the IAA pilot.
