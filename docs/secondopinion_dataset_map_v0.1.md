# SecondOpinion — Peer-Review Dataset Map (verified, v0.1)

A curated, **verified** map of public peer-review datasets, organized by which axis of SecondOpinion's product each one serves.

**Product framing (decided):** author-facing rebuttal assistant — comment **materiality** triage + **resolution** check (does the rebuttal substantively address the concern). *Not* a journal-side audit tool, *not* an acceptance/uptake predictor.

**Master source:** Kuznetsov et al. 2024, *What Can NLP Do for Peer Review?* (arXiv:2405.06563) + companion dataset repo (`github.com/OAfzal/nlp-for-peer-review`). Most rows are drawn from / cross-checked against that repo; recent additions (Re², RbtAct, DEFEND, ContraSciView, RevCI, BetterPR) were verified individually.

**Verified column:** ✓ = confirmed in this review (direct source or the authoritative repo); ⚠ = name/figure not independently confirmed — check before relying.

**Two caveats that apply to every row:**
- **Domain:** almost all are NLP/ML-conference data — close to your ICLR target (an advantage), but field norms differ. Clean for *evaluation*; watch transfer for *training*.
- **None of these is your core label.** No public dataset annotates "did the rebuttal *substantively resolve* the concern." That label is your IAA pilot. External data can pre-train / bootstrap / validate *components* — it cannot replace the core.

---

## 1. Rebuttal alignment & response structure  — prerequisites for resolution; Form-2 strategy

| Dataset | Year / venue | What it annotates | Your axis | ✓ | Link |
|---|---|---|---|---|---|
| **Re²** | 2025, arXiv | Full-stage review + multi-turn rebuttal: 19,926 submissions / 70,668 reviews / 53,818 rebuttals; **consistency-ensured (initial-submission text)**; incl. scores before/after, aspect ratings, meta-reviews, decisions | Largest base for author-side rebuttal pipeline; carries score-change target | ✓ | arXiv:2505.07920 · HF: `Daoze/ReviewRebuttal` |
| **RbtAct** | 2026, arXiv | Rebuttal as supervision; separates comments that **led to concrete revisions/plans** vs **only defended**; actionable feedback generation | **Closest prior art to your resolution idea** — bootstrap source *and* competitor | ✓ | arXiv:2603.09723 |
| **DISAPERE** | 2022, NAACL | Multi-layer discourse structure between reviews & rebuttals (review actions, rebuttal stances) | Review↔rebuttal stance/action; partial overlap w/ not-addressed/deflects | ✓ | ACL 2022.naacl-main.89 · `github.com/nnkennard/DISAPERE` |
| **APE** (Argument Pair Extraction) | 2020, EMNLP | Links review arguments to their rebuttal responses (argument pairs); ~4,764 pairs ⚠ | Comment↔rebuttal mapping layer | ✓ (count ⚠) | ACL 2020.emnlp-main.569 · `github.com/LiyingCheng95/ArgumentPairExtraction` |
| **DEFEND** | 2026, arXiv | Extends ReviewCritique: rebuttal-action labels + gold rebuttal-segment mapping (small: 4 papers / 185 segments) | Rebuttal-action taxonomy; too small to be gold | ✓ | arXiv:2603.27360 |
| **Jiu-Jitsu Argumentation** | 2023, EMNLP | Review statements w/ attitude roots, themes, canonical rebuttals | Rebuttal-strategy generation (Form 2) | ✓ | ACL 2023.emnlp-main.894 |

## 2. Substantive resolution  — your CORE; not externally available

| Source | What it covers | Note |
|---|---|---|
| **Your own IAA pilot** | Expert judgment: did the rebuttal *substantively resolve* the concern (fully / partial / deflects-generic / not-addressed) | The core label. **External data cannot replace this.** |

> **Resolution-gold ladder** (near → far from your construct): SubstanReview / ReviewCritique (review quality only) → DISAPERE / APE (stance / pairing) → RbtAct (revision-vs-defended, auto-derived from rebuttal) → **your pilot (expert substantive-resolution)**. Your pilot stays at the top and is unavoidable; RbtAct's signal is the best thing to bootstrap from.

## 3. Adjacent signals for comment priority  — not direct materiality

| Dataset | Year / venue | What it annotates | Your axis | ✓ | Link |
|---|---|---|---|---|---|
| **ReAct** | 2022, arXiv | Review-comment **actionability** classification | Can benchmark whether a comment admits a concrete response/action | ✓ | arXiv:2210.00443 · `github.com/gtmdotme/ReAct` |
| **BetterPR** | 2022, TPDL | Constructive vs non-constructive comments | Can benchmark constructiveness / usefulness, not importance | ✓ | Springer 978-3-031-16802-4_53 · `github.com/PrabhatkrBharti/BetterPR` |
| **"Not all peer reviews are significant"** | 2026, Scientometrics | Exhaustive vs trivial reviews (CoT) | Closest external proxy for significance; verify construct fit before use | ✓ | Springer s11192-025-05435-7 |
| **Peer Review Analyze** | — | (listed by collaborator; actionability-adjacent) | Actionability-adjacent; verify before use | ⚠ | verify before use |

**Important correction:** none of these directly annotates SecondOpinion's strongest version of **materiality**: whether a concern hits the paper's core contribution, central evidence, or decision-critical claim. They can benchmark adjacent priority signals (actionability, constructiveness, substantiation, deficiency), but the core materiality construct still needs the IAA pilot.

## 4. Evidence / substantiation  — the "did the reviewer justify it" sub-axis of A

| Dataset | Year / venue | What it annotates | Your axis | ✓ | Link |
|---|---|---|---|---|---|
| **SubstanReview** | 2023, EMNLP-F | Claim↔evidence pairs in reviews; substantiation = reviewer attached a justification (550 reviews; 50 w/ Likert) | "Specific & reasoned vs vague/bald assertion" — **not** correctness, **not** importance | ✓ | ACL 2023.findings-emnlp.684 · `github.com/YanzhuGuo/SubstanReview` |
| **ReviewCritique** | 2024, arXiv | Per-segment **deficiency** labels + explanations; human + LLM reviews; expert annotators (16 PhD / 11 faculty) | Review-segment quality / deficiency (broad) | ✓ | arXiv:2406.16253 |

## 5. Reviewer tone / confidence  — auxiliary (read tone vs substance); v2 enrichment

| Dataset | Year / venue | What it annotates | Your axis | ✓ | Link |
|---|---|---|---|---|---|
| **HedgePeer** | 2022, JCDL | Hedge cues / uncertainty spans | Reviewer conviction (how firm is the concern) | ✓ | ACM 10.1145/3529372.3533300 · `github.com/Tirthankar-Ghosal/HedgePeer-Dataset` |
| **PolitePEER** | 2023, LRE | Politeness intensity | "Polite-but-deadly" detection | ✓ | Springer s10579-023-09662-3 · `github.com/PrabhatkrBharti/PolitePEER` |
| **"Please be polite to your peers"** | 2024, Scientometrics | Tone + objectivity (multi-task) | Tone vs substance | ✓ | Springer s11192-024-04938-z |

## 6. Cross-reviewer agreement / contradiction  — your consensus leg

| Dataset | Year / venue | What it annotates | Your axis | ✓ | Link |
|---|---|---|---|---|---|
| **ContraSciView** (= "When Reviewers Lock Horn") | 2023, EMNLP | ~8.5k papers, ~28k review pairs (ICLR + NeurIPS); agree vs contradict; built on ASAP-Review | Consensus / disagreement — replace your noisy lexical-overlap proxy | ✓ | arXiv:2310.18685 · `github.com/sandeep82945/Contradiction-in-Peer-Review` |
| **RevCI** | 2026, arXiv | Graded contradiction *intensity* + evidence pairs; extends ContraSciView | Finer consensus signal | ✓ | arXiv:2605.10171 |

## 7. Author actually revised / outcome  — resolution-by-revision; prediction target

| Dataset | Year / venue | What it annotates | Your axis | ✓ | Link |
|---|---|---|---|---|---|
| **ARIES** | 2023, arXiv | Review comments ↔ the paper edits made in response | "Did the author actually change it" (resolution-by-revision) | ✓ | arXiv:2306.12587 · `github.com/allenai/aries` |
| **Does my rebuttal matter?** | 2019, NAACL | Review scores **before / after rebuttal** (ACL 2018) | Score-change target — *only if* you ever pursue prediction | ✓ | ACL N19-1129 |
| *(Re² also carries before/after scores — see §1)* | | | | | |

## 8. Argument structure / claim extraction  — validate your extraction

| Dataset | Year / venue | What it annotates | Your axis | ✓ | Link |
|---|---|---|---|---|---|
| **AMPERE** | 2019, NAACL | 10,386 argumentative propositions from 400 review comments + types | Claim extraction / proposition typing | ✓ | ACL N19-1219 |
| **ASAP-Review / ReviewAdvisor** | 2022, JAIR | Aspect + sentiment annotation of reviews | Aspect categorization (clarity / novelty / …) | ✓ | JAIR 128622 · `github.com/neulab/ReviewAdvisor` |
| **COMPARE** | 2021, arXiv | Comparison-discussion sentences + taxonomy | A specific concern type ("compare to X") | ✓ | arXiv:2108.04366 |
| **Fromm et al. argument mining** | 2021, AAAI | Argument structures in reviews | Argument mining | ✓ | AAAI 16607 |

## 9. General base / benchmark  — scale; not your product label

| Dataset | Year / venue | What it annotates | ✓ | Link |
|---|---|---|---|---|
| **NLPeer** | 2023, ACL | Unified, structured papers + reviews, cross-domain (backbone for many others) | ✓ | ACL 2023.acl-long.277 |
| **PeerRead** | 2018, NAACL | First NLP peer-review dataset; acceptance / score prediction | ✓ | ACL N18-1149 · `github.com/allenai/PeerRead` |
| **MOPRD** | 2023, arXiv | Multidisciplinary open peer review, whole process | ✓ | arXiv:2212.04972 |

## 10. Meta-review  — deprioritized in your roadmap

| Dataset | Year / venue | What it annotates | ✓ | Link |
|---|---|---|---|---|
| **PeerSum** | 2023, EMNLP-F | Meta-review as a summary of the full thread (conflicting info) | ✓ | ACL 2023.findings-emnlp.472 · `github.com/oaimli/PeerSum` |

## Out of scope  — process integrity, not an author-side product
Reviewer-anchoring RCT (2023) · Malicious paper bidding (2023) · Catch-Me-If-I-Can strategic reviewing (2020) · Reviewer-assignment gold standard (2023) · AAMAS bidding (2017). All real (in the master repo); none relevant to a comment-quality / resolution product.

---

## How to use this (priority for your next phase)

1. **Start the IAA pilot in parallel now** — expert labels on **substantive resolution + core materiality** (§2). Nothing here substitutes for it, and benchmarks should not become a reason to delay this gate.
2. **Fastest clean benchmark:** use ContraSciView / RevCI (§6) to replace the noisy lexical consensus proxy. These are closest to your ICLR/NeurIPS domain and directly target a known weak leg.
3. **Bootstrap / pre-train, don't replace:** RbtAct + DISAPERE + APE + Re² (§1) for comment↔rebuttal mapping & rebuttal-action; ReAct + BetterPR + SubstanReview (§3, §4) for adjacent priority signals such as actionability / constructiveness / substantiation.
4. **Treat domain transfer explicitly:** ICLR/NeurIPS-native resources such as ContraSciView and Re² give stronger evidence for your current data domain; ARR/NLP-journal resources are useful component tests but weaker product evidence.
5. **v2 enrichment only:** tone / conviction (§5). Relevant for author-facing interpretation, but don't let it re-expand the product before the core is validated.
6. **Pipeline check (from Re²):** make sure you align reviews against the **initial submission**, not the revised / camera-ready PDF — otherwise grounding & resolution get spurious results.
7. **If you ever pursue prediction:** use **reviewer score-change** (Re² / "Does my rebuttal matter?", §7), *not* meta-review uptake — and beat baseline before putting it in any pitch.

## Product/pitch interpretation

External datasets support the claim that peer-review comment quality, actionability, rebuttal structure, tone, and contradiction are active research problems. That is useful evidence, but it also means the space is becoming crowded. The defensible SecondOpinion claim is not simply "we combine existing components." It is: **we validate substantive-resolution and core-materiality judgments for an author-facing rebuttal workflow, then turn those judgments into practical triage and pressure-testing tools.**

**⚠ Not independently confirmed in this review:** "Peer Review Analyze" (name) · APE pair count (~4,764) · "RMR-75K" exact name (the RbtAct *paper* is confirmed; verify the dataset's name/size in-paper).
