# Concern Survival LLM Calibration

- Input items: 10
- Labels: 10
- High-confidence training candidates: 2
- Auto/LLM agreement: 60.0%

## Label Counts

| Label set | Counts |
| --- | --- |
| `auto_label_counts` | `{"not_found": 2, "partial": 4, "survived": 4}` |
| `llm_survival_label_counts` | `{"not_found": 5, "partial": 4, "survived": 1}` |
| `llm_concern_quality_counts` | `{"high": 2, "low": 5, "medium": 3}` |
| `llm_ac_stance_counts` | `{"mentioned_neutrally": 6, "not_mentioned": 4}` |
| `high_confidence_label_counts` | `{"partial": 1, "survived": 1}` |

## Agreement

- `7QlKLvfVge:LsvjaIpscH:6` auto=`survived` llm=`survived` quality=`high`
  - Claim: The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?
  - Meta: Why use the consequence of the proof in the middle of the proof?''
  - Rationale: The meta-review explicitly quotes and references the reviewer concern about the rigor of the proof and the use of consequences mid-proof, indicating it is acknowledged as a point of contention. The AC mentions addressing reviewers and cites the specific concerns, showing reliance on the same issue. The concern is sp...
- `dYjuJGTEbc:3MMkDoB21Q:1` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: The paragraph about Kantorovich relaxation states that the minimum is attained at an extremal point under some conditions which are detailed in appendix; the conditions should be put forward in the main text.
  - Meta: Moreover, several aspects of the theoretical results are noted to require detailed rewriting to enhance clarity and comprehensibility.
  - Rationale: The meta-review discusses the paper broadly, noting need for rewriting and lack of related work discussion, but does not focus on the specific claim about Kantorovich relaxation conditions being brought to main text. The reviewer claim centers on a particular sentence about extremal point conditions in appendix; the...
- `rGvDRT4Z60:8IuiGuz9Hc:4` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Clarify FairDP-SGD: definition and existence; and request where FAIR-PATE's CheXpert results are.
  - Meta: Finally, reviewer p5Rv noted the small improvements of FairPATE over baselines and raised concerns about the diversity and clarity of experiments, with several benchmarks relegated to the appendix without thorough discussion.
  - Rationale: Meta-review discusses reviewer concerns (diversity and clarity of experiments, appendix, comparisons) and mentions rejection mechanism in fairness, but does not clearly endorse or rely on the specific concern about FairDP-SGD definition or existence or CheXpert results. The matched_term 'clear' and 'fairpate' relate...
- `eepoE7iLpL:Omfs3dIcbU:0` auto=`partial` llm=`partial` quality=`medium`
  - Claim: Equation 4 describes the neural network construction. However, I am unclear about the objective function to optimize the neural network.
  - Meta: This paper proposes a method for "neural subset selection" based on deep sets.
  - Rationale: The reviewer’s claim_text raises uncertainty about the objective function and how the network is used for subset selection (methodology issue). The meta-review mentions the paper, notes strengths/weaknesses, and discusses responses and acceptance recommendation, but does not substantively repeat or rely on the speci...
- `AOSsLRKQrX:iusxEbIueU:5` auto=`partial` llm=`partial` quality=`high`
  - Claim: The model training in Section 3.6 incorporates multiple loss functions. Have ablation studies been conducted to understand the impact of each loss function on the overall performance?
  - Meta: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
  - Rationale: The meta-review repeatedly cites concerns about ablations and evaluation (e.g., “not ready for publication,” “concerns about the experimental evaluation, including ablations”), which aligns with the reviewer claim about ablation studies and component impact. However, the meta-review centers on broader issues of clar...
- `AJBkfwXh3u:KidnSLrJ44:3` auto=`not_found` llm=`not_found` quality=`low`
  - Claim: 2. Does $||A||$ operate by summing all elements of $A$ in Equation 14? Besides, does Equation 14 exist error? To satisying the sparsity requirement of causal and dynamic causal graph set, whether Equation 14 should be replaced by $\frac{{||A_t^C|{|_1} + ||A_t^S|{|_1}}}{{||{A_t}|{|_1}}}$?
  - Meta: This paper presents a causal approach to improving the interpretability of Graph Neural Networks (GNNs).
  - Rationale: The meta-review discusses overall novelty and static vs dynamic applicability, and does not mention the specific claim about Equation 14, sparsity replacement, or ||A||. The claim text is a focused theoretical question not echoed or relied upon in the meta-review. Therefore semantic_survival is not_found. The meta-r...

## Disagreement

- `B0wJ5oCPdB:ZOPmtxTnai:0` auto=`survived` llm=`partial` quality=`medium`
  - Claim: What is the fundamental explanation that this method works well?
  - Meta: Beyond the paper's relevance, the reviewers appreciate the simplicity of the method and its improvements over the CoT baseline, as well as the clarity of the presentation.
  - Rationale: The meta-review discusses spatial reasoning in LLMs and CoS, noting improvements over CoT and questioning significance of algorithmic contributions. The specific concern in claim_text about fundamental explanation for why the method works is not clearly echoed as a core concern in the meta-review; the review mention...
- `rGvDRT4Z60:yub0t46EhK:5` auto=`partial` llm=`not_found` quality=`low`
  - Claim: Why Tran et and Jagielski et al. are not reported for the UTK-dataset experiment?
  - Meta: Reviewer Mex5 highlighted the need to consider fairness when rejecting queries in privacy models, noting that ignoring fairness can be both consequential in practice and, in experiments, impact the Pareto frontier's observed gains.
  - Rationale: The meta-review discusses fairness in rejecting queries and general issues; it does not address the specific reviewer claim about Tran et al. and Jagielski et al. not being reported for the UTK-dataset experiment. The matched_meta_segment mentions fairness considerations and reviewers, but the exact concern text abo...
- `10eQ4Cfh8p:w67nfG2dMW:0` auto=`survived` llm=`not_found` quality=`low`
  - Claim: The performance evaluation of the proposed framework seems quite limited, especially as the baselines are overly simplified in Table 1.
  - Meta: The paper misses certain baselines in its performance evaluation.
  - Rationale: The meta-review discusses general weaknesses but does not clearly map to the specific reviewer claim text about baselines being overly simplified in Table 1. The matched_meta_segment notes missing baselines, which partially aligns, but the meta-review does not substantively endorse or rely on the exact concern from...
- `gYcft1HIaU:EwWKiU8GWB:1` auto=`survived` llm=`not_found` quality=`low`
  - Claim: What is the source of the EHR resource used in the preliminary making of the dataset?
  - Meta: The dataset may be a useful resource for researchers in biomedical NLP going forward.
  - Rationale: The meta-review discusses the MedDisK dataset, evaluation design, motivation, and validity concerns, but does not address the specific reviewer claim about the source of the EHR resource used in preliminary dataset construction. The claim text asks for the source of the EHR resource; this exact concern is not semant...

## High Confidence

- `7QlKLvfVge:LsvjaIpscH:6` auto=`survived` llm=`survived` quality=`high`
  - Claim: The proof needs to be more rigorous. Why use the consequence of the proof in the middle of the proof?
  - Meta: Why use the consequence of the proof in the middle of the proof?''
  - Rationale: The meta-review explicitly quotes and references the reviewer concern about the rigor of the proof and the use of consequences mid-proof, indicating it is acknowledged as a point of contention. The AC mentions addressing reviewers and cites the specific concerns, showing reliance on the same issue. The concern is sp...
- `AOSsLRKQrX:iusxEbIueU:5` auto=`partial` llm=`partial` quality=`high`
  - Claim: The model training in Section 3.6 incorporates multiple loss functions. Have ablation studies been conducted to understand the impact of each loss function on the overall performance?
  - Meta: Substantial concerns about the experimental evaluation, including ablations, (slightly) more visually complex datasets, and overall limited evidence to support the proposed working of the method and disentangling being the key to the reported performance.
  - Rationale: The meta-review repeatedly cites concerns about ablations and evaluation (e.g., “not ready for publication,” “concerns about the experimental evaluation, including ablations”), which aligns with the reviewer claim about ablation studies and component impact. However, the meta-review centers on broader issues of clar...