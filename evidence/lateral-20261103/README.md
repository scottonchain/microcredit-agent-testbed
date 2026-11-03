# Daily lateral run, November 3, 2026: N1 and F9 receipts, attestation specification, stale-action sweep

Claude Code (AI), the daily lateral-register run (first run in the repository-attached session; the November 2 fresh-session run lost its receipt to a 403 push). Public sources only; no contact, spend, account or deployment. Read on November 3 through the session proxy (curl) where the host allowed it; Upwork's pages return 403 to the proxy, so the Upwork facts come from Upwork's own text as quoted in search summaries [secondary]. Prolific's pages were read directly [primary].

## Receipt 1 (N1, verifiable skill signals): partner terms of the credential channel

**Test (from the register):** retrieve the partner terms of Upwork's Partner Certified Talent programme and write the attestation specification from the contract's events. The November 2 run classified this as a lead; that receipt was lost. Re-run today.

**Found [secondary, Upwork's own wording via search summaries; support.upwork.com and upwork.com/partner-certification return 403 to this session]:**
- Being Partner Certified "means you've completed a certification from one of Upwork's trusted partners, and that certification has been verified and added to your profile"; the badge "shows across profiles and proposals"; after a credential is completed it "is automatically sent to Upwork" and the freelancer claims it.
- Upwork "selects partners based on their credibility, industry recognition, and alignment with the skills clients are most actively hiring for"; the partner-portal help says to "work with the Upwork partnerships team if certification is required". No published application, criteria list or fee for a would-be issuer was found.

**Classification: bound.** The channel exists and does display third-party credentials where hiring happens, which is the mechanism N1 needs. But the issuer side is closed to an unknown organisation: Upwork chooses its partners by existing reputation and there is no public door. The hypothesis `hyp:verifiable-skill-signal-20261101` prediction 1 ("partner terms admit an issuer without prior certifying reputation, or name what such an issuer must show") meets its disconfirming observation as far as the public record goes. **Score:** execute 2 to 1 (the test now needs a partnership this team cannot enter); total 13 to 12. **Re-entry:** an existing Upwork partner (a training provider or certifier) willing to carry a completed-work attestation as part of its own credential; or Upwork publishing issuer terms. Until then N1's value is the attestation itself, usable on any channel that reads a public record.

**Attestation specification (what the pool can attest from its own events, without a partner):**

| Field | Source event in the pool | Verifiable by |
| --- | --- | --- |
| Loans repaid on time, count and total principal | loan origination and repayment events | anyone, from the chain |
| Days late, if any; defaults: none or count | repayment timestamps against due dates | anyone |
| Backed by a named person's stake at origination | backing event | anyone (backer pseudonymous) |
| Purpose category of each loan (business input, stock, tool) | the lender's record, borrower opt-in | the lender of record signs |
| Issuer | the lender of record's key | signature check |
| Subject | the borrower's chosen public key, linked to a profile only by the borrower | the borrower controls disclosure |

Form: a signed JSON document (issuer, subject key, period, the six fields, chain and contract address, issuance time), verifiable by recomputing the events from the chain and checking the signature. It states only what happened on the pool; it makes no claim of skill. It is the same artefact a partner would consume if one ever appears, and it costs nothing to issue. It does not yet exist; it becomes a D16 operations item once the first real loans exist, and it stays opt-in.

## Receipt 2 (F9, paid human evaluation bought by the agent economy): a panel's public terms and price

**Test (from the register):** price our own verification need against a panel's public terms and record whether a disclosed-AI buyer is permitted.

**Found [primary: Prolific's payment principles and pricing pages, read November 3]:**
- "Our minimum rate is £6 / $8 per hour … We recommend paying at least £9 / $12 per hour."
- "For pay-as-you-go pricing, our platform fee is usually 42.8% for corporate customers, and a discounted 33.3% for academic or non-profit customers."
- Prolific's "100% Human Guarantee" and its February 2026 bot authenticity checks are aimed at AI agents posing as participants; nothing read addresses an AI-operated buyer account, and the researcher terms page was not reachable (404 at the published path). The buyer side is therefore unaddressed in public text, not permitted and not forbidden.

**Price of our own need:** one independent receipt check of fifteen minutes at the recommended 12 dollars an hour is a 3.00 dollar reward plus 1.28 dollars fee (corporate) or 1.00 dollar (nonprofit): about 4 to 4.30 dollars a check. The team's own need, about three hours a month (from the November 3 B10 demand-trace audit), prices at roughly 50 dollars a month.

**Classification: bound.** The panel route is priced and the floor is public; a disclosed-AI buyer is neither admitted nor excluded in the text found; the team's own demand is a demand trace of about 50 dollars a month, which is real but too small to be the market F9 needs. The path's value depends on outside agent operators buying judgment, which this receipt cannot show. **Score:** unchanged (2, 2, 3, 2, 3 = 12). **Next cheapest test (on a later run):** read the researcher terms by another route (curl to the terms URL from a different path, or Hermes from its host) for an organisation and automation clause; and count public agent-economy buyers of human evaluation (bounties, rubric panels) as a demand trace that is not ours.

## Decisions first (rule 1 and rule 9)

No register or direction date falls today after the November 3 selection decided earlier in the day. Rule 9 sweep of world-model actions past due by more than seven days (21 found): each is cancelled with its reason and re-entry condition in its stop conditions, marked done where its evidence shows the deliverable, or re-dated with an owner who holds it. Table:

| Action | Disposition | Reason and re-entry |
| --- | --- | --- |
| human-agent-discovery-sync, sepolia-prototype-sync, credit-officer-sync, prime-directive-sync, hermes-field-brief, codex-show-diff | cancelled | Sync agendas for October meetings that passed; the syncs themselves were stopped by the October 16 repair instruction. Re-entry: a new sync names the item. |
| aml-safeguards-design | done | Superseded and answered by the D16 legal analysis (OFAC screen; no AML program rule for a non-mortgage lender). |
| codex-independent-bootstrap-candidate-review, bootstrap-acceptance-by-next-sync, bootstrap-candidate-by-next-sync, bootstrap-candidate-testnet-execution, krock-card, bot-job-board-created-demand | cancelled | The BOOTSTRAP-001 commercial experiment was closed by the operator on October 28 (issue 17). Evidence retained. Re-entry: a replacement experiment under the October 28 self-sustaining rule. |
| daily-audio-discussion-post | cancelled | Repetitive publication stopped October 16; blog routines paused by the operator November 2. Re-entry: the operator resumes the blog routines. |
| email-pilot-researchers | done | Its bounded sends and replies are in its evidence; the window closed. |
| hermes-outside-demand-ledger-20261008 | done | The ledger returned (22 evidence rows); the November 1 stop records the result. |
| human-pilot-partner-and-site | cancelled | Superseded by D8 (parked) and D16 (Colorado first, lender of record named). Re-entry: D8's partner or D16's state expansion. |
| transitive-conservation-theorem | done | Theory repository PR 14 merged (board 15, November 1 manifest). |
| techne-watch-stop-card | cancelled | The watched card's window passed; nothing on it. Re-entry: a new card. |
| omnequa-website-operate | re-dated, owner claude | Website operation passed to the Claude steward under the execution-owner toggle (PR 411 DNS, PR 47 walkthrough); due 2026-12-01 with the steward's daily receipts as evidence. |
| pool-funding-20261019 | cancelled | The October 20 scenarios passed; the testnet pool is now funded by the D7 drip workflow. Re-entry: D7 gate 5 (the operator's reserve). |

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| C4 / D12 human-first lending on one order | November 1 request sent; no reply by the November 2 gate | November 8 18:00 UTC: Claude records the disposition |
| C1 / D6 virtual worlds | November 3 bound (payout concentration); PARKED | re-entry only |
| B10 agent as employer | November 3 audit; PARKED (L3) | operator queue row (seed and payout route) or an independent payer |
| C2 ACP | one indexed settlement, payer unknown | November 8 18:00 UTC: Claude decides on the Hermes trace or NONE |
| N1 skill signals | today's bound (issuer door closed) | attestation becomes a D16 operations item at first real loans |
| F9 human evaluation | today's bound (price 4 dollars a check; buyer side unaddressed) | next run: researcher terms by another route; outside-buyer count |
| N2 rules-as-code | parked at its stop | November 4: candidate selection decision (next run) |
| D16 human-first mainnet | legal analysis merged (PR 418); rails round two (PR 416) | November 10, 17, 24 rows in the D16 lane |

## Sources

| Item | URL | Read |
| --- | --- | --- |
| Upwork, What is the Partner Certified Talent program | https://support.upwork.com/hc/en-us/articles/41175146350995-What-is-the-Partner-Certified-Talent-program | secondary (403 to the proxy); Upwork's wording via search summary |
| Upwork partner certification page | https://www.upwork.com/partner-certification | secondary (403) |
| Upwork, How to become an Upwork partner expert | https://support.upwork.com/hc/en-us/articles/28973308900243-How-to-become-an-Upwork-partner-expert | secondary |
| Prolific payment principles | https://researcher-help.prolific.com/en/articles/445230-prolific-s-payment-principles | primary |
| Prolific pricing | https://www.prolific.com/pricing | primary |
| Prolific 100% Human Guarantee | https://researcher-help.prolific.com/en/articles/624524-what-is-the-100-human-guarantee | primary |
| Prolific CEO open letter on AI agents | https://www.prolific.com/resources/ai-agent-debate-open-letter-by-ceo-phelim-bradley | secondary (search summary) |
