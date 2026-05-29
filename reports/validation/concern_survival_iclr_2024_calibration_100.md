# Concern Survival Calibration Sample

- Version: `concern-survival-calibration-v0.1`
- Source survival version: `concern-survival-meta-review-v0.1`
- Sample size: 100
- Candidate count: 854
- Seed: 42
- Strategy: `balanced_by_auto_survival_label`

## Label Guidance

- `survived`: The meta-review substantively repeats, endorses, or relies on this reviewer concern.
- `partial`: The meta-review discusses the same broad issue but loses important specificity.
- `not_found`: The meta-review does not mention this concern in a meaningful way.
- `unsure`: The pair is ambiguous or needs more context before labeling.

## Sample Counts

| Auto label | Items |
| --- | ---: |
| `not_found` | 33 |
| `partial` | 33 |
| `survived` | 34 |

## Items

### 7QlKLvfVge:LsvjaIpscH:6 auto=`survived` score=0.678 decision=`reject`
- Claim: The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?
- Source: 5. The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?
- Matched meta-review segment: Why use the consequence of the proof in the middle of the proof?''
- Human survival label: 
- Human concern quality: 
- Notes: 

### dYjuJGTEbc:3MMkDoB21Q:1 auto=`not_found` score=0.057 decision=`reject`
- Claim: The paragraph about Kantorovich relaxation states that the minimum is attained at an extremal point under some conditions which are detailed in appendix; the conditions should be put forward in the main text.
- Source: In the paragraph about Kantorovich relaxation it is stated that the minimum is attained at an extremal point under some conditions which are detailed in appendix. This point is central to the use of the algorithm afterwards. Thus I believe the conditions should be put forward in the main text.
- Matched meta-review segment: Moreover, several aspects of the theoretical results are noted to require detailed rewriting to enhance clarity and comprehensibility.
- Human survival label: 
- Human concern quality: 
- Notes: 

### B0wJ5oCPdB:ZOPmtxTnai:0 auto=`survived` score=0.435 decision=`reject`
- Claim: What is the fundamental explanation that this method works well?
- Source: - What is the fundamental explanation that this method works well?
- Matched meta-review segment: Beyond the paper's relevance, the reviewers appreciate the simplicity of the method and its improvements over the CoT baseline, as well as the clarity of the presentation.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rGvDRT4Z60:yub0t46EhK:5 auto=`partial` score=0.204 decision=`reject`
- Claim: Why Tran et and Jagielski et al. are not reported for the UTK-dataset experiment?
- Source: - Why Tran et and Jagielski et al. are not reported for the UTK-dataset experiment?
- Matched meta-review segment: Reviewer Mex5 highlighted the need to consider fairness when rejecting queries in privacy models, noting that ignoring fairness can be both consequential in practice and, in experiments, impact the Pareto frontier's observed gains.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:w67nfG2dMW:0 auto=`survived` score=0.374 decision=`reject`
- Claim: The performance evaluation of the proposed framework seems quite limited, especially as the baselines are overly simplified in Table 1.
- Source: - The performance evaluation of the proposed framework seems quite limited, especially as the baselines are overly simplified in Table 1.
- Matched meta-review segment: The paper misses certain baselines in its performance evaluation.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rGvDRT4Z60:8IuiGuz9Hc:4 auto=`partial` score=0.278 decision=`reject`
- Claim: Clarify FairDP-SGD: definition and existence; and request where FAIR-PATE's CheXpert results are.
- Source: * **FairDP-SGD" What is FairDP-SGD ? It doesn't seem to have been defined anywhere ? Is it an existing work ? Where is FAIR-PATE's result on CheXpert ?
- Matched meta-review segment: Finally, reviewer p5Rv noted the small improvements of FairPATE over baselines and raised concerns about the diversity and clarity of experiments, with several benchmarks relegated to the appendix without thorough discussion.
- Human survival label: 
- Human concern quality: 
- Notes: 

### gYcft1HIaU:EwWKiU8GWB:1 auto=`survived` score=0.360 decision=`reject`
- Claim: What is the source of the EHR resource used in the preliminary making of the dataset?
- Source: What is the source of the EHR resource used in the preliminary making of the dataset?
- Matched meta-review segment: The dataset may be a useful resource for researchers in biomedical NLP going forward.
- Human survival label: 
- Human concern quality: 
- Notes: 

### eepoE7iLpL:Omfs3dIcbU:0 auto=`partial` score=0.259 decision=`accept`
- Claim: Equation 4 describes the neural network construction. However, I am unclear about the objective function to optimize the neural network.
- Source: 1. Equation 4 describes the neural network construction. However, I am unclear about the objective function to optimize the neural network. Also, after optimization, how do you use this neural network to select a subset?
- Matched meta-review segment: This paper proposes a method for "neural subset selection" based on deep sets.
- Human survival label: 
- Human concern quality: 
- Notes: 

### AOSsLRKQrX:iusxEbIueU:5 auto=`partial` score=0.257 decision=`reject`
- Claim: The model training in Section 3.6 incorporates multiple loss functions. Have ablation studies been conducted to understand the impact of each loss function on the overall performance?
- Source: The model training in Section 3.6 incorporates multiple loss functions. Have ablation studies been conducted to understand the impact of each loss function on the overall performance?
- Matched meta-review segment: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
- Human survival label: 
- Human concern quality: 
- Notes: 

### AJBkfwXh3u:KidnSLrJ44:3 auto=`not_found` score=0.120 decision=`accept`
- Claim: 2. Does $||A||$ operate by summing all elements of $A$ in Equation 14? Besides, does Equation 14 exist error? To satisying the sparsity requirement of causal and dynamic causal graph set, whether Equation 14 should be replaced by $\frac{{||A_t^C|{|_1} + ||A_t^S|{|_1}}}{{||{A_t}|{|_1}}}$?
- Source: 2. Does $||A||$ operate by summing all elements of $A$ in Equation 14? Besides, does Equation 14 exist error? To satisying the sparsity requirement of causal and dynamic causal graph set, whether Equation 14 should be replaced by $\frac{{||A_t^C|{|_1} + ||A_t^S|{|_1}}}{{||{A_t}|{|_1}}}$?
- Matched meta-review segment: This paper presents a causal approach to improving the interpretability of Graph Neural Networks (GNNs).
- Human survival label: 
- Human concern quality: 
- Notes: 

### w73feIekdO:NLKFsY27K9:4 auto=`not_found` score=0.162 decision=`reject`
- Claim: Can you elaborate on the tradeoff between computational complexity of your technique and (epsilon, delta) choices during coreset construction?
- Source: 3) Can you elaborate on the tradeoff between computational complexity of your technique and (epsilon, delta) choices during coreset construction?
- Matched meta-review segment: There are serious concerns regarding the experiments and presentation of the paper.
- Human survival label: 
- Human concern quality: 
- Notes: 

### w73feIekdO:NLKFsY27K9:1 auto=`survived` score=0.353 decision=`reject`
- Claim: I have several questions that will help me identify what the central contributions are and on how the proposed method outperforms over other methods in the state of the art.
- Source: I have several questions that will help me identify what the central contributions are and on how the proposed method outperforms over other methods in the state of the art.
- Matched meta-review segment: Classic tracking methods frequently employ clustering and robust statistical approaches, and it is crucial to benchmark the proposed method against these alternatives to showcase its advancements in the state of the art.
- Human survival label: 
- Human concern quality: 
- Notes: 

### i8PjQT3Uig:76XC5M0kbk:1 auto=`survived` score=0.448 decision=`accept`
- Claim: What benefit does it have over other world model methods (like Dreamer)?
- Source: Moreover, it should be made clear what benefit it does have over other world model methods (like Dreamer).
- Matched meta-review segment: It seeks to develop a method for learning world model with efficient incremental updates.
- Human survival label: 
- Human concern quality: 
- Notes: 

### jXR5pjs1rV:dXSWosECmZ:3 auto=`not_found` score=0.129 decision=`reject`
- Claim: Insufficient Discussion on Personalization: The paper does not sufficiently explore prior work in personalization within general preference learning and information retrieval; expanding discussion could broaden context.
- Source: - Insufficient Discussion on Personalization: While the background on language-model specific alignment techniques is quite solid, the paper does not sufficiently explore prior work in personalization within the realms of general preference learning and information retrieval. Expanding the discussion to include these fields could provide a richer context and potentially lead to new directions to explore.
- Matched meta-review segment: In the discussion between authors and reviewers, some of these points could be resolved but other not.
- Human survival label: 
- Human concern quality: 
- Notes: 

### dYjuJGTEbc:hJUcbfxUWY:2 auto=`not_found` score=0.144 decision=`reject`
- Claim: Synthetic data: GWL and SpecGWL perform better than EGWB in some figures; need reason why these baselines fail params and why EGWB succeeds.
- Source: - Synthetic data: Figure 4 exhibits superior results for GWL and SpecGWL compared to Figure 2. Moreover, in Figure 4 GWL out performs SpecGWL given the true cluster size distribution. Is there any reason why is that the case? I am actually surprised that, for these apparently simple problems GWL and SpecGWL fail to retrieve the right clustering. Understanding the specific reasons for their failure is beneficial in order to comprehend why EGWB, in contrast, succeeds.
- Matched meta-review segment: Moreover, several aspects of the theoretical results are noted to require detailed rewriting to enhance clarity and comprehensibility.
- Human survival label: 
- Human concern quality: 
- Notes: 

### xibcBSuuq0:zwpI0TjvXj:1 auto=`partial` score=0.203 decision=`reject`
- Claim: I would suggest the authors to test on more challenging MARL benchmarks, though those benchmarks often require more exploration, which may pose challenges for the proposed method.
- Source: I would suggest the authors to test on more challenging MARL benchmarks, though those benchmarks often require more exploration, which may pose challenges for the proposed method.
- Matched meta-review segment: This paper studies the exploration-exploitation tradeoff in multi-agent reinforcement learning, by proposing a new method of constructing some Stable Prefix Policy using Monte-Carlo Trajectory Tree.
- Human survival label: 
- Human concern quality: 
- Notes: 

### i8PjQT3Uig:kQVoyHQ5Cg:2 auto=`not_found` score=0.198 decision=`accept`
- Claim: There is a critical weakness in the paper: the paper claims to develop a sparse representation-based approach for model learning, but it is not justified the reported benefits come from the use of the sparse representation for policy learning or for model learning. Note that the former has been extensive studied. in general, a full replay method should be the best in mitigating catastrophic forgetting, but the empirical results reported that the proposed algorithm can sometimes even outperform full replay. That raises a natural question that the benefit mainly comes from the policy learning part by using sparse representation, rather than the proposed model learning part.
- Source: 3. There is a critical weakness in the paper: the paper claims to develop a sparse representation-based approach for model learning, but it is not justified the reported benefits come from the use of the sparse representation for policy learning or for model learning. Note that the former has been extensive studied. in general, a full replay method should be the best in mitigating catastrophic forgetting, but the empirical results reported that the proposed algorithm can sometimes even outperform full replay. That raises a natural question that the benefit mainly comes from the policy learning part by using sparse representation, rather than the proposed model learning part.
- Matched meta-review segment: It seeks to develop a method for learning world model with efficient incremental updates.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:zlSWBdRAhX:0 auto=`survived` score=0.409 decision=`reject`
- Claim: There is no empirical evidence to justify the claim that the training paradigm can be readily adapted to other combinatorial optimization problems, and there is no explanation of how this can actually be done.
- Source: however, there is 1) no empirical evidence to justify the claim and 2) no explanation of *how* this can actually be done.
- Matched meta-review segment: The methodology seems specifically tailored for FJSP, with no clear evidence or explanation of its adaptability to other combinatorial optimization problems.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rp5vfyp5Np:YktI8n3TeZ:5 auto=`survived` score=0.545 decision=`reject`
- Claim: The intent policy learning relies on human preferences, which may introduce uncertainty and cost; need discussion on practicality and data requirements.
- Source: 1. The human preference-based intention policy learning brings extra requirement and uncertainty to the process - the collection of human preference data can be expensive. More importantly, to obtain human preference labels, one need to first collect diverse behavior data so that human can pick the intended policy. Would the collection of the behavior data already involve a pre-defined target policy? (If that's the case, why not directly use the target policy for attacks?)
- Matched meta-review segment: Complexity and Uncertainty in Intention Policy Learning: The process of learning intention policy based on human preferences introduces extra requirements and uncertainties, including the expensive collection of human preference data and potential biases.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:wckxlkPL42:0 auto=`survived` score=0.399 decision=`reject`
- Claim: Actions (in Section 3.1) are critical, but not defined clearly. I have no problems with actions for construction heuristics, but actions for improvement heuristics are not well defined.
- Source: - Actions (in Section 3.1) are critical, but not defined clearly. I have no problems with actions for construction heuristics, but actions for improvement heuristics are not well defined. In Section 3.2 “Insertion Position Embedding” (P5), the definition of insertion position is undefined clearly, and why the number of choices is (n+m) for each operation. Besides, it is also unclear about why the total number of insertion positions is equal to n×(n+m). For these unclear descriptions, there is no clue to understand the proposed method. Note that in Section 3.2 “Policy Model” (P6), there is no way to understand the description “Obviously, there are at most m different insertion schemes for each improvement decision.”
- Matched meta-review segment: Certain critical components, like the improvement step's applicability to other problems and the reasoning behind various embeddings, are not well explained.
- Human survival label: 
- Human concern quality: 
- Notes: 

### xibcBSuuq0:WZgHO4PFTI:2 auto=`not_found` score=0.186 decision=`reject`
- Claim: The Experimental Evaluation suggests some cases of competitiveness but does not compare the methods from a computational point of view, which I believe would help understand the pros and cons of the proposed method. Finally, it was not clear to me how the hyper-optimization of the Sota algorithms used as baselines was done, both in the standard case and in the SDD-augmented case.
- Source: - The Experimental Evaluation suggests some cases of competitiveness but does not compare the methods from a computational point of view, which I believe would help understand the pros and cons of the proposed method. Finally, it was not clear to me how the hyper-optimization of the Sota algorithms used as baselines was done, both in the standard case and in the SDD-augmented case.
- Matched meta-review segment: This paper studies the exploration-exploitation tradeoff in multi-agent reinforcement learning, by proposing a new method of constructing some Stable Prefix Policy using Monte-Carlo Trajectory Tree.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:zlSWBdRAhX:7 auto=`not_found` score=0.190 decision=`reject`
- Claim: How would the model perform if only the generator was trained, and what if training includes generator+improve but only the generator is used for the solution?
- Source: 2. As in the “weaknesses” section, how would the model perform if only the generator was trained? And what if we trained with generator+improve but only used the generator for the solution?
- Matched meta-review segment: It features an innovative approach using two models that work concurrently: one for generating solutions and another for improving them.
- Human survival label: 
- Human concern quality: 
- Notes: 

### jXR5pjs1rV:dXSWosECmZ:2 auto=`survived` score=0.350 decision=`reject`
- Claim: Lack of Policy-Level Evaluation: The paper focuses on reward-model level evaluation; including policy-level evaluations would provide a more comprehensive understanding of practical applications.
- Source: - Lack of Policy-Level Evaluation: The paper focuses exclusively on reward-model level evaluation. Including policy-level evaluations, such as example outputs of language models fine-tuned with the customized reward models, would provide a more comprehensive understanding of the practical applications and effectiveness of the approach.
- Matched meta-review segment: Although the reviewers agree that the paper is interesting and makes a step in the right direction, they also raise a number of critical comments and concerns, including the limited novelty of the baseline approach, the synthetic nature and possible bias of the dataset, the lack of baselines and alternatives, the lack of policy-level evaluation, the insufficient discussion on personalisation, and questions regarding generalisation.
- Human survival label: 
- Human concern quality: 
- Notes: 

### b0IRscfEOb:EjhiYaDJAD:1 auto=`not_found` score=0.084 decision=`reject`
- Claim: Question: What is the point of $ $? It is not associated with any passage and we already have the [SEP] special token to dissociate between the text and the retrieved passages.
- Source: What is the point of $ $ ? It is not associated with any passage and we already have the [SEP] special token to dissociate between the text and the retrieved passages.
- Matched meta-review segment: Furthermore, the aspect of doing joint IE is also mature, and not novel.
- Human survival label: 
- Human concern quality: 
- Notes: 

### eepoE7iLpL:lN5nKGKcEZ:2 auto=`partial` score=0.325 decision=`accept`
- Claim: Baselines do not consider the information from superset, but these baselines be improved by adding the invariant sufficient statistic of the superset?
- Source: - Baselines do not consider the information from superset, but these baselines be improved by adding the invariant sufficient statistic of the superset?
- Matched meta-review segment: The authors took time to provide extensive responses to the reviewer complaints but the reviewers did not take sufficient time to acknowledge these responses.
- Human survival label: 
- Human concern quality: 
- Notes: 

### xibcBSuuq0:WZgHO4PFTI:0 auto=`not_found` score=0.125 decision=`reject`
- Claim: The related works section addresses the background rather than the related works, and the background is insufficient in the exposition to provide tools to understand what will be done later. Trembling Hands Nash Equilibria are never defined, for example.
- Source: - The related works section addresses the background rather than the related works, and the background is insufficient in the exposition to provide tools to understand what will be done later. Trembling Hands Nash Equilibria are never defined, for example.
- Matched meta-review segment: However, it reaches a consensus that the paper could be improved by providing more effective and sufficient experimental results, in terms of comparisons with baselines, and testing the settings beyond the cooperative ones.
- Human survival label: 
- Human concern quality: 
- Notes: 

### cQgjz0mf0r:JFysq9wa5A:4 auto=`survived` score=0.344 decision=`reject`
- Claim: Is SplineCAM an exact method? If so, why does it only work in 2D?
- Source: Is SplineCAM an exact method? If so, why does it only work in 2D?
- Matched meta-review segment: On the other hand, the numerical experiments are not strong and solid to locate this paper as an empirical verification of existing work.
- Human survival label: 
- Human concern quality: 
- Notes: 

### BQvbL2sFQx:QocYHmpKnK:4 auto=`not_found` score=0.178 decision=`reject`
- Claim: Are the accuracy results reported without shifts? The experimental procedure is unclear, please explain.
- Source: Are the accuracy results reported without shifts? The experimental procedure is unclear, please explain.
- Matched meta-review segment: The reviewers agree that while the motivation of the paper is clear, the presentation needs significant improvement, particularly the algorithmic description.
- Human survival label: 
- Human concern quality: 
- Notes: 

### lK2V2E2MNv:Y3CIkpDJh7:0 auto=`survived` score=0.431 decision=`accept`
- Claim: Comprehensive ablation of w/ and wo/ assignment prediction on the same vision/language backbones is missing.
- Source: 1. Comprehensive ablation of w/ and wo/ assignment prediction on the same vision/language backbones is missing.
- Matched meta-review segment: The paper proposes VLAP, a method to bridge vision encoders and language models through assignment prediction.
- Human survival label: 
- Human concern quality: 
- Notes: 

### ApjY32f3Xr:4e1fSBB3OO:1 auto=`partial` score=0.310 decision=`reject`
- Claim: The average L2RE can be skewed if one (or few) of the parameter settings fails (i.e., have L2RE of 100%) while others have very low errors (such as ~1e-4).
- Source: The average L2RE can be skewed if one (or few) of the parameter settings fails (i.e., have L2RE of 100%) while others have very low errors (such as ~1e-4).
- Matched meta-review segment: There was one very critical review, in which it was criticised that there is no clear methodological contribution in this paper.
- Human survival label: 
- Human concern quality: 
- Notes: 

### kmn0BhQk7p:5ZYljDrhoa:2 auto=`not_found` score=0.000 decision=`accept`
- Claim: What is the baseline in Fig. 25?
- Source: 2. What is the baseline in Fig. 25?
- Matched meta-review segment: No match
- Human survival label: 
- Human concern quality: 
- Notes: 

### qBL04XXex6:Cw9UmirZBD:3 auto=`partial` score=0.312 decision=`accept`
- Claim: The paper is based on the motivation that starting with a simple prompt without human annotations for LLMs, BoT may get weak thoughts. However, with aggregation, BoT is capable of deriving a more logical and effective thought chain from them, thereby guiding the subsequent refinement.
- Source: The paper is based on the motivation that starting with a simple prompt without human annotations for LLMs, BoT may get weak thoughts. However, with aggregation, BoT is capable of deriving a more logical and effective thought chain from them, thereby guiding the subsequent refinement.
- Matched meta-review segment: The paper introduces "Boosting of Thoughts" (BoT), a novel approach for problem-solving in Large Language Models (LLMs), marked by its conceptually clear framework that utilizes an iterative trial-and-error mechanism for prompt refinement.
- Human survival label: 
- Human concern quality: 
- Notes: 

### lK2V2E2MNv:Y3CIkpDJh7:2 auto=`partial` score=0.262 decision=`accept`
- Claim: In Tab1,2,3, when compared with previous works, the vision/language backbone is always different. I wonder if using the same backbones as previous works, will the proposed method still outperform them?
- Source: 4. In Tab1,2,3, when compared with previous works, the vision/language backbone is always different. I wonder if using the same backbones as previous works, will the proposed method still outperform them?
- Matched meta-review segment: The paper proposes VLAP, a method to bridge vision encoders and language models through assignment prediction.
- Human survival label: 
- Human concern quality: 
- Notes: 

### BTKAeLqLMw:M95mCPFWRx:0 auto=`not_found` score=0.110 decision=`accept`
- Claim: The technical body of these papers are uncomfortably similar. Combining a number of existing metrics (often in trivial ways) such as quality, diversity, etc. as a new evaluation metric and conducting the evaluations largely with the help of GPTs. And the end goals are also the same–to achieve comparable or better performance with fewer samples. I'm not sure how much "research gap" remains there and how individual works may continue to contribute to that–at least, this concern is still not resolved by this paper.
- Source: The technical body of these papers are uncomfortably similar. Combining a number of existing metrics (often in trivial ways) such as quality, diversity, etc. as a new evaluation metric and conducting the evaluations largely with the help of GPTs. And the end goals are also the same–to achieve comparable or better performance with fewer samples. I'm not sure how much "research gap" remains there and how individual works may continue to contribute to that–at least, this concern is still not resolved by this paper.
- Matched meta-review segment: They evaluate by fine-tuning Llama-13B model, showing solid gains over baselines.
- Human survival label: 
- Human concern quality: 
- Notes: 

### tmsqb6WpLz:KX6fDquf1N:4 auto=`survived` score=0.472 decision=`accept`
- Claim: The basis of the method assumes that p(x)=p(topic,style,factual), but is there a justification to that decomposition? what about arithmetic? how does it fall to this decomposition?
- Source: * The basis of the method assumes that p(x)=p(topic,style,factual), but is there a justification to that decomposition? what about arithmetic? how does it fall to this decomposition?
- Matched meta-review segment: Assumes a decomposition in style, topic, and factual knowledge
- Human survival label: 
- Human concern quality: 
- Notes: 

### eUgS9Ig8JG:i5Pj9In9p1:4 auto=`partial` score=0.235 decision=`accept`
- Claim: Are pre-computation times explicitly indicated in the results?
- Source: 2. I may have missed this but are pre-computation times explicitly indicated in the results?
- Matched meta-review segment: Experiments support the efficiency claims compared to existing simplicial complex learning baselines.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:wckxlkPL42:6 auto=`not_found` score=0.182 decision=`reject`
- Claim: It’s not clear that “Job Sequence Embedding”, if $O_{ij}$ ($j$-th operation of Job $i$) is processed then $A_J(J_i, O_{ij})$ = 1?
- Source: It’s not clear that “Job Sequence Embedding”, if $O_{ij}$ ($j$-th operation of Job $i$) is processed then $A_J(J_i, O_{ij})$ = 1?
- Matched meta-review segment: Clarity Issues: The paper has several writing and typographical errors, unclear descriptions, and missing references.
- Human survival label: 
- Human concern quality: 
- Notes: 

### ApjY32f3Xr:C4sqXJNESI:5 auto=`survived` score=0.425 decision=`reject`
- Claim: Request discussion of limitations of benchmarking tool and avenues for future research to advance PINNs.
- Source: Can you discuss the limitations of your benchmarking tool, and how future research could address these limitations to further advance the field of PINNs?
- Matched meta-review segment: After the rebuttal and discussion phase, however, I still think that the lacking novelty on the conceptual side is indeed a severe weakness of this paper, which could not be compensated by the experimental studies: In my opinion, the conclusions drawn from the benchmark experiments seem to be somewhat limited regarding truly novel insights into PINNs.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 1FWDEIGm33:wXp9GL22N6:1 auto=`partial` score=0.212 decision=`reject`
- Claim: The paper does not clearly explain what the paper suggests beyond proposing a new metaphor and why this is critical.
- Source: I struggled to understand the importance of this problem, even after reading the paper. It is unclear what the implications and potential applications of this work are. The paper confirms that LLMs do not give consistent responses, and that LLMs are not like humans, as shown in Experiments and discussed in Discussion. However, it is not clear what the paper suggests (besides proposing a new metaphor) and why this is critical.
- Matched meta-review segment: The paper does not clearly convey intuitions, justifications and implications of superpositions.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 3wL1tj3kqE:hkZA15bqkJ:2 auto=`not_found` score=0.147 decision=`reject`
- Claim: Could you elaborate on the robustness of your method against different types of distribution shifts compared to existing methods by providing ablation studies?
- Source: Could you elaborate on the robustness of your method against different types of distribution shifts compared to existing methods by providing ablation studies?
- Matched meta-review segment: Further, the motivations are not well addressed, the novelty aspects are unclear, and experimental validation is insufficient, including poor ablations.
- Human survival label: 
- Human concern quality: 
- Notes: 

### miGpIhquyB:9c9pOV3Yi5:2 auto=`survived` score=0.341 decision=`reject`
- Claim: The biases in the reference datasets could also be affecting conformity, faithfulness and performance. It might help to include multiple reference datasets per domain-task combination to evaluate whether the trends hold across them.
- Source: L2: The biases in the reference datasets could also be affecting conformity, faithfulness and performance. It might help to include multiple reference datasets per domain-task combination to evaluate whether the trends hold across them.
- Matched meta-review segment: This paper discusses multiple automatic metrics to evaluate synthetic data generated by LLMs, considering different models and training regimes, namely: faithfulness, diversity, conformity, complexity, and performance.
- Human survival label: 
- Human concern quality: 
- Notes: 

### H9DYMIpz9c:Ie1VUg7cqO:6 auto=`partial` score=0.312 decision=`reject`
- Claim: Q3. Why isn't FMLP also used as a teacher network in Table 1?
- Source: Q3. Why isn't FMLP also used as a teacher network in Table 1?
- Matched meta-review segment: The experiments also showed good gains at the tested scales.
- Human survival label: 
- Human concern quality: 
- Notes: 

### JWrl5pJCnl:L4ACqWaj8p:2 auto=`partial` score=0.200 decision=`reject`
- Claim: What’s the main improvement of Instruct2act? Could the authors list some difference between Instruct2act and VIMA, except for using foundation model to detect the objects?
- Source: 2. What’s the main improvement of Instruct2act? Could the authors list some difference between Instruct2act and VIMA, except for using foundation model to detect the objects?
- Matched meta-review segment: The task prompt is used to generate python code using the LLM, which then interactively queries visual foundation models to perform the task.
- Human survival label: 
- Human concern quality: 
- Notes: 

### BQvbL2sFQx:QiY7LeGJCD:0 auto=`partial` score=0.240 decision=`reject`
- Claim: The algorithmic/mathematical presentation should be clearer. Occasionally notation appears that has not been precisely defined (e.g. $S_o$ on pg. 4 or the use of the $y$ variable). I specifically find Figure 1 hard to understand.
- Source: The algorithmic/mathematical presentation should be clearer. Occasionally notation appears that has not been precisely defined (e.g. $S_o$ on pg. 4 or the use of the $y$ variable). I specifically find Figure 1 hard to understand.
- Matched meta-review segment: The reviewers agree that while the motivation of the paper is clear, the presentation needs significant improvement, particularly the algorithmic description.
- Human survival label: 
- Human concern quality: 
- Notes: 

### H9DYMIpz9c:Ie1VUg7cqO:5 auto=`not_found` score=0.135 decision=`reject`
- Claim: Q2. On a related note, it was not clear to me exactly how the precomputed trajectories were used. My assumption was that instead of training the network in the inner loop only from random initializations, instead the network from the inner loop will be initialized with parameters from one of the training trajectories. Is this correct?
- Source: Q2. On a related note, it was not clear to me exactly how the precomputed trajectories were used. My assumption was that instead of training the network in the inner loop only from random initializations, instead the network from the inner loop will be initialized with parameters from one of the training trajectories. Is this correct?
- Matched meta-review segment: The experiments also showed good gains at the tested scales.
- Human survival label: 
- Human concern quality: 
- Notes: 

### DwcV654WBP:E60zlLaTes:1 auto=`survived` score=0.354 decision=`reject`
- Claim: The paper focuses on the foundation model of video representation learning and claims zero-shot performance is significantly improved by freezing shallow layers and training deeper layers.
- Source: This paper, TVTSv2, is the second version of TVTS paper. It focuses on the foundation model of video representation learning. Specifically, this paper first points out the so called degradation issue existing in video representation field. Based on this degradation observation, this paper proposes a hypothesis that such degradation is from the noisy text data. Accordingly, it freezes the shallow layers of text encoder while training the deeper layers to alleviate this issue. In this way, the zero-shot performance is significantly improved to show the great generalization ability of the proposed training strategy.
- Matched meta-review segment: The authors claim that this model realizes task-agnostic video representation learning.
- Human survival label: 
- Human concern quality: 
- Notes: 

### My7lkRNnL9:CAFQrSYUkW:2 auto=`not_found` score=0.127 decision=`accept`
- Claim: Can we consider PEPITA-Hebbian temporally local since it's a long-term plasticity rule? ... this would be too short for long-term Hebbian changes ... you can treat both parts of the update rule as if they happen for the same network state -- meaning that PEPITA-Hebbian would be temporally local.
- Source: 2. Can we consider PEPITA-Hebbian temporally local since it's a long-term plasticity rule? Since the network is trained with two passes over the same input, the PEPITA-TL approximation adds the first Hebbian term immediately after the first forward pass, so 10s/100s of ms. This would be too short for long-term Hebbian changes (as far as I know), so in your model you can treat both parts of the update rule as if they happen for the same network state -- meaning that PEPITA-Hebbian would be temporally local. (I guess you can account for short-term plasticity as a result of the first forward pass (so non-Hebbian changes proportional to input activity only).)
- Matched meta-review segment: The authors have somewhat addressed these concerns, however, as with much of the ‘biologically-plausible’ neural network literature, the results are obtained using small networks on relatively simple datasets and do not completely match/outperform backpropagation.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 7vVWiCrFnd:cWeTjQ3r9w:0 auto=`partial` score=0.337 decision=`accept`
- Claim: Could you apply your methods on large-scale graphs?
- Source: - Could you apply your methods on large-scale graphs?
- Matched meta-review segment: Although, some of the reviewers raised concerns about the computational complexity and the lack of scalability of the methodology, which in return limits the experiments to small datasets.
- Human survival label: 
- Human concern quality: 
- Notes: 

### SLw9fp4yI6:E3kdriGSqM:2 auto=`not_found` score=0.088 decision=`accept`
- Claim: The question I am trying to get at here is: does toxicity require the full complexity of model arithmetic? It seems like a fairly simple application which may simply require a subtraction, in which case the need for more complex proposed model arithmetic might not be supported here.
- Source: - The first is toxicity which does use both the linear and union operators but only in conjunction with weights that seem to be quite hand tuned (0.9, 0.96, 0.99). It would be useful to also see a simpler framing of this problem with model arithmetic, e.g. simply subtracting the M_toxic instead of the union. The question I am trying to get at here is: does toxicity require the full complexity of model arithmetic? It seems like a fairly simple application which may simply require a subtraction, in which case the need for more complex proposed model arithmetic might not be supported here.
- Matched meta-review segment: The submission introduces a new method for controlled text generation through 'language model arithmetic', in which different models and classifiers are combined to give fine-grained control over generation.
- Human survival label: 
- Human concern quality: 
- Notes: 

### lK2V2E2MNv:85dFa83C5l:3 auto=`partial` score=0.208 decision=`accept`
- Claim: Could ablations with and without the assignment loss be provided to show its effectiveness?
- Source: 1. Could abalations with and without the assignment loss be provided to show its effectiveness?
- Matched meta-review segment: Reviewer 5A8P highlighted the method's incremental nature compared to existing work and requested ablation tests to justify the impact of these changes.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rp5vfyp5Np:cJESK6o5Pr:4 auto=`partial` score=0.309 decision=`reject`
- Claim: Expanding the experimental results to include additional comparison metrics would be valuable. Specifically, how does PALM fare against targeted attacks and various other defense methods?
- Source: 2. Expanding the experimental results to include additional comparison metrics would be valuable. Specifically, how does PALM fare against targeted attacks and various other defense methods?
- Matched meta-review segment: Broaden Evaluations: Expanding the range of defense methods tested and providing a fairer comparison with existing baselines would improve the evaluation's comprehensiveness and fairness.
- Human survival label: 
- Human concern quality: 
- Notes: 

### qBL04XXex6:1lDRac9ePM:0 auto=`partial` score=0.211 decision=`accept`
- Claim: prompt engineering is often model-dependent, and the techniques may evolve as LLM capabilities improve. This may not offer long-term guidance for research unless it uncovers fundamental insights.
- Source: - I agree that prompt engineering is crucial for LLM applications. However, it's worth noting that prompt engineering is often model-dependent, and the techniques may evolve as LLM capabilities improve. This may not offer long-term guidance for research unless it uncovers fundamental insights. This distinction is critical in differentiating academic research from practical production. Therefore, while the paper does offer valuable techniques for prompting the model and achieving good results on evaluation sets, it lacks in-depth discussion of the underlying reasons. This makes the paper better suited for application-oriented conferences rather than ICLR.
- Matched meta-review segment: The approach looks novel and may inspire follow-up research on this.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 3wL1tj3kqE:WvBbfGXxTl:4 auto=`not_found` score=0.069 decision=`reject`
- Claim: Q2: Table 7 shows that the number of encoders can also affect the trade-off between performance and fairness. Why does a single encoder improve the fairness and multiple encoders help generalization performance in the proposed approach?
- Source: Q2: Table 7 shows that the number of encoders can also affect the trade-off between performance and fairness. Why does a single encoder improve the fairness and multiple encoders help generalization performance in the proposed approach?
- Matched meta-review segment: Overall, the number of flaws raised by the reviewers are indeed large.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:zlSWBdRAhX:3 auto=`survived` score=0.388 decision=`reject`
- Claim: No standard deviation or multiple runs reported; reproducibility concern.
- Source: Finally, no standard deviation has been reported nor multiple runs.
- Matched meta-review segment: Incomplete Empirical Evaluations: Missing results in comparison tables and Lack of standard deviations or multiple run results weaken the robustness of the results presented.
- Human survival label: 
- Human concern quality: 
- Notes: 

### kKRbAY4CXv:uwuFudLbCi:0 auto=`not_found` score=0.190 decision=`reject`
- Claim: Lacks references to related work that uses neural networks only at the spatial level with time discretizations, hindering context and comparisons.
- Source: The paper lacks references to related work that adopts neural networks only at the spatial level while using time discretizations to evolve spatial fields over time. Including references to papers like "Evolutional deep neural network (Physical Review E 2021)," "Implicit Neural Spatial Representations for Time-dependent PDEs (ICML 2023)," and "Neural Galerkin Scheme with Active Learning for High-Dimensional Evolution Equations" could help provide context and comparisons.
- Matched meta-review segment: 2) Once the details are recollected from different parts of the paper (namely, the BiNet approach that learns the density) it becomes clear that the paper uses the operator splitting plus BiNet to learn the neural network approximation to boundary potentials.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 1FWDEIGm33:MzDh7uJCEU:3 auto=`not_found` score=0.000 decision=`reject`
- Claim: How do you distinguish between expected and unexpected? Expected by whom?
- Source: (2) How do you distinguish between expected and unexpected? Expected by whom?
- Matched meta-review segment: No match
- Human survival label: 
- Human concern quality: 
- Notes: 

### gYcft1HIaU:9agLWa56ez:1 auto=`survived` score=0.379 decision=`reject`
- Claim: This work does not go into as much detail about the representation of medical knowledge in LLMs, providing only a benchmark without technical insight of what the LLMs might be doing or how they encode medical information.
- Source: * This work does not go into as much detail about the representation of medical knowledge in LLMs, providing only a benchmark without technical insight of what the LLMs might be doing or how they encode medical information.
- Matched meta-review segment: The authors assert, but without much argument, that LLMs must "master adequate knowledge" to be used in this space, but this is not clear to me a priori.
- Human survival label: 
- Human concern quality: 
- Notes: 

### DwcV654WBP:r3JEOduxeC:6 auto=`not_found` score=0.156 decision=`reject`
- Claim: In Table 3, do those models good at retrieval also perform well, like OmniVL, CLIP-ViP, and UMT?
- Source: 5. In Table 3, do those models good at retrieval also perform well, like OmniVL, CLIP-ViP, and UMT?
- Matched meta-review segment: On the other hand, the other two positive reviewers raise concerns about limited experiments to claim the proposed learns a task-agnostic representation.
- Human survival label: 
- Human concern quality: 
- Notes: 

### cQgjz0mf0r:JFysq9wa5A:0 auto=`survived` score=0.382 decision=`reject`
- Claim: the motivation is weak
- Source: 1. the motivation is weak
- Matched meta-review segment: In that sense, the theoretical contributions are not sufficiently novel.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rp5vfyp5Np:vGNqxpozDP:3 auto=`partial` score=0.213 decision=`reject`
- Claim: In the introduction, the paper illustrates the practical implications of targeted attacks on robotics, but the concern is raised that BATTLE is a white-box attack applying perturbations to states. In the context of robotics, its practical applicability is very limited. The paper could benefit from a more thorough clarification or discussion of this concern and its potential implications for practical applications.
- Source: In the introduction, the paper illustrates the practical implications of targeted attacks on robotics, but the concern is raised that BATTLE is a white-box attack applying perturbations to states. In the context of robotics, its practical applicability is very limited. The paper could benefit from a more thorough clarification or discussion of this concern and its potential implications for practical applications.
- Matched meta-review segment: Discuss Limitations: Incorporating a discussion on the limitations of the proposed method would provide a more balanced and complete understanding of the research.
- Human survival label: 
- Human concern quality: 
- Notes: 

### DwcV654WBP:577ajxueBu:2 auto=`not_found` score=0.089 decision=`reject`
- Claim: Could it be that in the video clips the objects/actions of interest were the only moving parts in the scene causing the attention grab?
- Source: COuld it be that in the video clips the objeects/actions of interest were the only moving parts in the scene causing the attention grab?
- Matched meta-review segment: The authors claim that this model realizes task-agnostic video representation learning.
- Human survival label: 
- Human concern quality: 
- Notes: 

### B0wJ5oCPdB:8krLAr9E1i:4 auto=`survived` score=0.384 decision=`reject`
- Claim: How does CoS perform when compared to other potential solutions or methods that might address spatial reasoning in LLMs? Such as program-based CoT that involve symbolic reasoning?
- Source: How does CoS perform when compared to other potential solutions or methods that might address spatial reasoning in LLMs? Such as program-based CoT that involve symbolic reasoning?
- Matched meta-review segment: The paper highlights deficiencies with existing methods and proposes Chain-of-Symbols (CoS), a framework that converts Chain-of-Thought (CoT) reasoning into a sequence of symbols that capture relevant spatial relationships.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rp5vfyp5Np:YktI8n3TeZ:2 auto=`survived` score=0.429 decision=`reject`
- Claim: Is it clear how the attack success rate is defined and whether it could be biased since the intention policy is an approximation of real human intention?
- Source: 2. In experiments, the authors mainly evaluate the attack success rate. However, it is not clear how the success rate is defined. Is it based on whether the victim acts as the intention policy suggests? But would it be biased since the intention policy is just an approximation of the real human intention? What if the intention learning does not learn a desired reward model or intention policy?
- Matched meta-review segment: Important concepts like "intention policy" and "success rate" are not clearly defined.
- Human survival label: 
- Human concern quality: 
- Notes: 

### pYmQId95iR:u5ZC4CoNyk:5 auto=`partial` score=0.287 decision=`reject`
- Claim: Table 3 is referenced on page 9 but does not exist.
- Source: Table 3 is referenced on page 9 but does not exist.
- Matched meta-review segment: This is because given the generality of RL, it is easy to come up with very hard tasks for any class of algorithms, but that does not mean that the task is necessarily best to make progress for a given class of algorithms.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:zlSWBdRAhX:2 auto=`partial` score=0.310 decision=`reject`
- Claim: The experimental section lacks key baselines (RGA, 2SGA, 2 DRL baselines) and missing solution time for OR-Tools; this hinders assessment of performance.
- Source: The experimental section seems to be lacking some baselines - for instance, Table 1 only compares against OR-Tools and dispatching rules, but not against RGA and 2SGA and the 2 DRL baselines. Also, OR-Tools is missing the solution time, so it is difficult to assess how the proposed approach compares in solution time (given that the quality is already worse than the OR-Tools metaheuristics).
- Matched meta-review segment: For instance, comparisons against some existing RL-based methods and metaheuristics are not adequately presented.
- Human survival label: 
- Human concern quality: 
- Notes: 

### lK2V2E2MNv:NE4BzEScxi:0 auto=`survived` score=0.464 decision=`accept`
- Claim: The main concern of this work is the methodology is relatively incremental without new concepts or findings.
- Source: (1) The main concern of this work is the methodology is relatively incremental without new concepts or findings.
- Matched meta-review segment: Their main concern, among others, was the proposed method is incremental, despite its strong results across various tasks.
- Human survival label: 
- Human concern quality: 
- Notes: 

### cQgjz0mf0r:ohnIAzeDZx:1 auto=`partial` score=0.255 decision=`reject`
- Claim: The lack of a need for labels makes this measure ripe for helping to help explain the effects of self-supervised learning. I'm a bit surprised that the authors don't include experiments for why (e.g) BYOL can work by measuring the local complexity of teacher & student networks as they train, and iteratively replace each other.
- Source: The lack of a need for labels makes this measure ripe for helping to help explain the effects of self-supervised learning. I'm a bit surprised that the authors don't include experiments for why (e.g) BYOL can work by measuring the local complexity of teacher & student networks as they train, and iteratively replace each other.
- Matched meta-review segment: Through numerical experiments, they examined the proposed complexity measure to see how it is correlated to important phenomena (grokking, double-descent, memorization) throughout the training.
- Human survival label: 
- Human concern quality: 
- Notes: 

### UVSKuh9eK5:AUeGBXg0Pe:1 auto=`survived` score=0.418 decision=`reject`
- Claim: Conclusion are less convincing due to the limited candidate in each experiment. For instance, in Table 1, it will be interesting to shows the NMI for a subset of LAION with the same number of data to other dataset. Also in table 2, there's only 4 results, please consider adding more variance of dataset and CLIP architecture .
- Source: Conclusion are less convincing due to the limited candidate in each experiment. For instance, in Table 1, it will be interesting to shows the NMI for a subset of LAION with the same number of data to other dataset. Also in table 2, there's only 4 results, please consider adding more variance of dataset and CLIP architecture .
- Matched meta-review segment: The conclusion is less convincing due to the limited candidates in each experiment.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 23OEmHVkpq:8CzSIMq0YG:1 auto=`survived` score=0.348 decision=`reject`
- Claim: RTD definition should be included in the main paper.
- Source: 2. As the authors explained, the RTD was defined in a previous work, but we believe it is important to be defined in the main paper.
- Matched meta-review segment: After reading the paper, reviews, and rebuttal, the AC agrees with the reviewers that the relation between RTD and disentanglement learning should be more clearly and thoroughly justified.
- Human survival label: 
- Human concern quality: 
- Notes: 

### cXs5md5wAq:vb8QNXNzVn:2 auto=`not_found` score=0.190 decision=`reject`
- Claim: Clarity & Explanation: Need clearer explanations for terms and metrics (e.g., keystone bacteria, R2 calculation) for readers from medical backgrounds.
- Source: * Clarity & Explanation: Coming from medicin to ML is always a challenge. It would be helpful if the paper could provide clearer explanations for terms and metrics, especially for readers transitioning from medical backgrounds. E.g. keystone bacteria are not explained, good vs acceptable R2 is unclear to the reader (I can’t even find clearly how is this calculated, despite looking in appendix A which I should not have to for the main outcome), I assume that R2 is highly dependent on the underlying complexity, also the datasets have completely different bacteria suggesting that their purpose was different but this is unclear to me despite reading it several times.
- Matched meta-review segment: Lack of methodological clarity.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 3wL1tj3kqE:YyOvX2x0kY:0 auto=`partial` score=0.205 decision=`reject`
- Claim: The paper lacks comprehensive information about the training of the domain density translator G' for fairness generalization. Training G' is not straightforward due to the varying sensitive attributes across different datasets.
- Source: - The clarity of the paper is lacking, with several important details omitted. For instance, the paper lacks comprehensive information about the training of the domain density translator $G'$ for fairness generalization. Training $G'$ is not straightforward due to the varying sensitive attributes across different datasets.
- Matched meta-review segment: The main issue, evidenced by all reviewers, regards the poor clarity of the presentation/organization of the paper, even lacking of details, which prevent the full understanding of the work.
- Human survival label: 
- Human concern quality: 
- Notes: 

### gtkFw6sZGS:5Ici66sfg0:0 auto=`not_found` score=0.121 decision=`accept`
- Claim: LLMs should somehow emulate human capabilities and not other LLMs' capabilities.
- Source: - LLMs should somehow emulate human capabilities and not other LLMs' capabilities.
- Matched meta-review segment: The Auto-J evaluator could be used by the research community who focus on open source LLMs.
- Human survival label: 
- Human concern quality: 
- Notes: 

### w73feIekdO:NLKFsY27K9:0 auto=`survived` score=0.426 decision=`reject`
- Claim: results on the two datasets are not convincing.
- Source: While I understand the rationale and setup of the problem for translating motion vector inputs as coresets and tracking, the results on the two datasets are not convincing. While the paper talks a lot about how this approach is substantially better in comparison to neural-net based methods, it fails to refer to any of the classic methods in tracking where clustering, robust statistical methods are used. The paper does refer to a review paper and states that there are over 1000 articles on the subject. However, if the central aim of the paper is to demonstrate the advancement in tracking algorithms the paper should demonstrate the effectiveness of the algorithm designed by comparing it with at least one alternative (e.g. mean-shift based tracking , Comaniciu et al (CVPR 2000)). I note that the mean-shift based tracker performed in real-time in low computational power settings for given candidate regions in a video over two decades ago.
- Matched meta-review segment: Firstly, the paper exclusively showcases results in only two scenarios, with the demonstration often lacking clarity, comprehensive reporting, and in-depth analysis.
- Human survival label: 
- Human concern quality: 
- Notes: 

### gYcft1HIaU:K0w3kEaTHx:4 auto=`partial` score=0.239 decision=`reject`
- Claim: Clarify why common diseases are considered in the knowledge base since ICD10-based selection cites common diseases for MedDisK.
- Source: The authors claim that current QA-based medical evaluation datasets cover only some common diseases. However, in section 3.1 where the authors introduce their proposed knowledge base, it is said that "We first select a subset from the ICD10 database according to whether the diseases are common in clinical (determined by clinical experts) and are statistically frequent in EHR (Electronic Health Record), resulting in 10,632 common diseases." I wonder why they also consider common diseases in their knowledge base?
- Matched meta-review segment: The authors assert, but without much argument, that LLMs must "master adequate knowledge" to be used in this space, but this is not clear to me a priori.
- Human survival label: 
- Human concern quality: 
- Notes: 

### miGpIhquyB:yPyy646e3D:0 auto=`partial` score=0.306 decision=`reject`
- Claim: The heavy use of DistilBERT accuracies in the evaluation framework confounds faithfulness with the difficulty (or complexity) of the dataset, making some findings questionable.
- Source: 1. I like the general idea of the proposed evaluation framework, but my biggest concern about this framework is the heavy use of DistilBERT accuracies in the evaluation framework. For the faithfulness metric, the framework is evaluating the performance of DistilBERT on the generated dataset. This confounds faithfulness with the difficulty (or complexity) of the dataset. This makes some of the finding questionable. For example, is there really a tradeoff between faithfulness and diversity/complexity, or is this correlation comes from the correlation between difficulty and diversity/complexity? I wonder if the authors can provide gold evaluation results for the DistilBERT models.
- Matched meta-review segment: This paper discusses multiple automatic metrics to evaluate synthetic data generated by LLMs, considering different models and training regimes, namely: faithfulness, diversity, conformity, complexity, and performance.
- Human survival label: 
- Human concern quality: 
- Notes: 

### kmn0BhQk7p:aPvo3w4FSN:0 auto=`survived` score=0.462 decision=`accept`
- Claim: Some experiment setups should be justified. For some attributes (e.g., MSE for age), accuracy is not the correct metric.
- Source: 1. Some experiment setups should be justified. For some attributes (e.g., MSE for age), accuracy is not the correct metric.
- Matched meta-review segment: However, some constructive criticisms are noted, such as the need for additional justification of certain experiment setups, the consideration of alternative metrics for specific attributes, and ethical considerations regarding the use of sensitive topics.
- Human survival label: 
- Human concern quality: 
- Notes: 

### AOSsLRKQrX:1wptEDWn4N:0 auto=`survived` score=0.358 decision=`reject`
- Claim: Were the hyperparameters tuned for the baselines?
- Source: - Were the hyperparameters tuned for the baselines?
- Matched meta-review segment: This setting is quite interesting and novel, as pointed out by the reviewers, and the paper demonstrates how the proposed approach is able to improve over baselines.
- Human survival label: 
- Human concern quality: 
- Notes: 

### UVSKuh9eK5:lo6OmS3vso:0 auto=`survived` score=0.542 decision=`reject`
- Claim: There is no description or motivation for the attribute selection, are those attributes randomly selected or generated? How do the authors guarantee that those attributes are not present or co-occur less in the training data?
- Source: + There is no description or motivation for the attribute selection, are those attributes randomly selected or generated? How do the authors guarantee that those attributes are not present or co-occur less in the training data?
- Matched meta-review segment: It does not guarantee that the attributes in test set are not present or co-occur less in the training data.
- Human survival label: 
- Human concern quality: 
- Notes: 

### yacRhge4zQ:pKsEW8Yja4:0 auto=`partial` score=0.211 decision=`reject`
- Claim: A key assumption is the common-knowledge of a pre-calculated PF among the considered critera, specifically privacy, fairness and model utility. This can be difficult to satisfy in practice.
- Source: A key assumption is the common-knowledge of a pre-calculated PF among the 
considered critera, specifically privacy, fairness and model utility. This can be difficult to satisfy in practice.
- Matched meta-review segment: However, a key concern raised by all reviewers is the assumption of a pre-calculated Pareto Frontier (PF) and its practical feasibility.
- Human survival label: 
- Human concern quality: 
- Notes: 

### IefMMX12yk:Z2Yp4ywhAo:0 auto=`survived` score=0.458 decision=`reject`
- Claim: GNAS methods nowadays have been expanded to large-scale datasets, while the paper only showed the results on Physics and Ogbn-Arxiv datasets. Could you please give a more overall perfomance comparison with other GNAS methods like GUASS on large-scale OGB datasets?
- Source: 1. GNAS methods nowadays have been expanded to large-scale datasets, while the paper only showed the results on Physics and Ogbn-Arxiv datasets. Could you please give a more overall perfomance comparison with other GNAS methods like GUASS on large-scale OGB datasets? 

 [1] Large-scale graph neural architecture search, ICML 2022.
- Matched meta-review segment: The reviewers raise important points regarding the evaluation of the proposed method and suggest expanding the comparison to include more recent GNAS methods, especially on large-scale datasets such as OGB datasets, and considering benchmarks like NAS-Bench-Graph.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rEQ8OiBxbZ:AP19rMVi04:4 auto=`survived` score=0.342 decision=`reject`
- Claim: Given the proposed method centers on pre-trained representation learning, what form do the learned representation embeddings take for downstream tasks?
- Source: 2. Given the proposed method centers on pre-trained representation learning, what form do the learned representation embeddings take for downstream tasks?
- Matched meta-review segment: Given the limited supporting evidence for the proposed method's advantages, I recommend rejecting the paper.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 7vVWiCrFnd:aHtDQsXakn:3 auto=`survived` score=0.391 decision=`accept`
- Claim: What is the complexity of GNNs with phantom nodes or phantom edges for node classification and link prediction?
- Source: 3. What's the complexity of GNNs with phantom nodes or phantom edges, for node classification and link prediction ,respectively?
- Matched meta-review segment: Within this framework the authors show how to systematically extend the capabilities of GNNs in modeling complex distributions and inference targets, with a particular focus on phantom nodes and phantom edges, showcasing their empirical improvements in real-world applications of GNNs.
- Human survival label: 
- Human concern quality: 
- Notes: 

### BQvbL2sFQx:ggRvsrGJrq:1 auto=`not_found` score=0.103 decision=`reject`
- Claim: The compelling motivation for shift equivariance is not supported by problem specific datasets. All experiments are done on generic datasets. CIFAR-10 does not seem to fit the motivation at all with its 32x32 images. It seems like a misfit for the purpose of the paper. I expect that the industrial applications involve high-resolution imagery. If authors can provide results on high-resolution datasets, especially from the industrial domain this will make the results a lot more compelling.
- Source: - The compelling motivation for shift equivariance is not supported by problem specific datasets. All experiments are done on generic datasets. CIFAR-10 does not seem to fit the motivation at all with its 32x32 images. It seems like a misfit for the purpose of the paper. I expect that the industrial applications involve high-resolution imagery. If authors can provide results on high-resolution datasets, especially from the industrial domain this will make the results a lot more compelling. There is a recent dataset described here: https://arxiv.org/pdf/2303.06673.pdf. I am sure that more search will reveal more datasets like this. I remember encountering similar problems on kaggle.
- Matched meta-review segment: The authors did not provide any feedback, thus none of the concerns raised by the reviewers were addressed.
- Human survival label: 
- Human concern quality: 
- Notes: 

### AZGIwqCyYY:aWxMIfTpWd:3 auto=`partial` score=0.252 decision=`accept`
- Claim: The paper presents an appealing goal, providing generalized Hamiltonian representations consistent across different physical domains. However, given the presented quantitative and qualitative results it is hard to judge the actual generalization and performance of the framework as detailed in the following points:
- Source: The paper presents an appealing goal, providing generalized Hamiltonian representations consistent across different physical domains. However, given the presented quantitative and qualitative results it is hard to judge the actual generalization and performance of the framework as detailed in the following points:
- Matched meta-review segment: The paper is well-written and interesting, the approach sensible, and the qualitative and quantitative results are strong and the benefit of meta-learning appears clear.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 10eQ4Cfh8p:w67nfG2dMW:3 auto=`survived` score=0.375 decision=`reject`
- Claim: The proposed framework suggests a novel perspective for solving FJSP. Unlike the majority of iterative improving approaches that often perform improvement steps from a complete solution, the proposed framework employs "improving" actions during solution construction.
- Source: This paper proposes an end-to-end RL framework to solve the Flexible Job-Shop Problem (FJSP). The framework consists of two major components: a generation model that produces an assignment of operations that updates the partial solution, and an improving model that refines the current partial solution. By repeating the generation and improving steps until the complete solution is found, the proposed framework finds a solution for FJSP.
- Matched meta-review segment: Strengths: The paper's strength lies in its novel dual-model approach to solving FJSP, which combines solution generation and improvement in a concurrent training framework.
- Human survival label: 
- Human concern quality: 
- Notes: 

### gtkFw6sZGS:5yEYAAadyY:0 auto=`survived` score=0.343 decision=`accept`
- Claim: The papers is a large engineering effort (e.g., distilling GPT-4 for the task of evaluation) without much novel ideas
- Source: - The papers is a large engineering effort (e.g., distilling GPT-4 for the task of evaluation) without much novel ideas (I do not think that a paper needs to be novel to be accepted, but this paper does score low in terms of novelty)
- Matched meta-review segment: I do think that the paper does not present anything massively significant in terms of new science, but the overall flow of the methods in the paper present a novel artifact in terms of the Auto-J evaluator that could be useful to the community.
- Human survival label: 
- Human concern quality: 
- Notes: 

### AJBkfwXh3u:q90TUxGqx8:2 auto=`partial` score=0.227 decision=`accept`
- Claim: In Table 2, for Node classification task, OrphicX performs better than DyGNNExplainer on DTree-Grid dataset but is not bolded?
- Source: In Table 2, for Node classification task, OrphicX performs better than DyGNNExplainer on DTree-Grid dataset but is not bolded?
- Matched meta-review segment: The reviewers comment that most of the benchmarks are in static datasets, so it is not clear how the method would actually behave in dynamical graphs.
- Human survival label: 
- Human concern quality: 
- Notes: 

### dYjuJGTEbc:S9Hah6oZoZ:3 auto=`not_found` score=0.198 decision=`reject`
- Claim: What do the two axes in Fig.3 represent? It should be labeled in the figure.
- Source: 5. What do the two axes in Fig.3 represent? It should be labeled in the figure.
- Matched meta-review segment: Moreover, several aspects of the theoretical results are noted to require detailed rewriting to enhance clarity and comprehensibility.
- Human survival label: 
- Human concern quality: 
- Notes: 

### miGpIhquyB:yPyy646e3D:4 auto=`not_found` score=0.115 decision=`reject`
- Claim: Question on prompt design and sensitivity: how prompts were selected and whether findings are sensitive to different prompts.
- Source: 2. How do design or select prompts for the study conducted in your paper? Have you checked the sensitivity of the findings with respect to different prompts?
- Matched meta-review segment: Findings reveal differences in instruction-tuned models for data generation vs other model families, where they find a loss of diversity.
- Human survival label: 
- Human concern quality: 
- Notes: 

### lNIj5FdXsC:W8u5ZMVoLw:2 auto=`partial` score=0.246 decision=`reject`
- Claim: The paper proposes a way to utilize RNN to adopt hidden states through multiple layers. It claims that the new method helps improve long-range information processing.
- Source: 1. The paper proposes a way to utilize RNN to adopt hidden states through multiple layers. It claims that the new method helps improve long-range information processing.
- Matched meta-review segment: The only novelty of GRED is the usage of a linear RNN, which is equivalent to using a linear layer with shared parameters as the UPD function in Definition 1.
- Human survival label: 
- Human concern quality: 
- Notes: 

### miGpIhquyB:REwQirNHgK:0 auto=`not_found` score=0.159 decision=`reject`
- Claim: Unsupported Claims. The paper raises a claim that "reinforcement learning with human feedback (RLHF) in ChatGPT leads to a significant degradation in synthetic dataset generation capabilities." However, the paper lacks a clear explanation of how the authors attribute this performance drop specifically to RLHF.
- Source: 2. Unsupported Claims. The paper raises a claim that "reinforcement learning with human feedback (RLHF) in ChatGPT leads to a significant degradation in synthetic dataset generation capabilities." However, the paper lacks a clear explanation of how the authors attribute this performance drop specifically to RLHF. A more detailed description of the experimental setup and results related to this assertion would enhance the paper's clarity and credibility.
- Matched meta-review segment: Strengths: This paper presents valuable work towards evaluating generations of language models, and reveals important insights into what might be determining the quality of generated data under different training regimes, especially instruction tuning which has led to many generated datasets.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 1FWDEIGm33:MzDh7uJCEU:1 auto=`not_found` score=0.149 decision=`reject`
- Claim: Conclusions are overstated. The paper states "we will see that discarding the old metaphor may question the interpretation of recent studies aiming at characterizing the values, personality traits, social skills or moral values of LLMs using tools developed to measure attributes of human psychology". The current status of the argument has not led to this conclusion directly.
- Source: (2) Conclusions are overstated. The paper states "we will see that discarding the old metaphor may question the interpretation of recent studies aiming at characterizing the values, personality traits, social skills or moral values of LLMs using tools developed to measure attributes of human psychology". The current status of the argument has not led to this conclusion directly. The paper needs to reconnect and build out a cohesive careful argument in order to support this claim.
- Matched meta-review segment: It questions interpretability of existing work using psychological questionnaires to characterize LLMs' values.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rEQ8OiBxbZ:AP19rMVi04:3 auto=`not_found` score=0.156 decision=`reject`
- Claim: What exactly constitutes the input for TokenGT-3D? Is it the original molecules, or do you utilize each local structure segmentation after masking and perturbation? Or is it the masked and perturbed local structure segmentations of a single molecule, or something else entirely?
- Source: 1. What exactly constitutes the input for TokenGT-3D? Is it the original molecules, or do you utilize each local structure segmentation after masking and perturbation? Or is it the masked and perturbed local structure segmentations of a single molecule, or something else entirely?
- Matched meta-review segment: This method leverages the geometric information of local molecular structures by dividing the molecule into tetrahedra of a few atoms and using a graph-based representation.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 7vVWiCrFnd:uXWt0SbIG0:2 auto=`partial` score=0.250 decision=`accept`
- Claim: Certain related works are missing in the paper. Recent works on Factor Graph Neural Networks (FGNN) [1] are highly related works in establishing connections between PGMs and GNNs. A small discussion on the relevance would be pertinent.
- Source: Certain related works are missing in the paper. Recent works on Factor Graph Neural Networks (FGNN) [1] are highly related works in establishing connections between PGMs and GNNs. A small discussion on the relevance would be pertinent.
- Matched meta-review segment: Although the perspective is new, due to the lack of scalability it is only applicable to small graphs.
- Human survival label: 
- Human concern quality: 
- Notes: 

### 9L9j5bQPIY:91NkdJpVId:0 auto=`not_found` score=0.167 decision=`reject`
- Claim: In Section 4.4, it seems to me that there is nothing to train with a k-NN classifier when the meta-encoder is frozen. What do you mean by training here?
- Source: In Section 4.4, it seems to me that there is nothing to train with a k-NN classifier when the meta-encoder is frozen. What do you mean by training here?
- Matched meta-review segment: The resulting latent representation (via a nearest neighbor prediction function) of the autoencoder is capable of predicting what modality the original model was being trained on and predicting the accuracy of the classifier to a reasonable degree.
- Human survival label: 
- Human concern quality: 
- Notes: 

### pYmQId95iR:u5ZC4CoNyk:6 auto=`partial` score=0.217 decision=`reject`
- Claim: The authors suggest categorising the aspects that make the benchmark challenging and evaluating multiple state-of-the-art algorithms per category across difficulties; this is a suggested change or experiments.
- Source: - Categorise the various aspects of this benchmark that make it supposedly challenging for current RL (e.g sparse rewards, exploration, long horizon). 
- Then choose 2 or more state-of-the-art algorithms in each category to evaluate.
- Evaluate them on all (or sample/representative) difficulty levels of all 40 games (or a sample/representative subset).
- Finally, provide a detailed discussion on why various algorithms belonging to each category succeed or fail on various tasks with various difficulty levels.
- Matched meta-review segment: This paper proposes a benchmark for neural algorithmic reasoning and evaluates a variety of algorithms on these tasks.
- Human survival label: 
- Human concern quality: 
- Notes: 

### IefMMX12yk:aj2q9ksHth:3 auto=`partial` score=0.246 decision=`reject`
- Claim: 5. How many edges can be deleted in the adopted datasets?
- Source: 5. How many edges can be deleted in the adopted datasets?
- Matched meta-review segment: The reviewers raise important points regarding the evaluation of the proposed method and suggest expanding the comparison to include more recent GNAS methods, especially on large-scale datasets such as OGB datasets, and considering benchmarks like NAS-Bench-Graph.
- Human survival label: 
- Human concern quality: 
- Notes: 

### jXR5pjs1rV:dXSWosECmZ:1 auto=`survived` score=0.503 decision=`reject`
- Claim: Lack of Baselines and Alternatives: Comparison of fine-tuned reward models to a prompted language model would strengthen the contribution.
- Source: - Lack of Baselines and Alternatives: Since (as mentioned in the previous point) prompted language models already show significant capability of customizing their outputs to align with the preferences described in their prompt, comparison of fine-tuned reward models to a prompted language model would further strengthen the contribution.
- Matched meta-review segment: The main contributions are the introduction of a novel synthetic preference dataset specifically designed for the customization of reward models, and a baseline training methodology employing multi-stage fine-tuning.
- Human survival label: 
- Human concern quality: 
- Notes: 

### cQgjz0mf0r:3gM8OP4zZK:3 auto=`partial` score=0.268 decision=`reject`
- Claim: I do not understand how it should be used and how it helps to analyze the actual behavior of the deep classifier
- Source: I think that the proposed measure is an interesting and simple approach to approximate the number of convex regions (in some sense the complexity) of the classifier around the training data. However, I do not understand how it should be used and how it helps to analyze the actual behavior of the deep classifier.
- Matched meta-review segment: The methodology is not well explained, and the experimental results are not exposed in well organized way.
- Human survival label: 
- Human concern quality: 
- Notes: 

### rGvDRT4Z60:yub0t46EhK:2 auto=`not_found` score=0.170 decision=`reject`
- Claim: How does the framework work in case of some distribution shift? This is especially important in the context of my question above.
- Source: - How does the framework work in case of some distribution shift? This is especially important in the context of my question above.
- Matched meta-review segment: See the issues raised above, most related to concerns regarding prior work, presentation of results, and implications of the rejection mechanism in fairness in practice.
- Human survival label: 
- Human concern quality: 
- Notes: 
