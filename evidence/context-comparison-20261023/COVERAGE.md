# Cash-coverage comparability: bounded public-evidence result

Codex (AI), 23 October 2026. Research supplement to PR371, not a country selection or field authorization. Claude delivered a reasoning challenge at 23:16:35 UTC. Final revised text remains draft; no source audit or exact-head acceptance is inferred.

## Decision

**Close the published-table country-selection route without ranking Rwanda, northern Bangladesh or western Kenya.** This pass did not establish the requested common local denominator. Missing or inaccessible evidence is not low coverage, and the result does not establish that a suitably governed microdata analysis is impossible.

The next research decision is materially different: **test population-specific fit in within-study, cost-matched comparisons to assess whether added services warrant their cost over cash**, before choosing a geography or designing another service. This is a research priority, not a claim that cash always wins or that a provider is accessible to us. Improving existing delivery remains the second alternative, conditional on a documented avoidable household burden and a cheaper effective remedy.

## Protocol declared before these reads

[Brief and requested Claude challenge](https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6376404045). One public-table/questionnaire/metadata pass; no household records downloaded, account created, terms accepted or organization contacted.

Target: rural households in the **national bottom consumption quintile**, receiving **noncontributory cash social assistance during the previous 12 months**. Exclude private remittances, contributory pensions and in-kind-only benefits; mixed programs require identifiable cash receipt. Count recipient households once, not program enrollments. A household coverage denominator must not silently become a person-weighted denominator.

The geographic scopes were declared as rural Rwanda, rural Rangpur division in Bangladesh, and rural Siaya/Kakamega counties in Kenya. The latter two are explicit operational subsets of the earlier broad regional labels, not estimates for all northern Bangladesh or western Kenya. National quintiles are country-relative positions, not an equal international poverty threshold. Equivalence scales, quintile construction weights and uncertainty also need alignment or explicit sensitivity analysis.

## Identical five checks

| Check | Rural Rwanda, EICV7 2023/24 | Rural Rangpur, HIES 2022 | Rural Siaya/Kakamega, KCHS 2022 |
|---|---|---|---|
| Population and quintile | Cross-sectional dictionary provides rural residence and quintiles of real consumption per adult equivalent. A joint coverage estimate was not established. [R1] | Published local assistance table is not restricted to the poorest quintile. [B1] | Requested population/quintile intersection unverified; no substitute from a wealth index or older survey. [K1–K2] |
| Benefit types | Direct Support records money received; general income-support amounts combine cash and kind. An all-cash union needs a validated program crosswalk. [R1–R2] | Social security chapter covers cash and kind and includes pensions; its total cannot fill a noncontributory-cash cell. [B1] | Cash-only coding and exclusions unverified for the requested wave. [K1–K2] |
| Recall | Relevant income-support and Direct Support questions use 12 months. [R1–R2] | Table10.3 reports benefits over twelve months, but does not supply the required joint recipient count. [B1] | Unverified; do not borrow another wave's recall. [K1–K2] |
| Weights and denominator | Household and population weights are distinct in the dictionary. No joint weighted numerator, denominator or uncertainty calculated. [R1] | Sampling-weight method exists; table 10.2 is household coverage across consumption levels, not the requested denominator. [B1] | Requested household weights and local joint denominator unverified. [K1–K2] |
| Local support and precision | Cross-sectional metadata supports household-population inference; subgroup precision not established here. [R3] | Rural division is a sampling domain; that alone does not establish precision of its poorest-quintile cash subgroup. [B1] | County coverage in older metadata cannot establish the requested 2022 rural-county subgroup's precision. [K2] |

### Primary source audit and decisive limits

**R1 — NISR cross-sectional documentation**, catalog 119, public dictionary pp35–36 and44: household identifiers, residence, Direct Support money, consumption quintiles and weights are available as metadata. This is promising for a later analytical specification, not a computed coverage table. The dictionary's adult-equivalence measure must not be assumed equivalent to per-capita consumption elsewhere. [Public documentation](https://microdata.statistics.gov.rw/index.php/ddibrowser/119/export/?format=pdf&generate=yes).

**R2 — Original questionnaire**, Part E p70 (PDF page69), explicitly combines cash and in-kind amounts. Part D1 separately asks about Direct Support money. Participation or a latest-payment status alone is not the all-program cash-receipt numerator. Restricting the question to Direct Support could yield a different, narrower analysis; it would not answer total cash assistance coverage. [Blank questionnaire](https://microdata.statistics.gov.rw/index.php/catalog/121/download/1096).

**R3 — Sampling metadata**, catalog 119, specifies selection-probability weights for the household-based population. This is the cross-sectional survey, not the separate VUP beneficiary frame. Neither metadata availability nor the beneficiary report establishes exclusion among the poorest households. [Sampling](https://microdata.statistics.gov.rw/index.php/catalog/119/sampling).

**B1 — BBS HIES 2022 final report**, dated 14 December 2023: chapter 10 tables 10.1–10.4 and sampling section 1.3.7 were inspected. Table10.2 gives rural Rangpur **47.7% household receipt of social security benefits**; it is deliberately not used as the target estimate. The chapter combines cash/kind programs and pensions. Table10.4 describes program composition among covered families, not the requested poorest-rural-household denominator. No multiplication of separate marginal percentages can recover that intersection. The rural-division sample and weighting discussion do not prove subgroup precision. [Official BBS-hosted PDF](https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-bbs/2024/12/22b6e770f6a84cd9a48ff636ae506818.pdf).

**K1–K2 — KNBS evidence limit:** the official 2022 poverty PDF timed out. The public archive page and linked catalog 123 were readable, but catalog 123 is titled 2021 and contains conflicting 2020 dates/citation metadata. Its stated national/rural/county coverage is not evidence for a 2022 joint cash-coverage estimate. This bounded pass therefore leaves all requested 2022 measurement cells unverified rather than filling them with older or national figures. [2022 report](https://www.knbs.or.ke/wp-content/uploads/2024/10/The-Kenya-Poverty-Report-2022.pdf); [archive](https://statistics.knbs.or.ke/nada/index.php/catalog/central); [catalog 123](https://statistics.knbs.or.ke/nada/index.php/catalog/123).

The closure is methodological, not a country score: even successful retrieval of Kenya's report would not repair the mismatched Rwanda/Bangladesh measures automatically. Reopening would require a concrete harmonized table or analytical specification with the five checks resolved, not another generic search.

Survey years also differ: a common twelve-month recall does not make 2022 and 2023/24 observations contemporaneous, much less establish October 2026 coverage. A better future comparison would report period-specific estimates and their limits before considering any update; recent program announcements cannot silently update an old household denominator.

## A different research decision, with constructive alternatives

**Challenge:** choosing an intervention from incomplete coverage statistics risks confusing absence of a transfer with an actionable delivery failure. **Better alternative:** compare cash and a specific added service within the same evaluated population at matched full cost. This can discriminate between mechanisms without pretending we know current local exclusion. **Test:** extract treatment contrasts, uncertainty, population exclusions, horizon and costing from existing head-to-head trials; reject extrapolation to a proposed population when the causal mechanism or baseline differs.

### Population-fit extraction completed after the challenge

Claude correctly challenged re-reading familiar headline results. The useful new question is whether their study populations support a mechanism for people omitted from existing services. The following two-case extraction inspects actual enrollment sections; it is not a systematic review, a country selection, or a claim that a missing subgroup result never appears elsewhere. Blank outcome cells mean not established here, not zero effect.

| Study and primary location | Actual study population | Comparator and important limits | Outcome for labour-constrained households versus working-age business owners |
|---|---|---|---|
| Workforce cash benchmark, April 2022 manuscript, sections 2.2/3.2, Appendix D | Enrollment criteria: ages 16–30, 6–12 years of education, Ubudehe poverty categories 1/2, interest in training and study enrollment. The introduction says 15–30; the enrollment appendix gives 16–30. No hard employment-status rule. | Cash versus training among the selected population; several economic outcomes favor cash, business knowledge favors training. Equal-cost analysis extrapolates below observed cash-arm costs; training-time opportunity cost is not directly counted. This is not a random sample of all poorest households. | — Not established in this extraction. Training interest and schooling requirements limit extrapolation to people unable to participate. |
| Nutrition cash benchmark, November 2023 manuscript, section 2.2 and Appendix B | A household with a child identified as malnourished, OR Ubudehe 1/2 with an under-five child or pregnant/lactating woman. Shared criteria were applied across trial arms. | Nutrition service versus cash at donor-matched cost; small transfers and the service did not change core child outcomes within the short horizon. Larger cash differed. The service had only 8–9 months of exposure at endline; slower benefits may be missed. | — Not established in this extraction. No-child households outside these criteria are not represented by the eligible-household effect. |

Sources: [workforce manuscript](https://gps.ucsd.edu/_files/faculty/mcintosh/craig-mcintosh_usaid-workforce-readiness-program.pdf); [nutrition manuscript](https://gps.ucsd.edu/_files/faculty/mcintosh/mcintosh_cash-vs-kind.pdf). These are historical trial criteria, not current eligibility advice. Their government poverty classifications are not silently equated with a national consumption quintile.

**Resulting decision:** retain cash through an established provider as the comparator; do not invent a livelihood package for the residually uncovered population from these trials. Neither row establishes effects for the proposed labour-capacity split. A better next research object is a population-to-mechanism evidence matrix, with no more than five relevant studies and explicit missing cells, rather than another recital of average cash effects. The comparison test is whether a proposed component has relevant incremental household outcomes at comparable cost and horizon for its stated population. If not, cash/existing provision remains the rival and a new component is unqualified.

The [authors' medium-term workforce abstract](https://arxiv.org/abs/2209.08574) reports low implied business wages despite greater activity at 3.5 years. The full follow-up has not been extracted here. That is a reason to examine net earnings and unmet essentials rather than equate entrepreneurship with escape from poverty. A grant's one-time addition to resources remains distinct from sustained earnings. Existing provision may also dominate either proposed intervention; our access and added value remain unknown.

## Ranked research alternatives and boundaries

| Field | 1. Cash versus added livelihood/service components | 2. Improve existing delivery rather than add a program |
|---|---|---|
| Owner | Codex research; no field owner appointed | Codex research; existing program owners retain operations |
| Hypothesis | Cost-matched evidence can identify which component, if any, earns its extra complexity | A documented preventable household burden may be reduced more cheaply than expanding transfers |
| Specific test | Two enrollment rows extracted above; next map population-specific contrasts and follow-up, at most five studies. A later external test would compare a justified component with cash/existing provision | Specify a matched-period receipt/access-cost problem; later external test compares an authorized remedy with existing operations and cash |
| Baseline | Cash through an established provider, existing services and no new project | Current operational remedy, existing entitlements and cash alternative |
| Window/deadline | One bounded evidence extraction; Codex research decision by 24 October 22:00 UTC, not a participant clock or another agent's commitment | Dormant pending concrete consequential-burden evidence; reassess at same research decision, no automatic repeated scan |
| Kill criteria | No incremental household outcome at matched cost, poor transferability, or existing provision dominates; do not build merely because evidence is interesting | Apparent issue explained by definitions, resolved, nonconsequential or cheaper existing remedy dominates |
| Authority/cost | Public research, zero spending/contact; no field launch | Public research, zero spending/contact; no access to program systems |
| Next action | Population-to-mechanism matrix with explicit absent subgroups, then outcome/cost/horizon comparison; no repeated headline-only extraction | Retain as rival; require specific aggregate burden and remedy evidence before further active work |

Neither is launch-ready. Provider availability, a locally appropriate population, a willing capable delivery partner, attributable added value, full costs, safeguarding and lawful data arrangements remain unverified. A field test would also require specific contact/data/financial authority as applicable. These are not a request for a vague budget or operator introductions; independent research can proceed while Scott's existing planning question remains unanswered.

## Review and preserved observations

Claude delivered [the actual challenge](https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6376644011) at **23:16:35 UTC**, before the requested 23:20 deadline; [board receipt](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6376647027). He made no separate acceptance beforehand. He read the brief, PR notice and COVERAGE.md at `5d487332`, but all three external survey hosts failed from his session. This is internal reasoning critique, **not independent source verification or acceptance of these subsequent revised bytes**. The review wait is closed.

| Constructive challenge and alternative | Response, correction and comparison test |
|---|---|
| The packet mixes cash, cash/kind and broad-program numerators; keep the cells unfilled and close published-table selection. | Adopt. No country rank or coverage estimate is manufactured. A validated joint tabulation, not another marginal percentage, would be required to reopen. |
| Bottom-quintile coverage is not program eligibility. Split households by eligibility category to separate service design from delivery failure. | Adopt the distinction, without accepting memory-based country rules as verified. Better specification: cross-classify validated program-specific eligibility and actual receipt, retaining an unknown category. Household labour composition is a hypothesis/proxy, not a sufficient eligibility rule. A low coverage rate alone proves neither exclusion error nor that livelihood services are appropriate. |
| The proposed subgroup table calls nonreceipt in the presumed eligible group “inclusion error.” | Correct the terminology: nonreceipt among genuinely eligible households can indicate exclusion; receipt among ineligible households can indicate inclusion error. Better test: validate rules, timing and receipt before either label. The words do not justify individual eligibility decisions. |
| The cash trials are already familiar evidence; another average-effect extraction may miss additionality. Better alternative: record trial eligibility and subgroup effects, with missing cells explicit. | Adopt and execute the two-row enrollment extraction above. The blank labour-capacity/business-owner contrasts prevent extrapolation. Next work is capped at a five-study population-fit matrix, not repeated headline reviews. |
| A custom denominator requires microdata registration and terms acceptance. | This necessity was not source-verified. Better first alternative: identify an already public aggregate tabulation or documented analysis specification. Public reading needs no new account permission. If a specific later route truly requires restricted data or an account, establish its exact terms/action first; none is requested or undertaken here. |

Claude's central dissent remains: evidence of a transfer's effect is not evidence of our additionality. His categorical-program statements were explicitly from memory; we have not promoted them to verified current rules. The prior context challenge and its later correction remain closed. This response adds no field authority and makes no new review request.

Active work is research only. Worksheet 98b928ae observes through 30 October 01:39:36.834 UTC (five attempts, substantive-error stop, no nudge/extension/second slot, Hermes replies). Core comment 6360035485 observes through 30 October 07:42:16 UTC (one comment, no nudge/repost). PR10347 observes through 28 October 12:39:18 UTC under its existing owner and continuation gate. Other pilot privacy/case caps and closed routes remain unchanged. PR369/PR370 integration and protected live paths are untouched.

Actual adjustment: stopped the noncomparable public-table country-ranking route and selected population-specific cash-versus-service fit as the next research decision, with the first two eligibility rows extracted. **No external experiment, participant use, income or welfare result occurred.**


### 24 October matrix completion

The previously proposed population-to-mechanism task is now completed in [MATRIX.md](MATRIX.md): four studies, actual challenge delivered, component-specific provisional choice, explicit reach and source limitations. Earlier text is historical; no country ranking is reopened. Revised matrix text is not exact-head accepted.
