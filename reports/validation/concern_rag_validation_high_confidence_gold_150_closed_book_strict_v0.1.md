# Concern RAG Validation

- Queries: 150
- Memory records: 198
- Exclude same paper: True

## Metrics

| Metric | Value |
| --- | ---: |
| `match_hit@1` | 0.713 |
| `match_hit@3` | 0.867 |
| `match_hit@5` | 0.887 |
| `match_knn_accuracy@1` | 0.713 |
| `match_knn_accuracy@3` | 0.773 |
| `match_knn_accuracy@5` | 0.793 |
| `match_mrr` | 0.789 |
| `quality_hit@1` | 0.507 |
| `quality_hit@3` | 0.813 |
| `quality_hit@5` | 0.913 |
| `quality_knn_accuracy@1` | 0.507 |
| `quality_knn_accuracy@3` | 0.440 |
| `quality_knn_accuracy@5` | 0.480 |
| `quality_mrr` | 0.660 |
| `random_match_hit@1` | 0.705 |
| `random_match_hit@3` | 0.851 |
| `random_match_hit@5` | 0.877 |
| `random_quality_hit@1` | 0.445 |
| `random_quality_hit@3` | 0.807 |
| `random_quality_hit@5` | 0.911 |
| `type_hit@1` | 0.413 |
| `type_hit@3` | 0.707 |
| `type_hit@5` | 0.833 |

## Label Counts

- `gold_meta_review_match_counts`: `{"not_found": 7, "partial": 121, "survived": 22}`
- `memory_match_counts`: `{"not_found": 7, "partial": 169, "survived": 22}`
- `gold_concern_quality_counts`: `{"high": 79, "low": 10, "medium": 61}`
- `memory_quality_counts`: `{"high": 97, "low": 10, "medium": 91}`

## Miss Examples

- `jx6njBKH8E:ZUBG0iUrpP:0` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `SLw9fp4yI6:E3kdriGSqM:1` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `rhgIgTSSxW:CEBB2izG6I:0` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `eR4W9tnJoZ:yDixzw0azY:0` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `1FWDEIGm33:MzDh7uJCEU:5` gold=`not_found` retrieved=['survived', 'partial', 'partial']
- `eR4W9tnJoZ:yDixzw0azY:3` gold=`not_found` retrieved=['survived', 'partial', 'partial']
- `B0wJ5oCPdB:ZOPmtxTnai:1` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `rp5vfyp5Np:YktI8n3TeZ:2` gold=`survived` retrieved=['partial', 'partial', 'not_found']