# Scoring Benchmark Guardrail

- Status: `pass`

## Checks

| Check | Status | Current | Baseline / Threshold | Limit |
| --- | --- | ---: | ---: | ---: |
| `accuracy_min` | `pass` | 0.7500 | 0.4000 | 0.4000 |
| `macro_f1_min` | `pass` | 0.6987 | 0.2500 | 0.2500 |
| `accuracy_drop` | `skipped` | 0.7500 | - | 0.0200 |
| `macro_f1_drop` | `skipped` | 0.6987 | - | 0.0200 |

## Notes

- Guardrails are for benchmark regression only. They do not prove the scoring construct is correct.
- Use this after prompt, retrieval, adapter, or scoring-weight changes.
