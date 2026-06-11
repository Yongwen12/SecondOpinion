# Evidence Chain Pseudo-Expert Calibration

- Tasks: 150
- Labels: 150
- Exact match rate: 12.0%

## Field Match Rates

| Field | Match rate |
| --- | ---: |
| claim_extraction_correct | 100.0% |
| claim_grounded | 100.0% |
| claim_importance | 100.0% |
| evidence_supports_claim | 100.0% |
| expert_confidence | 100.0% |
| rebuttal_addresses_claim | 26.7% |
| recommended_action | 38.0% |

## Label Counts

- `recommended_action_counts`: `{"clarify": 93, "must_address": 57}`
- `rebuttal_address_counts`: `{"generic_or_unclear": 36, "not_addressed": 26, "partially_addressed": 85, "resolved": 3}`
- `evidence_support_counts`: `{"insufficient": 150}`

## Example Disagreements

- `task_0b976a0be36b` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "not_addressed", "recommended_action": "must_address"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "must_address"}
- `task_b1b3bbb6cf2c` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
- `task_389338f26c25` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
- `task_5eaee46caf65` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
- `task_ff9aa18ec35a` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "clarify"}
- `task_9e5c227a2d99` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
- `task_f560b26ec726` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "medium", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "clarify"}
- `task_7117c141d219` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "clarify"}
- `task_0b4fa87e72ef` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "clarify"}
- `task_43f2498b8e3c` system={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "generic_or_unclear", "recommended_action": "provide_evidence"} pseudo={"claim_extraction_correct": "yes", "claim_grounded": "yes", "claim_importance": "high", "evidence_supports_claim": "insufficient", "expert_confidence": "medium", "rebuttal_addresses_claim": "partially_addressed", "recommended_action": "clarify"}
