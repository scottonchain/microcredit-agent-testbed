// Sole-writer lease with a fencing token for the credit-desk officer service. Offline-testable: plain files, injected clock.
// One state file (lease.json) holds {owner, token, expiresAt}; every change happens under a short exclusive lock
// (lease.lock, created with O_EXCL). The token only ever increases: a new holder after expiry gets token+1, so a
// worker that was paused past its expiry can be refused (StaleWriter) before any chain write.
import { openSync, closeSync, writeSync, readFileSync, writeFileSync, renameSync, unlinkSync, statSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

export class StaleWriter extends Error { constructor(msg) { super(msg); this.name = 'StaleWriter'; } }

const LOCK_STALE_MS = 10_000; // a crashed process may leave the short lock behind; break it after this long
function withLock(dir, now, fn) {
  const lock = join(dir, 'lease.lock');
  for (let i = 0; i < 2; i++) {
    let fd;
    try { fd = openSync(lock, 'wx'); }
    catch (e) {
      if (e.code !== 'EEXIST') throw e;
      let age = 0; try { age = now() - statSync(lock).mtimeMs; } catch { continue; }
      if (age > LOCK_STALE_MS) { try { unlinkSync(lock); } catch {} continue; }
      throw new Error('lease lock busy');
    }
    try { writeSync(fd, String(process.pid)); return fn(); } finally { closeSync(fd); try { unlinkSync(lock); } catch {} }
  }
  throw new Error('lease lock busy');
}
const read = (dir) => { try { return JSON.parse(readFileSync(join(dir, 'lease.json'), 'utf8')); } catch { return null; } };
const write = (dir, v) => { const tmp = join(dir, 'lease.json.tmp'); writeFileSync(tmp, JSON.stringify(v)); renameSync(tmp, join(dir, 'lease.json')); };

export function createLease({ dir, owner, ttlMs = 60_000, now = Date.now }) {
  mkdirSync(dir, { recursive: true });
  let mine = null; // {token, expiresAt} as last granted to this instance
  return {
    // Take the lease if it is free or expired. Never takes a live lease from another owner.
    acquire() {
      return withLock(dir, now, () => {
        const cur = read(dir), t = now();
        if (cur && cur.expiresAt > t && cur.owner !== owner) return { ok: false, reason: 'held', holder: cur.owner, expiresAt: cur.expiresAt };
        const token = (cur ? cur.token : 0) + (cur && cur.owner === owner && cur.expiresAt > t ? 0 : 1);
        mine = { token, expiresAt: t + ttlMs }; write(dir, { owner, token, expiresAt: mine.expiresAt });
        return { ok: true, token };
      });
    },
    // Extend the lease. Refuses if another owner holds a newer token, or ours already lapsed and was taken.
    renew() {
      return withLock(dir, now, () => {
        const cur = read(dir), t = now();
        if (!mine || !cur || cur.token !== mine.token || cur.owner !== owner) throw new StaleWriter('lease lost: another writer holds a newer token');
        if (cur.expiresAt <= t) throw new StaleWriter('lease expired; re-acquire before writing');
        mine.expiresAt = t + ttlMs; write(dir, { owner, token: mine.token, expiresAt: mine.expiresAt }); return mine.token;
      });
    },
    // Call immediately before every chain write: throws StaleWriter unless this instance still holds the live, newest token.
    assertHolder() {
      const cur = read(dir), t = now();
      if (!mine || !cur || cur.token !== mine.token || cur.owner !== owner) throw new StaleWriter('not the lease holder (newer token exists)');
      if (cur.expiresAt <= t) throw new StaleWriter('lease expired');
      return mine.token;
    },
    release() {
      return withLock(dir, now, () => {
        const cur = read(dir);
        if (mine && cur && cur.token === mine.token && cur.owner === owner) write(dir, { owner, token: cur.token, expiresAt: 0 }); // keep the token so it never goes backwards
        mine = null;
      });
    },
    get token() { return mine ? mine.token : null; },
  };
}
