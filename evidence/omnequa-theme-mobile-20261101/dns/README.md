# DNS move for omnequa.org: GitHub Pages replaces the Sites host

Claude Code (AI), November 3, 2026. Operator direction in session: Codex's
tokens are gone, so the Sites project can no longer be deployed; the operator
asked Claude to handle the website update, enabled GitHub Pages on
`scottonchain/microcredit-vision` (branch `gh-pages`, custom domain omnequa.org)
and supplied a GoDaddy personal access token as a network secret. This reopens
the DNS work that the website action's stop conditions name; it is recorded here
as operator-directed, not as an autonomous decision.

## State before any write

`zone-before-20261103.json` (and `zone-current.json`, the copy the script checks
against): the complete zone read through the GoDaddy Domains v3 API on
2026-11-03 (two independent reads, 22 records, identical to Codex's
`operations/omnequa-dns-20261013/after.json` in the vision repository). No
credential appears in this folder; the API token is injected by the session
proxy and never written to disk.

## Planned writes (`apply_dns.py`)

| Record | Change |
| --- | --- |
| A `@` 162.159.143.30 | replace with 185.199.108.153 |
| A `@` 172.66.3.26 | replace with 185.199.109.153 |
| A `@` | add 185.199.110.153 and 185.199.111.153 |
| CNAME `www` | custom-domains.chatgpt.site. to scottonchain.github.io. |
| TXT `_openai-site-verification`, `_cf-custom-hostname`, `_openai-site-verification.www`, `_cf-custom-hostname.www` | delete |

Mail and Microsoft records (MX, SPF, DMARC, autodiscover, lync, sip, msoid, SRV),
NS, SOA, `_domainconnect` and the `email` CNAME are not touched. The script
re-reads the zone before every write, stops if any untouched record differs,
looks up the current record ID each time (October showed IDs can change during a
run), stops on any non-2xx response, logs every request and response without
credentials to `write-results.json`, and saves the final zone as `zone-after.json`.

## Status

The first run on 2026-11-03 (about 16:58Z) was refused by Claude Code's auto-mode
permission classifier ("DNS / Domain / Cert Changes") before any request was sent.
The operator then switched the session out of auto mode and said "run it". At
17:06Z the script's opening guard stopped it: the zone no longer matched the
snapshot. `zone-after-20261103.json` is that read: 20 records, with every planned
change already present (four GitHub A records at the apex, www CNAME to
scottonchain.github.io, the four Sites TXT records gone) and the 15 untouched
records identical to the snapshot including their record IDs. The script wrote
nothing; the changes were made outside this session between the 05:1xZ snapshot
and 17:06Z. The operator attributes them to another session; none of the
operator's ten most recent cloud sessions was active on November 3, so the
route is not identified here. GitHub's Pages settings showed "DNS Check in
Progress" and "Enforce HTTPS" unavailable at 17:2xZ, the normal state before
the certificate issues.

Live check at 17:09Z: https://omnequa.org and https://www.omnequa.org both reach
GitHub Pages, which still presents its `*.github.io` certificate, so the custom
domain certificate is pending; the site serves once GitHub issues it and
"Enforce HTTPS" can then be enabled in the repository's Pages settings. Plain
HTTP cannot be tested from this container.

## Verified on GitHub Pages, 17:41Z

- https://omnequa.org/ answers HTTP 200 from `server: GitHub.com` with a certificate
  issued for omnequa.org; https://www.omnequa.org/ answers 301 to the apex.
- `/style.css` is the patched stylesheet plus 523 bytes appended by a later
  gh-pages commit from another Claude session (8e72341, 17:18Z, a `/try/`
  walkthrough page and the removal of the previous host's injected script). All
  eleven mobile edits are present in the served file.
- Live phone audit (`report-live-github-pages-20261103.json`), 11 routes at 320
  and 390 px: no page scrolls sideways, navigation 14 px on every page, research
  page document width equals the viewport. Remaining out-of-viewport elements are
  table cells inside the analytics and research scroll regions. `/try/` also
  fits at both widths.
- Still to do by the operator: tick "Enforce HTTPS" in the repository's Pages
  settings now that the certificate exists.
