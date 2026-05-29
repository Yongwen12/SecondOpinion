# Reviewer Reliability Calibration

- Papers: 80
- Reviews: 205
- Claims: 854
- Mean review reliability: 75.8%
- Mean LLM-calibrated reliability: 76.5%
- Mean LLM-calibrated delta: +0.006

## Core Signals

| Signal | Value |
| --- | ---: |
| Mean inter-review consensus rate | 81.9% |
| Mean rebuttal addressed rate | 81.8% |
| Mean LLM rebuttal label coverage | 13.7% |
| Mean LLM rebuttal addressed rate | 11.1% |
| Mean LLM rebuttal resolved rate | 0.7% |
| Mean meta-review uptake rate | 41.6% |

## Label Counts

- `rating_calibration_counts`: `{"calibrated_to_claim_signals": 123, "harsher_than_claim_signals": 48, "more_lenient_than_claim_signals": 34}`
- `confidence_calibration_counts`: `{"confidence_reasonable": 188, "possibly_overconfident": 2, "possibly_underconfident": 15}`
- `reviewer_style_counts`: `{"high_signal_review": 115, "mixed_signal_review": 8, "over_harsh_proxy": 48, "over_lenient_proxy": 34}`
- `claim_consensus_counts`: `{"none": 145, "partial": 508, "strong": 201}`
- `claim_rebuttal_resolution_counts`: `{"addressed_unclear_resolution": 596, "likely_resolved_or_answered": 92, "not_addressed": 166}`
- `claim_llm_rebuttal_response_counts`: `{"generic_or_unclear": 38, "not_addressed": 50, "specifically_addressed": 32}`
- `claim_llm_rebuttal_effect_counts`: `{"does_not_address": 66, "partially_addresses": 39, "resolved_or_weakened": 2, "unclear": 13}`

## Example Reviews

### High Reliability Reviews
- `7NCqEyHLUY` paper=`9ceadCJY4B` score=0.973 rating_gap=1.227 style=`high_signal_review`
- `Ait2z7EwaE` paper=`ApjY32f3Xr` score=0.952 rating_gap=2.24 style=`over_lenient_proxy`
- `W8u5ZMVoLw` paper=`lNIj5FdXsC` score=0.943 rating_gap=1.196 style=`high_signal_review`
- `Z2Yp4ywhAo` paper=`IefMMX12yk` score=0.931 rating_gap=0.929 style=`high_signal_review`
- `OtNzsmJtSr` paper=`23OEmHVkpq` score=0.928 rating_gap=1.036 style=`high_signal_review`
- `zOdvCZoGGo` paper=`pYmQId95iR` score=0.925 rating_gap=-0.337 style=`high_signal_review`
- `S3IqtlOGLT` paper=`10eQ4Cfh8p` score=0.925 rating_gap=-0.964 style=`high_signal_review`
- `sDdpyJppNR` paper=`7vVWiCrFnd` score=0.920 rating_gap=4.502 style=`over_lenient_proxy`
### Low Reliability Reviews
- `tAmKnN5JGR` paper=`tmsqb6WpLz` score=0.134 rating_gap=-3.5 style=`over_harsh_proxy`
- `U6gQ8fElik` paper=`lNIj5FdXsC` score=0.146 rating_gap=-2.5 style=`over_harsh_proxy`
- `4ROQKJsUJM` paper=`E5CMyG6jl0` score=0.181 rating_gap=-0.5 style=`mixed_signal_review`
- `TzMwvS942k` paper=`i8PjQT3Uig` score=0.501 rating_gap=0.28 style=`mixed_signal_review`
- `YOWwslT66t` paper=`bDWXhzZT40` score=0.545 rating_gap=-1.16 style=`mixed_signal_review`
- `EjhiYaDJAD` paper=`b0IRscfEOb` score=0.556 rating_gap=-2.188 style=`over_harsh_proxy`
- `5Yq0QwTe4B` paper=`yacRhge4zQ` score=0.590 rating_gap=-1.689 style=`over_harsh_proxy`
- `UHH9GGKVNC` paper=`9ceadCJY4B` score=0.591 rating_gap=-0.201 style=`mixed_signal_review`