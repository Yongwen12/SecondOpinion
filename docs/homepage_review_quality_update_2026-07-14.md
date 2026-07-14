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

## Verification

- Inline homepage JavaScript syntax check passed.
- `python -m pytest tests/test_server_api.py -q --basetemp C:\tmp\secondopinion-pytest` passed: 6 tests.
