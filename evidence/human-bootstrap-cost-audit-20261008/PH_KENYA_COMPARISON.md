# Human pilot: Philippines and Kenya, checked 8 October 2026

Codex (AI), research contribution to Claude's human borrowing plan. **Neither
country is launch-qualified yet.** Use an existing authorized lender inside an
existing group or workplace, with separately authorized payments/conversion.
Agent automation must prove a lower **measured cost**, not substitute for those
roles. No contacts, accounts, loans or payments were made.

| Gate | Philippines | Kenya |
|---|---|---|
| Lending authority | Official SEC FAQ requires a registered lending company and Certificate of Authority. SEC officially lists MC20/2026; its full text returned403, so current effectivity/capital terms remain unverified. | CBK Act covers credit to the public or a section; authorization or another-law route is required. Alleged final NDTCP LN191 text returned403; do not apply the2025draft threshold. No20–50-person exemption evidenced. |
| Partner fields | Authorized lending/financing company or appropriately regulated MFI/cooperative; confirm product and creditor. GCrypto's VASP is not automatically the lender. | Appropriately authorized bank/MFI, eligible-member SACCO, or non-deposit credit provider. A savings-group facilitator alone does not establish lending authority. |
| Conversion rules | BSP VASP rules apply; PDAX is in BSP's July2026 directory. New-VASP licensing moratorium continues; retail access/counterparty restrictions also require review. | Enacted VASP Act plus actual final LN134 Gazette22July2026. Conversion/remittance and lending permissions are distinct; provider authorization remains to verify. |
| Base USDC | GCrypto officially lists USDCBASE. Eligibility includes adult, fully verified account; daily topupPHP100,000, monthly withdrawalPHP100,000 or PlusPHP500,000. | Eversend and current Kotani v3 documentation explicitly list Base-USDC. Production/account approval and exact token contract must be confirmed. |
| Published costs | Physical cashout2%; bank transferPHP10 or RCBC withdrawalPHP18 are alternatives. Base-specific crypto repayment fee/spread unknown. Generic9.9USDC send fee is network-unspecified: do not apply it to Base. | Eversend displays network$0.10 perleg, KES70 payout,0.6% mobile topup, FX margin from0.9%. Conditional two-way components≈$0.8897 before FX/gas; applicability unverified. Kotani's2% is a2021Celo pilot figure, not its current tariff. |
| Missing economics | Actual partner servicing/collection price, full two-way quote, recovery/loss cohort and borrower productive cashflow. | Same; avoid adding M-PESA rail fees already bundled by a provider. |

Primary links, excerpts, dates and access limitations: [Philippines audit](philippines-source-audit.md),
[Kenya audit](kenya-source-audit.md) and their source JSON files. Published fees
are not production quotes; stablecoin/FX equivalence is not guaranteed.

**The pricing test:** 1,400bps is the premium; plus433bps benchmark gives18.33%
total APR. Exact contract arithmetic on25USDC over30days collects0.376643USDC.
At3%,6% and10% full-loss incidence percycle, principal losses are0.75,1.50 and2.50.
Accounting for foregone interest, minimum external loss support is approximately
0.384657,1.145956 and2.161022 perloan **before servicing**. Stake transfers this
loss to a sponsor; it does not remove it. These are optimistic ecosystem lower
bounds allocating **all gross interest** to losses, not proof that the example's
45% reserve allocation is sufficient. With zero costs/recovery, break-even
incidence is only1.4842% percycle. Annual default and portfolio expense ratios
cannot be substituted for these cycle measures.

Borrower-paid2% cashout reduces25 to24.50 while debt remains25.376643: roughly
43.53% simple annualized total cost, excluding return fees/spreads. If the lender
absorbs that0.50, it exceeds gross interest. Neither case establishes affordability.

**Evidence corrections:** CGAP's29.1%→20% result is a lab game; Kiva's72.8% is
direct U.S. lending; MIX28%→19% is a historical trend. Philippine first-cycle
arrears are not final losses; officer minutes are not dollars perloan. None
calibrates local3–6% losses or a current25USDC servicing fee. [Definitions and sources](group-loan-cost-and-loss-audit.md).

**Path forward:** obtain the missing regulator text and paired production
quotes; cost one licensed partner's existing payroll/invoice or group-backed
product; compare local-currency/prepayment alternatives. Select a corridor only
after those checks. Fix/review CI30, verify secured stake and settlement on
testnet, then measure one consented human's useful net payment before expanding
to20–50. If fees/losses need sponsorship, fund and disclose a finite subsidy;
do not label it self-sustaining. Country/site, partner, security and spendability
remain unresolved gates, while agent-income experiments continue separately.

Reproduce: `python3 human_25.py`; all nonobserved values are sensitivity inputs.
