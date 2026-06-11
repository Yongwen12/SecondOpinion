const pipelineLayers = [
  {
    name: "Ingestion",
    steps: [
      {
        title: "Parse submission",
        artifact: "Venue: ICLR",
        note: "Detected an ICLR-style OpenReview submission."
      },
      {
        title: "Collect reviews",
        artifact: "Reviews and scores",
        note: "Found reviewer ratings, confidences, and full review text."
      }
    ]
  },
  {
    name: "Review analysis",
    steps: [
      {
        title: "Classify stance",
        artifact: "Reviewer + SO stance",
        note: "Mapped reviewer posture separately from Second Opinion agreement with reviewer points."
      },
      {
        title: "Extract claims",
        artifact: "Claim-level points",
        note: "Separated actionable criticisms from summaries and praise."
      },
      {
        title: "Cluster issues",
        artifact: "Cross-review issues",
        note: "Baseline and evaluation concerns overlap across multiple reviewers."
      },
      {
        title: "Score review quality",
        artifact: "SO scores ready",
        note: "Novelty framing is risky, but likely addressable with clearer positioning."
      }
    ]
  },
  {
    name: "Rebuttal",
    steps: [
      {
        title: "Prioritize responses",
        artifact: "High-priority points",
        note: "High-overlap issues are promoted into the rebuttal workspace."
      },
      {
        title: "Draft suggestions",
        artifact: "5 response blocks",
        note: "Drafted concise, evidence-led response suggestions for each issue."
      },
      {
        title: "Tone check",
        artifact: "Direct, non-defensive",
        note: "Final guidance avoids arguing with reviewers and focuses on evidence."
      }
    ]
  }
];

const stanceScale = [
  ["strongly_disagree", "Needs help"],
  ["disagree", "Strongly questionable"],
  ["mixed", "Questionable"],
  ["agree", "Partly valid"],
  ["strongly_agree", "Well supported"]
];

const demoConfigs = {
  "paper-evidence-chain": {
    src: "./demos/evidence_chain_demo.json",
    format: "evidence-chain"
  },
  "paper-microbial": {
    src: "./demos/demo_three_papers_audit_results.json",
    paperId: "cXs5md5wAq"
  },
  "paper-tabr": {
    src: "./demos/demo_three_papers_audit_results.json",
    paperId: "rhgIgTSSxW"
  },
  "paper-nekm": {
    src: "./demos/demo_three_papers_audit_results.json",
    paperId: "kKRbAY4CXv"
  }
};

const analysis = {
  paperTitle: "Second Opinion Demo Submission",
  venue: "ICLR",
  year: "2026",
  metrics: [
    ["5.25", "Avg score"],
    ["3.75", "Avg confidence"],
    ["75.8", "Avg SO score"],
    ["5", "Issue clusters"],
    ["3", "High priority"]
  ],
  overview: {
    situation: "Borderline, with a clear path to a stronger rebuttal. The main risk is not the average score; it is that two reviewers frame the contribution as under-positioned against baselines.",
    leverage: "Reviewer 2 has the best score-change potential: the concerns are specific, evidence-facing, and mostly answerable within the rebuttal window.",
    strategy: "Lead with one contribution claim, then answer baseline and evaluation concerns before lower-level presentation issues.",
    scoreDistribution: [
      ["4.0", 36],
      ["4.5", 55],
      ["5.0", 82],
      ["5.5", 74],
      ["6.0", 46],
      ["6.5+", 22]
    ]
  },
  reviewers: [
    {
      id: "R1",
      score: 6,
      confidence: 4,
      qualityScore: 82,
      stance: "supportive",
      potential: "Medium",
      headline: "Mostly positive, asks for sharper novelty framing.",
      auditSummary: "High-quality review: specific, professional, and mostly actionable. The novelty concern needs more explicit manuscript grounding.",
      dominantAuditStance: "agree",
      stanceSummary: "Second Opinion agrees with most R1 points, while marking the novelty critique as only partly grounded.",
      stanceBreakdown: {
        strongly_disagree: 0,
        disagree: 0,
        mixed: 1,
        agree: 3,
        strongly_agree: 1
      },
      dimensions: {
        Professionalism: 92,
        Specificity: 78,
        "Evidence grounding": 74,
        Actionability: 84,
        Fairness: 82
      },
      response: "Thank R1 for recognizing the contribution, then make the novelty claim more concrete and cite the exact section where the method differs."
    },
    {
      id: "R2",
      score: 4,
      confidence: 3,
      qualityScore: 61,
      stance: "skeptical",
      potential: "High",
      headline: "Concerned about missing baselines and experimental breadth.",
      auditSummary: "Uneven review quality: the main concerns are important, but some claims are broader than the retrieved manuscript evidence supports.",
      dominantAuditStance: "disagree",
      stanceSummary: "Second Opinion disagrees with several broad R2 claims, but agrees that baseline coverage needs a precise response.",
      stanceBreakdown: {
        strongly_disagree: 1,
        disagree: 2,
        mixed: 1,
        agree: 1,
        strongly_agree: 0
      },
      dimensions: {
        Professionalism: 76,
        Specificity: 67,
        "Evidence grounding": 52,
        Actionability: 63,
        Fairness: 49
      },
      response: "Prioritize R2. Acknowledge the baseline concern, add a compact comparison table, and state which additional experiment can be completed."
    },
    {
      id: "R3",
      score: 5,
      confidence: 4,
      qualityScore: 72,
      stance: "mixed",
      potential: "Medium",
      headline: "Likes the idea but doubts whether the evaluation proves the central claim.",
      auditSummary: "Generally useful review: the evaluation concern is fair, but the review compresses several distinct issues into one broad objection.",
      dominantAuditStance: "mixed",
      stanceSummary: "Second Opinion is mixed on R3: the evaluation concern is valid, but the novelty comparison needs more evidence.",
      stanceBreakdown: {
        strongly_disagree: 0,
        disagree: 1,
        mixed: 2,
        agree: 2,
        strongly_agree: 0
      },
      dimensions: {
        Professionalism: 86,
        Specificity: 69,
        "Evidence grounding": 66,
        Actionability: 70,
        Fairness: 71
      },
      response: "Tie the main claim to the strongest existing results. Avoid overclaiming; define the scope more tightly."
    },
    {
      id: "R4",
      score: 6,
      confidence: 4,
      qualityScore: 88,
      stance: "supportive",
      potential: "Low",
      headline: "Supportive review with presentation-level requests.",
      auditSummary: "Strong review quality: concise, professional, and well calibrated to fixable presentation issues.",
      dominantAuditStance: "strongly_agree",
      stanceSummary: "Second Opinion strongly agrees that R4's points are fair, low-risk, and directly actionable.",
      stanceBreakdown: {
        strongly_disagree: 0,
        disagree: 0,
        mixed: 1,
        agree: 2,
        strongly_agree: 2
      },
      dimensions: {
        Professionalism: 95,
        Specificity: 84,
        "Evidence grounding": 82,
        Actionability: 90,
        Fairness: 88
      },
      response: "Answer briefly. Do not spend too much rebuttal budget unless the AC echoes this concern."
    }
  ],
  priorities: [
    ["Baseline comparison", "Must address before novelty or writing issues."],
    ["Evaluation scope", "Clarify what the experiments prove and what they do not prove."],
    ["Contribution framing", "Move from general novelty language to a concrete differentiator."]
  ],
  issues: [
    {
      title: "Missing baseline comparison",
      raisedBy: ["R2", "R3"],
      severity: "High",
      fixability: "Medium",
      priority: "Must",
      summary: "Reviewers think the paper does not sufficiently compare against the most relevant non-specialized baseline.",
      assessment: "This is the highest leverage issue because it appears in multiple reviews and directly affects the credibility of the experimental claim.",
      strategy: "Acknowledge and clarify. Add a short comparison table if possible, and explicitly justify why the current baselines answer the core research question.",
      quotes: [
        "The evaluation would be stronger with a direct comparison to a simpler non-LLM baseline.",
        "It is unclear whether the proposed pipeline is better than a standard retrieval baseline."
      ],
      draft: "We agree that a direct comparison to a simpler baseline helps clarify the contribution. In the revision, we will add a compact baseline table and clarify that our claim is not that the pipeline dominates all retrieval systems, but that evidence-grounded review-point auditing benefits from claim-level decomposition plus manuscript-grounded verification."
    },
    {
      title: "Novelty is under-framed",
      raisedBy: ["R1", "R3"],
      severity: "Medium",
      fixability: "High",
      priority: "High",
      summary: "The novelty may be present, but the reviews suggest the paper does not state it crisply enough.",
      assessment: "This looks like a communication gap rather than a fatal technical weakness.",
      strategy: "Lead with a one-sentence contribution claim and map it to the closest prior work.",
      quotes: [
        "The idea is interesting, but the paper should more clearly state what is new.",
        "I am not fully convinced that the contribution is distinct from existing review-assistance tools."
      ],
      draft: "We will revise the introduction to state the contribution more concretely: Second Opinion audits reviewer claims rather than generating replacement reviews, and each judgment is tied to reviewer wording, retrieved manuscript evidence, stance, and rebuttal guidance."
    },
    {
      title: "Evaluation scope is narrow",
      raisedBy: ["R2"],
      severity: "Medium",
      fixability: "Medium",
      priority: "High",
      summary: "A reviewer worries that the current evaluation does not show robustness across enough submissions.",
      assessment: "The critique is fair if the paper presents broad claims, but manageable if the rebuttal narrows the claim and adds a small additional sample.",
      strategy: "Concede and fix. State what can be added now and what remains future work.",
      quotes: [
        "The system is evaluated on too few examples to support the broader claim."
      ],
      draft: "We agree that the current evaluation is an MVP-scale study. We will soften the broad claim, add two additional ICLR submissions in the appendix, and report where the system fails or requires human expert judgment."
    },
    {
      title: "Method description is hard to follow",
      raisedBy: ["R4"],
      severity: "Low",
      fixability: "High",
      priority: "Medium",
      summary: "The review asks for clearer wording around pipeline stages and reliability checks.",
      assessment: "This is easy to fix and should be answered briefly.",
      strategy: "Cite existing evidence and promise a diagram or clearer stage names.",
      quotes: [
        "The pipeline would be easier to follow with clearer naming of each stage."
      ],
      draft: "We will add a pipeline figure and rename the stages to Ingestion, Review Analysis, Evidence Grounding, and Rebuttal Guidance."
    },
    {
      title: "Claims may require external expertise",
      raisedBy: ["R2"],
      severity: "Medium",
      fixability: "Low",
      priority: "Medium",
      summary: "Some novelty and field-consensus judgments cannot be fully settled from the manuscript alone.",
      assessment: "This should be framed as a limitation of the current system rather than over-defended.",
      strategy: "Explain scope and describe planned external-reference support.",
      quotes: [
        "For novelty judgments, it is unclear how the system knows the broader literature."
      ],
      draft: "We agree that novelty and field-consensus judgments require external references. The current MVP uses manuscript-grounded evidence only and downgrades confidence for such claims; future versions will add venue guidelines and literature-grounded retrieval."
    }
  ]
};

let activeTab = "overview";
let activeIssue = 0;
let activeReviewer = 0;
let activeClaim = 0;
let activeAnalysis = analysis;
let activeAnalysisPromise = Promise.resolve(analysis);

const form = document.querySelector("#analysis-form");
const pipelineSection = document.querySelector("#pipeline");
const workspaceSection = document.querySelector("#workspace");
const pipelineLayersEl = document.querySelector("#pipeline-layers");
const analysisLogEl = document.querySelector("#analysis-log");
const pipelineTitleEl = document.querySelector("#pipeline-title");
const paperTitleEl = document.querySelector("#paper-title");
const paperMetricsEl = document.querySelector("#paper-metrics");
const reviewerRailEl = document.querySelector("#reviewer-rail");
const tabPanelEl = document.querySelector("#tab-panel");

form.addEventListener("submit", (event) => {
  event.preventDefault();
  activeAnalysisPromise = loadSelectedAnalysis();
  startAnalysis();
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    activeTab = button.dataset.tab;
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item === button));
    renderTab();
  });
});

function startAnalysis() {
  pipelineSection.classList.remove("hidden");
  workspaceSection.classList.add("hidden");
  analysisLogEl.innerHTML = "";
  pipelineTitleEl.textContent = "Running layered review analysis";
  renderPipeline(0);
  pipelineSection.scrollIntoView({ behavior: "smooth", block: "start" });

  const flatSteps = pipelineLayers.flatMap((layer, layerIndex) =>
    layer.steps.map((step, stepIndex) => ({ ...step, layerIndex, stepIndex }))
  );

  flatSteps.forEach((step, index) => {
    window.setTimeout(() => {
      renderPipeline(index + 1);
      addLog(step.note);
      if (index === flatSteps.length - 1) {
        window.setTimeout(showWorkspace, 450);
      }
    }, 520 * (index + 1));
  });
}

function renderPipeline(doneCount) {
  const flatIndexFor = (layerIndex, stepIndex) => {
    let count = 0;
    for (let i = 0; i < layerIndex; i += 1) {
      count += pipelineLayers[i].steps.length;
    }
    return count + stepIndex;
  };

  pipelineLayersEl.innerHTML = pipelineLayers
    .map((layer, layerIndex) => {
      const layerStart = flatIndexFor(layerIndex, 0);
      const layerEnd = layerStart + layer.steps.length;
      const status = doneCount >= layerEnd ? "Complete" : doneCount > layerStart ? "Active" : "Queued";
      const steps = layer.steps
        .map((step, stepIndex) => {
          const flatIndex = flatIndexFor(layerIndex, stepIndex);
          const state = doneCount > flatIndex ? "done" : doneCount === flatIndex ? "current" : "pending";
          const icon = state === "done" ? "✓" : flatIndex + 1;
          return `
            <div class="step ${state}">
              <span class="step-icon">${icon}</span>
              <span>
                <span class="step-title">${escapeHtml(step.title)}</span>
                <span class="step-artifact">${state === "pending" ? "" : escapeHtml(step.artifact)}</span>
              </span>
            </div>
          `;
        })
        .join("");
      return `
        <article class="layer">
          <div class="layer-head">
            <h3>${escapeHtml(layer.name)}</h3>
            <span class="layer-status">${status}</span>
          </div>
          <div class="steps">${steps}</div>
        </article>
      `;
    })
    .join("");
}

function addLog(note) {
  const li = document.createElement("li");
  li.textContent = note;
  analysisLogEl.prepend(li);
}

async function showWorkspace() {
  pipelineTitleEl.textContent = "Analysis complete";
  try {
    activeAnalysis = await activeAnalysisPromise;
  } catch (error) {
    console.error(error);
    activeAnalysis = analysis;
  }
  activeIssue = 0;
  activeReviewer = 0;
  activeClaim = 0;
  workspaceSection.classList.remove("hidden");
  renderWorkspace();
  workspaceSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderWorkspace() {
  paperTitleEl.textContent = `${activeAnalysis.venue} ${activeAnalysis.year} · ${activeAnalysis.paperTitle}`;
  paperMetricsEl.innerHTML = activeAnalysis.metrics
    .map(([value, label]) => `<div class="metric-chip"><b>${escapeHtml(value)}</b><span>${escapeHtml(label)}</span></div>`)
    .join("");
  reviewerRailEl.innerHTML = activeAnalysis.reviewers
    .map(
      (reviewer) => `
        <div class="reviewer-mini">
          <strong>${reviewer.id}<span>${reviewer.score} / ${reviewer.confidence}</span></strong>
          <div class="mini-score">
            <span>SO score</span>
            <b>${reviewer.qualityScore}</b>
          </div>
          <span class="mini-stance ${stanceClass(reviewer.dominantAuditStance)}">
            ${escapeHtml(stanceLabel(reviewer.dominantAuditStance))}
          </span>
          <span>${escapeHtml(reviewer.headline)}</span>
        </div>
      `
    )
    .join("");
  renderTab();
}

function renderTab() {
  workspaceSection.classList.toggle("reviewers-mode", activeTab === "reviewers");
  if (activeTab === "overview") {
    renderOverview();
    return;
  }
  if (activeTab === "reviewers") {
    renderReviewers();
    return;
  }
  renderRebuttal();
}

function renderOverview() {
  tabPanelEl.innerHTML = `
    <div class="overview-stack">
      <article class="surface">
        <div class="surface-head">
          <h3>Quick summary</h3>
          <p>${escapeHtml(activeAnalysis.overview.situation)}</p>
        </div>
        <div class="surface-body">
          <div class="summary-grid">
            <ul class="status-list">
              <li><b>Highest leverage reviewer</b><span>${escapeHtml(activeAnalysis.overview.leverage)}</span></li>
              <li><b>Response strategy</b><span>${escapeHtml(activeAnalysis.overview.strategy)}</span></li>
            </ul>
            <div class="summary-score-panel">
              <h4>Review audit scores</h4>
              ${renderReviewerScoreBoard()}
            </div>
          </div>
        </div>
      </article>

      <article class="surface">
        <div class="surface-head">
          <h3>Second Opinion stance map</h3>
          <p>Color-coded support for reviewer points, from contradicted to well supported.</p>
        </div>
        <div class="surface-body">
          ${renderStanceLegend()}
          ${renderStanceMap()}
        </div>
      </article>
    </div>
  `;
}

function renderReviewers() {
  const reviewers = activeAnalysis.reviewers || [];
  activeReviewer = Math.max(0, Math.min(activeReviewer, reviewers.length - 1));
  const reviewer = reviewers[activeReviewer] || reviewers[0];
  const claims = Array.isArray(reviewer?.claims) ? reviewer.claims : [];
  activeClaim = Math.max(0, Math.min(activeClaim, claims.length - 1));

  tabPanelEl.innerHTML = `
    <div class="reviewer-analysis-stack">
      <div class="reviewer-tab-layout">
        <div class="reviewer-tabs" role="tablist" aria-label="Reviewers">
          ${reviewers
            .map(
              (item, index) => `
                <button
                  class="reviewer-tab ${index === activeReviewer ? "active" : ""}"
                  type="button"
                  role="tab"
                  aria-selected="${index === activeReviewer}"
                  data-reviewer-tab="${index}"
                >
                  <strong>${item.id}</strong>
                  <span>${item.score} / ${item.confidence}</span>
                  <b class="${stanceClass(item.dominantAuditStance)}">${stanceLabel(item.dominantAuditStance)}</b>
                </button>
              `
            )
            .join("")}
        </div>
        ${reviewer ? renderReviewerDetailPanel(reviewer, activeClaim) : ""}
      </div>
    </div>
  `;

  tabPanelEl.querySelectorAll("[data-reviewer-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      activeReviewer = Number(button.dataset.reviewerTab);
      activeClaim = 0;
      renderReviewers();
    });
  });

  tabPanelEl.querySelectorAll("[data-claim-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      activeClaim = Number(button.dataset.claimTab);
      renderReviewers();
    });
  });
}

function renderReviewerDetailPanel(reviewer, selectedClaimIndex) {
  const claims = Array.isArray(reviewer.claims) ? reviewer.claims : [];
  return `
    <article class="reviewer-detail-panel">
      <div class="selected-reviewer-head">
        <div class="reviewer-summary-copy">
          <h3>${reviewer.id}</h3>
          <div class="review-meta">
            <span class="badge">Score ${reviewer.score}</span>
            <span class="badge">Confidence ${reviewer.confidence}</span>
            <span class="badge stance ${reviewer.stance}">${capitalize(reviewer.stance)}</span>
            <span class="badge ${reviewer.potential.toLowerCase()}">${reviewer.potential} potential</span>
            <span class="badge">${claims.length} claims</span>
          </div>
          <p>${escapeHtml(reviewer.headline)}</p>
        </div>
        <div class="reviewer-summary-metrics">
          <div class="mini-distribution">
            ${renderStanceDistribution(reviewer.stanceBreakdown)}
            <b class="stance-pill ${stanceClass(reviewer.dominantAuditStance)}">${stanceLabel(reviewer.dominantAuditStance)}</b>
          </div>
          <div class="score-summary" aria-label="Second Opinion reviewer assessment">
            <div class="so-stance-label ${stanceClass(reviewer.dominantAuditStance)}">
              <span>SO stance</span>
              <b>${stanceLabel(reviewer.dominantAuditStance)}</b>
            </div>
            <div class="quality-score ${qualityClass(reviewer.qualityScore)}">
              <b>${reviewer.qualityScore}</b>
              <span>SO score</span>
            </div>
          </div>
        </div>
      </div>

      <div class="reviewer-detail-body">
        <div class="reviewer-audit-grid">
          <section>
            <h4>Review quality dimensions</h4>
            <div class="score-stack">
              ${renderScoreRows(reviewer.dimensions)}
            </div>
          </section>
          <section>
            <h4>Rebuttal instruction</h4>
            <div class="draft-box">
              <p>${escapeHtml(reviewer.response)}</p>
            </div>
          </section>
        </div>

        <section>
          <h4>Extracted claims and scores</h4>
          ${renderClaimTabs(claims, selectedClaimIndex)}
        </section>
      </div>
    </article>
  `;
}

function renderRebuttal() {
  const issue = activeAnalysis.issues[activeIssue] || activeAnalysis.issues[0];
  tabPanelEl.innerHTML = `
    <div class="issue-workspace">
      <div class="issue-list">
        ${activeAnalysis.issues
          .map(
            (item, index) => `
              <button class="issue-button ${index === activeIssue ? "active" : ""}" type="button" data-issue="${index}">
                <strong>${escapeHtml(item.title)}</strong>
                <span>${item.raisedBy.join(", ")} · ${item.priority} priority</span>
              </button>
            `
          )
          .join("")}
      </div>

      <article class="issue-detail">
        <div class="issue-detail-section">
          <div class="issue-top">
            <div>
              <h3>${escapeHtml(issue.title)}</h3>
              <div class="issue-meta">
                <span class="badge">Raised by ${issue.raisedBy.join(", ")}</span>
                <span class="badge ${issue.severity.toLowerCase()}">${issue.severity} severity</span>
                <span class="badge ${issue.fixability.toLowerCase()}">${issue.fixability} fixability</span>
                <span class="badge ${issue.priority.toLowerCase()}">${issue.priority} priority</span>
              </div>
            </div>
          </div>
        </div>

        <div class="issue-detail-section">
          <p>${escapeHtml(issue.summary)}</p>
          ${issue.scores ? renderIssueScoreStrip(issue.scores) : ""}
        </div>

        <div class="issue-detail-section">
          <h3>Second Opinion assessment</h3>
          <p>${escapeHtml(issue.assessment)}</p>
        </div>

        <div class="issue-detail-section">
          <h3>Reviewer quotes</h3>
          <ul class="quote-list">
            ${issue.quotes.map((quote) => `<li>${escapeHtml(quote)}</li>`).join("")}
          </ul>
        </div>

        ${issue.evidence_chain ? `
          <div class="issue-detail-section">
            <h3>Evidence chain</h3>
            ${renderEvidenceChain(issue.evidence_chain)}
          </div>
        ` : ""}

        <div class="issue-detail-section">
          <h3>Suggested strategy</h3>
          <p>${escapeHtml(issue.strategy)}</p>
        </div>

        <div class="issue-detail-section">
          <h3>Draft response</h3>
          <div class="draft-box">
            <p>${escapeHtml(issue.draft)}</p>
          </div>
        </div>
      </article>
    </div>
  `;

  tabPanelEl.querySelectorAll(".issue-button").forEach((button) => {
    button.addEventListener("click", () => {
      activeIssue = Number(button.dataset.issue);
      renderRebuttal();
    });
  });
}

function renderIssueScoreStrip(scores) {
  const items = [
    ["Grounding", scores.grounding],
    ["Evidence", scores.evidence_support],
    ["Rebuttal resolved", scores.rebuttal_resolution],
    ["Robustness", scores.lifecycle_robustness]
  ];
  return `
    <div class="issue-score-strip">
      ${items
        .map(([label, value]) => `<span><b>${formatPercent(numberOrNull(value) || 0)}</b>${escapeHtml(label)}</span>`)
        .join("")}
    </div>
  `;
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function labelize(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderReviewerScoreBoard() {
  return `
    <div class="reviewer-score-board">
      ${activeAnalysis.reviewers
        .map(
          (reviewer) => `
            <div class="audit-score-row">
              <div>
                <strong>${reviewer.id}</strong>
                <span>${escapeHtml(reviewer.auditSummary)}</span>
              </div>
              <div class="audit-score-meter">
                <div class="score-track">
                  <span class="score-fill ${qualityClass(reviewer.qualityScore)}" style="width:${reviewer.qualityScore}%"></span>
                </div>
                <b>${reviewer.qualityScore}</b>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderClaimTabs(claims, selectedClaimIndex) {
  if (!claims.length) {
    return `<p class="empty-note">No extracted claim breakdown is available for this reviewer.</p>`;
  }
  const safeIndex = Math.max(0, Math.min(selectedClaimIndex, claims.length - 1));
  const selectedClaim = claims[safeIndex];
  return `
    <div class="claim-tab-layout">
      <div class="claim-tabs" role="tablist" aria-label="Extracted claims">
        ${claims
          .map(
            (claim, index) => `
              <button
                class="claim-tab ${index === safeIndex ? "active" : ""}"
                type="button"
                role="tab"
                aria-selected="${index === safeIndex}"
                data-claim-tab="${index}"
              >
                <strong>Claim ${claim.claimIndex}</strong>
                <span>${escapeHtml(truncate(claim.claim_text || "Reviewer claim", 72))}</span>
                <b class="${stanceClass(claim.normalizedStance)}">${stanceLabel(claim.normalizedStance)}</b>
              </button>
            `
          )
          .join("")}
      </div>
      <div class="claim-detail-panel">
        ${renderClaimCard(selectedClaim)}
      </div>
    </div>
  `;
}

function renderClaimCard(claim) {
  const chainHtml = claim.evidence_chain ? renderEvidenceChain(claim.evidence_chain) : "";
  const scoreExplanationHtml = claim.score_explanations ? renderScoreExplanations(claim.score_explanations) : "";
  return `
    <article class="claim-card">
      <div class="claim-card-head">
        <div>
          <h5>Claim ${claim.claimIndex}</h5>
          <p>${escapeHtml(claim.claim_text || "Reviewer claim was extracted, but no text was recorded.")}</p>
        </div>
        <span class="stance-pill ${stanceClass(claim.normalizedStance)}">SO: ${stanceLabel(claim.normalizedStance)}</span>
      </div>

      <div class="claim-meta">
        <span class="badge">${escapeHtml(labelize(claim.claim_type || "claim"))}</span>
        <span class="badge">${escapeHtml(capitalize(String(claim.importance || "medium")))}</span>
        <span class="badge">${escapeHtml(labelize(claim.verdict || "not recorded"))}</span>
        <span class="badge ${claim.guidancePriority}">${capitalize(claim.guidancePriority)} priority</span>
      </div>

      <div class="claim-score-grid">
        ${renderClaimScoreRows(claim)}
      </div>

      <div class="claim-analysis-grid">
        <div class="claim-note">
          <b>Second Opinion assessment</b>
          <p>${escapeHtml(claim.second_opinion_take || claim.reasoning_summary || "No claim-level assessment was recorded.")}</p>
        </div>
        <div class="claim-note">
          <b>Reviewer source</b>
          <p>${escapeHtml(claim.source_sentence || claim.claim_text || "No source sentence recorded.")}</p>
        </div>
        <div class="claim-note claim-note-wide">
          <b>Suggested rebuttal</b>
          <p>${escapeHtml(claim.rebuttal_guidance?.suggested_response || "Answer this point with the strongest available evidence and avoid overclaiming.")}</p>
        </div>
      </div>
      ${scoreExplanationHtml}
      ${chainHtml}
    </article>
  `;
}

function renderClaimCards(claims) {
  if (!claims.length) {
    return `<p class="empty-note">No extracted claim breakdown is available for this reviewer.</p>`;
  }
  return `
    <div class="claim-list">
      ${claims
        .map((claim) => renderClaimCard(claim))
        .join("")}
    </div>
  `;
}

function renderClaimScoreRows(claim) {
  const rows = claim.scores
    ? [
        ["Grounding", claim.scores.grounding, 1],
        ["Specificity", claim.scores.specificity, 1],
        ["Evidence support", claim.scores.evidence_support, 1],
        ["Consensus", claim.scores.consensus, 1],
        ["Rebuttal resolved", claim.scores.rebuttal_resolution, 1],
        ["Lifecycle robust", claim.scores.lifecycle_robustness, 1]
      ]
    : [
        ["Support", claim.support_score, 100],
        ["Answer coverage", claim.answer_coverage_score, 100],
        ["Question value", claim.question_value_score, 100],
        ["Specificity", claim.specificity, 4],
        ["Evidence support", claim.evidence_support, 4],
        ["Actionability", claim.actionability, 4],
        ["Fairness", claim.fairness_score, 100]
      ];
  const filteredRows = rows.filter(([, value]) => numberOrNull(value) !== null);

  return filteredRows
    .map(([label, value, max]) => {
      const numeric = numberOrNull(value) || 0;
      const percent = Math.max(0, Math.min(100, Math.round((numeric / max) * 100)));
      const display = max === 1 ? `${Math.round(percent)}%` : max === 100 ? String(Math.round(numeric)) : `${numeric}/4`;
      return `
        <div class="claim-score-row">
          <span>${escapeHtml(label)}</span>
          <div class="score-track">
            <span class="score-fill ${qualityClass(percent)}" style="width:${percent}%"></span>
          </div>
          <b>${escapeHtml(display)}</b>
        </div>
      `;
    })
    .join("");
}

function renderScoreExplanations(explanations) {
  const entries = Object.entries(explanations || {}).filter(([, value]) => value);
  if (!entries.length) {
    return "";
  }
  return `
    <details class="score-explain">
      <summary>Score explanations</summary>
      <div class="score-explain-grid">
        ${entries
          .map(([key, value]) => `<p><b>${escapeHtml(labelize(key))}</b><span>${escapeHtml(value)}</span></p>`)
          .join("")}
      </div>
    </details>
  `;
}

function renderEvidenceChain(chain) {
  const groups = [
    ["Original / manuscript evidence", chain.manuscript],
    ["External evidence", chain.external],
    ["Inter-reviewer consensus", chain.consensus],
    ["Author rebuttal", chain.rebuttal],
    ["Meta-review uptake", chain.meta_review],
    ["Post-rebuttal discussion", chain.discussion]
  ];
  return `
    <details class="evidence-chain" open>
      <summary>Evidence chain</summary>
      <div class="evidence-chain-grid">
        ${groups
          .map(([title, records]) => renderEvidenceGroup(title, records || []))
          .join("")}
      </div>
    </details>
  `;
}

function renderEvidenceGroup(title, records) {
  if (!records.length) {
    return `
      <section class="evidence-node empty">
        <h6>${escapeHtml(title)}</h6>
        <p>No signal recorded.</p>
      </section>
    `;
  }
  return `
    <section class="evidence-node">
      <h6>${escapeHtml(title)}</h6>
      ${records
        .slice(0, 3)
        .map(
          (record) => `
            <blockquote>
              <b>${escapeHtml(record.label || record.source_type || "Evidence")}</b>
              <p>${escapeHtml(truncate(record.text || "", 260))}</p>
            </blockquote>
          `
        )
        .join("")}
    </section>
  `;
}

function renderScoreRows(dimensions) {
  return Object.entries(dimensions)
    .map(
      ([label, value]) => `
        <div class="score-row">
          <span>${escapeHtml(label)}</span>
          <div class="score-track">
            <span class="score-fill ${qualityClass(value)}" style="width:${value}%"></span>
          </div>
          <b>${value}</b>
        </div>
      `
    )
    .join("");
}

function renderStanceLegend() {
  return `
    <div class="stance-legend" aria-label="Second Opinion stance legend">
      ${stanceScale
        .map(
          ([key, label]) => `
            <span>
              <i class="${stanceClass(key)}"></i>
              ${escapeHtml(label)}
            </span>
          `
        )
        .join("")}
    </div>
  `;
}

function renderStanceMap() {
  return `
    <div class="stance-map">
      ${activeAnalysis.reviewers
        .map(
          (reviewer) => `
            <div class="stance-map-row">
              <div>
                <strong>${reviewer.id}</strong>
                <span>${escapeHtml(reviewer.stanceSummary)}</span>
              </div>
              <div class="stance-map-main">
                ${renderStanceDistribution(reviewer.stanceBreakdown)}
                <b class="stance-pill ${stanceClass(reviewer.dominantAuditStance)}">${stanceLabel(reviewer.dominantAuditStance)}</b>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderStanceDistribution(breakdown) {
  const total = Object.values(breakdown).reduce((sum, value) => sum + value, 0) || 1;
  const segments = stanceScale
    .map(([key, label]) => {
      const count = breakdown[key] || 0;
      if (!count) {
        return "";
      }
      const width = Math.max(8, Math.round((count / total) * 100));
      return `
        <span
          class="stance-segment ${stanceClass(key)}"
          style="width:${width}%"
          title="${escapeHtml(label)}: ${count}"
          aria-label="${escapeHtml(label)}: ${count}"
        ></span>
      `;
    })
    .join("");
  return `<div class="stance-distribution">${segments}</div>`;
}

function stanceLabel(value) {
  const found = stanceScale.find(([key]) => key === value);
  return found ? found[1] : "Questionable";
}

function stanceClass(value) {
  return `so-stance-${String(value || "mixed").replaceAll("_", "-")}`;
}

function qualityClass(score) {
  if (score >= 80) {
    return "quality-high";
  }
  if (score >= 65) {
    return "quality-mid";
  }
  return "quality-low";
}

async function loadSelectedAnalysis() {
  const demoSelect = document.querySelector("#demo-select");
  const selectedDemo = demoSelect ? demoSelect.value : "paper-microbial";
  const demoConfig = demoConfigs[selectedDemo];
  if (!demoConfig) {
    return analysis;
  }
  const response = await fetch(demoConfig.src, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Unable to load demo dataset: ${response.status}`);
  }
  const auditResult = await response.json();
  if (auditResult.schema_version === "evidence-chain-demo-v0.1" || demoConfig.format === "evidence-chain") {
    return buildAnalysisFromEvidenceChainDemo(auditResult);
  }
  return buildAnalysisFromAuditResult(auditResult, demoConfig);
}

function buildAnalysisFromEvidenceChainDemo(demo) {
  const paper = demo.paper || {};
  const reviewers = (demo.reviewers || []).map((reviewer, reviewerIndex) => {
    const claims = (reviewer.claims || []).map((claim, claimIndex) => ({
      ...claim,
      claimIndex: claim.claim_index || claimIndex + 1,
      claim_text: claim.claim_text,
      normalizedStance: normalizeStance(claim.stance),
      guidancePriority: guidancePriority(claim)
    }));
    const stanceBreakdown = getStanceBreakdown(claims);
    const dominantAuditStance = getDominantStance(stanceBreakdown);
    const qualityScore = Math.round((numberOrNull(reviewer.review_reliability_score) || 0) * 100);
    return {
      id: reviewer.display_id || `R${reviewerIndex + 1}`,
      review_id: reviewer.review_id,
      score: reviewer.rating || "n/a",
      confidence: reviewer.confidence || "n/a",
      qualityScore,
      stance: "mixed",
      potential: reviewer.high_risk_claim_count >= 2 ? "High" : reviewer.high_risk_claim_count === 1 ? "Medium" : "Low",
      headline: reviewer.summary || "Evidence-chain reviewer analysis.",
      auditSummary: `${reviewer.high_risk_claim_count || 0} high-risk claims. Lifecycle robustness ${formatPercent(reviewer.mean_lifecycle_robustness)}.`,
      dominantAuditStance,
      stanceSummary: `SecondOpinion stance distribution across ${claims.length} evidence-chain claims.`,
      stanceBreakdown,
      dimensions: {
        "Reviewer reliability": qualityScore,
        "Lifecycle robustness": Math.round((numberOrNull(reviewer.mean_lifecycle_robustness) || 0) * 100),
        "High-risk pressure": Math.min(100, (reviewer.high_risk_claim_count || 0) * 25)
      },
      claims,
      response: bestReviewerGuidance(claims)
    };
  });
  const workspace = demo.rebuttal_workspace || [];
  return {
    paperTitle: paper.title || "Evidence-chain demo",
    venue: paper.venue || "ICLR",
    year: String(paper.year || "2024"),
    metrics: [
      [String(demo.summary?.review_count || reviewers.length), "Reviews"],
      [String(demo.summary?.claim_count || 0), "Claims"],
      [String(demo.summary?.high_priority_claim_count || 0), "High priority"],
      [formatPercent(demo.summary?.mean_reviewer_reliability), "Reliability"],
      [formatPercent(demo.summary?.mean_lifecycle_robustness), "Robustness"]
    ],
    overview: {
      situation: `${demo.summary?.claim_count || 0} reviewer claims are organized into an auditable evidence chain for this paper.`,
      leverage: workspace[0]
        ? `${workspace[0].display_id || workspace[0].review_id} has the top rebuttal item: ${truncate(workspace[0].claim_text, 130)}`
        : "No high-priority rebuttal item is available.",
      strategy: "Read high-priority claim cards first, then expand evidence chains and score explanations before drafting the response."
    },
    reviewers,
    priorities: workspace.slice(0, 5).map((item) => [
      truncate(item.claim_text, 84),
      `${labelize(item.priority)} / ${labelize(item.strategy)}: ${truncate(item.suggested_response, 140)}`
    ]),
    issues: workspace.slice(0, 8).map((item) => ({
      title: truncate(item.claim_text, 82),
      raisedBy: [item.display_id || item.review_id],
      severity: item.priority === "must" ? "High" : "Medium",
      fixability: item.strategy === "add_experiment" ? "Medium" : "High",
      priority: labelize(item.priority),
      summary: `Lifecycle robustness ${formatPercent(item.lifecycle_robustness)}.`,
      assessment: `Recommended strategy: ${labelize(item.strategy)}.`,
      strategy: item.suggested_response,
      quotes: item.evidence_to_cite?.length ? item.evidence_to_cite : [item.claim_text],
      draft: item.suggested_response,
      scores: item.scores,
      evidence_chain: item.evidence_chain
    }))
  };
}

function buildAnalysisFromAuditResult(auditResult, demoConfig = {}) {
  const allAudits = Array.isArray(auditResult.audits) ? auditResult.audits : [];
  const matchingAudits = demoConfig.paperId
    ? allAudits.filter((audit) => audit.paper_id === demoConfig.paperId)
    : allAudits;
  const audits = matchingAudits.length ? matchingAudits : allAudits;
  const paperIds = unique(audits.map((audit) => audit.paper_id).filter(Boolean));
  const singlePaper = paperIds.length <= 1;
  const selectedPaperTitle =
    demoConfig.paperTitle || audits.find((audit) => audit.paper_title)?.paper_title || "Audit demo";
  const paperIndexById = new Map(paperIds.map((paperId, index) => [paperId, index + 1]));
  const reviewIndexByPaper = new Map();

  const reviewers = audits.map((audit) => {
    const paperIndex = paperIndexById.get(audit.paper_id) || 1;
    const nextReviewIndex = (reviewIndexByPaper.get(audit.paper_id) || 0) + 1;
    reviewIndexByPaper.set(audit.paper_id, nextReviewIndex);
    const claims = Array.isArray(audit.claims) ? audit.claims : [];
    const stanceBreakdown = getStanceBreakdown(claims);
    const dominantAuditStance = getDominantStance(stanceBreakdown);
    const priorityClaims = claims.filter((claim) => guidancePriority(claim) === "high");
    const rating = numberOrNull(audit.rating_normalized);
    const confidence = numberOrNull(audit.reviewer_confidence_normalized);
    const qualityScore = Math.round(numberOrNull(audit.rqs_score) ?? 0);
    const highPriorityCount = priorityClaims.length;

    return {
      id: singlePaper ? `R${nextReviewIndex}` : `P${paperIndex}-R${nextReviewIndex}`,
      score: formatMetric(rating),
      confidence: formatMetric(confidence),
      qualityScore,
      stance: reviewerSentiment(rating),
      potential: highPriorityCount >= 2 ? "High" : highPriorityCount === 1 ? "Medium" : "Low",
      headline: audit.summary || "Second Opinion audit completed for this review.",
      auditSummary: singlePaper
        ? `${audit.decision || "Decision unknown"}. ${issueFlagSummary(audit.issue_flags)}`
        : `${audit.paper_title || "Untitled paper"} · ${audit.decision || "Decision unknown"}. ${issueFlagSummary(audit.issue_flags)}`,
      dominantAuditStance,
      stanceSummary: `Second Opinion stance distribution across ${claims.length} extracted reviewer points.`,
      stanceBreakdown,
      dimensions: mapAuditDimensions(audit.dimensions),
      claims: claims.map((claim, claimIndex) => ({
        ...claim,
        claimIndex: claimIndex + 1,
        guidancePriority: guidancePriority(claim),
        normalizedStance: normalizeStance(claim.stance)
      })),
      response: bestReviewerGuidance(claims)
    };
  });

  const allClaims = audits.flatMap((audit, auditIndex) =>
    (audit.claims || []).map((claim) => ({ audit, claim, reviewer: reviewers[auditIndex] }))
  );
  const highPriorityClaims = allClaims.filter(({ claim }) => guidancePriority(claim) === "high");
  const avgRqs = average(audits.map((audit) => audit.rqs_score));
  const avgRating = average(audits.map((audit) => audit.rating_normalized));
  const avgConfidence = average(audits.map((audit) => audit.reviewer_confidence_normalized));
  const lowestReviewer = reviewers.reduce((lowest, reviewer) => {
    if (!lowest || reviewer.qualityScore < lowest.qualityScore) {
      return reviewer;
    }
    return lowest;
  }, null);

  return {
    paperTitle: selectedPaperTitle,
    venue: "ICLR",
    year: "2024",
    metrics: [
      [formatMetric(avgRating), "Avg score"],
      [formatMetric(avgConfidence), "Avg confidence"],
      [formatMetric(avgRqs), "Avg SO score"],
      [
        String(singlePaper ? audits.length : auditResult.paper_count || paperIds.length || 0),
        singlePaper ? "Reviews" : "Papers"
      ],
      [String(highPriorityClaims.length), "High priority"]
    ],
    overview: {
      situation: singlePaper
        ? `${audits.length} reviews and ${allClaims.length} reviewer points audited for this ICLR 2024 paper.`
        : `${auditResult.paper_count || paperIds.length || 0} papers, ${auditResult.audit_count || audits.length} reviews, and ${allClaims.length} reviewer points audited from the ICLR 2024 demo packet.`,
      leverage: lowestReviewer
        ? `${lowestReviewer.id} has the lowest Second Opinion review-quality score (${lowestReviewer.qualityScore}) and should be inspected first.`
        : "No reviewer audit is available.",
      strategy: "Start with high-priority rebuttal guidance, then use stance colors to separate valid reviewer points from weakly grounded or contradicted claims."
    },
    reviewers,
    priorities: buildPriorities(highPriorityClaims),
    issues: buildIssues(allClaims)
  };
}

function buildPriorities(highPriorityClaims) {
  const items = [];
  const seen = new Set();
  for (const { claim, reviewer } of highPriorityClaims) {
    const title = truncate(claim.claim_text || "High-priority reviewer point", 84);
    if (seen.has(title)) {
      continue;
    }
    seen.add(title);
    const guidance = claim.rebuttal_guidance || {};
    items.push([
      title,
      `${reviewer.id}: ${truncate(guidance.suggested_response || "Use the retrieved evidence to answer this point directly.", 140)}`
    ]);
    if (items.length >= 5) {
      break;
    }
  }
  if (items.length) {
    return items;
  }
  return [["No high-priority rebuttal items", "The loaded demo did not expose high-priority guidance."]];
}

function buildIssues(allClaims) {
  const sorted = [...allClaims].sort((left, right) => {
    const priorityDelta = priorityRank(guidancePriority(right.claim)) - priorityRank(guidancePriority(left.claim));
    if (priorityDelta) {
      return priorityDelta;
    }
    return importanceRank(right.claim.importance) - importanceRank(left.claim.importance);
  });
  const issues = sorted.slice(0, 8).map(({ audit, claim, reviewer }) => {
    const guidance = claim.rebuttal_guidance || {};
    return {
      title: truncate(claim.claim_text || "Reviewer point", 82),
      raisedBy: [reviewer.id],
      severity: importanceRank(claim.importance) >= 2 ? "High" : "Medium",
      fixability: guidancePriority(claim) === "high" ? "Medium" : "High",
      priority: capitalize(guidancePriority(claim)),
      summary: claim.extraction_reason || claim.source_sentence || audit.summary || "Reviewer point extracted from the audit result.",
      assessment: claim.second_opinion_take || claim.reasoning_summary || "Second Opinion assessment is available in the full report.",
      strategy: guidance.suggested_response || "Answer this point with the strongest available evidence and avoid overclaiming.",
      quotes: [claim.source_sentence || claim.claim_text || "No source quote recorded."],
      draft: guidance.suggested_response || "Acknowledge the point, cite the relevant manuscript evidence, and state the concrete revision or clarification.",
      scores: claim.scores,
      evidence_chain: claim.evidence_chain
    };
  });
  return issues.length ? issues : analysis.issues;
}

function mapAuditDimensions(dimensions) {
  const labels = {
    claim_accuracy_and_evidence: "Claim accuracy",
    technical_substance: "Technical substance",
    specificity: "Specificity",
    constructiveness: "Constructiveness",
    balance_and_fairness: "Balance and fairness",
    professional_tone: "Professional tone",
    score_text_consistency: "Score consistency",
    venue_guideline_compliance: "Venue compliance"
  };
  const entries = Object.entries(dimensions || {});
  if (!entries.length) {
    return { "Review quality": 0 };
  }
  return Object.fromEntries(
    entries.map(([key, value]) => {
      const numeric = numberOrNull(value) ?? 0;
      const normalized = numeric <= 5 ? Math.round((numeric / 4) * 100) : Math.round(numeric);
      return [labels[key] || key.replaceAll("_", " "), Math.max(0, Math.min(100, normalized))];
    })
  );
}

function getStanceBreakdown(claims) {
  const breakdown = Object.fromEntries(stanceScale.map(([key]) => [key, 0]));
  for (const claim of claims) {
    const stance = normalizeStance(claim.stance);
    breakdown[stance] += 1;
  }
  return breakdown;
}

function getDominantStance(breakdown) {
  return stanceScale.reduce((best, [key]) => {
    if ((breakdown[key] || 0) > (breakdown[best] || 0)) {
      return key;
    }
    return best;
  }, "mixed");
}

function normalizeStance(value) {
  const normalized = String(value || "mixed").trim().toLowerCase().replaceAll("-", "_");
  if (stanceScale.some(([key]) => key === normalized)) {
    return normalized;
  }
  return "mixed";
}

function bestReviewerGuidance(claims) {
  const claim =
    claims.find((item) => guidancePriority(item) === "high" && item.rebuttal_guidance?.suggested_response) ||
    claims.find((item) => item.rebuttal_guidance?.suggested_response);
  return claim?.rebuttal_guidance?.suggested_response || "Use the issue workspace to inspect claim-level rebuttal guidance.";
}

function guidancePriority(claim) {
  const priority = String(claim?.rebuttal_guidance?.priority || "medium").trim().toLowerCase();
  return ["must", "high", "medium", "low"].includes(priority) ? priority : "medium";
}

function priorityRank(priority) {
  return { low: 1, medium: 2, high: 3, must: 4 }[priority] || 2;
}

function importanceRank(importance) {
  const value = String(importance || "").toLowerCase();
  if (value === "major") {
    return 3;
  }
  if (value === "medium" || value === "minor") {
    return 2;
  }
  return 1;
}

function reviewerSentiment(rating) {
  if (rating === null) {
    return "mixed";
  }
  if (rating >= 6) {
    return "supportive";
  }
  if (rating >= 4) {
    return "mixed";
  }
  return "skeptical";
}

function issueFlagSummary(flags) {
  if (!Array.isArray(flags) || !flags.length) {
    return "No recurring issue flags.";
  }
  return `${flags.length} issue flags, including ${flags.slice(0, 2).map((flag) => flag.replaceAll("-", " ")).join(" and ")}.`;
}

function unique(values) {
  return [...new Set(values)];
}

function average(values) {
  const numericValues = values.map(numberOrNull).filter((value) => value !== null);
  if (!numericValues.length) {
    return null;
  }
  return numericValues.reduce((sum, value) => sum + value, 0) / numericValues.length;
}

function numberOrNull(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatMetric(value) {
  const numeric = numberOrNull(value);
  if (numeric === null) {
    return "n/a";
  }
  return Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(1);
}

function formatPercent(value) {
  const numeric = numberOrNull(value);
  if (numeric === null) {
    return "n/a";
  }
  return `${Math.round(numeric * 100)}%`;
}

function truncate(value, maxLength) {
  const text = String(value || "").trim();
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 3).trim()}...`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
