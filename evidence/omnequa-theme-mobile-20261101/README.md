# Live mobile audit and stylesheet patch for the Omnequa theme

Claude Code (AI), November 1 to 3, 2026. Marker: `THEME-MOBILE-live-20261103-r2`.
Existing action `action:omnequa-website-operate`. The operator reported that the
updated omnequa.org theme is not mobile friendly, asked that the computation stay
in this session, and said Codex applies the change to the Sites project. Revision
r2 replaces the November 1 local-only record: the host was allowed on November 3
and the live site was measured directly.

## Decision, evidence sought, simpler route, stop condition

Decision: which stylesheet change makes omnequa.org usable on a phone, so a
reader on a 320 to 414 CSS px screen can read the navigation and every page
without sideways scrolling. Human outcome: phone readers can use the site.
Nothing here changes the lending qualification (NONE QUALIFIES) or the revolving
first-job payment guarantee path in NORTH_STAR.md; no spend, contact or
guarantee is involved.

Evidence sought: horizontal page overflow, elements outside the viewport,
navigation font size and link height, text under 12 px and tap targets under
24 px, measured on the live pages at 320, 360, 390, 414 and 768 CSS px, before
and after the patch.

Simpler route considered: fix only the one page that scrolls sideways. Rejected
because the navigation on every page is 11 px at 320 px and 12 px at 390 px,
which is the defect a reader meets first.

Stop or change condition: if Codex's build or the Sites checkout no longer
contains one of the eleven anchor strings, `apply_patch_live.py` stops without
writing and the patch must be re-based on the current file. If the live audit
after deployment still reports `navFont=11px` or `overflow=true`, the deployed
file is not the patched one.

## What is live, and how it differs from the GitHub backup

The live stylesheet (22,249 bytes, SHA-256 `49265e1c…`, fetched 2026-11-03
between 05:05Z and 05:17Z, served by Cloudflare with `max-age=0, must-revalidate`) is a superset of
the vision backup `omnequa/theme/assets/style.css` at `b49d21b`
(15,761 bytes, `cd8a75f7…`): the first 275 rules are identical and 108 rules were
appended for the analytics page, the forecast article and a six-link navigation
(Analytics was added). The backup is therefore stale and was not patched; the
patch here targets the live file. `live/style-live-20261103.css` is the exact
fetched copy.

## Result on the live site before the patch

Measured with the pre-installed Chromium and Playwright, phone emulation,
viewports 320, 360, 390, 414 and 768 CSS px, eleven routes including the
analytics, research and one article page. `live/report-live-before.json` holds
every number; screenshots are in `live/`.

| Finding | Where | Measure |
| --- | --- | --- |
| Page scrolls sideways | `/research/agent-operated-businesses/` | document scroll width 440 px at 320, 360 and 414 px viewports, 441 at 390: a bare table in `.prose` has no overflow rule (the `.article table` rule does not reach it) |
| Data tables clipped | `/analytics/` | three tables forced to 480 px inside a 316 px scroll region at 390 px, so the last column is hidden until the reader scrolls the region; 42 to 57 elements outside the viewport |
| Navigation unreadable | every page | 11 px at 320 and 360 px, 12 px at 390 and 414 px; six links wrap to two rows |
| Small text | every page | 489 text elements under 12 px across the run (eyebrows, dates, captions) |
| Small targets | every page | footer links 22 px tall; 550 targets under 24 px across the run |
| Tablet hero | `/` at 768 px | 66 px heading in a two-column grid |

The viewport meta tag is present on every live page, and the home, journal,
article, about, history, work, newsroom, contact and privacy pages do not
overflow. The problem is the two content pages above plus legibility.

## The patch

`live/style.patch` is a unified diff from the live file to `live/style-patched.css`
(SHA-256 `24a55440…`); `live/style-readable.diff` shows the same change one rule
per line. `apply_patch_live.py <in> <out>` applies the eleven edits and stops if
any anchor is not found exactly once:

1. `text-size-adjust:100%` on `html`.
2. Tablet (761 to 1100 px): hero heading `clamp(44px,7vw,66px)`.
3. Phone (760 px and below): navigation at 14 px, wrapping, links 40 px tall; the 380 px rule that shrank it to 11 px is removed; the appended six-link rule is aligned to the same sizes.
4. Phone: 12 px floor for eyebrows, card dates, feed note, archive dates, analytics jump links, chart captions and origin titles; 13 px for "Read the story"; 11 px for uppercase index labels, evidence tags and decision-note terms.
5. Phone: footer links 14 px with 6 px vertical padding (36 px targets).
6. `.prose table` gets the same block-and-scroll rule as `.article table`, which ends the sideways page scroll on the research page.
7. `.data-content table{min-width:480px}` becomes `min-width:0`: the three analytics tables have three or four columns and fit a phone.

No markup, builder, journal script or content changes.

## Result on the live site with the patch

Verified by loading the live pages with the patched stylesheet substituted for
`/style.css` at request time (`CSS_OVERRIDE` in `audit.cjs`), same viewports and
routes. `live/report-live-after.json`:

| Measure | before | after |
| --- | --- | --- |
| Pages with sideways scroll (55 page-width pairs) | 4 | 0 |
| Research page document width at 390 px | 441 | 390; table 350 px wide |
| Analytics tables at 390 px | 480 px each in a 316 px region | 316, 378 and 316 px; two fit, one scrolls inside its region |
| Navigation font at 320 and 390 px | 11 px, 12 px | 14 px |
| Text under 12 px, whole run | 489 | 175 (11 px uppercase labels remain by choice) |
| Targets under 24 px, whole run | 550 | 198 (inline text links remain) |
| Hero heading at 768 px | 66 px | 53.8 px |

Screenshots: `live/home-320-{before,after}.png`,
`live/research-table-390-{before,after}.png`,
`live/analytics-table-390-{before,after}.png` (details opened for the capture),
`live/research_agent-operated-businesses-390-{before,after}.png`,
`live/analytics-390-{before,after}.png`.

## Handoff to Codex

1. In the Sites checkout run `python3 apply_patch_live.py assets/style.css assets/style.css`
   (or apply `live/style.patch`), then the theme's build and checks, then deploy.
   Mirror the result to `omnequa/theme/assets/style.css` on vision main and update
   the file hash in `theme/evidence/theme-2026-11-01.json`; the backup there is
   already behind the live file.
2. After deployment run `node audit.cjs https://omnequa.org ./live-shots` from any
   host with Playwright. Expected: `overflow=false` on every row, `navFont=14px`
   at every width, and the research page at scroll width equal to the viewport.
3. `node tables.cjs <outdir>` reproduces the table measurements and screenshots
   if the two content pages need a second look.

## Limitations

Chromium emulation on live pages, not a physical device, assistive technology,
zoom or WCAG claim. The analytics four-column table still scrolls inside its
labelled region on phones narrower than about 420 px. Eleven routes were measured;
archived October pages and the forecast article were not. No paid work, human
earnings or funnel step results from this.
