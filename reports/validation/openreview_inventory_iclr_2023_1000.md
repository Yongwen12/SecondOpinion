# OpenReview Data Inventory

- Snapshot: `20260621T082818Z`
- Venue/year: `ICLR 2023`
- Papers: 1000
- Replies: 14357

## Metric Feasibility

| Metric | Papers | Rate | Status |
| --- | ---: | ---: | --- |
| `claim_grounding` | 1000 | 100.0% | `strong` |
| `concern_survival_decision_comment` | 0 | 0.0% | `not_available` |
| `concern_survival_meta_or_decision` | 0 | 0.0% | `not_available` |
| `concern_survival_meta_review` | 0 | 0.0% | `not_available` |
| `confidence_calibration` | 1000 | 100.0% | `strong` |
| `inter_review_consensus` | 1000 | 100.0% | `strong` |
| `post_rebuttal_discussion_followup` | 620 | 62.0% | `usable` |
| `post_rebuttal_review_update_proxy` | 564 | 56.4% | `usable` |
| `rating_text_calibration` | 1000 | 100.0% | `strong` |
| `rebuttal_alignment` | 880 | 88.0% | `strong` |
| `reviewer_discussion_followup` | 635 | 63.5% | `usable` |

## Availability

| Signal | Papers | Rate |
| --- | ---: | ---: |
| `has_author_response` | 880 | 88.0% |
| `has_confidence` | 1000 | 100.0% |
| `has_decision_label` | 1000 | 100.0% |
| `has_decision_note` | 1000 | 100.0% |
| `has_official_comments` | 635 | 63.5% |
| `has_post_rebuttal_review_update` | 564 | 56.4% |
| `has_post_rebuttal_reviewer_comments` | 620 | 62.0% |
| `has_ratings` | 1000 | 100.0% |
| `has_reviewer_or_ac_discussion` | 635 | 63.5% |
| `has_reviews` | 1000 | 100.0% |
| `has_two_or_more_reviews` | 1000 | 100.0% |

## Note Types

| Type | Count |
| --- | ---: |
| `author_response` | 7879 |
| `decision` | 1000 |
| `official_comment` | 1611 |
| `official_review` | 3786 |
| `other` | 81 |

## Recommended Validation Tracks

- `Rebuttal Alignment`: measure whether extracted claims are addressed by author responses.
- `Post-Rebuttal Follow-Up`: use reviewer/AC comments after rebuttal as a smaller but high-value signal.
- `Inter-Review Consensus`: measure whether independent reviewers raise similar claims.

## Papers With Rich Follow-Up

- `uvSQ8WhWHQ`: Plansformer: Generating Multi-Domain Symbolic Plans using Transformers (responses=21, reviewer/AC comments=15, post-rebuttal comments=15, decision=Reject)
- `oJpVVGXu9i`: Share Your Representation Only: Guaranteed Improvement of the Privacy-Utility Tradeoff in Federated Learning (responses=24, reviewer/AC comments=12, post-rebuttal comments=12, decision=Accept: poster)
- `cVFD6qE8gnY`: Planning with Sequence Models through Iterative Energy Minimization (responses=16, reviewer/AC comments=12, post-rebuttal comments=12, decision=Accept: poster)
- `ashgrQnYsm`: MBrain: A Multi-channel Self-Supervised Learning Framework for Brain Signals (responses=27, reviewer/AC comments=11, post-rebuttal comments=11, decision=Reject)
- `WzGdBqcBicl`: Understanding and Adopting Rational Behavior by Bellman Score Estimation (responses=20, reviewer/AC comments=11, post-rebuttal comments=11, decision=Accept: notable-top-25%)
- `tmIiMPl4IPa`: Factorized Fourier Neural Operators (responses=17, reviewer/AC comments=11, post-rebuttal comments=10, decision=Accept: poster)
- `5mqFra2ZSuf`: SP2 : A Second Order Stochastic Polyak Method (responses=37, reviewer/AC comments=10, post-rebuttal comments=10, decision=Accept: poster)
- `j3GK3_xZydY`: Revisiting Intrinsic Reward for Exploration in Procedurally Generated Environments (responses=28, reviewer/AC comments=10, post-rebuttal comments=10, decision=Accept: poster)
- `n0okuXMlI7V`: Catastrophic overfitting is a bug but it is caused by features (responses=19, reviewer/AC comments=10, post-rebuttal comments=10, decision=Reject)
- `rmoMvptXK7M`: Gray-Box Gaussian Processes for Automated Reinforcement Learning (responses=14, reviewer/AC comments=10, post-rebuttal comments=10, decision=Accept: poster)
