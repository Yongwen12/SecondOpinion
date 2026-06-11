# Evidence Chain Pseudo-Expert Calibration

- Tasks: 24
- Labels: 24
- Exact match rate: 0.0%

## Field Match Rates

| Field | Match rate |
| --- | ---: |
| claim_extraction_correct | 100.0% |
| claim_grounded | 100.0% |
| claim_importance | 100.0% |
| evidence_supports_claim | 0.0% |
| expert_confidence | 20.8% |
| rebuttal_addresses_claim | 54.2% |
| recommended_action | 100.0% |

## Label Counts

- `recommended_action_counts`: `{"clarify": 10, "deprioritize": 1, "must_address": 1, "provide_evidence": 12}`
- `rebuttal_address_counts`: `{"generic_or_unclear": 8, "not_addressed": 1, "partially_addressed": 14, "resolved": 1}`
- `evidence_support_counts`: `{"contradicts": 2, "mixed": 17, "supports": 5}`

## Example Disagreements

- `task_38ac02f00325` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "mixed", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "provide_evidence"}
- `task_9a364b0b08d5` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "mixed", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "provide_evidence"}
- `task_b656fcd69f85` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "mixed", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "provide_evidence"}
- `task_4c5d0fd55d08` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "supports", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
- `task_3c0bd75b978b` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "high", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "supports", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "provide_evidence"}
- `task_686793da2caf` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "contradicts", "expert_confidence": "high", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"}
- `task_e687ca80c398` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "contradicts", "expert_confidence": "high", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"}
- `task_1eaff550785d` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "mixed", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "provide_evidence"}
- `task_62838b1ddb53` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "mixed", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
- `task_e873148b88da` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "supports", "expert_confidence": "high", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
