# Grounding Validation Report

- Status: `pass`
- Dataset: `iclr_2024`
- Model: `gpt-5-nano`
- Reviews checked: 200
- Final claims checked: 887

## Core Metrics

| Metric | Value |
| --- | ---: |
| Final grounding pass rate | 100.0% |
| Source field valid rate | 100.0% |
| Source text present rate | 100.0% |
| Source sentence index found rate | 25.2% |
| Raw candidate grounding pass rate | 89.7% |
| Reviews with no accepted claims | 2 (1.0%) |
| Review extraction errors | 0 (0.0%) |

## Source Fields

| Source field | Claims |
| --- | ---: |
| `questions` | 309 |
| `review_text` | 30 |
| `strengths` | 14 |
| `summary` | 11 |
| `weaknesses` | 523 |

## Raw Grounding Failures

- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The steady state is entirely determined by the parameters $a_{i,j}$ and $K_i$. The authors use a vector composed of $[\mu_i, K_i, \nu_i^s, \nu_i^r, random]$ to simulate the genome data in their simulation. It would be a good idea to highlight that within the simulated genome vector only the components $[K_i, \nu_i^s, \nu_i^r]$ determine the steady state solution.
  - Source: `weaknesses` - 4. Given the GLV equations, the steady state solutions can be found by solving a system of $|S|$ linear algebraic equations:\n \\begin{equation}\\n \\sum_{j=1}^{|S|}a_{i,j}n_j = K_i.\\n\end{equation}\\nThe steady state is entirely determined by the parameters $a_{i,j}$ and $K_i$. The authors use a vector composed of $[\\mu_i, K_i, \\nu_i^s, \\nu_i^r, random]$ (where $a_{i,j} \\approx \\nu_i^s. \\nu_j^r$) to simulate the genome data in their simulation. It would be a good idea to highlight that within the simulated genome vector only the components $[K_i, \\nu_i^s, \\nu_i^r]$ determine the s...
- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The parameter $a_{i,j}$ contains information on the pairwise interaction between different species. On the other hand, the information in a genome is completely intrinsic to a particular species. The authors should square these two facts.
  - Source: `weaknesses` - 5. The parameter $a_{i,j}$ (broken into two vectors $\\nu_i^s, \\nu_j^r$ to simulate the genome) contains information on the pairwise interaction between different species. On the other hand, the information in a genome is completely intrinsic to a particular species. The authors should square these two facts.
- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: A proper simulation would entail simulation of the genome data. The genome data typically do not include information on interaction between species. But for simulations, the interaction matrix was used to derive $\\nu$ vectors. The claim of interpretability seems to be questionable.
  - Source: `weaknesses` - 6. A proper simulation would entail simulation of the genome data. The genome data typically do not include information on interaction between species. But for simulations, the interaction matrix was used to derive $\\nu$ vectors. The claim of interpretability seems to be questionable.
- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The authors need to provide details on how the node (genome) attributes were obtained, especially $\\nu$'s, as in real-world data, the ground-truth interaction $a_{ij}$ is not available.
  - Source: `weaknesses` - 8. The authors need to provide details on how the node (genome) attributes were obtained, especially $\\nu$'s, as in real-world data, the ground-truth interaction $a_{ij}$ is not available.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The largest studied communities are 26 and this needs to be put in context with the other fields, citing Wikipedia “1010 to 1011 cells per gram of intestinal content” seems far off from the estimated single colonies.
  - Source: `weaknesses` - * The largest studied communities are 26 and this needs to be put in context with the other fields, citing Wikipedia “1010 to 1011 cells per gram of intestinal content” seems far off from the estimated single colonies.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The types of bacteria should also be matched with the environment that you aim to generalize for.
  - Source: `weaknesses` - * The types of bacteria should also be matched with the environment that you aim to generalize for.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: Adding it to the paper risks of overfitting the data even more.
  - Source: `weaknesses` - * Adding it to the paper risks of overfitting the data even more.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: I wonder if the field wouldn’t benefit more from going from 500 samples to 1-2000 more than this paper.
  - Source: `weaknesses` - * I wonder if the field wouldn’t benefit more from going from 500 samples to 1-2000 more than this paper.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: E.g. keystone bacteria are not explained, good vs acceptable R2 is unclear to the reader (I can’t even find clearly how is this calculated, despite looking in appendix A which I should not have to for the main outcome)
  - Source: `weaknesses` - * E.g. keystone bacteria are not explained, good vs acceptable R2 is unclear to the reader (I can’t even find clearly how is this calculated, despite looking in appendix A which I should not have to for the main outcome), I assume that R2 is highly dependent on the underlying complexity, also the datasets have completely different bacteria suggesting that their purpose was different but this is unclear to me despite reading it several times.
- `LGzAT6gNeL` / `rhgIgTSSxW` (source_sentence_not_found)
  - Claim: Paper doesn't go into detail describing differences with prior deep learning-based tabular methods. What might explain the performance differences? Ex. "prior work, where several layers with multi-head attention between objects and features are often used" but was this what led to retrieval's low benefit in the past?
  - Source: `weaknesses` - Paper doesn't go into detail describing differences with prior deep learning-based tabular methods. What might explain the performance differences? Ex. \"prior work, where several layers with multi-head attention between objects and features are often used\" but was this what led to retrieval's low benefit in the past?

## Final Claim Failures

No final accepted claim grounding failures.

## Warnings

- `uwuFudLbCi` / `kKRbAY4CXv` (low_claim_source_overlap)
  - Claim: Repeated sentence about evolutionary kernel appears twice in review_text; no need to extract as separate point.
  - Source: `review_text` - The method incorporates an evolutionary kernel, which inherently preserves the structure of the problem.
- `CZ5Y4HIwQW` / `ApjY32f3Xr` (low_claim_source_overlap)
  - Claim: Adding such a description and correlating the numerical findings to the theoretical properties of each method is probably the most important, yet under-performed, part of the work in my opinion.
  - Source: `weaknesses` - To be clear, I understand the paper's space constraints, but this is very important in my opinion. The least the authors could do is to add such a section, however briefly, to the appendix.
- `x6ra6HBgkh` / `fMX07g3prp` (summary_or_strengths_source)
  - Claim: The paper presents a simple and effective way to improve the predictive performance of GNNs for NAS. The empirical evaluation demonstrates that the performance increases with the number of datapoints, which is nice to see.
  - Source: `strengths` - - The paper presents a simple and effective way to improve the predictive performance of GNNs for NAS. The empirical evaluation demonstrates that the performance increases with the number of datapoints, which is nice to see.
- `ZNU7d8MOkM` / `qBL04XXex6` (summary_or_strengths_source)
  - Claim: 1. This is an innovative extension of the Chain-of-Thought (CoT) and Tree-of-Thought (ToT) methods. Compared to CoT and ToT, the author adopts the idea on leveraging error analysis to refine the LLM. This can be a limitation of CoT and ToT, as they do not conduct error analysis and more importantly, learn from errors. The motivation is intuitive and clear.
  - Source: `strengths` - 1. This is an innovative extension of the Chain-of-Thought (CoT) and Tree-of-Thought (ToT) methods. Compared to CoT and ToT, the author adopts the idea on leveraging error analysis to refine the LLM. This can be a limitation of CoT and ToT, as they do not conduct error analysis and more importantly, learn from errors. The motivation is intuitive and clear.
- `6xFAd71bxb` / `H9DYMIpz9c` (summary_or_strengths_source)
  - Claim: This method doesn't work on datasets of that size, however this shows an improvement in scaling.
  - Source: `strengths` - This method doesn't work on datasets of that size, however this shows an improvement in scaling.
- `KqbT3NNcP2` / `H9DYMIpz9c` (summary_or_strengths_source)
  - Claim: Empirical results are thorough, although a bit limited in terms of number of datasets for sequence modeling (only PTB is used)
  - Source: `strengths` - Empirical results are thorough, although a bit limited in terms of number of datasets for sequence modeling (only PTB is used)
- `yPyy646e3D` / `miGpIhquyB` (summary_or_strengths_source)
  - Claim: The work would benefit from evaluating on more complex tasks to test generality
  - Source: `summary` - This work studies the quality of synthetic data generated by LLMs. The major contribution of this work is proposing a framework to evaluate LLM's ability to generate synthetic data for specific tasks, and compare behavior across different LLMs. The evaluation framework consists of five different axes: performance, complexity, conformity, diversity and faithfulness. These properties are either evaluated using accuracy-based metrics, or modified version of existing tools (e.g., distict-n, mauve, etc.). Using this framework, this work compares LLMs with different size, from different model fam...
- `REwQirNHgK` / `miGpIhquyB` (low_claim_source_overlap)
  - Claim: There are several works that aim to improve the quality of prompts to yield higher-quality datasets, some examples include: Chung et al... Yu et al...
  - Source: `weaknesses` - - Chung et al. "Increasing Diversity While Maintaining Accuracy: Text Data Generation with Large Language Models and Human Interventions." ACL 2023.
- `wadmtNhdKQ` / `6AtXCnHCFy` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: There is a lack of broader validation beyond two datasets and limited baselines.
  - Source: `summary` - This paper introduces a special domain generalization scenario termed Load-Domain domain generalization and proposes a new model, the Feature Shift Network (FSN), tailored for this scenario. The authors conduct experiments on the CWRU bearing dataset and the MNIST dataset, comparing FSN with classical fault diagnosis methods and other domain generalization methods.
- `wadmtNhdKQ` / `6AtXCnHCFy` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: There is a lack of broader validation beyond two datasets and limited baselines.
  - Source: `summary` - This paper introduces a special domain generalization scenario termed Load-Domain domain generalization and proposes a new model, the Feature Shift Network (FSN), tailored for this scenario. The authors conduct experiments on the CWRU bearing dataset and the MNIST dataset, comparing FSN with classical fault diagnosis methods and other domain generalization methods.
