// Delivery serializer: the ONLY place an alert-state item becomes something a sender may transmit. Items from toSend() and salvaged
// items from a damaged outbox are internal objects and may carry arbitrary keys or codes. This function restricts every message,
// normal or salvaged, to a validated occurrence id, a known kind, known codes and the static text for each code. Anything it
// cannot make safe is not sent: it returns { ok: false, quarantine } and the raw evidence (bounded in size) is for LOCAL storage
// only, never for a sender, a board or a log that leaves the host. It never throws.
import { OUTBOUND_DETAIL } from './collector.mjs';

const ID = /^(alert|repeat|recovery):o([1-9][0-9]{0,15})$/;
export const MAX_CODES = 32, MAX_RAW = 4096;
const raw = (x) => { try { return String(JSON.stringify(x)).slice(0, MAX_RAW); } catch { return '[unserializable]'; } };

export function serializeDelivery(item) {
  try {
    const q = (reason) => ({ ok: false, reason, quarantine: { reason, raw: raw(item) } });
    if (!item || typeof item !== 'object' || Array.isArray(item)) return q('BAD_ITEM');
    const m = typeof item.key === 'string' ? ID.exec(item.key) : null;
    if (!m) return q('BAD_ID');
    if (item.kind !== m[1]) return q('KIND_MISMATCH');
    if (!Number.isSafeInteger(item.seq) || item.seq < 1 || String(item.seq) !== m[2]) return q('SEQ_MISMATCH');
    if (!Array.isArray(item.codes) || item.codes.length > MAX_CODES || (item.kind !== 'recovery' && item.codes.length === 0)) return q('BAD_CODES');
    let altered = false;
    const codes = [...new Set(item.codes.map((c) => { if (typeof c === 'string' && Object.hasOwn(OUTBOUND_DETAIL, c)) return c; altered = true; return 'UNKNOWN_CODE'; }))].sort();
    const at = Number.isFinite(item.at) && Math.abs(item.at) <= 8.64e15 ? new Date(item.at).toISOString() : null;
    const message = { id: item.key, kind: item.kind, at, alerts: codes.map((code) => ({ code, detail: OUTBOUND_DETAIL[code] })) };
    return altered ? { ok: true, message, quarantine: { reason: 'CODES_ALTERED', raw: raw(item) } } : { ok: true, message };
  } catch { return { ok: false, reason: 'SERIALIZER_FAILURE', quarantine: { reason: 'SERIALIZER_FAILURE', raw: '[unavailable]' } }; }
}
