# OpenReview Data Inventory

- Snapshot: `20260621T083053Z`
- Venue/year: `ICLR 2022`
- Papers: 1000
- Replies: 14593

## Metric Feasibility

| Metric | Papers | Rate | Status |
| --- | ---: | ---: | --- |
| `claim_grounding` | 1000 | 100.0% | `strong` |
| `concern_survival_decision_comment` | 1000 | 100.0% | `strong` |
| `concern_survival_meta_or_decision` | 1000 | 100.0% | `strong` |
| `concern_survival_meta_review` | 0 | 0.0% | `not_available` |
| `confidence_calibration` | 1000 | 100.0% | `strong` |
| `inter_review_consensus` | 1000 | 100.0% | `strong` |
| `post_rebuttal_discussion_followup` | 704 | 70.4% | `usable` |
| `post_rebuttal_review_update_proxy` | 611 | 61.1% | `usable` |
| `rating_text_calibration` | 1000 | 100.0% | `strong` |
| `rebuttal_alignment` | 900 | 90.0% | `strong` |
| `reviewer_discussion_followup` | 712 | 71.2% | `usable` |

## Availability

| Signal | Papers | Rate |
| --- | ---: | ---: |
| `has_author_response` | 900 | 90.0% |
| `has_confidence` | 1000 | 100.0% |
| `has_decision_comment_text` | 1000 | 100.0% |
| `has_decision_label` | 1000 | 100.0% |
| `has_decision_note` | 1000 | 100.0% |
| `has_official_comments` | 712 | 71.2% |
| `has_post_rebuttal_review_update` | 611 | 61.1% |
| `has_post_rebuttal_reviewer_comments` | 704 | 70.4% |
| `has_ratings` | 1000 | 100.0% |
| `has_reviewer_or_ac_discussion` | 712 | 71.2% |
| `has_reviews` | 1000 | 100.0% |
| `has_two_or_more_reviews` | 1000 | 100.0% |

## Note Types

| Type | Count |
| --- | ---: |
| `author_response` | 7554 |
| `decision` | 1000 |
| `official_comment` | 1975 |
| `official_review` | 3899 |
| `other` | 164 |
| `withdrawal` | 1 |

## Recommended Validation Tracks

- `Rebuttal Alignment`: measure whether extracted claims are addressed by author responses.
- `Post-Rebuttal Follow-Up`: use reviewer/AC comments after rebuttal as a smaller but high-value signal.
- `Inter-Review Consensus`: measure whether independent reviewers raise similar claims.

## Papers With Rich Follow-Up

- `KJztlfGPdwW`: Rethinking Goal-Conditioned Supervised Learning and Its Connection to Offline RL (responses=22, reviewer/AC comments=14, post-rebuttal comments=14, decision=Accept (Poster))
- `BrFIKuxrZE`: Fair Normalizing Flows (responses=13, reviewer/AC comments=14, post-rebuttal comments=14, decision=Accept (Poster))
- `-llS6TiOew`: Fairness in Representation for Multilingual NLP: Insights from Controlled Experiments on Conditional Language Modeling (responses=39, reviewer/AC comments=13, post-rebuttal comments=13, decision=Accept (Spotlight))
- `fJIrkNKGBNI`: Effective Polynomial Filter Adaptation for Graph Neural Networks (responses=39, reviewer/AC comments=12, post-rebuttal comments=12, decision=Reject)
- `gdegUuC_fxR`: Hessian-Free High-Resolution Nesterov Acceleration for Sampling (responses=19, reviewer/AC comments=11, post-rebuttal comments=11, decision=Reject)
- `hcQHRHKfN_`: Continuously Discovering Novel Strategies via Reward-Switching Policy Optimization (responses=17, reviewer/AC comments=11, post-rebuttal comments=11, decision=Accept (Poster))
- `Vog_3GXsgmb`: Discovering Nonlinear PDEs from Scarce Data with Physics-encoded Learning (responses=26, reviewer/AC comments=10, post-rebuttal comments=10, decision=Accept (Poster))
- `XIZaWGCPl0b`: Tesseract: Gradient Flip Score to Secure Federated Learning against Model Poisoning Attacks (responses=18, reviewer/AC comments=10, post-rebuttal comments=10, decision=Reject)
- `ZOcX-eybqoL`: Generalisation in Lifelong Reinforcement Learning through Logical Composition (responses=24, reviewer/AC comments=9, post-rebuttal comments=9, decision=Accept (Poster))
- `QguFu30t0d`: FedGEMS: Federated Learning of Larger Server Models via Selective Knowledge Fusion (responses=20, reviewer/AC comments=9, post-rebuttal comments=9, decision=Reject)
