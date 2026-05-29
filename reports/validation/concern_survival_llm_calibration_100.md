# Concern Survival LLM Calibration

- Input items: 100
- Labels: 100
- High-confidence training candidates: 42
- Auto/LLM agreement: 74.0%

## Label Counts

| Label set | Counts |
| --- | --- |
| `auto_label_counts` | `{"not_found": 33, "partial": 33, "survived": 34}` |
| `llm_survival_label_counts` | `{"not_found": 49, "partial": 32, "survived": 17, "unsure": 2}` |
| `llm_concern_quality_counts` | `{"high": 38, "low": 40, "medium": 22}` |
| `llm_ac_stance_counts` | `{"endorsed_or_relied_on": 19, "mentioned_as_resolved_or_outweighed": 1, "mentioned_neutrally": 47, "not_mentioned": 33}` |
| `high_confidence_label_counts` | `{"not_found": 3, "partial": 22, "survived": 17}` |

## Agreement

- `7QlKLvfVge:LsvjaIpscH:6` auto=`survived` llm=`survived` quality=`high`
  - Claim: The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?
  - Meta: Why use the consequence of the proof in the middle of the proof?''
  - Rationale: The meta-review explicitly cites a reviewer concern: 'The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?' and discusses addressing reviewer concerns and the need for clear motivation. This shows direct repetition and reliance on the same concern. The concern is spec...
- `dYjuJGTEbc:3MMkDoB21Q:1` auto=`not_found` llm=`not_found` quality=`medium`
  - Claim: The paragraph about Kantorovich relaxation states that the minimum is attained at an extremal point under some conditions which are detailed in appendix; the conditions should be put forward in the main text.
  - Meta: Moreover, several aspects of the theoretical results are noted to require detailed rewriting to enhance clarity and comprehensibility.
  - Rationale: The meta-review focuses on need for rewriting and lack of related work discussion; the specific reviewer claim about putting conditions in main text exists in a separate claim_text of the reviewer, but the meta-review mentions clarity and comparison issues rather than explicitly endorsing that the specific condition...
- `rGvDRT4Z60:8IuiGuz9Hc:4` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Clarify FairDP-SGD: definition and existence; and request where FAIR-PATE's CheXpert results are.
  - Meta: Finally, reviewer p5Rv noted the small improvements of FairPATE over baselines and raised concerns about the diversity and clarity of experiments, with several benchmarks relegated to the appendix without thorough discussion.
  - Rationale: The meta-review summarizes reviewer concerns about fairness, presentation, and prior work but does not substantively repeat the exact reviewer claim about clarifying FairDP-SGD or where FAIR-PATE's CheXpert results are. The claim text asks for definitions and results; the meta-review mentions issues about diversity,...
- `eepoE7iLpL:Omfs3dIcbU:0` auto=`partial` llm=`partial` quality=`high`
  - Claim: Equation 4 describes the neural network construction. However, I am unclear about the objective function to optimize the neural network.
  - Meta: This paper proposes a method for "neural subset selection" based on deep sets.
  - Rationale: The meta-review mentions the same broad issue as the claim (neural subset selection, objective function/optimization details) and notes weaknesses and reviewer responses, but does not substantively repeat or rely on the specific concern about equation 4 objective function; it references weaknesses and acceptance dis...
- `AOSsLRKQrX:iusxEbIueU:5` auto=`partial` llm=`partial` quality=`high`
  - Claim: The model training in Section 3.6 incorporates multiple loss functions. Have ablation studies been conducted to understand the impact of each loss function on the overall performance?
  - Meta: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
  - Rationale: The meta-review explicitly cites substantial concerns about the experimental evaluation, including ablations, datasets, and disentangling being the key to reported performance. It endorses and relies on the concern that the ablation and disentanglement claims are not well-supported, and calls for more evidence. This...
- `AJBkfwXh3u:KidnSLrJ44:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: 2. Does $||A||$ operate by summing all elements of $A$ in Equation 14? Besides, does Equation 14 exist error? To satisying the sparsity requirement of causal and dynamic causal graph set, whether Equation 14 should be replaced by $\frac{{||A_t^C|{|_1} + ||A_t^S|{|_1}}}{{||{A_t}|{|_1}}}$?
  - Meta: This paper presents a causal approach to improving the interpretability of Graph Neural Networks (GNNs).
  - Rationale: The meta-review discusses overall interpretability of causal GNNs and notes concerns about validation pipeline and static vs dynamic graphs, but it does not echo or rely on the specific reviewer question about Equation 14 and the proposed replacement. The reviewer’s claim text is a theory question about equation det...
- `w73feIekdO:NLKFsY27K9:4` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Can you elaborate on the tradeoff between computational complexity of your technique and (epsilon, delta) choices during coreset construction?
  - Meta: There are serious concerns regarding the experiments and presentation of the paper.
  - Rationale: The meta-review discusses experiments and presentation; it does not mention the specific claim about tradeoff between computational complexity and epsilon-delta during coreset construction. The claim_text is about elaborating tradeoffs; meta-review focuses on experiments/presentation and general criticisms. Insuffic...
- `i8PjQT3Uig:76XC5M0kbk:1` auto=`survived` llm=`survived` quality=`high`
  - Claim: What benefit does it have over other world model methods (like Dreamer)?
  - Meta: It seeks to develop a method for learning world model with efficient incremental updates.
  - Rationale: The meta-review repeats the concern in the claim by noting the paper should compare to state-of-the-art baselines as a weakness and discusses its contribution and importance. It endorses that concerns were addressed and that the contribution is meaningful. This shows substantive reference to the same concern (compar...
- `jXR5pjs1rV:dXSWosECmZ:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Insufficient Discussion on Personalization: The paper does not sufficiently explore prior work in personalization within general preference learning and information retrieval; expanding discussion could broaden context.
  - Meta: In the discussion between authors and reviewers, some of these points could be resolved but other not.
  - Rationale: The meta-review discusses personalization and evaluation/novelty concerns, but does not clearly reflect the specific claim about 'Insufficient Discussion on Personalization' as a standalone concern within the meta-review. The auto_survival_label is not_found, and while the meta-review mentions 'insufficient discussi...
- `dYjuJGTEbc:hJUcbfxUWY:2` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Synthetic data: GWL and SpecGWL perform better than EGWB in some figures; need reason why these baselines fail params and why EGWB succeeds.
  - Meta: Moreover, several aspects of the theoretical results are noted to require detailed rewriting to enhance clarity and comprehensibility.
  - Rationale: The meta-review discusses broader issues (novel GW-type method, need for rewriting, lack of discussion/comparison) but does not address the specific claim about synthetic data where GWL/SpecGWL outperform EGWB in Figures 2/4 or reasons for baseline failures. The user claim is about why baselines fail params and EGWB...

## Disagreement

- `B0wJ5oCPdB:ZOPmtxTnai:0` auto=`survived` llm=`not_found` quality=`low`
  - Claim: What is the fundamental explanation that this method works well?
  - Meta: Beyond the paper's relevance, the reviewers appreciate the simplicity of the method and its improvements over the CoT baseline, as well as the clarity of the presentation.
  - Rationale: The meta-review discusses the paper's contributions, novelty, and evaluation, but it does not address the specific claim about a fundamental explanation for why the method works. The user claim text asks for explanation, but the meta-review focuses on high-level critique, lack of novel algorithms, and prompt enginee...
- `rGvDRT4Z60:yub0t46EhK:5` auto=`partial` llm=`not_found` quality=`low`
  - Claim: Why Tran et and Jagielski et al. are not reported for the UTK-dataset experiment?
  - Meta: Reviewer Mex5 highlighted the need to consider fairness when rejecting queries in privacy models, noting that ignoring fairness can be both consequential in practice and, in experiments, impact the Pareto frontier's observed gains.
  - Rationale: The meta-review discusses fairness in rejecting queries and general issues about prior work, presentation, and implications of rejection mechanism. It does not substantively repeat, endorse, or rely on the specific reviewer concern about Tran et al. and Jagielski et al. not reported for the UTK-dataset experiment. T...
- `10eQ4Cfh8p:w67nfG2dMW:0` auto=`survived` llm=`not_found` quality=`low`
  - Claim: The performance evaluation of the proposed framework seems quite limited, especially as the baselines are overly simplified in Table 1.
  - Meta: The paper misses certain baselines in its performance evaluation.
  - Rationale: The meta-review discusses general weaknesses and lacks empirical baselines; it does not substantively repeat or rely on the exact reviewer concern text about baselines being overly simplified in Table 1. The auto-survival note mentions missing baselines, but the meta-review's own content does not clearly endorse or...
- `gYcft1HIaU:EwWKiU8GWB:1` auto=`survived` llm=`not_found` quality=`low`
  - Claim: What is the source of the EHR resource used in the preliminary making of the dataset?
  - Meta: The dataset may be a useful resource for researchers in biomedical NLP going forward.
  - Rationale: The meta-review discusses general framing of MedDisK and evaluation issues but does not substantively repeat or rely on the specific reviewer claim about the source of the EHR resource. The reviewer claim is a narrowly framed question about data provenance, not central to the meta-review’s concerns, and the meta-rev...
- `w73feIekdO:NLKFsY27K9:1` auto=`survived` llm=`not_found` quality=`medium`
  - Claim: I have several questions that will help me identify what the central contributions are and on how the proposed method outperforms over other methods in the state of the art.
  - Meta: Classic tracking methods frequently employ clustering and robust statistical approaches, and it is crucial to benchmark the proposed method against these alternatives to showcase its advancements in the state of the art.
  - Rationale: The meta-review discusses general concerns about experiments, comparisons, and presentation but does not directly mention the specific reviewer claim about identifying central contributions or outperforming state-of-the-art. The reviewer claim is a generic meta-question, while the meta-review focuses on methodologic...
- `10eQ4Cfh8p:zlSWBdRAhX:0` auto=`survived` llm=`partial` quality=`high`
  - Claim: There is no empirical evidence to justify the claim that the training paradigm can be readily adapted to other combinatorial optimization problems, and there is no explanation of how this can actually be done.
  - Meta: The methodology seems specifically tailored for FJSP, with no clear evidence or explanation of its adaptability to other combinatorial optimization problems.
  - Rationale: The meta-review explicitly notes lack of empirical justification for adaptability claims outside FJSP and emphasizes that the methodology is tailored to FJSP with no evidence of adaptability. This aligns with the claim that there is no empirical evidence to justify the claim and no explanation of how it can be done,...
- `10eQ4Cfh8p:wckxlkPL42:0` auto=`survived` llm=`partial` quality=`high`
  - Claim: Actions (in Section 3.1) are critical, but not defined clearly. I have no problems with actions for construction heuristics, but actions for improvement heuristics are not well defined.
  - Meta: Certain critical components, like the improvement step's applicability to other problems and the reasoning behind various embeddings, are not well explained.
  - Rationale: The reviewer claim about unclear definitions and sections (actions definitions, insertion position embedding, and policy model) is echoed in the meta-review as part of "Clarity Issues" and specifically notes that critical components are not well explained. The meta-review substantively repeats the concern about uncl...
- `cQgjz0mf0r:JFysq9wa5A:4` auto=`survived` llm=`not_found` quality=`low`
  - Claim: Is SplineCAM an exact method? If so, why does it only work in 2D?
  - Meta: On the other hand, the numerical experiments are not strong and solid to locate this paper as an empirical verification of existing work.
  - Rationale: The meta-review discusses general concerns about overlap with existing work and overall issues, but does not substantively repeat or rely on the specific claim text about SplineCAM exactness or 2D limitation. The matched meta segment mentions empirical verification of existing work, not the exact question about Spli...
- `lK2V2E2MNv:Y3CIkpDJh7:0` auto=`survived` llm=`not_found` quality=`low`
  - Claim: Comprehensive ablation of w/ and wo/ assignment prediction on the same vision/language backbones is missing.
  - Meta: The paper proposes VLAP, a method to bridge vision encoders and language models through assignment prediction.
  - Rationale: The meta-review text discusses overall acceptance and rebuttal dynamics, reviewer opinions, and the paper’s incremental nature, but it does not substantively mention or rely on the specific concern from the claim: “Comprehensive ablation of with and without assignment prediction on the same vision/language backbones...
- `lK2V2E2MNv:Y3CIkpDJh7:2` auto=`partial` llm=`not_found` quality=`low`
  - Claim: In Tab1,2,3, when compared with previous works, the vision/language backbone is always different. I wonder if using the same backbones as previous works, will the proposed method still outperform them?
  - Meta: The paper proposes VLAP, a method to bridge vision encoders and language models through assignment prediction.
  - Rationale: The meta-review discusses VLAP, its performance, and reviewers’ opinions. The specific concern in the claim text about using same backbones versus previous works is not meaningfully mentioned or analyzed in the meta-review. The matched segment does not substantively repeat or rely on that concern; at most it notes t...

## High Confidence

- `7QlKLvfVge:LsvjaIpscH:6` auto=`survived` llm=`survived` quality=`high`
  - Claim: The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?
  - Meta: Why use the consequence of the proof in the middle of the proof?''
  - Rationale: The meta-review explicitly cites a reviewer concern: 'The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?' and discusses addressing reviewer concerns and the need for clear motivation. This shows direct repetition and reliance on the same concern. The concern is spec...
- `eepoE7iLpL:Omfs3dIcbU:0` auto=`partial` llm=`partial` quality=`high`
  - Claim: Equation 4 describes the neural network construction. However, I am unclear about the objective function to optimize the neural network.
  - Meta: This paper proposes a method for "neural subset selection" based on deep sets.
  - Rationale: The meta-review mentions the same broad issue as the claim (neural subset selection, objective function/optimization details) and notes weaknesses and reviewer responses, but does not substantively repeat or rely on the specific concern about equation 4 objective function; it references weaknesses and acceptance dis...
- `AOSsLRKQrX:iusxEbIueU:5` auto=`partial` llm=`partial` quality=`high`
  - Claim: The model training in Section 3.6 incorporates multiple loss functions. Have ablation studies been conducted to understand the impact of each loss function on the overall performance?
  - Meta: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
  - Rationale: The meta-review explicitly cites substantial concerns about the experimental evaluation, including ablations, datasets, and disentangling being the key to reported performance. It endorses and relies on the concern that the ablation and disentanglement claims are not well-supported, and calls for more evidence. This...
- `w73feIekdO:NLKFsY27K9:1` auto=`survived` llm=`not_found` quality=`medium`
  - Claim: I have several questions that will help me identify what the central contributions are and on how the proposed method outperforms over other methods in the state of the art.
  - Meta: Classic tracking methods frequently employ clustering and robust statistical approaches, and it is crucial to benchmark the proposed method against these alternatives to showcase its advancements in the state of the art.
  - Rationale: The meta-review discusses general concerns about experiments, comparisons, and presentation but does not directly mention the specific reviewer claim about identifying central contributions or outperforming state-of-the-art. The reviewer claim is a generic meta-question, while the meta-review focuses on methodologic...
- `i8PjQT3Uig:76XC5M0kbk:1` auto=`survived` llm=`survived` quality=`high`
  - Claim: What benefit does it have over other world model methods (like Dreamer)?
  - Meta: It seeks to develop a method for learning world model with efficient incremental updates.
  - Rationale: The meta-review repeats the concern in the claim by noting the paper should compare to state-of-the-art baselines as a weakness and discusses its contribution and importance. It endorses that concerns were addressed and that the contribution is meaningful. This shows substantive reference to the same concern (compar...
- `xibcBSuuq0:zwpI0TjvXj:1` auto=`partial` llm=`partial` quality=`high`
  - Claim: I would suggest the authors to test on more challenging MARL benchmarks, though those benchmarks often require more exploration, which may pose challenges for the proposed method.
  - Meta: This paper studies the exploration-exploitation tradeoff in multi-agent reinforcement learning, by proposing a new method of constructing some Stable Prefix Policy using Monte-Carlo Trajectory Tree.
  - Rationale: The reviewer concern about testing on more challenging MARL benchmarks is echoed in the meta-review as a general suggestion for more extensive experimental evaluation, not as a direct endorsement or repetition of the exact concern. The meta-review discusses experimental improvements and broader testing but does not...
- `10eQ4Cfh8p:zlSWBdRAhX:0` auto=`survived` llm=`partial` quality=`high`
  - Claim: There is no empirical evidence to justify the claim that the training paradigm can be readily adapted to other combinatorial optimization problems, and there is no explanation of how this can actually be done.
  - Meta: The methodology seems specifically tailored for FJSP, with no clear evidence or explanation of its adaptability to other combinatorial optimization problems.
  - Rationale: The meta-review explicitly notes lack of empirical justification for adaptability claims outside FJSP and emphasizes that the methodology is tailored to FJSP with no evidence of adaptability. This aligns with the claim that there is no empirical evidence to justify the claim and no explanation of how it can be done,...
- `rp5vfyp5Np:YktI8n3TeZ:5` auto=`survived` llm=`survived` quality=`high`
  - Claim: The intent policy learning relies on human preferences, which may introduce uncertainty and cost; need discussion on practicality and data requirements.
  - Meta: Complexity and Uncertainty in Intention Policy Learning: The process of learning intention policy based on human preferences introduces extra requirements and uncertainties, including the expensive collection of human preference data and potential biases.
  - Rationale: The meta-review explicitly discusses the weakness about 'Complexity and Uncertainty in Intention Policy Learning' and treats it as a significant weakness, echoing the claim text about uncertainty and data requirements. The AC (meta-review) endorses or relies on this concern as part of evaluating weaknesses, and the...
- `10eQ4Cfh8p:wckxlkPL42:0` auto=`survived` llm=`partial` quality=`high`
  - Claim: Actions (in Section 3.1) are critical, but not defined clearly. I have no problems with actions for construction heuristics, but actions for improvement heuristics are not well defined.
  - Meta: Certain critical components, like the improvement step's applicability to other problems and the reasoning behind various embeddings, are not well explained.
  - Rationale: The reviewer claim about unclear definitions and sections (actions definitions, insertion position embedding, and policy model) is echoed in the meta-review as part of "Clarity Issues" and specifically notes that critical components are not well explained. The meta-review substantively repeats the concern about uncl...
- `jXR5pjs1rV:dXSWosECmZ:2` auto=`survived` llm=`survived` quality=`high`
  - Claim: Lack of Policy-Level Evaluation: The paper focuses on reward-model level evaluation; including policy-level evaluations would provide a more comprehensive understanding of practical applications.
  - Meta: Although the reviewers agree that the paper is interesting and makes a step in the right direction, they also raise a number of critical comments and concerns, including the limited novelty of the baseline approach, the synthetic nature and possible bias of the dataset, the lack of baselines and alternatives, the la...
  - Rationale: The meta-review explicitly mentions several concerns (e.g., lack of policy-level evaluation, synthetic dataset, lack of baselines) and these points align with the claim about missing policy-level evaluation. The meta-review repeats and relies on the same concern as stated in the claim_text, indicating substantive re...