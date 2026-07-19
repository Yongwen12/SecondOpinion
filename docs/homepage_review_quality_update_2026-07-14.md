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

## Eighth pass (2026-07-18): emoji reactions beside the vote, votes de-texted

Two-layer community feedback, WhatsApp-channel style, with the layers kept orthogonal
by palette curation rather than by merging systems:

- **Votes lose their words.** Board rows, the rate modal, and the paper-page reviewer
  detail all use the same compact pair: `▲ count / ▼ count` with the meaning in
  title/aria ("Agree with this assessment" / "This review was helpful"). The selected
  side fills ink. GitHub-precedent: judgments (Approve / Request changes) and emoji
  reactions live side by side without labels colliding.
- **Emoji reactions are a judgment-free layer.** Fixed palette 💀 😂 🤯 🫡 😭 - deliberately
  no 👍/👎/✅/🎯, so reactions never overlap the agree/disagree semantics. One reaction
  per session per review (tap a new one to switch, tap your own to remove), rendered as
  square chips next to the vote pair on all three surfaces, with a "+" opener that
  expands the full palette inline.
- **Backend**: `reviewer_reactions` table (unique per paper/reviewer/session; alembic
  20260718_0004), `POST /api/papers/{id}/reviewers/{key}/reactions` (whitelist, 422 on
  judgment emoji, 429 rate limit at 120/h), counts embedded in the scorecard
  (`reactions` + `viewer_reaction` per reviewer), in dynamic leaderboard rows, and
  overlaid onto the static home snapshot by the renamed
  `enrich_home_community_signals` (formerly `enrich_home_comment_previews`).
- Reactions feed no scores; votes remain the calibration signal. No-API/demo rows fall
  back to a local `soDemoReactions` store, and against an old backend the strip
  degrades to a "+" that toasts on failure.

## Verification (eighth pass)

- `python -m pytest tests/test_server_api.py -q`: 8 passed, including the new
  `test_reviewer_reaction_flow` (react, switch, second session, scorecard + home
  embeds, clear, 422 on 👍, 404 on ghost paper).
- Browser against the seeded local API: chips render from the enriched snapshot
  (💀3 😂1), picker opens/closes, react-switch-remove round-trips, reload restores the
  viewer's own chip from the server, paper-page detail and modal share counts, a modal
  removal syncs back to the board row, mobile 375px has no overflow.
- Inline JS `node --check` passed.

## Ninth pass (2026-07-18): reactions become the primary response tool

- The quick set (💀 😂 🤯) now renders as tappable chips at all times, even at zero -
  one tap reacts, no picker needed. Long-tail emoji (😤 😭) surface automatically once
  they have counts (or are the viewer's pick) and otherwise live behind the "+", which
  disappears entirely when all five are visible.
- 🫡 (Unicode 14) replaced with 😤: Windows 10's emoji font predates Unicode 13, so the
  salute rendered as a tofu box. The palette now sticks to pre-Unicode-13 glyphs;
  server whitelist updated to match.
- Comment invites shorten to "Add a take ->" on board rows and paper-page reviewer
  previews - reactions lead, comments follow.
- Verified against the seeded local API: zero-count quick chips tap-to-react directly,
  "+" expands the full palette with 😤/😭, counts auto-surface long-tail chips, and the
  paper-page detail hides the "+" when nothing is left to reveal. pytest 8 passed;
  inline JS node --check passed.

## Tenth pass (2026-07-18): the full core set on the surface, a big palette in the popover

- All five core emoji (💀 😂 🤯 😤 😭) now stay on the surface at all times, poll-style:
  a zero-count chip is an open ballot, and the count appears beside the emoji once
  someone taps it.
- The "+" opens a proper popover (2px-ink panel, wraps to the viewport) holding the
  full 25-emoji palette: the core five plus 🔥 👀 🤔 😬 😅 🙃 😱 🤬 😴 🥱 🍿 ☕ 🤡 🗿 💅 🎻
  🚩 😈 🤖 😇 - all pre-Unicode-13 (Windows 10-safe), all judgment-free. Extended emoji
  surface as counted chips once used. Picking closes the popover; clicking anywhere
  outside dismisses it. Server whitelist matches the 25.
- Verified: zero-count core chips tap-to-react, popover pick (🍿, 🤖) surfaces a counted
  chip on board rows and the paper-page detail, outside-click dismissal, 375px fit;
  pytest 8 passed; inline JS node --check passed.

## Eleventh pass (2026-07-18): the paper page adopts the board-row surface contract

The paper page still segregated all interaction inside the expandable detail, so a
reader saw scores and review text but no way to respond without opening a panel. Now
every reviewer entry carries the same surface as a home board row:

- Collapsed: Reviewer N + score, review excerpts, then the live social strip
  (▲/▼ votes + the five core reaction chips + "+" popover) and the take previews -
  vote and react with zero clicks of expansion.
- Expanded: the deep layer only - AI read, the full Community-takes form and thread,
  the score dimensions with evidence, and the OpenReview/report links. The vote and
  reaction strip stays on the surface above (no duplicate inside the panel).
- New `positionReactionPicker` clamps the "+" popover into the viewport (the strip
  sits 52px-indented inside entries; on 375px the panel used to overflow right).
  Synchronous measurement, since rAF never fires in throttled tabs.

Verified: all three collapsed entries show votes/chips with live counts; voting and
reacting from the collapsed state round-trips; expansion shows no duplicate strip and
keeps the surface strip; popovers clamp inside 375px on both the board and paper
pages; pytest 8 passed; inline JS node --check passed.

## Twelfth pass (2026-07-19): scores step back, human signals keep the red

Board rows shouted their reference number: a 42px red score, a red-bordered paper
button, green/red vote arrows, and a pure-black quote fighting the masthead. This
pass demotes everything that is machine reference and keeps color only where a
human acted:

- Row quotes (and the modal claim) drop one rung to `#2f2f2f`; pure black now
  belongs to the board headline and tab block alone, so the page keeps a single
  black anchor above the fold.
- The score goes gray: 30px / weight 800 / `#4a4a4a` with a `#9a9a9a` unit line,
  and the micro meter fills in ink instead of red on every board. Severity still
  reads from the bar length and HIGH/WATCH tier word - the number is a reference,
  not a verdict.
- "MORE ABOUT THIS PAPER" sheds its red box and becomes a quiet gray text link;
  red only answers the cursor.
- Vote arrows lose the green/red fills: gray at rest, ink on hover. A cast vote is
  the only colored state - agree fills the cell black, disagree fills it the site
  red, both with a white arrow and count.
- Zero counts vanish: an unvoted row shows two bare arrows (min-width keeps the
  target), and a count appears only once someone has voted. aria-labels keep the
  full wording either way.

Verified via localhost:8377 DOM pass: quote `rgb(47,47,47)` vs headline
`rgb(17,17,17)`, score `rgb(74,74,74)` 30px/800, meter fill `rgb(17,17,17)`,
rowrate border/padding 0, arrows `rgb(143,143,143)`, zero `.outrage-vote-count`
spans in demo data; inline JS node --check passed.

## Thirteenth pass (2026-07-19): the reviewer panel folds into two drawers

The expanded reviewer panel stacked the full comment form, the thread, and the
dimension grid in one long scroll. Now the deep layer is two collapsed `<details>`
drawers under the AI-read line:

- "Community takes · N takes / add yours" - the form, thread, and status live
  inside; the summary carries the count so the scent survives the fold.
- "Why this score · AI dimensions & evidence" - no longer open by default.
- Drawer state is remembered per reviewer (`takesOpen`/`dimsOpen`, captured via a
  capture-phase `toggle` listener, since re-renders rebuild the DOM): posting a
  take or voting re-renders the panel without slamming the drawer shut.

Verified on localhost:8377 demo data: both drawers collapsed on expansion; opening
takes + posting keeps the drawer open and bumps the summary to "1 take"; a vote
re-render keeps both open flags; inline JS node --check passed.
