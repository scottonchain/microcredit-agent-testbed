# Persona loop log

One line per iteration: id, persona, outcome, findings (F1..), fixes (X1..).

## p001 Ahmed, 24, student, iPhone SE (build afd6f76 + sw d7-v5). Outcome: loan $2.50 after the desk chat, repaid $2.51 ten days later, loan closed. 22 commands.
- F1 (slowed): home and Borrow show $0.00 and a grey Borrow; he had to discover the credit desk first. -> X1 fast path: the first screen after the wallet asks how much and what for, and routes to the desk itself.
- F2 (annoyed, felt risky): a passkey prompt just to send a chat message; "everything is public" warning. -> X2 the ask is one signed step with a plain line "this approval sends your request"; the public line becomes one short sentence.
- F3 (annoyed): jargon (USDC, faucet, 0x address, block explorer, dues sentence); Help never defines them; recovery code next to Remove wallet. -> X3 plain words everywhere ("test dollars", no addresses on the main screens, explorer link behind "details"), Help reordered, Remove wallet moved to the bottom under its own heading.
- Small: $2.60 after borrowing $2.50, the 0.10 pre-fund unexplained -> X4 one line "The desk added $0.10 for the interest". Borrow button grey for 5 s with no feedback -> X5 the sending sheet opens at once.
## p002 Fatima, 22, Pixel 5. Outcome: NO loan: the harness started her phone on a blank tab (about:blank) and the brief said "start with look", so she never reached the app. Harness defect H1, fixed: the phone now opens the link on start. Rerun as p002 after the fix. Her one real observation stands as a product note: a blank page with no name, no error and nothing to tap reads like a scam link; the app must show its name and a retry when it cannot load (X6: a static first paint in index.html with the app's name and a "cannot reach the network, try again" fallback if the script fails).
## p003 Victor, iPhone SE. Outcome: asked for $20, got $5, repaid $5.04 on day 30; app said "Overdue by 1 day". 48 commands.
- F2 (felt unfair, scary): "Due in 30 days" then "Overdue by 1 day" on the 30th day with the backer-loss warning. -> X7 due dates in days: "Due today" within the day, "Late by N days" after, the default warning only from a week late. Fixed.
- F3 (scared): Remove wallet sits among Help buttons and "Remove" is the big green button. -> X8 Keep it is the primary, Remove it secondary; the button lives under "Done testing?" at the bottom. Fixed.
- Small: $5.10 unexplained (X4, the credit screen now says the officer put a few cents in for the interest); jargon (X3, done); "about $0.04" vs "keep a few dollars" (X9 the note now says the cents are already there; fixed); Send feedback had no button (X-D5, fixed); the test banner read as "why am I here for a real bill" (banner reworded: practice version, not real money).
- F1 blank start: harness defect H1 (fixed before this report).
## p005 Ken, Desktop Edge (build: fast path v1). Outcome: $5 loan via the free-text desk (wanted $6), repaid after 3 days, closed. 29 commands.
- F3 (scared): after the Borrow Done popup the page behind read "Available $0.00 / no credit yet", looked like failure. -> X10 the fresh home screen renders behind the Done sheet. Fixed.
- F1/F2: expected real money; "0x address" meaningless. -> banner reworded (X-banner); Send screen says whose address and where it comes from (X11). The practice nature is said on the first screen; a person who needs real money will still be disappointed: that is the test's honesty, not a defect.
- F4-F10: jargon (line, backs you, network fees) -> X12 plain words; when-chips vs 30-day term -> X13 "(you have up to 30 days)"; owe $5.01 vs "paid $5.00, $0.00 interest" -> X14 cents rounded up, "less than a cent"; two Pay back buttons -> X15 one, in the loan card; ambiguous date 1/13/2027 -> X16 "Jan 13, 2027". Fixed.
- Laptop: fingerprint never visibly asked (virtual authenticator); on a real laptop Windows Hello shows. Not a defect.
## p004 Ivy, 68, Pixel 7 (fast path v1). Outcome: $2 loan, repaid the same sitting, closed. 27 commands.
- F1 (slowed): the ask screen gave no total cost or due date before "Ask for this loan". -> X17 a live line under the choices: you get $X now, pay back about $Y within 30 days, no other fees. Fixed.
- F2 (dented trust): dates and amounts disagree across screens. Dates: an artifact of the shared fork clock (other testers' "days" moved the world's calendar into January) plus the short date format (X16 fixed); amounts: $2.02 (30-day estimate) vs $2.01 (today) vs "$0.00 interest" (X14 fixed). -> X18 the home loan card says "You owe today $X" and "about $Y by the due date". Fixed. The clock note now tells a tester the shared clock moved.
- F3: "no credit yet" behind the Done sheet (X10 fixed); "network fees are paid for you" vs "no fees" (fixed: "No fees during the test").
- Tiny: "Borrow $2.00 now" pale beside the big Send -> X19 it becomes the primary button when borrowing is possible. "Receipt" fold on a chat send: left as is.
## p002 Fatima, 22, Pixel 5 (fast path v1). Outcome: $3 loan, $1 the same day, $2.01 ten days later, closed; the mistyped "3.o0" only greyed the button. 42 commands.
- F1 (almost blocked): the credit desk chat never refreshed while she watched; replies showed only when she reopened the desk much later. Cause: two credit screens rendered in a row (ask flow + Done sheet) and the older one killed the newer one's poller. -> X20 one poller owned by the latest credit screen, 3 s. Fixed. Officer latency under three parallel testers was 30 to 60 s per reply (world artifact; one applicant at a time in production answers in about 10 s).
- F7 (felt wrong): "paid $2.01: $3.00 borrowed plus about $-0.99 interest" after a part payment. -> X21 the close-out says what was paid now and in total, interest over the whole loan from the rate and the days. Fixed.
- F3/F4/F5: "Backed by 0x8E2B…" -> X22 "The credit desk"; "no fees" vs "9.33% a year" -> X23 "No fees; interest about 0.8% a month"; "In two weeks" vs 30 days (X13); due date in January (shared-clock artifact, X16 format).
- Minor: no hint for "3.o0" -> X24 "Numbers only, like 3 or 3.50"; receipt breakdown and unexplained words: left for a later pass.

## Batch 3 (p006 Lucia 24 iPhone SE, p007 Kofi 27 Pixel 7, p008 Grace 72 iPhone 13). All three got the loan and paid it back; 27, 28 and 31 commands; none blocked.
Findings (F = finding, X = fix shipped in this batch, H = harness):
- F25 "Get started" seems to do nothing, then jumps (all three): the ask screen painted only after its reads. X25: the ask screen paints "One moment…" at once; the button disables while the wallet is made; the setup sheet names the fingerprint prompt and the wait.
- F26 First screen reads like a game: "test loan", "wallet", "recovery code", no amount (p006, p007, p008). X26: welcome says "Try a small loan: borrow up to $5 of test dollars, pay it back, tell us how it went", one Get started button, nothing to buy with it; the wallet and recovery wording moved to Help.
- F27 Nobody explains the extra 10 cents (all three). X27: the desk's approval note, the wallet screen ("Includes the few cents the credit desk put here to cover your interest") and the Done note after borrowing all say it; the officer prompt says it too.
- F28 "How much?" asked again with 25% / 50% / Max after the amount was agreed (p006). X28: "Borrow $5.00 now" on the credit screen borrows in one tap (startBorrow, shared with the Borrow screen); the percentage chips are gone.
- F29 "A small buffer is approved" (p006, p007). X29: "Only what you owe is taken. The approval is a cent or two higher so that the interest growing in the next minute is covered too."
- F30 Cents that do not add up: "You paid $5.01: $5.00 plus less than a cent" while the wallet moved 5.10 to 0.10 (p006, p007, p008). X30: the close-out states what was actually pulled (the wallet's balance change), the interest in hundredths of a cent, and the wallet balance now; "$0.00 of that interest counts" is shown only from a cent up.
- F31 Receipt is only a link to a site that shows a bot check (p007, p008). X31: the Receipt fold now carries date and time, the action, the wallet and the record id; the link is secondary and warns about the robot check.
- F32 "No fees" against "9.33% a year" (p008). X32: one wording everywhere: no fees, interest about 0.8% a month (9.33% a year); the Borrow screen's "Term: 30 days" line replaced.
- F33 No Pay back before a loan, and "Borrow up to $0.00" with a Borrow button that only refuses (p008). X33: the Borrow button is hidden until there is credit (Ask for a loan is the one action); the limit card says a Pay back button appears when something is owed.
- F34 Unexplained words: wallet, line, backing, recovery code (all three). X34: Help's word list covers wallet, backing, recovery code; the backing card is "Who vouches for you" with a one-line explanation; the officer is told to say "you can borrow up to $X", never "line".
- F35 "In a week" chosen but "within 30 days" shown (p006). X35: the cost note prices the chosen week or fortnight and the 30-day maximum, and says pay-back is one tap in the app.
- F36 "What you write is public" read after writing (p006). X36: the note sits on the purpose field, before typing.
- F37 Only $5, needed $8 (p007): the practice cap; the chips say "up to $5 in this practice version". Not changed.
- H5 Due dates in 2027 and day counts jumping (p007, p008): the fork clock is shared and other personas warp it. The look output now prints the phone's own calendar date ("today, by this phone's calendar") so a tester compares like with like. Day counts use ceil already.
- H6 No fingerprint prompt ever appears (p007, p008): the virtual authenticator approves silently. Real phones show the OS prompt. Not a product change.
Regression on the new build: install suite 24/24; cancel-passkey text fixed (the error now reads every field of the DOMException; test T18); T11 compares the friend's balance change (the fork keeps balances between runs).

## Batch 4 (p009 Sam 61 iPhone, p010 Hana desktop Chrome, p011 Omar Pixel). All three got and repaid the loan; 45, 29, 28 commands.
- F38 (p010, blocked 40 s, felt dishonest): the officer said "you're set, tap Borrow" but no backing landed and no Borrow button appeared. Cause in the daemon: three applicants answered at once collided on the officer's nonce; the fallback re-sent the same text with backing 0 ("backing-unchanged"). X38: the officer's sends are serialized, a nonce error is retried once, and the fallback text says the amount could not be recorded and asks for one more message.
- F39 (p009, blocked and made late): on the due day the wallet was 4 cents short; the prefund had failed in the same collision (the drip is a second send). The app then sent her to the public faucet, outside the app, with the network and the address unexplained; copy gave no feedback (it does, 1.2 s; she missed it). X39, per the operator's direction of 19:30Z: the desk sends the missing cents itself. Pay back shows "Ask the desk for the cents" (one tap, stays on the screen, updates by itself); the daemon tops up a short borrower once per loan (at most half a test dollar) and says so; the drip is serialized too. Receive no longer teaches the faucet; it is an "Advanced" fold, only for when the desk is away. Help and the credit screen say the cents are provided so the interest can be paid, and that in a real loan the borrower pays it.
- F40 (p009, p011): no way to ask for an amount of one's own ($3.75, $8). X40: an "Other" chip with a box ($1 to the cap); the desk grants whole dollars, the Borrow button offers the amount asked.
- F41 (p009): "Pay only part" ignored "$4,o8" and "$4,08" silently. X41: amounts accept a comma, spaces and a dollar sign; a wrong entry gets "Numbers only, like 2 or 2.50".
- F42 (p009, p011): "Due today" the day before, day counts that jump. X42: due lines count calendar days, so the phone's date and the app agree. (The jumps themselves are the shared fork clock, H5.)
- F43 (p011): the wallet's "about $5.04 by the due date" did not fall after a part payment. X43: the forecast starts from what is owed now.
- F44 (p010, p011): the receipt's date (real clock) contradicted the app's "today" (network clock). X44: receipts use the network clock.
- F45 (p009, p011): close-out pennies ("$5.01 in total: $5.00 plus about $0.02"). X45: interest is stated in cents to two decimals and earlier payments are named; no rounded total.
- F46 (p011): a grey, silent "Ask for this loan" button. X46: a hint under it until the three choices are made.
- F47 (p009): "Borrow $4.00 now" with no "are you sure". Kept at one tap (the fingerprint prompt is the confirmation on a real phone); the note under the button says so.
- Officer design review (operator, 19:35Z): the daemon now keeps a spend ledger (cost per call from the CLI), an hourly and a daily budget, a per-applicant cap, exponential cooldown after failures (30 s to 15 min), bounded inputs (last 8 messages, 500 chars each, applicant text marked as data), a system-prompt rule against instructions in applicant text, sanitized replies (no links, no addresses, 420 chars), and a hybrid decision: the structured ask is decided by the rules and only phrased by the model; past any limit the rules officer answers. Logged per reply: model, tokens, cost.

## Batch 5 (p012 Yara, p013 Arjun, p014 June). p012 got $2 and repaid 5 days late; p013 and p014 got NO loan: 38, 50, 48 commands.
- F48 (p012, p013, p014; blocked two of three, "felt dishonest"): the practice desk had used all its test stake on earlier personas (lines stay after repayment). The model's reply said "you can borrow up to $5, tap Borrow" and the clamp appended "no free stake left", so every answer was yes and no at once, three to four times per persona, with a Borrow button that never came. X48: with no stake and no existing backing the daemon answers with one fixed sentence (no model call); a clamped grant gets one fixed sentence naming the amount it can back; the officer is told never to say "stake" or "line". The practice desk was re-funded with 500 test USDC (fund-desk.mjs). The live desk has 15: the same limit will bind after three applicants; its top-up is the steward's drip rule.
- F49 (p012, p013): the officer claimed "I've put a few cents in your wallet" on later messages when nothing was sent. X49: the prompt states whether the cents go out with this reply; the rule says to mention them only then.
- F50 (p013, p014): "Send feedback" did nothing (a mailto, no mail app in the harness; on a phone it leaves the app). X50: feedback is a sheet in the app; it goes to the team through the credit desk thread ("Feedback: …", public, no personal details) and the desk thanks the person without a model call; the daemon logs it as 'feedback'.
- F51 (p013): the wallet page said nothing about the pending request. X51: with no credit yet, the wallet page says the request is with the officer (or that the desk answered) and the button leads to the desk.
- F52 (p012, p013, p014): a Done box after every chat line. X52: chat lines, the ask and the feedback send quietly (progress sheet only, no OK).
- F53 (p014): "stake" and "lines" unexplained. X53: Help defines stake; the officer no longer uses either word.
- F54 (p012, p014): a practice-money app for a real bus pass or sewing machine: the welcome already says so in the first line; the Try page says it; no change.
- H7: the world's desk stake is finite; re-fund before each run of ten personas (fund-desk.mjs, 500).
- Budgets in the world officer for the loop: 4 USD an hour, 30 a day, 8 model calls per applicant a day; the live officer keeps the defaults (0.75 an hour, 3 a day, 6 per applicant).

## Batch 6 (p015 Luis desktop, p016 Elena, p017 Olu). All three got the loan and paid it back (p016 borrowed again at once); 21, 26, 23 commands. First batch with no blocker inside the app; the re-funded desk and the serialized officer held up with three applicants at once (three grants in 15 s, no nonce error).
- F55 (p015): the form sends a sentence in the borrower's name that he never saw. X55: the ask screen shows the exact sentence before the tap ("This is sent to the credit officer in your name: …").
- F56 (p015, desktop): every line says "phone"; nothing about a shared computer. X56: the word follows the device (phone or computer); Help's "Done testing?" warns that anyone who can unlock a shared computer could open the wallet.
- F57 (p015): the recovery code box clips. X57: taller box; Help says the code reopens the wallet if the device is lost and that a loan stays yours either way (p016 F6).
- F58 (p015): "Includes the few cents the desk put here" after the loan closed. X58: shown only before the first loan or while one is open.
- F59 (p016, p017): "owe $2.02" against "paid $2.01, 1.28 cents": X59: the pay-back card states the exact interest so far in cents, so the ceiling-to-the-cent figure is explained.
- F60 (p017): "8k" and "8" got the same message in the Other box. X60: three messages: numbers only; at least $1; "$8 is more than the $5 maximum in this practice version".
- F61 (p017): no one line before the one tap. X61: the officer's note ends "Borrow $5.00 now: you get $5.00; pay back about $5.04 by <date>, less if sooner."
- F62 (p015, p017): one-tap Borrow with no confirm; fingerprint not visible. Kept: the OS prompt is the confirmation on a real device (H6).
- H5 again (p016 F1, p017 F3): the shared clock jumped between taps because other personas warped it; the brief already explains it. Next: run each batch's personas with staggered day warps, or one persona at a time per world.
- H8: the harness waited for "Your wallet" case-insensitively and the setup sheet says "Setting up your wallet", so the suites' create step could race the wallet creation (desk suite D01 failed twice). Fixed: create waits for the ask or home hash with no sheet open.

## Batch 7 (p018 Zara, p019 Ali, p020 Isla desktop). All three got and repaid the loan; 38, 33, 26 commands; no blocker in the app. Desk re-funded; serialized officer answered three at once.
- F63 (p018, p019; risky): the credit screen kept a live "Borrow $X now" box and button after the loan was made, with a fresh date; a slip would take a second loan. X63: the button and the offer hide while a loan is open; after a repaid loan it reads "Borrow again"; the exact due date is shown only once a loan exists.
- F64 (p018; privacy): the desk box took name, age, job, family and payday with no warning before Send. X64: the box's label says what not to write; a check for names, ages, numbers, family and work words asks "Before you send" with "Let me change it" first.
- F65 (p019, p020, p018): the late box still said "about $X by the due date if you wait" and nobody said whether being late costs a fee. X65: past the due date the forecast is dropped; the late line and Help say there is no late fee and what a default means.
- F66 (p019): "Pay this part" sits under the big green button. X66: more room between them.
- F67 (p020): the shared-computer warning came only in Help after borrowing. X67: the welcome says it on a computer.
- F68 (p018): the feedback box truncates silently. X68: "Up to 400 characters."
- F69 (p018, p019, p020): due date from the desk a day off the Done box. X69: the desk no longer names a date before the loan exists.
- H5 (all three): the shared fork clock jumped between taps ("Late by 5 days" seconds after borrowing). Next: one world per persona (three forks on separate ports), so no tester's warp touches another's loan.

## Batch 8 (p021 Idris, p022 Priya, p023 Kwame), one world each. All three got and repaid the loan; 24, 22, 22 commands; no blocker in the app; the clock still read 2028 on world 1 (fork warped by earlier runs), so forks are reset before each batch from batch 9.
- F70 (p021, p022, p023): owed shown rounded up ("$2.01") against "paid $2.00" and "0.05 cents". X70: one rounding everywhere (nearest cent, as the wallet shows), the exact interest in cents beside it; the "approval is a cent or two higher" sentence is gone ("Only what you owe is taken, to the fraction of a cent").
- F71 (p023): the landing page promises "tell us how it went" but nothing offers it after repayment. X71: the loan-closed box has a "Tell us how it went" button; More has it too; both open the in-app feedback sheet.
- F72 (p022): the sent desk line vanished for ten seconds. X72: the chat redraws right after a send, so the line shows at once with "the officer is reading your message".
- F73 (p022): "a wallet I never made". X73: the ask screen says the wallet is ready and what opens it.
- F74 (p022, p023): where is the real loan. X74: the welcome says there is none yet and that the test decides whether one should exist.
- F75 (p021): Help's wall of grey text. X75: the word list is a list. "Done testing?" now points at the recovery-code fold by name (p022 F10).
- F76 (p022, p023): the receipt names no amount. X76: the pay-back receipt carries the amount in its title.
- Kept: one-tap Borrow with the fingerprint as the confirmation (p021, p022); Receive under More (p021 F1: the friend's advice to "use Receive first" is from the old walkthrough).

## Batch 9 (p024 Amara, p025 Ravi desktop, p026 Chloe), one fresh world each (forks reset to the live head first; no clock artefacts reported). All three got and repaid the loan; 20, 18, 31 commands; no blocker in the app.
- F77 (p026, p024): "You can borrow up to $0.00" before asking read as a refusal; no word that a Pay back button appears later. X77: before the desk has answered, the card says "Ask the desk first" and that a Pay back button appears once something is owed.
- F78 (p024): Help missing from the top of the wallet page. X78: Help link in the wallet header too.
- F79 (p026): Help's Back dumps on the wallet instead of the form. X79: Back goes back in the history when there is one.
- F80 (p025): "0.38 cents of interest" read as 38 cents. X80: one helper everywhere: "0.38 of a cent of interest" under a cent, "1.49 cents of interest" above; the wallet's owed line adds "borrowed plus … so far" so "$5.00" with growing interest is explained (p025 F3).
- F81 (p024): "test dollars / tokens / practice money" meant nothing. X81: the welcome says "The dollars in it are not real: you cannot pay a bill or buy anything with them."
- F82 (p024): "backed by The credit desk", who is that. X82: "The credit desk (the AI officer that vouches for you)".
- F83 (p025): no end-of-session reminder on a shared computer. X83: the loan-closed box says it on a computer.
- H9 (p026 F1): `tap $5` unquoted lost the dollar sign in the shell and tapped the first control (Help). The brief now says to quote taps and typed text.
- H6 again (p025, p026): no fingerprint prompt in the harness.

## Batch 10 (p027 Femi, p028 Bella 72, p029 Tom dark mode). All three got and repaid the loan; 27, 29, 19 commands; no blocker in the app.
- F84 (p028; trust): asked how to get the money to the shop, the officer said "tap Borrow, yours to spend on your tool" after the loan was made. X84: officer rule: never say the test dollars can be spent or pay a bill; with an open loan, never say tap Borrow.
- F85 (p028, p029): the practice line should come before the headline's promise. X85: the welcome's first sentence is "This is a practice app: the dollars in it are not real and cannot pay a bill or buy anything."
- F86 (p027): "Done testing?" read as a question, the remove box frightened ("Nothing on the network is deleted" meant nothing). X86: "Forget this wallet on this phone", with plain words: the loan record and test dollars stay on the test network and the recovery code brings the wallet back.
- F87 (p029): the backing line rendered in monospace and split words. X87: plain font for the desk's name.
- F88 (p027, p029): "0.38 of a cent" hard to read; "0 of a cent" for a tiny amount (p028). X88: "less than a cent of interest (0.38 of a cent)"; "a fraction of a cent" under a hundredth.
- F89 (p028): Help never answers "how do I use this money". X89: the Test dollars entry says you cannot spend them anywhere.
- H6/H5 (all three): no fingerprint prompt in the harness; the calendar jumps after Get started because the fork's clock (the live chain's time at fork) differs from the phone's; forks are reset before every third batch.

## Batch 11 (p030 Rosa desktop, p031 Daniel, p032 Sofia). All three got and repaid the loan; 24, 21, 16 commands; no blocker.
- F90 (p032): the grey "Ask for this loan" gave no reason. X90: "Still to choose: what it is for, ..." names exactly what is missing.
- F91 (p032; desk): "What it is for is my business" read as a business. X91: officer rule: if no reason or a private one, ask once for a few words before granting.
- F92 (p030): "up to $3" against "Borrow $2.50 now". X92: the note says "agreed to $2.50 (what you asked for; the desk's limit for you is $3.00)".
- F93 (p030, p031): the friend's "use Receive first" (old walkthrough) found nothing. X93: the welcome says nothing needs fetching; the desk provides the cents.
- F94 (p030, p031): no "tomorrow" option. X94: a Tomorrow chip.
- F95 (p031): the officer says "Tap Borrow now", the button reads "Borrow $1.00 now". X95: the officer says "the Borrow button", never quoting a label.
- F96 (p032, p030): wallet $2.10 to $0.10 against "paid $2.00". X96: the close-out says the remaining cents are the desk's gift for the interest and can be kept.
