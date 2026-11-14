// Offline tests for the dedup decision, the read-back validator, the decide-post CLI and the draft workflow's use of them. Run: node test-dedup.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { boardMessage, boardComment, validateBoardComment } from './adapter.mjs';
import { parseDedupConfig, parseMonitorComment, decide, DEFAULTS, POST_REASONS, SKIP_REASONS, HALT_REASONS } from './dedup.mjs';
import { main as decideMain } from './decide-post.mjs';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) pass++; else { fail++; console.log('FAIL', n); } };
const here = dirname(fileURLToPath(import.meta.url));
const BOT = 'github-actions[bot]';
const NOW = Date.parse('2026-11-14T12:00:00Z');
const iso = (ms) => new Date(ms).toISOString().replace('.000Z', 'Z');
const ago = (s) => iso(NOW - s * 1000);

// ---- builders: bodies come from the real message builder, so the tests cannot drift from the sender's format ----
const mkOutcome = (codes) => ({ status: codes.length ? 'ALERT' : 'OK', outbound: { alerts: codes.map((code) => ({ code })) }, health: { endpoint: 'primary', blockNumber: 100, pendingCount: codes.length ? 1 : 0, oldestPendingAgeS: codes.length ? 900 : null } });
const body = (codes, minute = '20261114115500', atMs = NOW) => boardComment(boardMessage({ outcome: mkOutcome(codes), nowMs: atMs, idSuffix: minute }));
const MALFORMED = 'edited by hand, still carrying m-officer-chain-monitor-1';
const row = (id, ageS, bodyText, login = BOT) => ({ id, created_at: ago(ageS), login, body: bodyText });
const listing = (rows, count = rows.length) => ({ count, comments: rows });
const D = (codes, rows, extra = {}) => decide({ candidate: body(codes, '20261114120000'), listing: listing(rows, extra.count ?? rows.length), nowMs: NOW, config: extra.config });
const reasonOf = (r) => `${r.post ? 'POST' : r.halt ? 'HALT' : 'SKIP'}:${r.reason}`;

// ---- config ----
ok(parseDedupConfig(undefined).ok && JSON.stringify(parseDedupConfig(undefined).config) === JSON.stringify(DEFAULTS), 'no config means the documented defaults');
ok(parseDedupConfig({}).ok && parseDedupConfig({ okReceiptS: 3600 }).config.okReceiptS === 3600, 'a partial config keeps the other defaults');
for (const bad of [null, 5, 'x', [], { extra: 1 }, { repeatAlertS: 899 }, { unusableMaxPerDay: 0 }, { unusableMaxPerDay: 25 }, { maxCandidateAgeS: 59 }, { maxCandidateAgeS: 3601 }, { repeatAlertS: 86401 }, { repeatAlertS: 1000.5 }, { repeatAlertS: '3600' }, { okReceiptS: 899 }, { slackS: -1 }, { slackS: 901 }, { maxPerHour: 0 }, { maxPerHour: 61 }, { capacityLimit: 99 }, { capacityLimit: 2501 }, { clockSkewS: 0 }, { clockSkewS: 301 }, { expectedLogin: '' }, { expectedLogin: 'a b' }, { expectedLogin: 'x[bot]y' }, { expectedLogin: 5 }, { repeatAlertS: NaN }, { repeatAlertS: Infinity }])
  ok(parseDedupConfig(bad).ok === false, `config refuses ${JSON.stringify(bad)}`);
for (const good of [{ repeatAlertS: 900 }, { unusableMaxPerDay: 1 }, { unusableMaxPerDay: 24 }, { maxCandidateAgeS: 60 }, { maxCandidateAgeS: 3600 }, { repeatAlertS: 86400 }, { slackS: 0 }, { slackS: 900 }, { maxPerHour: 1 }, { maxPerHour: 60 }, { capacityLimit: 100 }, { capacityLimit: 2500 }, { clockSkewS: 1 }, { clockSkewS: 300 }, { expectedLogin: 'github-actions' }])
  ok(parseDedupConfig(good).ok, `config accepts the range edge ${JSON.stringify(good)}`);
ok(parseDedupConfig(Object.create({ repeatAlertS: 1000 })).ok === false, 'config refuses an object with an inherited prototype');
ok(parseDedupConfig(Object.assign(Object.create(null), { okReceiptS: 3600 })).ok, 'config accepts a null-prototype plain object');

// ---- the read-back validator is not the sender gate ----
{ const b = body([]);
  ok(validateBoardComment(b).ok && parseMonitorComment(b).ok, 'both accept the exact posted bytes');
  ok(!validateBoardComment(b.slice(0, -1)).ok, 'the sender gate refuses a body whose final newline was lost');
  ok(parseMonitorComment(b.slice(0, -1)).ok, 'the read-back parser accepts the same body without its final newline');
  ok(!parseMonitorComment(b + '\n').ok && !parseMonitorComment(b.slice(0, -1) + '\n\n').ok, 'a second trailing newline is refused');
  ok(!parseMonitorComment(b.replace(/\n/g, '\r\n')).ok && !parseMonitorComment(b.slice(0, -1) + '\r').ok, 'carriage returns are refused');
  ok(!parseMonitorComment(' ' + b).ok && !parseMonitorComment(b.replace('```json', '``` json')).ok, 'leading space or a changed fence is refused');
  const p = parseMonitorComment(b); ok(p.status === 'OK' && p.codes.length === 0 && p.id === 'm-officer-chain-monitor-20261114115500', 'an OK body gives status, no codes and its id');
  const a = parseMonitorComment(body(['RPC_UNAVAILABLE', 'PENDING_AGE'])); ok(a.ok && a.status === 'ALERT' && a.codes.join() === 'PENDING_AGE,RPC_UNAVAILABLE', 'an ALERT body gives its codes sorted');
  const tampered = b.replace('Officer chain monitor OK', 'Officer chain monitor OK!'); ok(!parseMonitorComment(tampered).ok, 'a changed message text is refused');
  const forged = body([]).replace('"op":"ok"', '"op":"alert"'); ok(!parseMonitorComment(forged).ok, 'a status that disagrees with its op is refused');
  const extra = body([]).replace('"v":2', '"v":2,"v":2'); ok(!parseMonitorComment(extra).ok, 'duplicate JSON keys are refused');
  for (const bad of [undefined, null, 5, {}, [], '', 'x', 'x'.repeat(5000)]) ok(!parseMonitorComment(bad).ok, `read-back parser refuses ${typeof bad === 'string' ? bad.slice(0, 6) : String(bad)}`); }

// ---- the decision matrix ----
const OK_ROW = (id, ageS, minute) => row(id, ageS, body([], minute));
const AL_ROW = (id, ageS, minute, codes = ['PENDING_AGE']) => row(id, ageS, body(codes, minute));
ok(reasonOf(D([], [])) === 'POST:NO_PREVIOUS', 'an empty board posts the first status');
// a status that differs while the code lists are equal still counts as a change (an ALERT with no codes is a different state from OK)
{ const alertNoCodes = boardComment(boardMessage({ outcome: { status: 'ALERT', outbound: { alerts: [] }, health: mkOutcome([]).health }, nowMs: NOW, idSuffix: '20261114450000' }));
  ok(parseMonitorComment(alertNoCodes).ok && parseMonitorComment(alertNoCodes).status === 'ALERT' && parseMonitorComment(alertNoCodes).codes.length === 0, 'an ALERT with no codes is a valid, distinct state');
  ok(reasonOf(D([], [row(5, 900, alertNoCodes)])) === 'POST:CHANGED' && reasonOf(decide({ candidate: alertNoCodes.replace('20261114450000', '20261114500000'), listing: listing([OK_ROW(5, 900, '20261114450000')]), nowMs: NOW })) === 'POST:CHANGED', 'OK and a code-less ALERT are different states in both directions'); }
// code order in a hand-made body does not matter: the parser sorts and de-duplicates
{ const sorted = body(['PENDING_AGE', 'RPC_STALE'], '20261114450000'); const swapped = sorted.replace('PENDING_AGE, RPC_STALE', 'RPC_STALE, PENDING_AGE');
  ok(swapped !== sorted && validateBoardComment(swapped).ok, 'a body with the codes in another order still passes the sender gate');
  ok(parseMonitorComment(swapped).codes.join() === 'PENDING_AGE,RPC_STALE', 'the read-back parser returns the codes sorted');
  const dup = sorted.replace('PENDING_AGE, RPC_STALE', 'PENDING_AGE, PENDING_AGE, RPC_STALE'); ok(validateBoardComment(dup).ok && parseMonitorComment(dup).codes.join() === 'PENDING_AGE,RPC_STALE', 'a repeated code is counted once');
  ok(reasonOf(decide({ candidate: body(['PENDING_AGE', 'RPC_STALE'], '20261114500000'), listing: listing([row(5, 900, swapped)]), nowMs: NOW })) === 'SKIP:UNCHANGED_ALERT', 'the same codes in another order are not a change'); }
ok(reasonOf(D([], [row(1, 100, 'human text', 'someone')])) === 'POST:NO_PREVIOUS', 'a board with only other authors has no previous monitor state');
ok(reasonOf(D([], [OK_ROW(5, 900, '20261114450000')])) === 'SKIP:UNCHANGED_OK', 'OK after a recent OK stays silent');
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 900, '20261114450000')])) === 'SKIP:UNCHANGED_ALERT', 'the same ALERT after a recent identical ALERT stays silent');
ok(reasonOf(D(['PENDING_AGE'], [OK_ROW(5, 900, '20261114450000')])) === 'POST:CHANGED', 'OK to ALERT posts at once');
ok(reasonOf(D([], [AL_ROW(5, 900, '20261114450000')])) === 'POST:CHANGED', 'ALERT to OK (recovery) posts at once');
ok(reasonOf(D(['RPC_UNAVAILABLE'], [AL_ROW(5, 900, '20261114450000')])) === 'POST:CHANGED', 'a different alert code posts at once');
ok(reasonOf(D(['PENDING_AGE', 'RPC_STALE'], [AL_ROW(5, 900, '20261114450000')])) === 'POST:CHANGED', 'an added alert code posts at once');
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 900, '20261114450000', ['PENDING_AGE', 'RPC_STALE'])])) === 'POST:CHANGED', 'a removed alert code posts at once');
ok(reasonOf(D(['RPC_STALE', 'PENDING_AGE'], [AL_ROW(5, 900, '20261114450000', ['PENDING_AGE', 'RPC_STALE'])])) === 'SKIP:UNCHANGED_ALERT', 'code order does not make a change');
// intervals, with the 300 s slack: ALERT repeats at 3600 s, OK receipt at 21600 s
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 3299, '20261114450000')])) === 'SKIP:UNCHANGED_ALERT', 'an ALERT 3299 s old is not yet repeated');
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 3300, '20261114450000')])) === 'POST:REPEAT_ALERT', 'an ALERT 3300 s old (3600 minus the 300 s slack) is repeated');
ok(reasonOf(D([], [OK_ROW(5, 21299, '20261114450000')])) === 'SKIP:UNCHANGED_OK', 'an OK 21299 s old is not yet re-sent');
ok(reasonOf(D([], [OK_ROW(5, 21300, '20261114450000')])) === 'POST:RECEIPT_OK', 'an OK 21300 s old gets its periodic receipt');
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 3300, '20261114450000')], { config: { slackS: 0 } })) === 'SKIP:UNCHANGED_ALERT' && reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 3600, '20261114450000')], { config: { slackS: 0 } })) === 'POST:REPEAT_ALERT', 'slack zero means the exact interval');
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 1800, '20261114450000')], { config: { repeatAlertS: 900 } })) === 'POST:REPEAT_ALERT', 'the ALERT repeat interval is configurable');
// the newest monitor comment is the state, whatever else is on the board
ok(reasonOf(D([], [AL_ROW(1, 5000, '20261114000000'), OK_ROW(2, 900, '20261114450000')])) === 'SKIP:UNCHANGED_OK', 'the newest monitor comment decides, not an older one');
ok(reasonOf(D([], [OK_ROW(2, 900, '20261114450000'), AL_ROW(1, 5000, '20261114000000')])) === 'SKIP:UNCHANGED_OK', 'list order does not matter, creation time does');
ok(reasonOf(D([], [OK_ROW(7, 900, '20261114450000'), AL_ROW(8, 900, '20261114450100')])) === 'POST:CHANGED', 'equal creation times are broken by the higher comment id');
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(5, 900, '20261114450000'), row(6, 60, 'a human note', 'someone')])) === 'SKIP:UNCHANGED_ALERT', 'newer comments by other people do not reset the state');
// trust: only the expected login
ok(reasonOf(D([], [OK_ROW(1, 7200, '20261114000000'), row(2, 60, body(['PENDING_AGE'], '20261114450000'), 'attacker')])) === 'SKIP:UNCHANGED_OK', 'a lookalike ALERT from another author is ignored');
ok(reasonOf(D(['PENDING_AGE'], [row(1, 60, body(['PENDING_AGE'], '20261114450000'), 'attacker')])) === 'POST:NO_PREVIOUS', 'a lookalike from another author does not silence the real monitor');
ok(reasonOf(D(['PENDING_AGE'], [row(1, 60, null, '')])) === 'POST:NO_PREVIOUS', 'a comment from a deleted account (empty login) is just another author')
ok(reasonOf(D(['PENDING_AGE'], [row(1, 60, body(['PENDING_AGE'], '20261114450000'), 'github-actions')])) === 'POST:NO_PREVIOUS', 'the login must match exactly, including the [bot] suffix');
ok(reasonOf(D(['PENDING_AGE'], [row(1, 60, body(['PENDING_AGE'], '20261114450000'), 'other-bot[bot]')], { config: { expectedLogin: 'other-bot[bot]' } })) === 'SKIP:UNCHANGED_ALERT', 'the expected login is configurable');
// unusable previous state posts, it never silences
ok(reasonOf(D(['PENDING_AGE'], [row(1, 60, MALFORMED, BOT)])) === 'POST:PREVIOUS_UNUSABLE', 'a newest monitor comment that no longer validates is not trusted');
ok(reasonOf(D(['PENDING_AGE'], [row(1, 60, null, BOT)])) === 'POST:NO_PREVIOUS', 'a bot comment with no body makes no claim to be the monitor and is not part of its stream');
ok(reasonOf(D(['PENDING_AGE'], [AL_ROW(1, 900, '20261114450000'), row(2, 60, MALFORMED, BOT)])) === 'POST:PREVIOUS_UNUSABLE', 'an older valid comment does not stand in for a newer broken one');
ok(reasonOf(D([], [row(1, -3600, body([], '20261114450000'))])) === 'POST:PREVIOUS_UNUSABLE', 'a comment dated an hour in the future is not trusted');
ok(reasonOf(D([], [row(1, -30, body([], '20261114450000'))])) === 'SKIP:UNCHANGED_OK', 'a comment within the clock skew tolerance is trusted');
ok(reasonOf(D([], [row(1, -61, body([], '20261114450000'))])) === 'POST:PREVIOUS_UNUSABLE', 'a comment just beyond the 60 s skew tolerance is not');
// id collisions and the hourly cap
ok(reasonOf(decide({ candidate: body([], '20261114450000'), listing: listing([OK_ROW(5, 21400, '20261114450000')]), nowMs: NOW })) === 'SKIP:DUPLICATE_ID', 'an id already on the board is never posted again, even when a receipt is due');
ok(reasonOf(decide({ candidate: body([], '20261114450000'), listing: listing([OK_ROW(5, 21400, '20261114450000', 'attacker')].map((r) => ({ ...r, login: 'attacker' }))), nowMs: NOW })) === 'POST:NO_PREVIOUS', 'an id used by another author does not block the monitor');
{ const many = (n, ageS) => Array.from({ length: n }, (_, i) => AL_ROW(100 + i, ageS - i, `2026111400${String(i).padStart(2, '0')}`, i % 2 ? ['PENDING_AGE'] : ['RPC_STALE']));
  ok(reasonOf(D([], many(8, 3000))) === 'SKIP:RATE_CAP', 'eight monitor posts in the last hour cap further posting, even for a change');
  ok(reasonOf(D([], many(7, 3000))) === 'POST:CHANGED', 'seven in the last hour do not');
  ok(reasonOf(D([], many(8, 7000))) === 'POST:CHANGED', 'posts older than an hour are not counted');
  ok(reasonOf(D([], many(3, 3000), { config: { maxPerHour: 3 } })) === 'SKIP:RATE_CAP', 'the cap is configurable'); }
// the listing
ok(reasonOf(decide({ candidate: body([]), listing: null, nowMs: NOW })) === 'HALT:LIST_UNAVAILABLE', 'no listing halts, it does not post blind');
for (const bad of [{ comments: [], count: -1 }, { comments: 'x', count: 0 }, { comments: [], count: 1.5 }, { comments: [], count: '0' }, { comments: [null], count: 1 }, { comments: [{ id: 1 }], count: 1 }, { comments: [row(1, 10, 'x'), row(1, 20, 'y')], count: 2 }, { comments: [{ ...row(1, 10, 'x'), created_at: 'yesterday' }], count: 1 }, { comments: [{ ...row(1, 10, 'x'), created_at: '2026-13-45T25:61:61Z' }], count: 1 }, { comments: [{ ...row(1, 10, 'x'), created_at: '2026-11-14T11:00:00.000Z' }], count: 1 }, { comments: [{ ...row(1, 10, 'x'), body: 5 }], count: 1 }, { comments: [{ ...row(1, 10, 'x'), login: null }], count: 1 }, { comments: [{ ...row(-1, 10, 'x') }], count: 1 }, { comments: [{ ...row(1.5, 10, 'x') }], count: 1 }])
  ok(reasonOf(decide({ candidate: body([]), listing: bad, nowMs: NOW })) === 'HALT:LIST_UNAVAILABLE', `a malformed listing halts: ${JSON.stringify(bad).slice(0, 60)}`);
ok(reasonOf(D([], [OK_ROW(1, 900, '20261114450000')], { count: 2 })) === 'HALT:LIST_INCOMPLETE', 'a list shorter than the issue comment count is incomplete and halts');
ok(reasonOf(D([], [OK_ROW(1, 900, '20261114450000'), OK_ROW(2, 800, '20261114450100')], { count: 1 })) === 'SKIP:UNCHANGED_OK', 'a list longer than the count (a comment arrived in between) is fine');
{ const filler = (n) => Array.from({ length: n }, (_, i) => row(1000 + i, 100000 + i, null, 'someone'));
  ok(reasonOf(D([], filler(2399))) === 'POST:NO_PREVIOUS', 'one below the capacity limit still works');
  ok(reasonOf(D([], filler(2400))) === 'HALT:HALT_CAPACITY', 'at the capacity limit the job halts instead of filling the board');
  ok(reasonOf(D([], [], { count: 0, config: { capacityLimit: 100 } })) === 'POST:NO_PREVIOUS' && reasonOf(D([], filler(100), { config: { capacityLimit: 100 } })) === 'HALT:HALT_CAPACITY', 'the capacity limit is configurable'); }
// candidate, clock and config problems
ok(reasonOf(decide({ candidate: 'junk', listing: listing([]), nowMs: NOW })) === 'HALT:CANDIDATE_INVALID' && reasonOf(decide({ candidate: undefined, listing: listing([]), nowMs: NOW })) === 'HALT:CANDIDATE_INVALID', 'an invalid candidate halts');
ok(reasonOf(decide({ candidate: body([]), listing: listing([]), nowMs: NOW, config: { nope: 1 } })) === 'HALT:CONFIG_INVALID', 'a bad config halts');
for (const bad of [NaN, 0, -1, 1.5, 'x', undefined, Infinity]) ok(reasonOf(decide({ candidate: body([]), listing: listing([]), nowMs: bad })) === 'HALT:INTERNAL', `a bad clock halts: ${String(bad)}`);
for (const bad of [undefined, null, 5, 'x']) ok(decide(bad).halt === true, `decide never throws on ${String(bad)}`);
{ const hostile = { get comments() { throw new Error('boom'); }, count: 1 }; ok(reasonOf(decide({ candidate: body([]), listing: hostile, nowMs: NOW })) === 'HALT:INTERNAL', 'a throwing input becomes INTERNAL, not an exception'); }
// every reason the module can return is in a closed list
{ const all = new Set(); const t = (r) => all.add(r.reason);
  t(D([], [])); t(D([], [OK_ROW(5, 900, '20261114450000')])); t(D(['PENDING_AGE'], [AL_ROW(5, 900, '20261114450000')])); t(D([], [AL_ROW(5, 900, '20261114450000')]));
  t(D(['PENDING_AGE'], [AL_ROW(5, 3300, '20261114450000')])); t(D([], [OK_ROW(5, 21300, '20261114450000')])); t(D([], [row(1, 5, 'x')]));
  ok([...all].every((r) => [...POST_REASONS, ...SKIP_REASONS, ...HALT_REASONS].includes(r)), 'every returned reason is in the closed lists');
  ok(new Set([...POST_REASONS, ...SKIP_REASONS, ...HALT_REASONS]).size === POST_REASONS.length + SKIP_REASONS.length + HALT_REASONS.length && [...POST_REASONS, ...SKIP_REASONS, ...HALT_REASONS].every((r) => /^[A-Z_]+$/.test(r)), 'the closed lists are disjoint and output-safe'); }
// a long run: with the schedule every 15 minutes, a steady OK posts only its periodic receipt and a steady ALERT only its repeat
{ let posts = []; let rows = []; let id = 1; const start = NOW;
  for (let k = 0; k < 96 * 2; k++) { // two days of runs at :07,:22,:37,:52
    const t = start + k * 900000 + 7 * 60000;
    const minute = new Date(t).toISOString().replace(/[-:T]/g, '').slice(0, 14);
    const cand = body([], minute, t); const r = decide({ candidate: cand, listing: { count: rows.length, comments: rows }, nowMs: t });
    if (r.post) { posts.push(r.reason); rows = [...rows, { id: id++, created_at: iso(t), login: BOT, body: cand }]; } }
  ok(posts.length <= 10 && posts[0] === 'NO_PREVIOUS' && posts.slice(1).every((x) => x === 'RECEIPT_OK'), `a steady OK for two days posts ${posts.length} receipts, not 192`);
  posts = []; rows = []; id = 1;
  for (let k = 0; k < 96 * 2; k++) {
    const t = start + k * 900000 + 7 * 60000; const minute = new Date(t).toISOString().replace(/[-:T]/g, '').slice(0, 14);
    const cand = body(['PENDING_AGE'], minute, t); const r = decide({ candidate: cand, listing: { count: rows.length, comments: rows }, nowMs: t });
    if (r.post) { posts.push(r.reason); rows = [...rows, { id: id++, created_at: iso(t), login: BOT, body: cand }]; } }
  ok(posts.length >= 47 && posts.length <= 49 && posts.slice(1).every((x) => x === 'REPEAT_ALERT'), `a steady ALERT for two days posts ${posts.length} repeats, about one an hour`); }

// ---- review round 1 (OpenAI, comment 6877440773) ----
// 1. ids have second resolution; a retry of the same send is dropped, a changed state under a used id is never silently discarded
{ const id = (sec) => `202611141200${sec}`; const cand = (codes, sec) => body(codes, id(sec), NOW);
  ok(reasonOf(decide({ candidate: cand(['PENDING_AGE'], '30'), listing: listing([row(5, 20, body([], id('10'), NOW - 20000))]), nowMs: NOW })) === 'POST:CHANGED', 'OK to ALERT inside the same minute posts: the ids differ at second resolution');
  ok(reasonOf(decide({ candidate: cand(['RPC_STALE'], '30'), listing: listing([row(5, 20, body(['PENDING_AGE'], id('10'), NOW - 20000))]), nowMs: NOW })) === 'POST:CHANGED', 'one ALERT to a different ALERT inside the same minute posts');
  ok(reasonOf(decide({ candidate: cand([], '30'), listing: listing([row(5, 20, body([], id('30'), NOW))]), nowMs: NOW })) === 'SKIP:DUPLICATE_ID', 'a retry of the same send (same id, same state) is dropped');
  ok(reasonOf(decide({ candidate: cand(['PENDING_AGE'], '30'), listing: listing([row(5, 20, body([], id('30'), NOW))]), nowMs: NOW })) === 'HALT:ID_COLLISION', 'the same id with a different state fails the job visibly instead of discarding the change');
  ok(reasonOf(decide({ candidate: cand(['PENDING_AGE', 'RPC_STALE'], '30'), listing: listing([row(5, 20, body(['PENDING_AGE'], id('30'), NOW))]), nowMs: NOW })) === 'HALT:ID_COLLISION', 'a changed code set under a used id is also a collision');
  ok(reasonOf(decide({ candidate: cand([], '30'), listing: listing([row(5, 20, body([], id('30'), NOW), 'attacker')]), nowMs: NOW })) === 'POST:NO_PREVIOUS', 'an id used by another author is not a collision'); }
{ const alertNoCodes = boardComment(boardMessage({ outcome: { status: 'ALERT', outbound: { alerts: [] }, health: mkOutcome([]).health }, nowMs: NOW, idSuffix: '20261114120030' }));
  ok(reasonOf(decide({ candidate: alertNoCodes, listing: listing([row(5, 20, body([], '20261114120030', NOW))]), nowMs: NOW })) === 'HALT:ID_COLLISION' && reasonOf(decide({ candidate: body([], '20261114120030', NOW), listing: listing([row(5, 20, alertNoCodes)]), nowMs: NOW })) === 'HALT:ID_COLLISION', 'a status difference with equal code lists under a used id is a collision too'); }
// 2. other workflows share the Actions bot login: only the monitor's own stream counts
{ const ci = (n, ageS) => Array.from({ length: n }, (_, i) => row(2000 + i, ageS + i, `CI summary ${i}: all checks passed`, BOT));
  ok(reasonOf(D(['PENDING_AGE'], ci(8, 60))) === 'POST:NO_PREVIOUS', 'eight unrelated bot comments in the last hour do not trigger the monitor rate cap');
  ok(reasonOf(D([], [OK_ROW(1, 900, '20261114114500'), ...ci(10, 10)])) === 'SKIP:UNCHANGED_OK', 'unrelated bot comments newer than the monitor record do not replace its state');
  ok(reasonOf(D(['PENDING_AGE'], [...ci(10, 5000), OK_ROW(1, 900, '20261114114500'), ...ci(10, 10).map((r) => ({ ...r, id: r.id + 100 }))])) === 'POST:CHANGED', 'unrelated bot comments before and after a real record leave the comparison intact');
  const bad = (n, ageS) => Array.from({ length: n }, (_, i) => row(3000 + i, ageS + i, `${MALFORMED} ${i}`, BOT));
  ok(reasonOf(D(['PENDING_AGE'], bad(8, 60))) === 'SKIP:RATE_CAP', 'malformed comments that claim the monitor id still count toward its cap');
  ok(reasonOf(D(['PENDING_AGE'], [OK_ROW(1, 900, '20261114114500'), ...bad(1, 10)])) === 'POST:PREVIOUS_UNUSABLE', 'a malformed monitor claim newer than the last valid record makes the state unusable, so the run posts');
  ok(reasonOf(D([], [OK_ROW(1, 900, '20261114114500'), ...ci(1, 10)].map((r) => ({ ...r, login: r.id === 1 ? 'attacker' : r.login })))) === 'POST:NO_PREVIOUS', 'the login must still match for the monitor stream'); }
// 3. a stale or future snapshot is never posted as a current receipt
{ const at = (ageS) => decide({ candidate: body([], '20261114115500', NOW - ageS * 1000), listing: listing([]), nowMs: NOW });
  ok(reasonOf(at(0)) === 'POST:NO_PREVIOUS' && reasonOf(at(600)) === 'POST:NO_PREVIOUS', 'a snapshot up to the freshness budget (600 s) old is accepted');
  ok(reasonOf(at(601)) === 'HALT:STALE_CANDIDATE' && reasonOf(at(86400)) === 'HALT:STALE_CANDIDATE', 'a snapshot older than the budget fails the job visibly, even with an empty board');
  ok(reasonOf(at(-30)) === 'POST:NO_PREVIOUS' && reasonOf(at(-61)) === 'HALT:STALE_CANDIDATE', 'a snapshot dated beyond the clock-skew tolerance in the future is refused');
  ok(reasonOf(decide({ candidate: boardComment(boardMessage({ outcome: mkOutcome([]), nowMs: NaN, idSuffix: '20261114115500' })), listing: listing([]), nowMs: NOW })) === 'HALT:STALE_CANDIDATE', 'a candidate with no observation time is refused');
  ok(reasonOf(decide({ candidate: body([], '20261114115500', NOW - 3000000), listing: listing([]), nowMs: NOW, config: { maxCandidateAgeS: 3600 } })) === 'POST:NO_PREVIOUS', 'the freshness budget is configurable');
  const p = parseMonitorComment(body([], '20261114115500', NOW - 5000)); ok(p.atMs === NOW - 5000, 'the parser returns the observation time, which is not the comment creation time'); }

// 4. review by Hermes (PR 476 comment 6877454092): a previous state that keeps reading back unusable must not post on every tick
{ const crlf = (b) => b.replace(/\n/g, '\r\n'); const bad = (id, ageS, m) => row(id, ageS, crlf(body([], m)));
  ok(reasonOf(D([], [bad(1, 900, '20261114114500')])) === 'POST:PREVIOUS_UNUSABLE', 'one unusable previous comment still posts a fresh baseline');
  ok(reasonOf(D([], [bad(1, 1800, '20261114113000'), bad(2, 900, '20261114114500')])) === 'POST:PREVIOUS_UNUSABLE', 'two unusable comments in a day still post (the limit is three)');
  ok(reasonOf(D([], [bad(1, 3000, '20261114111000'), bad(2, 1800, '20261114113000'), bad(3, 900, '20261114114500')])) === 'HALT:PREVIOUS_STUCK', 'three unusable monitor comments within a day halt instead of posting again');
  ok(reasonOf(D([], [bad(1, 90000, '20261113110000'), bad(2, 80000, '20261113113000'), bad(3, 900, '20261114114500')])) === 'POST:PREVIOUS_UNUSABLE', 'unusable comments older than a day are not counted');
  ok(reasonOf(D([], [bad(1, 3000, '20261114111000'), bad(2, 1800, '20261114113000'), bad(3, 900, '20261114114500')], { config: { unusableMaxPerDay: 4 } })) === 'POST:PREVIOUS_UNUSABLE', 'the limit is configurable');
  ok(reasonOf(D([], [OK_ROW(1, 1800, '20261114113000'), OK_ROW(2, 900, '20261114114500')])) === 'SKIP:UNCHANGED_OK', 'usable posts never count toward the stuck limit');
  ok(reasonOf(D(['PENDING_AGE'], [OK_ROW(1, 900, '20261114113000'), row(2, 60, MALFORMED, BOT)])) === 'POST:PREVIOUS_UNUSABLE', 'one hand-edited comment after a valid record posts a fresh baseline, it is not stuck');
  ok(reasonOf(D([], [OK_ROW(1, 7000, '20261114100000'), OK_ROW(2, 5000, '20261114103000'), bad(3, 900, '20261114114500')])) === 'POST:PREVIOUS_UNUSABLE', 'valid posts in the day are not counted as unusable: two valid plus one bad is one unusable, not three');
  const others = Array.from({ length: 5 }, (_, i) => row(500 + i, 600 + i, `CI note ${i}`, 'someone-else'));
  ok(reasonOf(D([], [...others, bad(3, 900, '20261114114500')])) === 'POST:PREVIOUS_UNUSABLE', 'comments by other authors are never counted toward the stuck limit'); }
// a simulated read-back that always returns an unusable body: the monitor posts three times, then halts every tick, never 96 a day
{ let rows = [], id = 1, posts = 0, halts = 0; for (let k = 0; k < 96; k++) { const t = NOW + k * 900000;
    const cand = body([], new Date(t).toISOString().replace(/[-:T]/g, '').slice(0, 14), t); const r = decide({ candidate: cand, listing: { count: rows.length, comments: rows }, nowMs: t });
    if (r.post) { posts++; rows = [...rows, { id: id++, created_at: iso(t), login: BOT, body: cand.replace(/\n/g, '\r\n') }]; } else if (r.halt) halts++; }
  ok(posts <= 4 && halts >= 85, `a read-back that never parses posts ${posts} times in a day and halts ${halts} ticks, not 96 posts`); }

// ---- the decide-post CLI ----
{ const files = {}; const io = (over = {}) => ({ readFile: (p) => { if (!(p in files)) throw new Error('nofile'); return files[p]; }, write: (s) => { io.out = s; }, now: () => NOW, ...over });
  const run = (extra = []) => { io.out = ''; const code = decideMain(['node', 'x', 'cand.md', 'comments.json', 'count.txt', ...extra], io()); return { code, out: io.out }; };
  files['cand.md'] = body([]); files['comments.json'] = JSON.stringify([]); files['count.txt'] = '0\n';
  let r = run(); ok(r.code === 0 && r.out === 'post=true\nreason=NO_PREVIOUS\n', 'CLI: first run posts and prints exactly two lines');
  files['comments.json'] = JSON.stringify([OK_ROW(5, 900, '20261114450000')]); files['count.txt'] = '1';
  r = run(); ok(r.code === 0 && r.out === 'post=false\nreason=UNCHANGED_OK\n', 'CLI: a quiet skip exits 0 with post=false');
  files['count.txt'] = '2'; r = run(); ok(r.code === 3 && r.out === 'post=false\nreason=LIST_INCOMPLETE\n', 'CLI: an incomplete list exits 3 and never prints post=true');
  files['count.txt'] = 'abc'; r = run(); ok(r.code === 3 && r.out === 'post=false\nreason=LIST_UNAVAILABLE\n', 'CLI: a count that is not a number halts');
  files['count.txt'] = '1'; files['comments.json'] = '{not json'; r = run(); ok(r.code === 3 && r.out === 'post=false\nreason=LIST_UNAVAILABLE\n', 'CLI: unparseable comments halt');
  files['comments.json'] = JSON.stringify({ not: 'an array' }); r = run(); ok(r.code === 3 && r.out.startsWith('post=false'), 'CLI: comments that are not an array halt');
  delete files['comments.json']; r = run(); ok(r.code === 3 && r.out === 'post=false\nreason=LIST_UNAVAILABLE\n', 'CLI: a missing comments file halts');
  files['comments.json'] = JSON.stringify([]); files['count.txt'] = '0'; delete files['cand.md']; r = run(); ok(r.code === 3 && r.out === 'post=false\nreason=CANDIDATE_INVALID\n', 'CLI: a missing candidate halts');
  files['cand.md'] = body([]); files['cfg.json'] = JSON.stringify({ okReceiptS: 3600 }); r = run(['cfg.json']); ok(r.code === 0 && r.out.startsWith('post=true'), 'CLI: an optional config file is read');
  files['cfg.json'] = '{bad'; r = run(['cfg.json']); ok(r.code === 3 && r.out === 'post=false\nreason=CONFIG_INVALID\n', 'CLI: an unreadable config halts, it does not fall back to defaults');
  files['cfg.json'] = JSON.stringify({ unknown: 1 }); r = run(['cfg.json']); ok(r.code === 3 && r.out === 'post=false\nreason=CONFIG_INVALID\n', 'CLI: an unknown config key halts');
  files['cand.md'] = body([]); files['comments.json'] = '[]'; files['cfg.json'] = '{}';
  for (const bad of ['', '  ', '0x10', '1e2', '-1', '1.5', '12345678', 'NaN']) { files['count.txt'] = bad; r = run(); ok(r.code === 3 && r.out === 'post=false\nreason=LIST_UNAVAILABLE\n', `CLI: a count file that says ${JSON.stringify(bad)} halts (Number() would have turned some of these into numbers)`); }
  files['count.txt'] = '0';
  // the wrapper does not trust the decision either: it prints only closed-list tokens and a consistent pair
  const hostile = (d) => { io.out = ''; const code = decideMain(['node', 'x', 'cand.md', 'comments.json', 'count.txt'], io({ decide: () => d })); return { code, out: io.out }; };
  r = hostile({ post: true, halt: false, reason: 'CHANGED' }); ok(r.code === 0 && r.out === 'post=true\nreason=CHANGED\n', 'CLI: a consistent post decision is printed');
  r = hostile({ post: true, halt: true, reason: 'CHANGED' }); ok(r.code === 3 && r.out.startsWith('post=false\n'), 'CLI: a halt never prints post=true');
  r = hostile({ post: true, halt: false, reason: 'evil\npost=true' }); ok(r.code === 3 && r.out === 'post=false\nreason=INTERNAL\n', 'CLI: a reason outside the closed lists is replaced and fails the step');
  r = hostile({ post: false, halt: false, reason: 'CHANGED' }); ok(r.code === 3 && r.out === 'post=false\nreason=INTERNAL\n', 'CLI: a post reason on a non-post decision is inconsistent and fails the step');
  r = hostile({ post: true, halt: false, reason: 'UNCHANGED_OK' }); ok(r.code === 3 && r.out === 'post=false\nreason=INTERNAL\n', 'CLI: a skip reason on a post decision is inconsistent and fails the step');
  r = hostile(null); ok(r.code === 3 && r.out === 'post=false\nreason=INTERNAL\n', 'CLI: a missing decision fails the step');
  r = (() => { io.out = ''; const code = decideMain(['node', 'x', 'cand.md', 'comments.json', 'count.txt'], io({ decide: () => { throw new Error('boom'); } })); return { code, out: io.out }; })(); ok(r.code === 3 && r.out === 'post=false\nreason=INTERNAL\n', 'CLI: a throwing decision fails the step');
  // hostile board content can never reach the output file: only closed-list tokens are printed
  files['cfg.json'] = JSON.stringify({}); files['comments.json'] = JSON.stringify([{ id: 1, created_at: ago(10), login: 'x\npost=true', body: 'y\nreason=Z' }]); files['count.txt'] = '1';
  r = run(['cfg.json']); ok(/^post=(true|false)\nreason=[A-Z_]+\n$/.test(r.out), 'CLI: the output is always two closed-form lines whatever the board contains'); }

// ---- the draft workflow uses the decision, in order, and stays inactive ----
{ const wf = readFileSync(join(here, 'draft-workflow', 'officer-chain-monitor.yml'), 'utf8');
  const send = /^  send:\n((?:    .*\n|\n)+)/m.exec(wf)[1];
  const idx = (s) => send.indexOf(s);
  ok(idx('validate-comment.mjs') > -1 && idx('validate-comment.mjs') < idx('decide-post.mjs') && idx('decide-post.mjs') < idx('/issues/462/comments" --input'), 'send job order: validate, then decide, then post');
  ok(/id: decide/.test(send) && /steps\.decide\.outputs\.post == 'true'/.test(send) && /decide-post\.mjs status-comment\.md comments\.json count\.txt > decision\.txt/.test(send) && /cat decision\.txt >> "\$GITHUB_STEP_SUMMARY"/.test(send) && /if \[ "\$code" -eq 0 \]; then cat decision\.txt >> "\$GITHUB_OUTPUT"; fi/.test(send) && /exit "\$code"/.test(send), 'the post step runs only when the decision says post, and the decision is written to the step output');
  ok(/\(\.user\.login \/\/ ""\)/.test(send), 'a deleted account (no user object) becomes an empty login instead of failing the read')
  ok(/--paginate/.test(send) && /github-actions\[bot\]/.test(send) && idx('count.txt') < idx('comments.json'), 'the whole comment list is read after the count, and bodies are kept only for the monitor login');
  { const step = /id: decide\n        run: \|\n((?:          .*\n)+)/.exec(send); ok(step && /set \+e/.test(step[1]) && step[1].indexOf('set +e') < step[1].indexOf('decide-post.mjs') && step[1].indexOf('GITHUB_STEP_SUMMARY') > step[1].indexOf('decide-post.mjs'), 'the decide step turns errexit off before the decision, so a halt still writes its summary before the step fails'); }
  ok(!/\|\| true/.test(wf) && !/2>\/dev\/null/.test(send), 'no failure is swallowed in the send job');
  ok(/bash -e/.test(wf) && /pipefail/.test(wf), 'the draft says it relies on the default bash -e and why no pipe carries a result that matters');
  ok(!/\|\s*(gh|jq)[^\n]*>\s*comments\.json/.test(send), 'the list is written by one command and slurped by another, not through a pipe whose failure bash -e would not see');
  ok((wf.match(/^    if: \$\{\{ false \}\}$/gm) || []).length === 2 && !wf.includes('.github/workflows/officer'), 'both jobs are still disabled'); }

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
