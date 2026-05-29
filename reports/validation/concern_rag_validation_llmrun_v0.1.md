# Concern RAG Validation

- Queries: 48
- Memory records: 48
- Exclude same paper: False

## Metrics

| Metric | Value |
| --- | ---: |
| `match_hit@1` | 0.500 |
| `match_hit@3` | 0.812 |
| `match_hit@5` | 0.896 |
| `match_knn_accuracy@1` | 0.500 |
| `match_knn_accuracy@3` | 0.521 |
| `match_knn_accuracy@5` | 0.542 |
| `match_mrr` | 0.656 |
| `quality_hit@1` | 0.854 |
| `quality_hit@3` | 0.917 |
| `quality_hit@5` | 0.917 |
| `quality_knn_accuracy@1` | 0.854 |
| `quality_knn_accuracy@3` | 0.875 |
| `quality_knn_accuracy@5` | 0.896 |
| `quality_mrr` | 0.882 |
| `random_match_hit@1` | 0.437 |
| `random_match_hit@3` | 0.788 |
| `random_match_hit@5` | 0.894 |
| `random_quality_hit@1` | 0.806 |
| `random_quality_hit@3` | 0.910 |
| `random_quality_hit@5` | 0.920 |
| `type_hit@1` | 0.188 |
| `type_hit@3` | 0.604 |
| `type_hit@5` | 0.729 |

## Label Counts

- `gold_meta_review_match_counts`: `{"not_found": 4, "partial": 27, "survived": 17}`
- `memory_match_counts`: `{"not_found": 4, "partial": 27, "survived": 17}`
- `gold_concern_quality_counts`: `{"high": 43, "low": 1, "medium": 4}`
- `memory_quality_counts`: `{"high": 43, "low": 1, "medium": 4}`

## Miss Examples

- `w73feIekdO:NLKFsY27K9:1` gold=`not_found` retrieved=['survived', 'partial', 'partial']
- `yacRhge4zQ:pKsEW8Yja4:0` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `10eQ4Cfh8p:w67nfG2dMW:3` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `pYmQId95iR:u5ZC4CoNyk:6` gold=`not_found` retrieved=['partial', 'survived', 'partial']
- `9L9j5bQPIY:91NkdJpVId:2` gold=`not_found` retrieved=['survived', 'partial', 'partial']