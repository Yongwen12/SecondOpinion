# Concern Survival LLM Calibration

- Input items: 100
- Labels: 100
- High-confidence training candidates: 6
- Auto/LLM agreement: 42.0%

## Label Counts

| Label set | Counts |
| --- | --- |
| `auto_label_counts` | `{"not_found": 100}` |
| `llm_meta_review_match_counts` | `{"not_found": 42, "partial": 24, "unsure": 34}` |
| `llm_concern_quality_counts` | `{"high": 6, "low": 68, "medium": 16, "unsure": 10}` |
| `llm_ac_treatment_counts` | `{"endorsed_or_relied_on": 2, "mentioned_neutrally": 34, "not_mentioned": 64}` |
| `high_confidence_match_counts` | `{"not_found": 1, "partial": 5}` |

## Agreement

- `SLw9fp4yI6:jKZS833UEW:0` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Experimentation seems a little weak. It'd be great to compare with some of the work that's come out of UW/AI2 in the past couple of years like DExperts, which you cite but dont compare with, and Quark (Lu et al. 2022). It'd also be great to compare with GeDi and a few other baselines. That'd strengthen the experimen...
  - Meta: I think some people will find this pretty interesting, so might be worth a spotlight
  - Rationale: The meta-review discusses the submission's overall novelty, motivation, and limited evaluation, but it does not mention or address the specific reviewer concern about comparing with UW/AI2 work (DExperts, Quark, GeDi) or other baselines. The concern is not semantically present in the meta-review text. Given this, th...
- `9L9j5bQPIY:ruFJeXpRL4:1` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Figure 1 has no proper caption, which makes it hard to read and understand the figure.
  - Meta: No match
  - Rationale: The meta-review text focuses on general commentary about the paper's aims, methods, and omissions, but it does not substantively repeat, endorse, or rely on the specific claim that 'Figure 1 has no proper caption'. The reviewer note appears to be about clarity of a figure, which is not discussed in the meta-review....
- `dYjuJGTEbc:3MMkDoB21Q:4` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: In practice what are the optimal value used for the epsilon parameter for each datasets?
  - Meta: No match
  - Rationale: The meta-review discusses general methodological improvements and writing quality but does not substantively mention the specific claim about optimal epsilon values for datasets. The reviewer claim is about experimental parameter values; the meta-review focuses on related work discussion, citations, and clarity. The...
- `lK2V2E2MNv:85dFa83C5l:1` auto=`not_found` llm=`not_found` quality=`unsure`
  - Claim: The contribution over existing works like MAGMA is not enough; the difference is that this paper uses MAGMA with the assignment prediction loss, but effectiveness is not shown clearly.
  - Meta: The paper proposes VLAP, a method to bridge vision encoders and language models through assignment prediction.
  - Rationale: The meta-review discusses VLAP and its performance, but does not mention the specific reviewer concern text about the contribution over MAGMA and assignment prediction loss. The auto_survival_label is not_found, but the meta-review text does not clearly discuss the exact claim about novelty/impact over MAGMA or assi...
- `xibcBSuuq0:zwpI0TjvXj:3` auto=`not_found` llm=`not_found` quality=`unsure`
  - Claim: In the matrix game presented in Section 1, should the $epsilon$ for player 1 be 0.1?
  - Meta: No match
  - Rationale: The meta-review discusses general feedback on the paper but does not mention the specific reviewer claim about an epsilon value in a matrix game. There is no explicit linkage or discussion of the claim_text within the meta-review. Thus, the concern is not_found. However, the meta-review content is broad and does not...
- `DwcV654WBP:577ajxueBu:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: The joint attention module is not described clearly. Is it the same as in CLIP?
  - Meta: Despite a few positive scores, some critical issues are not fully addressed during the rebuttal.
  - Rationale: The meta-review text discusses overall reception and issues, but does not mention or substantively repeat the claim about the joint attention module clarity or its relation to CLIP. The matched_meta_segment hints at rebuttal issues, not the joint attention description. therefore the specific claim “The joint attenti...
- `kmn0BhQk7p:8NbuASNUu3:0` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Implications are a function of how good the humans are i.e., if the golden labels are inaccurate (e.g., how can I be sure that the age attribute is within error tolerance), all conclusions need to be made with a grain of salt.
  - Meta: However, some constructive criticisms are noted, such as the need for additional justification of certain experiment setups, the consideration of alternative metrics for specific attributes, and ethical considerations regarding the use of sensitive topics.
  - Rationale: The meta-review discusses general strengths/weaknesses of the paper and ethics/privacy issues, but does not substantively mention the specific claim about how gold labels accuracy affects all conclusions. The provided meta-review emphasizes novelty, impact, and some criticisms about experimental setup and synthetic...
- `eR4W9tnJoZ:f1HR8JtDsA:6` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Framework does not account for user personalization and privacy concerns when sharing data with LLM providers.
  - Meta: No match
  - Rationale: The claimed concern about user personalization and privacy when sharing data with LLM providers is about ethics and user data handling. The meta-review discusses ads, LLMs, evaluation, novelty, etc., but does not substantively repeat, endorse, or rely on the specific concern of personalization/privacy in data sharin...
- `9L9j5bQPIY:91NkdJpVId:2` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: It is unclear why we need unitwise and interunit meta-autoencoders.
  - Meta: No match
  - Rationale: The meta-review discusses the paper's qualitative interpretation and broader design issues but does not substantively mention or endorse the specific claim “It is unclear why we need unitwise and interunit meta-autoencoders.” The meta-review does not repeat or rely on this exact concern and there is no clear discuss...
- `yacRhge4zQ:RAgT6VcsEb:0` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: The main contribution is to model the dynamic interaction between the model builder and the regulator. I don't see how having these two considerations has added to the model.
  - Meta: This paper studies multi-agent multi-objective modeling in the context of trustworthy machine learning (ML).
  - Rationale: The meta-review discusses overall trustworthy ML and issues like Pareto Frontier and experimental setup, but it does not mention or substantively repeat the specific reviewer concern about modeling dynamic interaction between model builder and regulator or its added value. The matched_meta_segment is vague and only...

## Disagreement

- `dYjuJGTEbc:S9Hah6oZoZ:4` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: There are typos and careless statements and the authors need to polish this paper carefully. For example, 1) page 1, it should be $G_1(D_1,P_1)$ in the third row from the bottom, 2) page 2, the second paragraph, the second point of the limitations has grammatical mistakes, 3) What is EGWB an abbreviation for? The au...
  - Meta: While the authors have addressed some of these issues in their rebuttal, the reviewers unanimously feel that the paper necessitates extensive rewriting.
  - Rationale: The reviewer claim concerns writing quality issues (typos, explanations of EGWB, etc.). The meta-review discusses need for extensive rewriting and lack of discussion/comparison to related works, which aligns with writing clarity and presentation. However, the specific examples of typos are not echoed in the meta-rev...
- `eUgS9Ig8JG:tkcYyLyiYm:0` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Runtime and asymptotic comparisons in this work are done by excluding the precomputation of features. I think this is misleading, since in practice, the precomputation is certainly part of the computation, especially during inference. Thus, the presented gains seem to be only valid during training, when the features...
  - Meta: Experiments support the efficiency claims compared to existing simplicial complex learning baselines.
  - Rationale: The reviewer claim argues that excluding precomputation of features makes runtime comparisons misleading, implying gains only due to training-time aspects. The meta-review notes that the method trades high computation for precomputed features and that experiments support efficiency claims, but does not explicitly en...
- `BTKAeLqLMw:M95mCPFWRx:0` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: The technical body of these papers are uncomfortably similar. Combining a number of existing metrics (often in trivial ways) such as quality, diversity, etc. as a new evaluation metric and conducting the evaluations largely with the help of GPTs. And the end goals are also the same–to achieve comparable or better pe...
  - Meta: They evaluate by fine-tuning Llama-13B model, showing solid gains over baselines.
  - Rationale: The reviewer claim concerns novelty/gap in data selection for alignment and similarity to prior work. The meta-review discusses evaluation setup, gains, and motivation but does not substantively repeat or rely on the exact concern. The meta-review is largely neutral about impact and questions motivation, not endorsi...
- `H9DYMIpz9c:Ie1VUg7cqO:3` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: What is meant by $d\mathbf{m} = d\mathbf{m} + \frac{\partial w_t}{\partial m_t} \cdot d\mathbf{w}$? Is $w_t$ supposed to be $\mathbf{w}_T$, or is this expression meant to be a recursive formula? What about the formulas for the other quantities, and how are these combined to compute the meta gradient?
  - Meta: I would highly recommend the authors to address these issues and aim for a more comprehensive and balanced overview of their approach in a revised version of the paper.
  - Rationale: The meta-review discusses meta-learning and two concerns (fatal flaw in theory; amortizing wall-clock time) but the specific reviewer claim about a mathematical formula and clarity is not addressed in meta-review. The connection is weak and the meta-review does not substantively repeat or rely on the same concern. T...
- `kmn0BhQk7p:nHD6rOZnlp:0` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Have you considered using LLMs to "rewrite" inputs in a privacy-preserving manner?
  - Meta: The paper under consideration presents a pioneering exploration into the use of Language Model Models (LLMs) to infer sensitive attributes from user-written text, particularly on online platforms like Reddit.
  - Rationale: The meta-review discusses privacy inference from LLMs and mentions anonymization, synthetic data, and evaluation; however, it does not clearly repeat or endorse the specific claim about using LLMs to rewrite inputs for privacy-preserving purposes. The matched_term is 'llms' but the exact concern about rewriting inpu...
- `AZGIwqCyYY:MPDVvgTzbR:0` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: In Figure 4, why does a lower CKA value of the meta-trained model suggest it learned more similar representations during adaptation? As the authors mentioned, should a low CKA value indicate different representations?
  - Meta: The author response and updated manuscript addressed many of the most significant weaknesses, and as such I recommend acceptance.
  - Rationale: The claim text asks about interpretation of CKA values in Figure 4. The meta-review mentions limitations and scope not clearly defined, but does not discuss CKA or representations across adaptation. It notes results are strong and limitations broadly. This is a tenuous, indirect relevance (semantic gap). The AC trea...
- `BQvbL2sFQx:ggRvsrGJrq:6` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Results in Table 2 are marginal and statistically insignificant. To me, the value of this result is approaching 0, because most confidence intervals overlap. It does not make sense to use bold font to signify the best model, when the best model is not significantly different than another model.
  - Meta: Additionally, some of the presented gains are marginal and statistically negligible due to the stochastic nature of the training.
  - Rationale: The meta-review notes that gains are marginal and statistically negligible due to stochastic training, which aligns with the claim that results are marginal; but it does not repeat or endorse the exact claim about Table 2 being insignificant or bold font issue. The matched segment references marginal gains and evalu...
- `w73feIekdO:FG7cu1nT3G:1` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Please check the weaknesses listed above.
  - Meta: No match
  - Rationale: The meta-review discusses general concerns about experiments and presentation, but does not explicitly substantiate the same specific concern as in the claim_text (weakness list). The claim is generic ('Please check the weaknesses listed above.') and not a concrete, shareable claim present in the meta-review. The me...
- `xibcBSuuq0:zDGIRGC8oM:1` auto=`not_found` llm=`unsure` quality=`unsure`
  - Claim: In Eq. (3), why is y^t related to s^t instead of s^{t+1} given vanilla QMIX formulation? theoretical basis questioned for Q^t_assem accuracy.
  - Meta: The theoretical results and writing may use some improvement also.
  - Rationale: The meta-review discusses general suggestions for improvement and experimental results; it does not clearly address the specific theoretical concern about Eq. (3) and why y^t relates to s^t instead of s^{t+1}. The matched_meta_segment shows
- `AJBkfwXh3u:WOT2WFINQc:0` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: In table 2, the best performance for OrphicX is obtained by DTree-Grid?
  - Meta: No match
  - Rationale: The claim_text asks about table 2 result for OrphicX with DTree-Grid. The meta-review discusses general interpretability, dynamic graphs, and static-dataset concerns but does not substantively discuss OrphicX or the specific table/result. There is mention of benchmarks and static datasets, which is tangential. Not_f...

## High Confidence

- `AOSsLRKQrX:tYw6kbOlZq:3` auto=`not_found` llm=`partial` quality=`high`
  - Claim: Missing experiment details. The training details including the hyperparameters are not provided. Some critical parameters (e.g. number of slots/concepts, loss weights) should be discussed.
  - Meta: There are also some concerns that the proposed model is too complex and has not been sufficiently ablated, which leaves it unclear what components contribute most to the performance.
  - Rationale: The meta-review discusses general concerns about evaluation, ablations, and disentanglement not being clearly supported by evidence, which aligns with the claim about missing experiment details. However, the exact claim about missing training details/hyperparameters is not directly echoed; the meta-review focuses on...
- `yacRhge4zQ:pKsEW8Yja4:2` auto=`not_found` llm=`partial` quality=`high`
  - Claim: Can this PF be realized in practice? i.e., how to accurately obtain it? and if only a somewhat inaccurate one can be obtained, what are its implications?
  - Meta: However, a key concern raised by all reviewers is the assumption of a pre-calculated Pareto Frontier (PF) and its practical feasibility.
  - Rationale: The meta-review explicitly highlights the key concern about the assumption of a pre-calculated Pareto Frontier and questions its practical feasibility, which aligns with the review claim about realizing PF in practice. The AC/meta-review relies on and endorses this concern as a central issue affecting the paper's su...
- `9L9j5bQPIY:91NkdJpVId:2` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: It is unclear why we need unitwise and interunit meta-autoencoders.
  - Meta: No match
  - Rationale: The meta-review discusses the paper's qualitative interpretation and broader design issues but does not substantively mention or endorse the specific claim “It is unclear why we need unitwise and interunit meta-autoencoders.” The meta-review does not repeat or rely on this exact concern and there is no clear discuss...
- `7vVWiCrFnd:uXWt0SbIG0:0` auto=`not_found` llm=`partial` quality=`high`
  - Claim: The first paragraph is problematic. “implicitly assume that node representations learnt by GNNs are independent conditioned on node features and edges, thereby ignoring the joint dependency among nodes...” does not represent the related works accurately. These works do not ignore dependency among the nodes, which is...
  - Meta: Within this framework the authors show how to systematically extend the capabilities of GNNs in modeling complex distributions and inference targets, with a particular focus on phantom nodes and phantom edges, showcasing their empirical improvements in real-world applications of GNNs.
  - Rationale: The claim challenges a specific representation assumption in related works (independence vs joint dependency) and states that prior works do not ignore dependency, which is at least echoed by the meta-review's mention of extendability, probabilistic graphical methods, and citations to complexity/scalability. The met...
- `AOSsLRKQrX:tYw6kbOlZq:1` auto=`not_found` llm=`partial` quality=`high`
  - Claim: No ablations are provided. The model contains multiple components, but there are no ablation experiments to study the effect of each component. For example, the effect of recovering object representation versus image representation, the effect of learning the slots to be a linear combination of concepts, the number...
  - Meta: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
  - Rationale: The meta-review explicitly notes concerns about experimental evaluation and ablations, and mentions that the model is not ready for publication. It references the need for ablations and more evidence, which aligns with the claim about no ablations present. While the meta-review discusses broader evaluation concerns,...
- `JWrl5pJCnl:A3gHHaLomn:0` auto=`not_found` llm=`partial` quality=`high`
  - Claim: The proposed work's claimed distinction with CaP is unclear. The authors write "Unlike existing methods such as CaP (Liang et al., 2022), which directly generates policy codes, our approach generates decision-making actions that can help reduce the error rate when performing complex tasks." But, the proposed methodo...
  - Meta: The paper does not convincingly articulate what is technically novel w.r.t.
  - Rationale: The meta-review states that the paper does not convincingly articulate novelty w.r.t prior work (code-as-policies) and questions results; this aligns with the claim about unclear distinction with CaP. It mentions CaP in critique, indicating the concern is present but not framed as a strong endorsement. The meta-revi...