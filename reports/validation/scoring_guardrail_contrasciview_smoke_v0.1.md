# Scoring Benchmark Guardrail

- Status: `pass`

## Checks

| Check | Status | Current | Baseline / Threshold | Limit |
| --- | --- | ---: | ---: | ---: |
| `accuracy_min` | `pass` | 0.8594 | 0.5000 | 0.5000 |
| `macro_f1_min` | `skipped` | 0.5225 | - | - |
| `accuracy_drop` | `pass` | 0.8594 | 0.8807 | 0.2500 |
| `macro_f1_drop` | `pass` | 0.5225 | 0.4683 | 0.0200 |

## Notes

- Guardrails are for benchmark regression only. They do not prove the scoring construct is correct.
- Use this after prompt, retrieval, adapter, or scoring-weight changes.
