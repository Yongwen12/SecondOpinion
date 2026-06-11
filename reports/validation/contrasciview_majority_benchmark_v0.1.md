# Component Benchmark

- Task type: `classification`
- Records: 47975

## Summary

| Metric | Value |
| --- | ---: |
| `record_count` | 47975 |
| `accuracy` | 0.881 |
| `majority_baseline` | 0.881 |
| `balanced_accuracy` | 0.500 |
| `macro_f1` | 0.468 |

## Label Counts

- Gold: `{"contradiction": 5725, "not_contradiction": 42250}`
- Predicted: `{"not_contradiction": 47975}`

## Per Label

| Label | Precision | Recall | F1 | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `contradiction` | 0.000 | 0.000 | 0.000 | 0 | 0 | 5725 |
| `not_contradiction` | 0.881 | 1.000 | 0.937 | 42250 | 5725 | 0 |

## Notes

- This benchmark validates component outputs only. It does not validate core materiality or substantive resolution unless the input gold labels explicitly come from that construct.
