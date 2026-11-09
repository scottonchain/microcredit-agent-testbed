// The poll cycle of the officer service, composed from the hardened pieces. All chain access is injected, so it runs
// offline in tests. NOT wired into desk-daemon.mjs and not activated: it is the proven shape of the replacement loop.
import { reconcile } from './pending.mjs';
import { recordPoll } from './status.mjs';
import { withTimeout } from './timing.mjs';

export function createWorker({ lease, journal, statusPath, chain, now = Date.now, callTimeoutMs = 30_000, receiptTimeoutMs = 90_000 }) {
  return {
    // One cycle. Returns what happened; throws only StaleWriter-class errors the caller must treat as "stop writing".
    async pollOnce() {
      const got = lease.token ? (lease.renew(), { ok: true }) : lease.acquire();
      if (!got.ok) return { ran: false, reason: got.reason };
      const result = { ran: true, replied: [], held: [], waited: [], confirmed: [], failed: [] };
      let pollOk = true, lastReplyAt = null, lostLease = false;
      try {
        // 1) Reconcile unfinished operations from a previous run BEFORE any new write.
        const decisions = await reconcile(journal, {
          getReceipt: (tx) => withTimeout(chain.receipt(tx), callTimeoutMs, 'receipt'), now,
          alreadyApplied: (op) => withTimeout(chain.applied(op.info.applicant), callTimeoutMs, 'applied'),
        });
        const blocked = new Set();
        for (const d of decisions) {
          const op = journal.all()[d.id];
          if (d.decision === 'confirm') { journal.done(d.id, 'confirmed-on-chain'); result.confirmed.push(d.id); }
          else if (d.decision === 'failed') { journal.abandon(d.id, 'mined and reverted'); result.failed.push(d.id); }
          else if (d.decision === 'wait') { blocked.add(op.info.applicant); result.waited.push(d.id); }
          else if (d.decision === 'hold') { blocked.add(op.info.applicant); result.held.push(d.id); }
          else if (d.decision === 'replay-allowed') { journal.abandon(d.id, 'not applied and no transaction recorded; will be handled as a fresh item'); }
        }
        // 2) New work: one journaled write at a time, fenced.
        const pending = await withTimeout(chain.pending(), callTimeoutMs, 'pending');
        for (const applicant of pending) {
          if (blocked.has(applicant)) continue;
          const id = `reply:${applicant}`;
          const token = lease.assertHolder();
          journal.begin(id, { applicant }, token);
          lease.assertHolder(); // re-check after the journal write, immediately before the chain write
          // Sign first, journal the hash, then broadcast: a crash between these steps leaves a recorded hash to look up.
          const prepared = await withTimeout(chain.prepare(applicant, token), callTimeoutMs, 'prepare');
          journal.sent(id, prepared.txHash);
          lease.assertHolder(); // last check before the broadcast itself
          await withTimeout(prepared.broadcast(), callTimeoutMs, 'broadcast');
          const tx = prepared.txHash;
          const rc = await withTimeout(chain.receipt(tx), receiptTimeoutMs, 'receipt');
          if (rc && rc.status === 'success') { journal.done(id, 'success'); lastReplyAt = now(); result.replied.push(applicant); }
          else { journal.abandon(id, 'reply reverted'); result.failed.push(id); }
        }
      } catch (e) {
        if (e && e.name === 'StaleWriter') { lostLease = true; throw e; } // a worker that lost the lease writes no status: it must not read as ok
        pollOk = false; result.error = e && e.name || 'Error';
      } finally {
        if (!lostLease) recordPoll(statusPath, { now, lastReplyAt, openOps: journal.open().length, ok: pollOk });
      }
      return result;
    },
  };
}
