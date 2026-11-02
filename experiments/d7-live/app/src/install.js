// Putting the app on the home screen. A link on another site cannot install a web app: a browser offers that
// only from the app's own address. Chromium browsers (Android Chrome, desktop Chrome and Edge) fire
// `beforeinstallprompt` and let the page open the install dialog. iOS Safari has no dialog: the person taps
// Share, then Add to Home Screen. Other browsers keep an Install or Add to Home screen entry in their menu.

let deferred = null;   // the captured beforeinstallprompt event; usable once
let installed = false; // appinstalled fired on this page
const listeners = new Set();
const notify = () => listeners.forEach((fn) => { try { fn(); } catch {} });

// Already running from a home-screen icon (Android, desktop) or as an iOS home-screen web app.
export const standalone = () => { try { return (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true; } catch { return false; } };
// iPhone, iPod and iPad; iPadOS Safari reports a Mac user agent with touch points.
export const isIOS = () => /iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
export const supportsPrompt = () => 'onbeforeinstallprompt' in window;
export const canPrompt = () => deferred !== null;
export const available = () => !standalone() && !installed;
export const kind = () => (deferred ? 'prompt' : isIOS() ? 'ios' : 'manual');
// The site's "install" link opens the app with ?install=1 so the install step is offered at once.
export const askedByLink = () => { try { return new URLSearchParams(location.search).has('install'); } catch { return false; } };
export const dropLinkFlag = () => { try { if (askedByLink()) history.replaceState(history.state, '', location.pathname + location.hash); } catch {} };
export const onChange = (fn) => listeners.add(fn);

export function watch() {
  if (window.__bip && !deferred) deferred = window.__bip; // fired before this module ran; index.html keeps it
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferred = e; notify(); });
  window.addEventListener('appinstalled', () => { deferred = null; installed = true; notify(); });
  try { window.matchMedia('(display-mode: standalone)').addEventListener('change', notify); } catch {}
}

// Opens the browser's install dialog. Resolves to 'accepted', 'dismissed' or null when no dialog is available.
export async function prompt() {
  const e = deferred; if (!e) return null; deferred = null;
  try { await e.prompt(); const r = await e.userChoice; return (r && r.outcome) || null; } catch { return null; } finally { notify(); }
}

// On browsers that fire beforeinstallprompt it usually arrives shortly after load; wait briefly for it so a
// sheet opened on page load can offer the dialog instead of menu instructions.
export const settle = (ms = 1500) => new Promise((resolve) => {
  if (deferred || !supportsPrompt() || standalone()) return resolve();
  const t = setTimeout(done, ms);
  function done() { clearTimeout(t); listeners.delete(done); resolve(); }
  listeners.add(done);
});
