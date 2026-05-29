# Rebuttal Resolution LLM Calibration

- Input items: 120
- Labels: 120
- High-confidence training candidates: 31
- Proxy/LLM agreement: 34.2%

## Label Counts

- `proxy_label_counts`: `{"addressed_unclear_resolution": 66, "likely_resolved_or_answered": 27, "not_addressed": 27}`
- `llm_response_label_counts`: `{"generic_or_unclear": 32, "likely_resolved": 2, "not_addressed": 55, "specifically_addressed": 31}`
- `llm_effect_counts`: `{"does_not_address": 62, "partially_addresses": 34, "resolved_or_weakened": 6, "unclear": 18}`
- `llm_specificity_counts`: `{"generic": 35, "none": 52, "specific": 32, "unclear": 1}`
- `high_confidence_response_label_counts`: `{"likely_resolved": 2, "not_addressed": 6, "specifically_addressed": 23}`

## Examples

### High Confidence
- `tmsqb6WpLz:IeQh1AMom9:2` proxy=`addressed_unclear_resolution` llm=`specifically_addressed` confidence=`high`
  - Claim: There is a \"side note\" in page 7: \"When capacity is limited, the topic ratio and factual ratio simultaneously reduce on Pubmed in Figure 6.\" I did not see topic ratio reduces in Figure 6. Is this information supposed to be told by Figure 6?
  - Response: The side note on page 7 is intended to explain the phenomenon that the topic ratio (red line) reduces with decreasing model capacity on PubMed (the left plot of Figure 6).
  - Rationale: The author response directly mentions the side note and explains that the topic ratio reduces with decreasing model capacity on PubMed, which corresponds to the reviewer’s concern about whether Figure 6 communicates that topic ratio reduces. It clarifies that the red line topic ratio decreases an...
- `1FWDEIGm33:pfCqf1kmPM:4` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: Do you have any data about the influence of the training datasets on the experimental results that you showed in this paper?
  - Response: In other words, we show that context influences the questionnaire results in unexpected ways.
  - Rationale: The author response directly mentions that context influences questionnaire results, which aligns with addressing the reviewer’s claim about data on the influence of training datasets. However, the response shifts the claim to context effects on questionnaire results rather than providing data ab...
- `UVSKuh9eK5:lo6OmS3vso:2` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: Most of the conclusions are prevalent in the literature (e.g., the diversity of training captions promotes compositionality [3]), and the mutual information analysis does not seem to provide additional insights [4, 5].
  - Response: Specifically, we conducted the first analysis (Section 3.3.1) that examines the impact of caption diversity and quality in training datasets on the mutual information (MI) between object and attribute tokens.
  - Rationale: The author explicitly cites a novel analysis (Section 3.3.1) claiming it examines caption diversity/quality and its impact on mutual information between object and attribute tokens, directly addressing the reviewer’s claim that the MI analysis does not add insights. However, the claim suggests MI...
- `H9DYMIpz9c:KqbT3NNcP2:2` proxy=`not_addressed` llm=`not_addressed` confidence=`high`
  - Claim: My major questions concern the clarifications about the approach listed above, without which it is really hard to judge the technical correctness / soundness of the paper.
  - Response: First of all, we really appreciate your review — we believe this is a good quality review where you ask very valid questions
  - Rationale: Author response segment is polite but does not discuss the reviewer claim about clarifications; it merely acknowledges the review and compliments it without addressing what needs clarification or providing any information about approach or technical soundness.
- `kKRbAY4CXv:eSJOZmZeDG:0` proxy=`addressed_unclear_resolution` llm=`specifically_addressed` confidence=`high`
  - Claim: The authors should define earlier what they mean by evolutionary PDEs.
  - Response: We focus on semi-linear PDEs because they allow us to derive the evolutionary pattern of the desired ideal solution, something that is not achievable with nonlinear PDEs (which may not even have a corresponding fundamental solution for the operator).
  - Rationale: The author response directly discusses the reviewer claim by stating a scope choice (semi-linear PDEs) and contrasts with nonlinear PDEs to justify definition/approach. This directly addresses clarity concern by clarifying what they mean, even though it may not fully define 'evolutionary PDEs' in...
- `rp5vfyp5Np:YktI8n3TeZ:6` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: The paper suggests the method can be used to improve robustness of agents, which may require careful evaluation; include limitations.
  - Response: Furthermore, we applied various defense methods to gauge the robustness of these agents.
  - Rationale: The author response segment states that they applied various defense methods to gauge robustness, which directly addresses the reviewer’s claim about evaluating robustness and including limitations. It provides a concrete action (testing defense methods) rather than a vague assertion. However, it...
- `cXs5md5wAq:3FBIToMxSZ:3` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: What is the rationale for using a GNN on a very simple graph?
  - Response: We are interested in using the GNN as a dynamics model, where we cannot assume any prior knowledge on the graph connectivity.
  - Rationale: The author states the GNN is used as a dynamics model and explicitly notes lack of prior knowledge on graph connectivity, which directly engages the reviewer’s claim about rationale for using a GNN on a simple graph. It explains context and purpose, showing why a GNN is chosen given uncertain con...
- `jx6njBKH8E:ZUBG0iUrpP:6` proxy=`not_addressed` llm=`not_addressed` confidence=`high`
  - Claim: The paper discusses mitigations and future work but does not provide concrete experimental validation or quantification of proposed mitigations.
  - Response: I went over the text multiple times but did not realize what the point of that experiment is.
  - Rationale: The author response segment expresses confusion about the point of an experiment, but it does not engage with the reviewer claim about mitigations lacking concrete validation. It neither discusses mitigations, experiments, or quantification, nor provides any evidence or clarification supportive o...
- `10eQ4Cfh8p:w67nfG2dMW:2` proxy=`not_addressed` llm=`not_addressed` confidence=`high`
  - Claim: What is "Generate+improve" in Table 3? Is it different from GIM?
  - Response: 
  - Rationale: The author segment is empty in the provided data, so there is no discussion or clarification about what 'Generate+improve' means or whether it differs from GIM. Therefore, the claim is not addressed.
- `qBL04XXex6:1lDRac9ePM:2` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: More analysis or ablation studies are also helpful.
  - Response: We have added more details and discussions on edge weight computation for trees and the aggregation strategies in Sections C and D of the Appendix.
  - Rationale: Author mentions added details on edge weight computation and aggregation strategies in Sections C and D of the Appendix, directly addressing the reviewer’s request for more analysis/ablation and clarifying key components.
### Proxy Disagreement
- `rhgIgTSSxW:CEBB2izG6I:3` proxy=`addressed_unclear_resolution` llm=`not_addressed` confidence=`low`
  - Claim: Is TabR applicable to categorical features? It seems like the paper only considers continuous features.
  - Response: Different scope:** the work fully focuses on small ( It seems like the paper only considers continuous features
  - Rationale: The author response repeats that the work focuses on continuous features but does not discuss applicability to categorical features or acknowledge the reviewer’s specific concern. It does not provide evidence, experiments, or argument addressing whether TabR can handle categorical features; thus,...
- `AZGIwqCyYY:MPDVvgTzbR:1` proxy=`addressed_unclear_resolution` llm=`not_addressed` confidence=`low`
  - Claim: The paper should include ablation or comparisons across different baselines to justify the contribution of meta-learning the unified Hamiltonian representations.
  - Response: W1** The evaluation can be strengthened by considering comparing the proposed methods with other Few-shot Learning and Physics-informed Neural Networks methods for system domain generalization under both "consistent" and "different" physical laws.
  - Rationale: The author response merely restates the reviewer’s suggestion without discussing ablation or comparative baselines, and provides no direct mention of performing ablations or adding comparisons. It does not address whether such experiments will be done or how they would affect the contribution.
- `1FWDEIGm33:pfCqf1kmPM:4` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: Do you have any data about the influence of the training datasets on the experimental results that you showed in this paper?
  - Response: In other words, we show that context influences the questionnaire results in unexpected ways.
  - Rationale: The author response directly mentions that context influences questionnaire results, which aligns with addressing the reviewer’s claim about data on the influence of training datasets. However, the response shifts the claim to context effects on questionnaire results rather than providing data ab...
- `rEQ8OiBxbZ:ugAdT84dP2:2` proxy=`likely_resolved_or_answered` llm=`generic_or_unclear` confidence=`low`
  - Claim: How does the method perform on datasets like QM9?
  - Response: Response: We would like to point out that we adopt only 2D graph inputs for the biochemistry prediction tasks to **conform with** established dataset conventions and existing baseline approaches on MoleculeNet, including GraphMVP, 3DInfomax, and other 3D pre-trained models - all of which use 2D i...
  - Rationale: The author response mentions using 2D graph inputs and cites established datasets/baselines, but it does not answer how the method performs on QM9 specifically. It frames conformity to conventions rather than providing performance results or analysis on QM9. This is largely generic justification...
- `JWrl5pJCnl:A3gHHaLomn:4` proxy=`addressed_unclear_resolution` llm=`not_addressed` confidence=`low`
  - Claim: How was comparison to DT done, as DT doesn't take in language instructions?
  - Response: >**Q7: How was the comparison to DT done, as DT doesn't take in language instructions?
  - Rationale: The author response segment repeats the question about DT comparison and does not provide any answer or discussion of how the comparison was performed or its implications.
- `gtkFw6sZGS:5Ici66sfg0:1` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`low`
  - Claim: It is clear that this paper is in a long line of other approaches. Yet, it is not clear why evaluating LLMs with an LLM is principled.
  - Response: Yet, it is not clear why evaluating LLMs with an LLM is principled.
  - Rationale: The author response segment merely restates the same concern (“not clear why evaluating LLMs with an LLM is principled”) without addressing why this principle is valid or providing justification/evidence. It does not directly respond to the reviewer’s claim beyond repeating it, so it is not speci...
- `UVSKuh9eK5:lo6OmS3vso:2` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: Most of the conclusions are prevalent in the literature (e.g., the diversity of training captions promotes compositionality [3]), and the mutual information analysis does not seem to provide additional insights [4, 5].
  - Response: Specifically, we conducted the first analysis (Section 3.3.1) that examines the impact of caption diversity and quality in training datasets on the mutual information (MI) between object and attribute tokens.
  - Rationale: The author explicitly cites a novel analysis (Section 3.3.1) claiming it examines caption diversity/quality and its impact on mutual information between object and attribute tokens, directly addressing the reviewer’s claim that the MI analysis does not add insights. However, the claim suggests MI...
- `cQgjz0mf0r:ohnIAzeDZx:0` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`low`
  - Claim: The biggest weakness in the paper seems to be that a critical part of it is missing. The experimental setup in section 4.1 states 
> We control the size of the local neighborhood by controlling the diagonal lengths via the $r$ parameter mentioned in section...
  - Response: > The biggest weakness in the paper seems to be that a critical part of it is missing.
  - Rationale: The author response repeats the reviewer’s claim (
- `rp5vfyp5Np:YktI8n3TeZ:6` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: The paper suggests the method can be used to improve robustness of agents, which may require careful evaluation; include limitations.
  - Response: Furthermore, we applied various defense methods to gauge the robustness of these agents.
  - Rationale: The author response segment states that they applied various defense methods to gauge robustness, which directly addresses the reviewer’s claim about evaluating robustness and including limitations. It provides a concrete action (testing defense methods) rather than a vague assertion. However, it...
- `b0IRscfEOb:Uhi3FtaPLV:0` proxy=`addressed_unclear_resolution` llm=`not_addressed` confidence=`low`
  - Claim: The word "passage" is confusing - does it refer to the entities and relationships obtained by the retriever? The authors need further clarification.
  - Response: > “In the textual description of Section 3, the word "passage" is confusing - does it refer to the entities and relationships obtained by the retriever?
  - Rationale: The author response segment repeats the reviewer claim without providing any clarification or direct answer. It does not address whether "passage" refers to entities/relationships or offer a resolution. Therefore, it is not addressed and remains unclear in effect.