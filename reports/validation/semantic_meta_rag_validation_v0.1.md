# Concern RAG Validation

- Queries: 155
- Memory records: 155
- Input queries: 500
- Input memory records: 500
- Filters: `{"only_decisive_meta_labels": true, "only_high_confidence": true}`
- Exclude same paper: True

## Metrics

| Metric | Value |
| --- | ---: |
| `majority_match_baseline` | 0.955 |
| `majority_quality_baseline` | 0.568 |
| `match_hit@1` | 0.942 |
| `match_hit@3` | 0.968 |
| `match_hit@5` | 0.968 |
| `match_knn_accuracy@1` | 0.942 |
| `match_knn_accuracy@3` | 0.955 |
| `match_knn_accuracy@5` | 0.955 |
| `match_mrr` | 0.955 |
| `quality_hit@1` | 0.574 |
| `quality_hit@3` | 0.852 |
| `quality_hit@5` | 0.935 |
| `quality_knn_accuracy@1` | 0.574 |
| `quality_knn_accuracy@3` | 0.516 |
| `quality_knn_accuracy@5` | 0.497 |
| `quality_mrr` | 0.709 |
| `random_match_hit@1` | 0.912 |
| `random_match_hit@3` | 0.959 |
| `random_match_hit@5` | 0.961 |
| `random_quality_hit@1` | 0.500 |
| `random_quality_hit@3` | 0.867 |
| `random_quality_hit@5` | 0.959 |
| `type_hit@1` | 0.471 |
| `type_hit@3` | 0.748 |
| `type_hit@5` | 0.865 |

## Label Counts

- `gold_meta_review_match_counts`: `{"not_found": 1, "partial": 148, "survived": 6}`
- `memory_match_counts`: `{"not_found": 1, "partial": 148, "survived": 6}`
- `gold_concern_quality_counts`: `{"high": 66, "low": 1, "medium": 88}`
- `memory_quality_counts`: `{"high": 66, "low": 1, "medium": 88}`

## Miss Examples

- `ApjY32f3Xr:4e1fSBB3OO:0` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `7vVWiCrFnd:UTwNz3TQsJ:4` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `qBL04XXex6:1lDRac9ePM:1` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `1FWDEIGm33:MzDh7uJCEU:0` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `rhgIgTSSxW:CEBB2izG6I:0` gold=`not_found` retrieved=['partial', 'partial', 'partial']