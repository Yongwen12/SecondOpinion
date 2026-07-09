# SecondOpinion Public Homepage Design v0.1

Date: 2026-06-28

This document defines the next public homepage direction for SecondOpinion after the first shareable production release.

The main change is conceptual:

> The homepage should behave like a paper search and community signal console, not like an article-style landing page.

## 1. Context

The current public version proves that the product can be shared:

- frontend connects to the production API by default;
- home data, search, scorecard, and reviewer vote APIs are working;
- public scorecards do not expose internal scoring fields;
- production scoring jobs are backed by Postgres and workers.

The main issue is now product experience, not infrastructure.

Current UI problems:

1. Different information types do not have enough visual separation.
2. The main browsing area, red list, and black list have weak hierarchy.
3. Red list and black list read like sections appended below an article, but they should act as side signals.
4. Interactions are too linear and static for a community or information-query entry point.

## 2. Design Goal

The homepage should support three user jobs:

1. **Search a known paper**
   Search by title, DOI-like identifier, OpenReview/forum ID, or arXiv-like identifier when available.

2. **Browse recently scored papers**
   See what has recently been scored for the selected conference/year.

3. **Use community signals**
   Quickly notice helpful reviewers, risky reviewers, disputed papers, and recent voting activity.

The default homepage should answer:

```text
What can I search?
What is the community currently scoring?
Which signals should I pay attention to?
What can I open or vote on next?
```

## 3. Product References

The following products are useful references, not visual templates to copy.

| Reference | Useful Pattern |
| --- | --- |
| Semantic Scholar | Search-first scholarly entry point. |
| PubMed | Search plus structured discovery and filters. |
| Hugging Face Papers | Paper community feed with time-based trending. |
| Product Hunt | Main launch feed plus side/community discovery signals. |
| Hacker News | Dense ranked list with lightweight social metadata. |
| Stack Overflow Questions | Fixed metric columns for votes, answers, views, and status. |
| PubPeer | Precise paper identity search and discussion-oriented scholarly context. |
| Letterboxd | Object catalog plus ratings, lists, reviews, and community activity. |

Implication for SecondOpinion:

> Keep search and the paper list as the primary path. Move red list, black list, votes, and disputed signals into a side rail or mobile tab layer.

## 4. Information Architecture

### 4.1 Top-Level Regions

Desktop:

```text
+--------------------------------------------------------------------------------+
| Header: brand, global search, selected conference/year, API/data status          |
+--------------------------------------------------------------------------------+
| Control bar: year chips, view tabs, sort/filter controls                         |
+---------------------------------------------------------+----------------------+
| Main paper browser                                      | Community signal rail |
| - recently scored papers                                | - red list            |
| - search results                                        | - black list          |
| - selected year/list view                               | - recent votes        |
| - expanded scorecard preview                            | - disputed papers     |
+---------------------------------------------------------+----------------------+
```

Mobile:

```text
+------------------------------------------------+
| Brand + status                                  |
| Search                                          |
| Year chips                                      |
| Recent | Red | Black | Debate | Votes           |
| Main list or selected signal list               |
+------------------------------------------------+
```

### 4.2 Default State

Default desktop state:

- header search is visible and ready;
- selected conference defaults to `ICLR`;
- selected year defaults to the newest year with enough scored papers;
- main region shows `Recent scored papers`;
- side rail shows red list, black list, recent votes, and most disputed signals;
- no large marketing hero is shown.

Default mobile state:

- search stays near the top;
- signal rail becomes segmented tabs;
- `Recent` is selected by default.

## 5. Content Hierarchy

### 5.1 Paper List Item

Each paper row/card should have a stable comparison structure:

```text
[score] [title]
        [venue/year] · [reviewers] · [comments] · [updated]
        [signal label] [confidence/dispute label]
        [+ top positive signal] [- top risk signal]
        [Scorecard] [Vote] [Evidence/OpenReview]
```

Priority order:

1. paper score or reviewer-quality signal;
2. paper title;
3. year, venue, reviewer count, comment count;
4. confidence/risk/dispute badges;
5. top positive and negative reasons;
6. actions.

Example:

```text
82  B+   Scaling Laws for Neural Language Models
         ICLR 2020 · 4 reviewers · 31 scored comments · updated 4h ago
         High confidence · Low dispute
         + specific reviewer evidence   - limited baseline discussion
         Scorecard · Vote · OpenReview
```

### 5.2 Side Rail Items

Side rail items should be deliberately smaller than main list items.

Red list row:

```text
#1  94  Baseline Hawk
        Paper title · 18 useful · 2 disputed
```

Black list row:

```text
#1  28  Vague Thunder
        Paper title · 3 useful · 21 disputed
```

Side rail rows should not show full explanations. Their job is to route the user back into the main content or a scorecard preview.

### 5.3 Detail Preview

Clicking a paper should open a lightweight preview before full navigation.

Preferred desktop behavior:

- open an inline expansion under the selected paper, or a right-side drawer replacing the signal rail;
- show paper summary, reviewer score distribution, top reviewers, bottom reviewers, and primary actions.

Preferred mobile behavior:

- open an expandable panel below the selected paper;
- full scorecard opens as a separate focused view.

## 6. Visual Hierarchy

### 6.1 Page Density

The homepage should feel like a usable information console:

- no oversized hero;
- no large explanatory copy blocks;
- compact top navigation;
- dense but readable paper list;
- side rail with lower visual weight.

### 6.2 Layout Weight

Desktop target:

```text
Main browser: 68-72% width
Signal rail: 28-32% width
```

The main browser owns the user's attention. The signal rail provides context and shortcuts.

### 6.3 Score Treatment

Scores should use fixed-width treatment so rows are comparable.

Recommended score display:

```text
82
B+
```

or:

```text
82 Review Signal
```

Avoid burying scores inside prose. They should be visible at the left edge or as a consistent leading badge.

### 6.4 Color Rules

Use a neutral base with semantic accents.

Recommended semantics:

- positive/helpful: green or blue-green accent;
- risk/disputed: amber or muted red accent;
- neutral metadata: gray;
- selected state: dark text plus subtle filled background;
- API/data status: small dot plus short label.

Avoid:

- full-page red/green opposition;
- one-note beige or one-note blue palette;
- decorative gradients as the primary structure;
- large cards that all compete at the same weight.

### 6.5 Typography

Recommended hierarchy:

```text
Page brand: compact, persistent
Section title: small but strong
Paper title: highest weight inside list
Score: numeric, fixed-width, high contrast
Metadata: smaller muted text
Badges: short, semantic, scan-friendly
Actions: compact buttons or links
```

## 7. Interaction Model

### 7.1 Search

Search should be the primary action.

Behavior:

1. User types title, paper ID, OpenReview ID, DOI-like text, or arXiv-like text.
2. Results appear in the main browser.
3. If a result has a scorecard, show score and `Scorecard`.
4. If indexed but not scored, show `Score not ready` and `Queue scoring`.
5. If not indexed, show a precise empty state and current coverage.

Current compatible API:

```text
GET /api/conferences/{conference_id}/papers?query=...&year=...&limit=...
GET /api/papers/{paper_id}/scorecard
POST /api/papers/{paper_id}/scoring-jobs
```

### 7.2 Browse Controls

Primary tabs:

```text
Recent scored | Highest score | Lowest score | Most disputed | Needs votes
```

Initial implementation can support only `Recent scored` from the existing `/api/home` response, while rendering disabled or staged controls for later views only if they do not mislead users.

Year chips:

```text
2026 | 2025 | 2024 | 2023 | 2022
```

Conference selector:

```text
ICLR initially; structure should allow more conferences later.
```

Current compatible API:

```text
GET /api/home?conference=ICLR&year=2025&limit=12
GET /api/leaderboards?conference=ICLR&year=2025&limit=10
GET /api/conferences
```

### 7.3 Side Rail

Desktop side rail sections:

1. Red list
2. Black list
3. Recent votes
4. Most disputed papers

For v0.1 implementation, red list and black list can ship first because the API already supports them. Recent votes and most disputed can appear only when backed by real data.

Click behavior:

- clicking a side rail reviewer opens the corresponding paper and focuses that reviewer in the scorecard preview;
- clicking a side rail paper changes the main browser context or opens the paper preview;
- side rail should never navigate the user away without a visible state transition.

### 7.4 Scorecard Preview

Paper preview should show:

- paper title, year, venue;
- overall score and signal label;
- top red-list reviewer for this paper;
- top black-list reviewer for this paper;
- reviewer count and comment count;
- `Open full scorecard`;
- `Vote` entry if reviewer-level vote is available.

Reviewer preview should show:

- nickname/avatar;
- reviewer score;
- useful/disputed vote counts;
- six dimension scores, if already public;
- one representative comment or summary;
- vote buttons.

### 7.5 Voting

Voting should feel immediate.

Behavior:

1. User clicks useful/disputed.
2. UI updates optimistically.
3. API sync runs.
4. If API fails, revert or show a small non-blocking error.

Current compatible API:

```text
POST /api/papers/{paper_id}/reviewers/{reviewer_key}/votes
```

Public labels:

```text
Useful
Disputed
```

Avoid making the public UI sound like it is attacking real reviewers.

## 8. Required States

### 8.1 Loading

Use row skeletons or compact placeholders:

```text
Loading recent scored papers...
Loading reviewer signals...
```

Do not show demo/fallback language in production.

### 8.2 Empty

Empty state examples:

```text
No scored papers for ICLR 2026 yet.
Try ICLR 2025 or search an indexed paper.
```

```text
No leaderboard yet.
Reviewer lists appear after scorecards are available for this year.
```

### 8.3 Error

Error state:

```text
SecondOpinion API is unavailable.
Search and live scorecards need the production API.
```

Keep this short and operational. Do not expose stack traces or internal pipeline names.

### 8.4 Scoring Job

When a paper is indexed but not scored:

```text
Scorecard not ready
Queue scoring
```

After queueing:

```text
Scoring queued
```

If possible, poll:

```text
GET /api/scoring-jobs/{job_id}
```

## 9. Implementation Phases

### Phase 1: Layout And Hierarchy

Ship the structural redesign with existing data:

- compact header and search;
- year chips;
- main recent scored paper list;
- right side red/black rail on desktop;
- mobile tabs for red/black;
- stronger score/title/metadata hierarchy;
- production-safe loading, empty, and error states.

No new backend endpoint is required for this phase.

### Phase 2: Preview Interactions

Add interaction depth:

- paper row expansion or drawer preview;
- focused reviewer preview from red/black rail;
- smoother vote feedback;
- scorecard preview before full scorecard view.

May use existing scorecard endpoint.

### Phase 3: Rich Community Signals

Add new signal sections when backed by data:

- recent votes;
- most disputed papers;
- needs votes;
- highest/lowest paper lists;
- daily/weekly/monthly activity views.

This may require new aggregated API fields.

## 10. Acceptance Criteria

The redesigned homepage is acceptable when:

1. A first-time user immediately sees search, recent scored papers, and community signals in the first viewport.
2. Red list and black list are visually side signals on desktop, not article sections appended below the main content.
3. Paper rows are comparable by score, title, metadata, and social signal without opening every scorecard.
4. Mobile keeps the same information architecture through tabs instead of a squeezed side rail.
5. Loading, empty, API error, and scorecard-not-ready states are explicitly designed.
6. Public UI does not expose internal fields such as `hybrid_scores`, `memory_prior`, `mapped_score`, retrieved examples, scorer internals, or debug pipeline labels.
7. The page can be implemented with the current production API for Phase 1.

## 11. Open Questions

1. Should the public label remain `Red List` / `Black List`, or should the UI show softer labels such as `Most Helpful` / `Needs Scrutiny` while preserving internal terminology?
2. Should the homepage rank reviewers globally within a year, or should paper-level lists be emphasized more heavily?
3. Should scores be shown as raw `0-100`, letter grades, or both?
4. Should the default year be fixed, newest imported year, or newest year with a minimum number of scored papers?

## 12. Immediate Design Decision

For the next implementation pass, use this default:

```text
Header:
  SecondOpinion + search + API/data status

Controls:
  ICLR + year chips + Recent scored selected

Main:
  Recent scored papers, fixed score column, title-first rows

Side rail:
  Red list and black list, compact reviewer rows

Mobile:
  Search + year chips + Recent/Red/Black tabs
```

This keeps the v0.1 redesign achievable with existing production data while correcting the core hierarchy problem.
