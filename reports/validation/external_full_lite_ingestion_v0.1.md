# External Scoring Dataset Ingestion

- Schema: `external-full-lite-ingestion-v0.1`
- Generated at: `2026-06-20T14:18:42.035446+00:00`
- Selected datasets: 14
- Normalized records: 73193
- Scoring-memory records: 73193
- Ready datasets: 8
- Blocked datasets: 6

## Dataset Status

| Dataset | Batch | Mode | Status | Records | Dimensions | Use |
| --- | --- | --- | --- | ---: | --- | --- |
| ReAct | first | full-lite | `ready` | 1250 | `actionability` | Constructive/actionable comment examples for the actionability prior. |
| BetterPR | first | full-lite | `ready` | 1516 | `actionability` | Constructive vs non-constructive comments for actionability and reviewer helpfulness. |
| SubstanReview | first | full-lite | `ready` | 2777 | `substantiation` | Evaluation/justification spans become substantiated vs unsupported reviewer claims. |
| ReviewCritique | first | metadata-only | `blocked` | 0 | `substantiation` | Planned deficiency labels would strengthen substantiation/deficiency priors. |
| PolitePEER | first | full-lite | `ready` | 2500 | `professionalism` | Tone labels turn professionalism from LLM-only into an external-data-backed prior. |
| ContraSciView | first | full-lite | `ready` | 47975 | `consensus_conflict` | Contradictory review-pair labels support consensus/conflict guardrails. |
| RevCI | first | metadata-only | `blocked` | 0 | `consensus_conflict` | Would add evidence-level contradiction intensity beyond binary conflict. |
| DISAPERE | first | full-lite | `ready` | 4463 | `rebuttal_robustness` | Review-sentence/rebuttal-sentence alignments support rebuttal robustness and response specificity. |
| RbtAct | second | metadata-only | `blocked` | 0 | `rebuttal_robustness`, `actionability` | Would connect review actionability to author uptake and revision impact. |
| APE | second | semi-connect | `ready` | 9166 | `rebuttal_alignment` | Argument-pair labels support review-comment to rebuttal alignment. |
| ARIES | second | semi-connect | `ready` | 3546 | `revision_alignment` | Comment-to-edit links open a lightweight path from review concerns to revision alignment. |
| AMPERE | second | metadata-only | `blocked` | 0 | `argument_role` | Would tag review-comment argument roles such as request, evaluation, fact, and reference. |
| ASAP-Review | second | metadata-only | `blocked` | 0 | `review_aspect` | Would add aspect labels for soundness, novelty, comparison, presentation, and related review facets. |
| Re2 | re2 | metadata-only | `blocked` | 0 | `rebuttal_robustness` | Strategic review/rebuttal subset for multi-turn rebuttal robustness once a stable artifact is reachable. |

## Blockers

- **ReviewCritique**: No stable public raw dataset URL was found during the 2026-06-20 pass.
- **RevCI**: Paper is public, but no stable raw artifact URL was found during the 2026-06-20 pass.
- **RbtAct**: No stable public RMR-75K raw artifact URL was found during the 2026-06-20 pass.
- **AMPERE**: No stable public raw dataset URL was found during the 2026-06-20 pass.
- **ASAP-Review**: Requires Google Drive download flow; not pulled in the no-dependency public-URL ingester.
- **Re2**: Dataset URL is an anonymous repository landing page; no direct raw subset URL was confirmed in this pass.

## Scoring Use

- The connected records are normalized into the shared external scoring schema.
- The CLI can build lexical scoring memory from the normalized corpus without fine-tuning.
- Blocked datasets remain represented in the manifest so the backlog is explicit and reproducible.
