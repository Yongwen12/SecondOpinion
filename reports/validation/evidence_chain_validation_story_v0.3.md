# Evidence Chain Validation Story

## Product Demo Readiness

The current evidence-chain demo covers 4 reviews and 24 reviewer claims for one representative ICLR paper. 13 claims are high-priority or must-address rebuttal items.

- Priority mix: `{"high": 12, "low": 1, "medium": 10, "must": 1}`
- Mean reviewer reliability: 73.3%
- Mean lifecycle robustness: 48.5%

## Benchmark Status

The current benchmark packet contains 300 claim items across 38 reviewer-calibration-derived papers, with three ablation views: `review_only`, `review_manuscript`, and `full_evidence_chain`.

This calibration-derived benchmark is strong for lifecycle, rebuttal, consensus, and meta-review validation; manuscript/external evidence ablations still require more PDF-backed audit runs.

## Pseudo-Expert Calibration

- Pseudo-expert labels: 150
- Exact agreement with system-derived expected labels: 12.0%
- Recommended-action agreement: 38.0%
- Rebuttal-resolution agreement: 26.7%
- Evidence-support agreement: 100.0%

## Interpretation

- The UI now supports the product story: identify dangerous reviewer claims, explain the evidence chain, and recommend response strategy.
- The benchmark packet now makes evidence-chain ablations explicit, so future LLM or human labels can measure whether added evidence improves judgment.
- Pseudo-expert labels are not gold labels; they are a calibration harness and sanity check before spending money on experts.
- Current pseudo-expert disagreement on evidence support is useful: it shows where stance-based system outputs and evidence-score-based review differ, which is exactly the calibration target for expert labels.
- The next real validation step is to replace pseudo-expert labels with 200-300 human/expert labels on the same schema.

## Recommended Investor Demo Script

1. Open the evidence-chain reader and select the demo paper.
2. Show the top high-priority claim and its score breakdown.
3. Expand the evidence chain: reviewer wording, manuscript evidence, rebuttal, consensus, and meta-review uptake.
4. Switch to the rebuttal workspace and show how SecondOpinion prioritizes what the author should answer first.
5. Close with the validation path: benchmark ablations and expert labels.
