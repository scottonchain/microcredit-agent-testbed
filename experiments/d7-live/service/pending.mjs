// Persisted pending-operation journal for the officer service. An operation is written BEFORE its chain write, then
// advanced as it is sent and confirmed. After a restart, reconcile() decides what each unfinished operation needs
// from chain facts; it never replays on its own. States: intent -> sent -> done | abandoned.
import { readFileSync, writeFileSync, renameSync, mkdirSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';

export function openJournal(path) {
  mkdirSync(dirname(path), { recursive: true });
  const load = () => { if (!existsSync(path)) return { ops: {} }; try { return JSON.parse(readFileSync(path, 'utf8')); } catch { throw new Error('journal unreadable: refuse to run until a person looks at it'); } };
  const save = (j) => { const tmp = path + '.tmp'; writeFileSync(tmp, JSON.stringify(j)); renameSync(tmp, path); };
  return {
    begin(id, info, token) { const j = load(); if (j.ops[id] && j.ops[id].state !== 'done' && j.ops[id].state !== 'abandoned') throw new Error('operation already in flight: ' + id); j.ops[id] = { state: 'intent', info, token, at: Date.now() }; save(j); },
    sent(id, txHash) { const j = load(); if (!j.ops[id]) throw new Error('unknown operation'); j.ops[id].state = 'sent'; j.ops[id].txHash = txHash; j.ops[id].sentAt = Date.now(); save(j); },
    done(id, outcome) { const j = load(); if (!j.ops[id]) throw new Error('unknown operation'); j.ops[id].state = 'done'; j.ops[id].outcome = outcome; save(j); },
    abandon(id, why) { const j = load(); if (!j.ops[id]) throw new Error('unknown operation'); j.ops[id].state = 'abandoned'; j.ops[id].why = why; save(j); },
    open() { const j = load(); return Object.entries(j.ops).filter(([, o]) => o.state === 'intent' || o.state === 'sent').map(([id, o]) => ({ id, ...o })); },
    all() { return load().ops; },
  };
}

// Decide, for each unfinished operation, what is safe. Injected chain facts:
//   getReceipt(txHash) -> {status:'success'|'reverted'} | null (not mined or unknown)
//   alreadyApplied(op) -> true | false | null  (null = cannot tell)
// Results: 'confirm' (done on chain), 'failed' (mined and reverted), 'wait' (sent, no receipt yet), 'replay-allowed'
// (not applied and no transaction hash was recorded), 'hold' (cannot tell, or a recorded transaction stayed unmined past
// maxWaitMs: needs a person; never replay).
// The caller must journal the signed transaction's hash BEFORE broadcasting it (sent()), so that 'replay-allowed' means no
// transaction can exist. For the CreditDesk, reply() does not revert on an applicant who is not pending: a blind replay would
// add a second officer message, so alreadyApplied(op) must be 'the applicant is no longer in pending()'.
export async function reconcile(journal, { getReceipt, alreadyApplied, now = Date.now, maxWaitMs = 600_000 }) {
  const out = [];
  for (const op of journal.open()) {
    let decision;
    if (op.state === 'sent') {
      const r = await getReceipt(op.txHash).catch(() => null);
      if (r && r.status === 'success') decision = 'confirm';
      else if (r && r.status === 'reverted') decision = (await alreadyApplied(op).catch(() => null)) === true ? 'confirm' : 'failed';
      else if ((await alreadyApplied(op).catch(() => null)) === true) decision = 'confirm';
      else decision = (op.sentAt && now() - op.sentAt > maxWaitMs) ? 'hold' : 'wait'; // a signed transaction may still be mined; after maxWaitMs a person decides
    } else {
      const a = await alreadyApplied(op).catch(() => null);
      decision = a === true ? 'confirm' : a === false ? 'replay-allowed' : 'hold';
    }
    out.push({ id: op.id, state: op.state, decision });
  }
  return out;
}
