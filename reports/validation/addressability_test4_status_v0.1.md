# Addressability Test 4 Status

## Status

Prepared, not fully executed.

The Test 4 classifier and reporting pipeline are ready, and the dry-run confirms the target sample/control structure. The actual LLM labeling pass was not executed because it would send OpenReview paper abstracts and reviewer concerns to the external OpenAI API. That data transfer needs explicit user approval before running.

## Dry-Run Counts

- Prepared unique claims: 240
- Main unresolved/generic candidate claims: 232
- Resolved/effect control claims: 8
- Specifically-addressed control claims: 63
- Paper context coverage: 240/240 have title + abstract
- No-leakage prompt config:
  - rebuttal text included: false
  - existing response/effect labels included: false
  - importance proxy included: false

## Test 1b - Importance / Resolution Independence

- Judgment: independent model calls
- Same call: false
- Same prompt: false
- Importance prompt sees rebuttal: false
- Resolution prompt sees importance: true
- Discount Test-1 directional: partially

Interpretation: importance is produced during claim extraction from the original review only. Rebuttal resolution is produced later from reviewer-claim/author-response pairs. The Test-1 cross-tab is not confounded by one shared model call, but importance remains an unvalidated LLM proxy and should not be treated as human-validated materiality.

## Next Command If Approved

```powershell
python -m secondopinion.addressability_classification
```

This will produce:

- `data/validation/addressability_test4_llm_labels_v0.1.jsonl`
- `data/validation/addressability_test4_self_consistency_v0.1.jsonl`
- `data/validation/addressability_test4_report_v0.1.json`
- `reports/validation/addressability_test4_report_v0.1.md`
