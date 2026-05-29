# Concern Survival LLM Calibration

- Input items: 500
- Labels: 500
- High-confidence training candidates: 155
- Auto/LLM agreement: 62.8%

## Label Counts

| Label set | Counts |
| --- | --- |
| `auto_label_counts` | `{"not_found": 214, "partial": 245, "survived": 41}` |
| `llm_meta_review_match_counts` | `{"not_found": 134, "partial": 280, "survived": 7, "unsure": 79}` |
| `llm_concern_quality_counts` | `{"high": 68, "low": 229, "medium": 195, "unsure": 8}` |
| `llm_ac_treatment_counts` | `{"endorsed_or_relied_on": 9, "mentioned_as_resolved_or_outweighed": 2, "mentioned_neutrally": 304, "not_mentioned": 185}` |
| `high_confidence_match_counts` | `{"not_found": 1, "partial": 148, "survived": 6}` |

## Agreement

- `cQgjz0mf0r:y2KQyGW4Ax:3` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Suggest deeper analysis of training dynamics in settings like self-supervised to add theoretical insight.
  - Meta: Through numerical experiments, they examined the proposed complexity measure to see how it is correlated to important phenomena (grokking, double-descent, memorization) throughout the training.
  - Rationale: The meta-review discusses overlap with existing work and notes limited novelty and weak experiments, which aligns with the reviewer concern about deeper analysis in self-supervised settings. However, the meta-review does not explicitly reiterate the exact claimed concern about deeper training dynamics analysis in se...
- `JWrl5pJCnl:oNACfe2nfm:0` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Important related work RT-2 [1] is missing, likely because it is too recent to be included and discussed.
  - Meta: The paper does not convincingly articulate what is technically novel w.r.t.
  - Rationale: The meta-review discusses novelty and compares to prior work, but the specific concern in claim_text is that important related work is missing (RT-2). The meta-review does not address this exact concern; it mentions general novelty concerns and comparisons to state of the art, but does not hinge on whether RT-2 is m...
- `rEQ8OiBxbZ:s1KaX4GPTJ:6` auto=`partial` llm=`partial` quality=`high`
  - Claim: Can the authors comment on the disparity of the approach of their validation scores on moleculeNet vs those on the large-scale challenge?
  - Meta: The reviewers expressed serious concerns about the unconvincing experiments, which lack empirical evidence to support the proposed approach's superiority.
  - Rationale: The meta-review discusses concerns about unconvincing experiments and limited empirical evidence, which aligns with the claimed concern about disparity/validation scores; the AC treatment shows reliance on the experiments' credibility in evaluating superiority. The evidence is specific (unconvincing experiments, lac...
- `AZGIwqCyYY:FBXRP3lnzq:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: the cases where meta-learning is not necessarily beneficial should also be revealed, with which the claims would become more falsifiable and convincing.
  - Meta: The reviewers generally found the paper well-written and well-motivated and the experiments interesting and compelling within the setting of Hamiltonian systems.
  - Rationale: The claim concerns revealing negative cases where meta-learning is not beneficial. The meta-review discusses limitations and unclear scope but does not substantively repeat or rely on the specific concern about not-beneficial cases; it mentions weaknesses broadly. There is no clear semantic match showing the meta-re...
- `My7lkRNnL9:RzQfnEwCrf:4` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Overall, the contribution is judged as insufficient empirically or theoretically.
  - Meta: However, they have raised concerns, e.g., about the limited scope of the empirical and theoretical evaluation.
  - Rationale: The meta-review notes concerns about limited empirical/theoretical evaluation but does not strongly endorse or rely on the concern; it is mentioned as a weakness and somewhat addressed. The reviewer claim about overall insufficiency is echoed but not central to the meta-review’s conclusion. Evidence strength is mode...
- `xNdE7RiRyP:5DuTHFMr8O:3` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Is meta-learning used only as part of pre-training or also for on-device training? It seems to me that classical transfer learning is done on-device. Do the authors think that on-device meta-learning techniques, e.g. few-shot learning, would be a feasible/reasonable approach?
  - Meta: In particular, the authors introduce a sparse update learning method that trains convolutional neural networks with less memory and computation demands.
  - Rationale: The meta-review discusses on-device training and mentions limited applicability and comparisons; the claim asks about meta-learning on-device vs pre-training. The meta-review talks about on-device training via sparse update method but does not clearly endorse or rely on meta-learning concepts. The concern’s specific...
- `IefMMX12yk:MqJPeccgXL:1` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Insufficient experiments on large-scale graph data: The large-scale graph data set used in the experiments of this article only contains OGBN-ARXIV. Therefore, more experiments on large-scale graph data are needed to verify the performance of the GASSIP method.
  - Meta: Introducing a joint mechanism for graph data and architecture, the proposed method, Lightweight Graph Neural Architecture Search with Graph Sparsification and Network Pruning (GASSIP), identifies crucial sub-architectures using valuable graph data.
  - Rationale: The meta-review discusses a claim about insufficient experiments on large-scale data and recommends more comparisons, including on large datasets like OGB, NAS-Bench-Graph, etc. The meta-review mentions the idea of evaluation and comparisons but does not directly repeat the exact concern phrase. It covers the issue...
- `IefMMX12yk:aj2q9ksHth:0` auto=`partial` llm=`partial` quality=`medium`
  - Claim: The research problem is not novel to the community. There have been a series of work for the co-optimization of neural architecture and data, even at the domain of graph NAS and graph data.
  - Meta: The paper addresses a gap in the existing research on Graph Neural Architecture Search (GNAS) by focusing on its applications in resource-constrained scenarios.
  - Rationale: The claim concerns novelty and prior work on co-optimization of architecture and data in graph NAS. The meta-review discusses GNAS, sparsification, and evaluation, but does not directly claim that novelty is repetitive; it mentions related works and gaps but does not substantively endorse or rely on the specific con...
- `7QlKLvfVge:uuzRX1XOFc:3` auto=`partial` llm=`partial` quality=`low`
  - Claim: In Figure 2, the value of C for certain layers is not significant. Is it possible to skip some layers when computing v?
  - Meta: The authors should present the proposed method clearly without creating any possible misunderstnging!
  - Rationale: The meta-review mentions clarity of explanation and avoiding misunderstanding, which aligns with the claim about Fig.2 and skipping layers, but the match is indirect and focuses on motivation and responses rather than the specific claim about C values being non-significant. The AC treatment is neutral/mentioned as p...
- `7QlKLvfVge:LsvjaIpscH:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: The memory and computational complexity could be analyzed more thoroughly, especially how the approach scales with larger datasets/models. Are there ways to make the optimization more efficient?
  - Meta: How can your projection keep the performance?'' and ``The proof needs to be more rigorous.
  - Rationale: Meta-review text discusses broad critiques of motivation, clarity, and rigor, but does not mention the specific reviewer concern: the claim about memory/computation analysis and scaling. The matched_meta_segment and matched_terms are unrelated (“more”). Therefore the concern is not found. Evidence strength is low be...

## Disagreement

- `miGpIhquyB:fPDC3rXMpU:2` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: Tradeoffs (Figure 2) are shown only with respect to temperature; other sampling-control variables like top-p should be explored to determine if the observed tradeoffs are specific to temperature.
  - Meta: there were some issues with the definitions of some metrics, and some experimental settings which were not fully explored.
  - Rationale: The reviewer claim concerns tradeoffs across sampling variables like top-p and temperature. The meta-review discusses metrics for evaluating generated data, differences across models and training regimes, and notes issues with definitions and experimental settings. It does not substantively mention or rely on the sp...
- `rp5vfyp5Np:YktI8n3TeZ:1` auto=`survived` llm=`partial` quality=`medium`
  - Claim: To obtain human preference labels, one need to first collect diverse behavior data so that human can pick the intended policy.
  - Meta: Complexity and Uncertainty in Intention Policy Learning: The process of learning intention policy based on human preferences introduces extra requirements and uncertainties, including the expensive collection of human preference data and potential biases.
  - Rationale: The reviewer claim concerns that human preference data collection adds expense and uncertainty. The meta-review discusses complexity and uncertainty of intention policy learning, mentioning expensive data collection and biases in weaknesses, but does not explicitly repeat or endorse the exact reviewer concern as a c...
- `b0IRscfEOb:ucX6pk7TSU:0` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: As one of the emphases of this paper is the integration of EL and RE tasks. The mutual influence between EL and RE should be more clearly demonstrated in the experimental analysis section.
  - Meta: While ReLiK's integration of entity linking and relation extraction is commendable, the architecture of each module within it remains maybe too similar to existing models.
  - Rationale: The claim concerns whether there is a mutual influence between EL and RE and its demonstration in experiments. The meta-review focuses on integration being commendable but criticizes similarity to existing models and maturity/not novel. It does not substantively discuss the specific need to demonstrate mutual influe...
- `eUgS9Ig8JG:4sGhXacqSF:6` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Section 4.2 claims need clearer explanation to ensure they act on oriented features; simplicial awareness discussion is necessary and a connection to existing methods should be clarified.
  - Meta: While reviewers appreciate the method and the computational saving the fact that GNN works have followed this path of adding features and proving WL expressive power reduces a bit the novelty in this work.
  - Rationale: The reviewer claim concerns Section 4.2 clarity about simplicial-aware features and connection to existing methods. The meta-review discusses efficiency, WL expressive power, novelty, and scalability, but does not clearly address Section 4.2 clarity or oriented features or simplicial awareness discussion. It mention...
- `JWrl5pJCnl:oNACfe2nfm:2` auto=`partial` llm=`unsure` quality=`low`
  - Claim: This work mentions the utilization of two types of LLMs: text-davinci-003 and LLaMA-Adapter. Could you provide an explanation on the performance differences between these two?
  - Meta: While the authors tried to perform a few additional experiments to allay these concerns, I do not think they were convincing.
  - Rationale: The claim asks for explanation on performance differences between two LLMs (text-davinci-003 and LLaMA-Adapter). The meta-review discusses general limitations and lack of novelty, empirical evaluations, and does not mention these two specific LLM types or compare them. There is lexical overlap (“experiments” etc.) b...
- `AJBkfwXh3u:KidnSLrJ44:5` auto=`survived` llm=`partial` quality=`medium`
  - Claim: 5. How to interpret the 'dynamic' in DyGNNExplainer? Can the datasets in experiments support the augment raised in this paper, as it seems there are no dynamic graph in experiments?
  - Meta: The reviewers comment that most of the benchmarks are in static datasets, so it is not clear how the method would actually behave in dynamical graphs.
  - Rationale: The meta-review acknowledges that most benchmarks are static and questions applicability to dynamic graphs, which aligns with the reviewer claim about interpretation of 'dynamic' in DyGNNExplainer and lack of dynamic graphs in experiments. However, the meta-review does not substantively repeat or rely on the exact r...
- `kKRbAY4CXv:uwuFudLbCi:2` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: Clarification needed on relationship to Lin et al. 2023a/b and their convolution/Gaussian representations; unclear author contribution beyond time-dependence.
  - Meta: This is completely unreproducible, unclear and is just not ready for publication in any form.
  - Rationale: The meta-review discusses the paper's clarity and reproducibility, but does not address the specific reviewer claim about relationship to Lin et al. 2023a/b or their convolution/Gaussian representations, nor about author contributions beyond time-dependence. The claim is not clearly present in the meta-review, and t...
- `My7lkRNnL9:MQTHAuclRi:1` auto=`not_found` llm=`partial` quality=`low`
  - Claim: Figure readability issues hinder interpretation (hard to read figures, overlap not easily visible, colors inconspicuous).
  - Meta: While the results of the paper are interesting, the empirical evaluation is not sufficiently significant to warrant a spotlight or oral.
  - Rationale: The claim concerns readability in figures. The meta-review discusses empirical evaluation, scope, and acceptance verdict, but does not address figure readability or clarity issues. The match is only tangential if at all, and the meta-review does not substantively repeat or rely on the claim. Evidence strength is low...
- `rhgIgTSSxW:yVdQ7kKCcl:1` auto=`partial` llm=`not_found` quality=`low`
  - Claim: Why is the T function required to use LinearWithoutBias?
  - Meta: The fourth reviewer seems unfair, and is the author of one of the competing methods puts forward in the critical review.
  - Rationale: The auto_survival_label is about a concern in a specific reviewer dispute (fourth reviewer unfair). The meta-review discusses overall quality and positioning relative to prior art, but does not reiterate, endorse, or rely on the specific concern about the fourth reviewer or unfairness. It mentions fairness of a revi...
- `lK2V2E2MNv:Vjq2iwj6Mu:0` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: The motivation for restricting the learned parameter space to just linear layers is unclear -- it would have been more interesting to see more analysis around different learned parameter space including non-linear layers.
  - Meta: Overall, Reviewers m8gW and 5A8P provided positive reviews, finding the proposed method interesting and acknowledging its achievement of state-of-the-art results.
  - Rationale: The meta-review discusses the paper's incremental nature and mentions responses to rebuttals, but it does not substantively repeat or rely on the specific concern about restricting learned parameter space to linear layers or analysis of non-linear layers. The claim text cites this motivation issue, but the meta-revi...

## High Confidence

- `rEQ8OiBxbZ:s1KaX4GPTJ:6` auto=`partial` llm=`partial` quality=`high`
  - Claim: Can the authors comment on the disparity of the approach of their validation scores on moleculeNet vs those on the large-scale challenge?
  - Meta: The reviewers expressed serious concerns about the unconvincing experiments, which lack empirical evidence to support the proposed approach's superiority.
  - Rationale: The meta-review discusses concerns about unconvincing experiments and limited empirical evidence, which aligns with the claimed concern about disparity/validation scores; the AC treatment shows reliance on the experiments' credibility in evaluating superiority. The evidence is specific (unconvincing experiments, lac...
- `IefMMX12yk:MqJPeccgXL:1` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Insufficient experiments on large-scale graph data: The large-scale graph data set used in the experiments of this article only contains OGBN-ARXIV. Therefore, more experiments on large-scale graph data are needed to verify the performance of the GASSIP method.
  - Meta: Introducing a joint mechanism for graph data and architecture, the proposed method, Lightweight Graph Neural Architecture Search with Graph Sparsification and Network Pruning (GASSIP), identifies crucial sub-architectures using valuable graph data.
  - Rationale: The meta-review discusses a claim about insufficient experiments on large-scale data and recommends more comparisons, including on large datasets like OGB, NAS-Bench-Graph, etc. The meta-review mentions the idea of evaluation and comparisons but does not directly repeat the exact concern phrase. It covers the issue...
- `IefMMX12yk:aj2q9ksHth:0` auto=`partial` llm=`partial` quality=`medium`
  - Claim: The research problem is not novel to the community. There have been a series of work for the co-optimization of neural architecture and data, even at the domain of graph NAS and graph data.
  - Meta: The paper addresses a gap in the existing research on Graph Neural Architecture Search (GNAS) by focusing on its applications in resource-constrained scenarios.
  - Rationale: The claim concerns novelty and prior work on co-optimization of architecture and data in graph NAS. The meta-review discusses GNAS, sparsification, and evaluation, but does not directly claim that novelty is repetitive; it mentions related works and gaps but does not substantively endorse or rely on the specific con...
- `rp5vfyp5Np:YktI8n3TeZ:1` auto=`survived` llm=`partial` quality=`medium`
  - Claim: To obtain human preference labels, one need to first collect diverse behavior data so that human can pick the intended policy.
  - Meta: Complexity and Uncertainty in Intention Policy Learning: The process of learning intention policy based on human preferences introduces extra requirements and uncertainties, including the expensive collection of human preference data and potential biases.
  - Rationale: The reviewer claim concerns that human preference data collection adds expense and uncertainty. The meta-review discusses complexity and uncertainty of intention policy learning, mentioning expensive data collection and biases in weaknesses, but does not explicitly repeat or endorse the exact reviewer concern as a c...
- `rGvDRT4Z60:nPlMdbTUzW:5` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Rejection rate is not shown in any experiments. One could view a misclassification as a rejection, however. Please include rejection rates or view them as misclassifications in the results.
  - Meta: See the issues raised above, most related to concerns regarding prior work, presentation of results, and implications of the rejection mechanism in fairness in practice.
  - Rationale: The meta-review discusses rejection mechanisms and fairness implications and notes reviewer concerns; however, it does not substantively repeat or rely on the exact reviewer claim that 'rejection rate is not shown' or that 'view misclassification as rejection'. The match is about the broader concern of evaluating re...
- `AOSsLRKQrX:Md9p3Kh1UT:3` auto=`partial` llm=`partial` quality=`medium`
  - Claim: To prove decoupling, an experiment that directly probes this decoupling is crucial; the 4.4 ablation is unclear and toy-scale, casting doubt on generalization.
  - Meta: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
  - Rationale: The meta-review discusses concerns about experimental evaluation, ablations, and disentanglement as a causal factor, which aligns with the claim about the need for a direct decoupling probe. However, the exact claim text is not verbatim; the meta-review emphasizes broad concerns (clarity, ablations, disentanglement)...
- `7vVWiCrFnd:UTwNz3TQsJ:2` auto=`partial` llm=`partial` quality=`high`
  - Claim: The proposed method seems not scalable as it requires identifying maximum cliques that is exponentially complex, and even relaxing it to cliques with size k has super-quadratic complexity O(n^k) (please correct me if I am wrong). This limitation has not been discussed in the paper, and experiments only include small...
  - Meta: Although, some of the reviewers raised concerns about the computational complexity and the lack of scalability of the methodology, which in return limits the experiments to small datasets.
  - Rationale: The reviewer claim concerns scalability and the claim that limitation not discussed. The meta-review mentions concerns about computational complexity and lack of scalability and notes rebuttal addressing comments, concluding applicability limited to small graphs. It repeats the broad concern but does not endorse the...
- `eUgS9Ig8JG:4sGhXacqSF:6` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Section 4.2 claims need clearer explanation to ensure they act on oriented features; simplicial awareness discussion is necessary and a connection to existing methods should be clarified.
  - Meta: While reviewers appreciate the method and the computational saving the fact that GNN works have followed this path of adding features and proving WL expressive power reduces a bit the novelty in this work.
  - Rationale: The reviewer claim concerns Section 4.2 clarity about simplicial-aware features and connection to existing methods. The meta-review discusses efficiency, WL expressive power, novelty, and scalability, but does not clearly address Section 4.2 clarity or oriented features or simplicial awareness discussion. It mention...
- `AJBkfwXh3u:KidnSLrJ44:5` auto=`survived` llm=`partial` quality=`medium`
  - Claim: 5. How to interpret the 'dynamic' in DyGNNExplainer? Can the datasets in experiments support the augment raised in this paper, as it seems there are no dynamic graph in experiments?
  - Meta: The reviewers comment that most of the benchmarks are in static datasets, so it is not clear how the method would actually behave in dynamical graphs.
  - Rationale: The meta-review acknowledges that most benchmarks are static and questions applicability to dynamic graphs, which aligns with the reviewer claim about interpretation of 'dynamic' in DyGNNExplainer and lack of dynamic graphs in experiments. However, the meta-review does not substantively repeat or rely on the exact r...
- `SLw9fp4yI6:294WvaLe2c:1` auto=`partial` llm=`partial` quality=`high`
  - Claim: Lack of exploration of the space of possible expressions. The authors present an extremely general method for constructing interesting distributions to sample from, but only test a handful. It would be disappointing if it turned out that this technique is extremely brittle to the specific Language Model Arithmetic e...
  - Meta: The submission introduces a new method for controlled text generation through 'language model arithmetic', in which different models and classifiers are combined to give fine-grained control over generation.
  - Rationale: The reviewer claims a lack of exploration of the space of expressions and limited evaluation (only 4 expressions, etc.). The meta-review mentions limited evaluation as a weakness: "The main limitation is the relatively narrow scope of the evaluation, which focuses on toxicity and (in the revision) sentiment." This c...