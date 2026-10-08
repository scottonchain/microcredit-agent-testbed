# Economic admission support for Claude — 2026-10-08

This calculator complements the human-lending/field-partner research without claiming a new bootstrap demonstration. No existing real consenting buyer is identified. Service prices, borrower work/compute, fees, default probabilities and recovery are structural assumptions. API $0.23 alone comes from pinned author-listed AgentCash search/scrape rates, not an actual invoice or current quote. No funds, emails, RPC calls or protected repository changes.

Run `python3 admission.py fixtures.json` and `python3 check_invariants.py` from this directory. Python standard library only; exact six-decimal stablecoin values become integer micros and excess precision is rejected. Native ETH quote remains in wei; no fake six-decimal token conversion. Flat fees and percentage fees round conservatively upward.

| Structural case | Necessary advance | Borrower net | Spendable human payout | Lender expected margin |
|---|---:|---:|---:|---:|
| Conditional accepted $1 service | $0.485000 | $0.425000 | $0.392535 | $0.008900 |
| Buyer prepays inputs | $0 | $0.435000 | $0.402237 | No loan |
| Sponsor directly advances inputs | $0 | $0.435000 | $0.402237 | No pooled loan |
| Worker has input cash | $0 | $0.435000 | $0.402237 | No loan |
| Customer pays nothing; no recovery | $0.485000 exposure | -$0.575000 | $0 | -$0.486000 |
| 20% default, only $0.10 recovery | $0.485000 | $0.425000 if accepted | $0.392535 if accepted | -$0.070000 |

Conditional service includes input .23, compute .05, work .20, gas .005, platform .05, refund reserve .02, default reserve .01, finance .01. Upfront input+compute+work+gas=.485. Reserves remain provisions, not observed spent funds; future release is excluded. Buyer-funded $1 price is hypothetical. Expected lender margin uses 1% default probability, full .485 cash recovery and .001 lender cost; full recovery must be actually enforceable, not reputation accounting. Human outcome subtracts 1%+$.01 ramp and 2%+$.01 payout charges after borrower costs. These ramp figures are assumptions, not a country/provider quote; no fixed 1:1 fiat redemption, legal eligibility or withdrawal access is established.

Paying upfront work .20 assumes worker has an actual paid supplier/employee expense; if operator time is deferred rather than paid before settlement, remove it from capital need while retaining full economic cost. Sponsorship is non-repayable in this comparator; if sponsor requires principal/fees, model that financing explicitly. Prepaid price here is part of the $1 total, not extra revenue. Operational loan is admitted conditionally only with positive borrower net and positive risk-adjusted lender margin; structural admission is never market qualification.

Two identical fully retained successful net earnings accumulate enough input cash to stop borrowing: .425+.425=.85 >= .485. This assumes all earnings retained; the listed human payout cannot simultaneously be spent and counted as retained capital. If humans must receive money every job, configure a split and calculate slower exit separately.

Historical Hermes r15 actual read-only quote at Base block52317986: reward 2,510,707,389,920wei; full reserved gas11,787,172,931,592wei; borrower margin -9,277,465,541,672wei; lender margin1,000,000,000wei. It fails even with zero compute/work costs. Native principal12,707,276,393,564wei is financing, never profit. Full stateful simulation unsupported, quote stale, simulated lens reward not earned. NO LOAN.

For Claude's human-level launch plan: require a consenting buyer's funded order, actual nonspendable escrow terms and repayment assignment, actual supplier invoice/402 quote, human labor rate, platform fees, refund/default allocation, and a usable compliant ramp quote. Prefer prepayment or sponsorship if available. Admit only the residual necessary advance and reject any job whose full-cost borrower or enforceable loss-adjusted lender margin is nonpositive. Measure realized human withdrawal; do not substitute wallet balance for livelihood. No current mainnet spending authorization is supplied by this package.

Meaningful checks passed: exact token precision; prepayment eliminates necessity; each additional operating expense cannot improve net/human payout; greater default risk or less recovery cannot improve lender margin; ETH full-cycle conservation excludes principal; payout rounding conserves net; retained-capital exit threshold.

## Subsidy, recovery and conservation correction

Direct nonrepayable sponsor advance is a gift, not earned buyer revenue. Sponsor loses .485 cash; worker actual cash increase is .920, composed of .435 resource-adjusted earnings plus .485 subsidy. The .402237 modeled human payout specifically excludes/ringfences the gift; it does not represent all wallet cash. Reinvestment comparisons likewise use resource-adjusted earnings, not repeated donor grants. Buyer prepayment is included within total $1 price and never counted twice.

Conditional loan recovery is explicitly financed by hypothetical separate sponsor stake, not free lender protection. With assumed 1% default and .485 secured recovery, sponsor expected principal loss is .004850; full default transfers .485 from sponsor to lender. Lender's .008900 expected margin alone does not establish ecosystem admission: sponsor loss, opportunity cost and recovery delay require compensation and measured viability. The calculator records loss/cost but does not assume sponsor consent or a sustainable fee allocation. The .01 finance fee presently belongs to lender, not sponsor; sponsor expected loss is uncompensated. Reject interpreting this as a complete self-sustaining market.

Success accounting conserves cash across buyer, borrower, sponsor, lender, vendors/platform/provision accounts and lender-cost recipient. Default conserves borrower residual, lender shortfall, one sponsor recovery debit and vendor costs; it never adds stake to lender cash without equal source debit. Recovery exceeding separate stake capacity raises an error. Provisions are allocations and not necessarily realized expenditure; party ledger reports structural budget allocation. The assumed stake is distinct from lender principal and donor gift; no actor capital availability or duplicate-use permission is evidenced.

Every conditional human-spendability flag remains FALSE: actual identity, jurisdiction, platform eligibility, labor agreement, available payout/ramp and real withdrawal are unverified. A positive hypothetical after-fee number is not spendable income. Additional invariant checks verify grant exclusion, success/default conservation, sponsor-funded recovery, unfunded recovery refusal and unverified human eligibility.

Mixed financing default now includes buyer prepayment as buyer loss, sponsor grant as sponsor loss, and worker opening cash as the worker's own consumed capital. A .485 input budget funded by .10 worker cash + .10 prepayment + .10 grant requires .185 loan; on full hypothetical stake recovery, default deltas buyer-.10, worker-.10, sponsor-.285, lender minus lender cost, and resource providers+.485 conserve exactly. Prepayment above the total agreed price is rejected.

Human fee amounts are hypothetical quotes, not actual deductions. Predicted human surplus is preserved even when negative; `human_route_economically_viable` then becomes false, requiring a different route or refusing the job. Actual human spendability remains unverified in every case. The invariant result is emitted only after all fourteen check families finish successfully.
