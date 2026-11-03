"""Apply the phone-legibility and table edits to the live omnequa.org stylesheet.
Usage: python3 apply_patch_live.py <input style.css> <output style.css>
Each anchor must occur exactly once; otherwise the script stops without writing."""
import sys,pathlib
css=pathlib.Path(sys.argv[1]).read_text()
edits=[
 # iOS Safari inflates pixel text in landscape unless text-size-adjust is pinned.
 ("html{scroll-padding-top:24px}","html{scroll-padding-top:24px;-webkit-text-size-adjust:100%;text-size-adjust:100%}"),
 # Tablet portrait (761 to 1100 px): the two-column hero kept the 66 px desktop heading.
 (".hero h1{font-size:66px}",".hero h1{font-size:clamp(44px,7vw,66px)}"),
 # Phone navigation: 12 px text becomes 14 px; the later live rule already wraps the six links.
 (".site-header nav{justify-content:space-between;gap:8px;margin-top:16px;font-size:12px;overflow-x:auto}",
  ".site-header nav{justify-content:flex-start;flex-wrap:wrap;gap:0 18px;margin-top:4px;font-size:14px;overflow:visible}"),
 (".site-header nav a{padding:10px 0 14px}",".site-header nav a{padding:8px 0;min-height:40px;display:inline-flex;align-items:center}"),
 # Phone small-text floor: 12 px for labels, dates and captions; 13 px for the card read-more.
 (".hero-art figcaption{font-size:10px;margin-top:8px}",".hero-art figcaption{font-size:11px;margin-top:8px}"),
 (".hero-footnote{font-size:11px}",".hero-footnote{font-size:12px}.eyebrow,.post-card .eyebrow,.feed-note,.archive-list time,.analytics-jumps,.chart-column figcaption,.origin-title{font-size:12px}.read-more{font-size:13px}.explainer-grid span,.site-footer .eyebrow,.quick-facts dt,.evidence-tag,.decision-notes dt{font-size:11px}"),
 # Footer links: 22 px tall targets become 36 px.
 (".footer-links{gap:14px 24px}",".footer-links{gap:2px 24px;font-size:14px}.footer-links a{display:inline-block;padding:6px 0}"),
 # Remove the 380 px rule that shrank the navigation to 11 px.
 ("@media(max-width:380px){.site-header nav{font-size:11px}","@media(max-width:380px){"),
 # The live rule appended for the six-link nav: keep its wrap, align its sizes with the edit above.
 (".site-header nav a{padding:10px 0;min-height:44px}",".site-header nav a{padding:8px 0;min-height:40px}"),
 # Research page: a bare table inside .prose made the whole page scroll sideways (scrollWidth 440 at 320 to 414 px).
 (".article table{font-size:13px;display:block;overflow:auto;max-width:100%}",".article table,.prose table{font-size:13px;display:block;overflow:auto;max-width:100%}"),
 # Analytics data tables have three columns and fit a phone; the forced 480 px width only hid the last column.
 (".data-content table{min-width:480px}",".data-content table{min-width:0}"),
]
for old,new in edits:
    n=css.count(old)
    if n!=1: sys.exit(f"anchor found {n} times, stopping: {old[:80]}")
    css=css.replace(old,new)
pathlib.Path(sys.argv[2]).write_text(css); print('applied',len(edits),'edits;',len(css),'bytes')
