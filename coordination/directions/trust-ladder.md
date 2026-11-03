# Direction D17: the trust ladder, from the practice desk to network trust

Claude Code (AI), 2026-11-03. **Status: PROPOSED design with a working prototype; builds on D7 (the app) and D16 (the human-first lane) and changes neither's gates.** Written from the operator's direction of November 3 (chat; summarised, not quoted as a receipt): the agentic screening of borrowers is too weak even for a demo; find a real way to screen people we do not know, with documents or an explanation; say in the practice app that it approves everyone because it is a test; make participation in the practice count toward a real credit decision; and document a path from simple determinations on the app to real trust on the real app, converging to PageRank-like network trust. Base inspected: testbed `main` 9abf82c (model 0.1.213) and the app branch `claude/d7-live-sim-app-20261101` at f455fe4. Prototype: [experiments/self-service-borrower-app/screening/](../../experiments/self-service-borrower-app/screening/) (28 tests in `tools/check.py`). Not a deployment, a loan offer, a credit decision or evidence of human benefit.

## The four questions

- **Measurable human outcome or decision:** whether a person we have never met can be told yes or no on a first real loan by a method that (a) a person can read and act on (every no carries its reasons), (b) does not hand free credit to a stranger who regenerates identities, and (c) gets cheaper and more accurate as the pool's own record grows, so the operator's mainnet decision (D16) rests on a screen that was measured, not asserted. The human scorecard stays `M = B / sponsor money consumed`.
- **Evidence sought:** the admitted first-loan default rate and admission rate of each policy version on real applications (exact binomial bounds); the measured cost per assessment; the share of declines that the applicant could cure with one document; and, on the ladder's last rung, whether a stake-seeded graph score predicts repayment better than the interview score on the same cases.
- **Competing simpler routes:** no screen at all with full backing (the pool is indifferent to the borrower; the backer carries the risk, which is what the practice desk does with its own stake); a partner's existing group lending inside its own meeting (D8); direct cash. The ladder is only worth climbing if a stranger with a backer, but without a group or a partner, is a person the project should reach.
- **Stop or change condition:** a policy version whose admitted default interval lies above the 11 percent ceiling (D7 rule 5); evidence that the screen declines the people the project exists for faster than it declines defaulters (false rejection measured by the randomised holdout, D7 rule 6); a measured cost per assessment above 15 cents; or the graph score failing to beat the interview score on held-out cases, in which case the top rung is not climbed and the interview stays.

## The problem, stated exactly

The practice app on the test network has a credit officer, and it is a real agent: the desk daemon runs the model through the headless CLI, with a rules officer as fallback when the budget, a cooldown or an outage says so. But its instructions grant the amount asked, up to the desk's maximum, and decline only for abuse, threats, a request that is not for the applicant, or a wallet with a past default. The structured request the app writes ("I need $X for Y. I can pay it back Z.") is decided by rules; the model only phrases the answer. So the officer would not deny an ordinary request, and it should not: the desk backs every loan with its own test stake, every word is public on the test network, and the test is of the app, not of the person. From November 3 the desk says so with its first grant, and the app and tester guide say it too.

A real loan cannot work this way. Three things the practice desk cannot do:

1. **Read evidence.** Everything on the test network is public, so nothing personal may be written there. A real screen needs a pay stub, a statement, an order or a quote, which must go to the lender privately.
2. **Know that a person is one person.** A free identity can be regenerated until one passes any filter ([ring attacks](../../research/ring-attacks-on-agent-trust-systems.md)). Only money at stake, a named backer's or the applicant's own, makes the pool indifferent to who the borrower is (D7 screen rule 2).
3. **Learn.** The desk has no record that carries forward. A screen that does not get better with every repaid loan will always be an interview, and interviews are expensive and gameable.

The ladder below fixes each in turn.

## Rung 0: the practice desk (live now)

What it is: the public chat on the test network, the desk's own stake, three facts in the request (what for, how much, when), one AI officer that says yes to every proper request and says so. What it measures: whether a person can complete the loop (install, ask, borrow, send, repay) with no wallet software and no ETH, and what confuses them. What it records: per wallet, loans taken, repaid, days late, defaults, all public. What it establishes about trust: almost nothing, and it says so. One thing carries forward: **a completed practice loop** (at least one loan repaid, no default) is a verified statement in the real screen, worth 5 points of 100, never backing.

## Rung 1: the first real loan (the app plus the screen)

The screen is the prototype in `experiments/self-service-borrower-app/screening/`. It runs on the lender's own machine (`python3 -m screening.server`), never on the public network, and stores each application privately with its dossier and decision. It has four parts; the agent is in exactly one of them.

**Seven taps.** The interview was seventeen questions on November 3 at midday; the operator said that is too many unless they are low-load multiple choice. It is now seven, six of them chips: what the money is for (seven purposes), how much (3, 5, 10 or another amount), when it can be paid back (30, 60, 90 days), where repayment comes from (six sources), what is usually left each month after rent, food and other loans (five bands), who stands behind the loan (a backer, my own deposit, nobody yet), and one consent. That is the whole practice interview. A real loan adds the evidence stage: the applicant's name as it appears on documents, one sentence in their own words (typed or spoken), who pays them, the backer's account, and up to three documents. Deterministic follow-ups ask for what is missing ("you said repayment comes from sales; show a sales record or a statement from the last 90 days") and raise the simpler route ("could the customer pay part up front instead?"). Nothing asks about a protected characteristic; an application that carries one is refused before scoring.

**Documents.** Each upload is typed (pay stub, employment letter, bank or mobile-money statement, sales record, customer order, supplier quote, benefit letter, backer's note), hashed, and reduced to claims: who paid, how much, how often, on what date, in whose name. This is where the agent works. The Claude extractor reads PDFs and images with a structured output schema, sees only the document and never the applicant's answers (so it cannot be talked into agreeing with them), and reports its token usage, so the cost per assessment is measured against D16's 10 cent target rather than assumed. A rule-based extractor reads labelled text for tests. A document's hash is kept in a private registry; the same pay stub on a second application is a severe contradiction.

**Dossier.** Every statement is tagged stated (the applicant said it), evidenced (a fresh document supports it) or verified (the pool's own ledger or the practice desk's public record confirms it). Contradictions are coded, not prose: a document in another name, a document older than 90 days or dated in the future, a stated surplus above what the documents show, a request above the supplier's quote, a customer order paid after the loan's term, an order to be filled whose customer is not the repayment source, a backer who is the applicant, a backer with a default, an open loan, a reused document. The extractor's own concerns become one coded flag at most.

**Policy.** Deterministic, versioned (`2026-11-03.1`), with published weights that sum to 100: repayment source (30: verified, evidenced, stated), capacity (20: the monthly instalment against the monthly surplus, halved when the surplus is only stated), purpose (15: productive and evidenced, productive stated, other), the backer's or deposit's record in the pool (15), the applicant's own history (10: an on-time repayment with us; 5 for a linked practice loop), consistency (10, less 5 per minor contradiction). Four hard rules come before the score and are never outweighed: no backing means no loan; a default or an open loan in the pool means no loan; a severe contradiction means no loan; and the cap is at most the backing that exists, at most a fifth of the reserve, at most the request. Below 40 is a decline; 40 to 64 is a first loan up to 5 USDC; 65 and above up to 10; after one on-time repayment the repeat tier allows 20. Every decline lists its reasons in the applicant's terms ("Repayment source not shown: no recent pay stub, statement, sales record or customer order shows it"), which is what an adverse-action notice needs. The agent never emits the number; the code does, and a person can recompute it from the dossier.

Four worked examples ship with the prototype and run in the test suite: a market trader with a statement, a quote and an aunt who has repaid twice (approved, 10 USDC, 85 of 100); a pay stub in someone else's name, four months old (declined, with the name mismatch as the first reason); an emergency with no backer and nothing left each month (declined, with the backing rule first); a warehouse starter with an offer letter, her own 5 USDC deposit and two repaid practice loans (approved, 5 USDC, 78 of 100).

**Linking the practice record.** The real app asks for the practice wallet's address and has the applicant sign a one-line challenge with the same passkey that runs the practice wallet. The lender's intake verifies the signature and reads the desk's public record (loans, repayments, days late, defaults). Without the signature the practice wallet is a stated claim and earns nothing. This is the whole of "participation counts": a verified fact with a small weight, not a line and not backing.

**What the officer agent does at this rung:** it extracts, it flags, and in the practice desk it phrases. It does not decide and it cannot create a line, which is the existing officer rule ([MANDATORY_CREDIT_OFFICER_COMPARISON.md](../../docs/MANDATORY_CREDIT_OFFICER_COMPARISON.md)) and the contract's design (the order router requires its one-use approval of an exact order; capacity comes from stake).

## Rung 2: repeat loans and graduation

After one on-time repayment the applicant's own history is verified and worth the full 10 points; the cap rises to 20 USDC. In open access repeat loans stay fully backed; in a named cohort, where identities are not free (one line per person through an existing relationship or a partner's KYC), the backing share may fall to one half (D7 rule 4, with the two-identity ring it guards against). A backer's own record now matters twice: it is 15 points on the people they back, and their stake is slashed first when a borrower they backed defaults. The practice record stops mattering here; the real record has replaced it.

## Rung 3: network trust, and why the ladder converges to it

By rung 2 the pool holds a graph. Its nodes are people with one line each and stake roots (a backer's locked dollars, a sponsor's reserve). Its edges are backings (consented, with an amount and an expiry) and repayment history (interest actually paid to the pool, which is the one thing bot volume cannot fake, [METRICS.md](../../METRICS.md)). The required end state is already recorded ([TRANSITIVE_TRUST_TARGET.md](../../docs/TRANSITIVE_TRUST_TARGET.md), operator clarification of October 7): after bootstrap the system runs on transitive trust and staking with algorithmic creditworthiness, and officers are temporary.

Two outputs, never conflated:

- **Ranking and price.** A stake-seeded personalised PageRank: trust flows from the stake roots along backing edges, weighted by repaid history and damped by distance, so a person's score is high when people with money on the line vouch for them and those people earned their own standing the same way. The score ranks eligibility and sets the price inside the backing; it is deterministic, published, and checked against adversarial fixtures (shared-root diamonds, cycles, hub-and-spoke rings, Sybil expansion).
- **Capacity.** Routed stake only. A loan is a reservation of bounded paths from a root to the borrower, with every edge's consent and the root's remaining stake checked at origination, so credit cannot be created inside a cycle and a ring of free identities can score each other to the sky without minting a dollar. The ranking never substitutes for the resource ledger.

The ladder converges because each rung feeds the next's inputs, and the policy's weights move with it:

| Signal | Rung 0 | Rung 1 | Rung 2 | Rung 3 |
| --- | --- | --- | --- | --- |
| What for, how much, when | stated, public | stated, private; checked against documents | same | intake only |
| Documents (income, purpose) | none | evidenced; agent extracts | evidenced, refreshed | optional; history outweighs them |
| Backing | the desk's own stake | a named backer or own deposit, verified on chain (hard rule) | same; share may fall in a named cohort | routed stake through consented paths (the only capacity) |
| Applicant's history | practice loop, public | linked practice loop, 5 of 100 | real repayments, 10 of 100 | an edge weight in the graph |
| Backer's history | none | 15 of 100 from the pool's ledger | same, plus slashing order | the backer's own score, which came from their backers |
| The agent | phrases a yes | extracts and flags; never decides | same | audits manipulation, helps with disputes |
| Policy version | none | `2026-11-03.1` | a version with history weights raised | the graph function, published |

Each new policy version raises the weight of verified history and backers' records and lowers the weight of what was said and shown, as the pilot measures that the history predicts repayment at least as well. The limit of that process is a score that is a function of the graph alone, which is the stake-seeded PageRank above, with the interview reduced to the seven taps that fix what the loan is for. The officer does not need to be switched off at the end; its weight goes to zero.

## Gates between rungs (owner estimates, not accepted SLAs)

| Gate | What must be true | Owner | Dated step |
| --- | --- | --- | --- |
| 0 to 1 | D7 gates 2 and 3 (the app works for named testers); the practice desk says it approves everyone (done November 3); the screen's shadow-scoring report on the five named applicants and a synthetic set, with cost per assessment measured (D16, November 17) | Steward (D7), D16 lane | November 17 |
| 1 live | D16's compliance design (lender of record, privacy notice, adverse-action notice from the scorecard); the intake on the lender's machine; the passkey link to the practice record; the randomised holdout pre-registered | D16 lane, operator (lender of record) | With the mainnet packet |
| 1 to 2 | 20 first loans with exact binomial bounds on admitted defaults inside the 11 percent ceiling; backers' realised loss reported with the pool | D16 lane | After the first 20 loans |
| 2 to 3 | The graph ranking published and tested on adversarial fixtures; the capacity router (contract PR 28 lineage) reviewed; on held-out cases the graph score predicts repayment at least as well as the interview score; the sunset gates in TRANSITIVE_TRUST_TARGET.md | Contract repository, D16 lane | No date; evidence-gated |

## What the prototype does today, and does not

Does: the seven-tap interview with validation and follow-ups; typed document intake with hashing, a rule-based extractor and a Claude extractor with measured cost; the dossier with eleven coded contradictions; the policy with published weights, hard rules, caps and reasons; a local intake page that stores records privately; a command line that screens an application folder or the worked examples; 28 tests under `python tools/check.py`.

Does not: run on the practice app (which stays public and approves everyone, by design); verify a passkey signature for the practice link (the record is read from a pool-record file the app or the daemon writes; the signature check is the next build step); read the chain itself (the pool record is a JSON input); compute any graph score (rung 3 is a design here, with its own required proofs); establish demand, a borrower, a backer, a lender of record, or human benefit. The Claude extractor has not been run against a live key in the authoring session; its request shape follows the SDK's structured-output form and its cost arithmetic is unit-tested with a stub.

## What this document does not claim

No person has been screened. No default rate, admission rate or cost has been measured. The weights are a first published version to be replaced by the pilot's measurement, not a validated model. The graph score is the required end state and a design, not an implementation. Nothing here is an offer of credit.
