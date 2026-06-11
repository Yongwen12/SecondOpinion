# Concern RAG Validation

- Queries: 421
- Memory records: 421
- Input queries: 500
- Input memory records: 500
- Filters: `{"only_decisive_meta_labels": true, "only_high_confidence": false}`
- Exclude same paper: True

## Metrics

| Metric | Value |
| --- | ---: |
| `majority_match_baseline` | 0.665 |
| `majority_quality_baseline` | 0.442 |
| `match_hit@1` | 0.587 |
| `match_hit@3` | 0.872 |
| `match_hit@5` | 0.931 |
| `match_knn_accuracy@1` | 0.587 |
| `match_knn_accuracy@3` | 0.601 |
| `match_knn_accuracy@5` | 0.644 |
| `match_mrr` | 0.729 |
| `quality_hit@1` | 0.390 |
| `quality_hit@3` | 0.727 |
| `quality_hit@5` | 0.865 |
| `quality_knn_accuracy@1` | 0.390 |
| `quality_knn_accuracy@3` | 0.344 |
| `quality_knn_accuracy@5` | 0.401 |
| `quality_mrr` | 0.571 |
| `random_match_hit@1` | 0.542 |
| `random_match_hit@3` | 0.858 |
| `random_match_hit@5` | 0.935 |
| `random_quality_hit@1` | 0.364 |
| `random_quality_hit@3` | 0.720 |
| `random_quality_hit@5` | 0.858 |
| `type_hit@1` | 0.435 |
| `type_hit@3` | 0.758 |
| `type_hit@5` | 0.860 |

## Label Counts

- `gold_meta_review_match_counts`: `{"not_found": 134, "partial": 280, "survived": 7}`
- `memory_match_counts`: `{"not_found": 134, "partial": 280, "survived": 7}`
- `gold_concern_quality_counts`: `{"high": 68, "low": 160, "medium": 186, "unsure": 7}`
- `memory_quality_counts`: `{"high": 68, "low": 160, "medium": 186, "unsure": 7}`

## Miss Examples

- `7QlKLvfVge:LsvjaIpscH:3` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `xNdE7RiRyP:JJaMxMXMtr:2` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `3wL1tj3kqE:6hdEd9y3Hn:3` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `eUgS9Ig8JG:6iCqDrP0HV:1` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `BQvbL2sFQx:QocYHmpKnK:2` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `rp5vfyp5Np:vGNqxpozDP:0` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `qBL04XXex6:Fv3pXWd41e:4` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `ApjY32f3Xr:4e1fSBB3OO:0` gold=`survived` retrieved=['partial', 'partial', 'not_found']