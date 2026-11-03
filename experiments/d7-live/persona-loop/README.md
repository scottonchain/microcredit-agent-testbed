# Persona loop: a headless phone for usability testing

The harness the steward uses to run ordinary-person personas through the practice app: a Chromium phone (or desktop browser) with a virtual passkey authenticator, driven one tap at a time, against a copy of the live test pool with its own credit desk and AI officer. An agent without a platform authenticator can test the app with it; a person can read the same reports.

## What is here
- `world-server.mjs`: one practice world: a forked pool on a local node, a credit desk, an officer, a bundler, the app on a web port and a small control API (`/health`, `/fund`, `/warp`, `/state`, a stand-in faucet page).
- `browser-server.mjs`: the phone. One HTTP command at a time: `look`, `tap <words>`, `type <box> <text>`, `press`, `back`, `reload`, `home`, `wait <s>`, `scroll [up]`, `days <n>` (moves the world's clock), `tabs`, `switch <n>`, `closetab`, `shot`, `logs`, `done`. Every command returns the screen's text, what can be tapped, and a screenshot path.
- `p.mjs`: the command-line client (`node p.mjs PORT look`).
- `start-browser.sh N PORT [WORLD]`: starts the phone for persona N from `scenarios.json` (device, colour scheme, font scale), on world 1, 2 or 3.
- `brief.py N PORT`: prints the tester's brief: who they are, the rules (you only know what the screen tells you), the command budget, and the report format.
- `scenarios.json`: 100 personas; every fifth one on a desktop browser.
- `DESIGN-DECISIONS.md`: the usability decisions the runs produced.

## Run one world and one tester
From `experiments/d7-live` (Node 20 or later, Playwright's Chromium installed, `npm ci` done):

```bash
bash fork-up.sh                                    # local fork of Base Sepolia on :8545
cd persona-loop
D7_DIR=.. RPC_URL=http://127.0.0.1:8545 DAEMON_MODE=rules node world-server.mjs &   # DAEMON_MODE=claude needs the claude CLI
bash start-browser.sh 1 4201 &                     # persona 1 on world 1
python3 brief.py 1 4201                            # read the brief, then drive the phone:
node p.mjs 4201 look
node p.mjs 4201 tap "Get started"
```

Worlds 2 and 3: `PORT=8546 bash fork-up.sh`, then `CTRL_PORT=4181 WEB_PORT=4174 BUNDLER_PORT=4338 RPC_URL=http://127.0.0.1:8546 node world-server.mjs` (world 3: 8547, 4182, 4175, 4339). One world per tester keeps the clocks apart: `days` moves the whole world's clock.

## Rules for a tester
Write nothing personal to the credit desk: everything there is public on the test network. The dollars are test tokens; nothing is a real loan. Report what confused you, where you stopped and whether anything felt like real money, in your own words, with the screenshot numbers.

## Costs
The officer in `claude` mode makes one model call per applicant message (about 300 to 650 output tokens, a few cents each) through the `claude` CLI, with an hourly and a daily budget, a per-applicant cap and a cooldown after failures (`OFFICER_BUDGET_USD_PER_HOUR`, `OFFICER_BUDGET_USD_PER_DAY`, `OFFICER_MAX_LLM_PER_APPLICANT_PER_DAY`); past a limit a rules officer answers. `rules` mode makes no model calls.
