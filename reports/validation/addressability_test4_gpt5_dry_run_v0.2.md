# Addressability Classification Test 4 Dry Run

- Prepared unique claims: 240
- Main unresolved/generic candidate claims: 232
- Resolved/effect control claims: 8
- Specifically-addressed control claims: 63
- Paper context counts: `{"title_abstract": 240}`
- No-leakage check: `{"prompt_includes_existing_response_or_effect_labels": false, "prompt_includes_importance_proxy": false, "prompt_includes_rebuttal_text": false}`

## Test 1b - Importance / Resolution Independence

- Judgment: `independent_model_calls`
- Same call: `False`
- Same prompt: `False`
- Importance prompt sees rebuttal: `False`
- Interpretation: Importance is produced during claim extraction from the original review only. Rebuttal resolution is produced later from reviewer-claim/author-response pairs. The Test-1 cross-tab is not confounded by a single shared model call, but importance remains an unvalidated LLM proxy and should not be treated as human-validated materiality.
