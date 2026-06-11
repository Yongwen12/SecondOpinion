# Presentation P0 Checks

## Test 1 - Materiality Proxy x Resolution

- LLM-labeled rebuttal claims: 240
- Importance proxy counts: `{"high": 182, "low": 48, "medium": 10}`
- Response counts: `{"generic_or_unclear": 70, "likely_resolved": 2, "not_addressed": 105, "specifically_addressed": 63}`
- Effect counts: `{"does_not_address": 128, "partially_addresses": 73, "resolved_or_weakened": 8, "unclear": 31}`
- High-importance and unresolved/partial effect: 155 (64.6%)
- Specifically addressed but unresolved/partial effect: 57 (23.8%)
- Response/effect relation counts: `{"adjacent": 47, "conflict": 2, "exact": 191}`

### Importance x Effect

`{"high": {"does_not_address": 104, "partially_addresses": 51, "resolved_or_weakened": 4, "unclear": 23}, "low": {"does_not_address": 20, "partially_addresses": 20, "resolved_or_weakened": 3, "unclear": 5}, "medium": {"does_not_address": 4, "partially_addresses": 2, "resolved_or_weakened": 1, "unclear": 3}}`

### Response x Effect

`{"generic_or_unclear": {"does_not_address": 22, "partially_addresses": 18, "unclear": 30}, "likely_resolved": {"resolved_or_weakened": 2}, "not_addressed": {"does_not_address": 104, "unclear": 1}, "specifically_addressed": {"does_not_address": 2, "partially_addresses": 55, "resolved_or_weakened": 6}}`

## Test 2 - Sample Size Alignment

- Summary counts: `{"claim_count": 854, "llm_consensus_label_count": 120, "llm_rebuttal_label_count": 240, "paper_count": 80, "review_count": 205}`
- Actual nested counts: `{"claim_count": 854, "paper_count": 80, "paper_with_claim_count": 53, "review_count": 205, "review_with_claim_count": 202}`
- Interpretation: Use 80 papers / 205 reviews / 854 claims for the reviewer-calibration report scope. Use 53 papers / 202 reviews / 854 claims when reporting only papers/reviews that contain claim records.

## Test 3 - Grounding Check

- Reviewer-calibration claims: 854
- Grounded true/false: 854 / 0
- Grounded rate: 100.0%
- Logic: In reviewer_calibration.py, `grounded` is set to bool(clean_text(claim.get('source_sentence', ''))).
- Interpretation: In lifecycle/reviewer-calibration, grounding is currently an extraction/source-sentence gate, not a discriminative review-quality axis.
- Grounding validation raw pass rate: 89.7%
- Grounding validation final pass rate: 100.0%
- Raw grounding failures: 164 of 1594

### Grounding Examples

- `cXs5md5wAq:3FBIToMxSZ:0` grounded=True claim=The proposed approach for using GNNs for bacterial communities is vaguely described and not well justified.
- `cXs5md5wAq:3FBIToMxSZ:1` grounded=True claim=The key methods section (2.2) provides a generic description of existing GNN approaches, and is missing key microbiome specific information (in particular, what is the topology of the graph).
- `cXs5md5wAq:3FBIToMxSZ:2` grounded=True claim=Overall, the proposed method - applying GNN model in a straightforward way to a very small, fully-connected graph - is poorly justified and weak on novelty.
- `cXs5md5wAq:3FBIToMxSZ:3` grounded=True claim=What is the rationale for using a GNN on a very simple graph?
- `cXs5md5wAq:3FBIToMxSZ:4` grounded=True claim=What is the benefit of focusing on predicting steady state, instead of focusing on dynamical changes to the relative abundances (e.g., dysbiosis).
- `cXs5md5wAq:2gTtKikoba:0` grounded=True claim=The methodological contribution is limited as the presented work is mostly implementing GNNs for microbial steady state predictions.
- `cXs5md5wAq:2gTtKikoba:1` grounded=True claim=This is a reasonable assumption to make. However the fact that this method works only for steady state solutions needs to be emphasized.
- `cXs5md5wAq:2gTtKikoba:2` grounded=True claim=Did all such simulations lead to steady state solutions? Were any simulations that did not lead to steady state solutions discarded? Do the authors also have any comments on the frequency of steady state solutions when …
- `cXs5md5wAq:2gTtKikoba:3` grounded=True claim=The authors should square these two facts.
- `cXs5md5wAq:2gTtKikoba:4` grounded=True claim=The claim of interpretability seems to be questionable.

### Raw Grounding Failure Examples From Validation

- `cXs5md5wAq:2gTtKikoba` reason=['source_sentence_not_found'] claim=The steady state is entirely determined by the parameters $a_{i,j}$ and $K_i$. The authors use a vector composed of $[\mu_i, K_i, \nu_i^s, \nu_i^r, random]$ to simulate the genome data in their simulation. It would be a…
- `cXs5md5wAq:2gTtKikoba` reason=['source_sentence_not_found'] claim=The parameter $a_{i,j}$ contains information on the pairwise interaction between different species. On the other hand, the information in a genome is completely intrinsic to a particular species. The authors should squa…
- `cXs5md5wAq:2gTtKikoba` reason=['source_sentence_not_found'] claim=A proper simulation would entail simulation of the genome data. The genome data typically do not include information on interaction between species. But for simulations, the interaction matrix was used to derive $\\nu$ …
- `cXs5md5wAq:2gTtKikoba` reason=['source_sentence_not_found'] claim=The authors need to provide details on how the node (genome) attributes were obtained, especially $\\nu$'s, as in real-world data, the ground-truth interaction $a_{ij}$ is not available.
- `cXs5md5wAq:vb8QNXNzVn` reason=['source_sentence_not_found'] claim=The largest studied communities are 26 and this needs to be put in context with the other fields, citing Wikipedia “1010 to 1011 cells per gram of intestinal content” seems far off from the estimated single colonies.
