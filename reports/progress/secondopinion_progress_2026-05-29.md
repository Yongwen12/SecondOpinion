# SecondOpinion Progress Report - 2026-05-29

## Executive Summary

SecondOpinion has moved from a basic review-audit prototype into a measurable reviewer-claim evaluation system. The current system can extract reviewer claims, verify that each claim is grounded in the original review, attach paper/rebuttal/external evidence, and evaluate whether reviewer concerns survive across the review lifecycle.

The most important product insight is that we are no longer only judging papers. We can also score the reliability, robustness, and influence of reviewer comments themselves.

## Current System Framework

The current pipeline has seven main layers:

1. Data ingestion
   - OpenReview snapshot normalization.
   - Public ICLR 2024 sample/snapshot support.
   - PDF evidence store support for paper text chunks.

2. Reviewer claim extraction
   - Extracts concrete claims from weaknesses, questions, review text, and selected strength/summary fields.
   - Filters neutral summaries and pure praise.
   - Preserves source fields and source text for downstream grounding.

3. Grounding validation
   - Checks whether every extracted claim can be traced back to the original review.
   - Upgraded from sentence-index-only grounding to more stable location metadata, including character offsets and paragraph/bullet context.
   - This is the P0 quality gate: without grounding, later reviewer-quality metrics are not trustworthy.

4. Evidence collection
   - Internal evidence: paper text/PDF chunks and author rebuttal.
   - External evidence: venue guideline provider and OpenAlex scholarly metadata provider.
   - Supports offline deterministic runs and online OpenAlex enrichment.
   - First version avoids expensive full-text crawling by default.

5. Concern survival and historical case memory
   - Measures whether a reviewer claim survives into meta-review / AC discussion.
   - Builds calibrated high-confidence examples.
   - Exports RAG memory, SFT examples, and preference-style examples.
   - Closed-book RAG validation shows that historical cases improve claim-quality judgment without giving the model the answer directly.

6. Reviewer calibration
   - Measures reviewer reliability using:
     - claim grounding
     - inter-reviewer consensus
     - rating-text calibration
     - confidence calibration
     - rebuttal resolution
     - post-rebuttal discussion follow-up
     - meta-review uptake
   - Adds LLM-calibrated labels for rebuttal resolution and inter-reviewer consensus.

7. Claim lifecycle robustness
   - Newest addition.
   - Scores whether a reviewer claim remains robust across the full lifecycle:
     - grounded in original review
     - supported by other reviewers
     - not genuinely resolved by author rebuttal
     - followed up after rebuttal
     - taken up in meta-review
   - Produces claim-level, review-level, and dataset-level robustness metrics.

## Key Validation Results

Dataset: ICLR 2024 public OpenReview sample, 80 papers.

Reviewer calibration v0.3 lifecycle report:

| Metric | Result |
| --- | ---: |
| Papers | 80 |
| Reviews | 205 |
| Claims | 854 |
| Mean review reliability | 75.8% |
| Mean LLM-calibrated review reliability | 74.6% |
| Mean inter-review consensus rate | 81.9% |
| Mean meta-review uptake rate | 41.6% |
| Mean claim lifecycle robustness | 57.5% |
| High-robustness claims | 97 |
| Medium-robustness claims | 650 |
| Low-robustness claims | 107 |

LLM-calibrated rebuttal resolution:

| Label | Count |
| --- | ---: |
| not_addressed | 105 |
| generic_or_unclear | 70 |
| specifically_addressed | 63 |
| likely_resolved | 2 |

LLM-calibrated rebuttal effect:

| Label | Count |
| --- | ---: |
| does_not_address | 128 |
| partially_addresses | 73 |
| unclear | 31 |
| resolved_or_weakened | 8 |

This supports an important early finding: many author responses appear responsive at a lexical level, but only a small fraction clearly resolve or weaken the reviewer concern.

## RAG Validation Result

The historical case-memory RAG direction has an initial measurable signal.

After redesigning the experiment to avoid open-book leakage, the closed-book strict ablation showed that RAG improves the model's ability to predict whether a reviewer concern is likely to be reflected/accepted later by AC or meta-review. This validates the idea that prior calibrated review cases can help judge new reviewer claims.

Current interpretation:

- RAG is not being used to predict paper acceptance directly.
- RAG is being used to improve judgment of reviewer-claim quality and likely influence.
- The best target is reviewer-claim assessment, not acceptance prediction.

## Most Valuable Product Insight So Far

The strongest data-mining value is reviewer-claim robustness.

A concern is robust if it is:

- grounded in the original review,
- semantically supported by other reviewers,
- not actually resolved by the author response,
- still discussed after rebuttal,
- and/or adopted in the meta-review.

This creates a stronger story than simple review scoring:

> SecondOpinion can audit not only papers, but also the quality and influence of peer-review comments.

That is valuable for authors, reviewers, area chairs, and conference/workshop quality control.

## Current Artifacts

Important generated reports:

- `reports/validation/reviewer_calibration_iclr_2024_full_v0.3_lifecycle.md`
- `reports/validation/reviewer_calibration_iclr_2024_full_v0.2.md`
- `reports/validation/rebuttal_resolution_llm_calibration_120.md`
- `reports/validation/rebuttal_resolution_llm_calibration_extra120.md`
- `reports/validation/inter_reviewer_consensus_llm_calibration_120.md`
- `reports/validation/concern_survival_iclr_2024_full.md`
- `reports/validation/grounding_iclr_2024_200.md`
- `reports/validation/openreview_inventory_iclr_2024_80.md`

Important generated validation data:

- `data/validation/reviewer_calibration_iclr_2024_full_v0.3_lifecycle.json`
- `data/validation/rebuttal_resolution_llm_merged_120.jsonl`
- `data/validation/rebuttal_resolution_llm_merged_extra120.jsonl`
- `data/validation/inter_reviewer_consensus_llm_merged_120.jsonl`
- `data/validation/concern_survival_balanced_high_confidence_gold_150.jsonl`
- `data/validation/concern_survival_gold_expansion_llm_merged_500.jsonl`

## Engineering Status

Test status:

- Full test suite passed: 89 passed.

Major implemented modules:

- `src/secondopinion/external_evidence.py`
- `src/secondopinion/external_providers/openalex.py`
- `src/secondopinion/external_providers/venue_guidelines.py`
- `src/secondopinion/grounding_validation.py`
- `src/secondopinion/concern_survival.py`
- `src/secondopinion/concern_calibration.py`
- `src/secondopinion/rag_validation.py`
- `src/secondopinion/reviewer_calibration.py`
- CLI integrations in `src/secondopinion/cli.py`

## Known Limitations

1. Current concern-survival and consensus matching still include deterministic lexical proxy components.
2. LLM calibration coverage is partial, not full-dataset gold labeling.
3. Reviewer identity aggregation is not available in this public OpenReview snapshot because reviewer signatures appear anonymized per submission.
4. Decision comments in this dataset mostly contain accept/reject labels without explanatory text, so decision-comment survival is not currently useful.
5. Raw OpenReview snapshots and PDFs are intentionally kept out of Git by `.gitignore`.

## Recommended Next Steps

1. Expand LLM calibration coverage for lifecycle robustness.
2. Build a small human/LLM-audited gold set focused on:
   - high robustness claim
   - low robustness claim
   - rebuttal genuinely resolved
   - rebuttal only generic/partial
3. Add product-facing reviewer claim cards:
   - original claim
   - evidence grounding
   - author response assessment
   - lifecycle robustness score
   - recommended author action
4. Use lifecycle robustness as the core evaluation target for RAG and future fine-tuning.
5. Prepare an investor-facing demo around one paper showing how claims move through the lifecycle.

