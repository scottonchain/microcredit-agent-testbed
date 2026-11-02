// Putting the app on the home screen. A link on another site cannot install a web app: a browser offers that
// only from the app's own address. Chromium browsers (Android Chrome, desktop Chrome and Edge) fire
// `beforeinstallprompt` and let the page open the install dialog. iOS Safari has no dialog: the person taps
// Share, then Add to Home Screen. Other browsers keep an Install or Add to Home screen entry in their menu.

let deferred = null;   // the captured beforeinstallprompt event; usable once
let installed = false; // appinstalled fired, the dialog was accepted, or the browser reports the app installed
const listeners = new Set();
const notify = () => listeners.forEach((fn) => { try { fn(); } catch {} });
const ua = () => navigator.userAgent || '';

// Already running from a home-screen icon (Android, desktop) or as an iOS home-screen web app.
export const standalone = () => { try { return (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true; } catch { return false; } };
// iPhone, iPod and iPad; iPadOS Safari reports a Mac user agent with touch points.
export const isIOS = () => /iP(hone|ad|od)/.test(ua()) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
// Chromium exposes the install event (whether or not it will fire); WebKit never does.
export const supportsPrompt = () => 'onbeforeinstallprompt' in window;
// WebKit family: iPhone, iPad and Mac Safari. Their home-screen and Dock apps keep their own copy of this site's data.
export const appleWebKit = () => isIOS() || (/Safari\//.test(ua()) && !/Chrome|Chromium|CriOS|Edg|Firefox|FxiOS/.test(ua()) && !supportsPrompt());
export const canPrompt = () => deferred !== null;
export const isInstalled = () => installed;
export const available = () => !standalone() && !installed;
export const kind = () => (deferred ? 'prompt' : isIOS() ? 'ios' : 'manual');
// The name a person knows their browser by. Every iOS browser runs WebKit and shares the home-screen behaviour.
export function browserName() {
  const u = ua();
  if (isIOS()) return /CriOS\//.test(u) ? 'Chrome' : /FxiOS\//.test(u) ? 'Firefox' : /EdgiOS\//.test(u) ? 'Edge' : 'Safari';
  if (/Edg\//.test(u)) return 'Edge'; if (/Firefox\//.test(u)) return 'Firefox'; if (/SamsungBrowser\//.test(u)) return 'Samsung Internet';
  if (/Chrome\//.test(u)) return 'Chrome'; if (/Safari\//.test(u)) return 'Safari'; return 'your browser';
}
// A page opened inside another app's own web view (Instagram, Facebook, Gmail on Android) cannot add to the
// home screen; the person opens it in the browser first. iOS web views lack the Safari token; Android WebViews
// carry "; wv)". Safari View Controller and Chrome Custom Tabs look like the browser and cannot be told apart.
export const inAppView = () => (isIOS() && !standalone() && !/Safari\//.test(ua())) || /; wv\)/.test(ua()) || /FBAN|FBAV|Instagram|Line\//.test(ua());
// A link with ?install=1 (the tester guide carries one) opens the app with the install step offered at once.
export const askedByLink = () => { try { return new URLSearchParams(location.search).has('install'); } catch { return false; } };
export const dropLinkFlag = () => { try { if (askedByLink()) history.replaceState(history.state, '', location.pathname + location.hash); } catch {} };
export const onChange = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };

export function watch() {
  if (window.__bip && !deferred) deferred = window.__bip; // fired before this module ran; index.html keeps it
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferred = e; notify(); });
  window.addEventListener('appinstalled', () => { deferred = null; installed = true; notify(); });
  try { window.matchMedia('(display-mode: standalone)').addEventListener('change', notify); } catch {}
  // An app installed earlier and opened in a browser tab gets no install event; Chrome can say it is installed
  // when the manifest lists this app under related_applications.
  try { if (navigator.getInstalledRelatedApps) navigator.getInstalledRelatedApps().then((apps) => { if (apps && apps.length) { installed = true; notify(); } }).catch(() => {}); } catch {}
}

// Opens the browser's install dialog. Resolves to 'accepted', 'dismissed' or null when no dialog is available.
export async function prompt() {
  const e = deferred; if (!e) return null; deferred = null;
  try { await e.prompt(); const r = await e.userChoice; const o = (r && r.outcome) || null; if (o === 'accepted') installed = true; return o; } catch { return null; } finally { notify(); }
}
