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

The first run on 2026-11-03 was refused by Claude Code's auto-mode permission
classifier ("DNS / Domain / Cert Changes") before any request was sent. No DNS
record has been changed by this record. Receipts are added here when the writes
run.
