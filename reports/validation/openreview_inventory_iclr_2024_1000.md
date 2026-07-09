# OpenReview Data Inventory

- Snapshot: `20260621T082900Z`
- Venue/year: `ICLR 2024`
- Papers: 1000
- Replies: 14249

## Metric Feasibility

| Metric | Papers | Rate | Status |
| --- | ---: | ---: | --- |
| `claim_grounding` | 957 | 95.7% | `strong` |
| `concern_survival_decision_comment` | 0 | 0.0% | `not_available` |
| `concern_survival_meta_or_decision` | 787 | 78.7% | `usable` |
| `concern_survival_meta_review` | 787 | 78.7% | `usable` |
| `confidence_calibration` | 957 | 95.7% | `strong` |
| `inter_review_consensus` | 957 | 95.7% | `strong` |
| `post_rebuttal_discussion_followup` | 586 | 58.6% | `usable` |
| `post_rebuttal_review_update_proxy` | 470 | 47.0% | `usable` |
| `rating_text_calibration` | 957 | 95.7% | `strong` |
| `rebuttal_alignment` | 772 | 77.2% | `usable` |
| `reviewer_discussion_followup` | 594 | 59.4% | `usable` |

## Availability

| Signal | Papers | Rate |
| --- | ---: | ---: |
| `has_author_response` | 772 | 77.2% |
| `has_confidence` | 957 | 95.7% |
| `has_decision_label` | 787 | 78.7% |
| `has_decision_note` | 787 | 78.7% |
| `has_meta_review` | 787 | 78.7% |
| `has_meta_review_text` | 787 | 78.7% |
| `has_official_comments` | 594 | 59.4% |
| `has_post_rebuttal_review_update` | 470 | 47.0% |
| `has_post_rebuttal_reviewer_comments` | 586 | 58.6% |
| `has_ratings` | 957 | 95.7% |
| `has_reviewer_or_ac_discussion` | 594 | 59.4% |
| `has_reviews` | 957 | 95.7% |
| `has_two_or_more_reviews` | 957 | 95.7% |

## Note Types

| Type | Count |
| --- | ---: |
| `author_response` | 7198 |
| `decision` | 787 |
| `meta_review` | 788 |
| `official_comment` | 1698 |
| `official_review` | 3729 |
| `other` | 49 |

## Recommended Validation Tracks

- `Concern Survival`: use claim overlap with meta-review as the first measurable downstream proxy.
- `Rebuttal Alignment`: measure whether extracted claims are addressed by author responses.
- `Post-Rebuttal Follow-Up`: use reviewer/AC comments after rebuttal as a smaller but high-value signal.
- `Inter-Review Consensus`: measure whether independent reviewers raise similar claims.

## Papers With Rich Follow-Up

- `li1Z0OQfnA`: On Local Equilibrium in Non-Concave Games (responses=15, reviewer/AC comments=15, post-rebuttal comments=15, decision=Reject)
- `rGvDRT4Z60`: FairPATE: Exposing the Pareto Frontier of Fairness, Privacy, Accuracy, and Coverage (responses=15, reviewer/AC comments=12, post-rebuttal comments=12, decision=Reject)
- `m7aPLHwsLr`: DRSM: De-Randomized Smoothing on Malware Classifier Providing Certified Robustness (responses=37, reviewer/AC comments=11, post-rebuttal comments=11, decision=Accept (poster))
- `kTRGF2JEcx`: Instructing Large Language Models to Identify and Ignore Irrelevant Conditions (responses=27, reviewer/AC comments=11, post-rebuttal comments=11, decision=Reject)
- `f1xnBr4WD6`: Cycle Consistency Driven Object Discovery (responses=23, reviewer/AC comments=10, post-rebuttal comments=10, decision=Accept (poster))
- `EyDPfGy4Wh`: Few Heads are Enough (responses=13, reviewer/AC comments=10, post-rebuttal comments=10, decision=Reject)
- `VaZa8zj0Yw`: Lyfe Agents: generative agents for low-cost real-time social interactions (responses=22, reviewer/AC comments=9, post-rebuttal comments=9, decision=Reject)
- `kIPEyMSdFV`: Reverse Diffusion Monte Carlo (responses=20, reviewer/AC comments=9, post-rebuttal comments=9, decision=Accept (poster))
- `QHVTxso1Is`: Efficient Unsupervised Knowledge Distillation with Space Similarity (responses=22, reviewer/AC comments=8, post-rebuttal comments=8, decision=Reject)
- `BoMvv7ypDF`: Recursive Score Estimation Accelerates Diffusion-Based Monte Carlo (responses=17, reviewer/AC comments=8, post-rebuttal comments=8, decision=Reject)
