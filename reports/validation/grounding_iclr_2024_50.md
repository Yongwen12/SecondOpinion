# Grounding Validation Report

- Status: `pass`
- Dataset: `iclr_2024`
- Model: `gpt-5-nano`
- Reviews checked: 50
- Final claims checked: 227

## Core Metrics

| Metric | Value |
| --- | ---: |
| Final grounding pass rate | 100.0% |
| Source field valid rate | 100.0% |
| Source text present rate | 100.0% |
| Source sentence index found rate | 23.8% |
| Raw candidate grounding pass rate | 89.0% |
| Reviews with no accepted claims | 1 (2.0%) |
| Review extraction errors | 0 (0.0%) |

## Source Fields

| Source field | Claims |
| --- | ---: |
| `questions` | 75 |
| `review_text` | 8 |
| `strengths` | 4 |
| `summary` | 5 |
| `weaknesses` | 135 |

## Raw Grounding Failures

- `2gTtKikoba` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: Within the simulated genome vector only the components [K_i, \nu_i^s, \nu_i^r] determine the steady state solution.
  - Source: `weaknesses` - It would be a good idea to highlight that within the simulated genome vector only the components [K_i, \nu_i^s, \nu_i^r] determine the steady state solution.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: The largest studied communities are 26 and this needs to be put in context with the other fields, citing Wikipedia “1010 to 1011 cells per gram of intestinal content” seems far off from the estimated single colonies.
  - Source: `weaknesses` - * The largest studied communities are 26 and this needs to be put in context with the other fields, citing Wikipedia “1010 to 1011 cells per gram of intestinal content” seems far off from the estimated single colonies.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: Adding it to the paper risks of overfitting the data even more.
  - Source: `weaknesses` - * Adding it to the paper risks of overfitting the data even more.
- `vb8QNXNzVn` / `cXs5md5wAq` (source_sentence_not_found)
  - Claim: Regarding the conclusion I’m a little confused as to why it doesn’t recommend including more data.
  - Source: `weaknesses` - * Regarding the conclusion I’m a little confused as to why it doesn’t recommend including more data. I believe the authors have devoted significant time to this paper and before we put others down this path, perhaps we should wait for more data or do the authors truly feel that GEMs will be the solution?
- `hZLx3fXD5m` / `kKRbAY4CXv` (source_sentence_not_found)
  - Claim: Interpretability: The paper discusses the use of neural networks, which are often seen as "black-box" models. While the paper addresses some interpretability challenges, it might not provide a complete solution to the interpretability issues associated with deep learning approaches.
  - Source: `weaknesses` - 4. **Interpretability**: The paper discusses the use of neural networks, which are often seen as \"black-box\" models. While the paper addresses some interpretability challenges, it might not provide a complete solution to the interpretability issues associated with deep learning approaches.
- `eSJOZmZeDG` / `kKRbAY4CXv` (source_sentence_not_found)
  - Claim: I don't understand where the nonlinear ODE is coming from in step 1 and then how there is \"numerically integration\" for the related linear PDE. Typically, in numerical methods a (non)linear PDE is first discretized in space and then the resulting semi-discrete form of the ODE is discretized in time. The authors should clarify what they mean here.
  - Source: `weaknesses` - I don't understand where the nonlinear ODE is coming from in step 1 and then how there is \"numerically integration\" for the related linear PDE. Typically, in numerical methods a (non)linear PDE is first discretized in space and then the resulting semi-discrete form of the ODE is discretized in time. The authors should clarify what they mean here.
- `eSJOZmZeDG` / `kKRbAY4CXv` (source_sentence_not_found)
  - Claim: Care should be taken with the discretization because this adds a first order error into the scheme. For example, the first equation should not be discretized with the 1st order accurate Forward Euler without even citing the method. This is an explicit method and there are necessary bounds on $\\Delta t$/\\tau to ensure numerical stability. See Krishnapriyan et. al, \"Learning continuous models...
  - Source: `weaknesses` - Care should be taken with the discretization because this adds a first order error into the scheme. For example, the first equation should not be discretized with the 1st order accurate Forward Euler without even citing the method. This is an explicit method and there are necessary bounds on $\\Delta t$/$\\tau$ to ensure numerical stability. See Krishnapriyan et. al, \"Learning continuous models for continuous physics\", 2023 (https://arxiv.org/pdf/2202.08494.pdf) on how the time discretization matters in NeuralODE and the 4th order RK4 is advantageous but even that scheme without being car...
- `eSJOZmZeDG` / `kKRbAY4CXv` (source_sentence_not_found)
  - Claim: Could use standard notation from numerical methods $\\Delta t$ instead $\\tau$
  - Source: `weaknesses` - Could use standard notation from numerical methods $\\Delta t$ instead $\\tau$
- `eSJOZmZeDG` / `kKRbAY4CXv` (source_sentence_not_found)
  - Claim: Does the method work only on semi-linear PDEs? If so, this is a bit limiting and the authors should discuss the extension to nonlinear PDEs.
  - Source: `questions` - Does the method work only on semi-linear PDEs? If so, this is a bit limiting and the authors should discuss the extension to nonlinear PDEs.
- `CZ5Y4HIwQW` / `ApjY32f3Xr` (source_sentence_not_found)
  - Claim: The page limit constraint is hitting the work hard in my opinion; by the time the authors present the data and experiments, there is less than half a page left to interpret the results and provide discussions and conclusions.
  - Source: `weaknesses` - 1. I'm saying out of respect to the author's work, but this paper may be more suited for a journal format. In particular, the page limit constraint is hitting the work hard in my opinion. \n\n * By the time the authors present the data and experiments, there is less than half a page left to interpret the results and provide discussions and conclusions.

## Final Claim Failures

No final accepted claim grounding failures.

## Warnings

- `uwuFudLbCi` / `kKRbAY4CXv` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: The strengths mention energy-stable time discretization and evolutionary kernel but the items repeat; need concise strengths without duplication.
  - Source: `strengths` - The method incorporates an evolutionary kernel, which inherently preserves the structure of the problem.
- `uwuFudLbCi` / `kKRbAY4CXv` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: The strengths mention energy-stable time discretization and evolutionary kernel but the items repeat; need concise strengths without duplication.
  - Source: `strengths` - The method incorporates an evolutionary kernel, which inherently preserves the structure of the problem.
- `4e1fSBB3OO` / `ApjY32f3Xr` (summary_or_strengths_source)
  - Claim: The tool provides a diverse set of 20 different PDEs spanning over various application domains.
  - Source: `summary` - The paper provides a benchmarking tool called PINNacle which was lacking in the domain of PINNs. The tool provides a diverse set of 20 different PDEs spanning over various application domains.
- `x6ra6HBgkh` / `fMX07g3prp` (summary_or_strengths_source)
  - Claim: The paper presents a simple and effective way to improve the predictive performance of GNNs for NAS. The empirical evaluation demonstrates that the performance increases with the number of datapoints, which is nice to see.
  - Source: `strengths` - - The paper presents a simple and effective way to improve the predictive performance of GNNs for NAS. The empirical evaluation demonstrates that the performance increases with the number of datapoints, which is nice to see.
- `ZNU7d8MOkM` / `qBL04XXex6` (summary_or_strengths_source)
  - Claim: The experiments are clear, the results are effective. And all experiments are classic experiments from CoT and ToT, so it is clear to compare BoT’s performance over CoT and ToT.
  - Source: `strengths` - The experiments are clear, the results are effective. And all experiments are classic experiments from CoT and ToT, so it is clear to compare BoT’s performance over CoT and ToT.
- `Ie1VUg7cqO` / `H9DYMIpz9c` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: Overall assessment: There are strong empirical results and a novel gradient-through-Adam method, but major notation issues, a flawed proof, and unclear assumptions demand substantial revisions before conclusions are credible.
  - Source: `summary` - The authors introduce a dataset distillation (DD) method called Farzi Data for data with a "left to right" (autoregressive) causal structure. Their algorithm has two novel elements: 1) the parameterization of the synthetic distilled data, which allows them to apply it to discrete data (such as the tokens in language modeling); and 2) a method for computing the outer loop gradient for DD when the inner loop is performed with Adam, which has a constant memory footprint independent of the number of inner optimization steps. They conduct extensive experiments with their proposed method on langu...
- `Ie1VUg7cqO` / `H9DYMIpz9c` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: Overall assessment: There are strong empirical results and a novel gradient-through-Adam method, but major notation issues, a flawed proof, and unclear assumptions demand substantial revisions before conclusions are credible.
  - Source: `summary` - The authors introduce a dataset distillation (DD) method called Farzi Data for data with a "left to right" (autoregressive) causal structure. Their algorithm has two novel elements: 1) the parameterization of the synthetic distilled data, which allows them to apply it to discrete data (such as the tokens in language modeling); and 2) a method for computing the outer loop gradient for DD when the inner loop is performed with Adam, which has a constant memory footprint independent of the number of inner optimization steps. They conduct extensive experiments with their proposed method on langu...
- `YktI8n3TeZ` / `rp5vfyp5Np` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: The paper claims robustness improvements but provides limited details on evaluation of robustness or attack robustness under varying conditions.
  - Source: `summary` - The method can be also used to improve the robustness of agents.
- `YktI8n3TeZ` / `rp5vfyp5Np` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: The paper claims robustness improvements but provides limited details on evaluation of robustness or attack robustness under varying conditions.
  - Source: `summary` - The method can be also used to improve the robustness of agents.
- `YktI8n3TeZ` / `rp5vfyp5Np` (summary_or_strengths_source, low_claim_source_overlap)
  - Claim: The explanation of success rates and whether the success is tied to the intended policy or the approximation raises concerns about evaluation bias.
  - Source: `strengths` - This paper proposes an interesting type of attacks that are oriented by desired behaviors. Compared to prior works focusing on reward minimizing, the proposed attack can be more widely applicable. In real-world environments where rewards are not well-defined, such attack objective can be interesting to investigate. Learning the intention policy from human preference is also an interesting idea, although I have some concerns on it (see weakness).
