# Rebuttal Resolution LLM Calibration

- Input items: 120
- Labels: 120
- High-confidence training candidates: 29
- Proxy/LLM agreement: 27.5%

## Label Counts

- `proxy_label_counts`: `{"addressed_unclear_resolution": 65, "likely_resolved_or_answered": 31, "not_addressed": 24}`
- `llm_response_label_counts`: `{"generic_or_unclear": 38, "not_addressed": 50, "specifically_addressed": 32}`
- `llm_effect_counts`: `{"does_not_address": 66, "partially_addresses": 39, "resolved_or_weakened": 2, "unclear": 13}`
- `llm_specificity_counts`: `{"generic": 41, "none": 47, "specific": 32}`
- `high_confidence_response_label_counts`: `{"not_addressed": 1, "specifically_addressed": 28}`

## Examples

### High Confidence
- `bDWXhzZT40:BXa90ADyFW:2` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: How were the targets in table 1 derived; why are these targets desirable?
  - Response: c) we have also attempted to connect the real-world experiments to each of these scenarios, showing that our gains in synthetic settings generalize.
  - Rationale: Author response mentions connecting real-world experiments to scenarios and that gains in synthetic settings generalize, which relates to targets' desirability and derivation by showing external validity. However the claim asks how targets in table 1 were derived and why desirable; response does...
- `JWrl5pJCnl:oNACfe2nfm:0` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: Important related work RT-2 [1] is missing, likely because it is too recent to be included and discussed.
  - Response: >**Q1: Important related work RT-2 [1] is missing, likely because it is too recent to be included and discussed.
  - Rationale: Author restates the reviewer claim and indicates RT-2 is missing due to recency. This discusses the claim directly, but there is no explicit evidence or claim of resolution beyond acknowledging omission; the proxy label quotes show acknowledgment but not resolution. Therefore: specifically_addres...
- `kmn0BhQk7p:5ZYljDrhoa:1` proxy=`addressed_unclear_resolution` llm=`specifically_addressed` confidence=`high`
  - Claim: Do the authors release results on the synthetic examples? Since the experiment is not reproducible, it would be important to have result s on the synthetic data so future work can build upon the results of this paper.
  - Response: We then tested GPT-4 (the most capable model in prior experiments) on the synthetic examples, reporting the numbers in App.
  - Rationale: Author response mentions testing GPT-4 on the synthetic examples and that numbers are reported in the Appendix, directly addressing the reviewer’s request for results on synthetic data and reproducibility. However, it does not provide the actual results in the main text nor confirm public release...
- `xNdE7RiRyP:5DuTHFMr8O:0` proxy=`not_addressed` llm=`specifically_addressed` confidence=`high`
  - Claim: I found it hard to follow the paper at times, as it felt a bit unfocused, especially in Section 2, but the italicized summary provided at the end of each section definitely helped. Overall the paper is very dense (and many additional parts are left to the a...
  - Response: We will clarify this point in Sections 3.1 and A.2.
  - Rationale: Author response directly mentions clarifying points in Sections 3.1 and A.2, which directly targets the reviewer’s claim about lack of clarity and unfocused sections. However, the claim concerns overall clarity and section 2; the response commits to clarification in later sections rather than pro...
- `dYjuJGTEbc:3MMkDoB21Q:2` proxy=`addressed_unclear_resolution` llm=`specifically_addressed` confidence=`high`
  - Claim: How does the result of theorem 3 relate to the convergence of the algorithm implemented in practice?
  - Response: Theorem 3 provides a conservative condition between $\lambda$ and $\epsilon$ under which the convergence of the alternating algorithm is guaranteed.
  - Rationale: Author cites Theorem 3 providing a conservative condition between lambda and epsilon under which convergence of the alternating algorithm is guaranteed, directly addressing the reviewer claim about link between theorem and practical convergence. However, the response only states a conditional gua...
- `AJBkfwXh3u:q90TUxGqx8:1` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: The significance of the proposed approach is not clear. It is hard to judge the performance improvement achieved by DyGNNExplainer since other baselines are all for static graphs.
  - Response: W3:** Since our method is the first study on dynamic graph interpretability, we can only utilize the baselines from static graph interpretability tasks.
  - Rationale: The author response directly cites a limitation used for justification: baselines are from static graph interpretability because this is the first study on dynamic graph interpretability. This directly addresses the reviewer’s claim about performance comparison and significance. It acknowledges t...
- `gtkFw6sZGS:5yEYAAadyY:0` proxy=`addressed_unclear_resolution` llm=`specifically_addressed` confidence=`high`
  - Claim: The papers is a large engineering effort (e.g., distilling GPT-4 for the task of evaluation) without much novel ideas
  - Response: > “The papers is a large engineering effort (e.g., distilling GPT-4 for the task of evaluation) without much novel ideas (I do not think that a paper needs to be novel to be accepted, but this paper does score low in terms of novelty)”
  - Rationale: The author response directly quotes the reviewer claim about novelty and asserts that novelty is not always required for acceptance and notes the paper scores low on novelty. It engages with the claim by acknowledging the issue and offering a stance, thus addressing the claim directly. However, i...
- `eUgS9Ig8JG:4sGhXacqSF:4` proxy=`addressed_unclear_resolution` llm=`specifically_addressed` confidence=`high`
  - Claim: Many experiments for tasks other than trajectory prediction use unoriented data by assigning scalar values to high-order simplices, which is incompatible with oriented operators; unclear implementation details.
  - Response: In the numerical experiments for trajectory prediction, the input features are oriented flows on simplicial complexes, prompting us to use oriented incidence matrices for aggregation.
  - Rationale: The author response directly addresses the reviewer’s claim by stating that in trajectory prediction experiments the inputs are oriented flows and oriented incidence matrices are used for aggregation, which directly tackles the concern about unoriented data and incompatibility with oriented opera...
- `7vVWiCrFnd:aHtDQsXakn:5` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: The experiments do not include a wide range of GNN methods referenced in theory.
  - Response: We did not include all GNN variants in the analysis because our methods focus on node classification and link prediction methods and aim to improve the expressiveness of MPNNs.
  - Rationale: The author explicitly references the reviewer’s claim that the experiments do not include a wide range of GNN methods and explains that their focus is on node classification and link prediction, which justifies not including all variants. This directly engages the claim, but the justification is...
- `cQgjz0mf0r:ohnIAzeDZx:1` proxy=`likely_resolved_or_answered` llm=`specifically_addressed` confidence=`high`
  - Claim: The lack of a need for labels makes this measure ripe for helping to help explain the effects of self-supervised learning. I'm a bit surprised that the authors don't include experiments for why (e.g) BYOL can work by measuring the local complexity of teache...
  - Response: > I'm a bit surprised that the authors don't include experiments for why (e.g) BYOL can work by ...
  - Rationale: The author response segment directly references the reviewer claim by restating the surprise about not including BYOL experiments and mentions measuring local complexity and teacher/student dynamics. It shows an intention to address the claim. However, the segment ends with an ellipsis and does n...
### Proxy Disagreement
- `rGvDRT4Z60:nPlMdbTUzW:0` proxy=`addressed_unclear_resolution` llm=`not_addressed` confidence=`low`
  - Claim: The implications of rejecting for fairness are not considered. Rejection for privacy has implications in terms of privacy budget and likewise rejections for fairness come with implications and ignoring them might be responsible for the observed gains on the...
  - Response: Rejection for privacy has implications in terms of privacy budget and likewise rejections for fairness come with implications and ignoring them might be responsible for the observed gains on the Pareto frontier.
  - Rationale: The author_response_segment repeats parts of the reviewer claim about privacy and fairness implications but does not discuss how these implications affect fairness, privacy budget, or Pareto frontier. It does not engage with the example of rejecting decisions at inference time, nor does it provid...
- `gtkFw6sZGS:5yEYAAadyY:1` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`low`
  - Claim: The presentation of the method and contribution feels very confusing to me
  - Response: > “The presentation of the method and contribution feels very confusing to me (maybe it's just my fault).
  - Rationale: The author response repeats the reviewer’s claim without providing any specific discussion or evidence addressing the confusion about method and contribution. It does not directly answer how the method will be clarified or what changes will be made. There is no concrete resolution or guidance, on...
- `yacRhge4zQ:5Yq0QwTe4B:3` proxy=`likely_resolved_or_answered` llm=`not_addressed` confidence=`low`
  - Claim: Requests for clarification of the Pareto frontier assumption.
  - Response: Can the authors clarify the assumption of a pre-calculated Pareto frontier as common knowledge?
  - Rationale: Author response segment is identical to reviewer claim and does not provide any clarifying content or argument. No discussion of Pareto frontier assumption is present; thus the claim is not addressed.
- `9L9j5bQPIY:sNTMZ9SFl1:0` proxy=`addressed_unclear_resolution` llm=`not_addressed` confidence=`low`
  - Claim: It is very hard to assess the paper results as the only representation is given using T-SNE and two feature confusion matrices representing the ability of the meta-network to distinguish between audio and video features.
  - Response: We think we don’t need to compare our approach to others in our result section because the metanetwork is tested in a new problem setting where we have to infer the ability of a model without access to the dataset.
  - Rationale: The reviewer claim asserts that results are hard to assess due to lack of representations (T-SNE and confusion matrices) comparing to other work. The author response says they don’t need to compare to others because testing in a new problem setting. This does not discuss the specific concern abou...
- `miGpIhquyB:REwQirNHgK:0` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`low`
  - Claim: Unsupported Claims. The paper raises a claim that "reinforcement learning with human feedback (RLHF) in ChatGPT leads to a significant degradation in synthetic dataset generation capabilities." However, the paper lacks a clear explanation of how the authors...
  - Response: Q: Can you provide a more detailed explanation of the experimental design and results that support RLHF negatively impacting ChatGPTs text generation capabilities?
  - Rationale: The author response asks for more detail about experimental design and results, but does not itself provide any clarification or evidence resolving how RLHF specifically degrades synthetic dataset generation. It is a generic request for more information rather than addressing the reviewer’s claim...
- `B0wJ5oCPdB:EMJYZmbvDC:2` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`low`
  - Claim: Though authors list some advantages of the proposed CoS, at the same time, CoS is more difficult to track LLMs reasoning path. I would encourage authors to discuss some limitations of this work.
  - Response: "It seems that the success of this method, referred to as CoS, might be limited to simpler, more straightforward spatial tasks."
  - Rationale: Author response asserts potential limitation to simpler tasks but does not directly discuss the reviewer claim about tracking LLM reasoning path or discuss limitations generally. It is vague and not clearly addressing the specific limitation; thus generic/unclear and unlikely to resolve.
- `23OEmHVkpq:JJaPaIjUli:3` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`low`
  - Claim: The authors applied the proposed TopDis to infer disentangled directions in a pretrained style-GAN, is there some quantitative results? Then dose the method can be applied to other disentangled methods?
  - Response: __Q2__: _The authors applied the proposed TopDis to infer disentangled directions in a pretrained style-GAN, is there some quantitative results?
  - Rationale: The author response simply repeats part of the reviewer’s claim and asks about quantitative results; it does not provide any new quantitative data, analysis, or concrete steps addressing whether there are quantitative results or applicability to other disentangled methods. There is no direct addr...
- `qBL04XXex6:Cw9UmirZBD:3` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`medium`
  - Claim: The paper is based on the motivation that starting with a simple prompt without human annotations for LLMs, BoT may get weak thoughts. However, with aggregation, BoT is capable of deriving a more logical and effective thought chain from them, thereby guidin...
  - Response: This, in turn, makes BoT an automated prompting framework because by iteratively collecting effective error analysis in the prompt without human annotations, LLMs can be guided to produce a correct reasoning chain toward problem solving.
  - Rationale: The author response states BoT becomes automated prompting by collecting effective error analysis without human annotations, guiding LLMs to produce correct reasoning. This touches the reviewer claim about starting with simple prompt and aggregation leading to better thought chain, but it doesn't...
- `B0wJ5oCPdB:8krLAr9E1i:3` proxy=`addressed_unclear_resolution` llm=`generic_or_unclear` confidence=`medium`
  - Claim: How scalable is the CoS method, especially for larger and more complex spatial environments? Is there an automatic way to converse into chain of symbols, or does it require manual rules and symbols design for each task and even each in-context sample?
  - Response: "It seems that the success of this method, referred to as CoS, might be limited to simpler, more straightforward spatial tasks."
  - Rationale: Author's response asserts a limitation to simpler tasks but does not engage with the reviewer’s specific scalability and automation questions. It does not provide evidence, methods, or discussion on automatic conversion to chain of symbols or general scalability. The claim remains only partially...
- `3wL1tj3kqE:6hdEd9y3Hn:6` proxy=`addressed_unclear_resolution` llm=`not_addressed` confidence=`low`
  - Claim: Speaking of fair machine learning in general, it aims to mitigate spurious correlations between sensitive attributes and model outcomes. Although this work mentions fairness multiple times, it is unclear to me how to mitigate the spurious correlations durin...
  - Response: Although this work mentions fairness multiple times, it is unclear to me how to mitigate the spurious correlations during training.
  - Rationale: The author response segment repeats the reviewer’s concern about unclear mitigation of spurious correlations and does not provide any new information, methods, or evidence to address how training mitigates spurious correlations. It fails to directly discuss the proposal in the paper or offer spec...