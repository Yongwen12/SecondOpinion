# SecondOpinion External Scoring Memory Status v0.1

Date: 2026-06-17

Superseded by `docs/external_scoring_memory_status_v0.2.md` on 2026-06-20. This file is kept as the first smoke-integration snapshot.

This document records the implementation status for short-term target 2+3:

1. Use external peer-review datasets as scoring memory.
2. Combine retrieval priors with LLM scores.
3. Run benchmark guardrails before scorer changes ship.

## Implemented Path

The current implementation is no-fine-tuning:

- Normalize external datasets into a shared scoring schema.
- Build scoring-memory examples from normalized records.
- Retrieve examples per dimension with lexical retrieval.
- Blend `llm_score` and `memory_prior` into `final_score`.
- Run a benchmark suite and guardrail report.
- Display backend-shaped `hybrid_scores` in the public demo.

## Implemented Adapters

| Dataset | Dimension(s) | Status |
|---|---|---|
| ContraSciView | Consensus / conflict | Adapter retained and upgraded to shared schema |
| ReAct | Actionability; specificity when labels are present | Adapter implemented |
| SubstanReview | Substantiation | Adapter implemented |
| DISAPERE | Rebuttal robustness | Adapter implemented |
| RbtAct | Rebuttal robustness | Adapter implemented |

## Smoke Artifacts

- `data/validation/external_scoring_memory_smoke_corpus_v0.1.jsonl`
- `data/validation/scoring_memory_external_smoke_v0.1.jsonl`
- `data/validation/hybrid_scoring_external_smoke_result_v0.1.json`
- `data/validation/scoring_memory_suite_smoke_v0.1.json`
- `reports/validation/scoring_memory_suite_smoke_v0.1.md`
- `data/validation/scoring_memory_suite_guardrail_smoke_v0.1.json`
- `reports/validation/scoring_memory_suite_guardrail_smoke_v0.1.md`
- `frontend/demos/hybrid_scoring_demo.json`

## Current Limits

- Smoke fixtures prove the integration path; they are not the full external datasets.
- Full raw datasets should live under `data/external/<dataset>/` and stay out of Git.
- Consensus / conflict still has a separate ContraSciView smoke path; it is not included in the combined multi-dataset smoke memory yet.
- Professionalism remains LLM-only in the demo until PolitePEER / HedgePeer are wired.
