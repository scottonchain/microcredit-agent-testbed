// The passkey prompt only works while this page is in front. If it is not, the browser refuses with the technical
// text "The document is not focused", which used to be shown as "Cancelled. Nothing was sent". These helpers check
// the page at the exact moment the browser's passkey call is made and, if it is not in front, fail at once with a named
// FocusError. There is deliberately no waiting and no resume: the attempt ends, nothing is signed, and the person must
// tap the button again (a fresh user action). Pure functions over an injected document so they can be tested without a browser.
export class FocusError extends Error {
  constructor(message) { super(message || 'The document is not focused. Return to this page and try again.'); this.name = 'FocusError'; }
}
export const isForeground = (doc) => !!doc && doc.visibilityState === 'visible' && (typeof doc.hasFocus !== 'function' || doc.hasFocus());

// Wraps the browser's passkey "get" call. `state.approved` becomes true only after the person has approved (the call
// resolved), which lets a later failure be described truthfully: before approval nothing can have been signed.
export function guardedGet(get, doc, state) {
  return async (credentialOptions) => {
    if (!isForeground(doc)) throw new FocusError();
    const result = await get(credentialOptions);
    state.approved = true;
    return result;
  };
}
