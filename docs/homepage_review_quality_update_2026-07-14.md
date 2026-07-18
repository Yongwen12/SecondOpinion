# Homepage review-quality update — 2026-07-14

## Purpose

Make the public review rankings easier to interpret and make community ratings better informed.

## Homepage

- Reframed the three boards as **Worst Review Failures**, **Personal / Toxic**, and **Reviews Worth Keeping**.
- Clarified that the first board is ordered by review-quality risk, with rank #1 representing the most severe item in that list.
- Added a compact venue review-quality-risk chart using full 2025 scored-review aggregates, not a leaderboard sample.
- An empty homepage search with a selected venue opens that venue's ranked review list, ordered by risk and capped at 50 results.
- Removed secondary audit/coverage explanatory copy from the landing view.

## Community rating modal

- Removed AI score and AI-rationale presentation from the vote flow.
- Added a neutral reminder that the user is rating a public review, not the paper or reviewer as a person.
- Loads public paper context (abstract and decision), the complete official review, and relevant extracted review chunks. These sections are collapsed by default.
- Normalizes common LaTeX notation in paper titles shown by the paper picker.

## API support

- The scorecard endpoint now returns the paper abstract plus the selected reviewer's complete official review and review chunks.
- Venue-scoped home requests honor a caller limit up to 50 leaderboard entries.

## Follow-up pass (same day): venue hook + board legibility

- Replaced the six-row venue risk table with a compact strip: a headline hook ("The meanest reviewers are at TMLR.") generated from the top-ranked venue, plus six ranked venue cells (№1 inverted in ink, score shown as `20/100` with a relative bar). Roughly one third of the previous height; stays resident on the page instead of moving to a one-time popup.
- Board tabs became a full-width three-cell segmented control with a glyph identity per board (✖ failures, ☠ toxic, ★ worth keeping) and per-board counts, so the three boards read at a glance.
- Row ranks for the top three use stacked glyphs (✖✖✖ / ✖✖ / ✖, ★ on the praise board) with a small №; scores render as `95/100` with a micro meter, expressing the 0–100 scale without explanatory copy.
- Venue data uses canonical casing (NeurIPS) so venue-strip clicks match the search select options.

## Third pass (same day): community takes move to the surface

- Board cards drop the reviewer nickname and the AI verdict line. Each card now shows: the review claim (headline), paper title · venue, an agree/disagree vote tally, and up to two community comments ("takes") inline with author handle and age, plus a "+N more takes" opener. Empty state invites the first take.
- Card comments hydrate lazily from the comments API for rows with a nonzero comment count, cached client-side; posting/editing/deleting a comment from the modal updates the card immediately.
- The rate modal is reordered around community input: claim headline (nickname removed), paper line, vote buttons, comment form, community takes — with paper abstract / full review / chunks collapsed at the bottom as evidence.
- On the paper scorecard, the community-takes block moves above the AI dimension grid, since user comments and votes are the core asset.

## Fourth pass (same day): embed comment previews in home rows

- `build_leaderboards` now embeds `latest_comments` (up to two newest, plus an accurate `comment_count`) on every leaderboard row via a new `comment_previews_by_reviewer` helper, which loads a paper's comments once and returns both count and previews. This replaces the count-only `comment_counts_by_reviewer` (superseded; `limit=0` yields counts alone).
- The default 2025 homepage is served from the pre-rendered snapshot, which is comment-cold. `enrich_home_comment_previews` overlays live previews and refreshed counts from the DB onto the snapshot's rows at request time (deduped per paper, best-effort — a failure serves the bare snapshot). So both the venue (dynamic) and default (static) home paths carry community takes in the first payload.
- Frontend seeds `boardCommentCache` from each row's embedded `latest_comments` and only fetches rows that lack an embed, eliminating the per-row `/comments` round trips on first paint. Opening a review still fetches the full comment list.
- Votes on the static-home path are unchanged (still snapshot values); only comments are overlaid. Refreshing vote tallies live is a possible follow-up.

## Fifth pass (same day): unify voting and comments on the paper page

- The paper scorecard's reviewer detail panel now uses the same interaction contract as the board rows and rate modal: an Agree/Disagree (or Helpful/Not quite for strong reviews, score >= 70) vote row with live counts, followed by the Community takes form and thread. Votes go through the existing per-reviewer vote endpoint with optimistic select-and-rollback.
- The AI multi-dimension scoring collapses into a one-line digest ("AI score dimensions — Helpfulness 15 · Friction 10 · Tone risk 5") that expands on click, with the score guide inside; metric bars animate on expand.
- Reviewer nicknames ("Vague Thunder", "Outrage Beacon") are replaced by plain positional names: Reviewer 1, Reviewer 2, ... in payload order, across cards, the detail panel, comment filters, and topic tooltips. Nicknames stay in the payload (avatars still derive from them) but are no longer displayed.
- Paper-page comment loads/posts/edits/deletes now write through to the homepage board comment cache, so takes stay consistent when navigating back.
- Merged with the concurrent "Refine community voting UI" pass: vote labels unify on Helpful / Not helpful everywhere (board modal and paper detail), board rows keep their inline agree/disagree vote strip, and board-row reviewer aliases derive from the reviewer key (R4 -> "Reviewer 4") instead of nicknames.

## Verification

- Inline homepage JavaScript syntax check passed.
- `python -m pytest tests/test_server_api.py -q --basetemp C:\tmp\secondopinion-pytest` passed: 6 tests.

## Sixth pass (2026-07-18): comments on the surface, an honest venue index, inline reviewer expansion

User feedback drove three changes:

1. **Comments no longer hide inside panels.** Home board rows always render their takes strip: rows with comments show the two newest plus "+N more takes ->", and empty rows show a "No takes yet - add the first ->" opener into the rate modal (the invite had regressed to nothing). On the paper page, each collapsed reviewer entry now previews its two newest community takes (with the same +N / add-the-first openers) using the comments already embedded in the scorecard payload - zero extra requests. The openers expand the reviewer inline; the empty-state opener also focuses the comment box.
2. **The venue ranking reads as a ranking, not navigation.** The six-cell segmented strip (which looked like clickable tabs but only preset the search dropdown) is now a static leaderboard: one row per venue with a rank number, venue name, a score-scaled bar, `NN/100`, and the review count. Plain divs - no button semantics, cursor, or hover states - with #1 carried in accent red. The `data-venue-filter` click handler was removed.
3. **Reviewer entries expand in place and say what the score is.** Collapsed rows show `Reviewer N`, the big score with an explicit `/100` + "AI usefulness" label, and the review excerpts. Clicking expands a dossier directly under that reviewer (never at the section bottom, which the old `#scoreDetail` panel did): AI one-line read, Helpful/Not-helpful vote row, the Community-takes form and thread, the "Why this score" dimension grid with quotes/verdicts open by default, and a prominent "Read the full review on OpenReview ->" button plus Report link. The bottom `#scoreDetail` element, its clip/animation CSS, and the digest-summary fold are gone; `renderScoreDetail()` now just re-renders the reviewer grid.

Implementation notes: scorecard loads seed `boardCommentCache` per reviewer so paper-page and home-board previews stay consistent both directions; `commentCount` tracks post/edit/delete so "+N more" math stays honest; metric bars carry inline widths animated by a CSS `barIn` keyframe instead of the old `requestAnimationFrame` width writer (which never fired in throttled/background tabs, leaving bars empty); reduced-motion disables both the expansion and bar animations.

## Verification (sixth pass)

- Inline homepage JavaScript syntax check passed (`node --check` on the extracted script).
- `python -m pytest tests/test_server_api.py -q` passed: 7 tests (backend untouched).
- Browser-verified against a locally seeded API (3 reviewers, mixed comment counts): venue rows render as non-interactive divs with scaled bars; board rows show embedded takes and the empty invite; paper page shows per-reviewer previews (+N counts), inline expansion above the next entry, working vote round-trip, comment post updating thread, previews, and the home board cache; deep link `?paper=...&reviewer=R2` opens expanded; mobile (375px) has no horizontal scroll and a one-column dimension grid.

## Seventh pass (2026-07-18): one visual hierarchy for the landing page

The venue index, the search form, and the main board all carried similar visual weight,
so the page had no focal point. New hierarchy - identity, action, context, story:

- **Search moves up** directly under the masthead intro: the page's primary action, and
  the only heavy-bordered box in the top zone.
- **The venue risk index demotes to a compact brief** below the search: 15px title, gray
  kicker, 30px rows with 4px bars and 14px scores (~207px total, down from ~330px). Red
  survives only on the #1 row and the named venue. Still fully static.
- **The board becomes the page's story**: a red uppercase eyebrow ("99,671 public reviews
  audited"), the heading scaled to clamp(32px, 3.6vw, 44px) with a red terminal period -
  the largest type on the page after the masthead.

Type scale on desktop now reads masthead 92 > board heading 44 > review quotes 20 >
venue brief 15/14. Verified in-browser (order, block heights, fold position, static venue
rows, board takes unaffected) at 1280px and 375px; inline JS `node --check` passed.
