# SecondOpinion Homepage v0.1 — Implementation Plan (Handoff Spec)

Date: 2026-06-28
Status: ready to implement
Audience: implementing agent (no prior conversation context assumed)

This plan corrects and operationalizes `Public Homepage Design v0.1`. It is grounded in the
**actual** production code, not the design doc's assumptions. Several design-doc statements assume
backend capabilities that do not exist; those are flagged and replaced below.

> **Apply edits by matching the quoted code, not by line number.** Line numbers are given for
> orientation only and will drift as you edit. Every change lists its file + function + exact
> current text to match.

---

## 0. Guiding principle: ship the *truth*, then ship the polish

The redesign's whole thesis is "community signals." Today the signal is partly **manufactured**:
reviewer up/down ("useful/disputed") counts are seeded from the score and shown as if they were
community votes. Fixing that is **P0** and blocks calling anything a "community signal." Visual
hierarchy (P1/P2) matters less than not lying about the data.

Priority order:

- **P0 — Signal truthfulness.** Stop displaying synthetic votes. Show real votes only.
- **P1 — Don't mislabel/over-promise.** Score semantics, search coverage copy, no unbacked badges.
- **P2 — Hierarchy + integrity.** Ranking honesty, nickname collisions, labels, visible error/sparse states, a11y.
- **P3 — Guardrails.** What to deliberately *not* build in v0.1 (and why), so the page stays honest.

---

## Layout & Visual Decisions (v0.1)

These resolve the 20 layout questions raised for this pass. Defaults match the original
`Public Homepage Design v0.1` doc (esp. §4.1, §5.2, §6.1–6.4, §12) and console conventions. Items
marked **[taste]** are reversible brand calls — a default is applied so implementation can start;
override in one line if you disagree. **One item (Q18, the scrutiny-list name) is worth an explicit
confirm.**

**Current → target structure.** The home today is a vertical stack (hero → search → year chips →
feed → mobile board tabs → `home-boards-grid` with two side-by-side cards). Target is a **two-column
console**: a full-width header (brand + compact search + year chips) above a left feed column and a
right signal rail. Implement the feed+rail band as a CSS grid on the `.community-home` content:
`grid-template-columns: minmax(0, 1fr) clamp(300px, 30%, 360px)`, header spanning both columns;
collapse to one column under ~900px where the mobile tabs take over. This is a real restructure of the
markup, not just CSS.

### Core layout (Q1–Q5)

1. **Two columns on desktop — yes.** Left `Recently scored papers` ≈ 70%, right signal rail ≈ 30%
   (design §6.2). Single full-width header above both.
2. **Rail = one container, two stacked sections** (not two side-by-side cards). `Most Helpful` on top,
   the scrutiny list below, inside one right-column container. Replaces the current side-by-side
   `home-boards-grid`. Keeps the rail reading as one peripheral unit.
3. **Sticky rail — yes.** `position: sticky; top: <header height>` with `max-height: calc(100vh - …)`
   and `overflow:auto` so long lists scroll internally while the feed scrolls the page.
4. **Show both boards on desktop** (stacked, top 5 each — slice to 5 in the frontend; API still
   returns 10). No desktop tab; tabs are a mobile-only pattern. Desktop has the width, and both
   signals should be glanceable at once (design §4.1).
   **⚠ Under review — the two-mirror-list pattern is contested.** Top-N vs bottom-N of one quality
   sort are the two ends of the *same* list (≈ one signal, not two), and they rank *pseudonyms* the
   visitor can't follow or act on — low information, low actionability. Pending decision before the
   rail is finalized: **Option A** keep only "Most Helpful"; **Option B** replace the second list with
   a *paper-level* axis (Most Disputed / Needs votes / highest-quality-reviewed papers) — papers are
   clickable and actionable (design Open Q2, which leans paper-level). Treat the second list as
   not-yet-final until this is chosen.
5. **Mobile — tabs.** Single column with a segmented control `Recent | Most Helpful | <scrutiny>`,
   `Recent` selected by default (design §4.2). Extend the existing `mobile-board-tabs` by adding a
   `Recent` tab. (Not collapse-below — tabs keep the column clean.)

### Information hierarchy (Q6–Q8)

6. **First-screen focus.** Search is the top **primary action** but compact (no hero); the
   `Recently scored papers` feed is the **visual center of gravity** directly below; rail to the
   right. All three visible in the first viewport (acceptance #1).
7. **Rail row primary = paper title** (your recommendation, adopted). Nickname is a secondary tag.
   This also defuses the "Vague Thunder" nickname collision (P2-B). Rail rows route the user back to
   the paper (design §5.2).
8. **Per-row score = numeric badge, not the full phrase.** Fixed-width numeric badge at the left edge
   (design §6.3) + a per-row signal label + a header-level "Review quality" caption + a
   `title="Reviewer quality score (0–100)"` tooltip. Do **not** stamp "Review quality score" on every
   row — too heavy. (See P1-A.)

### Visual weight (Q9–Q12)

9. **Rail = light lists, not cards.** Small rows, subtle separators, lower contrast than feed rows
   (design §5.2/§6.2). The feed owns attention; the rail is context.
10. **[taste] Semantic accent, not green/red blocks.** Design §6.4 explicitly says *avoid full-page
    red/green opposition*. Default: neutral rows with a small accent — teal/green dot or left-border
    for `Most Helpful`, amber/muted-red for the scrutiny list. Not full-card green vs red fills.
11. **[taste] Neutral console base.** Shift the warm cream base toward a neutral white / light-gray
    information-tool palette (design §6.1 "usable information console"); keep at most a subtle warm
    hint as accent. Override if brand wants to retain the warm tone.
12. **Shrink the search region — yes.** Compact header search; drop the landing/hero framing. The page
    should open as a console, not a marketing page (design §6.1).

### Interaction (Q13–Q16)

13. **Rail item click → open that paper's scorecard** (existing `openHomePaper` behavior), focusing
    the clicked reviewer when it is a reviewer row. Always a visible transition, never a silent jump
    (design §7.3). Locate-in-feed is rejected: the rail is leaderboard-scoped and the paper may not be
    in the visible feed.
14. **Paper row click → open the full scorecard** (existing resolved view). **No preview drawer this
    pass** — it is design Phase 2 and out of scope for a layout-only v0.1 (Q19/Q20). Defer.
15. **Year switch syncs the rail — yes** (your recommendation, adopted; already how
    `loadCommunityHome(year)` works — `/api/home` returns that year's leaderboards).
16. **Mobile tab switches the main column content** (one list at a time: Recent / Most Helpful /
    scrutiny). Search + year chips stay fixed above the tabs.

### Naming (Q17–Q18)

17. **Drop "Red List / Black List" visible text entirely** — keep them only as internal code/data
    keys (`red`/`black`, CSS `--red`, etc.). Public UI never says "Black List". (P2-C.)
18. **[taste] Scrutiny-list label.** Default: **`Most Helpful` / `Least Useful`** (your pick).
    "Least Useful" is plain language and matches the product's existing **Useful** vote button, so the
    list label and the action vocabulary line up. It describes the *reviews'* usefulness, not the
    reviewer's character (lowest brand/defamation risk; the list is auto-generated over pseudonymous
    reviewers attached to *real* paper titles). For strict symmetry with the vote label you may also set
    the positive list to **`Most Useful`** (→ `Most Useful` / `Least Useful`); keep `Most Helpful` if
    you prefer the warmer positive. Avoid jargon ("Lowest Signal") and accusatory framing
    ("Most Questionable", "Review Risk").

### Scope (Q19–Q20)

19. **Homepage layout only.** Do not redesign the scorecard detail view's *layout* this pass. Its
    *text* still changes: P0/P1 truthfulness (vote counts, score caption) and the P1-D copy de-jargon
    (signal/chunk → plain words) both apply to detail-view strings. Strings change; structure does not.
20. **No new backend endpoints.** Reuse `/api/home` (and `/api/leaderboards` if needed). Server changes
    are: the P0 truthfulness fixes *inside existing functions*, the P2-A vote rate-limit, and the P1-D
    copy change to `signal_label()` in `reviewer_public_scorecard.py` (string output only). No new
    routes, no new aggregated fields (those are design Phase 3).

---

## P0 — Signal truthfulness (synthetic votes → real votes only)

### Background (verified in code)

- `default_social_counts(score, index)` fabricates `up`/`down` from the score
  (`src/secondopinion/reviewer_public_scorecard.py:247`). It is the per-reviewer `social` baked into
  every scorecard at build time (`public_reviewer`, same file ~line 128).
- `public_comments(...)` fabricates per-comment `up`/`down` from the score (same file ~line 172).
- `latest_scored_papers(...)` **sums those synthetic counts** into the home feed `social`
  (`src/secondopinion/server/repository.py:384`) — real votes are never even added here.
- `apply_vote_counts(...)` adds real votes **on top of** the synthetic base
  (`repository.py:453`).
- `build_leaderboards(...)` (server) adds real votes on top of `social_json` synthetic base and uses
  the inflated totals for ranking (`repository.py:513`).
- Frontend renders all of the above as "N useful / M disputed".

Net effect: a freshly scored paper with **zero** real votes still shows e.g. "18 useful · 2 disputed".
This violates the design's own Acceptance Criterion #6 ("no fabricated fields, no demo/fallback
language in production").

### Target behavior

Displayed `up`/`down` everywhere = **count of rows in the `votes` table only**. No seeding.
When a reviewer/paper has zero real votes, the UI says "Be the first to vote" (or omits the metric),
never "0 useful / 0 disputed" rendered as if data exists.

No data migration is required: the **read paths become authoritative** and ignore the stored
synthetic baseline. (Existing scorecards keep stale `social` in their JSON, but it is no longer read
for display.) Optionally re-derive later; not needed for correctness.

### P0-A — Stop seeding at build time

File: `src/secondopinion/reviewer_public_scorecard.py`

1. `default_social_counts` — return zeros (keep the signature so the caller at `public_reviewer`
   needs no change):

   Match:
   ```python
   def default_social_counts(score: int, index: int) -> dict[str, int]:
       return {
           "up": max(10, round(score * 1.4) - index * 3),
           "down": max(2, round((100 - score) * 0.6) + index * 2),
       }
   ```
   Replace with:
   ```python
   def default_social_counts(score: int, index: int) -> dict[str, int]:
       # Community counts come only from real votes in the `votes` table. No seeding.
       return {"up": 0, "down": 0}
   ```

2. `public_comments` — zero the synthetic per-comment counts. Keep the `score` local (still used for
   `tone_for_score`). Match inside the `comments.append({...})`:
   ```python
               "up": max(8, round(score * 0.75)),
               "down": max(2, round((100 - score) * 0.24)),
   ```
   Replace with:
   ```python
               "up": 0,
               "down": 0,
   ```

### P0-B — Home feed shows real vote totals

File: `src/secondopinion/server/repository.py`, function `latest_scored_papers`.

`Vote`, `func`, `select`, and `defaultdict` are already imported in this module — no new imports.

1. Delete the synthetic-sum block. Match:
   ```python
           social_up = 0
           social_down = 0
           for reviewer in reviewers:
               if not isinstance(reviewer, dict):
                   continue
               social = reviewer.get("social") or {}
               social_up += int(social.get("up") or 0)
               social_down += int(social.get("down") or 0)
   ```
   …and remove it.

2. Before the `for paper, scorecard in rows:` loop, compute real vote totals per paper in one query.
   Insert after `rows = session.execute(...).all()`:
   ```python
       paper_ids = [paper.paper_id for paper, _ in rows]
       votes_by_paper: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
       if paper_ids:
           vote_rows = session.execute(
               select(Vote.paper_id, Vote.vote, func.count(Vote.id))
               .where(Vote.paper_id.in_(paper_ids))
               .group_by(Vote.paper_id, Vote.vote)
           ).all()
           for pid, vote, count in vote_rows:
               if vote in ("up", "down"):
                   votes_by_paper[str(pid)][str(vote)] = int(count)
   ```

3. In the per-paper dict, replace the social field. Match:
   ```python
                   "social": {"up": social_up, "down": social_down},
   ```
   Replace with:
   ```python
                   "social": votes_by_paper[paper.paper_id],
                   "vote_total": votes_by_paper[paper.paper_id]["up"] + votes_by_paper[paper.paper_id]["down"],
   ```

### P0-C — Scorecard detail shows real votes only

File: `repository.py`, function `apply_vote_counts`. Match:
```python
        base = reviewer.get("social") or {}
        reviewer["social"] = {
            "up": int(base.get("up") or 0) + counts[reviewer_key]["up"],
            "down": int(base.get("down") or 0) + counts[reviewer_key]["down"],
        }
```
Replace with:
```python
        reviewer["social"] = {
            "up": counts[reviewer_key]["up"],
            "down": counts[reviewer_key]["down"],
        }
```
(The `leaderboard_keys_from_public(...)` call right after now ranks on real-only social, which starts
at 0 → ranking ≈ quality score. That is the intended honest behavior; see P2-A.)

### P0-D — Red/Black rail shows real votes only (and honest ranking)

File: `repository.py`, function `build_leaderboards` (the server one, ~line 513). Match:
```python
        social = dict(score.social_json or {})
        extra = counts_by_paper[score.paper_id][score.reviewer_key]
        up = int(social.get("up") or 0) + extra["up"]
        down = int(social.get("down") or 0) + extra["down"]
        red_score = score.score + up * 0.16 - down * 0.22
        black_score = (100 - score.score) + down * 0.34 - up * 0.1
```
Replace with:
```python
        extra = counts_by_paper[score.paper_id][score.reviewer_key]
        up = extra["up"]
        down = extra["down"]
```
Then change the sort to rank by **quality score only**, with a deterministic tiebreak (integrity:
anonymous votes must not be able to move a reviewer onto a public list in v0.1 — see P2-A). Match:
```python
    red = sorted(items, key=lambda item: item["red_score"], reverse=True)[:limit]
    black = sorted(items, key=lambda item: item["black_score"], reverse=True)[:limit]
    return {"red": red, "black": black}
```
Replace with:
```python
    red = sorted(items, key=lambda item: (-item["score"], item["reviewer_key"]))[:limit]
    black = sorted(items, key=lambda item: (item["score"], item["reviewer_key"]))[:limit]
    return {"red": red, "black": black}
```
And drop the now-unused `red_score`/`black_score` keys from the appended `items` dict (the frontend
does not read them — it reads `score`, `up`, `down`, `nickname`, `paper_title`, `paper_id`,
`reviewer_key`).

### P0-E — Frontend renders real counts; "Be the first" when zero

File: `frontend/index.html` (`<script>` section).

1. Add a small helper near the other render helpers (e.g. just above `renderLatestPapers`):
   ```js
   function socialText(up, down, comments) {
     const u = Number(up || 0), d = Number(down || 0), c = Number(comments || 0);
     const commentPart = `${c} comments`;
     if (u + d === 0) return `${commentPart} · Be the first to vote`;
     return `${u} useful / ${d} disputed / ${commentPart}`;
   }
   ```

2. `renderLatestPapers` — match:
   ```js
                 <span class="home-paper-social">${Number(social.up || 0)} useful / ${Number(social.down || 0)} disputed / ${Number(item.comment_count || 0)} comments</span>
   ```
   Replace with:
   ```js
                 <span class="home-paper-social">${escapeHtml(socialText(social.up, social.down, item.comment_count))}</span>
   ```

3. `boardRows` — match:
   ```js
               <span class="board-meta">${Number(item.up || 0)} useful / ${Number(item.down || 0)} disputed</span>
   ```
   Replace with (rail rows have no comment count; show votes or the prompt):
   ```js
               <span class="board-meta">${(Number(item.up||0)+Number(item.down||0))===0 ? 'No votes yet' : `${Number(item.up||0)} useful / ${Number(item.down||0)} disputed`}</span>
   ```

4. Neutralize the hard-coded placeholder fake counts so a stray pre-API render can't show invented
   numbers. In the initial `splitComments = [...]` array, set every `up`/`down` to `0`. In the
   initial `reviewers = [...]` array there are no social fields (fine). These arrays are pre-API
   placeholders for the resolved view; zeroing keeps them honest. (Low risk, low effort.)

### P0-F — Tests

File: `tests/test_server_api.py`, `test_api_search_scorecard_vote_and_job_flow`. The seed hand-sets
`social: {"up": 1, "down": 0}`. With P0-C, display is real-votes-only, so after one up-vote the count
is **1**, not 2. Match:
```python
    assert vote.json()["scorecard"]["reviewers"][0]["social"]["up"] == 2
```
Replace with:
```python
    assert vote.json()["scorecard"]["reviewers"][0]["social"]["up"] == 1
```

Add new assertions in the same test (after the existing `home` block) to lock in truthfulness:
```python
    # Home feed exposes only real vote totals (zero before anyone votes).
    assert home.json()["latest_papers"][0]["social"] == {"up": 0, "down": 0}
    assert home.json()["latest_papers"][0]["vote_total"] == 0
```

Add a unit test in `tests/test_reviewer_public_scorecard.py`:
```python
def test_build_public_scorecard_does_not_seed_synthetic_votes():
    source = {
        "paper": {"title": "Demo Paper"},
        "reviewers": [
            {"display_id": "R1", "claims": [
                {"claim_text": "Add a baseline.", "hybrid_scores": {"specificity": {"final_score": 0.9}}}
            ]},
        ],
    }
    public = build_public_scorecard(source)
    assert public["reviewers"][0]["social"] == {"up": 0, "down": 0}
    assert all(c["up"] == 0 and c["down"] == 0 for c in public["comments"])
```

Run: `python -m pytest tests/test_server_api.py tests/test_reviewer_public_scorecard.py tests/test_server_batch_scoring.py -q`
(the batch test stores scorecards; confirm nothing else asserts seeded social).

---

## P1 — Stop mislabeling / over-promising

### P1-A — Make the score say what it measures

The number is **review quality** (mean of the six review-quality dimensions: Specificity, Evidence
Link, Actionability, Peer Support, Rebuttal Risk, Tone — see `DIMENSION_LABELS`). It is **not** a
paper-quality rating. On a row next to a famous paper title, a bare "82" reads as "this paper = 82".
That misread is the single biggest credibility risk. The number must always carry a caption.

This resolves design **Open Question #3**: show numeric `0–100` + the existing signal label. **Do not**
add letter grades ("B+") — they do not exist in the API and the example in the design doc is
aspirational.

File: `frontend/index.html`.

1. Score ring caption. Match:
   ```html
             <div class="score-ring" id="scoreRing" aria-label="Overall score 73 out of 100">
               <div class="score-value"><strong id="overallScore">73</strong><span>overall</span></div>
   ```
   Replace the caption word and aria:
   ```html
             <div class="score-ring" id="scoreRing" aria-label="Review quality score 73 of 100">
               <div class="score-value"><strong id="overallScore">73</strong><span>review quality</span></div>
   ```
   And in `renderOverallScore`, match `ring.setAttribute('aria-label', \`Overall score ${avg} out of 100\`);`
   → `ring.setAttribute('aria-label', \`Review quality score ${avg} of 100\`);`

2. Add a one-line clarifier under the feed header. In the `Recently scored papers` panel head markup,
   under the `<h2>`, add:
   ```html
   <p class="panel-note">Scores rate <strong>review quality</strong>, not the paper.</p>
   ```
   Style it as small muted text (reuse `.panel-kicker` styling or add `.panel-note`).

3. Board pill is currently `${score} Q` in `boardRows` — replace the cryptic `Q`. Match
   `<span class="paper-score-pill">${Math.round(Number(item.score || 0))} Q</span>` →
   `<span class="paper-score-pill" title="Reviewer quality score">${Math.round(Number(item.score || 0))}</span>`
   and rely on the section header / row label for "reviewer quality".

### P1-B — Search coverage copy must match the backend

Verified: `search_papers` matches the query against `Paper.title`, `Paper.paper_id`,
`Paper.openreview_forum_id` (ILIKE), **scoped to a single conference** (`conference_id` is required).
There is **no DOI column and no arXiv column**, and **no cross-conference search**.

Do:
- Keep the placeholder honest. Current text "Search paper title, OpenReview ID, or link" is fine —
  **do not** add "DOI" or "arXiv" affordances anywhere (design §7.1 lists them; they are not backed).
- `parsePaperTitle` has a `doi.org` branch that turns a pasted DOI URL into a title query that can
  never match → user gets a confusing "not indexed". Add an explicit guard: if the input resolves to
  a DOI, short-circuit with a clear message instead of querying. In `submitPaperViaApi`, before the
  title query, detect DOI and call a new `showUnsupportedIdentifier(source)` that sets the landing
  error / toast to: `"DOI lookup isn't supported yet — search by paper title or OpenReview ID."`
- Coverage message in `showNotIndexedPaper` hardcodes "ICLR 2022-2025 sample papers". Acceptable for
  v0.1. If cheap, derive the range from `/api/conferences` (`min_year`/`max_year` are returned by
  `list_conferences`). Otherwise leave it.

### P1-C — Do not render unbacked badges

Design §5.1 shows `High confidence · Low dispute` badges per paper row. **The API has no paper-level
confidence and no dispute field** (reviewer-level `confidence` is often null; "disputed" is only a
down-vote alias). Do not add these badges. If you want a dispute hint later, derive it **only** from
real disputed votes when `down > 0`.

### P1-D — De-jargon public copy (jargon scan results)

"signal" and "chunk" are internal vocabulary that leaks into the public UI. A scan of
`frontend/index.html` and `src/secondopinion/reviewer_public_scorecard.py` found the items below.
**Change rendered text only** — keep CSS classes, element ids, data-attributes, and JS variable names
(`signal-chip`, `signal-dot`, `chunk-id`, `data-chunk`, `signalLabel`, `voteState[chunk]`, `tone-*`)
exactly as they are; they are not user-visible (same rule as the `red`/`black` keys).

**Tier 1 — clear leaks. CONFIRMED IN SCOPE for v0.1** (cross-cutting copy pass; touches the home feed,
the detail view's *text*, and the builder's string output — but no layout or endpoint changes):

- **"chunks" → "comments".** Detail-view paper stats render "N chunks": the `paperStats` placeholder
  `<span>6 chunks</span>` and `renderPaperInfo`'s `` `${summary.comment_count ?? splitComments.length} chunks` ``
  → "comments". Status-badge fallback `'Review chunk'` → `'Review comment'`. The visible `chunk-id` tag
  ("C1"…) is an internal id shown as a label — drop it or relabel "#1" (low priority).
- **Score bands: drop "Signal" — highest-impact leak.** The band label shows in every home-feed row's
  meta *and* the detail signal chip. The score is review quality, so use plain words. Map:
  `High Signal → Strong review` · `Solid Signal → Solid review` · `Needs Signal → Mixed review` ·
  `Weak Signal → Weak review` (pairs with the "Review quality" caption from P1-A).
  - **Source of truth:** update `reviewer_public_scorecard.py::signal_label` (the four return strings)
    and `frontend::scoreBand` fallback strings to the new wording, so freshly scored cards are plain
    at the source.
  - **Stored-data remap (apply at data-ingest, not per-render):** `signal_label` *and each reviewer's
    `label`* are persisted in the scorecard, so already-scored cards still carry the old wording. Add a
    `plainBand(label)` helper (passes through anything already plain) and apply it **once in
    `applyPublicScorecard`** — to `summary.signal_label` and to every `reviewers[].label` as the data is
    ingested — so all downstream renders (overall chip, reviewer cards, comment status-badges) stay
    consistent. Also remap `item.signal_label` in `renderLatestPapers` for the home feed.
    *Symptom to close:* the live build remaps only the overall chip, so it shows "Mixed review" up top
    while the reviewer cards still read "Needs Signal" — exactly the gap this ingest-layer remap fixes.
  - **Tests:** no existing test asserts the band strings — the `test_server_api.py` fixture supplies its
    own `signal_label` and only checks `overall_score`, so nothing breaks. Optionally update that
    fixture's `"Solid Signal"` → `"Solid review"` for hygiene.
- **Other "review signal" phrasings:** toast `'Review signal updated'` (×2) → `'Scorecard updated'`;
  home-feed/topic fallback `'Review signal'` / `'review signal'` → `'review'`; criterion fallback
  `'Reviewer-facing score signal.'` → `'Reviewer quality score.'`; builder `'SecondOpinion found a
  review signal here.'` → `'SecondOpinion scored this comment.'`; `situation` "…surfaced as
  public-facing review signals." → "…then surfaced for the community."; criterion "…needs a clearer
  signal." → "…needs to be more specific."

**Tier 2 — brand decision (your call):** **"Review Signal Community"** (in `<title>`, the hero, and a
landing aria-label) is product identity, not a score label. You can keep the masthead brand even after
removing "signal" from the per-row score labels — the confusing part is the row label, not the title.
If you want it gone too: "Review Quality Community" / "Peer Review, Reviewed".

**Tier 3 — borderline, optional:** dimension labels `Peer Support` and `Rebuttal Risk` are jargon-y but
carry tooltips (consider `Peer Agreement` / `Holds up after rebuttal`); "Scorecard" is a product term
but intuitive (keep); nicknames ("Vague Thunder") are whimsical, not jargon (collision handled in P2-B).

---

## P2 — Hierarchy + integrity

### P2-A — Ranking integrity (anonymous votes must not move public lists in v0.1)

Votes are keyed only by a cookie `session_id` (`upsert_vote`, `reviewer_vote` in `api.py`). Clearing
cookies / incognito = unlimited votes. Because the old ranking folded votes into `red_score`/
`black_score`, anyone could brigade a (pseudonymous) reviewer onto the public "Black List".

- P0-D already changes v0.1 ranking to **quality score only** (votes shown but not ranking). Keep it
  that way until real abuse controls exist.
- Add minimal server-side rate limiting on the vote endpoint. File `src/secondopinion/server/api.py`,
  `reviewer_vote`. Simplest acceptable v0.1: cap votes per `session_id` per rolling window (e.g. 60 /
  hour) by counting recent `Vote.updated_at` rows for that session and returning HTTP 429 past the
  cap. (In-memory token buckets won't survive multiple workers; prefer the DB count.) Document this
  as a stopgap; real sybil resistance is Phase 3.
- When Phase 3 reintroduces vote-weighted ranking, do it **after** auth/rate-limit hardening, not
  before.

### P2-B — Fix nickname collisions in the rail

`nickname_for` assigns **"Vague Thunder" to every reviewer scoring < 50**
(`reviewer_public_scorecard.py:222`), and the red pool is a small fixed set. Because v0.1 ranks the
black list purely by lowest score (P0-D), the rail will literally show
`Vague Thunder / Vague Thunder / Vague Thunder`. The paper title is the real disambiguator.

File: `frontend/index.html`, `boardRows`. Make the **paper title the primary identity** and the
nickname a secondary tag (this also matches design §5.2: the rail's job is to route back to the
paper). Match the row template:
```js
           <button class="community-board-row" type="button" data-home-board-paper="${escapeHtml(item.paper_id || '')}">
             <span class="home-paper-meta">#${index + 1} / ${escapeHtml(item.paper_title || 'ICLR paper')}</span>
             <strong>${escapeHtml(item.nickname || item.reviewer_key || 'Reviewer')}</strong>
             <span class="paper-score-pill">${Math.round(Number(item.score || 0))} Q</span>
             <span class="board-meta">${Number(item.up || 0)} useful / ${Number(item.down || 0)} disputed</span>
           </button>
```
Replace with (title bold primary, nickname demoted to a tag; pill caption fixed per P1-A; votes per
P0-E):
```js
           <button class="community-board-row" type="button" data-home-board-paper="${escapeHtml(item.paper_id || '')}">
             <span class="board-rank">#${index + 1}</span>
             <strong class="board-paper-title">${escapeHtml(item.paper_title || 'ICLR paper')}</strong>
             <span class="home-paper-meta">${escapeHtml(item.nickname || item.reviewer_key || 'Reviewer')}</span>
             <span class="paper-score-pill" title="Reviewer quality score">${Math.round(Number(item.score || 0))}</span>
             <span class="board-meta">${(Number(item.up||0)+Number(item.down||0))===0 ? 'No votes yet' : `${Number(item.up||0)} useful / ${Number(item.down||0)} disputed`}</span>
           </button>
```
Add light CSS for `.board-rank` / `.board-paper-title` (title is the visual anchor; keep the rail
rows smaller than main-feed rows per design §6.2).

### P2-C — Soften the public list labels (decision, not an open question)

Design **Open Question #1** is launch-blocking, not deferrable: a publicly labeled "Black List" of
reviewers (even pseudonymized, attached to real paper titles, produced by an automated scorer) reads
as an attack and carries brand/defamation risk. Mitigation already in place: identities are
**pseudonyms** (good). Recommended decision: soften the **public** labels while keeping `red`/`black`
as internal code/data keys.

Change visible strings only:
- "Red List" → "Most Helpful"; "Black List" → the scrutiny label chosen in Layout Q18 (default "Least Useful").
- Locations: home board headings, mobile board tabs, and the in-app `leaderboard-card` headers.
- **Do not** rename JS variables, API keys, CSS classes (`home-board--red`, etc.), or DB fields.

Test coupling: `tests/test_frontend_api_wiring.py::test_frontend_has_community_home_entrypoint`
asserts the string `"Review quality, ranked by the community."` and the element ids
`homeRedList` / `homeBlackList` — keep those (ids and that headline stay). If you change the visible
"Red List"/"Black List" **text**, update any test that asserts that visible text. (Currently the
wiring test asserts ids, not the words "Red List"; verify before editing.)

If the team prefers to keep "Red List / Black List" branding, that is a product call — but make it
**explicitly**, and keep the softer subtitle ("Top reviewers" / "Needs scrutiny") so the page never
reads as naming-and-shaming.

### P2-D — Visible error and sparse states

Design §8.3 wants an explicit API-unavailable state. Today `loadCommunityHome`'s `catch` only
`console.warn`s and re-renders empty — a down API looks identical to "no data".

File: `frontend/index.html`, `loadCommunityHome`. Distinguish the two:
- Add a status element above the feed (e.g. `<div id="homeStatus" role="status" aria-live="polite" hidden></div>`).
- On `catch`, show: `"SecondOpinion API is unavailable. Search and live scorecards need the production API."` (short, operational — no stack traces, no internal pipeline names per §8.3).
- On success with empty arrays, keep the existing "No scored papers yet" empty states (that is the
  correct *empty*, not *error*, copy).
- Sparse case (design gap): when the feed has 1–2 papers and the rail is near-empty, the page still
  reads as broken. At minimum, keep the "Be the first to vote" affordance (P0-E) so thin data looks
  intentional rather than missing.

### P2-E — Accessibility: don't encode signal by color alone

Tones map to color (`toneMap`) for the core positive/risk distinction. Pair every tone with text or
an icon so colorblind users get the signal:
- The `signal-dot` next to the signal label should carry a shape/aria, not just a color fill.
- Reviewer/score tones already have a text `label` in most places — ensure the home pill and rail
  also expose the signal label as text (P1-A covers the caption). Keep it brief; this is polish, not
  a blocker.

### P2-F — Remove the per-paper leaderboards from the scorecard detail view

The detail view renders its own "Most Helpful / Least Useful" leaderboards (the `leaderboard-section`
with `#redList` / `#blackList`, populated by `renderLeaderboards` / `orderedLeaderboard` /
`leaderboardRow`). On a single paper these are **redundant and low-value**: every reviewer is already
listed above with their score, and ranking 3–4 same-paper reviewers — whose scores often cluster (e.g.
61–62, all "Mixed review") — conveys nothing. In the live build they render as two empty boxes, which
reads as broken. Leaderboards are a **homepage**, cross-paper / whole-year signal (design §4.1), not a
per-scorecard one.

- Remove the `leaderboard-section` block from the resolved/detail view and the `renderLeaderboards` /
  `orderedLeaderboard` / `leaderboardRow` calls that feed it.
- To keep the "who was most helpful here" cue for free, **sort the reviewer cards by score descending**
  in `renderReviewerCards` (highest-quality review first). No separate section needed.
- Reviewer-level voting stays on each reviewer card / comment; removing the leaderboard does not remove
  voting.

### P2-G — Microinteractions, identity & voice (live-build feedback)

Polish, but it carries the product's personality — worth doing in v0.1.

- **Votes read as like / dislike, not "+ / −".** Replace the `+`/`−` glyphs (`vote-icon`, in
  `renderComments` and any reviewer-card vote UI) with thumbs-up / thumbs-down (👍 / 👎 or inline SVG).
  Keep the count, the optimistic toggle, the `is-up`/`is-down` states, and `aria-pressed`. **Pair with
  P0:** the live build shows inflated counts ("👍 45 / 👎 11") that are *synthetic* — once P0 lands
  these are real and usually start at 0, so render the thumb with no number (or "0") at zero votes,
  never a fabricated 45.
- **Red/black top accent on the two boards (homepage rail).** Per your call, give each board a colored
  **top accent** (thin top bar / heading tint): red for `Most Helpful`, black for `Least Useful`. Keeps
  a subtle red/black visual identity while the *labels* stay soft — color identity without the "Black
  List" wording. Two cautions: (1) keep it a top *accent*, not a full-card block (design §6.4); (2)
  solid black reads funereal/shaming and red-for-good reads as "error" to Western users — consider
  charcoal over pure black and an honor-roll "ribbon red". Final hue is your taste call.
- **Recognizable pixel avatars, keyed to the nickname.** Today 3 avatars (`R1/R2/R3`) cycle, so they
  look random and repeat. Redesign as a small library of distinct, *recognizable* pixel mascots themed
  to the nickname's noun (Hawk → hawk, Anchor → anchor, Scout → binoculars, Needle → needle, Fog →
  cloud, Mapper → map, Pilot → checklist, Cartographer → compass, Thunder → storm cloud), and key the
  avatar to the nickname so the same name always gets the same mascot. *Also fix nickname uniqueness:*
  `nickname_for` draws from a small pool, so one paper shows two "Assumption Mapper" cards — within a
  single scorecard, nicknames (and thus avatars) must be unique (append a suffix or widen the pool).
  (Side note: the nickname "Signal Cartographer" itself leaks "signal" — rename, e.g. "Compass
  Cartographer", per P1-D.)
- **Second-opinion voice: short, punchy, a little cheeky — not academic.** The `SO` take under each
  comment (`second_opinion` / the scorer's `second_opinion_take`, plus the fallback strings) reads like
  a rubric today ("This comment contains a usable signal, but the author may need to pin down the exact
  target."). Target the earlier, livelier voice: one line, punchy, a wink — aimed at the *review's
  vagueness*, never at the paper's authors or the reviewer as a person (brand/defamation guardrail),
  and jargon-free (no "signal", per P1-D). Examples (before → after):
  - "This comment contains a usable signal, but the author may need to pin down the exact target." →
    **"Useful-ish — but it's aiming at a fog bank. Name the target."**
  - dry "novelty is limited" take → **"'Not novel' — compared to *what*? Cite a name or it's a vibe."**
  - generic praise → **"Says 'reproducible.' Shows no receipts."** · **"Right neighborhood, no address."**
  - fallback "SecondOpinion found a review signal here." → **"SO read it. Verdict: meh, but salvageable."**
  Source: the scorer prompt that generates `second_opinion_take` (update its voice) + the static
  fallbacks in `public_comments`. This is a prompt/copy change, not a layout one.

---

## P3 — Guardrails: what to deliberately NOT build in v0.1

Building these now would either mislead users or require backend that does not exist. Ship the page
without them; add when data/endpoints land (design Phase 3).

- **No disabled browse tabs.** Design §7.2 lists `Recent / Highest / Lowest / Most disputed / Needs
  votes`. Only `Recent scored` is backed by `/api/home`. Render **only** Recent. Do **not** render
  greyed-out tabs — a row of dead tabs reads as broken and contradicts the "usable console" goal.
- **No conference switcher behavior.** Keep ICLR fixed (search is hardcoded to `/api/conferences/ICLR/papers`).
  The selector can exist visually only when changing it actually re-scopes search. `/api/conferences`
  is available to populate it later.
- **No DOI / arXiv search.** Not backed (P1-B).
- **No "Recent votes" / "Most disputed" rail sections.** No aggregated endpoint exists. Adding them
  would require new API fields (design Phase 3). Ship red/black only.
- **Preview drawer (design Phase 2) is optional for this pass.** If built, reuse
  `GET /api/papers/{id}/scorecard` and ensure it renders **real, zero-aware** votes (P0-E). Do not
  introduce new fake counts.

---

## Acceptance checklist (maps to design §10)

- [ ] Home feed `social` and scorecard reviewer `social` reflect **only** real `votes` rows; zero
      before anyone votes. (P0; covered by updated `test_server_api.py`.)
- [ ] No path renders fabricated "useful/disputed"; zero-vote items show "Be the first to vote" /
      "No votes yet". (P0-E)
- [ ] Score is always captioned as **review quality**, never a bare number or letter grade; one-line
      "scores rate review quality, not the paper" clarifier present. (P1-A; design Q3 resolved)
- [ ] No "signal"/"chunk" jargon in rendered public text: score bands read as plain quality words,
      comment counts say "comments" not "chunks"; code identifiers (classes/ids/attrs) unchanged. (P1-D)
- [ ] Search UI promises only title / paper ID / OpenReview ID within the selected conference; no
      DOI/arXiv affordance; DOI paste yields a clear "not supported yet" message. (P1-B)
- [ ] No paper-level confidence/dispute badges. (P1-C)
- [ ] Red/Black ranked by quality score only; vote endpoint rate-limited. (P2-A)
- [ ] Rail rows lead with paper title (nickname demoted) so "Vague Thunder" collisions don't look
      broken; rail rows visually lighter than feed rows. (P2-B, design §6.2)
- [ ] Public labels softened to "Most Helpful" / "Least Useful" (default; or another Q18 option,
      explicitly chosen); "Red List"/"Black List" never shown; internal keys unchanged. (P2-C / Layout Q17–Q18)
- [ ] Desktop is two-column: feed ≈70% / sticky signal rail ≈30%; rail is one container with two
      stacked light lists, both visible. (Layout Q1–Q4, Q9)
- [ ] Compact search header (no hero); search + recent feed + rail all in the first viewport. (Layout Q6, Q12)
- [ ] Mobile uses `Recent | Most Helpful | <scrutiny>` tabs, Recent default; tab switches the main
      column. (Layout Q5, Q16)
- [ ] No preview drawer; row/rail click opens the existing scorecard with a visible transition. (Layout Q13, Q14)
- [ ] Scorecard detail layout untouched; no new backend routes added. (Layout Q19, Q20)
- [ ] API-unavailable state is visible and distinct from empty; copy is short/operational. (P2-D, §8.3)
- [ ] No disabled browse tabs, no unbacked rail sections, ICLR fixed. (P3)
- [ ] Public scorecard still hides internal fields (`hybrid_scores`, `memory_prior`, `mapped_score`,
      scorer internals). Re-run `test_api_search_scorecard_vote_and_job_flow` /
      `test_build_public_scorecard_*`. (design §10.6 — already enforced by existing tests; keep green)

## Files touched (summary)

- `src/secondopinion/reviewer_public_scorecard.py` — P0-A (zero seeding), P1-D (`signal_label` wording).
- `src/secondopinion/server/repository.py` — P0-B/C/D (real votes only; honest ranking).
- `src/secondopinion/server/api.py` — P2-A (vote rate limit).
- `frontend/index.html` — P0-E, P1-A, P1-B, P1-D (de-jargon copy + `plainBand` remap), P2-B, P2-C, P2-D, P2-E.
- `tests/test_server_api.py`, `tests/test_reviewer_public_scorecard.py` — P0-F (+ truthfulness tests);
  P1-D adds no required test changes (no test asserts band strings; fixture wording update optional).

## Open questions resolved here

- **Q1 (red/black labels):** soften public labels now (P2-C). Decision required before launch.
- **Q2 (global vs paper-level ranking):** emphasize **paper-level** rail rows (P2-B); global
  pseudonymous reviewer ranking amplifies the collision + ethics risk.
- **Q3 (score format):** numeric 0–100 + signal label, always captioned "review quality"; no letter
  grades (P1-A).
- **Q4 (default year):** keep 2025 fixed for v0.1 (API + frontend already default there). To make it
  "newest year with enough scored papers" later, probe `/api/home` per year and pick the newest whose
  `latest_papers` length ≥ a threshold (e.g. 6); fall back to the newest non-empty year.
