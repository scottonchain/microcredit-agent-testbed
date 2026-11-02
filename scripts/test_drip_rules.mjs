// node --test scripts/test_drip_rules.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DAILY_CAP_USDC, FLOOR_USDC, MAX_PER_RUN_ANY, loadAllowlist, parseAmount, runTitle, runsSince, spentToday, decide } from './drip_rules.mjs';

const list = loadAllowlist(JSON.parse(readFileSync(new URL('./drip_allowlist.json', import.meta.url), 'utf8')));
const treasury = list.get('0x2aa4069f65931e8b35ed11ac493b1c3ab9917212');
const officer = list.get('0xb88dc88d538a754f57cab344c1e09d02c129fcf2');
const base = { recipientBalance: 0, teamBalance: 180.2, spent: 0, teamIsRecipient: false };

test('allowlist carries the steward conditions', () => {
  assert.equal(treasury.maxPerRun, 25); assert.equal(treasury.maxBalance, 25);
  assert.equal(officer.maxPerRun, 5); assert.equal(officer.maxBalance, 5);
  assert.throws(() => loadAllowlist([{ address: '0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212', max_per_run: 26, max_balance: 1 }]));
  assert.throws(() => loadAllowlist([]));
});

test('amount parsing', () => {
  assert.equal(parseAmount('5'), 5); assert.equal(parseAmount('0.5'), 0.5);
  assert.equal(parseAmount('0'), null); assert.equal(parseAmount('-1'), null); assert.equal(parseAmount('5e1'), null); assert.equal(parseAmount(''), null);
});

test('default run for the officer passes; the officer stops at its balance cap', () => {
  assert.deepEqual(decide({ ...base, entry: officer, amount: 5, recipientBalance: 1.9 }), { ok: true });
  assert.equal(decide({ ...base, entry: officer, amount: 5, recipientBalance: 5 }).ok, false);
  assert.equal(decide({ ...base, entry: officer, amount: 10 }).ok, false);
});

test('the treasury may take 25 per run while below 25', () => {
  assert.deepEqual(decide({ ...base, entry: treasury, amount: 25, recipientBalance: 24.9 }), { ok: true });
  assert.equal(decide({ ...base, entry: treasury, amount: 25, recipientBalance: 25 }).ok, false);
  assert.equal(decide({ ...base, entry: treasury, amount: 25.01 }).ok, false);
});

test('floor, daily cap, allowlist and self-send', () => {
  assert.equal(decide({ ...base, entry: treasury, amount: 25, teamBalance: FLOOR_USDC + 24.99 }).ok, false);
  assert.deepEqual(decide({ ...base, entry: treasury, amount: 25, teamBalance: FLOOR_USDC + 25 }), { ok: true });
  assert.equal(decide({ ...base, entry: treasury, amount: 25, spent: DAILY_CAP_USDC - 24 }).ok, false);
  assert.deepEqual(decide({ ...base, entry: treasury, amount: 25, spent: DAILY_CAP_USDC - 25 }), { ok: true });
  assert.equal(decide({ ...base, entry: null, amount: 5 }).ok, false);
  assert.equal(decide({ ...base, entry: treasury, amount: 5, teamIsRecipient: true }).ok, false);
  assert.equal(decide({ ...base, entry: treasury, amount: null }).ok, false);
});

test('daily total from run titles: success and active count, dry runs and the current run do not, junk counts as the max', () => {
  const t = (amount, dry = false) => runTitle(amount, '0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212', dry);
  const runs = [
    { id: 1, status: 'completed', conclusion: 'success', display_title: t(25) },
    { id: 2, status: 'in_progress', conclusion: null, display_title: t(5) },
    { id: 3, status: 'completed', conclusion: 'failure', display_title: t(25) },
    { id: 4, status: 'completed', conclusion: 'success', display_title: t(25, true) },
    { id: 5, status: 'completed', conclusion: 'success', display_title: 'renamed by hand' },
    { id: 6, status: 'completed', conclusion: 'success', display_title: t(25) },
  ];
  assert.equal(spentToday(runs, '6'), 25 + 5 + MAX_PER_RUN_ANY);
  assert.equal(spentToday(runs, '999'), 25 + 5 + MAX_PER_RUN_ANY + 25);
});

test('runs since midnight UTC are selected by created_at, newest first', () => {
  const since = '2026-11-02T00:00:00Z';
  const runs = [
    { id: 1, created_at: '2026-11-02T17:50:33Z' },
    { id: 2, created_at: '2026-11-02T00:00:00Z' },
    { id: 3, created_at: '2026-11-01T23:59:59Z' },
    { id: 4 },
  ];
  assert.deepEqual(runsSince(runs, since).map((r) => r.id), [1, 2]);
});
