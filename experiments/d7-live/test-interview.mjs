// node --test experiments/d7-live/test-interview.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { decide, dossier, score, cap, WEIGHTS, TIERS, REASONS } from './interview.mjs';

const set = JSON.parse(readFileSync(new URL('./interview-synthetic.json', import.meta.url), 'utf8'));
const run = (id) => { const a = set.applicants.find((x) => x.id === id); return decide({ thread: a.thread, facts: a.facts, maxLine: set.maxLine }); };

test('schema: backing is an integer in 0..maxLine, reply under 420 chars with no links or addresses, score 0..100, cost a number', () => {
  for (const a of set.applicants) {
    const r = decide({ thread: a.thread, facts: a.facts, maxLine: set.maxLine });
    assert.ok(Number.isInteger(r.backing) && r.backing >= 0 && r.backing <= set.maxLine, a.id + ' backing ' + r.backing);
    assert.ok(typeof r.reply === 'string' && r.reply.length > 0 && r.reply.length <= 420, a.id + ' reply length');
    assert.ok(!/https?:\/\//i.test(r.reply) && !/0x[0-9a-fA-F]{6,}/.test(r.reply), a.id + ' reply carries a link or address');
    assert.ok(r.score >= 0 && r.score <= 100, a.id + ' score');
    assert.equal(typeof r.cost, 'number');
    assert.ok(Number.isInteger(r.ASSESS_US) && r.ASSESS_US >= 0);
  }
});

test('every synthetic applicant gets the expected outcome', () => {
  const misses = set.applicants.map((a) => ({ id: a.id, expect: a.expect, got: decide({ thread: a.thread, facts: a.facts, maxLine: set.maxLine }).outcome })).filter((x) => x.expect !== x.got);
  assert.deepEqual(misses, []);
});

test('hard rules precede the score: default and open loan decline with R09 / R08 whatever the score', () => {
  assert.deepEqual(run('s07-defaulted').reasons, ['R09']);
  assert.deepEqual(run('s08-open-loan').reasons, ['R08']);
  assert.equal(run('s07-defaulted').backing, 0);
});

test('a decline prints principal reasons from the code table and never a score number', () => {
  const r = run('s06-no-purpose-three-messages');
  assert.equal(r.outcome, 'decline');
  assert.ok(r.reasons.length >= 1 && r.reasons.every((c) => REASONS[c]));
  assert.ok(!/\b\d{1,3}\s*(points|score|\/100)\b/i.test(r.reply));
  assert.ok(/main reasons/i.test(r.reply));
});

test('above the cap is a counter-offer at the tier, with R14', () => {
  const r = run('s09-above-cap');
  assert.equal(r.outcome, 'counter'); assert.equal(r.backing, Math.min(set.maxLine, TIERS.first_loan_cap)); assert.ok(r.reasons.includes('R14'));
});

test('a repeat borrower reaches the repeat tier, bounded by maxLine', () => {
  const r = run('s10-repeat-borrower');
  assert.equal(r.outcome, 'grant'); assert.equal(r.backing, Math.min(set.maxLine, TIERS.repeat_loan_cap, 10));
  assert.ok(r.factors.find((f) => f.name === 'prior_repaid').pts === Math.min(WEIGHTS.prior_repaid_max, 2 * WEIGHTS.prior_repaid_each));
});

test('a contradiction costs its weight and is a printed reason', () => {
  const r = run('s11-contradiction');
  assert.ok(r.factors.find((f) => f.name === 'contradiction'));
  assert.ok(r.dossier.contradictions.some((c) => c.field === 'amount'));
});

test('applicant text is data: an injection changes nothing and its link and address never reach the reply', () => {
  const r = run('s14-injection');
  assert.equal(r.outcome, 'ask'); assert.equal(r.backing, 5);
  assert.ok(!/example\.invalid|0xabcdef/i.test(r.reply));
});

test('the dossier carries tags, not the transcript; no prohibited field exists', () => {
  const a = set.applicants[0]; const d = dossier(a.thread, a.facts);
  for (const k of Object.keys(d)) assert.ok(!/\b(name|address|age|sex|gender|race|religion|national|marital|language|photo|phone|email|employer)\b/i.test(k), 'field ' + k);
  assert.equal(d.purpose.tag, 'stated'); assert.equal(d.history.tag, 'verified');
});

test('weights are published and the score is the clamped sum of the factors', () => {
  const a = set.applicants[0]; const d = dossier(a.thread, a.facts); const s = score(d, set.maxLine);
  const sum = s.factors.reduce((x, f) => x + f.pts, 0);
  assert.equal(s.score, Math.max(0, Math.min(100, sum)));
  assert.ok(Object.isFrozen(WEIGHTS));
});

test('cap is bounded by maxLine even when the tier is larger', () => {
  const a = set.applicants.find((x) => x.id === 's10-repeat-borrower');
  const r = decide({ thread: a.thread, facts: a.facts, maxLine: 3 });
  assert.equal(r.backing, 3);
});

test('a reply says nothing a rules officer would not: no stake or line vocabulary', () => {
  for (const a of set.applicants) { const r = decide({ thread: a.thread, facts: a.facts, maxLine: set.maxLine }); assert.ok(!/\b(stake|credit line)\b/i.test(r.reply), a.id); }
});

test('cap(): explicit decline below the counter line', () => {
  const d = dossier([{ from: 0, text: 'money' }], { backing: 0, repaid: 0, open: 0, defaulted: false });
  const v = cap(score(d, 10), d, 10); assert.equal(v.outcome, 'decline'); assert.equal(v.backing, 0);
});
