# Human-first mainnet lane: research round one (November 3, 2026)

Claude Code (AI). Public sources read on 2026-11-03 through web search summaries (the session's network policy denies most of the primary hosts; primary URLs listed for the next round to read directly). Nothing here is a quote from a provider's live fee page; every figure is to be re-read before it prices anything. No contact, spend, account or deployment.

## A. Fiat to USDC for a borrower who never touches crypto

| Route | Fee and minimum as reported | Account or identity needed | Reading for a 0.25 dollar interest payment or a 10 dollar principal payment |
| --- | --- | --- | --- |
| Coinbase Onramp, hosted widget guest checkout (debit card, Apple Pay, no Coinbase account) | Retired June 30, 2026 per Coinbase's developer FAQ; earlier limit about 500 dollars a week; minimum about 5 dollars | None, while it existed | Gone |
| Coinbase Onramp, headless API | Card only, US only, up to 2,500 dollars a week, an access fee for the app; 2.5 percent card, 0.5 percent ACH per the FAQ; zero-fee USDC only for select partners | Coinbase app approval; borrower identity checks | 5 dollar minimum defeats interest-sized payments; works for principal at about 2.5 percent |
| MoonPay | About 3.99 percent with a 3.99 dollar minimum on cards; bank transfer 1 to 1.99 percent | Account and identity | A 0.25 dollar payment costs 3.99 dollars |
| Transak | 3.5 to 5.5 percent on cards | Account and identity | Same shape |
| Ramp Network | About 1.49 percent ACH, 2.9 to 3.9 percent card | Account and identity | Same shape |
| Kraken | 0.25 dollars plus 3.75 percent debit; ACH deposits held 7 days before withdrawal | Exchange account | Hold makes it useless for a due date |
| PayPal or Venmo PYUSD | No fee to buy, sell or send PYUSD; external transfer to Ethereum, Arbitrum, Solana (Base not listed); 1.5 percent on a transfer-and-sell | PayPal account | Needs a swap to USDC on Base; not a direct route |
| Stripe stablecoin acceptance | 1.5 percent, settles to the merchant's balance | Merchant account | The wrong direction: customers pay in stablecoin; useful only if the borrower already had USDC |
| Platform collects dollars and converts (option B) | Stripe card 2.9 percent plus 30 cents; ACH, Zelle, Cash App, Venmo near zero between people; Coinbase ACH 0.5 percent or free for account holders at the conversion step | The platform's accounts only; the borrower uses what they already have | The only route at 0 to 3 percent with no crypto exposure for the borrower |

**Finding (round one):** per-borrower on-ramps fail at interest-sized amounts because of fixed minimums and identity checks, and the only no-account route was retired in June 2026. The efficient route for a crypto-naive borrower is dollars in and dollars out at the platform, with conversion in batch on the platform's side, plus interest deducted at disbursement so a first loan needs no separate interest payment at all. That moves the question to the law: the platform becomes the collector of dollars and the converter.

## B. Lending to people in the United States

- There is no federal usury ceiling; each state sets caps and licensing for small unsecured loans. One 2026 summary counts 19 states plus the District of Columbia with caps of 17 to 36 percent APR and two states with none. Many states prohibit unlicensed lending; some use an unconscionability standard but still license.
- The CFPB said in 2025 it would not prioritise enforcement of its small-dollar rule; state enforcement of disclosure, unfair-practice and usury statutes is expected to rise.
- A crypto-collateralised comparator (Coinbase borrowing USDC through Morpho) is offered state by state; the licensing structure was not described in the sources read. Nothing read addresses unsecured USDC-denominated consumer loans or whether a protocol operator is a lender under state licensing law.
- Reported (vendor sources): CFPB Circular 2026-03 of May 5, 2026 requires specific, accurate adverse-action reasons under ECOA and Regulation B however complex the model; the EU AI Act's high-risk obligations for creditworthiness assessment apply from August 2, 2026.

**Finding:** the lender-of-record claim in the model (`claim:lender-of-record-required`) stands and widens: licensing, rate caps and adverse-action reasons all attach to whoever lends, and the trust interview makes the adverse-action rule concrete. These are counsel questions; the team drafts the brief and the operator names the jurisdiction and engages counsel.

## C. Conversational credit assessment

Nothing read describes an interview-style assessment for thin-file borrowers. The 2026 vendor and academic material converges on one architecture: the language model extracts and informs, a scoring model with pre-validated factor categories decides and supplies the reasons, and proxies for protected characteristics are the recurring failure (a 2025 Massachusetts settlement over a college default-rate variable is cited). That is the reviewed officer design already in this repository, so the interview is an intake layer on it, not a new scorer.

## Sources

| Topic | Source |
| --- | --- |
| Coinbase Onramp FAQ (guest checkout retirement, fees, headless) | https://docs.cdp.coinbase.com/onramp/additional-resources/faq |
| Coinbase Onramp overview | https://docs.cdp.coinbase.com/onramp/onramp-overview |
| On-ramp comparison 2026 (secondary) | https://eco.com/support/en/articles/15210390-best-stablecoin-onramps-2026-moonpay-transak-coinbase-onramp-compared |
| On-ramp true cost comparison (secondary) | https://www.benpay.com/blog/index.php/fiat-to-usdt-usdc-onramps-true-cost/ |
| Stripe stablecoin payments (secondary) | https://eco.com/support/en/articles/15083174-stripe-stablecoin-payments-2026 |
| PayPal crypto transfers (PYUSD networks, limits) | https://www.paypal.com/cshelp/article/help822 |
| PayPal consumer fees | https://paypal.com/fees |
| Venmo crypto transfers | https://help.venmo.com/hc/en-us/articles/16145303480595-Crypto-Transfers |
| Payday and small-dollar lending overview (Mondaq) | https://www.mondaq.com/unitedstates/dodd-frank-consumer-protection-act/1768580/payday-and-small-dollar-lending |
| Usury laws by state 2026 (secondary) | https://www.paidnice.com/usury-laws-by-state |
| Small-loan laws 2026 state by state (secondary) | https://www.rentbottomline.com/blog/small-loan-laws-in-2026-what-changed-state-by-state-and-why-where-you-live-matters-more-than-ever |
| Adverse action and language models (vendor) | https://www.respan.ai/resources/adverse-action-llm |
| AI credit scoring review (JRFM 2026) | https://mdpi-res.com/d_attachment/jrfm/jrfm-19-00104/article_deploy/jrfm-19-00104.pdf |
| Stablecoin micro-lending research note (secondary) | https://www.spark.money/research/stablecoin-micro-lending-unbanked-access |

## Round two (for the routine)

1. Read the primary fee pages directly where the environment allows; otherwise queue the hosts.
2. Stripe and Bridge dollar-to-USDC conversion for a platform: fees, minimums, KYC on the platform, payout to a Base address, payouts in dollars (cash-out).
3. Coinbase business account: ACH in, USDC out to Base, fees, limits, timing.
4. Money-transmission treatment of collecting one's own receivables and converting them, by state; what Kiva's US zero-interest model and a nonprofit lender exemption would change.
5. The cash-out side at pilot amounts: instant payout fees versus ACH.
6. A measured sandbox round trip (Stripe test mode plus Base Sepolia) with every fee written down.
