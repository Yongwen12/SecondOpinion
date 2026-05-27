Extract up to {{max_claims}} auditable reviewer points.

Decision procedure:
1. Read all supplied review fields.
2. Identify candidate criticisms, questions, suggestions, score justifications, and tone concerns.
3. Remove pure praise, neutral summaries, generic background, and duplicate points.
4. Split distinct criticisms into separate reviewer points.
5. For each retained point, copy the exact contiguous source_sentence from the selected source_field.
6. Return strict JSON only.

Review JSON:
{{review_json}}
