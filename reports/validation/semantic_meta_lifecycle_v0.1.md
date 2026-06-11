# Semantic Meta-Review Lifecycle Recalibration

## Scope

- Claims: 854
- Claims with semantic meta-review records: 500
- Claims with decisive semantic meta-review labels: 421
- High-confidence decisive semantic labels: 155
- Semantic/proxy exact agreement: 74.6%
- Semantic label counts: `{"not_found": 134, "partial": 280, "survived": 7, "unsure": 79}`
- Proxy labels on semantic records: `{"not_found": 214, "partial": 245, "survived": 41}`

## Mode Summary

| Mode | Claims | Mean lifecycle | Median lifecycle | Mean meta uptake | High | Medium | Low |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `current_proxy_meta` | 854 | 57.5% | 56.5% | 28.3% | 97 | 650 | 107 |
| `semantic_hybrid_meta` | 854 | 57.4% | 57.4% | 28.1% | 81 | 665 | 108 |
| `semantic_labeled_only` | 421 | 60.1% | 61.8% | 41.6% | 51 | 332 | 38 |
| `semantic_high_confidence_only` | 155 | 65.5% | 65.6% | 61.2% | 31 | 122 | 2 |

## Comparisons

### `semantic_hybrid_vs_current_all_claims`

- Claims compared: 854
- Mean score delta: -0.0%
- Mean absolute score delta: 1.5%
- Mean meta-review uptake delta: -0.2%
- Label changes: 37 (4.3%)
- Label-change counts: `{"high->medium": 21, "low->medium": 5, "medium->high": 5, "medium->low": 6}`

### `semantic_labeled_vs_current_subset`

- Claims compared: 421
- Mean score delta: -0.1%
- Mean absolute score delta: 2.9%
- Mean meta-review uptake delta: -0.3%
- Label changes: 37 (8.8%)
- Label-change counts: `{"high->medium": 21, "low->medium": 5, "medium->high": 5, "medium->low": 6}`

### `semantic_high_confidence_vs_current_subset`

- Claims compared: 155
- Mean score delta: +0.7%
- Mean absolute score delta: 2.5%
- Mean meta-review uptake delta: +3.2%
- Label changes: 13 (8.4%)
- Label-change counts: `{"high->medium": 9, "low->medium": 1, "medium->high": 3}`

## Semantic Meta-Review Diagnostics

- Matched records: 500
- Decisive records: 421
- Proxy positive rate: 63.7%
- Semantic positive rate: 68.2%
- Exact agreement rate: 74.6%
- Proxy false-positive candidates: 30 (11.2% of proxy positives)
- Proxy false-negative candidates: 49 (32.0% of proxy negatives)
- Semantic labels: `{"not_found": 134, "partial": 280, "survived": 7, "unsure": 79}`
- Proxy labels: `{"not_found": 214, "partial": 245, "survived": 41}`

## Notes

- `current_proxy_meta` keeps the existing lexical meta-review uptake signal.
- `semantic_hybrid_meta` replaces meta-review uptake with LLM semantic labels when decisive; missing/unsure labels fall back to proxy.
- `semantic_labeled_only` reports only claims with decisive semantic meta-review labels.
- `semantic_high_confidence_only` is the strictest subset: decisive semantic labels marked high-confidence training candidates.
- Rebuttal and consensus still use the current hybrid LLM/proxy logic; this report isolates the meta-review uptake leg.
