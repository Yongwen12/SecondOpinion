# Component Benchmark

- Task type: `classification`
- Records: 47975

## Summary

| Metric | Value |
| --- | ---: |
| `record_count` | 47975 |
| `accuracy` | 0.879 |
| `majority_baseline` | 0.881 |
| `balanced_accuracy` | 0.503 |
| `macro_f1` | 0.475 |

## Label Counts

- Gold: `{"contradiction": 5725, "not_contradiction": 42250}`
- Predicted: `{"contradiction": 151, "not_contradiction": 47824}`

## Per Label

| Label | Precision | Recall | F1 | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `contradiction` | 0.291 | 0.008 | 0.015 | 44 | 107 | 5681 |
| `not_contradiction` | 0.881 | 0.998 | 0.936 | 42143 | 5681 | 107 |

## Notes

- This benchmark validates component outputs only. It does not validate core materiality or substantive resolution unless the input gold labels explicitly come from that construct.
