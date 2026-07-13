# Homepage masthead redesign v0.2

Date: 2026-07-12/13. Scope: full frontend surface — landing (`.outrage-home`), detail view
(`.app-view`), methodology/privacy/terms, meta/favicon.

## Problem

In v0.1 the brand ("Judge My Reviewers", 15px) was the smallest text on the page while the
slogan ("A second opinion on peer review.", 54px) was the largest — inverted hierarchy for a
product whose name is the pitch. The page also spent three stacked bands (hero, boxed stats,
board intro) before showing any content, and carried a second accent (yellow) against the
declared palette of ink + one red.

## Design decisions

1. **The brand is the headline.** Newspaper-masthead layout: the `#homeBrand` reset button now
   lives inside the `h1` and renders at `clamp(48px, 7.6vw, 92px)`, weight 900, with the red
   square brand mark scaling with the type (`.13em`). The old slogan is demoted to a bold
   lead-in inside the intro paragraph. One glance = product name, second glance = what it does.
2. **One red, zero yellow.** All `#ffe600` / `#fffbe0` / `#fffdf0` usages removed: active tab is
   ink-on-white inverted to white-on-ink, ticker highlight is red text, CTA band is a black
   plate with a white button (hover red), search focus throws a hard red offset shadow,
   row/list hovers are neutral `#fafafa`/`#f5f5f5`.
3. **Praise mode = ink, not green.** `body.praise` now swaps the accent to `#111`: on the
   "Most Helpful" board the scores, stamp, and #1 rank turn ink while red stays reserved for
   friction. The brand mark is hardcoded red so it never changes meaning.
4. **Stats as a rule, not a card.** The boxed 3-cell coverage strip becomes an open band under a
   2px ink rule: 36px/900 tabular numerals, uppercase micro-labels, footnote hanging below.
   No borders between cells — the grid does the work.
5. **Board intro flows left.** Eyebrow → 30px H2 → one-line description, all left-aligned; the
   right-aligned clipped description from v0.1 is gone. Tabs keep the 2px ink baseline; the
   active tab is the only filled element on the page above the CTA.
6. **Utility bar.** Header slims to a hairline bar: uppercase tagline left, Methodology + Sign in
   right. Sign-in hover is red text instead of a yellow fill.

## Interaction map (unchanged hooks, sharpened states)

- Masthead click = home reset (`data-home-reset` moved with `#homeBrand`).
- Row hover: neutral wash + rank ignites to ink; `RATE THIS ->` and meta actions turn red.
- Search focus: border stays ink, red hard shadow signals live input; invalid state unchanged.
- Tabs: white-on-ink active, gray → ink on hover; counts stay hidden.
- Modal primary buttons: ink plate, red on hover (was yellow plate).

## Interaction pass (same date, second iteration)

Bug fixes found while adding polish:

- **Search form grid break**: with text entered, the clear button became a 4th visible item in a
  3-column grid and pushed "Find paper" onto a second row. Fixed with a 4th `auto` track
  (desktop) and `auto` instead of `42px` (mobile).
- **Invisible invalid state**: `showInputError()` set `.is-invalid` on the landing form but no
  CSS existed for it. Added red border + the existing `nudge` shake.
- **Toast**: still carried the old 12px radius and lime hard shadow; now a flat ink plate.

Additions:

- **Sticky mini-masthead** (`#stickyBar`): fixed 48px bar with brand, "Find paper /" and Sign in;
  appears via IntersectionObserver once `.home-intro` scrolls out, `visibility` gated so its
  buttons are unfocusable while hidden. Sign-in label syncs with auth state.
- **Keyboard affordance made visible**: `/` keycap hint sits in the search field (the shortcut
  already existed but was undiscoverable). Hides on focus or when the field has a value;
  hidden on mobile.
- **Search-results keyboard nav**: ArrowDown from the input enters the results, ArrowUp/Down
  moves, ArrowUp from the first result returns to the input, Escape closes and refocuses.
  Clicking outside the form/results also closes them.
- **Count-up stats**: coverage numbers tick up over ~850ms (cubic ease-out, tabular-nums so no
  jitter). Skipped under `prefers-reduced-motion`; background tabs snap to the final value.
- **Board-switch stagger**: rows slide in 26ms apart, only when the visible board kind changes
  (`renderCommunityBoard.lastKind` guard) — silent data refreshes do not replay it.
- **Tactile details**: the rotated stamp straightens on row hover; scorebox gets a plain-language
  `title` tooltip; `::selection` is ink-on-white inverted; all motion is disabled under
  `prefers-reduced-motion`.

## Adversarial review round (16-agent verify pass over the diff)

Confirmed and fixed:

- **Escape collisions**: the results-dropdown Escape handler now yields to open modals, only
  refocuses the input if focus was inside the search UI, and the pre-existing reviewer-deselect
  Escape branch yields to an open dropdown — one Escape peels one layer.
- **Entrance animation cancelled on load**: the first render is no longer treated as a board
  change (`lastKind` seeded), so the demo→static re-render can't cancel a stagger mid-flight.
- **Sticky bar stale state**: replaced raw IntersectionObserver entries with a `syncStickyBar()`
  that reads live geometry, gates on `body.is-idle`, rescues focus before hiding, and is called
  explicitly from `resetToSearch()` and the popstate home path — kills the flash-over-header on
  every scorecard→home return.
- **Praise mode scoped correctly**: instead of swapping `--oh-accent` to ink globally (which made
  the CTA button vanish black-on-black on hover and turned the sticky brand dot black), praise
  mode now overrides only the score semantics (num, #1 rank, stamp). Red remains the interaction
  color everywhere.
- **Focus visibility**: `.search-results--compact` cards got a red `:focus-visible` outline (the
  app-view dropdown previously fell back to an invisible 15%-alpha green halo).
- **Tooltip inheritance**: the `RATE THIS ->` button has its own `title` so it no longer inherits
  the scorebox's "open the row" tooltip that contradicted its click behavior.
- **Combobox ARIA**: both search inputs are `role=combobox` with `aria-expanded`/`aria-controls`
  wired in show/hideSearchResults; result buttons are `role=option`; empty state is presentational.
- **Pre-existing dead-end fixed**: #rateModal/#authModal lived inside `section.landing`, so in the
  detail view (`.is-resolved .landing{display:none}`) Save/Follow/Sign-in opened an invisible
  modal that froze scrolling and swallowed Escape. Both modals moved out to `<body>` level.

## Completion pass (2026-07-13): detail view, static pages, meta

**Detail view de-carded.** `.app-view` sections stopped being bordered boxes: the topbar carries
a 2px ink rule, each section below opens with its own 2px rule and an uppercase micro-header
(`THEMES`, `COMMENTS`), content sits flush with the container like the landing page. Reviewer
cards became a flat single-column list with hairline separators — selection is a 3px red inset
bar + gray wash, the expanded score panel is a flat `#fafafa` dossier with borderless metric
cells, and pixel avatars render `grayscale(1)` so the page stays ink + one red. Paper titles
wrap at up to 32px/900 instead of truncating with an ellipsis. Comment votes: "useful" fills
ink, "disputed" outlines red; the AI marker is a black chip; linked-comment highlight is a red
bar instead of per-reviewer pastel gradients. The old mobile reviewer carousel (horizontal
scroll-snap cards) became a natural stacked list.

**Static pages unified.** methodology/privacy/terms already shared the editorial skeleton;
their off-brand `#d71920` red became `#e10600`, fonts now match the app stack, `h1` weight is
900 with tight tracking, the brand link carries the red square mark, and links redden on hover.

**Meta finish.** All four pages ship an SVG favicon (ink square + red corner — the wordmark's
period motif), meta descriptions, and the index has OG tags.

## Verified

- Full test suite: 332 passed.
- 11/11 `tests/test_frontend_api_wiring.py` pass.
- 1440px: masthead fits one line (894px), no horizontal scroll.
- 375px: masthead wraps to exactly two lines at ~43px, stats fall to 2-col, no overflow.
- Praise/heat board toggle re-renders with correct accent semantics.
- Keyboard nav (down/down/up/up/Escape) walked through fake results correctly; click-outside
  closes; invalid submit shows red border; submit button stays on one row with clear visible.
