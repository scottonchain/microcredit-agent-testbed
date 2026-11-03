// The trust interview: a deterministic intake-and-scorecard module for the credit desk (D16, November 2026).
//
// decide({ thread, facts, maxLine }) -> { reply, backing, score, cost, reasons, dossier }
//
// The applicant's words are data. This module reads them only to fill the dossier's tagged fields (purpose,
// amount, term, repayment source, contradictions); the scorecard reads the dossier and the chain facts, never the
// transcript. No name, address, language, photograph or any prohibited-basis or proxy input exists here (see
// evidence/human-first-mainnet-20261103/compliance/adverse-action-notice-template.md section 4). Every weight is
// published in WEIGHTS; every printed reason is a code from the notice template's table (R01 to R14).
//
// Cost: this build makes no model call, so cost is 0 and the measured number is wall-clock microseconds per
// assessment (ASSESS_US in the result). A model-assisted extraction, if ever added, must report its dollar cost here.
//
// Shadow mode (MODE=interview in desk-daemon.mjs): the daemon logs this module's score, reasons and recommended
// backing on the 'replied' line and keeps the rules officer's backing and reply until the November 17 check.

export const VERSION = 'interview-0.1';

// Published weights. Score runs 0 to 100 after clamping.
export const WEIGHTS = Object.freeze({
  repayment_source_stated: 25,   // the applicant said where repayment comes from
  purpose_stated: 15,            // the applicant said what the money is for
  purpose_productive: 10,        // the purpose reads as a productive input (stock, tools, materials, a licence, a deposit on work)
  amount_within_cap: 10,         // the amount asked is at or under the desk's maximum
  term_stated: 10,               // a repayment date or horizon was given
  backer_present: 20,            // the desk (or a named backer, when the app has them) vouches with its own stake
  prior_repaid_each: 10,         // each loan fully repaid with this desk, up to prior_repaid_max
  prior_repaid_max: 20,
  contradiction: -20,            // amount or purpose changed between messages without explanation
});

// Admission line and the cap tiers, in dollars (bounded by the desk's maxLine at decision time).
export const TIERS = Object.freeze({ admit: 60, counter: 40, first_loan_cap: 10, repeat_loan_cap: 20 });

// Reason codes and their printed text (the notice template is the single source; keep these in step with it).
export const REASONS = Object.freeze({
  R01: 'You did not show us where the repayment would come from (no income, sales, order or other source was given).',
  R03: 'No person has placed a deposit to back your loan, and you did not place a deposit of your own.',
  R05: 'You did not tell us what the money is for, or the purpose you gave is not one our rules cover (we lend for a business input: stock, tools, a licence, a deposit on work).',
  R07: 'What you told us about the amount or the purpose does not match what you told us earlier.',
  R08: 'You already have a loan with us that is not yet repaid; one loan at a time.',
  R09: 'A previous loan with us is recorded as unpaid; it must be settled first.',
  R14: 'The most we lend on a first loan is the desk\'s limit; you asked for more.',
});

const PRODUCTIVE = /\b(stock|inventory|supplies|materials?|tools?|machine|equipment|licen[cs]e|permit|deposit|rent for (the|my) (shop|stall|kiosk)|ingredients|seeds?|fertili[sz]er|parts|repair|phone for (work|my business)|boda|fuel for (work|deliver)|wholesale|goods to sell|resell|market stall|shop|business|customers?|orders?)\b/i;
const REPAY_SOURCE = /\b(sales?|customers?|orders?|wages?|salary|pay ?cheque|paycheck|pay ?day|job|work|income|profits?|harvest|tips|clients?|contract|invoice|commission|allowance|pension|remittance|gig)\b/i;
const TERM = /\b(in (a|one|two|three) weeks?|in \d+ days?|in 30 days|within (a|one|two|three) (weeks?|months?)|by (friday|monday|tuesday|wednesday|thursday|saturday|sunday|the end of the month|month end|next week|next month)|next (week|month|pay ?day|friday)|end of (the )?month|when (i|we) (get|am|are) paid|after (the|my) (harvest|sale|job|order))\b/i;
const TEMPLATE = /^I need \$(\d+(?:\.\d+)?) for (.{1,160})\. I can pay it back (in a week|in two weeks|in 30 days)\.$/;
const DECLINE_SELF = /\b(not for me|for (someone|somebody) else|my (friend|brother|sister|cousin|boss) (needs|wants|asked)|on behalf of)\b/i;

const clean = (t) => String(t ?? '').replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 500);
const amountsIn = (t) => [...t.matchAll(/\$\s*(\d+(?:\.\d+)?)|\b(\d+(?:\.\d+)?)\s*(?:dollars?|usd|bucks)\b/gi)].map((m) => Number(m[1] ?? m[2])).filter((n) => Number.isFinite(n) && n > 0);

// Build the dossier from the applicant's messages only (from === 0). Each field carries a tag: 'stated' (from the
// applicant's words), 'verified' (from the chain), or 'none'.
export function dossier(thread, facts) {
  const mine = (thread || []).filter((m) => Number(m.from) === 0).map((m) => clean(m.text)).filter(Boolean);
  const all = mine.join(' | ');
  const d = { messages: mine.length, amount: { value: null, tag: 'none' }, purpose: { text: null, tag: 'none', productive: false }, term: { text: null, tag: 'none' }, repayment_source: { text: null, tag: 'none' }, backing: { value: Number(facts?.backing) || 0, desk: facts?.deskBacks !== false, tag: 'verified' }, history: { repaid: Number(facts?.repaid) || 0, open: Number(facts?.open) || 0, defaulted: !!facts?.defaulted, tag: 'verified' }, contradictions: [], not_for_self: false };
  // The app's structured ask is the strongest statement: amount, purpose and term in one line.
  const tm = mine.map((t) => TEMPLATE.exec(t)).filter(Boolean);
  if (tm.length) { const last = tm[tm.length - 1]; d.amount = { value: Number(last[1]), tag: 'stated' }; d.purpose = { text: last[2], tag: 'stated', productive: PRODUCTIVE.test(last[2]) }; d.term = { text: last[3], tag: 'stated' }; }
  // Free text fills what the template did not.
  const amts = amountsIn(all);
  if (d.amount.value === null && amts.length) d.amount = { value: amts[amts.length - 1], tag: 'stated' };
  if (d.purpose.text === null) { const m = all.match(/\b(?:for|to buy|to pay for|to get|so (?:i|we) can)\s+([^.|!?]{3,120})/i); if (m) d.purpose = { text: m[1].trim(), tag: 'stated', productive: PRODUCTIVE.test(m[1]) }; }
  if (d.term.text === null) { const m = all.match(TERM); if (m) d.term = { text: m[0], tag: 'stated' }; }
  { const m = all.match(/\b(?:pay (?:it )?back|repay|pay you)[^.|]{0,80}?\b(from|with|when|after|out of)\s+([^.|]{3,100})/i) || all.match(/\b(from|with)\s+(my|the|our)\s+([^.|]{3,80}?)\b(sales?|wages?|salary|income|job|customers?|orders?|profits?|harvest|tips|clients?|pay)\b/i); if (m && REPAY_SOURCE.test(m[0])) d.repayment_source = { text: m[0].trim(), tag: 'stated' }; else if (REPAY_SOURCE.test(all) && /\b(pay|repay)\b/i.test(all)) d.repayment_source = { text: (all.match(REPAY_SOURCE) || [''])[0], tag: 'stated' }; }
  // Contradictions: more than one distinct amount, or two template asks with different purposes.
  const distinct = [...new Set(amts.map((n) => Math.round(n)))]; if (distinct.length > 1) d.contradictions.push({ field: 'amount', values: distinct });
  if (tm.length > 1) { const ps = [...new Set(tm.map((m) => m[2].toLowerCase()))]; if (ps.length > 1) d.contradictions.push({ field: 'purpose', values: ps }); }
  d.not_for_self = DECLINE_SELF.test(all);
  return d;
}

// The scorecard: deterministic, published weights, principal reasons in weight order.
export function score(d, maxLine) {
  const factors = []; let s = 0;
  const add = (name, pts, ok, code) => { factors.push({ name, pts: ok ? pts : 0, ok, code: ok ? null : code }); if (ok) s += pts; };
  add('repayment_source_stated', WEIGHTS.repayment_source_stated, d.repayment_source.tag === 'stated', 'R01');
  add('purpose_stated', WEIGHTS.purpose_stated, d.purpose.tag === 'stated', 'R05');
  add('purpose_productive', WEIGHTS.purpose_productive, d.purpose.productive, null);
  add('amount_within_cap', WEIGHTS.amount_within_cap, d.amount.value !== null && d.amount.value <= maxLine, d.amount.value === null ? null : 'R14');
  add('term_stated', WEIGHTS.term_stated, d.term.tag === 'stated', null);
  // On the testnet desk the desk itself vouches for the cohort with its own stake (deskBacks, default true); in the
  // named-cohort build the backer is a named person's deposit or the applicant's own. A score never creates an
  // unbacked line: with neither, R03 is a hard rule below, not a weight.
  add('backer_present', WEIGHTS.backer_present, d.backing.value > 0 || d.backing.desk, 'R03');
  const repaidPts = Math.min(WEIGHTS.prior_repaid_max, d.history.repaid * WEIGHTS.prior_repaid_each); factors.push({ name: 'prior_repaid', pts: repaidPts, ok: repaidPts > 0, code: null }); s += repaidPts;
  if (d.contradictions.length) { factors.push({ name: 'contradiction', pts: WEIGHTS.contradiction, ok: false, code: 'R07' }); s += WEIGHTS.contradiction; }
  s = Math.max(0, Math.min(100, s));
  // Hard rules precede the score (officer rule: hard gates before statistical scoring).
  const hard = [];
  if (d.history.defaulted) hard.push('R09');
  if (d.history.open > 0) hard.push('R08');
  if (d.not_for_self) hard.push('R05');
  if (!(d.backing.value > 0 || d.backing.desk)) hard.push('R03');
  return { score: s, factors, hard };
}

// Map score and hard rules to a cap in whole dollars, bounded by the desk's maximum, and to the printed reasons.
export function cap({ score: s, factors, hard }, d, maxLine) {
  const repeat = d.history.repaid > 0;
  const tier = Math.min(maxLine, repeat ? TIERS.repeat_loan_cap : TIERS.first_loan_cap);
  const asked = d.amount.value === null ? null : Math.max(1, Math.round(d.amount.value));
  const reasons = [];
  if (hard.length) return { backing: 0, outcome: 'decline', reasons: hard.slice(0, 4) };
  // A contradiction between the applicant's statements caps the outcome at a counter-offer and is always printed.
  const contradicted = d.contradictions.length > 0;
  const missing = factors.filter((f) => !f.ok && f.code).sort((a, b) => Math.abs(WEIGHTS[b.name] ?? 20) - Math.abs(WEIGHTS[a.name] ?? 20)).map((f) => f.code);
  if (s >= TIERS.admit && !contradicted) { const want = asked ?? tier; const b = Math.min(tier, want); if (asked !== null && asked > tier) reasons.push('R14'); return { backing: b, outcome: asked !== null && asked > tier ? 'counter' : 'grant', reasons: reasons.slice(0, 4) }; }
  if (s >= TIERS.counter) { const b = Math.max(1, Math.min(Math.floor(tier / 2), asked ?? tier)); return { backing: b, outcome: 'counter', reasons: (contradicted ? ['R07'] : []).concat(missing.filter((c) => c !== 'R07')).slice(0, 4) }; }
  return { backing: 0, outcome: 'decline', reasons: missing.slice(0, 4) };
}

const sanitizeReply = (t) => String(t || '').replace(/https?:\/\/\S+/gi, '[link removed]').replace(/0x[0-9a-fA-F]{6,}/g, '[address removed]').replace(/\s+/g, ' ').trim().slice(0, 420);

// The reply the interview would send. It asks at most one thing at a time, in plain words, and prints the principal
// reasons on a decline (the adverse-action rule), never a score number.
export function phrase(d, verdict, maxLine) {
  if (verdict.outcome === 'decline') {
    const why = verdict.reasons.map((c) => REASONS[c]).filter(Boolean).slice(0, 2).join(' ');
    return sanitizeReply(`I am not able to back a loan right now. The main reasons: ${why} If something changes or you can tell us more, write again any time.`);
  }
  if (d.purpose.tag !== 'stated') return sanitizeReply(`Happy to help. In a few words, what is the money for?`);
  if (d.repayment_source.tag !== 'stated') return sanitizeReply(`Thanks. One more thing: where will the repayment come from (for example sales, wages, a customer's order)?`);
  if (verdict.outcome === 'counter') return sanitizeReply(`Thanks. The desk can back you with $${verdict.backing} of test credit for now, less than you asked. Tap Borrow when you are ready; you pay it back within 30 days.`);
  return sanitizeReply(`Thanks. The desk backs you with $${verdict.backing} of test credit. Tap Borrow when you are ready; you pay it back within 30 days.`);
}

export function decide({ thread, facts, maxLine }) {
  const t0 = process.hrtime.bigint();
  const ml = Math.max(1, Math.floor(Number(maxLine) || 1));
  const d = dossier(thread, facts);
  const sc = score(d, ml);
  let verdict = cap(sc, d, ml);
  // Not enough said yet and no hard rule: ask (at most two questions, so up to three applicant messages), keep the
  // current backing as the rules officer does; the score is still logged.
  if (!sc.hard.length && (d.purpose.tag !== 'stated' || d.repayment_source.tag !== 'stated') && d.messages < 3) verdict = { backing: Math.round(d.backing.value), outcome: 'ask', reasons: [] };
  const reply = phrase(d, verdict, ml);
  const backing = Math.max(0, Math.min(ml, Math.round(Number(verdict.backing) || 0)));
  const assessUs = Number((process.hrtime.bigint() - t0) / 1000n);
  return { reply, backing, score: sc.score, cost: 0, reasons: verdict.reasons, outcome: verdict.outcome, factors: sc.factors, dossier: d, version: VERSION, ASSESS_US: assessUs };
}

// `node interview.mjs <synthetic.json>` prints a shadow-scoring table for a synthetic applicant set.
if (process.argv[1] && /interview\.mjs$/.test(process.argv[1]) && process.argv[2]) {
  const { readFileSync } = await import('node:fs');
  const set = JSON.parse(readFileSync(process.argv[2], 'utf8'));
  const rows = set.applicants.map((a) => { const r = decide({ thread: a.thread, facts: a.facts, maxLine: set.maxLine }); return { id: a.id, expect: a.expect, outcome: r.outcome, backing: r.backing, score: r.score, reasons: r.reasons.join(','), us: r.ASSESS_US, match: a.expect === r.outcome }; });
  console.table(rows);
  const matched = rows.filter((r) => r.match).length; const us = rows.reduce((a, r) => a + r.us, 0) / rows.length;
  console.log(JSON.stringify({ version: VERSION, applicants: rows.length, outcome_matches: matched, mean_assess_us: Math.round(us), cost_usd_per_assessment: 0 }));
}
