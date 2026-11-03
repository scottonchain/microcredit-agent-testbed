# Direct reads after the network policy was opened (2026-11-03)

Claude Code (AI). On 2026-11-03 the operator opened the cloud environment's outbound network policy. This note records what that unblocked, read the same day from the environment itself. No contact, spend or deployment.

| Item that had been stalled | Source read | Result |
| --- | --- | --- |
| omnequa.org live check (DNS moved to GitHub Pages on 2026-11-03, PR 411) | https://omnequa.org/ and https://omnequa.org/try/ | HTTP 200, served by GitHub Pages (server header GitHub.com), page last modified 2026-11-03 17:19 UTC; the Try page links the app at https://scottonchain.github.io/microcredit-agent-testbed/ (200). The HTTP-to-HTTPS redirect cannot be checked from here (plain HTTP is not proxied); the "Enforce HTTPS" queue row stays |
| Roblox DevEx figures (evidence/lateral-decisions-20261103, operator queue row of 2026-11-03) | SEC 10-Q for the quarter ended 2025-06-30, FY2025 annual report, press release of 2025-09-05 on its Business Wire mirror, Game World Observer, Dexerto | Figures confirmed verbatim; queue row removed; README rows updated |
| Pension Credit campaign figure (third-idea brief of 2026-11-04) | https://www.cherwell.gov.uk/2025-PC-Success (published 2026-01-22) | "The total amount of benefits claimed was £399,939, with the average household receiving an additional £2,760 per year" |
| United States poverty guidelines (same brief) | https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines | 2026 guidelines read directly: 15,960 dollars for one person, 33,000 for four, in the 48 contiguous states and DC |
| PolicyEngine hosted API (same brief; offline packages had been used) | https://api.policyengine.org/us/metadata | Reachable, metadata version 2.2.1 |
| Dollar-rails fee sources (evidence/human-first-mainnet-20261103) | Coinbase developer FAQ and overview, onramp comparison page, PayPal fees, state small-loan pages | Read directly; one correction (MoonPay); appendix added to that README |

Still not reachable or not useful from here: sec.gov without a contact user agent (403), the corp.roblox.com newsroom path (404), sepolia.basescan.org (Cloudflare challenge), the GitHub Pages API (blocked by the proxy, not by the network policy), West Berkshire's site (403), PayPal help article 822 (403).
