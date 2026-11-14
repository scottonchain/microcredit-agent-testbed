// Numeric audit: every number in an outgoing message must be a value derived from the fixture ledger for the
// borrower the message is addressed to. Returns one verdict per numeric utterance (a message with at least one number).
import { numericTokens, schedule, total, balance, qEs, dateEs, FORBIDDEN_WORDS } from './servicing.mjs';

export function allowedFor(fx, b, extra = {}) {
  const s = schedule(b);
  const amounts = new Set([b.loan.principal_cents, b.loan.fee_cents, total(b), balance(b), b.loan.paid_cents, 0, ...s.map((x) => x.cents), ...(extra.amounts || [])].map(qEs));
  const dates = new Set(s.map((x) => dateEs(x.due)));
  const indexes = new Set(s.map((x) => String(x.n)));
  const counts = new Set([String(b.loan.installments)]);
  const days = new Set((extra.days || []).map(String));
  const hours = new Set([String(fx.escalation_window_hours)]);
  return { amount: amounts, date: dates, index: indexes, count: counts, days, hours };
}

export function auditMessage(fx, b, text, extra = {}) {
  const allowed = allowedFor(fx, b, extra);
  const toks = numericTokens(text);
  const errors = [];
  for (const k of toks) if (!allowed[k.kind].has(k.raw)) errors.push({ kind: k.kind, raw: k.raw, why: 'not a ledger value for this borrower' });
  // any digit left after removing recognised tokens and the fixed office-hours phrase is an unvetted number
  let rest = text.replace(fx.human_hours, '');
  for (const k of toks) rest = rest.replace(k.raw, '');
  rest = rest.replace(/cuota\s+(?:de\s+)?/gi, '').replace(/\b(de|en|dentro de)\b/g, '');
  const stray = rest.match(/\d+/g);
  if (stray) for (const x of stray) errors.push({ kind: 'stray', raw: x, why: 'number outside any ledger template' });
  const lower = text.toLowerCase();
  for (const w of FORBIDDEN_WORDS) if (lower.includes(w)) errors.push({ kind: 'tone', raw: w, why: 'forbidden collection-style word' });
  return { numeric: toks.length > 0, tokens: toks.length, errors };
}
