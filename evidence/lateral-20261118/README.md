# Daily lateral run, November 18, 2026: F2 remittance corridor cost and F8 ecosystem-services verification

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5. No register or direction date fell due today. Both tests are the next two far-lateral (F) paths without a receipt.

## Receipt 1 (F2, remittance corridor cost reduction)

**Test (register):** one corridor's cheapest licensed route versus the median, from the public database; stop if the cheapest licensed options are already near 3 percent.

**Found.** The Remittance Prices Worldwide site and its quarterly reports refuse this proxy, so the official figures were read from the World Bank indicator API (the same data, annual averages) and from Our World in Data's export of the SDG 10.c.1 series [primary public data; the export is saved beside this file].

| Series (World Bank) | 2021 | 2022 | 2023 | 2024 | 2025 |
| --- | --- | --- | --- | --- | --- |
| Average cost of sending to Guatemala, all corridors (SI.RMT.COST.IB.ZS) | 3.41 | 2.79 | 2.56 | | |
| Average cost of sending to Mexico | 1.78 | 1.34 | 2.65 | | |
| Average cost of sending to Kenya | 5.04 | 2.17 | 3.86 | | |
| Average cost of sending from the United States (SI.RMT.COST.OB.ZS) | 3.32 | 2.73 | 3.51 | | |
| SDG 10.c.1, cost of sending from the United States (Our World in Data export of the World Bank series) | | | 5.77 | 6.03 | 5.04 |
| SDG 10.c.1, cost of sending from Kenya | | | 10.15 | 10.80 | 12.41 |
| Global average, 200-dollar transfer, Q1 2025 (register source, site blocked here) | | | | | 6.49 |

The two United States series differ (3.51 against 5.77 for 2023): the indicator API's outbound series and the SDG 10.c.1 series are both labelled as the cost of sending from the country but are compiled differently (the SDG series tracks the 200-dollar transfer across RPW corridors), and the Remittance Prices methodology notes could not be read here to reconcile them. The inbound series, which is what a Guatemalan or Mexican household faces, is unambiguous.

**Reading (qualified November 20 on Codex's post-merge review, PR 487 comment 6991450919, and PR 491 review).** The figures read are all-corridor country averages: the average cost of sending to Guatemala and to Mexico across every surveyed corridor was about 2.6 percent in 2023, below the 3 percent target. That aggregate does not establish the United States to Guatemala or United States to Mexico corridor price, nor the cheapest-versus-median spread within either, because the corridor-level Remittance Prices data refuses this proxy. So the register's test (one corridor's cheapest licensed route versus the median) is **UNKNOWN**; what the aggregate shows is that there is little room for a three-point saving on average, not that none exists on the route. Kenya inbound averages 3.9 percent and sending out of Kenya costs 10 to 12, which no borrower of ours would do. **Classification: bound; PARKED for absent corridor-level data.** The D17 carry-forward is the aggregate only. **Score:** evidence 2 to 3; execute 1 unchanged; total 9 to 10. **What F2 becomes:** an aggregate fact for D17's rails table: remittances into Guatemala average about 2.6 percent across corridors, so the remittance-linked repayment option (F11) is bound by provider terms before price; the corridor-level price stays to be read.

## Receipt 2 (F8, payments for ecosystem services with agent-run verification)

**Test (register):** a public-data monitoring note on one programme's published plots; stop if verification cost is not the binding constraint.

**Found [primary: acorn.rabobank.com, which serves one script page for every address, read 2026-11-18; secondary: press and Acorn's own earlier materials as summarised in search results].**
- Scale and split, from the page as served: "591,761 Farmers supported, 372,605 Tonnes of CO2 removed, 555,559 Hectares covered"; "70% of carbon credit revenue flowing directly back to smallholders" (step 6, "Farmer Payout"). The register's 80 percent figure is the programme's earlier statement (80 to the farmer, 10 to the local partner, 10 to Acorn); the live page now says 70.
- Monitoring and verification, from the page: "Step 4 Biomass monitoring: using satellite data and remote sensing, we track tree growth and carbon capture at scale"; "Step 5 Verified carbon credits: carbon removals are verified by third-party auditors ... methodologies aligned with globally recognized standards". Earlier materials (secondary) put measurement, certification, validation and monitoring inside Acorn's 10 percent share of unit value, with a minimum unit price of 20 euros and ground truth from hand measurements.
- Per-farmer money, from press (secondary): one Brazilian cooperative's first round generated 242 removal units worth about 4,647 dollars, about 18.59 dollars per producer.
- Published plots: the registry is said to detail every unit down to the plot; the plot data did not render for this proxy, so no public-imagery note on named plots was possible this run.

**Reading (qualified November 20 on Codex's post-merge review, PR 487 comment 6991450919, and PR 491 review).** The programme's cumulative tonnes divided by farmers supported (372,605 over 591,761, about 0.63 tonnes each) is an illustrative aggregate ratio: it is not realized payout per paid farmer over an aligned period, since the counters are cumulative, the cohorts differ in age and not every supported farmer has been paid. The euro figures derived from it (about 9 euros at a 20-euro unit and 70 percent; 15 to 18 at 33 to 40 euros) are illustrations with the same limit. Verification already runs on satellite data at scale inside a bundled 10 percent share, but a bundled share does not isolate the marginal verification cost or show that it cannot bind participation. So **"verification cost is not the binding constraint" is an unproven hypothesis**, consistent with the aggregates but not established by them. **Classification: bound; PARKED for absent aligned payout, cohort and cost data**; a channel question like every farmer-facing path. **Score:** evidence 2 to 3; execute 1 unchanged; total 9 to 10. **Re-entry:** a programme publishes plot polygons openly and names verification cost as what limits payouts.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| F2 | November 18 bound, parked (qualified November 20): all-corridor averages read, corridor prices UNKNOWN | re-entry when corridor-level data is readable |
| F8 | November 18 bound, parked (qualified November 20): aggregate ratio and bundled share only; the constraint conclusion is a hypothesis | re-entry on open plot data with payout cohorts and a disclosed verification cost |
| F9 | November 13 bound on the buyer side | December 13 repeat read |
| F12 | November 17: test NONE by the D17 decision | D17 re-entry |
| F3, F5, F6, F7, F4, F1, N6, N7, N5, N1, F11 | bound or NONE | re-entry conditions |
| B8 | November 10 activity trace | payment trace by a lane with a wallet |
| D16 | November 17 shadow-scoring report merged (PR 486) | November 24 round trip |
| Held merges (PR 456, 458) | operator-queue row November 12 | operator names who may merge |

Remaining untested paths after this run: N9, B3, B11, F10.

## Sources

| Item | URL | Read |
| --- | --- | --- |
| World Bank indicator API, SI.RMT.COST.IB.ZS (Guatemala, Mexico, Kenya) and SI.RMT.COST.OB.ZS (United States), 2021 to 2023 | https://api.worldbank.org/v2/country/GTM/indicator/SI.RMT.COST.IB.ZS?format=json&date=2021:2025 | primary public data |
| Our World in Data, SDG 10.c.1 remittance costs export (World Bank series) | https://ourworldindata.org/grapher/remittance-costs-as-share-of-amount-remitted.csv | primary public data (processed); saved beside this file |
| World Bank Remittance Prices Worldwide, Q1 2025 (register source) | https://remittanceprices.worldbank.org/sites/default/files/rpw_main_report_and_annex_q125_1_0.pdf | blocked here; register anchor |
| Acorn (Rabobank), site as served | https://acorn.rabobank.com/en/ | primary (single-page shell) |
| Acorn 80/10/10 split and 10 percent monitoring share (earlier materials, via search summary) | https://acorn.rabobank.com/en/insetting | secondary (page did not render here) |
| AgFunderNews on the first CAMTA round | https://agfundernews.com/renature-microsoft-rabobank-announce-first-round-of-carbon-credits-with-agroforestry-startup | press |
