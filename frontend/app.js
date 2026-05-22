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
        artifact: "4 reviews, 4 scores",
        note: "Found reviewer ratings, confidences, and full review text."
      }
    ]
  },
  {
    name: "Review analysis",
    steps: [
      {
        title: "Classify stance",
        artifact: "1 supportive, 2 mixed, 1 skeptical",
        note: "Reviewer 2 is the highest leverage reviewer because the concerns are concrete and fixable."
      },
      {
        title: "Extract claims",
        artifact: "18 reviewer claims",
        note: "Separated actionable criticisms from summaries and praise."
      },
      {
        title: "Cluster issues",
        artifact: "5 issue clusters",
        note: "Baseline and evaluation concerns overlap across multiple reviewers."
      },
      {
        title: "Score fixability",
        artifact: "3 high-priority responses",
        note: "Novelty framing is risky, but likely addressable with clearer positioning."
      }
    ]
  },
  {
    name: "Rebuttal",
    steps: [
      {
        title: "Prioritize responses",
        artifact: "R2 and R3 first",
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

const analysis = {
  paperTitle: "Second Opinion Demo Submission",
  venue: "ICLR",
  year: "2026",
  metrics: [
    ["5.25", "Avg score"],
    ["3.75", "Avg confidence"],
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
      stance: "supportive",
      potential: "Medium",
      headline: "Mostly positive, asks for sharper novelty framing.",
      response: "Thank R1 for recognizing the contribution, then make the novelty claim more concrete and cite the exact section where the method differs."
    },
    {
      id: "R2",
      score: 4,
      confidence: 3,
      stance: "skeptical",
      potential: "High",
      headline: "Concerned about missing baselines and experimental breadth.",
      response: "Prioritize R2. Acknowledge the baseline concern, add a compact comparison table, and state which additional experiment can be completed."
    },
    {
      id: "R3",
      score: 5,
      confidence: 4,
      stance: "mixed",
      potential: "Medium",
      headline: "Likes the idea but doubts whether the evaluation proves the central claim.",
      response: "Tie the main claim to the strongest existing results. Avoid overclaiming; define the scope more tightly."
    },
    {
      id: "R4",
      score: 6,
      confidence: 4,
      stance: "supportive",
      potential: "Low",
      headline: "Supportive review with presentation-level requests.",
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

function showWorkspace() {
  pipelineTitleEl.textContent = "Analysis complete";
  workspaceSection.classList.remove("hidden");
  renderWorkspace();
  workspaceSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderWorkspace() {
  paperTitleEl.textContent = `${analysis.venue} ${analysis.year} · ${analysis.paperTitle}`;
  paperMetricsEl.innerHTML = analysis.metrics
    .map(([value, label]) => `<div class="metric-chip"><b>${escapeHtml(value)}</b><span>${escapeHtml(label)}</span></div>`)
    .join("");
  reviewerRailEl.innerHTML = analysis.reviewers
    .map(
      (reviewer) => `
        <div class="reviewer-mini">
          <strong>${reviewer.id}<span>${reviewer.score} / ${reviewer.confidence}</span></strong>
          <span>${escapeHtml(reviewer.headline)}</span>
        </div>
      `
    )
    .join("");
  renderTab();
}

function renderTab() {
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
    <div class="panel-grid">
      <article class="surface">
        <div class="surface-head">
          <h3>Situation</h3>
          <p>${escapeHtml(analysis.overview.situation)}</p>
        </div>
        <div class="surface-body">
          <ul class="status-list">
            <li><b>Highest leverage reviewer</b><span>${escapeHtml(analysis.overview.leverage)}</span></li>
            <li><b>Response strategy</b><span>${escapeHtml(analysis.overview.strategy)}</span></li>
          </ul>
        </div>
      </article>

      <article class="surface">
        <div class="surface-head">
          <h3>Score landscape</h3>
          <p>Current submission is highlighted against a mock ICLR distribution.</p>
        </div>
        <div class="surface-body">
          <div class="mini-chart">
            ${analysis.overview.scoreDistribution
              .map(
                ([label, height]) => `
                  <div class="bar ${label === "5.5" ? "target" : ""}">
                    <span style="height:${height}%"></span>
                    <label>${label}</label>
                  </div>
                `
              )
              .join("")}
          </div>
        </div>
      </article>
    </div>

    <article class="surface" style="margin-top:18px">
      <div class="surface-head">
        <h3>Response priorities</h3>
      </div>
      <div class="surface-body">
        <ul class="priority-list">
          ${analysis.priorities
            .map(([title, note]) => `<li><b>${escapeHtml(title)}</b><span>${escapeHtml(note)}</span></li>`)
            .join("")}
        </ul>
      </div>
    </article>
  `;
}

function renderReviewers() {
  tabPanelEl.innerHTML = `
    <div class="review-list">
      ${analysis.reviewers
        .map(
          (reviewer) => `
            <article class="review-card">
              <div class="review-card-top">
                <div>
                  <h3>${reviewer.id}</h3>
                  <div class="review-meta">
                    <span class="badge">Score ${reviewer.score}</span>
                    <span class="badge">Confidence ${reviewer.confidence}</span>
                    <span class="badge stance ${reviewer.stance}">${capitalize(reviewer.stance)}</span>
                    <span class="badge ${reviewer.potential.toLowerCase()}">${reviewer.potential} potential</span>
                  </div>
                </div>
              </div>
              <p>${escapeHtml(reviewer.headline)}</p>
              <div class="draft-box">
                <p>${escapeHtml(reviewer.response)}</p>
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderRebuttal() {
  const issue = analysis.issues[activeIssue];
  tabPanelEl.innerHTML = `
    <div class="issue-workspace">
      <div class="issue-list">
        ${analysis.issues
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

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
