# Concern Survival LLM Calibration

- Input items: 100
- Labels: 100
- High-confidence training candidates: 6
- Auto/LLM agreement: 41.0%

## Label Counts

| Label set | Counts |
| --- | --- |
| `auto_label_counts` | `{"not_found": 100}` |
| `llm_meta_review_match_counts` | `{"not_found": 41, "partial": 38, "unsure": 21}` |
| `llm_concern_quality_counts` | `{"high": 5, "low": 55, "medium": 37, "unsure": 3}` |
| `llm_ac_treatment_counts` | `{"endorsed_or_relied_on": 2, "mentioned_as_resolved_or_outweighed": 1, "mentioned_neutrally": 41, "not_mentioned": 56}` |
| `high_confidence_match_counts` | `{"partial": 6}` |

## Agreement

- `AZGIwqCyYY:MPDVvgTzbR:0` auto=`not_found` llm=`not_found` quality=`unsure`
  - Claim: In Figure 4, why does a lower CKA value of the meta-trained model suggest it learned more similar representations during adaptation? As the authors mentioned, should a low CKA value indicate different representations?
  - Meta: The author response and updated manuscript addressed many of the most significant weaknesses, and as such I recommend acceptance.
  - Rationale: The meta-review focuses on weaknesses, scope, and clarity, but does not clearly discuss the specific concern raised in the claim about CKA values and representation similarity. The meta-review mentions 'limitations of the approach and setting are not clearly defined' rather than analyzing Figure 4's CKA interpretati...
- `9L9j5bQPIY:ruFJeXpRL4:1` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Figure 1 has no proper caption, which makes it hard to read and understand the figure.
  - Meta: No match
  - Rationale: The meta-review discusses overall presentation and related work omissions, but does not substantively address the specific claim about Figure 1 caption clarity. The concern text about Figure 1 caption is not echoed, endorsed, or relied upon in the meta-review. Therefore, the meta-review does not mention the same con...
- `lK2V2E2MNv:85dFa83C5l:1` auto=`not_found` llm=`not_found` quality=`medium`
  - Claim: The contribution over existing works like MAGMA is not enough; the difference is that this paper uses MAGMA with the assignment prediction loss, but effectiveness is not shown clearly.
  - Meta: The paper proposes VLAP, a method to bridge vision encoders and language models through assignment prediction.
  - Rationale: The meta-review discusses VLAP and overall acceptance; it does not substantively repeat or rely on the specific reviewer concern about novelty versus MAGMA and assignment prediction loss. The claim text argues novelty and effectiveness, but the meta-review focuses on acceptance and rebuttals, not on the particular w...
- `1FWDEIGm33:MzDh7uJCEU:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: How do you distinguish between expected and unexpected? Expected by whom?
  - Meta: No match
  - Rationale: The meta-review discusses high-level conceptual framing and critiques of personality-like notions in LLMs, focusing on perspectives and controllability. It does not substantively repeat, endorse, or rely on the specific claim about “Large Language Models as superpositions of cultural perspectives” or the question “H...
- `DwcV654WBP:577ajxueBu:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: The joint attention module is not described clearly. Is it the same as in CLIP?
  - Meta: Despite a few positive scores, some critical issues are not fully addressed during the rebuttal.
  - Rationale: The claim text is about clarity of a joint attention module and asks if it is same as in CLIP. The meta-review discusses overfitting, freezing text encoder, and overall contribution; it does not address the joint attention module description or its relation to CLIP. Therefore the concern is not found in the meta-rev...
- `cQgjz0mf0r:JFysq9wa5A:5` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Broadly, what do you mean by double descent?
  - Meta: No match
  - Rationale: The meta-review focuses on broader issues of novelty, methodology, and writing quality; it does mention double-descent as part of their evaluation, but it does not substantively discuss or rely on the specific concern 'double descent' as a claim from the review. The auto_survival_label is not_found, and the meta-rev...
- `eR4W9tnJoZ:f1HR8JtDsA:6` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Framework does not account for user personalization and privacy concerns when sharing data with LLM providers.
  - Meta: No match
  - Rationale: The claim to be evaluated is about user personalization and privacy in data sharing with LLM providers. The meta-review focuses on the paper's lack of novelty, scalability, and evaluation, and recommends rejection. It does not substantively repeat or rely on the concern about personalization/privacy, nor does it dis...
- `bDWXhzZT40:eqXGBIkC31:1` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Section 4 is very hard to read, some design choices also appear arbitrary. For instance, intuitively, what is the role of $X_c$, $X_e$, $W_c$ and $W_e$, and why are the dimensionalities chosen as described in the paper? Elaborating more on the setup would help to better understand the settings and allow for estimati...
  - Meta: The authors show their method to be effective in achieving uncertainty-awareness and better generalisation performance.
  - Rationale: The meta-review discusses overall acceptance and general assessment of the paper, but does not address the specific claim about section 4 clarity or design choices, nor does it substantively repeat or rely on that specific concern. Evidence is ambiguous: the reviewer claim about readability is not clearly echoed or...
- `xNdE7RiRyP:lo8Aco3mUt:0` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: Could you please elaborate how the memory number was calculated in Tab.2. At which layer during the back-propagation it reached the peak memory?
  - Meta: Concerns about clarity of presentation.
  - Rationale: The meta-review discusses broad concerns about presentation clarity and applicability, but does not substantively repeat or endorse the specific reviewer concern about how memory footprint was calculated in Tab.2 or peak memory during back-propagation. The claim text requests calculation details for memory during ba...
- `7QlKLvfVge:FOfbfWgp15:0` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: This paper assumes the defender can get access to the backdoored image. However, this is hard to get in actual situations and thus limits its use greatly. I wonder whether it works without these backdoored data.
  - Meta: In this paper, the authors first explored the limitations of pruning-based defense through theoretical an empirical investigations and then proposed a Directional Rank Reduction method, a so-called extended neuron pruning framework, to address the limitations.
  - Rationale: The reviewer claim centers on whether backdoored data access is realistic and whether the method works without backdoored data. The meta-review discusses limitations of pruning-based defense and asks for clearer motivation and rigorous proofs, but does not substantively address the specific concern about access to b...

## Disagreement

- `dYjuJGTEbc:S9Hah6oZoZ:4` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: There are typos and careless statements and the authors need to polish this paper carefully. For example, 1) page 1, it should be $G_1(D_1,P_1)$ in the third row from the bottom, 2) page 2, the second paragraph, the second point of the limitations has grammatical mistakes, 3) What is EGWB an abbreviation for? The au...
  - Meta: While the authors have addressed some of these issues in their rebuttal, the reviewers unanimously feel that the paper necessitates extensive rewriting.
  - Rationale: The meta-review discusses the need for rewriting and mentions lack of discussion/comparison to related works, which aligns with the writing concerns in the claim. However, the claim is specific about typos and abbreviations on pages, which the meta-review does not substantively endorse or repeat. The meta-review cit...
- `eUgS9Ig8JG:tkcYyLyiYm:0` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Runtime and asymptotic comparisons in this work are done by excluding the precomputation of features. I think this is misleading, since in practice, the precomputation is certainly part of the computation, especially during inference. Thus, the presented gains seem to be only valid during training, when the features...
  - Meta: Experiments support the efficiency claims compared to existing simplicial complex learning baselines.
  - Rationale: The claim concerns runtime/approximation via excluding precomputation of features and argues this is misleading because precomputation is part of inference. The meta-review discusses efficiency through precomputed features and WL expressive power, acknowledging novelty limited. It mentions the general idea of making...
- `BTKAeLqLMw:M95mCPFWRx:0` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: The technical body of these papers are uncomfortably similar. Combining a number of existing metrics (often in trivial ways) such as quality, diversity, etc. as a new evaluation metric and conducting the evaluations largely with the help of GPTs. And the end goals are also the same–to achieve comparable or better pe...
  - Meta: They evaluate by fine-tuning Llama-13B model, showing solid gains over baselines.
  - Rationale: The reviewer raises a concern about novelty/ originality of data selection papers, suggesting a research gap remains unresolved. The meta-review discusses data selection methodology and evaluates gains from fine-tuning, but it does not substantively repeat or rely on the exact concern about novelty or unaddressed re...
- `H9DYMIpz9c:Ie1VUg7cqO:3` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: What is meant by $d\mathbf{m} = d\mathbf{m} + \frac{\partial w_t}{\partial m_t} \cdot d\mathbf{w}$? Is $w_t$ supposed to be $\mathbf{w}_T$, or is this expression meant to be a recursive formula? What about the formulas for the other quantities, and how are these combined to compute the meta gradient?
  - Meta: I would highly recommend the authors to address these issues and aim for a more comprehensive and balanced overview of their approach in a revised version of the paper.
  - Rationale: The meta-review discusses major concerns (fatal flaw in theory and amortization costs) but the specific claim about a mathematical expression and meta-gradient clarity is not clearly echoed in the meta-review. It mentions general issues and recommendations rather than substantively endorsing/relying on the exact con...
- `kmn0BhQk7p:nHD6rOZnlp:0` auto=`not_found` llm=`partial` quality=`high`
  - Claim: Have you considered using LLMs to "rewrite" inputs in a privacy-preserving manner?
  - Meta: The paper under consideration presents a pioneering exploration into the use of Language Model Models (LLMs) to infer sensitive attributes from user-written text, particularly on online platforms like Reddit.
  - Rationale: The meta-review discusses privacy risks and the use of LLMs to infer sensitive attributes from user text, which aligns with the claim about using LLMs to rewrite inputs in a privacy-preserving manner? However, the meta-review does not mention the specific 'rewrite inputs' mitigation technique; it focuses on inferenc...
- `SLw9fp4yI6:jKZS833UEW:0` auto=`not_found` llm=`unsure` quality=`low`
  - Claim: Experimentation seems a little weak. It'd be great to compare with some of the work that's come out of UW/AI2 in the past couple of years like DExperts, which you cite but dont compare with, and Quark (Lu et al. 2022). It'd also be great to compare with GeDi and a few other baselines. That'd strengthen the experimen...
  - Meta: I think some people will find this pretty interesting, so might be worth a spotlight
  - Rationale: The claim_text criticizes experimental weaknesess and suggests baselines (DExperts, Quark, GeDi). The meta-review discusses evaluation scope as a limitation and notes narrow evaluation focusing on toxicity and sentiment, but does not substantively repeat, endorse, or rely on the same specific concern about adding al...
- `BQvbL2sFQx:ggRvsrGJrq:6` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: Results in Table 2 are marginal and statistically insignificant. To me, the value of this result is approaching 0, because most confidence intervals overlap. It does not make sense to use bold font to signify the best model, when the best model is not significantly different than another model.
  - Meta: Additionally, some of the presented gains are marginal and statistically negligible due to the stochastic nature of the training.
  - Rationale: The meta-review notes that gains are marginal and statistically negligible and discusses evaluation/benchmark concerns, which align with the reviewer claim about results being marginal. However, the meta-review does not explicitly endorse or rely on the same diagnostic claim (that bold font is inappropriate due to n...
- `w73feIekdO:FG7cu1nT3G:1` auto=`not_found` llm=`partial` quality=`high`
  - Claim: Please check the weaknesses listed above.
  - Meta: No match
  - Rationale: The meta-review repeatedly emphasizes experimental issues, missing comparisons, and presentation flaws, which align with the claim about weaknesses in experiments. It substantively discusses the same concern (insufficient/convincing experiments) and endorses it as a key issue, thus surviving. The meta-review centers...
- `xibcBSuuq0:zDGIRGC8oM:1` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: In Eq. (3), why is y^t related to s^t instead of s^{t+1} given vanilla QMIX formulation? theoretical basis questioned for Q^t_assem accuracy.
  - Meta: The theoretical results and writing may use some improvement also.
  - Rationale: The claim text concerns a theoretical detail about QMIX and the relation of y^t to s^t. The meta-review discusses overall paper quality and suggestions for improvement but does not substantively repeat or rely on this specific theoretical concern. It mentions theoretical results may need improvement, but it does not...
- `AJBkfwXh3u:WOT2WFINQc:0` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: In table 2, the best performance for OrphicX is obtained by DTree-Grid?
  - Meta: No match
  - Rationale: The meta-review discusses interpretability and dynamic GNNs but does not clearly mention a specific concern about 'In table 2, the best performance for OrphicX is obtained by DTree-Grid?' or its causality-inspired explanations. The question claim is about a specific table and model, which the meta-review touches onl...

## High Confidence

- `kmn0BhQk7p:nHD6rOZnlp:0` auto=`not_found` llm=`partial` quality=`high`
  - Claim: Have you considered using LLMs to "rewrite" inputs in a privacy-preserving manner?
  - Meta: The paper under consideration presents a pioneering exploration into the use of Language Model Models (LLMs) to infer sensitive attributes from user-written text, particularly on online platforms like Reddit.
  - Rationale: The meta-review discusses privacy risks and the use of LLMs to infer sensitive attributes from user text, which aligns with the claim about using LLMs to rewrite inputs in a privacy-preserving manner? However, the meta-review does not mention the specific 'rewrite inputs' mitigation technique; it focuses on inferenc...
- `w73feIekdO:FG7cu1nT3G:1` auto=`not_found` llm=`partial` quality=`high`
  - Claim: Please check the weaknesses listed above.
  - Meta: No match
  - Rationale: The meta-review repeatedly emphasizes experimental issues, missing comparisons, and presentation flaws, which align with the claim about weaknesses in experiments. It substantively discusses the same concern (insufficient/convincing experiments) and endorses it as a key issue, thus surviving. The meta-review centers...
- `7vVWiCrFnd:uXWt0SbIG0:0` auto=`not_found` llm=`partial` quality=`high`
  - Claim: The first paragraph is problematic. “implicitly assume that node representations learnt by GNNs are independent conditioned on node features and edges, thereby ignoring the joint dependency among nodes...” does not represent the related works accurately. These works do not ignore dependency among the nodes, which is...
  - Meta: Within this framework the authors show how to systematically extend the capabilities of GNNs in modeling complex distributions and inference targets, with a particular focus on phantom nodes and phantom edges, showcasing their empirical improvements in real-world applications of GNNs.
  - Rationale: The claim text critiques a paragraph claiming independence assumption; the meta-review discusses GNN expressivity and mentions scalability concerns and applicability to small graphs. It does discuss the same broad issue (modeling dependencies/relations in GNNs) but does not directly endorse or repeat the exact criti...
- `kmn0BhQk7p:8NbuASNUu3:4` auto=`not_found` llm=`partial` quality=`medium`
  - Claim: The notion of “defenses” against such attacks also seems slim. But should this be something that we need to actively defend against? Sharing posts (as done in the status quo) intrinsically contains some notion of utility that will be removed if the deducible information is scrubbed. Can the authors comment on the same?
  - Meta: However, some constructive criticisms are noted, such as the need for additional justification of certain experiment setups, the consideration of alternative metrics for specific attributes, and ethical considerations regarding the use of sensitive topics.
  - Rationale: The claim text questions defenses against inference attacks and suggests commentary on scrubbing deducible information. The meta-review discusses broader privacy risk from using LLMs to infer sensitive attributes and notes constructive criticisms about methodology and ethics, but does not clearly endorse or rely on...
- `AOSsLRKQrX:tYw6kbOlZq:1` auto=`not_found` llm=`partial` quality=`high`
  - Claim: No ablations are provided. The model contains multiple components, but there are no ablation experiments to study the effect of each component. For example, the effect of recovering object representation versus image representation, the effect of learning the slots to be a linear combination of concepts, the number...
  - Meta: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
  - Rationale: The meta-review discusses broad concerns about the experimental evaluation and explicitly mentions ablations as part of the critique, which aligns with the claim that ablations are missing. The AC treatment endorses or relies on the concern about insufficient ablation studies and unclear disentanglement justificatio...
- `JWrl5pJCnl:A3gHHaLomn:0` auto=`not_found` llm=`partial` quality=`high`
  - Claim: The proposed work's claimed distinction with CaP is unclear. The authors write "Unlike existing methods such as CaP (Liang et al., 2022), which directly generates policy codes, our approach generates decision-making actions that can help reduce the error rate when performing complex tasks." But, the proposed methodo...
  - Meta: The paper does not convincingly articulate what is technically novel w.r.t.
  - Rationale: The meta-review discusses novelty and cites comparisons to CaP as a weakness, noting that the innovations seem minor and empirical results don't convince. The concern is central (novelty) and is echoed in the meta-review. The AC treatment mentions the issue neutrally as a weakness rather than endorsing it as solved....