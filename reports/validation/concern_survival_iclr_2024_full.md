# Concern Survival Via Meta-Review

- Snapshot: `20260522T083133Z`
- Model: `gpt-5-nano`
- Evaluable papers: 53
- Reviews evaluated: 205
- Claims evaluated: 854
- Dropped non-concern claims: 31
- Extraction errors: 0

## Core Metrics

| Metric | Value |
| --- | ---: |
| Strict survival rate | 8.8% |
| Loose survival rate | 41.3% |
| Survived claims | 75 |
| Partial claims | 278 |
| Not found claims | 501 |

## By Claim Type

| Claim type | Claims | Loose survived | Rate |
| --- | ---: | ---: | ---: |
| `ablation` | 14 | 5 | 35.7% |
| `baseline` | 44 | 27 | 61.4% |
| `clarity` | 131 | 45 | 34.4% |
| `ethics` | 19 | 7 | 36.8% |
| `experiment` | 331 | 136 | 41.1% |
| `general` | 57 | 25 | 43.9% |
| `methodology` | 82 | 42 | 51.2% |
| `novelty` | 79 | 42 | 53.2% |
| `theory` | 52 | 14 | 26.9% |
| `writing` | 45 | 10 | 22.2% |

## By Decision

| Decision | Papers | Claims | Loose survived | Rate |
| --- | ---: | ---: | ---: | ---: |
| `accept` | 16 | 229 | 91 | 39.7% |
| `reject` | 37 | 625 | 262 | 41.9% |

## Examples

### survived
- `cXs5md5wAq` / `vb8QNXNzVn` score=0.360 type=`general`
  - Claim: Conclusion regarding data: Unclear why the paper does not recommend including more data; implies need for more data or assessment of GEMs as solution.
  - Meta-review match: Just as one example, it's not clear why a fully-connected graph makes sense here (in the absence of more specific knowledge on the community graph).
- `kKRbAY4CXv` / `hZLx3fXD5m` score=0.413 type=`clarity`
  - Claim: Complexity: The proposed NEKM method is complex in its approach, involving the integration of operator splitting, boundary integral techniques, and Deep Neural Networks, which might be challenging for practitioners to implement and understand.
  - Meta-review match: 2) Once the details are recollected from different parts of the paper (namely, the BiNet approach that learns the density) it becomes clear that the paper uses the operator splitting plus BiNet to learn the neural network approximation to boundary potentials.
- `ApjY32f3Xr` / `C4sqXJNESI` score=0.425 type=`general`
  - Claim: Request discussion of limitations of benchmarking tool and avenues for future research to advance PINNs.
  - Meta-review match: After the rebuttal and discussion phase, however, I still think that the lacking novelty on the conceptual side is indeed a severe weakness of this paper, which could not be compensated by the experimental studies: In my opinion, the conclusions drawn from the benchmark experiments seem to be somewhat limited regarding truly novel insights into PINNs.
- `qBL04XXex6` / `1lDRac9ePM` score=0.380 type=`experiment`
  - Claim: LLMs can be unstable and prone to hallucination, which could result in bad or incorrect feedback when using the Boosting of Thoughts (BoT) iterative prompting framework. Is there analysis on the impact of "bad" LLM feedback?
  - Meta-review match: The paper introduces "Boosting of Thoughts" (BoT), a novel approach for problem-solving in Large Language Models (LLMs), marked by its conceptually clear framework that utilizes an iterative trial-and-error mechanism for prompt refinement.
- `qBL04XXex6` / `Fv3pXWd41e` score=0.569 type=`experiment`
  - Claim: The related claims that BoT and CoT outperform comparisons should be supported with explicit experimental details and comparisons; otherwise it remains unverified.
  - Meta-review match: the BoT methodology might incur high costs in API tokens due to its dependence on multiple iterations and frequent error analysis, an aspect that warrants further exploration to ensure fair comparison with CoT and ToT.
- `rp5vfyp5Np` / `YktI8n3TeZ` score=0.818 type=`general`
  - Claim: The human preference-based intention policy learning brings extra requirement and uncertainty to the process - the collection of human preference data can be expensive.
  - Meta-review match: Complexity and Uncertainty in Intention Policy Learning: The process of learning intention policy based on human preferences introduces extra requirements and uncertainties, including the expensive collection of human preference data and potential biases.
- `rp5vfyp5Np` / `YktI8n3TeZ` score=0.373 type=`general`
  - Claim: To obtain human preference labels, one need to first collect diverse behavior data so that human can pick the intended policy.
  - Meta-review match: Complexity and Uncertainty in Intention Policy Learning: The process of learning intention policy based on human preferences introduces extra requirements and uncertainties, including the expensive collection of human preference data and potential biases.
- `rp5vfyp5Np` / `YktI8n3TeZ` score=0.429 type=`experiment`
  - Claim: Is it clear how the attack success rate is defined and whether it could be biased since the intention policy is an approximation of real human intention?
  - Meta-review match: Important concepts like "intention policy" and "success rate" are not clearly defined.

### partial
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.315 type=`methodology`
  - Claim: The proposed approach for using GNNs for bacterial communities is vaguely described and not well justified.
  - Meta-review match: The paper studies bacterial communities by applying GNNs.
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.257 type=`methodology`
  - Claim: The key methods section (2.2) provides a generic description of existing GNN approaches, and is missing key microbiome specific information (in particular, what is the topology of the graph).
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `2gTtKikoba` score=0.284 type=`clarity`
  - Claim: The permutation invariance justification for using graph neural networks is confusing.
  - Meta-review match: Just as one example, it's not clear why a fully-connected graph makes sense here (in the absence of more specific knowledge on the community graph).
- `cXs5md5wAq` / `2gTtKikoba` score=0.243 type=`methodology`
  - Claim: Need details on how node attributes were obtained, especially nu's, since ground-truth a_ij not available.
  - Meta-review match: All reviewers generally agreed that the area is interesting, but raised a bunch of questions about the methodology, the details, scalability, and more.
- `cXs5md5wAq` / `vb8QNXNzVn` score=0.230 type=`clarity`
  - Claim: Motivation & Context: The paper's motivation needs clearer alignment with real-world applications.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `whc0meFjpm` score=0.206 type=`methodology`
  - Claim: Methodological novelty is limited since it is basically fitting a GNN on a bacterial community graph.
  - Meta-review match: Lack of methodological clarity.
- `rhgIgTSSxW` / `7UJsyfPyd4` score=0.215 type=`clarity`
  - Claim: A comparison of the inference and query complexity between the methods is lacking.
  - Meta-review match: The fourth reviewer seems unfair, and is the author of one of the competing methods puts forward in the critical review.
- `rhgIgTSSxW` / `CEBB2izG6I` score=0.247 type=`experiment`
  - Claim: What's the reason for choosing m to be 96? How does m affect the performance of TabR?
  - Meta-review match: The reviewers appreciated the extensive experiments, the writing, and the reproducibility of the work.

### not_found
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.169 type=`novelty`
  - Claim: Overall, the proposed method - applying GNN model in a straightforward way to a very small, fully-connected graph - is poorly justified and weak on novelty.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.146 type=`general`
  - Claim: What is the rationale for using a GNN on a very simple graph?
  - Meta-review match: Just as one example, it's not clear why a fully-connected graph makes sense here (in the absence of more specific knowledge on the community graph).
- `cXs5md5wAq` / `3FBIToMxSZ` score=0.000 type=`general`
  - Claim: What is the benefit of focusing on predicting steady state, instead of focusing on dynamical changes to the relative abundances (e.g., dysbiosis).
  - Meta-review match: No match
- `cXs5md5wAq` / `2gTtKikoba` score=0.190 type=`methodology`
  - Claim: The methodological contribution is limited as the presented work is mostly implementing GNNs for microbial steady state predictions.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `2gTtKikoba` score=0.183 type=`novelty`
  - Claim: This is a reasonable assumption to make. However the fact that this method works only for steady state solutions needs to be emphasized.
  - Meta-review match: Lack of methodological clarity.
- `cXs5md5wAq` / `2gTtKikoba` score=0.058 type=`experiment`
  - Claim: Did all such simulations lead to steady state solutions? Were any simulations that did not lead to steady state solutions discarded? Do the authors also have any comments on the frequency of steady state solutions when random parameters are used?
  - Meta-review match: All reviewers generally agreed that the area is interesting, but raised a bunch of questions about the methodology, the details, scalability, and more.
- `cXs5md5wAq` / `2gTtKikoba` score=0.144 type=`general`
  - Claim: The authors should square these two facts.
  - Meta-review match: While the authors provided some answers, ultimately there's enough outstanding questions and unclear items to make me believe the paper is still below the bar in the current iteration.
- `cXs5md5wAq` / `2gTtKikoba` score=0.051 type=`ethics`
  - Claim: The claim of interpretability seems to be questionable.
  - Meta-review match: All reviewers generally agreed that the area is interesting, but raised a bunch of questions about the methodology, the details, scalability, and more.
