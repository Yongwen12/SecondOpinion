# Scoring Benchmark Guardrail

- Status: `pass`

## Checks

| Check | Status | Current | Baseline / Threshold | Limit |
| --- | --- | ---: | ---: | ---: |
| `accuracy_min` | `skipped` | 0.3949 | - | - |
| `macro_f1_min` | `skipped` | 0.7385 | - | - |
| `accuracy_drop` | `skipped` | 0.3949 | - | 0.0200 |
| `macro_f1_drop` | `skipped` | 0.7385 | - | 0.0200 |

## Notes

- Guardrails are for benchmark regression only. They do not prove the scoring construct is correct.
- Use this after prompt, retrieval, adapter, or scoring-weight changes.
