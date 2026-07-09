# OpenReview Data Inventory

- Snapshot: `20260621T082946Z`
- Venue/year: `ICLR 2025`
- Papers: 1000
- Replies: 17563

## Metric Feasibility

| Metric | Papers | Rate | Status |
| --- | ---: | ---: | --- |
| `claim_grounding` | 971 | 97.1% | `strong` |
| `concern_survival_decision_comment` | 0 | 0.0% | `not_available` |
| `concern_survival_meta_or_decision` | 750 | 75.0% | `usable` |
| `concern_survival_meta_review` | 750 | 75.0% | `usable` |
| `confidence_calibration` | 971 | 97.1% | `strong` |
| `inter_review_consensus` | 971 | 97.1% | `strong` |
| `post_rebuttal_discussion_followup` | 626 | 62.6% | `usable` |
| `post_rebuttal_review_update_proxy` | 493 | 49.3% | `usable` |
| `rating_text_calibration` | 971 | 97.1% | `strong` |
| `rebuttal_alignment` | 701 | 70.1% | `usable` |
| `reviewer_discussion_followup` | 644 | 64.4% | `usable` |

## Availability

| Signal | Papers | Rate |
| --- | ---: | ---: |
| `has_author_response` | 701 | 70.1% |
| `has_confidence` | 971 | 97.1% |
| `has_decision_label` | 750 | 75.0% |
| `has_decision_note` | 750 | 75.0% |
| `has_meta_review` | 750 | 75.0% |
| `has_meta_review_text` | 750 | 75.0% |
| `has_official_comments` | 644 | 64.4% |
| `has_post_rebuttal_review_update` | 493 | 49.3% |
| `has_post_rebuttal_reviewer_comments` | 626 | 62.6% |
| `has_ratings` | 971 | 97.1% |
| `has_reviewer_or_ac_discussion` | 644 | 64.4% |
| `has_reviews` | 971 | 97.1% |
| `has_two_or_more_reviews` | 971 | 97.1% |

## Note Types

| Type | Count |
| --- | ---: |
| `author_response` | 9424 |
| `decision` | 750 |
| `meta_review` | 750 |
| `official_comment` | 2405 |
| `official_review` | 3926 |
| `other` | 62 |
| `withdrawal` | 246 |

## Recommended Validation Tracks

- `Concern Survival`: use claim overlap with meta-review as the first measurable downstream proxy.
- `Rebuttal Alignment`: measure whether extracted claims are addressed by author responses.
- `Post-Rebuttal Follow-Up`: use reviewer/AC comments after rebuttal as a smaller but high-value signal.
- `Inter-Review Consensus`: measure whether independent reviewers raise similar claims.

## Papers With Rich Follow-Up

- `dML3XGvWmy`: Gödel Agent: A Self-Referential Framework Helps for Recursively Self-Improvement (responses=30, reviewer/AC comments=15, post-rebuttal comments=15, decision=Reject)
- `eks3dGnocX`: How Transformers Solve Propositional Logic Problems: A Mechanistic Analysis (responses=23, reviewer/AC comments=14, post-rebuttal comments=14, decision=Reject)
- `MBBRHDuiwM`: URLOST: Unsupervised Representation Learning without Stationarity or Topology (responses=58, reviewer/AC comments=13, post-rebuttal comments=13, decision=Accept (Poster))
- `0XT3Lg6S2Q`: Efficient Adaptive Filtering for Deformable Image registration (responses=25, reviewer/AC comments=13, post-rebuttal comments=13, decision=Reject)
- `cuFnNExmdq`: UniTST: Effectively Modeling Inter-Series and Intra-Series Dependencies for Multivariate Time Series Forecasting (responses=14, reviewer/AC comments=13, post-rebuttal comments=13, decision=Reject)
- `9ut3QBscB0`: Beyond Standardization – Putting the Normality in Normalization (responses=45, reviewer/AC comments=12, post-rebuttal comments=12, decision=Reject)
- `uClUUJk05H`: Compositional simulation-based inference for time series (responses=16, reviewer/AC comments=12, post-rebuttal comments=12, decision=Accept (Poster))
- `WwmtcGr4lP`: GANDALF: Generative AttentioN based Data Augmentation and predictive modeLing Framework for personalized cancer treatment (responses=28, reviewer/AC comments=11, post-rebuttal comments=11, decision=Accept (Poster))
- `GBIUbwW9D8`: ExACT: Teaching AI Agents to Explore with Reflective-MCTS and Exploratory Learning (responses=30, reviewer/AC comments=10, post-rebuttal comments=10, decision=Accept (Poster))
- `R2834dhBlo`: Neural Interactive Proofs (responses=22, reviewer/AC comments=10, post-rebuttal comments=10, decision=Accept (Poster))
