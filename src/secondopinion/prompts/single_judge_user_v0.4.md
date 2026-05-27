Return a structured expert assessment for this reviewer point.

Output rules:
- quoted_manuscript_evidence must be a short exact quote or close excerpt from retrieved evidence when available.
- Do not use high confidence for evidence-limited, vague, specialist-context, novelty, theory, or field-consensus conclusions.
- Keep reasoning_summary concise and evidence-grounded.
- second_opinion_take must be user-facing and must not expose internal workflow or model details.

Scoring guidance:
- support_score is 0-100. For comments, suggestions, and score justifications, 0 means not supported by supplied evidence and 100 means strongly supported.
- For questions, support_score summarizes overall usefulness, answer_coverage_score says how much the manuscript already answers the question, and question_value_score says how valuable the question is as a review point.
- professionalism_score, specificity_score, helpfulness_score, and fairness_score are 0-100.

Rebuttal guidance options:
- priority: high, medium, or low.
- strategy: acknowledge_and_clarify, cite_existing_evidence, concede_and_fix, add_experiment_or_analysis, explain_scope, challenge_politely, or seek_expert_context.
- suggested_response should tell the author what to do next.
- evidence_to_cite should list supplied manuscript sections or passages to cite.
- risks_to_avoid should list mistakes that would weaken the rebuttal.

Audit input JSON:
{{audit_input_json}}
