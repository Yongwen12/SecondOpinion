# Grounding Validation Report

- Status: `pass`
- Dataset: `iclr_2024`
- Model: `gpt-5-nano`
- Reviews checked: 20
- Final claims checked: 88

## Core Metrics

| Metric | Value |
| --- | ---: |
| Final grounding pass rate | 100.0% |
| Source field valid rate | 100.0% |
| Source text present rate | 100.0% |
| Source char span found rate | 100.0% |
| Source paragraph locator found rate | 100.0% |
| Source bullet locator found rate | 67.0% |
| Legacy source sentence index found rate | 27.3% |
| Raw candidate grounding pass rate | 86.1% |
| Reviews with no accepted claims | 0 (0.0%) |
| Review extraction errors | 0 (0.0%) |

## Source Fields

| Source field | Claims |
| --- | ---: |
| `questions` | 32 |
| `review_text` | 6 |
| `weaknesses` | 50 |

## Raw Grounding Failures

- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: It would be a good idea to highlight that within the simulated genome vector only the components [K_i, \nu_i^s, \nu_i^r] determine the steady state solution.
  - Source: `weaknesses` - 4. Given the GLV equations, the steady state solutions can be found by solving a system of $|S|$ linear algebraic equations:\n \begin{equation}\n \sum_{j=1}^{|S|}a_{i,j}n_j = K_i.\n\end{equation}\nThe steady state is entirely determined by the parameters $a_{i,j}$ and $K_i$. The authors use a vector composed of $[\mu_i, K_i, \nu_i^s, \nu_i^r, random]$ (where $a_{i,j} \approx \nu_i^s. \nu_j^r$) to simulate the genome data in their simulation. It would be a good idea to highlight that within the simulated genome vector only the components $[K_i, \nu_i^s, \nu_i^r]$ determine the steady state s...
  - Locator: not located
- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The authors appear to be confused on equivariance and invariance. The permutation invariance justification for using graph neural networks is confusing.
  - Source: `weaknesses` - 7. The authors appear to be confused on equivariance and invariance. The permutation invariance justification for using graph neural networks is confusing. For example, GLV models are widely used to model the dynamics of microorganisms. But the GLV model is not permutation invariant. The authors stated "\\textit{When shuffling the order of bacteria within the train and test communities, the accuracy of MLPs drops significantly, clearly showing that the dynamics learned by MLPs are not invariant to permutations...}" It is to be expected that shuffling the data will lead to reduction in perfo...
  - Locator: not located
- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The authors need to provide details on how the node (genome) attributes were obtained, especially $\\nu$'s, as in real-world data, the ground-truth interaction $a_{ij}$ is not available.
  - Source: `weaknesses` - 8. The authors need to provide details on how the node (genome) attributes were obtained, especially $\\nu$'s, as in real-world data, the ground-truth interaction $a_{ij}$ is not available.
  - Locator: not located
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The largest studied communities are 26 and this needs to be put in context with the other fields, citing Wikipedia “1010 to 1011 cells per gram of intestinal content” seems far off from the estimated single colonies.
  - Source: `weaknesses` - * The largest studied communities are 26 and this needs to be put in context with the other fields, citing Wikipedia “1010 to 1011 cells per gram of intestinal content” seems far off from the estimated single colonies.
  - Locator: not located
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: Adding it to the paper risks of overfitting the data even more.
  - Source: `weaknesses` - * Adding it to the paper risks of overfitting the data even more.
  - Locator: not located
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: I wonder if the field wouldn’t benefit more from going from 500 samples to 1-2000 more than this paper.
  - Source: `weaknesses` - * I wonder if the field wouldn’t benefit more from going from 500 samples to 1-2000 more than this paper.
  - Locator: not located
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: keystone bacteria are not explained, good vs acceptable R2 is unclear to the reader (I can’t even find clearly how is this calculated, despite looking in appendix A which I should not have to for the main outcome), I assume that R2 is highly dependent on the underlying complexity, also the datasets have completely different bacteria suggesting that their purpose was different but this is unclea...
  - Source: `weaknesses` - * keystone bacteria are not explained, good vs acceptable R2 is unclear to the reader (I can’t even find clearly how is this calculated, despite looking in appendix A which I should not have to for the main outcome), I assume that R2 is highly dependent on the underlying complexity, also the datasets have completely different bacteria suggesting that their purpose was different but this is unclear to me despite reading it several times.
  - Locator: not located
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: Regarding the conclusion I’m a little confused as to why it doesn’t recommend including more data. I believe the authors have devoted significant time to this paper and before we put others down this path, perhaps we should wait for more data or do the authors truly feel that GEMs will be the solution?
  - Source: `weaknesses` - * Regarding the conclusion I’m a little confused as to why it doesn’t recommend including more data. I believe the authors have devoted significant time to this paper and before we put others down this path, perhaps we should wait for more data or do the authors truly feel that GEMs will be the solution?
  - Locator: not located
- `CEBB2izG6I` / `rhgIgTSSxW` (source_sentence_not_found)
  - Claim: Some aspects are not clear, see the questions section.
  - Source: `summary` - 1. Some aspects are not clear, see the questions section.
  - Locator: not located
- `eSJOZmZeDG` / `kKRbAY4CXv` (source_sentence_not_found)
  - Claim: I don't understand where the nonlinear ODE is coming from in step 1 and then how there is "numerically integration" for the related linear PDE. Typically, in numerical methods a (non)linear PDE is first discretized in space and then the resulting semi-discrete form of the ODE is discretized in time. The authors should clarify what they mean here.
  - Source: `weaknesses` - - I don't understand where the nonlinear ODE is coming from in step 1 and then how there is "numerically integration" for the related linear PDE. Typically, in numerical methods a (non)linear PDE is first discretized in space and then the resulting semi-discrete form of the ODE is discretized in time. The authors should clarify what they mean here.
  - Locator: not located

## Final Claim Failures

No final accepted claim grounding failures.

## Warnings

No warning examples in the sampled accepted claims.
