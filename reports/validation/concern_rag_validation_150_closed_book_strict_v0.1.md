# Concern RAG Validation

- Queries: 200
- Memory records: 48
- Exclude same paper: True

## Metrics

| Metric | Value |
| --- | ---: |
| `match_hit@1` | 0.220 |
| `match_hit@3` | 0.415 |
| `match_hit@5` | 0.480 |
| `match_knn_accuracy@1` | 0.220 |
| `match_knn_accuracy@3` | 0.285 |
| `match_knn_accuracy@5` | 0.280 |
| `match_mrr` | 0.322 |
| `quality_hit@1` | 0.235 |
| `quality_hit@3` | 0.275 |
| `quality_hit@5` | 0.295 |
| `quality_knn_accuracy@1` | 0.235 |
| `quality_knn_accuracy@3` | 0.220 |
| `quality_knn_accuracy@5` | 0.220 |
| `quality_mrr` | 0.257 |
| `random_match_hit@1` | 0.223 |
| `random_match_hit@3` | 0.425 |
| `random_match_hit@5` | 0.517 |
| `random_quality_hit@1` | 0.223 |
| `random_quality_hit@3` | 0.296 |
| `random_quality_hit@5` | 0.342 |
| `type_hit@1` | 0.435 |
| `type_hit@3` | 0.730 |
| `type_hit@5` | 0.845 |

## Label Counts

- `gold_meta_review_match_counts`: `{"not_found": 91, "partial": 56, "survived": 17, "unsure": 36}`
- `memory_match_counts`: `{"not_found": 4, "partial": 27, "survived": 17}`
- `gold_concern_quality_counts`: `{"high": 44, "low": 108, "medium": 38, "unsure": 10}`
- `memory_quality_counts`: `{"high": 43, "low": 1, "medium": 4}`

## Miss Examples

- `dYjuJGTEbc:3MMkDoB21Q:1` gold=`not_found` retrieved=['survived', 'partial', 'partial']
- `rGvDRT4Z60:yub0t46EhK:5` gold=`not_found` retrieved=['survived', 'partial', 'partial']
- `10eQ4Cfh8p:w67nfG2dMW:0` gold=`not_found` retrieved=['partial', 'survived', 'partial']
- `gYcft1HIaU:EwWKiU8GWB:1` gold=`not_found` retrieved=['survived', 'partial', 'partial']
- `AJBkfwXh3u:KidnSLrJ44:3` gold=`not_found` retrieved=['partial', 'survived', 'survived']
- `w73feIekdO:NLKFsY27K9:4` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `jXR5pjs1rV:dXSWosECmZ:3` gold=`not_found` retrieved=['partial', 'partial', 'partial']
- `dYjuJGTEbc:hJUcbfxUWY:2` gold=`not_found` retrieved=['partial', 'partial', 'partial']