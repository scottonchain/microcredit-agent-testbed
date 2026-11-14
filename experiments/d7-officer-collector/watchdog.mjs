// Watchdog for the collector, deliberately independent of it: no imports. It must run somewhere that does not depend on the
// collector's host, schedule or delivery path (an unqualified, unassigned deployment choice; see CONTRACT.md). Pure, never throws.
// checkWatchdog({ nowMs, record, maxSilenceS, skewS }) -> { status, alerts }; record is the collector's run record
// { at: ISO time, status: 'ok' | 'alert' | 'crashed' } as last written, or anything else when missing or damaged.
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
export function checkWatchdog(input) {
  try {
    const { nowMs, record, maxSilenceS, skewS = 60 } = input && typeof input === 'object' ? input : {};
    const alerts = []; const add = (code, detail) => alerts.push({ code, detail });
    if (!isNum(nowMs) || !(isNum(maxSilenceS) && maxSilenceS >= 60 && maxSilenceS <= 86400) || !(isNum(skewS) && skewS >= 1 && skewS <= 300)) return { status: 'ALERT', alerts: [{ code: 'CONFIG_INVALID', detail: 'nowMs, maxSilenceS (60 to 86400) or skewS (1 to 300) is invalid' }] };
    if (!record || typeof record !== 'object' || typeof record.at !== 'string' || !Number.isFinite(Date.parse(record.at)) || !['ok', 'alert', 'crashed'].includes(record.status)) add('WATCHDOG_RECORD_MISSING', 'no usable collector run record');
    else {
      const at = Date.parse(record.at);
      if (at > nowMs + skewS * 1000) add('FUTURE_RECORD', 'the collector run record is dated in the future');
      else if ((nowMs - at) / 1000 > maxSilenceS) add('COLLECTOR_MISSED_INVOCATION', `no collector run for ${Math.round((nowMs - at) / 1000)} s, limit ${maxSilenceS} s`);
      if (record.status === 'crashed') add('COLLECTOR_CRASHED', 'the last collector run ended in a crash');
    }
    return { status: alerts.length ? 'ALERT' : 'OK', alerts };
  } catch (e) { return { status: 'ALERT', alerts: [{ code: 'WATCHDOG_FAILURE', detail: 'watchdog threw' }] }; }
}
