import sys,pathlib
src=pathlib.Path(sys.argv[1]); css=src.read_text()
edits=[
 # iOS Safari inflates px text in landscape unless text-size-adjust is pinned.
 ("html{scroll-padding-top:24px}","html{scroll-padding-top:24px;-webkit-text-size-adjust:100%;text-size-adjust:100%}"),
 # Tablet portrait (761 to 1100): the two-column hero kept the 66px desktop heading.
 (".hero h1{font-size:66px}",".hero h1{font-size:clamp(44px,7vw,66px)}"),
 # Phone nav: 12px text in a hidden horizontal scroller becomes 14px links that wrap, each at least 44px tall.
 (".site-header nav{justify-content:space-between;gap:8px;margin-top:16px;font-size:12px;overflow-x:auto}",
  ".site-header nav{justify-content:flex-start;flex-wrap:wrap;gap:0 18px;margin-top:4px;font-size:14px;overflow:visible}"),
 (".site-header nav a{padding:10px 0 14px}",".site-header nav a{padding:8px 0;min-height:40px;display:inline-flex;align-items:center}"),
 # Phone small text floor of 12px for labels and captions; 13px for the card read-more.
 (".hero-art figcaption{font-size:10px;margin-top:8px}",".hero-art figcaption{font-size:11px;margin-top:8px}"),
 (".hero-footnote{font-size:11px}",".hero-footnote{font-size:12px}.eyebrow,.post-card .eyebrow,.feed-note,.archive-list time{font-size:12px}.read-more{font-size:13px}.explainer-grid span,.site-footer .eyebrow,.quick-facts dt{font-size:11px}"),
 # Footer links: 22px tall targets become 36px with the same visual rhythm.
 (".footer-links{gap:14px 24px}",".footer-links{gap:2px 24px;font-size:14px}.footer-links a{display:inline-block;padding:6px 0}"),
 # Remove the 380px rule that shrank nav text to 11px.
 ("@media(max-width:380px){.site-header nav{font-size:11px}","@media(max-width:380px){"),
]
for old,new in edits:
    n=css.count(old); assert n==1,(n,old)
    css=css.replace(old,new)
pathlib.Path(sys.argv[2]).write_text(css); print('applied',len(edits),'edits;',len(css),'bytes')
