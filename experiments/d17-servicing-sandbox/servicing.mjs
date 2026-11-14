// D17 W3 sandbox: a scripted Spanish servicing assistant for a lender's small short-term loans.
// Text only. No model call, no network, no live ledger, no signer, no real person. Every number in an outgoing
// message comes from the fixture ledger through a template; the assistant never repeats a number the sender typed.
// The risk rules of docs: coordination/directions/whatsapp-local-currency-channel.md (W3).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
export const loadFixtures = () => JSON.parse(readFileSync(join(here, 'fixtures.json'), 'utf8'));

// ---------- ledger arithmetic (integers only: quetzal cents) ----------
const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const addDays = (iso, n) => { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
export const dateEs = (iso) => { const [y, m, d] = iso.split('-').map(Number); return `${d} de ${MONTHS[m - 1]} de ${y}`; };
export const qEs = (cents) => { const whole = Math.floor(cents / 100), c = String(cents % 100).padStart(2, '0'); return `Q${String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${c}`; };
export const total = (b) => b.loan.principal_cents + b.loan.fee_cents;
export const balance = (b) => total(b) - b.loan.paid_cents;
export function schedule(b) { // equal instalments; the last one takes the rounding remainder
  const n = b.loan.installments, t = total(b), base = Math.floor(t / n), out = [];
  for (let i = 1; i <= n; i++) out.push({ n: i, due: addDays(b.loan.first_due, (i - 1) * b.loan.interval_days), cents: i === n ? t - base * (n - 1) : base });
  return out;
}
export const nextInstallment = (b) => schedule(b)[b.loan.paid_installments] || null;
export const daysBetween = (aIso, bIso) => Math.round((Date.parse(bIso + 'T00:00:00Z') - Date.parse(aIso + 'T00:00:00Z')) / 86400000);

// ---------- outgoing templates: { text, numbers } with the ledger values used ----------
const HELP = (fx) => `Si necesita ayuda, escriba "ayuda" o hable con ${fx.human_contact} ${fx.human_hours}.`;
export const FORBIDDEN_WORDS = ['deuda', 'cobro', 'cobranza', 'embargo', 'demanda', 'policía', 'policia', 'multa', 'vergüenza', 'verguenza', 'moroso', 'castigo', 'amenaza'];
const sty = (style, warm, plain) => (style === 'plain' ? plain : warm);

export const t = {
  disbursal(fx, b, style = 'warm') {
    const s = schedule(b);
    return { text: sty(style,
      `Hola ${b.first_name}, su préstamo de ${qEs(b.loan.principal_cents)} quedó registrado. El costo del servicio es ${qEs(b.loan.fee_cents)}. En total son ${qEs(total(b))}, en ${b.loan.installments} cuotas. La primera cuota es de ${qEs(s[0].cents)} y vence el ${dateEs(s[0].due)}. ${HELP(fx)}`,
      `Préstamo registrado: ${qEs(b.loan.principal_cents)}. Costo: ${qEs(b.loan.fee_cents)}. Total: ${qEs(total(b))} en ${b.loan.installments} cuotas. Primera cuota: ${qEs(s[0].cents)}, ${dateEs(s[0].due)}.`) };
  },
  reminder(fx, b, style = 'warm') {
    const i = nextInstallment(b);
    return { text: sty(style,
      `Hola ${b.first_name}, le recordamos que su cuota ${i.n} de ${b.loan.installments}, de ${qEs(i.cents)}, vence el ${dateEs(i.due)}. ${HELP(fx)}`,
      `Cuota ${i.n} de ${b.loan.installments}: ${qEs(i.cents)}, vence ${dateEs(i.due)}.`) };
  },
  dueToday(fx, b, style = 'warm') {
    const i = nextInstallment(b);
    return { text: sty(style,
      `Hola ${b.first_name}, hoy vence su cuota ${i.n} de ${b.loan.installments}, de ${qEs(i.cents)}. Gracias por su puntualidad. ${HELP(fx)}`,
      `Hoy vence la cuota ${i.n} de ${b.loan.installments}: ${qEs(i.cents)}.`) };
  },
  received(fx, b, paidCents, style = 'warm') {
    const left = balance(b);
    return { text: sty(style,
      left > 0
        ? `Gracias, ${b.first_name}. Registramos su pago de ${qEs(paidCents)}. Le quedan ${qEs(left)} por pagar.`
        : `Gracias, ${b.first_name}. Registramos su pago de ${qEs(paidCents)}. Su préstamo está pagado por completo.`,
      left > 0 ? `Pago registrado: ${qEs(paidCents)}. Saldo: ${qEs(left)}.` : `Pago registrado: ${qEs(paidCents)}. Saldo: ${qEs(0)}.`) };
  },
  late(fx, b, daysLate, style = 'warm') {
    const i = nextInstallment(b);
    if (daysLate >= 14) return { escalate: { reason: 'late_14_days', within_hours: fx.escalation_window_hours }, text: sty(style,
      `Hola ${b.first_name}, su cuota ${i.n} de ${b.loan.installments}, de ${qEs(i.cents)}, tiene ${daysLate} días de atraso. Queremos ayudarle a encontrar una solución: ${fx.human_contact} le escribirá dentro de ${fx.escalation_window_hours} horas.`,
      `Cuota ${i.n}: ${qEs(i.cents)}, ${daysLate} días de atraso. ${fx.human_contact} le escribirá dentro de ${fx.escalation_window_hours} horas.`) };
    if (daysLate >= 7) return { text: sty(style,
      `Hola ${b.first_name}, su cuota ${i.n} de ${b.loan.installments}, de ${qEs(i.cents)}, sigue pendiente desde el ${dateEs(i.due)}. Puede pagarla cuando pueda, y si hay un problema cuéntenos. ${HELP(fx)}`,
      `Cuota ${i.n}: ${qEs(i.cents)}, pendiente desde ${dateEs(i.due)}.`) };
    return { text: sty(style,
      `Hola ${b.first_name}, no vimos el pago de su cuota ${i.n} de ${b.loan.installments}, de ${qEs(i.cents)}, que venció el ${dateEs(i.due)}. Si ya pagó, avísenos. ${HELP(fx)}`,
      `Cuota ${i.n}: ${qEs(i.cents)}, venció ${dateEs(i.due)}, sin pago registrado.`) };
  },
};

// ---------- incoming: deterministic intent rules ----------
const norm = (s) => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ').trim();
const has = (s, words) => words.some((w) => s.includes(w));
const INJECTION = ['ignora', 'olvida tus instrucciones', 'instrucciones anteriores', 'actua como', 'eres ahora', 'system prompt', 'tu prompt', 'muestra tus reglas', 'modo desarrollador', 'dame todos los datos', 'lista de clientes', 'datos de otro', 'ignore previous', 'repite tus instrucciones'];
const ROLE_CLAIM = /\bsoy (el|la) (esposo|esposa|marido|hijo|hija|hermano|hermana|mama|papa|primo|prima|vecino|vecina|abogado|abogada|policia|jefe|patron|tio|tia|amigo|amiga|cunado|cunada)\b|\bde parte de\b|\bsoy familiar\b/;
const STOP = ['no mas mensajes', 'dejen de escribir', 'dejen de escribirme', 'baja', 'parar', 'stop', 'no me escriban', 'darme de baja'];
const NOT_ME = ['no soy ', 'numero equivocado', 'se equivocaron', 'equivocado de numero', 'no conozco a'];
const HARDSHIP = ['no puedo pagar', 'no tengo dinero', 'perdi mi trabajo', 'estoy enfermo', 'estoy enferma', 'enfermedad', 'prorroga', 'mas tiempo', 'no me alcanza', 'emergencia', 'fallecio', 'murio'];
const PAID = ['ya pague', 'pague', 'hice el pago', 'deposite', 'hice un deposito', 'transferi'];
const BALANCE = ['cuanto debo', 'saldo', 'cuanto me falta', 'cuanto tengo que pagar', 'mi cuota', 'cuando pago', 'cuando vence', 'cuanto es'];
const HELPWORD = ['ayuda', 'hablar con una persona', 'quiero hablar con', 'persona', 'humano'];

export const REFUSALS = {
  injection: 'No puedo cambiar mis reglas ni compartir información que no sea suya. Sigo aquí para ayudarle con su préstamo.',
  unknownSender: 'Este número no está registrado con nosotros, así que no puedo compartir información de préstamos. Si es cliente, escriba desde el número que registró o hable con la facilitadora.',
  roleClaim: 'Por su seguridad, solo puedo hablar de un préstamo con la persona a nombre de quien está. Pídale que nos escriba directamente.',
  shared: 'Este número lo usan varias personas con nosotros. Para continuar, dígame su nombre y su palabra de verificación.',
  verifyFailed: 'No pude verificar esos datos, así que no puedo compartir información. Puede hablar con la facilitadora para ayudarle.',
  optOut: 'Entendido, no le escribiremos más mensajes de servicio. Si cambia de opinión, puede escribirnos cuando quiera.',
  notMe: 'Disculpe la molestia, parece que hubo un error. Avisaremos para corregir el registro y no volveremos a escribirle a este número sobre este préstamo.',
  unknown: 'No estoy segura de haber entendido. ¿Quiere saber su saldo, su próxima cuota, o hablar con una persona?',
};

export function newConversation(from) { return { from, borrowerId: null, verified: false, verifyTries: 0, unknownCount: 0, optedOut: false, flagged: [] }; }

function byPhone(fx, phone) { return fx.borrowers.filter((b) => b.phone === phone); }

// One incoming message. Returns { reply, intent, escalate, disclosed, numbers } where `numbers` lists the ledger values used.
export function respond(fx, conv, text, today = '2026-12-01', style = 'warm') {
  const m = norm(text);
  const out = (reply, intent, extra = {}) => ({ reply, intent, escalate: null, disclosed: false, ...extra });
  const matches = byPhone(fx, conv.from);

  if (has(m, INJECTION)) return out(REFUSALS.injection, 'injection');                               // before anything else
  if (matches.length === 0) return out(REFUSALS.unknownSender, 'unknown_sender', { escalate: null });
  if (has(m, STOP)) { conv.optedOut = true; return out(REFUSALS.optOut, 'opt_out'); }
  if (has(m, NOT_ME) && !m.includes('no soy el') && !m.includes('no soy la')) {
    const named = matches.find((b) => m.includes('no soy ' + norm(b.first_name)));
    if (named || has(m, ['numero equivocado', 'se equivocaron', 'equivocado de numero', 'no conozco a'])) {
      conv.optedOut = true; return out(REFUSALS.notMe, 'not_me', { escalate: { reason: 'wrong_number', within_hours: fx.escalation_window_hours } });
    }
  }
  if (ROLE_CLAIM.test(m)) return out(REFUSALS.roleClaim, 'role_claim', { escalate: null });

  // who is speaking: a phone with one borrower identifies them; a shared phone needs a name and the verification word
  if (!conv.borrowerId) {
    if (matches.length === 1) { conv.borrowerId = matches[0].id; conv.verified = true; }
    else {
      const pick = matches.find((b) => m.includes(norm(b.first_name)));
      if (pick && m.includes(norm(pick.verification_word))) { conv.borrowerId = pick.id; conv.verified = true; conv.justVerified = true; }
      else {
        conv.verifyTries++;
        if (conv.verifyTries >= 3) return out(REFUSALS.verifyFailed, 'verify_failed', { escalate: { reason: 'verification_failed', within_hours: fx.escalation_window_hours } });
        return out(REFUSALS.shared, pick ? 'verify_needed' : 'shared_phone');
      }
    }
  }
  const b = fx.borrowers.find((x) => x.id === conv.borrowerId);
  const justVerified = conv.justVerified; conv.justVerified = false;

  if (has(m, HARDSHIP)) return out(`Lamento mucho lo que está pasando, ${b.first_name}. No puedo cambiar las fechas ni los montos por mi cuenta, pero ${fx.human_contact} le escribirá dentro de ${fx.escalation_window_hours} horas para buscar una solución con usted.`, 'hardship', { disclosed: false, escalate: { reason: 'hardship', within_hours: fx.escalation_window_hours } });
  if (has(m, HELPWORD)) return out(`Con gusto. ${fx.human_contact} le escribirá dentro de ${fx.escalation_window_hours} horas.`, 'human_request', { escalate: { reason: 'human_requested', within_hours: fx.escalation_window_hours } });
  if (has(m, PAID)) return out(`Gracias, ${b.first_name}. Todavía no veo ese pago registrado, y no puedo confirmarlo yo. ${fx.human_contact} lo revisará y le escribirá dentro de ${fx.escalation_window_hours} horas.`, 'paid_claim', { escalate: { reason: 'payment_unverified', within_hours: fx.escalation_window_hours } });
  if (has(m, BALANCE) || /\bq?\s?\d/.test(m)) {                                                         // a number typed by the sender is never repeated or accepted
    const i = nextInstallment(b), left = balance(b);
    if (!i) return out(`${b.first_name}, su préstamo está pagado por completo. Gracias.`, 'balance', { disclosed: true, numbers: { balance_cents: 0 } });
    return out(sty(style,
      `${b.first_name}, según nuestro registro le quedan ${qEs(left)} por pagar. Su próximo pago es la cuota ${i.n} de ${b.loan.installments}, de ${qEs(i.cents)}, y vence el ${dateEs(i.due)}.`,
      `Saldo: ${qEs(left)}. Próxima cuota ${i.n} de ${b.loan.installments}: ${qEs(i.cents)}, ${dateEs(i.due)}.`), 'balance', { disclosed: true, numbers: { balance_cents: left, installment_cents: i.cents, due: i.due } });
  }
  if (justVerified) return out(`Gracias, ${b.first_name}, ya la identifiqué. ¿Quiere saber su saldo, su próxima cuota, o hablar con una persona?`, 'verified');
  conv.unknownCount++;
  if (conv.unknownCount >= 2) return out(`${b.first_name}, voy a pedirle a ${fx.human_contact} que le escriba dentro de ${fx.escalation_window_hours} horas.`, 'unknown_escalated', { escalate: { reason: 'not_understood_twice', within_hours: fx.escalation_window_hours } });
  return out(REFUSALS.unknown, 'unknown');
}

// ---------- numeric audit: every number in an outgoing message must be a ledger value for that borrower ----------
const AMOUNT = /Q\d{1,3}(?:,\d{3})*\.\d{2}/g;
const DATE = /\b\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) de \d{4}\b/g;
const OF_N = /\bcuota (\d+) de (\d+)\b/gi;
const IDX_ONLY = /\bcuota (\d+)(?=:)/gi;
const COUNT = /\ben (\d+) cuotas\b/g;
const DAYS = /\b(\d+) días de atraso\b/g;
const HOURS = /\bdentro de (\d+) horas\b/g;
export function numericTokens(text) {
  const toks = [];
  for (const x of text.match(AMOUNT) || []) toks.push({ kind: 'amount', raw: x });
  for (const x of text.match(DATE) || []) toks.push({ kind: 'date', raw: x });
  for (const x of text.matchAll(OF_N)) { toks.push({ kind: 'index', raw: x[1] }); toks.push({ kind: 'count', raw: x[2] }); }
  for (const x of text.matchAll(IDX_ONLY)) toks.push({ kind: 'index', raw: x[1] });
  for (const x of text.matchAll(COUNT)) toks.push({ kind: 'count', raw: x[1] });
  for (const x of text.matchAll(DAYS)) toks.push({ kind: 'days', raw: x[1] });
  for (const x of text.matchAll(HOURS)) toks.push({ kind: 'hours', raw: x[1] });
  return toks;
}
