# SecondOpinion External Scoring Memory Status v0.2

Date: 2026-06-20

This document records the current implementation status for short-term target 2+3:

1. Use external peer-review datasets as scoring memory.
2. Combine retrieval priors with LLM scores.
3. Run benchmark guardrails before scorer changes ship.

## Current State

The project now has a no-fine-tuning external-memory path:

- External dataset adapters normalize records into the shared JSONL schema.
- `ingest-external-scoring-datasets` downloads public direct-link datasets, normalizes them, and builds scoring memory in one command.
- Tiny smoke fixtures prove each adapter path without committing full raw datasets.
- `build-scoring-memory --dimension auto` builds lexical scoring memory from normalized records.
- `score-dimensions-with-memory` returns `llm_score`, `memory_prior`, `final_score`, source, and retrieved examples.
- `run-scoring-memory-suite` generates benchmark and guardrail reports.
- The demo fixture now shows all six product dimensions as memory-backed.

Latest full-lite ingestion run:

- Date: 2026-06-20
- Ready datasets: 8
- Blocked / metadata-only datasets: 6
- Normalized records: 73,193
- Scoring-memory records: 73,193
- Raw data location: `data/external/<dataset>/` (ignored by Git)
- Normalized memory location: `data/normalized/` (ignored by Git)

## Product Scoring Dimensions

| Dimension | Wired external sources | Current use |
|---|---|---|
| Specificity | ReAct specificity fixture | Six-dimensional score memory |
| Substantiation | SubstanReview, ReviewCritique | Six-dimensional score memory |
| Actionability | ReAct, BetterPR | Six-dimensional score memory |
| Consensus / conflict | ContraSciView adapter, RevCI fixture | Six-dimensional score memory |
| Rebuttal robustness | DISAPERE, RbtAct, Re2 | Six-dimensional score memory |
| Professionalism | PolitePEER | Six-dimensional score memory |

## Full-Lite Ingestion Status

| Dataset | Status | Records | Dimension(s) | Notes |
|---|---|---:|---|---|
| ReAct | Ready | 1,250 | actionability | Public CSV downloaded and normalized |
| BetterPR | Ready | 1,516 | actionability | Public `toxicbert.csv` connected; Apple Numbers source remains a conversion task |
| SubstanReview | Ready | 2,777 | substantiation | Public train/test JSONL connected; span labels are converted into claim/evidence examples |
| PolitePEER | Ready | 2,500 | professionalism | Public full CSV connected |
| ContraSciView | Ready | 47,975 | consensus_conflict | Public annotated CSV connected |
| DISAPERE | Ready | 4,463 | rebuttal_robustness | Public ZIP connected; review/rebuttal alignments are converted into robustness labels |
| APE | Ready | 9,166 | rebuttal_alignment | Public ZIP connected as review-comment to rebuttal argument pairs |
| ARIES | Ready | 3,546 | revision_alignment | Public S3 annotation files connected; full `paper_edits` remains skipped for this phase |
| ReviewCritique | Blocked | 0 | substantiation | No stable public raw artifact URL found in this pass |
| RevCI | Blocked | 0 | consensus_conflict | Paper is public, but raw artifact URL is not confirmed |
| RbtAct | Blocked | 0 | rebuttal_robustness, actionability | RMR-75K raw artifact URL is not confirmed |
| AMPERE | Blocked | 0 | argument_role | Raw artifact URL is not confirmed |
| ASAP-Review / ReviewAdvisor | Blocked | 0 | review_aspect | Requires Google Drive download flow |
| Re2 | Blocked | 0 | rebuttal_robustness | Anonymous repository landing page found; direct subset URL is not confirmed |

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
- `src/secondopinion/external_dataset_ingestion.py`
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

Full-lite ingestion outputs:

- `data/validation/external_full_lite_ingestion_manifest_v0.1.json`
- `reports/validation/external_full_lite_ingestion_v0.1.md`
- `data/validation/external_full_lite_scoring_guardrail_v0.1.json`
- `reports/validation/external_full_lite_scoring_guardrail_v0.1.md`
- `reports/validation/external_full_lite_scoring_suite_v0.1.md`

The full scoring suite JSON is intentionally ignored because it contains per-record rows and is too large for Git.

## Guardrail Snapshot

The expanded smoke suite currently has:

- Records: 28
- Dimensions: 10
- Overall accuracy: 0.7500
- Overall macro F1: 0.6987
- Guardrail status: pass

This is a regression guardrail for adapter/scoring-memory behavior. It is not a claim that the tiny smoke fixtures are a real benchmark of reviewer quality.

The full-lite suite currently has:

- Records: 73,193
- Dimensions: 7
- Overall accuracy: 0.3949
- Overall macro F1: 0.7385
- Guardrail status: pass

This full-lite suite records the current proxy-label baseline. The low overall accuracy is mostly driven by simple proxy predictions for actionability and ContraSciView; it is not the final reviewer-scoring model quality.

## Current Limits

- Direct-link public datasets in the first pass have been downloaded locally under `data/external/<dataset>/`.
- Raw and normalized full-lite data remain out of Git.
- Current retrieval is lexical and dependency-light; embedding retrieval is still a later upgrade.
- No model has been fine-tuned.
- ReviewCritique, RevCI, RbtAct, AMPERE, ASAP-Review, and Re2 still need stable raw artifact access before they can move beyond metadata-only entries.
- DEFEND, HedgePeer, COMPARE, NLPeer, PeerRead, MOPRD, and PeerSum are still not wired into scoring memory.
- Structural/lifecycle dimensions are available as memory, but the default product flow remains: score six product dimensions first, then triage.
