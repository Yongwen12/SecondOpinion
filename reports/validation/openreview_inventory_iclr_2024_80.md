# OpenReview Data Inventory

- Snapshot: `20260522T083133Z`
- Venue/year: `ICLR 2024`
- Papers: 80
- Replies: 971

## Metric Feasibility

| Metric | Papers | Rate | Status |
| --- | ---: | ---: | --- |
| `claim_grounding` | 72 | 90.0% | `strong` |
| `concern_survival_decision_comment` | 0 | 0.0% | `not_available` |
| `concern_survival_meta_or_decision` | 53 | 66.2% | `usable` |
| `concern_survival_meta_review` | 53 | 66.2% | `usable` |
| `confidence_calibration` | 72 | 90.0% | `strong` |
| `inter_review_consensus` | 72 | 90.0% | `strong` |
| `post_rebuttal_discussion_followup` | 35 | 43.8% | `usable` |
| `post_rebuttal_review_update_proxy` | 30 | 37.5% | `limited` |
| `rating_text_calibration` | 72 | 90.0% | `strong` |
| `rebuttal_alignment` | 56 | 70.0% | `usable` |
| `reviewer_discussion_followup` | 36 | 45.0% | `usable` |

## Availability

| Signal | Papers | Rate |
| --- | ---: | ---: |
| `has_author_response` | 56 | 70.0% |
| `has_confidence` | 72 | 90.0% |
| `has_decision_label` | 53 | 66.2% |
| `has_decision_note` | 53 | 66.2% |
| `has_meta_review` | 53 | 66.2% |
| `has_meta_review_text` | 53 | 66.2% |
| `has_official_comments` | 36 | 45.0% |
| `has_post_rebuttal_review_update` | 30 | 37.5% |
| `has_post_rebuttal_reviewer_comments` | 35 | 43.8% |
| `has_ratings` | 72 | 90.0% |
| `has_reviewer_or_ac_discussion` | 36 | 45.0% |
| `has_reviews` | 72 | 90.0% |
| `has_two_or_more_reviews` | 72 | 90.0% |

## Note Types

| Type | Count |
| --- | ---: |
| `author_response` | 489 |
| `decision` | 53 |
| `meta_review` | 53 |
| `official_comment` | 94 |
| `official_review` | 279 |
| `other` | 3 |

## Recommended Validation Tracks

- `Concern Survival`: use claim overlap with meta-review as the first measurable downstream proxy.
- `Rebuttal Alignment`: measure whether extracted claims are addressed by author responses.
- `Post-Rebuttal Follow-Up`: use reviewer/AC comments after rebuttal as a smaller but high-value signal.
- `Inter-Review Consensus`: measure whether independent reviewers raise similar claims.

## Papers With Rich Follow-Up

- `rGvDRT4Z60`: FairPATE: Exposing the Pareto Frontier of Fairness, Privacy, Accuracy, and Coverage (responses=15, reviewer/AC comments=12, post-rebuttal comments=12, decision=Reject)
- `UVSKuh9eK5`: CLIP Exhibits Improved Compositional Generalization Through Representation Disentanglement (responses=14, reviewer/AC comments=8, post-rebuttal comments=8, decision=Reject)
- `AZGIwqCyYY`: Towards Cross Domain Generalization of Hamiltonian Representation via Meta Learning (responses=13, reviewer/AC comments=5, post-rebuttal comments=5, decision=Accept (poster))
- `xibcBSuuq0`: Do not Start with Trembling Hands: Improving Multi-agent Reinforcement Learning with Stable Prefix Policy (responses=9, reviewer/AC comments=5, post-rebuttal comments=5, decision=Reject)
- `kmn0BhQk7p`: Beyond Memorization: Violating Privacy via Inference with Large Language Models (responses=14, reviewer/AC comments=4, post-rebuttal comments=4, decision=Accept (spotlight))
- `rp5vfyp5Np`: BATTLE: Towards Behavior-oriented Adversarial Attacks against Deep Reinforcement Learning (responses=8, reviewer/AC comments=4, post-rebuttal comments=4, decision=Reject)
- `SLw9fp4yI6`: Controlled Text Generation via Language Model Arithmetic (responses=7, reviewer/AC comments=4, post-rebuttal comments=4, decision=Accept (spotlight))
- `B0wJ5oCPdB`: Chain-of-Symbol Prompting for Spatial Relationships in Large Language Models (responses=7, reviewer/AC comments=4, post-rebuttal comments=4, decision=Reject)
- `eUgS9Ig8JG`: SaNN: Simple Yet Powerful Simplicial-aware Neural Networks (responses=28, reviewer/AC comments=3, post-rebuttal comments=3, decision=Accept (spotlight))
- `eepoE7iLpL`: Enhancing Neural Subset Selection: Integrating Background Information into Set Representations (responses=18, reviewer/AC comments=3, post-rebuttal comments=3, decision=Accept (poster))
