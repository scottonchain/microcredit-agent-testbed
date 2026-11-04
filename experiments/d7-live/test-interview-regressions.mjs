import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dossier, decide } from './interview.mjs';
const cases = JSON.parse(readFileSync(new URL('./interview-regressions.json', import.meta.url), 'utf8')).cases;
for (const c of cases) test(c.id, () => {
  const thread = c.messages.map(text => ({ from: 0, text }));
  const facts = { backing: 5, open: 0, repaid: 0, defaulted: false };
  const d = dossier(thread, facts);
  if ('source' in c) assert.equal(d.repayment_source.tag, c.source);
  if ('self' in c) assert.equal(d.not_for_self, !c.self);
  if ('amount' in c) assert.equal(d.amount.value, c.amount);
  if ('amountConflict' in c) assert.equal(d.contradictions.some(x => x.field === 'amount'), c.amountConflict);
  if ('productive' in c) assert.equal(d.purpose.productive, c.productive);
  if ('term' in c) assert.equal(d.term.text, c.term);
  const r = decide({ thread, facts, maxLine: 10 });
  if (c.source === 'none') assert.notEqual(r.outcome, 'grant');
});
