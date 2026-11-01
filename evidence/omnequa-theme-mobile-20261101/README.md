# Mobile hardening patch for the November 1 Omnequa theme

Claude Code (AI), November 1, 2026. Marker: `THEME-MOBILE-b49d21b-20261101-r1`.
Existing action `action:omnequa-website-operate`. The operator reported that the
updated omnequa.org theme is not mobile friendly and asked that the computation
stay in this session while Codex applies the change to the Sites project. This is
one bounded local-source check and a source patch, not a live-site result.

## Decision, evidence sought, simpler route, stop condition

Decision: which change, if any, to the theme stylesheet makes the site usable on a
phone, so a reader on a 320 to 414 CSS px screen can read the navigation and
reach the journal. Human outcome: readers who arrive on phones can use the site;
nothing here changes the lending qualification (NONE QUALIFIES) or the revolving
first-job payment guarantee path in NORTH_STAR.md, and no spend, contact or
guarantee is involved.

Evidence sought: horizontal overflow, elements outside the viewport, navigation
font size and link height, text under 12 px and tap targets under 24 px, measured
on the exact theme source at 320, 360, 390, 414 and 768 CSS px.

Simpler route considered: do nothing and ask the operator for a screenshot. The
live host is unreachable from this container (proxy 403, DNS refused for the
fetch tool), so the operator's own view is still the only live evidence. The
patch was prepared anyway because the measured deficiencies are real on the
source and the fix is eight CSS edits.

Stop or change condition: if the operator's phone shows a defect this audit did
not reproduce (for example a stale cached stylesheet, or a page built from Sites
content that is absent from the GitHub backup), the live audit below should be run
by Codex against omnequa.org first and this patch should not be treated as the fix.

## Source and bound

Source: `scottonchain/microcredit-vision` main `b49d21b26d159f480137778cdd31c8b74a388992`,
directory `omnequa/theme/`. Its `assets/style.css` SHA-256 `cd8a75f7…` matches the
deployed-file hash in `omnequa/theme/evidence/theme-2026-11-01.json`, so the
backup is the deployed stylesheet as of that record. The site was rebuilt locally
with the theme's `tools/build.py` and `tools/theme.py` over the repository's
`content/` and `assets/`; `content/enterprise-research.html` and the Sites-only
archive normalization were not available, so the research page and the archived
October pages were not rendered. Chromium and Playwright already installed here;
localhost only; every non-local request aborted; no install, account, send, spend
or live request succeeded. Clock bounds 18:45Z to 19:00Z.

## Result on the unpatched theme

No horizontal overflow on any of 11 shell pages at 320, 360, 390, 414, 480, 600,
768, 820 and 1024 CSS px, and none on any of the 91 journal articles rendered
through `/journal/read/?slug=` at 320 and 390. The viewport meta tag is present on
all 29 built pages. The measured deficiencies are legibility and target size, not
layout breakage:

| Measure (home page) | 320 px before | 390 px before | after |
| --- | --- | --- | --- |
| Navigation font | 11 px | 12 px | 14 px |
| Navigation link height | 43 px | 44 px | 40 px, wraps to a second row below 390 px |
| Text under 12 px, all pages and widths | 489 | | 175 (uppercase labels at 11 px remain) |
| Tap targets under 24 px, all pages and widths | 550 | | 198 (inline text links remain) |
| Footer link height | 22 px | 22 px | 36 px |
| Hero heading at 768 px | 66 px in a two-column grid | | 53.8 px (`clamp(44px,7vw,66px)`) |

Raw numbers: `report-before.json`, `report-after.json`. Screenshots: `home-320-*`,
`home-360-after.png`, `home-768-*`.

## The patch

`style.css.patch` is a `git diff` against `omnequa/theme/assets/style.css` at
`b49d21b`; `git apply --check` passes. `style.css` is the full patched file
(SHA-256 `ae0046fe…`). `style-readable.diff` shows the same change with one rule per
line. `apply_patch.py` applies the eight edits to any copy of the stylesheet and
fails if an anchor string is not found exactly once. The edits:

1. `text-size-adjust:100%` on `html`, so iOS Safari does not inflate pixel text in landscape.
2. Tablet portrait (761 to 1100 px): hero heading `clamp(44px,7vw,66px)` instead of fixed 66 px.
3. Phone (760 px and below): navigation at 14 px, wrapping instead of a hidden horizontal scroller, links at least 40 px tall.
4. Phone: 12 px floor for eyebrows, card dates, feed note and archive dates; 13 px for "Read the story"; 11 px for uppercase index labels.
5. Phone: footer links 14 px with 6 px vertical padding (36 px targets), row gap reduced to keep the rhythm.
6. Removed the 380 px rule that shrank the navigation to 11 px.

Nothing else in the theme, builder, journal script, markup or content changes.
The theme's own `tools/test_focus.py` (3 tests) passes on the patched file and
`node --check assets/journal.js` passes; `tools/check.py` reports only the
missing Sites-only inputs noted above.

## Handoff to Codex

1. In the Sites checkout, apply `style.css.patch` to `assets/style.css` (or run
   `python3 apply_patch.py assets/style.css assets/style.css`), then run the
   theme's build and checks and deploy as usual. Update the file hash in
   `theme/evidence/theme-2026-11-01.json` and mirror the file to
   `omnequa/theme/assets/style.css` on vision main.
2. Before or after, run the live audit from a host that can reach omnequa.org:
   `node audit.cjs https://omnequa.org ./live-shots`. It prints, per page and
   width, the HTTP status, scroll width, overflow, navigation font, counts of
   small text and small targets, the viewport meta content and the stylesheet URLs,
   and writes `report.json` plus screenshots. If `navFont` is not 14px after
   deployment, the phone is still receiving the old stylesheet.
3. If the live run shows overflow or offenders that this local run did not, send
   that `report.json` and the screenshot back; the cause is then in Sites-only
   content or hosting, not in this stylesheet.

## Limitations

Local source only; no live page, real device, assistive technology, zoom or
WCAG claim. The operator's report of the defect remains unreproduced here. No
paid work, human earnings or funnel step results from this.
