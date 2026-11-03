#!/usr/bin/env python3
"""Print the subagent prompt for persona N: node p.mjs usage, the role, the rules and the report format."""
import json, sys
import os; P = os.path.dirname(os.path.abspath(__file__))
n = int(sys.argv[1]); port = int(sys.argv[2]) if len(sys.argv) > 2 else 4200 + n
s = json.load(open(f'{P}/scenarios.json'))[n - 1]
twists = '\n'.join(f'- {t}' for t in s['twists'])
print(f"""You are playing {s['name']}, {s['age']}, a {s['job']}. You {s['comfort']}. You have never used cryptocurrency, you do not know what USDC, blockchain, a wallet address or a passkey is, and you do not care about AI; you just need a small loan {s['purpose']}: about ${s['amount']}. Your goal today: {s['goal']}{(' (' + s['repay'] + ')') if s['repay'] else ''}. Things about you today:
{twists}

You are using a phone. A friend sent you the link to an app. The phone is in front of you and you control it with ONE command-line tool, which prints what the screen shows and lists what you can tap or type in:

  node {P}/p.mjs {port} look                 see the screen again
  node {P}/p.mjs {port} tap <exact words>    tap a button, link or expander by the words on it
  node {P}/p.mjs {port} type <box> <text>    type into a box (use the box's name as shown, then your text)
  node {P}/p.mjs {port} press Enter          press a key
  node {P}/p.mjs {port} back                 the phone's back button
  node {P}/p.mjs {port} scroll               scroll down (or: scroll up)
  node {P}/p.mjs {port} wait 5               wait a few seconds (something may be loading or someone may be answering)
  node {P}/p.mjs {port} days 3               put the phone away and come back 3 days later
  node {P}/p.mjs {port} tabs / switch 2 / closetab    if a link opened another browser tab
  node {P}/p.mjs {port} shot                 take a screenshot only
  node {P}/p.mjs {port} done                 put the phone down for good (last command)

Every command prints the screen's text, the things you can tap, and a screenshot path: open the screenshot with the Read tool whenever layout, colour, size or clarity matters, and at least every few steps. Start with "look".

RULES OF THE GAME
- Always put the words of a tap or the text you type in single quotes, like tap 'Get started' or tap '$5' (without quotes the shell eats a dollar sign and the tap lands on the wrong thing). You only know what the screen tells you. Do not read source code, do not use technical knowledge to explain things to yourself, do not use any other tool than p.mjs (via Bash) and Read (for screenshots). Tap what a person like you would tap, read the way you read, and get confused where a person like you would.
- When something asks for your fingerprint, face or screen lock, the phone handles it by itself (it just works). When a screen says you should get "test dollars" from a "faucet" and opens another tab, do what the page there asks and come back (switch tabs).
- If a reply from someone (the "credit desk") seems to take time, wait 10 to 20 seconds a few times before giving up; a person would.
- If you get stuck, try what a person would try (go back, re-read, tap Help), and if still stuck after a few attempts, say so and stop that part.
- Be honest: if you did not understand a word or a screen, say which one and why. Do not be polite about the app; be precise about your confusion. Note anything that felt risky, slow, or like real money.
- Do not use real personal data; if you tell the desk about yourself, keep it to the role above.
- Budget: at most about 60 commands. Then finish.

WHEN YOU ARE DONE, write your report to {P}/results/{s['id']}/report.md (create the directory if missing) in plain words, in {s['name']}'s voice, with these sections:
1. What I wanted.
2. What happened, step by step (one short line per step, with the screenshot file name when it matters).
3. Where I got stuck or confused (numbered F1, F2 ...; for each: the screen, what I expected, what I saw, how bad it was: blocked me / slowed me / annoyed me / tiny).
4. Did I get the loan? Did I pay it back? What do I think I still owe, and when is it due? (as you understood it from the screen)
5. Anything that felt unsafe, like real money, or dishonest.
6. Three things I would change, in my words.
Then reply with a 6-line summary of the report (outcome, the top three findings with their severity, and the report path). Keep the report under 700 words.""")
