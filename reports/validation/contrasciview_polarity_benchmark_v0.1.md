# Component Benchmark

- Task type: `classification`
- Records: 47975

## Summary

| Metric | Value |
| --- | ---: |
| `record_count` | 47975 |
| `accuracy` | 0.119 |
| `majority_baseline` | 0.881 |
| `balanced_accuracy` | 0.500 |
| `macro_f1` | 0.107 |

## Label Counts

- Gold: `{"contradiction": 5725, "not_contradiction": 42250}`
- Predicted: `{"contradiction": 47975}`

## Per Label

| Label | Precision | Recall | F1 | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `contradiction` | 0.119 | 1.000 | 0.213 | 5725 | 42250 | 0 |
| `not_contradiction` | 0.000 | 0.000 | 0.000 | 0 | 0 | 42250 |

## Notes

- This benchmark validates component outputs only. It does not validate core materiality or substantive resolution unless the input gold labels explicitly come from that construct.
