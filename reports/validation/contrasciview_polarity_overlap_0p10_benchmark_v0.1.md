# Component Benchmark

- Task type: `classification`
- Records: 47975

## Summary

| Metric | Value |
| --- | ---: |
| `record_count` | 47975 |
| `accuracy` | 0.859 |
| `majority_baseline` | 0.881 |
| `balanced_accuracy` | 0.523 |
| `macro_f1` | 0.522 |

## Label Counts

- Gold: `{"contradiction": 5725, "not_contradiction": 42250}`
- Predicted: `{"contradiction": 1952, "not_contradiction": 46023}`

## Per Label

| Label | Precision | Recall | F1 | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `contradiction` | 0.239 | 0.081 | 0.121 | 466 | 1486 | 5259 |
| `not_contradiction` | 0.886 | 0.965 | 0.924 | 40764 | 5259 | 1486 |

## Notes

- This benchmark validates component outputs only. It does not validate core materiality or substantive resolution unless the input gold labels explicitly come from that construct.
