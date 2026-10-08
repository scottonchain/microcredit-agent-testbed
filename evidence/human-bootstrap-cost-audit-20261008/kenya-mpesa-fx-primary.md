# Kenya M-PESA / FX primary-source audit

Codex research subagent; observed 2026-10-08 03:50 UTC. Read-only web research. No account access, contact, purchases, wallets, keys, or transactions.

**Result:** A USD25-sized illustration lands in the KES2,501–3,500 band. A conditional business-to-wallet disbursement plus Paybill repayment costs KES34 across the parties before provider charges; prepaid agent withdrawal adds KES52. These are tariff calculations, not an executable USDC/mobile-money quote. Current consumer P2P charges remain unverified from the primary tariff page.

## Dated exchange-rate anchor

CBK's bulletin dated **2 October 2026**, page 1 and Table 1 on page 2, records **KES129.71 per USD on 1 October 2026**. The PDF was directly fetched. Thus, assuming 1 USDC = USD1 solely for illustration, 25 USDC × 129.71 = **KES3,242.75**. A quoted integer payout of KES3,243 would fall in the same band but is not promised here. The observation is neither today's executable bid/ask nor a provider's USDC conversion rate. [Official CBK bulletin](https://www.centralbank.go.ke/uploads/weekly_bulletin/1967256963_Weekly%20CBK%20Bulletin%202%20October%202026.pdf).

## Applicable published rail components

The following figures were retrieved from search-indexed **official Safaricom PDFs**. Fresh direct opens returned 403, so no current signed tariff, original PDF hash, or executable pricing response was obtained. Their visible contents have no explicit effective date. A dated source observation does not establish that these figures remain binding for a particular account.

| Conditional operation, KES2,501–3,500 | Customer KES | Business KES | Aggregate KES |
|---|---:|---:|---:|
| Registered M-PESA B2C receipt | 0 | 9 | 9 |
| B2C with business-prepaid withdrawal | 0 | 9 + 52 | 61 |
| Paybill Customer Bouquet | 25 | 0 | 25 |
| Paybill Business Bouquet | 0 | 25 | 25 |
| Paybill Mgao | 16 | 9 | 25 |

Sources: [B2C tariff form](https://www.safaricom.co.ke/images/Downloads/B2C-Tariff-Form.pdf), [Paybill standard tariff guide](https://www.safaricom.co.ke/images/Downloads/M-Pesa-Paybill-Tariff-guide.pdf). Receiving charge zero here is specific to the registered B2C tariff, not a promise that a remittance provider is free. KES52 is the published prepaid-withdrawal component, not an independently fetched current consumer cashout quote. Do not add it again when already included in KES61.

## Two conditional round trips

**Wallet use:** disburse KES3,242.75 by the registered B2C route; retain/use wallet money; repay into a Paybill in the same band. Aggregate published components are 9 + 25 = **KES34 ≈ USD0.2621**, or **1.0485%** of the assumed USD25 principal. Allocation varies by Paybill tariff; Customer Bouquet means the borrower needs the return amount **plus KES25** in the wallet. The provider's actual Paybill and tariff have not been identified.

**Cash use:** choose the business-prepaid withdrawal variant and subsequently make the same-band Paybill repayment. Aggregate components are 61 + 25 = **KES86 ≈ USD0.6630**, or **2.6521%**. Cash business proceeds must reach the wallet before repayment; redeposit availability, applicable charges, cash denomination, ID and agent cash/float remain execution checks. This example does not assume free redeposit or invent a receiving fee.

At illustrative **1% interest**, add KES32.4275, making the minimum arithmetic hurdle KES66.4275 for wallet use or KES118.4275 for cash use, **before** USDC transfer gas, conversion spread in each direction, off/on-ramp fees, operating expenses, taxes, losses or currency movement. This is a cost floor under the stated choices, not a profitability forecast.

## Limits, operational prerequisites and unresolved inputs

Safaricom's **21 September 2023** release states KES250,000 per transaction and KES500,000 daily/account limits, following the August 2023 increase. It is historical primary evidence; a fresh account-limit check is still needed. [Official limit announcement](https://www.safaricom.co.ke/media-center-landing/press-releases/safaricom-gets-approval-to-increase-m-pesa-transaction-limits-to-ksh-250-000).

Safaricom's withdrawal instructions require identification and checking agent funds availability. This is a human cash interface, not an autonomous agent-controlled bank account. [Official transaction instructions](https://www.safaricom.co.ke/main-m-pesa/m-pesa-services/transactions/deposit-at-agent).

The primary consumer tariff pages returned 403. The widely reposted KES53 consumer P2P figure was **not accepted as verified**. P2P-return economics therefore use an unknown fee variable. Likewise, no Eversend or Kotani fee, supported Base-USDC route, customer eligibility, repayment routing or spread was established by this audit. Obtain actual two-way quotes and recipient consent before treating any human-serving path as executable. A wallet or cash round trip alone creates no income; bootstrap requires a real paid activity whose margin exceeds the complete cost.
