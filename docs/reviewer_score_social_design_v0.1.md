# SecondOpinion Reviewer Scorecard Social Design v0.1

Date: 2026-06-17

## 1. Project Background

SecondOpinion is an author-facing tool for reviewing peer-review comments. The core product idea is:

> Score reviewer comments first. Triage and rebuttal planning come after scoring.

The current backend already supports a six-dimension reviewer-comment scoring system:

1. Specificity
2. Substantiation
3. Actionability
4. Consensus / conflict
5. Rebuttal robustness
6. Professionalism

The latest implementation also connects external peer-review research datasets as scoring memory. Instead of fine-tuning a model, the system normalizes external datasets, retrieves similar examples, and combines the retrieval prior with an LLM score.

The current frontend still exposes too much internal process: analysis pipeline, live notes, implementation status, mapped labels, and dataset names. These are useful for us, but not for normal users. The next frontend version should become a product experience, not a technical dashboard.

## 2. Product Direction

The frontend should only show the user-facing result:

- Select or search a conference.
- Select or search a paper.
- Show the total reviewer-quality score.
- Show reviewer cards with total scores.
- Click a reviewer to see the detailed six-dimension score.
- Add a social layer: likes, dislikes, red list, and black list.

Internal terms should not appear in the public UI:

- `mapped`
- `implemented`
- `retrieval prior`
- `guardrail`
- `benchmark`
- external dataset names such as ReAct, SubstanReview, DISAPERE
- analysis pipeline stages
- live technical notes

These can remain available in an internal debug/admin view.

## 3. User Flow

```text
Open SecondOpinion
  -> Select conference
  -> Search or paste paper URL
  -> Analyze
  -> See paper-level reviewer quality
  -> See reviewer cards and leaderboards
  -> Like or dislike reviewer
  -> Click reviewer for detailed scoring
```

Main page:

```text
[ Conference ] [ Search paper title / OpenReview URL / Paper ID ] [ Analyze ]
```

Result page:

```text
Paper Reviewer Quality
82 / 100

Best reviewer: Baseline Hawk
Lowest reviewer: Vague Thunder

[Red List]                   [Black List]
1. Baseline Hawk   94        1. Vague Thunder   28
2. Clarity Wizard  91        2. Lazy Rejector   33
3. Polite Skeptic  89        3. Scope Shifter   37

Reviewers
[pixel] Baseline Hawk   91   Like 128   Dislike 9
[pixel] Polite Skeptic  84   Like 87    Dislike 12
[pixel] Vague Thunder   38   Like 10    Dislike 96
```

Reviewer detail:

```text
[pixel avatar] Baseline Hawk
Total Score: 91

Like / Dislike

Detailed Score
- Specificity: 92
- Evidence: 88
- Actionability: 95
- Agreement with other reviewers: 74
- Still matters after rebuttal: 81
- Tone: 96

Representative comment
"Please compare against a standard retrieval baseline and report runtime."
```

## 4. Social Layer

### 4.1 Red List / Black List

The red list shows the highest-rated reviewers. The black list shows the lowest-rated reviewers.

Recommended public labels:

- Red List: `Most Helpful Reviewers`
- Black List: `Least Helpful Reviewers`

The product can still use the stronger red/black visual language, but the text should avoid sounding like a personal attack. The system is rating review comments, not exposing real identities.

### 4.2 Likes And Dislikes

Each reviewer card has:

- Like
- Dislike

Likes and dislikes influence leaderboard position, but should not fully override system scoring.

Suggested ranking formula:

```text
public_rank_score =
  70% system_score
+ 20% social_vote_score
+ 10% engagement_score
```

Where:

```text
social_vote_score = normalized(upvotes - downvotes)
engagement_score = log(upvotes + downvotes + 1)
```

This keeps the ranking social without making it easy to game.

### 4.3 Reviewer Nicknames

The backend keeps the stable internal identity:

```text
paper_id + reviewer_id
```

The frontend shows a generated nickname based on the reviewer's comments.

Examples:

- Baseline Hawk
- Clarity Wizard
- Polite Skeptic
- Theory Sentinel
- Ablation Seeker
- Vague Thunder
- Scope Shifter

Nickname generation can use:

- main concern type: baseline, theory, experiment, clarity, novelty
- tone: polite, harsh, skeptical, constructive
- comment quality: specific, vague, evidence-heavy, action-oriented

The nickname should be deterministic for the same paper/reviewer pair unless the underlying comments change.

### 4.4 Pixel Avatar

Each reviewer gets a deterministic pixel-style avatar generated from:

```text
hash(paper_id + reviewer_id + nickname)
```

Avatar style should be simple and playful:

- small pixel head/icon
- limited color palette
- no realistic face
- no real identity implication

This makes the social layer feel memorable while protecting reviewer identity.

## 5. Scoring Implementation

The backend scoring path remains technical, but the frontend only shows the final output.

Current scoring pipeline:

```text
External datasets
  -> normalized scoring records
  -> scoring memory
  -> retrieval examples
  -> LLM dimension scores
  -> hybrid final scores
  -> reviewer aggregate score
  -> public reviewer card
```

Current no-fine-tuning implementation:

- Normalize external datasets into a shared JSONL schema.
- Build scoring memory from normalized records.
- Retrieve relevant examples per scoring dimension.
- Compute:

```text
final_score = 0.6 * llm_score + 0.4 * memory_prior
```

- Aggregate claim-level scores into reviewer-level scores.
- Run benchmark guardrails before changing scoring behavior.

The frontend should receive a clean public object, not raw technical details.

Suggested frontend-facing reviewer object:

```json
{
  "reviewer_key": "paper123:reviewer2",
  "nickname": "Baseline Hawk",
  "avatar_seed": "9f21c",
  "total_score": 91,
  "upvotes": 128,
  "downvotes": 9,
  "rank_score": 93,
  "summary": "Specific and actionable experimental feedback.",
  "dimensions": {
    "specificity": 92,
    "evidence": 88,
    "actionability": 95,
    "agreement": 74,
    "rebuttal_robustness": 81,
    "tone": 96
  },
  "representative_comment": "Please compare against a standard retrieval baseline and report runtime."
}
```

The private backend can still store:

- retrieved examples
- dataset labels
- benchmark status
- guardrail reports
- raw reviewer ID
- paper/reviewer mapping

## 6. Frontend Design

The next frontend should have three main sections.

### 6.1 Search Header

Purpose: start the workflow.

```text
SecondOpinion

[ICLR v] [Search paper / paste OpenReview URL] [Analyze]
```

No pipeline cards. No live notes.

### 6.2 Paper Summary

Purpose: show the main answer.

```text
Overall Reviewer Quality
82 / 100

Best reviewer: Baseline Hawk
Lowest reviewer: Vague Thunder
```

### 6.3 Reviewer Reputation Board

Purpose: make the product social and scannable.

```text
[Red List]     [Black List]
[Reviewer Cards]
```

Each reviewer card:

```text
[pixel avatar] Nickname
Total score
Short summary
Like / Dislike
```

Click opens detail.

## 7. Safety And Product Boundaries

This product should not claim:

- reviewer identity discovery
- objective truth about a reviewer as a person
- acceptance prediction
- replacement of expert judgment

The system should say it scores reviewer comments, not reviewers as humans.

Recommended wording:

> This score reflects the usefulness of the review comments for author response and revision planning.

Avoid wording like:

> This reviewer is bad.

For public or shareable leaderboards, reviewer identity should remain pseudonymous and paper-scoped unless the data source already makes identity public and the product has an explicit policy for it.

## 8. Implementation Milestones

### Milestone 1: Product UI Simplification

- Remove public analysis pipeline.
- Remove live notes.
- Remove technical status labels.
- Make the default result page show only total paper/reviewer scores.

### Milestone 2: Public Reviewer Model

- Add nickname generation.
- Add pixel avatar seed.
- Add public reviewer score object.
- Map six technical dimensions into user-friendly labels.

### Milestone 3: Social Feedback

- Add Like / Dislike controls.
- Store vote counts.
- Prevent repeated local votes in MVP.
- Later add account/session-based vote controls.

### Milestone 4: Leaderboards

- Add red list and black list.
- Use combined system/social ranking.
- Support Top 10 display.

### Milestone 5: Debug/Admin Separation

- Keep scoring memory, benchmark, guardrail, and pipeline views behind an internal debug mode.
- Suggested access pattern:

```text
?debug=1
```

## 9. Open Review Questions

1. Should the public UI say `Black List`, or should it use softer wording like `Least Helpful Reviewers`?
2. Should likes/dislikes be anonymous in MVP, or tied to user sessions?
3. Should reviewer nicknames be playful, neutral, or more academic?
4. Should rankings be per paper, per conference, or global across all analyzed papers?
5. Should the six detailed dimensions be visible by default, or only after expanding a reviewer card?

## 10. Current Implementation Status

Already implemented:

- Six-dimension scoring schema.
- External scoring memory path.
- Adapters for ContraSciView, ReAct, SubstanReview, DISAPERE, and RbtAct.
- Hybrid scoring output.
- Benchmark suite and guardrail report.
- Demo JSON with backend-shaped hybrid scores.

Not yet implemented:

- Product-level simplified UI.
- Red list / black list frontend.
- Like / dislike interaction.
- Nickname generation.
- Pixel avatars.
- Vote persistence.

The next engineering step is to replace the current frontend pipeline view with the simplified reviewer reputation board.
