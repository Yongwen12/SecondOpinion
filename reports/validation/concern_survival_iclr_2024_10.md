# Concern Survival Via Meta-Review

- Snapshot: `20260522T083133Z`
- Model: `gpt-5-nano`
- Evaluable papers: 8
- Reviews evaluated: 34
- Claims evaluated: 151
- Dropped non-concern claims: 6
- Extraction errors: 0

## Core Metrics

| Metric | Value |
| --- | ---: |
| Strict survival rate | 6.0% |
| Loose survival rate | 41.1% |
| Survived claims | 9 |
| Partial claims | 53 |
| Not found claims | 89 |

## By Claim Type

| Claim type | Claims | Loose survived | Rate |
| --- | ---: | ---: | ---: |
| `baseline` | 9 | 2 | 22.2% |
| `clarity` | 15 | 4 | 26.7% |
| `ethics` | 5 | 2 | 40.0% |
| `experiment` | 53 | 19 | 35.9% |
| `general` | 12 | 6 | 50.0% |
| `methodology` | 16 | 10 | 62.5% |
| `novelty` | 18 | 12 | 66.7% |
| `theory` | 14 | 4 | 28.6% |
| `writing` | 9 | 3 | 33.3% |

## Examples

### survived
- `qBL04XXex6` / `ZNU7d8MOkM` score=0.384 type=`experiment`
  - Claim: The paper claims BoT shows a clear advancement but provides limited independent evidence beyond CoT/ToT baselines; need clearer experimental validation.
  - Meta-review match: the BoT methodology might incur high costs in API tokens due to its dependence on multiple iterations and frequent error analysis, an aspect that warrants further exploration to ensure fair comparison with CoT and ToT.
- `rp5vfyp5Np` / `YktI8n3TeZ` score=0.818 type=`ethics`
  - Claim: The human preference-based intention policy learning brings extra requirement and uncertainty to the process - the collection of human preference data can be expensive.
  - Meta-review match: Complexity and Uncertainty in Intention Policy Learning: The process of learning intention policy based on human preferences introduces extra requirements and uncertainties, including the expensive collection of human preference data and potential biases.
- `rp5vfyp5Np` / `YktI8n3TeZ` score=0.459 type=`methodology`
  - Claim: How are the behavior sequences generated for human preference labeling?
  - Meta-review match: Lack of Practicality and Scalability: The reliance on extensive human labeling and assumptions about adversaries' capabilities raise concerns regarding the method's real-world applicability and scalability.
- `rp5vfyp5Np` / `YktI8n3TeZ` score=0.365 type=`novelty`
  - Claim: There is a question about the generalization to diverse environments or whether the method would require predefined target policies.
  - Meta-review match: The choice of baselines and limited defense methods used in experimentation also raise questions about the fairness and comprehensiveness of the evaluations.
- `rp5vfyp5Np` / `YktI8n3TeZ` score=0.525 type=`general`
  - Claim: The paper claims the method can improve robustness of agents; need evidence or discussion on this claim.
  - Meta-review match: The choice of baselines and limited defense methods used in experimentation also raise questions about the fairness and comprehensiveness of the evaluations.
- `rp5vfyp5Np` / `cJESK6o5Pr` score=0.441 type=`theory`
  - Claim: Additionally, the rationale for using preference-based RL remains unclear.
  - Meta-review match: Address Methodological Gaps: Providing more details about the training process, data requirements, and rationale for using preference-based RL would strengthen the paper.
- `rp5vfyp5Np` / `cJESK6o5Pr` score=0.634 type=`methodology`
  - Claim: The paper lacks some critical methodological details. For example, it doesn't specify how the victim policy approximator is trained or the volume of data required, leaving gaps in the understanding of the implementation.
  - Meta-review match: Inadequate Methodological Details and Evaluations: Critical details about the training of the victim policy approximator and the volume of data required are missing.
- `rp5vfyp5Np` / `vGNqxpozDP` score=0.342 type=`experiment`
  - Claim: The presentation of experimental results is somewhat confusing. The differences of scenarios in Figure 4 and 5 are not clear, and additional explanations are required for the target coordinates mentioned for Figure 4. Captions of Figures 7 (a) and (b) might need to be swapped, and sections (c) and (d) require clearer explanations.
  - Meta-review match: Confusing Presentation and Incomplete Discussion of Limitations: The paper lacks clarity in the presentation of experimental results and methodologies.

### partial
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.315 type=`methodology`
  - Claim: The proposed approach for using GNNs for bacterial communities is vaguely described and not well justified.
  - Meta-review match: The paper studies bacterial communities by applying GNNs.
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.257 type=`methodology`
  - Claim: The key methods section (2.2) provides a generic description of existing GNN approaches, and is missing key microbiome specific information (in particular, what is the topology of the graph).
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `2gTtKikoba` score=0.217 type=`theory`
  - Claim: the fact that this method works only for steady state solutions needs to be emphasized.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `2gTtKikoba` score=0.239 type=`clarity`
  - Claim: The authors appear to be confused on equivariance and invariance. The permutation invariance justification for using graph neural networks is confusing.
  - Meta-review match: Just as one example, it's not clear why a fully-connected graph makes sense here (in the absence of more specific knowledge on the community graph).
- `cXs5md5wAq` / `2gTtKikoba` score=0.208 type=`methodology`
  - Claim: The authors need to provide details on how the node (genome) attributes were obtained, especially $\nu$'s, as in real-world data, the ground-truth interaction $a_{ij}$ is not available.
  - Meta-review match: All reviewers generally agreed that the area is interesting, but raised a bunch of questions about the methodology, the details, scalability, and more.
- `cXs5md5wAq` / `whc0meFjpm` score=0.206 type=`methodology`
  - Claim: Methodological novelty is limited since it is basically fitting a GNN on a bacterial community graph.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `whc0meFjpm` score=0.255 type=`methodology`
  - Claim: Modeling the dynamics sounds interesting. Could the authors also use GNN in an iterative way to model the dynamics?
  - Meta-review match: All reviewers generally agreed that the area is interesting, but raised a bunch of questions about the methodology, the details, scalability, and more.
- `rhgIgTSSxW` / `7UJsyfPyd4` score=0.215 type=`theory`
  - Claim: A comparison of the inference and query complexity between the methods is lacking.
  - Meta-review match: The fourth reviewer seems unfair, and is the author of one of the competing methods puts forward in the critical review.

### not_found
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.169 type=`novelty`
  - Claim: Overall, the proposed method - applying GNN model in a straightforward way to a very small, fully-connected graph - is poorly justified and weak on novelty.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.146 type=`general`
  - Claim: What is the rationale for using a GNN on a very simple graph?
  - Meta-review match: Just as one example, it's not clear why a fully-connected graph makes sense here (in the absence of more specific knowledge on the community graph).
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.000 type=`experiment`
  - Claim: What is the benefit of focusing on predicting steady state, instead of focusing on dynamical changes to the relative abundances (e.g., dysbiosis).
  - Meta-review match: No match
- `cXs5md5wAq` / `2gTtKikoba` score=0.190 type=`methodology`
  - Claim: The methodological contribution is limited as the presented work is mostly implementing GNNs for microbial steady state predictions.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `2gTtKikoba` score=0.058 type=`experiment`
  - Claim: Did all such simulations lead to steady state solutions? Were any simulations that did not lead to steady state solutions discarded? Do the authors also have any comments on the frequency of steady state solutions when random parameters are used?
  - Meta-review match: All reviewers generally agreed that the area is interesting, but raised a bunch of questions about the methodology, the details, scalability, and more.
- `cXs5md5wAq` / `2gTtKikoba` score=0.051 type=`theory`
  - Claim: The parameter $a_{i,j}$ contains information on the pairwise interaction between different species. On the other hand, the information in a genome is completely intrinsic to a particular species. The authors should square these two facts.
  - Meta-review match: While the authors provided some answers, ultimately there's enough outstanding questions and unclear items to make me believe the paper is still below the bar in the current iteration.
- `cXs5md5wAq` / `2gTtKikoba` score=0.051 type=`ethics`
  - Claim: A proper simulation would entail simulation of the genome data. The genome data typically do not include information on interaction between species. But for simulations, the interaction matrix was used to derive $\nu$ vectors. The claim of interpretability seems to be questionable.
  - Meta-review match: All reviewers generally agreed that the area is interesting, but raised a bunch of questions about the methodology, the details, scalability, and more.
- `cXs5md5wAq` / `2gTtKikoba` score=0.198 type=`methodology`
  - Claim: How the nodes, edges and their associated attributes/features were constructed, especially based on the real-world data?
  - Meta-review match: Lack of methodological clarity.
