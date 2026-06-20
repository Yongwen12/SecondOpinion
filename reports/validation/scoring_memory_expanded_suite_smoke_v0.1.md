# Scoring Memory Benchmark Suite

- Records: 28
- Dimensions: 10
- Overall accuracy: 0.7500
- Overall macro F1: 0.6987

## By Dimension

| Dimension | Records | Accuracy | Macro F1 | Majority baseline |
| --- | ---: | ---: | ---: | ---: |
| `actionability` | 4 | 0.5000 | 0.3333 | 0.2500 |
| `argument_role` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `consensus_conflict` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `professionalism` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `rebuttal_alignment` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `rebuttal_robustness` | 6 | 0.5000 | 0.3333 | 0.3333 |
| `review_aspect` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `revision_alignment` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `specificity` | 2 | 1.0000 | 1.0000 | 0.5000 |
| `substantiation` | 4 | 0.5000 | 0.3750 | 0.2500 |

## Notes

- This suite checks external component labels used as scoring memory.
- It is a regression guardrail for the scorer, not proof that reviewer comments are objectively correct.
