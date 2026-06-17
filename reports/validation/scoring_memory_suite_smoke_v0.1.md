# Scoring Memory Benchmark Suite

- Records: 10
- Dimensions: 4
- Overall accuracy: 0.8000
- Overall macro F1: 0.7333

## By Dimension

| Dimension | Records | Accuracy | Macro F1 | Majority baseline |
| --- | ---: | ---: | ---: | ---: |
| `actionability` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `rebuttal_robustness` | 4 | 0.5000 | 0.3333 | 0.2500 |
| `specificity` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `substantiation` | 2 | 1.0000 | 1.0000 | 0.5000 |

## Notes

- This suite checks external component labels used as scoring memory.
- It is a regression guardrail for the scorer, not proof that reviewer comments are objectively correct.
