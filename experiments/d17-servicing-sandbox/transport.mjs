// Simulated transport: an in-memory text channel with a manual clock. No network, no WhatsApp, no real number.
// Messages are plain objects; nothing leaves the process.
export class SimTransport {
  constructor(startIso = '2026-12-01T09:00:00Z') { this.now = Date.parse(startIso); this.log = []; this.escalations = []; }
  iso() { return new Date(this.now).toISOString(); }
  today() { return this.iso().slice(0, 10); }
  advanceHours(h) { this.now += h * 3600000; }
  advanceDays(d) { this.advanceHours(24 * d); }
  record(dir, who, text, meta = {}) { this.log.push({ at: this.iso(), dir, who, text, ...meta }); }
  inbound(from, text) { this.record('in', from, text); }
  outbound(to, text, meta = {}) { this.record('out', to, text, meta); }
  escalate(borrowerId, reason, withinHours) {
    const e = { id: this.escalations.length + 1, borrowerId, reason, raisedAt: this.now, dueAt: this.now + withinHours * 3600000, answeredAt: null };
    this.escalations.push(e); return e;
  }
  // The simulated human answers after a stated delay; this tests the clock, not a real person's behaviour.
  answer(id, afterHours) { const e = this.escalations.find((x) => x.id === id); e.answeredAt = e.raisedAt + afterHours * 3600000; }
  onTime(e) { return e.answeredAt !== null && e.answeredAt <= e.dueAt; }
}
