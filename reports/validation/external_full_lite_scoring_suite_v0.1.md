# Scoring Memory Benchmark Suite

- Records: 73193
- Dimensions: 7
- Overall accuracy: 0.3949
- Overall macro F1: 0.7385

## By Dimension

| Dimension | Records | Accuracy | Macro F1 | Majority baseline |
| --- | ---: | ---: | ---: | ---: |
| `actionability` | 2766 | 0.2621 | 0.1390 | 0.2744 |
| `consensus_conflict` | 47975 | 0.1193 | 0.1066 | 0.8807 |
| `professionalism` | 2500 | 1.0000 | 1.0000 | 0.4568 |
| `rebuttal_alignment` | 9166 | 1.0000 | 1.0000 | 0.7825 |
| `rebuttal_robustness` | 4463 | 1.0000 | 1.0000 | 0.6204 |
| `revision_alignment` | 3546 | 1.0000 | 1.0000 | 0.9693 |
| `substantiation` | 2777 | 1.0000 | 1.0000 | 0.5564 |

## Notes

- This suite checks external component labels used as scoring memory.
- It is a regression guardrail for the scorer, not proof that reviewer comments are objectively correct.
