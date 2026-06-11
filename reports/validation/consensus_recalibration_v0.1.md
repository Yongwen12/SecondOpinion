# Consensus Recalibration

## Scope

- Claims: 854
- Claims with LLM consensus labels: 120

## Mode Summary

| Mode | Claims | Mean lifecycle | Median lifecycle | Mean consensus | High | Medium | Low |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `current_hybrid` | 854 | 57.5% | 56.5% | 53.3% | 97 | 650 | 107 |
| `strict_same_only_hybrid` | 854 | 56.6% | 55.6% | 48.8% | 94 | 631 | 129 |
| `current_labeled_only` | 120 | 54.5% | 55.4% | 38.5% | 5 | 90 | 25 |
| `strict_same_only_labeled` | 120 | 48.8% | 48.6% | 6.7% | 2 | 71 | 47 |

## Comparisons

### `strict_hybrid_vs_current_all_claims`

- Claims compared: 854
- Mean score delta: -0.8%
- Mean absolute score delta: 0.8%
- Label changes: 25 (2.9%)
- Label-change counts: `{"high->medium": 3, "medium->low": 22}`
- Mean signal deltas: `{"consensus": -0.0447, "discussion_followup": 0.0, "grounding": 0.0, "meta_review_uptake": 0.0, "rebuttal_robustness": 0.0, "specificity": 0.0}`

### `strict_labeled_vs_current_labeled`

- Claims compared: 120
- Mean score delta: -5.7%
- Mean absolute score delta: 5.7%
- Label changes: 25 (20.8%)
- Label-change counts: `{"high->medium": 3, "medium->low": 22}`
- Mean signal deltas: `{"consensus": -0.3183, "discussion_followup": 0.0, "grounding": 0.0, "meta_review_uptake": 0.0, "rebuttal_robustness": 0.0, "specificity": 0.0}`

## Diagnostics

- LLM-labeled claims: 120
- Proxy says partial/strong: 80.0%
- Current related/same support rate: 64.2%
- Strict same-concern support rate: 6.7%
- Related-but-different demotions: 69 (57.5%)
- Proxy-positive but not-same claims: 27
- Proxy-positive but related-different claims: 61
- Proxy labels: `{"none": 24, "partial": 54, "strong": 42}`
- LLM labels: `{"not_same_concern": 42, "related_but_different": 69, "same_concern": 8, "unsure": 1}`

## Example Demotions

- `cXs5md5wAq:2gTtKikoba:0` proxy=`partial`: The methodological contribution is limited as the presented work is mostly implementing GNNs for microbial steady state predictions.
- `rhgIgTSSxW:LGzAT6gNeL:0` proxy=`partial`: Paper doesn't go into detail describing differences with prior deep learning-based tabular methods. What might explain the performance differences?
- `rhgIgTSSxW:CEBB2izG6I:3` proxy=`partial`: Is TabR applicable to categorical features? It seems like the paper only considers continuous features.
- `kKRbAY4CXv:eSJOZmZeDG:1` proxy=`strong`: The method only works on semi-linear PDEs. This is actually a very strong assumption and limitation. The authors should discuss the extension to nonlinear PDEs.
- `ApjY32f3Xr:C4sqXJNESI:4` proxy=`partial`: How were boundary and initial conditions handled to ensure satisfaction in experiments?
- `eUgS9Ig8JG:6iCqDrP0HV:0` proxy=`partial`: On several occasions the notion of "non-deep baselines" is used. What is meant by this. Could you clarify what non-deep means here, which methods are these?
- `eUgS9Ig8JG:6iCqDrP0HV:2` proxy=`none`: In section 4. The sentence that starts with "The theorem implies that any arbitrary ..." is extremely long and hard to comprehend. I suggest to split it 2 or 3 sentence to improve readability.
- `qBL04XXex6:1lDRac9ePM:2` proxy=`none`: More analysis or ablation studies are also helpful.

## Notes

- `current_hybrid` mirrors the current lifecycle consensus score: same_concern=1.0, related_but_different=0.55, proxy fallback when no LLM label exists.
- `strict_same_only_hybrid` only treats LLM same_concern as inter-reviewer support; related_but_different, not_same_concern, and unsure all score 0.0.
- This report isolates the consensus leg. Rebuttal, discussion, grounding, specificity, and meta-review uptake use the current lifecycle-ablation scoring logic.
