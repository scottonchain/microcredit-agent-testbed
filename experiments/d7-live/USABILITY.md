# Usability rules and the persona loop

Rules (operator, 2026-11-03), binding for this app and its site pages:

1. Every tap or click a person has to make is inefficiency. Keep the count as low as possible and count it.
2. A person never follows a step-by-step outside the app: no external faucet walk, no install instructions, no copy-and-paste ritual. If the app needs something from elsewhere, the app does it or does without it.
3. People must be able to use it without having to think. The judges are usability testers playing ordinary people who just need a small loan, not developers.
4. It works right on a phone and on a desktop browser, from the same link.
5. On Android, putting the app on the home screen is one button.

## The persona loop

A persona is a short brief (a name, an age, a job, a device, how comfortable they are with phones, what they need the money for, and one or two things that will happen today: a mistyped amount, a message to the credit desk in broken sentences, coming back twenty-five days later). A subagent plays the persona on a headless phone or desktop browser against a local fork of the live pool, with a virtual passkey and a stand-in faucet page. It can only see what is on the screen (text, buttons, screenshots) and acts through a tool that taps, types, scrolls, waits and "comes back in N days". It writes a report in the person's words: what happened, where it got stuck, how bad each problem was, what it thinks it owes and when, and what felt unsafe.

Each report is read, the problems are fixed in the app (or marked as accepted with a reason), the tests are re-run, and the next persona starts. The loop runs for 100 personas; the counts that matter are taps to the first loan, taps to repay, and the share of personas that finish without a blocking problem. Findings and fixes are logged per iteration in the steward's loop log and summarised in the repository when a batch ships.

Nothing in the loop touches the live pool, real money or real people; personas are fictional and the fork is local.
