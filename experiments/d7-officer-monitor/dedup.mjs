// Dedup decision for the chain-only monitor (source only; nothing here posts, fetches or runs anywhere). Pure: no I/O, never throws.
// Question answered: given the candidate status comment and the board's existing comments, should this run post it?
//   post when the state differs from the newest monitor comment, or when that comment is old enough that a repeat (ALERT) or a
//   receipt (OK) is due; otherwise stay silent. The previous state is recovered from the board itself, because runs are ephemeral.
// Trust: only comments authored by the one expected login count as previous state. A lookalike from anyone else is ignored.
// Unknown state is never a reason to stay silent about an ALERT: an unusable previous comment means post. An unreadable or incomplete
// listing is the opposite case: the job fails visibly instead of posting blind, because blind posting is the flood this module prevents.
import { validateBoardComment } from './adapter.mjs';

const isInt = Number.isSafeInteger;
const RANGES = { maxCandidateAgeS: [60, 3600], repeatAlertS: [900, 86400], okReceiptS: [900, 86400], slackS: [0, 900], maxPerHour: [1, 60], capacityLimit: [100, 2500], clockSkewS: [1, 300] };
export const DEFAULTS = { maxCandidateAgeS: 600, repeatAlertS: 3600, okReceiptS: 21600, slackS: 300, maxPerHour: 8, capacityLimit: 2400, clockSkewS: 60, expectedLogin: 'github-actions[bot]' };
const LOGIN_RE = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?$/;
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
export const POST_REASONS = ['NO_PREVIOUS', 'PREVIOUS_UNUSABLE', 'CHANGED', 'REPEAT_ALERT', 'RECEIPT_OK'];
export const SKIP_REASONS = ['UNCHANGED_ALERT', 'UNCHANGED_OK', 'DUPLICATE_ID', 'RATE_CAP'];
export const HALT_REASONS = ['CONFIG_INVALID', 'CANDIDATE_INVALID', 'STALE_CANDIDATE', 'ID_COLLISION', 'LIST_UNAVAILABLE', 'LIST_INCOMPLETE', 'HALT_CAPACITY', 'INTERNAL'];

export function parseDedupConfig(raw) {
  if (raw === undefined) return { ok: true, config: { ...DEFAULTS } };
  const proto = raw && typeof raw === 'object' ? Object.getPrototypeOf(raw) : undefined;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || (proto !== Object.prototype && proto !== null)) return { ok: false };
  const known = new Set([...Object.keys(RANGES), 'expectedLogin']);
  if (Object.keys(raw).some((k) => !known.has(k))) return { ok: false };
  const cfg = {};
  for (const [k, [lo, hi]] of Object.entries(RANGES)) { const v = raw[k] === undefined ? DEFAULTS[k] : raw[k]; if (!isInt(v) || v < lo || v > hi) return { ok: false }; cfg[k] = v; }
  const login = raw.expectedLogin === undefined ? DEFAULTS.expectedLogin : raw.expectedLogin;
  if (typeof login !== 'string' || !LOGIN_RE.test(login)) return { ok: false };
  cfg.expectedLogin = login;
  return { ok: true, config: cfg };
}

// The monitor's own stream. The Actions bot identity is shared by every workflow in the repository, so the login alone does not say a comment
// is the monitor's. A comment is claimed by the monitor if its body carries the monitor's message id prefix. A claimed comment that does not
// validate is malformed monitor evidence: it still counts toward the rate cap and still makes the previous state unusable. A bot comment that
// makes no claim (an ordinary CI comment) is not part of the stream at all.
const CLAIM = 'm-officer-chain-monitor-';
export const claimsMonitor = (body) => typeof body === 'string' && body.includes(CLAIM);

// Read-back validator. The sender gate (validateBoardComment) demands the exact posted bytes, including the final newline, and a body read
// back from the board need not keep that newline. So this does NOT hand the raw body to the gate: it adds back at most ONE missing final
// newline, refuses carriage returns and any other whitespace difference, and only then applies the same gate. Returns { ok, status, codes, id, atMs } or { ok:false, why }.
export function parseMonitorComment(body) {
  try {
    if (typeof body !== 'string') return { ok: false, why: 'FORM' }; // size, carriage returns and every other byte difference are refused by the gate below
    const norm = body.endsWith('\n') ? body : body + '\n';
    const v = validateBoardComment(norm); if (!v.ok) return { ok: false, why: v.why };
    const j = JSON.parse(/^```json\n(\{.*\})\n```\n\n---\n/s.exec(norm)[1]);
    const t = /^Officer chain monitor (OK|ALERT)(?: \(([A-Z_]+(?:, [A-Z_]+)*)\))?: /.exec(j.i[0].x); if (!t) return { ok: false, why: 'TEXT' };
    const codes = t[2] ? [...new Set(t[2].split(', '))].sort() : [];
    const a = /, at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z|unknown)\. /.exec(j.i[0].x); // OBSERVATION time of the snapshot; delivery time is the comment's created_at
    const atMs = a && a[1] !== 'unknown' && Number.isFinite(Date.parse(a[1])) ? Date.parse(a[1]) : null;
    return { ok: true, status: t[1], codes, id: j.id, atMs };
  } catch { return { ok: false, why: 'ERROR' }; }
}

const halt = (reason) => ({ post: false, halt: true, reason });
const skip = (reason) => ({ post: false, halt: false, reason });
const go = (reason) => ({ post: true, halt: false, reason });

// listing: { count, comments } with count = the issue's comment count read BEFORE the list, comments = [{ id, created_at, login, body }] for the WHOLE
// thread (body may be null for other authors). A list shorter than the count is incomplete; one longer is fine (a comment arrived in between).
function checkListing(listing, cfg) {
  if (!listing || typeof listing !== 'object' || !Array.isArray(listing.comments) || !isInt(listing.count) || listing.count < 0) return { reason: 'LIST_UNAVAILABLE' };
  const seen = new Set(), rows = [];
  for (let i = 0; i < listing.comments.length; i++) {
    const c = listing.comments[i];
    if (!c || typeof c !== 'object' || !isInt(c.id) || c.id < 0 || typeof c.created_at !== 'string' || !ISO_RE.test(c.created_at) || !Number.isFinite(Date.parse(c.created_at)) || typeof c.login !== 'string' || !(c.body === null || typeof c.body === 'string') || seen.has(c.id)) return { reason: 'LIST_UNAVAILABLE' };
    seen.add(c.id); rows.push({ id: c.id, createdMs: Date.parse(c.created_at), login: c.login, body: c.body });
  }
  if (rows.length < listing.count) return { reason: 'LIST_INCOMPLETE' };
  if (rows.length >= cfg.capacityLimit) return { reason: 'HALT_CAPACITY' }; // here rows.length >= count, so this is the larger of the two
  return { rows };
}

// decide({ candidate, listing, nowMs, config }) -> { post, halt, reason }. A halt means "fail the job visibly"; post=false without halt means "quietly nothing to send".
export function decide(input) {
  try {
    const { candidate, listing, nowMs, config } = input; // destructured inside the try: decide(null) must halt, not throw
    const cfgR = parseDedupConfig(config); if (!cfgR.ok) return halt('CONFIG_INVALID');
    const cfg = cfgR.config;
    if (!isInt(nowMs) || nowMs <= 0) return halt('INTERNAL');
    const cand = parseMonitorComment(candidate); if (!cand.ok) return halt('CANDIDATE_INVALID');
    // A snapshot older than the freshness budget (a delayed job, a late manual retry) must not become a current-looking receipt; one dated in the future is not believed either.
    if (cand.atMs === null || nowMs - cand.atMs > cfg.maxCandidateAgeS * 1000 || cand.atMs > nowMs + cfg.clockSkewS * 1000) return halt('STALE_CANDIDATE');
    const l = checkListing(listing, cfg); if (l.reason) return halt(l.reason);
    const mine = l.rows.filter((r) => r.login === cfg.expectedLogin && claimsMonitor(r.body)); // the monitor's stream only
    for (const r of mine) { // the same id again: a retry of the same send is dropped quietly, but a DIFFERENT state under a used id is never silently discarded
      const p = parseMonitorComment(r.body); if (!p.ok || p.id !== cand.id) continue;
      return p.status === cand.status && p.codes.join() === cand.codes.join() ? skip('DUPLICATE_ID') : halt('ID_COLLISION');
    }
    if (mine.filter((r) => r.createdMs > nowMs - 3600000 && r.createdMs <= nowMs + cfg.clockSkewS * 1000).length >= cfg.maxPerHour) return skip('RATE_CAP');
    if (mine.length === 0) return go('NO_PREVIOUS');
    const newest = mine.reduce((a, r) => (r.createdMs > a.createdMs || (r.createdMs === a.createdMs && r.id > a.id) ? r : a));
    const prev = parseMonitorComment(newest.body);
    if (!prev.ok || newest.createdMs > nowMs + cfg.clockSkewS * 1000) return go('PREVIOUS_UNUSABLE'); // an unreadable or future-dated previous state is never a reason for silence
    if (prev.status !== cand.status || prev.codes.join() !== cand.codes.join()) return go('CHANGED');
    const ageS = (nowMs - newest.createdMs) / 1000;
    if (cand.status === 'ALERT') return ageS + cfg.slackS >= cfg.repeatAlertS ? go('REPEAT_ALERT') : skip('UNCHANGED_ALERT');
    return ageS + cfg.slackS >= cfg.okReceiptS ? go('RECEIPT_OK') : skip('UNCHANGED_OK');
  } catch { return halt('INTERNAL'); }
}
