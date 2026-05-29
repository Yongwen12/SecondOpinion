# Concern RAG Validation

- Queries: 48
- Memory records: 48
- Exclude same paper: True

## Metrics

| Metric | Value |
| --- | ---: |
| `match_hit@1` | 0.458 |
| `match_hit@3` | 0.792 |
| `match_hit@5` | 0.875 |
| `match_knn_accuracy@1` | 0.458 |
| `match_knn_accuracy@3` | 0.438 |
| `match_knn_accuracy@5` | 0.583 |
| `match_mrr` | 0.631 |
| `quality_hit@1` | 0.854 |
| `quality_hit@3` | 0.917 |
| `quality_hit@5` | 0.938 |
| `quality_knn_accuracy@1` | 0.854 |
| `quality_knn_accuracy@3` | 0.875 |
| `quality_knn_accuracy@5` | 0.896 |
| `quality_mrr` | 0.890 |
| `random_match_hit@1` | 0.437 |
| `random_match_hit@3` | 0.788 |
| `random_match_hit@5` | 0.895 |
| `random_quality_hit@1` | 0.804 |
| `random_quality_hit@3` | 0.911 |
| `random_quality_hit@5` | 0.920 |
| `type_hit@1` | 0.271 |
| `type_hit@3` | 0.583 |
| `type_hit@5` | 0.750 |

## Label Counts

- `gold_meta_review_match_counts`: `{"not_found": 4, "partial": 27, "survived": 17}`
- `memory_match_counts`: `{"not_found": 4, "partial": 27, "survived": 17}`
- `gold_concern_quality_counts`: `{"high": 43, "low": 1, "medium": 4}`
- `memory_quality_counts`: `{"high": 43, "low": 1, "medium": 4}`

## Miss Examples

- `UVSKuh9eK5:AUeGBXg0Pe:1` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `UVSKuh9eK5:lo6OmS3vso:0` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `yacRhge4zQ:pKsEW8Yja4:0` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `10eQ4Cfh8p:w67nfG2dMW:3` gold=`survived` retrieved=['partial', 'partial', 'partial']
- `pYmQId95iR:u5ZC4CoNyk:6` gold=`not_found` retrieved=['partial', 'survived', 'partial']
- `9L9j5bQPIY:91NkdJpVId:2` gold=`not_found` retrieved=['survived', 'partial', 'partial']