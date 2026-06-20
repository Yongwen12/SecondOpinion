# SecondOpinion External Scoring Memory Status v0.2

Date: 2026-06-20

This document records the current implementation status for short-term target 2+3:

1. Use external peer-review datasets as scoring memory.
2. Combine retrieval priors with LLM scores.
3. Run benchmark guardrails before scorer changes ship.

## Current State

The project now has a no-fine-tuning external-memory path:

- External dataset adapters normalize records into the shared JSONL schema.
- Tiny smoke fixtures prove each adapter path without committing full raw datasets.
- `build-scoring-memory --dimension auto` builds lexical scoring memory from normalized records.
- `score-dimensions-with-memory` returns `llm_score`, `memory_prior`, `final_score`, source, and retrieved examples.
- `run-scoring-memory-suite` generates benchmark and guardrail reports.
- The demo fixture now shows all six product dimensions as memory-backed.

## Product Scoring Dimensions

| Dimension | Wired external sources | Current use |
|---|---|---|
| Specificity | ReAct specificity fixture | Six-dimensional score memory |
| Substantiation | SubstanReview, ReviewCritique | Six-dimensional score memory |
| Actionability | ReAct, BetterPR | Six-dimensional score memory |
| Consensus / conflict | ContraSciView adapter, RevCI fixture | Six-dimensional score memory |
| Rebuttal robustness | DISAPERE, RbtAct, Re2 | Six-dimensional score memory |
| Professionalism | PolitePEER | Six-dimensional score memory |

## Structural And Lifecycle Memory

| Dimension | Wired external sources | Current use |
|---|---|---|
| Argument role | AMPERE | Diagnostic / structural memory |
| Review aspect | ASAP-Review / ReviewAdvisor | Diagnostic / structural memory |
| Rebuttal alignment | APE | Review-comment to rebuttal alignment memory |
| Revision alignment | ARIES | Review-comment to edit/revision memory |

These dimensions are connected to the same normalized corpus and scoring-memory builder, but they are not included in the default six-dimensional product total unless explicitly requested.

## Implemented Artifacts

Core adapter code:

- `src/secondopinion/external_dataset_adapters.py`
- `src/secondopinion/scoring_memory.py`

Smoke source fixtures:

- `data/validation/reviewcritique_scoring_smoke_source_v0.1.jsonl`
- `data/validation/betterpr_scoring_smoke_source_v0.1.jsonl`
- `data/validation/politepeer_scoring_smoke_source_v0.1.jsonl`
- `data/validation/revci_scoring_smoke_source_v0.1.jsonl`
- `data/validation/ampere_structural_smoke_source_v0.1.jsonl`
- `data/validation/asap_review_structural_smoke_source_v0.1.jsonl`
- `data/validation/ape_alignment_smoke_source_v0.1.jsonl`
- `data/validation/aries_revision_smoke_source_v0.1.jsonl`
- `data/validation/re2_lifecycle_smoke_source_v0.1.jsonl`

Expanded smoke outputs:

- `data/validation/external_scoring_memory_expanded_smoke_corpus_v0.1.jsonl`
- `data/validation/scoring_memory_external_expanded_smoke_v0.1.jsonl`
- `data/validation/hybrid_scoring_external_expanded_smoke_result_v0.1.json`
- `data/validation/hybrid_scoring_alignment_expanded_smoke_result_v0.1.json`
- `data/validation/scoring_memory_expanded_suite_smoke_v0.1.json`
- `reports/validation/scoring_memory_expanded_suite_smoke_v0.1.md`
- `data/validation/scoring_memory_expanded_suite_guardrail_smoke_v0.1.json`
- `reports/validation/scoring_memory_expanded_suite_guardrail_smoke_v0.1.md`

Frontend fixture:

- `frontend/demos/hybrid_scoring_demo.json`

## Guardrail Snapshot

The expanded smoke suite currently has:

- Records: 28
- Dimensions: 10
- Overall accuracy: 0.7500
- Overall macro F1: 0.6987
- Guardrail status: pass

This is a regression guardrail for adapter/scoring-memory behavior. It is not a claim that the tiny smoke fixtures are a real benchmark of reviewer quality.

## Current Limits

- Full raw datasets have not been downloaded into this repo.
- Full raw datasets should live under `data/external/<dataset>/` and remain out of Git.
- Current retrieval is lexical and dependency-light; embedding retrieval is still a later upgrade.
- No model has been fine-tuned.
- DEFEND, HedgePeer, COMPARE, NLPeer, PeerRead, MOPRD, and PeerSum are still not wired into scoring memory.
- Structural/lifecycle dimensions are available as memory, but the default product flow remains: score six product dimensions first, then triage.
