// The passkey prompt only works while this page is in front. If it is not, the browser refuses with the technical
// text "The document is not focused", which used to be shown as "Cancelled. Nothing was sent". These helpers check
// the page at the exact moment the browser's passkey call is made, wait briefly for the page to come back, and
// otherwise fail with a named FocusError. Pure functions over an injected document so they can be tested without a browser.
export class FocusError extends Error {
  constructor(message) { super(message || 'The document is not focused. Return to this page and try again.'); this.name = 'FocusError'; }
}
export const isForeground = (doc) => !!doc && doc.visibilityState === 'visible' && (typeof doc.hasFocus !== 'function' || doc.hasFocus());

export function waitForeground(doc, { timeoutMs = 3000, setTimer = setTimeout, clearTimer = clearTimeout } = {}) {
  if (isForeground(doc)) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const win = doc && doc.defaultView;
    let timer = null;
    const cleanup = () => { clearTimer(timer); doc.removeEventListener('visibilitychange', check); if (win) win.removeEventListener('focus', check); };
    const check = () => { if (isForeground(doc)) { cleanup(); resolve(); } };
    timer = setTimer(() => { cleanup(); reject(new FocusError()); }, timeoutMs);
    doc.addEventListener('visibilitychange', check);
    if (win) win.addEventListener('focus', check);
  });
}

// Wraps the browser's passkey "get" call. `state.approved` becomes true only after the person has approved (the call
// resolved), which lets a later failure be described truthfully: before approval nothing can have been signed.
export function guardedGet(get, doc, state, options) {
  return async (credentialOptions) => {
    await waitForeground(doc, options);
    const result = await get(credentialOptions);
    state.approved = true;
    return result;
  };
}
