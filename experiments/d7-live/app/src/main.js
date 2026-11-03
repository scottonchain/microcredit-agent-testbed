import qrcode from 'qrcode-generator';
import * as C from './core.js';
import { friendly } from './errors.js';
import * as I from './install.js';

const $ = (s) => document.querySelector(s);
const app = $('#app');
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const S = { client: null, cred: null, account: null, addr: null, bundler: null, snap: null };
I.watch();
const short = (a) => a.slice(0, 6) + '…' + a.slice(-4);
const days = (secs) => Math.max(0, Math.ceil(secs / 86400));
const centsText = (x) => x === 0n ? 'no interest yet' : x < 100n ? 'a fraction of a cent of interest' : x < C.CENT ? `less than a cent of interest (${(Number(x) / 1e4).toFixed(2).replace(/\.?0+$/, '')} of a cent)` : `${(Number(x) / 1e4).toFixed(2).replace(/\.?0+$/, '')} cents of interest`;
const devWord = () => (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) ? 'phone' : 'computer');
const fmtDate = (ts) => new Date(ts * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
let chainNow = null; // block time, so the screens agree with the pool even when the phone clock is wrong
const now = () => chainNow ?? Math.floor(Date.now() / 1000);
const dueLine = (l) => { const day = (t) => Math.floor(t / 86400); const dd = day(l.dueAt) - day(now()); const date = fmtDate(l.dueAt); // calendar days, so the phone's date and this line agree
  if (dd > 0) return `Due in ${dd} day${dd === 1 ? '' : 's'}, by ${date}.`;
  if (dd === 0) return `Due today (${date}). Pay back today and it is on time.`;
  const late = -dd; return `Late by ${late} day${late === 1 ? '' : 's'}: it was due ${date}. Pay back now. There is no late fee; only the small interest keeps growing.${late >= 7 ? ' After 30 days late the loan counts as a default: you could not borrow again, and the desk or friend who backed you would lose what they put up.' : ''}`; };

let sheetReturnFocus = null; // where focus goes back to when the sheet closes
function sheet({ title, body = '', actions = [] }) {
  const o = $('#overlay'); if (o.hidden) sheetReturnFocus = document.activeElement;
  $('#overlayTitle').textContent = title; $('#overlayBody').innerHTML = body;
  const box = $('#overlayActions'); box.innerHTML = '';
  actions.forEach((a) => { const b = document.createElement('button'); b.textContent = a.label; if (a.secondary) b.className = 'secondary'; b.onclick = a.onClick; box.appendChild(b); });
  o.hidden = false; const first = box.querySelector('button'); if (first) first.focus();
}
const closeSheet = () => { $('#overlay').hidden = true; const r = sheetReturnFocus; sheetReturnFocus = null; if (r && r.focus && document.contains(r)) { try { r.focus(); } catch {} } };
const go = (r) => { location.hash = r; };
const copy = async (t, btn) => { try { await navigator.clipboard.writeText(t); if (btn) { const o = btn.textContent; btn.textContent = 'Copied'; setTimeout(() => (btn.textContent = o), 1200); } } catch { prompt('Copy this:', t); } };

async function refresh() { S.snap = await C.snapshot(S.client, S.addr); try { chainNow = Number((await S.client.getBlock()).timestamp); } catch {} return S.snap; }

// ---------- running an action ----------
async function run(title, calls, { retryIds, summary, stay: stayHere, quiet, doneActions = [] } = {}) {
  const steps = ['Approve with your fingerprint, face or screen lock', 'Sending to the test network', 'Done'];
  const draw = (i, extra = '') => sheet({ title, body: `<ul class="steps">${steps.map((s, k) => `<li class="${k < i ? 'done' : k === i ? 'on' : ''}">${k < i ? '✓ ' : ''}${s}</li>`).join('')}</ul>${extra}` });
  draw(0);
  let attempt = 0, lastErr = null;
  for (;;) {
    try {
      const r = await C.send(S.bundler, S.account, calls, (st) => draw(st === 'sign' ? 0 : 1));
      if (r.success) {
        let extra = ''; try { extra = summary ? await summary(r) : ''; } catch {}
        const stay = stayHere || location.hash.startsWith('#credit');
        if (quiet) { closeSheet(); if (!stay) { location.hash = '#home'; render(); } return r; } // a chat line needs no Done box; a screen that stays is not re-drawn under the person's fingers (the chat poller shows the new line)
        if (!stay) { location.hash = '#home'; render(); } // the fresh home screen sits behind the Done sheet, so nothing looks failed
        sheet({ title: 'Done', body: `<div class="note ok">${esc(title)}: done.</div>${extra}<details><summary class="muted">Receipt</summary><p class="muted">${esc(new Date(now() * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }))}: ${esc(title)}, from wallet ${esc(short(S.addr))}. Recorded on the test network as ${esc(String(r.txHash).slice(0, 10))}… (<a href="${C.cfg.explorer}/tx/${r.txHash}" target="_blank" rel="noopener">public record site</a>; it may first check that you are not a robot).</p></details>`, actions: [{ label: 'OK', onClick: () => { closeSheet(); if (stay) render(); } }, ...doneActions] });
        return r;
      }
      lastErr = r.reason || 'Reverted';
      if (retryIds && attempt < 2 && /LoanNotRequested|WrongBorrower|NotCancellableYet/.test(lastErr)) { attempt++; calls = await retryIds(); continue; }
      sheet({ title: 'It did not go through', body: `<div class="note bad">${esc(friendly({ reason: lastErr }))}</div><details><summary>Technical details</summary><pre>${esc(lastErr)}</pre></details>`, actions: [{ label: 'Close', onClick: () => { closeSheet(); render(); } }] });
      return r;
    } catch (e) {
      const detail = (e.details || e.shortMessage || e.message || String(e));
      sheet({ title: 'It did not go through', body: `<div class="note bad">${esc(friendly(e))}</div><details><summary>Technical details</summary><pre>${esc(String(detail).slice(0, 600))}</pre></details>`, actions: [{ label: 'Close', onClick: () => { closeSheet(); render(); } }] });
      return null;
    }
  }
}
const refuse = (name) => { sheet({ title: 'Not possible yet', body: `<div class="note warn">${esc(friendly({ reason: name }))}</div>`, actions: [{ label: 'OK', onClick: closeSheet }] }); };

// ---------- putting the app on the home screen ----------
// On iPhone, iPad and Mac Safari the home-screen (or Dock) app keeps its own copy of the wallet entry, separate
// from the browser's; the passkey is meant to be shared. Each wallet has its own passkey, so a second wallet is a separate wallet, not a replacement.
let installToken = 0, installUnsub = null;
const endInstallWatch = () => { if (installUnsub) { installUnsub(); installUnsub = null; } };
const closeInstall = () => { endInstallWatch(); closeSheet(); };
const walletNote = (hasWallet) => { if (!I.appleWebKit()) return ''; const b = I.browserName(); return hasWallet
  ? `<p>Copy your recovery code first (it is on the Help screen). The home-screen app will not see the wallet you made in ${b}: in the new app tap <b>I already have a recovery code</b> and paste it. A second wallet there would be separate, with its own test dollars.</p>`
  : `<p>Add it first, then create your wallet from the new icon. A wallet created in ${b} does not show up in the home-screen app.</p>`; };
// Android installs the web app like any app: the phone's launcher decides whether the icon also lands on the Home
// screen. Samsung's One UI puts it in the Apps list only, unless Home screen settings says otherwise; a page cannot change that.
const androidWhereLine = () => `<p>Done. It is now one of your apps, called <b>Omnequa test</b>: open it from your app list or your Home screen.</p>`;
const inAppLine = () => `<p>Opened this inside another app (Messages, WhatsApp, Gmail)? First choose <b>Open in ${I.isIOS() ? 'Safari' : 'Chrome'}</b> (or <b>Open in browser</b>) from that app's menu, then tap Add to home screen again.</p>`;
function installContent(k, hasWallet) {
  const inApp = I.inAppView();
  if (k === 'prompt') return { body: '<p>Your browser will ask to install the Omnequa test wallet. It then opens from its own icon, without the browser bars. There is nothing to download from an app store.</p>', actions: [{ label: 'Install', onClick: doInstall }, { label: 'Not now', secondary: true, onClick: closeInstall }] };
  if (k === 'ios') return { body: `${inApp ? inAppLine() : ''}<ol class="howto"><li>Tap the <b>Share</b> button (the square with an arrow pointing up), usually at the bottom of the screen; on iPad it is at the top.</li><li>Scroll down and tap <b>Add to Home Screen</b>.</li><li>Tap <b>Add</b>.</li></ol><p>Then open the app from its new icon. If it is already there, just open it.</p>${walletNote(hasWallet)}${inApp ? '' : inAppLine()}`, actions: [{ label: 'OK', onClick: closeInstall }] };
  return { body: `${inApp ? inAppLine() : ''}<p>In your browser’s menu tap <b>Install app</b> or <b>Add to Home screen</b> (Samsung Internet: <b>Add page to</b>, then <b>Home screen</b>).</p><p class="muted">If it is already installed, open it from your home screen or app list. If there is nothing like that in the menu, keep using it here in the browser: nothing is lost.</p>${walletNote(hasWallet)}${inApp ? '' : inAppLine()}`, actions: [{ label: 'OK', onClick: closeInstall }] };
}
function showInstalled() {
  endInstallWatch(); installToken++;
  if (I.standalone()) sheet({ title: 'Installed', body: '<p>You are now in the app. Carry on here; later, open it from your Dock, Start menu or app launcher.</p>', actions: [{ label: 'OK', onClick: () => { closeSheet(); render(); } }] });
  else sheet({ title: 'Adding it now', body: I.isAndroid() ? androidWhereLine() : '<p>In a few seconds, look for an icon named <b>Omnequa test</b> on your home screen or in your app list. You can keep using this tab or close it.</p>', actions: [{ label: 'OK', onClick: () => { closeSheet(); render(); } }] });
}
async function doInstall() {
  if (I.isInstalled()) return showInstalled();
  const my = ++installToken; endInstallWatch();
  sheet({ title: 'Add to your home screen', body: '<p>Your browser is asking now: tap <b>Install</b> there.</p>', actions: [{ label: 'Cancel', secondary: true, onClick: closeInstall }] });
  const o = await I.prompt();
  if (my !== installToken || $('#overlay').hidden) return; // the person closed the sheet or moved on
  if (o === 'accepted') showInstalled();
  else sheet({ title: 'Not installed', body: '<p>No problem. You can add it from your browser’s menu, or here after you reopen the page.</p>', actions: [{ label: 'OK', onClick: closeInstall }] });
}
function installSheet() {
  const hasWallet = !!S.cred; const my = ++installToken; endInstallWatch();
  const draw = () => { const { body, actions } = installContent(I.kind(), hasWallet); sheet({ title: 'Add to your home screen', body, actions }); };
  draw();
  // The browser's install event can arrive after the sheet opened (first visit, slow network): upgrade the open
  // sheet in place. If the app gets installed meanwhile (browser menu), say so instead of offering a dialog.
  installUnsub = I.onChange(() => {
    if (my !== installToken || $('#overlay').hidden || $('#overlayTitle').textContent !== 'Add to your home screen') return endInstallWatch();
    if (I.isInstalled()) return showInstalled();
    if (I.kind() === 'prompt') draw();
  });
}
const installCard = () => I.available() ? '<div class="card" data-install><p><b>Add to your home screen</b> (optional)</p><p class="muted">It then opens from its own icon, like any app.</p><button class="secondary" id="install">Add to home screen</button></div>' : '';
const wireInstall = () => { const b = $('#install'); if (b) b.onclick = installSheet; };

// ---------- screens ----------
function header(title, back = true) { return `<div class="row" style="align-items:center">${back ? '<a class="back" href="#home" onclick="if (history.length > 1) { history.back(); return false; }">‹ Back</a>' : '<span></span>'}${title === 'Help' ? '' : '<a class="back" href="#help">Help</a>'}</div><h1>${esc(title)}</h1>`; }

function renderWelcome() {
  app.innerHTML = `${header('Try a small loan', false)}
  <p><b>This is a practice app: the dollars in it are not real and cannot pay a bill or buy anything.</b> Try borrowing up to $${Number(C.cfg.maxLine || 5)} of them, pay it back, and tell us how it went. There is no real loan here yet; this test is how we learn whether a real one should exist. You do not need to get test dollars from anywhere: the credit desk provides the few cents the interest needs.</p>
  <div class="card">${I.appleWebKit() ? (I.standalone()
    ? '<div class="note warn"><b>Already made a wallet in a browser on this device?</b> Tapping Create my wallet here makes a second, separate wallet; the first one’s test dollars stay in the first wallet. Instead, in that browser open Help, copy the recovery code, then tap <b>I already have a recovery code</b> below and paste it.</div>'
    : '<p class="muted">Made a wallet in the home-screen app already? Restore it with its recovery code (below) instead of creating a new one: a new wallet here would be a separate wallet with its own test dollars.</p>') : ''}<button id="create">Get started</button><p class="muted">Your fingerprint, face or screen lock is the key: no password, nothing to download, nothing to sign up for.${devWord() === 'computer' ? ' On a shared computer, remove the wallet from the Help screen when you are done.' : ''}</p></div>
  <details class="card"><summary>I have a recovery code from another ${devWord()}</summary><label for="rc">Recovery code</label><textarea id="rc" rows="3" autocapitalize="off" autocorrect="off" spellcheck="false"></textarea><button id="import" class="secondary" style="margin-top:8px">Restore wallet</button></details>
  ${installCard()}`;
  wireInstall();
  $('#create').onclick = async () => {
    $('#create').disabled = true; sheet({ title: 'Setting up your wallet', body: '<p>Approve the prompt on your phone (fingerprint, face or screen lock). This takes a few seconds.</p>' });
    try { const cred = await C.createPasskey('Omnequa test wallet'); C.saveCred(cred); await boot(); closeSheet(); go(C.cfg.desk ? 'ask' : 'home'); render(); }
    catch (e) { if ($('#create')) $('#create').disabled = false; sheet({ title: 'Could not set up', body: `<div class="note bad">${esc(friendly(e))}</div><details><summary>Technical details</summary><pre>${esc(String(e.message || e).slice(0, 400))}</pre></details>`, actions: [{ label: 'Close', onClick: closeSheet }] }); }
  };
  $('#import').onclick = async () => {
    try { const c = C.parseRecovery($('#rc').value); C.saveCred(c); await boot(); go('home'); render(); }
    catch { sheet({ title: 'That code does not work', body: '<div class="note bad">Paste the full recovery code exactly as saved.</div>', actions: [{ label: 'OK', onClick: closeSheet }] }); }
  };
}

async function renderHome(my = renderSeq) {
  app.innerHTML = `<h1>Your wallet</h1><div class="card"><div class="muted">Loading…</div></div>`;
  let s; try { s = await refresh(); if (stale(my)) return; } catch (e) { if (stale(my)) return; app.innerHTML = `<h1>Your wallet</h1><div class="note bad">${esc(friendly(e))}</div><button id="retry">Try again</button>`; $('#retry').onclick = renderHome; return; }
  const loans = C.openLoans(s); const active = loans.find((l) => l.status === C.ST.Active); const waiting = loans.find((l) => l.status === C.ST.Requested);
  if (C.cfg.desk && s.limit === 0n) { try { const d = await C.deskState(S.client, S.addr); s.deskThread = d.thread.length > 0; s.deskWaiting = d.unanswered > 0; } catch {} if (stale(my)) return; }
  const apr = Number(s.rate) / 100;
  app.innerHTML = `<div class="row"><span></span><a class="back" href="#help">Help</a></div><h1>Your wallet</h1>
  <div class="card"><div class="muted">Test dollars in your wallet</div><div class="big" id="bal">${C.money(s.usdcBal)}</div>${C.cfg.desk && s.backedBy.some((b) => b.who.toLowerCase() === C.cfg.desk.toLowerCase()) && s.usdcBal > 0n && (active || waiting || !s.loans.length) ? '<p class="muted">Includes the few cents the credit desk put here to cover your interest.</p>' : ''}</div>
  <div class="card"><div class="muted">${active || waiting ? 'Your credit limit' : 'You can borrow up to'}</div><div class="big" id="avail">${s.limit === 0n && C.cfg.desk && !s.defaulted ? 'Ask the desk first' : C.money(active || waiting ? s.limit : s.available)}</div>
    ${C.cfg.desk && !s.defaulted ? (s.limit === 0n ? (s.deskThread ? '<button id="gCredit">Credit desk</button>' : '<button id="gCredit">Ask for a loan</button>') : '<button class="secondary" id="gCredit">Credit desk</button>') : ''}<p class="muted">${s.limit === 0n ? (C.cfg.desk ? (s.deskThread ? (s.deskWaiting ? 'Your request is with the credit officer; the answer appears under Credit desk, usually within a minute.' : 'The credit desk answered under Credit desk; it could not back a loan yet.') : 'Say how much you need and what for; an AI credit officer answers in the app. When you owe something, a Pay back button appears here.') : 'You have no credit yet. <a href="#credit">How to get credit</a>') : active || waiting ? `You can borrow again after you pay this loan back. No fees; interest about ${(apr / 12).toFixed(1)}% a month.` : `Your limit is ${C.money(s.limit)}. No fees; interest about ${(apr / 12).toFixed(1)}% a month (${apr.toFixed(2)}% a year). When you owe something, a Pay back button appears here.`}</p></div>
  ${s.backedBy.length || s.youBack.length ? `<div class="card"><h2>Who vouches for you</h2><p class="muted">Backing is a promise to cover your loan if you do not pay it back.</p>${s.backedBy.length ? `<div class="muted">You are backed by</div>${s.backedBy.map((b) => `<div class="row">${C.cfg.desk && b.who.toLowerCase() === C.cfg.desk.toLowerCase() ? '<span>The credit desk (the AI officer that vouches for you)</span>' : `<span class="addr" style="border:0;padding:2px 0">${esc(short(b.who))}</span>`}<b>${C.money(b.amount)}</b></div>`).join('')}` : ''}${s.youBack.length ? `<div class="muted" style="margin-top:8px">You back</div>${s.youBack.map((b) => `<div class="row"><span class="addr" style="border:0;padding:2px 0">${esc(short(b.who))}</span><span><b>${C.money(b.amount)}</b> <a href="#back?to=${esc(b.who)}">Change</a></span></div>`).join('')}<p class="muted">What you back is locked as a guarantee until your friend repays.</p>` : ''}</div>` : ''}
  ${waiting ? `<div class="note warn">A loan of ${C.money(waiting.principal)} was requested but not paid out.<div class="grid"><button id="finish">Finish it</button><button class="secondary" id="cancelReq">Cancel it</button></div></div>` : ''}
  ${active ? `<div class="card"><div class="muted">You owe today</div><div class="big" id="owed">${C.money(active.owed)}</div>${active.owed > active.principal ? `<p class="muted">${C.money(active.principal)} borrowed plus ${centsText(active.owed - active.principal)} so far.</p>` : ''}<p class="${active.dueAt < now() ? 'note bad' : 'muted'}">${dueLine(active)}${active.dueAt > now() ? ` Interest grows a little each day: about ${C.money(C.ceilCent(active.owed + (active.principal * active.rateBps * BigInt(Math.max(0, active.dueAt - now()))) / (10000n * 31536000n)))} by the due date if you wait until then.` : ''}</p><button id="payNow">Pay back</button></div>` : ''}
  ${s.defaulted ? '<div class="note bad">This wallet has a defaulted loan and cannot borrow again.</div>' : ''}
  <div class="grid"><button id="gBorrow" ${active || waiting || s.defaulted ? 'disabled' : ''} ${C.cfg.desk && s.limit === 0n && !active && !waiting && !s.defaulted ? 'hidden' : ''}>Borrow</button><button class="secondary" id="gHelp">Help</button></div>
  <details class="card more"><summary>More</summary><div class="grid"><button class="secondary" id="gSend">Send money</button><button class="secondary" id="gReceive">Receive</button><button class="secondary" id="gBack">Back a friend</button>${C.cfg.desk ? '<button class="secondary" id="gFeedback">Tell us how it went</button>' : ''}</div></details>`;
  if ($('#gFeedback')) $('#gFeedback').onclick = openFeedback;
  $('#gBorrow').onclick = () => go('borrow'); $('#gSend').onclick = () => go('send'); $('#gReceive').onclick = () => go('receive'); $('#gBack').onclick = () => go('back'); $('#gHelp').onclick = () => go('help');
  if (active) $('#payNow').onclick = () => go('repay');
  if ($('#gCredit')) $('#gCredit').onclick = () => go(s.limit === 0n && !s.deskThread ? 'ask' : 'credit');
  if (waiting) {
    $('#finish').onclick = () => run('Finish loan', [C.poolCall('disburseLoan', [waiting.id])]);
    $('#cancelReq').onclick = () => run('Cancel request', [C.poolCall('cancelLoan', [waiting.id])]);
  }
}

// One borrow path for the Borrow screen and the credit desk's "Borrow $X now" button (one tap, no second screen).
async function startBorrow(v, { thenHome = false } = {}) {
  sheet({ title: 'Borrow ' + C.money(v), body: '<p>Checking with the pool…</p>' }); const err = await C.preflight(S.client, S.addr, 'requestLoan', [v]);
  if (err) { refuse(err); return null; }
  const build = async () => { const id = await C.nextLoanId(S.client); return [C.poolCall('requestLoan', [v]), C.poolCall('disburseLoan', [id])]; };
  const r = await run('Borrow ' + C.money(v), await build(), { retryIds: build, summary: async () => { const s2 = await refresh(); const l = C.openLoans(s2).find((x) => x.status === C.ST.Active); return l ? `<p>You now owe <b>${C.money(C.ceilCent(l.owed))}</b>, due by <b>${fmtDate(l.dueAt)}</b>. Pay it back any time before then, with one tap on your wallet screen. Interest grows a little each day; the few cents the desk put in your wallet cover it.</p>` : ''; } });
  if (thenHome && r && r.success) go('home');
  return r;
}
async function renderBorrow(my = renderSeq) {
  let s; try { s = await refresh(); } catch { s = S.snap; if (!s) throw new Error('Cannot reach the test network'); } if (stale(my)) return; const apr = Number(s.rate) / 100;
  app.innerHTML = `${header('Borrow')}
  <div class="card"><div class="muted">Available to borrow</div><div class="big">${C.money(s.available)}</div></div>
  <label for="amt">How much?</label><input id="amt" inputmode="decimal" placeholder="e.g. 3" autocomplete="off">
  <div id="terms" class="note ok" hidden></div><div id="warn"></div>
  <button id="go" disabled>Borrow</button>
  <p class="muted">You get the money right away. Pay it back any time within 30 days, all at once or in parts. Interest about ${(apr / 12).toFixed(1)}% a month (${apr.toFixed(2)}% a year), no other fees.</p>`;
  const amt = $('#amt'), terms = $('#terms'), go_ = $('#go');
  const pre = new URLSearchParams((location.hash.split('?')[1]) || '').get('amt'); if (pre && C.parseUsd(String(Number(pre) / 1e6))) amt.value = (Number(pre) / 1e6).toFixed(2).replace(/\.00$/, '');
  const upd = () => {
    const v = C.parseUsd(amt.value); go_.disabled = true; terms.hidden = true; $('#warn').innerHTML = '';
    if (v === null) { if (amt.value.trim()) $('#warn').innerHTML = '<div class="note warn">Numbers only, like 3 or 3.50.</div>'; return; } if (v === 0n) return;
    if (v > s.available) { $('#warn').innerHTML = `<div class="note warn">${s.available === 0n ? esc(friendly({ reason: 'NoCredit' })) : 'That is more than you can borrow right now (' + C.money(s.available) + ').'}</div>`; return; }
    const interest = (v * s.rate * 30n) / (10000n * 365n);
    terms.hidden = false; const ci = C.ceilCent(interest); terms.innerHTML = `You receive <b>${C.money(v)}</b> now. If you wait the full 30 days you owe about <b>${C.money(C.ceilCent(v + interest))}</b> (interest about ${C.money(ci)}); less if you pay sooner.${s.usdcBal >= ci ? ' The interest is already covered by what is in your wallet.' : ` You will need about ${C.money(ci)} more in your wallet by then; the app tells you where to get it.`}`;
    go_.disabled = false;
  };
  amt.oninput = upd; upd();
  go_.onclick = async () => { const v = C.parseUsd(amt.value); if (!v) return; go_.disabled = true; await startBorrow(v); go_.disabled = false; };
}

async function renderRepay(my = renderSeq) {
  let s; try { s = await refresh(); } catch { s = S.snap; if (!s) throw new Error('Cannot reach the test network'); } if (stale(my)) return; const l = s.loans.find((x) => x.status === C.ST.Active);
  if (!l) { app.innerHTML = `${header('Pay back')}<div class="card"><p>You have no loan to pay back.</p></div>`; return; }
  const quote = C.ceilCent(l.owed), pay = quote + C.headroom(l.principal); const short_ = quote > s.usdcBal ? quote - s.usdcBal : 0n;
  app.innerHTML = `${header('Pay back')}
  <div class="card"><div class="muted">You owe right now</div><div class="big">${C.money(l.owed)}</div><p class="muted">Borrowed ${C.money(l.principal)}${l.owed > l.principal ? ` plus ${centsText(l.owed - l.principal)} so far` : ''}. ${dueLine(l)} Your wallet has ${C.money(s.usdcBal)}.</p></div>
  ${short_ > 0n ? `<div class="note warn">You are ${C.money(short_ + C.CENT)} short: the interest is more than what is in your wallet.${C.cfg.desk ? ' Tap below and the credit desk sends the missing cents to this wallet (practice money). This screen then updates by itself.<div class="grid"><button id="askCents">Ask the desk for the cents</button></div><p class="muted" id="centsNote" hidden>Asked. The desk usually answers within a minute.</p>' : ''}${C.cfg.desk ? '' : `<details style="margin-top:8px"><summary>Get test dollars yourself</summary><p class="muted">Your address, for the test-dollar faucet (choose the Base Sepolia network and USDC there):</p><div class="addr">${esc(S.addr)}</div><div class="grid"><button class="secondary" id="copyA">Copy my address</button><button class="secondary" id="faucet">Open the faucet</button></div></details>`}</div>` : ''}
  <button id="all" ${short_ > 0n ? 'disabled' : ''}>Pay back everything</button>
  <details class="card" style="margin-top:18px"><summary>Pay only part</summary><label for="part">Amount</label><input id="part" inputmode="decimal" placeholder="e.g. 5"><div id="partWarn"></div><button id="partGo" class="secondary" style="margin-top:8px">Pay this part</button></details>
  <p class="muted">Only what you owe is taken, to the fraction of a cent.</p>`;
  if (short_ > 0n) { if ($('#faucet')) { $('#faucet').onclick = () => { copy(S.addr); window.open(C.cfg.faucet, '_blank', 'noopener'); }; $('#copyA').onclick = (e) => copy(S.addr, e.target); }
    if ($('#askCents')) $('#askCents').onclick = async () => {
      const r = await run('Ask for the cents', [C.deskCall('say', [`I am ${C.money(short_ + C.CENT)} short to pay back my loan. Please send the cents for the interest.`])], { stay: true, summary: async () => '<p>Asked. The desk usually answers within a minute, and this screen updates by itself.</p>' });
      if (r && r.success) { $('#askCents').disabled = true; $('#centsNote').hidden = false; const t0 = Date.now(); const poll = setInterval(async () => { if (!location.hash.startsWith('#repay') || Date.now() - t0 > 240000) return clearInterval(poll); try { const s2 = await refresh(); if (s2.usdcBal >= quote) { clearInterval(poll); render(); } } catch {} }, 4000); }
    }; }
  const doPay = async (amount, approveAmt, label) => {
    const allowance = await S.client.readContract({ address: C.cfg.usdc, abi: C.erc20Abi, functionName: 'allowance', args: [S.addr, C.cfg.pool] });
    const calls = []; if (allowance < approveAmt) calls.push(C.usdcCall('approve', [C.cfg.pool, approveAmt]));
    calls.push(C.poolCall('repayLoan', [l.id, amount]));
    const before = { bal: s.usdcBal, dues: await S.client.readContract({ address: C.cfg.pool, abi: C.poolAbi, functionName: 'duesPaid', args: [S.addr] }), limit: s.limit };
    await run(label || 'Pay back', calls, { doneActions: [{ label: 'Tell us how it went', secondary: true, onClick: () => { closeSheet(); render(); openFeedback(); } }], summary: async () => {
      const s2 = await refresh(); const l2 = s2.loans.find((x) => x.id === l.id); const paid = before.bal - s2.usdcBal; const elapsed = BigInt(Math.max(0, now() - l.disbursedAt)); const accrued = (l.principal * l.rateBps * elapsed) / (10000n * 31536000n); const totalPaid = l.principal + accrued; // simple interest on the original principal, over the whole loan
      const dues = (await S.client.readContract({ address: C.cfg.pool, abi: C.poolAbi, functionName: 'duesPaid', args: [S.addr] })) - before.dues;
      const intr = totalPaid > l.principal ? totalPaid - l.principal : 0n; const cents = (x) => x === 0n ? 'no interest (none had built up yet)' : centsText(x);
      if (l2 && l2.status === C.ST.Repaid) return `<p>Loan closed. ${totalPaid > paid + C.CENT ? `You paid <b>${C.money(paid)}</b> now and ${C.money(totalPaid - paid)} earlier` : `You paid <b>${C.money(paid)}</b>`}: the ${C.money(l.principal)} you borrowed plus ${cents(intr)}.${dues >= C.CENT ? ` ${C.money(dues)} of that interest counts toward your own credit, so your limit is now <b>${C.money(s2.limit)}</b>.` : ''} Your wallet now has <b>${C.money(s2.usdcBal)}</b>: the cents the desk gave you for the interest, which you can keep. You owe nothing and can borrow again right away.${devWord() === 'computer' ? ' On a shared computer, remove the wallet from the Help screen when you are done.' : ''}</p>`;
      return `<p>You paid <b>${C.money(paid)}</b>. Still owed: <b>${C.money(C.ceilCent(l2 ? l2.owed : 0n))}</b>. Interest is paid first, then the amount borrowed.</p>`; } });
  };
  $('#all').onclick = () => doPay(pay, pay, 'Pay back ' + C.money(l.owed));
  $('#partGo').onclick = () => { const v = C.parseUsd($('#part').value); $('#partWarn').innerHTML = ''; if (!v) { $('#partWarn').innerHTML = '<div class="note warn">Numbers only, like 2 or 2.50.</div>'; return; } if (v > s.usdcBal) return refuse('InsufficientBalance'); doPay(v, v, 'Pay back ' + C.money(v)); };
}

function renderSend() {
  const s = S.snap;
  app.innerHTML = `${header('Send')}
  <div class="card muted">Available: ${C.money(s?.usdcBal ?? 0n)}</div>
  <label for="to">To: your friend's address (from the Receive screen in their app; it starts with 0x)</label><input id="to" placeholder="0x…" autocapitalize="off" autocorrect="off" spellcheck="false">
  <label for="amt">Amount</label><input id="amt" inputmode="decimal" placeholder="e.g. 3">
  <div id="warn"></div><button id="go" style="margin-top:12px">Send</button>`;
  $('#go').onclick = async () => {
    const to = $('#to').value.trim(), v = C.parseUsd($('#amt').value); const w = $('#warn'); w.innerHTML = '';
    if (!C.isAddress(to)) { w.innerHTML = '<div class="note warn">That is not a valid wallet address.</div>'; return; }
    if (!v) { w.innerHTML = '<div class="note warn">Enter an amount.</div>'; return; }
    if (to.toLowerCase() === S.addr.toLowerCase()) { w.innerHTML = '<div class="note warn">That is your own address.</div>'; return; }
    const bal = (await refresh()).usdcBal; if (v > bal) { w.innerHTML = `<div class="note warn">You only have ${C.money(bal)}.</div>`; return; }
    await run('Send ' + C.money(v), [C.usdcCall('transfer', [C.getAddress(to), v])]);
  };
}

function renderReceive() {
  const qr = qrcode(0, 'M'); qr.addData(S.addr); qr.make();
  app.innerHTML = `${header('Receive')}
  <div class="card"><p class="muted">A friend with this app can send you test dollars: show them this code, or send them the address.</p><div class="qr">${qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true })}</div><div class="addr" id="addrBox">${esc(S.addr)}</div><button id="cp" class="secondary" style="margin-top:8px">Copy address</button></div>
  <div class="card"><h2>Where test dollars come from</h2><p class="muted">The credit desk puts the cents for the interest in your wallet when it says yes, and sends more if you are ever short when paying back. You never need to fetch test dollars yourself.</p><details><summary>Advanced: the public test-dollar faucet</summary><p class="muted">Anyone can also get test USDC from Circle's faucet: choose <b>Base Sepolia</b> and <b>USDC</b> there and paste this address. Only needed if the desk is away.</p><button id="fc" class="secondary">Open the faucet</button></details></div>`;
  $('#cp').onclick = (e) => copy(S.addr, e.target); $('#fc').onclick = () => { copy(S.addr); window.open(C.cfg.faucet, '_blank', 'noopener'); };
}

const ASK_KEY = 'd7.ask';
const loadAsk = () => { try { return JSON.parse(localStorage.getItem(ASK_KEY)) || {}; } catch { return {}; } };
const saveAsk = (a) => { try { localStorage.setItem(ASK_KEY, JSON.stringify(a)); } catch {} };
// The first screen after set-up: how much, what for, when. Three taps and one approval, then the credit officer answers.
async function renderAsk(my = renderSeq) {
  if (!C.cfg.desk) return go('home');
  const maxLine = Number(C.cfg.maxLine || 5); const prev = loadAsk();
  app.innerHTML = '<h1>What do you need?</h1><div class="card"><div class="muted">One moment…</div></div>'; // paint at once: the wallet was just created and the reads below take a few seconds
  let s = S.snap; try { s = await refresh(); } catch {} if (stale(my)) return;
  if (s && (C.openLoans(s).length || s.limit > 0n)) return go('home');
  let d = null; try { d = await C.deskState(S.client, S.addr); } catch {} if (stale(my)) return;
  if (d && d.thread.length) return go('credit');
  const amounts = [1, 2, 3, 5].filter((a) => a <= maxLine); if (!amounts.includes(maxLine)) amounts.push(maxLine); const custom = prev.custom || false;
  const purposes = ['Groceries', 'Transport', 'School', 'Work tools', 'A bill', 'Something else'];
  const whens = [['Tomorrow', 'tomorrow'], ['In a week', 'in a week'], ['In two weeks', 'in two weeks'], ['In 30 days', 'in 30 days']];
  const a = { amount: prev.amount || null, purpose: prev.purpose || null, when: prev.when || null, custom };
  app.innerHTML = `<div class="row"><span></span><a class="back" href="#help">Help</a></div><h1>What do you need?</h1><p class="muted">Your wallet is ready; it opens with your fingerprint, face or screen lock.</p>
  <div class="card"><div class="muted">How much? (up to $${maxLine} in this practice version)</div><div class="chips" id="amt">${amounts.map((v) => `<button class="chip" data-v="${v}">$${v}</button>`).join('')}<button class="chip" data-v="other">Other</button></div><input id="amtOther" inputmode="decimal" placeholder="e.g. 3.75" maxlength="8" hidden><div id="amtWarn"></div></div>
  <div class="card"><div class="muted">What is it for? <span>(anyone on the test network can read this, so keep it general)</span></div><div class="chips" id="why">${purposes.map((p) => `<button class="chip" data-v="${esc(p)}">${esc(p)}</button>`).join('')}</div><input id="whyText" placeholder="A few words, no personal details" maxlength="120" hidden></div>
  <div class="card"><div class="muted">When do you plan to pay it back? (you have up to 30 days)</div><div class="chips" id="when">${whens.map(([l, v]) => `<button class="chip" data-v="${esc(v)}">${esc(l)}</button>`).join('')}</div></div>
  <div id="askCost" class="note ok" hidden></div><p class="muted" id="askPreview" hidden></p>
  <button id="askGo" disabled>Ask for this loan</button><p class="muted" id="askHint">Choose an amount, what it is for and when you plan to pay it back.</p>
  <p class="muted">An AI credit officer reads this and answers in the app, usually within a minute.</p>
  <p class="muted"><a href="#credit">Write to the credit desk in your own words instead</a></p>`;
  const paint = () => { for (const [id, k] of [['amt', 'amount'], ['why', 'purpose'], ['when', 'when']]) document.querySelectorAll(`#${id} .chip`).forEach((b) => b.classList.toggle('on', id === 'amt' && a.custom ? b.dataset.v === 'other' : String(b.dataset.v) === String(a[k])));
    $('#amtOther').hidden = !a.custom; $('#whyText').hidden = a.purpose !== 'Something else'; $('#askGo').disabled = !(a.amount && a.purpose && a.when); $('#askHint').hidden = !$('#askGo').disabled; { const miss = [!a.amount && 'an amount', !a.purpose && 'what it is for', !a.when && 'when you plan to pay it back'].filter(Boolean); $('#askHint').textContent = miss.length ? 'Still to choose: ' + miss.join(', ') + '.' : ''; }
    const pv = $('#askPreview'); if (a.amount && a.purpose && a.when) { const whyTxt = a.purpose === 'Something else' ? ($('#whyText').value.trim() || 'something I need') : a.purpose.toLowerCase(); pv.hidden = false; pv.textContent = `This is sent to the credit officer in your name: “I need $${a.amount} for ${whyTxt}. I can pay it back ${a.when}.”`; } else pv.hidden = true;
    const c = $('#askCost'); if (a.amount && s && s.rate !== undefined) { const v = C.parseUsd(String(a.amount)); const i30 = C.ceilCent((v * s.rate * 30n) / (10000n * 365n)); c.hidden = false; const dW = a.when === 'tomorrow' ? 1n : a.when === 'in a week' ? 7n : a.when === 'in two weeks' ? 14n : 30n; const iW = C.ceilCent((v * s.rate * dW) / (10000n * 365n)); c.innerHTML = `If the officer agrees: you get <b>${C.money(v)}</b> now. Pay it back any time within 30 days, with one tap in this app: ${dW < 30n ? `about ${C.money(iW)} of interest if you pay ${esc(a.when)}, ` : ''}${C.money(i30)} at most (after the full 30 days). No other fees.`; } else c.hidden = true; };
  $('#whyText').oninput = paint;
  document.querySelectorAll('.chip').forEach((b) => (b.onclick = () => { const k = b.parentElement.id === 'amt' ? 'amount' : b.parentElement.id === 'why' ? 'purpose' : 'when';
    if (k === 'amount') { if (b.dataset.v === 'other') { a.custom = true; a.amount = null; saveAsk(a); paint(); $('#amtOther').focus(); return; } a.custom = false; $('#amtWarn').innerHTML = ''; }
    a[k] = k === 'amount' ? Number(b.dataset.v) : b.dataset.v; saveAsk(a); paint(); if (k === 'purpose' && a.purpose === 'Something else') $('#whyText').focus(); }));
  $('#amtOther').oninput = () => { const raw = $('#amtOther').value.trim(); const v = C.parseUsd(raw); const ok = v !== null && v >= 1_000_000n && v <= BigInt(maxLine) * 1_000_000n; const why = !raw ? '' : v === null ? 'Numbers only, like 3.75.' : v < 1_000_000n ? 'At least $1.' : v > BigInt(maxLine) * 1_000_000n ? `$${raw.replace(/[$\s]/g, '')} is more than the $${maxLine} maximum in this practice version.` : ''; $('#amtWarn').innerHTML = why ? `<div class="note warn">${esc(why)}</div>` : ''; a.amount = ok ? Number(v) / 1e6 : null; saveAsk(a); paint(); };
  paint();
  $('#askGo').onclick = async () => {
    const why = a.purpose === 'Something else' ? ($('#whyText').value.trim() || 'something I need') : a.purpose.toLowerCase();
    const text = `I need $${a.amount} for ${why}. I can pay it back ${a.when}.`;
    saveAsk(a);
    const r = await run('Ask for the loan', [C.deskCall('say', [text])], { quiet: true });
    if (r && r.success) { go('credit'); render(); }
  };
}
let chatTimer = null, chatToken = 0;
function stopChat() { if (chatTimer) { clearInterval(chatTimer); chatTimer = null; } }
async function renderCredit(my = renderSeq) {
  stopChat(); const tok = ++chatToken;
  if (!C.cfg.desk) return renderCreditManual();
  let snap = S.snap; try { snap = await refresh(); } catch {} if (stale(my)) return; const activeLoan = snap ? C.openLoans(snap).find((l) => l.status === C.ST.Active || l.status === C.ST.Requested) : null; const hadLoan = snap ? snap.loans.some((l) => l.status === C.ST.Repaid) : false;
  const maxLine = C.cfg.maxLine || 5;
  app.innerHTML = `${header('Credit desk')}
  <div class="card"><p class="muted">The credit officer (an AI) answers here, usually within a minute. What you write is public on the test network: no names or personal details.</p>
  <div id="chat" class="chat"><div class="muted">Loading…</div></div><div id="typing" class="muted" hidden>The credit officer is reading your message…</div></div>
  <div class="card" id="askBox"><label for="msg" class="muted">Your message (public on the test network: no name, age, job, phone or address)</label><textarea id="msg" rows="3" maxlength="1000" placeholder="What is it for, how much (up to $${maxLine}), and when will you pay it back?"></textarea>
  <div class="grid"><button id="send">Send</button><button class="secondary" id="toBorrow" hidden>Borrow</button></div><div id="warn"></div></div>
  <details class="card"><summary>Or ask a friend to back you</summary><p>Send them your address. In their app they open <b>Back a friend</b> and enter it. What they lock becomes your limit.</p><div class="addr">${esc(S.addr)}</div><button class="secondary" id="cp" style="margin-top:8px">Copy address</button></details>`;
  $('#cp').onclick = (e) => copy(S.addr, e.target); $('#toBorrow').onclick = () => { const v = $('#toBorrow').dataset.v; if (v) startBorrow(BigInt(v), { thenHome: true }); else go('borrow'); };
  const greeting = `Hello, I am the credit officer, an AI. Tell me what the loan is for, how much you need (up to $${maxLine} in this test) and when you will pay it back.`;
  let lastLen = -1, lastBacking = -1n;
  const draw = async () => {
    if (tok !== chatToken || !$('#chat')) return;
    let d; try { d = await C.deskState(S.client, S.addr); } catch (e) { if (tok !== chatToken || !$('#chat')) return; if (lastLen < 0) $('#chat').innerHTML = `<div class="note bad">${esc(friendly(e))}</div>`; return; }
    if (tok !== chatToken || !$('#chat')) return;
    if (d.thread.length === lastLen && d.backing === lastBacking) return; lastLen = d.thread.length; lastBacking = d.backing;
    const bubbles = [{ from: 1, text: greeting }, ...d.thread].map((m) => `<div class="bub ${m.from === 0 ? 'me' : 'desk'}">${esc(m.text)}</div>`).join('');
    const askA = loadAsk().amount; const canNow = d.backing > 0n && !activeLoan ? (askA && C.parseUsd(String(askA)) <= d.backing ? C.parseUsd(String(askA)) : d.backing) : 0n;
    const rate = S.snap && S.snap.rate !== undefined ? S.snap.rate : null; const i30 = rate !== null && canNow > 0n ? C.ceilCent((canNow * rate * 30n) / (10000n * 365n)) : 0n;
    const granted = d.backing > 0n ? `<div class="note ok" id="granted">The officer agreed ${canNow > 0n && canNow < d.backing ? `to <b>${C.money(canNow)}</b> (what you asked for; the desk's limit for you is ${C.money(d.backing)})` : `: you can borrow up to <b>${C.money(d.backing)}</b>`}. The desk also put a few cents of test dollars in your wallet so you can pay the interest (in a real loan you would pay that yourself).${canNow > 0n ? ` <b>Borrow ${hadLoan ? 'again ' : ''}${C.money(canNow)} now</b>: you get ${C.money(canNow)}; pay back about ${C.money(canNow + i30)} within 30 days (the exact date shows once you borrow), less if sooner. The loan is made at once; your fingerprint, face or screen lock confirms it.` : activeLoan ? ' You have a loan open now; pay it back from your wallet screen before borrowing again.' : ''}</div>` : '';
    $('#toBorrow').textContent = canNow > 0n ? `Borrow ${hadLoan ? 'again ' : ''}${C.money(canNow)} now` : 'Borrow'; $('#toBorrow').dataset.v = canNow > 0n ? String(canNow) : ''; $('#toBorrow').className = canNow > 0n ? '' : 'secondary'; $('#send').className = canNow > 0n ? 'secondary' : '';
    $('#chat').innerHTML = bubbles + granted; $('#typing').hidden = d.unanswered === 0;
    $('#toBorrow').hidden = d.backing === 0n || !!activeLoan; $('#send').disabled = d.unanswered >= 3;
    $('#warn').innerHTML = d.unanswered >= 3 ? '<div class="note warn">Please wait for the officer to answer before writing again.</div>' : d.freeStake === 0n && d.backing === 0n ? '<div class="note warn">The desk has no free stake right now, so it cannot grant new lines until some is added.</div>' : '';
  };
  chatTimer = setInterval(() => { if (tok !== chatToken) return; if (location.hash.startsWith('#credit')) draw(); else stopChat(); }, 3000); await draw();
  $('#send').onclick = async () => {
    const text = $('#msg').value.trim(); if (!text) return; if (text.length > 1000) { $('#warn').innerHTML = '<div class="note warn">Please keep it under 1000 characters.</div>'; return; }
    const personal = /\b(my name is|i am \d{1,3}( years)?|i'm \d{1,3}\b|\d[\d\s-]{6,}\d|@|street|road\b|avenue|my (husband|wife|son|daughter|kids|children|employer|boss|salary|wage|payday))/i.test(text);
    const send = async () => { const r = await run('Send your message', [C.deskCall('say', [text])], { quiet: true }); if (r && r.success) { if ($('#msg')) $('#msg').value = ''; await draw(); } };
    if (personal) return sheet({ title: 'Before you send', body: '<div class="note warn">This looks like it has personal details (a name, age, number, family or work). Everything written here is public on the test network and cannot be taken back. The officer needs only what the money is for, how much and when you will pay it back.</div>', actions: [{ label: 'Let me change it', onClick: closeSheet }, { label: 'Send anyway', secondary: true, onClick: () => { closeSheet(); send(); } }] });
    await send();
  };
}
function renderCreditManual() {
  app.innerHTML = `${header('Get credit')}
  <div class="card"><h2>How credit works here</h2><p>You can borrow only against credit that exists. Nobody can make it up. Credit comes from two places:</p>
  <ul><li><b>A friend backs you.</b> They lock some of their own test USDC as a guarantee for you. Your limit goes up by what they lock.</li><li><b>A test credit line.</b> The test operator can grant a line for the experiment.</li></ul></div>
  <div class="card"><h2>Ask a friend to back you</h2><p>Send them your address. In their app they open <b>Back a friend</b> and enter it.</p><div class="addr">${esc(S.addr)}</div><button class="secondary" id="cp" style="margin-top:8px">Copy address</button></div>`;
  $('#cp').onclick = (e) => copy(S.addr, e.target);
}

async function renderBack() {
  const s = S.snap || (await refresh());
  const [credit, freeStake] = await S.client.readContract({ address: C.cfg.pool, abi: C.poolAbi, functionName: 'getFreeCredit', args: [S.addr] });
  const q = new URLSearchParams((location.hash.split('?')[1]) || ''); const pre = q.get('to') || '';
  app.innerHTML = `${header('Back a friend')}
  <div class="card"><p>Backing lets a friend borrow against <b>your</b> guarantee. If they do not pay back, the amount you backed with can be lost. Back only people you trust, with test money.</p><div class="muted">Backing uses your own credit first, so it can lower how much you can borrow yourself. You can back up to ${C.money(credit + freeStake)} more without adding stake. You have ${C.money(s.usdcBal)} in your wallet to lock as new stake.</div></div>
  <label for="to">Friend's wallet address</label><input id="to" value="${esc(pre)}" placeholder="0x…" autocapitalize="off" autocorrect="off" spellcheck="false">
  <div id="cur" class="muted"></div>
  <label for="amt">Total you back them with (min $1.00, or 0 to remove)</label><input id="amt" inputmode="decimal" placeholder="e.g. 10"><div id="warn"></div><div id="plan" class="note ok" hidden></div>
  <button id="go" style="margin-top:12px">Save backing</button>`;
  let cur = 0n;
  const readCur = async () => { const to = $('#to').value.trim(); cur = 0n; if (C.isAddress(to)) { const bk = await S.client.readContract({ address: C.cfg.pool, abi: C.poolAbi, functionName: 'getBacking', args: [S.addr, C.getAddress(to)] }); cur = bk[0] + bk[1]; } $('#cur').textContent = cur > 0n ? `You currently back this friend with ${C.money(cur)}. Enter the new total.` : ''; upd(); };
  const upd = () => { const v = C.parseUsd($('#amt').value); const p = $('#plan'); if (v === null) { p.hidden = true; return; } const total = credit + freeStake;
    if (v < cur) { p.hidden = false; p.innerHTML = v === 0n ? `This removes your backing of ${C.money(cur)}. It only works if your friend does not owe more than their remaining limit.` : `This lowers your backing from ${C.money(cur)} to ${C.money(v)}. It only works if your friend does not owe more than their remaining limit.`; return; }
    const extra = v - cur; const need = extra > total ? extra - total : 0n; p.hidden = false; p.innerHTML = extra === 0n ? 'Nothing changes.' : need > 0n ? `This adds ${C.money(extra)}. It will lock <b>${C.money(need)}</b> of your wallet's USDC as new stake.` : `This adds ${C.money(extra)} using your free credit or stake.`; };
  $('#to').oninput = readCur; $('#amt').oninput = upd; if (pre) readCur();
  $('#go').onclick = async () => {
    const to = $('#to').value.trim(), v = C.parseUsd($('#amt').value); const w = $('#warn'); w.innerHTML = '';
    if (!C.isAddress(to)) { w.innerHTML = '<div class="note warn">That is not a valid wallet address.</div>'; return; }
    if (v === null) { w.innerHTML = '<div class="note warn">Enter an amount.</div>'; return; }
    if (to.toLowerCase() === S.addr.toLowerCase()) return refuse('SelfBacking');
    if (v !== 0n && v < 1000000n) return refuse('BackingTooSmall');
    await readCur(); const total = credit + freeStake; const extra = v > cur ? v - cur : 0n; const need = extra > total ? extra - total : 0n;
    if (need > s.usdcBal) { w.innerHTML = `<div class="note warn">To add ${C.money(extra)} you need ${C.money(need)} more test USDC in your wallet to lock as stake. Get some from the faucet.</div>`; return; }
    if (v === cur) { w.innerHTML = '<div class="note warn">That is what you already back them with.</div>'; return; }
    const calls = []; if (need > 0n) { calls.push(C.usdcCall('approve', [C.cfg.pool, need])); calls.push(C.poolCall('stake', [need])); }
    calls.push(C.poolCall('back', [C.getAddress(to), v]));
    await run((v === 0n ? 'Remove backing for ' : 'Back ') + short(to), calls, { summary: async () => { const lim = await S.client.readContract({ address: C.cfg.pool, abi: C.poolAbi, functionName: 'getBorrowLimit', args: [C.getAddress(to)] }); return `<p>${esc(short(to))} can now borrow up to <b>${C.money(lim[0])}</b>.</p>`; } });
  };
}

function openFeedback() { if (!C.cfg.desk) return; sheet({ title: 'Send feedback', body: '<p class="muted">What did you tap, what did you see, what did you expect? It goes to the team through the credit desk, so it is public on the test network: no names or personal details.</p><textarea id="fbText" rows="4" maxlength="400" placeholder="I tapped… I saw… I expected…"></textarea><p class="muted">Up to 400 characters.</p>', actions: [{ label: 'Send', onClick: async () => { const t = $('#fbText').value.trim(); if (!t) return; closeSheet(); const r = await run('Send feedback', [C.deskCall('say', ['Feedback: ' + t])], { stay: true, quiet: true }); if (r && r.success) sheet({ title: 'Thank you', body: '<p>Your note is with the team.</p>', actions: [{ label: 'OK', onClick: closeSheet }] }); } }, { label: 'Not now', secondary: true, onClick: closeSheet }] }); }
function renderHelp() {
  const code = C.recoveryCode(S.cred);
  app.innerHTML = `${header('Help')}
  <div class="card"><h2>How it works</h2><ol><li>Ask the credit desk (an AI credit officer, in the app). It vouches for you up to a few dollars and puts a few cents in your wallet for the interest.</li><li>Borrow up to your limit. The money is in your wallet at once.</li><li>Pay it back within 30 days, all at once or in parts. Being late brings no fee, only the small interest; after 30 days late the loan counts as a default and you could not borrow again. Paying back builds your history.</li></ol><p class="muted">Test dollars have no value. The credit desk provides the few cents the interest needs, so there is nothing to fetch; in a real loan you would pay the interest yourself.</p></div>
  <div class="card"><h2>Words you may see</h2><ul class="words"><li><b>Wallet</b>: where this app keeps your test dollars; only your fingerprint, face or screen lock opens it.</li><li><b>Test dollars</b>: play money on a test network, worth nothing. You cannot spend them anywhere; they only show how borrowing and paying back work.</li><li><b>Credit officer</b>: an AI that decides whether the desk vouches for your loan with its own test dollars.</li><li><b>Backing</b>: that promise to cover a loan if it is not paid back.</li><li><b>Stake</b>: the test dollars the desk locks up behind its promise; when they are all in use, it cannot back anyone new until someone pays back.</li><li><b>Interest</b>: a few cents a month on what you borrow, paid when you pay back; the only cost.</li><li><b>Recovery code</b>: a long code that reopens this same wallet on another ${devWord()}.</li></ul></div>
  <div class="card"><h2>Send feedback</h2><p>Tell us what confused you: what you tapped and what you saw. No personal information, please.</p>${C.cfg.desk ? '<button class="secondary" id="fb">Send feedback</button>' : '<a class="btn secondary" id="fb" href="mailto:claude-microcredit@agentmail.to?subject=Omnequa%20test%20wallet%20feedback&body=What%20I%20tapped%3A%0AWhat%20I%20saw%3A%0AWhat%20I%20expected%3A%0A">Send feedback</a>'}</div>
  ${installCard()}
  <details class="card"><summary>Use this wallet on another ${devWord()}</summary><p class="muted">This code reopens the same wallet elsewhere. Keep it private. If you lose this ${devWord()}, the code reopens the same wallet; a loan stays yours either way.</p><div class="addr" style="max-height:150px;overflow:auto">${esc(code)}</div><button id="cp" class="secondary" style="margin-top:8px">Copy recovery code</button></details>
  <details class="card"><summary>Forget this wallet on this ${devWord()}</summary><p class="muted">Only this ${devWord()} forgets the wallet. Your loan record and your test dollars stay on the test network, and the recovery code brings the same wallet back. If you want it back later, copy the recovery code first (under "Use this wallet on another ${devWord()}", just above).${devWord() === 'computer' ? ' On a shared computer, remove it when you are done: anyone who can unlock this computer could open it.' : ''}</p><button class="secondary" id="reset">Remove this wallet from this ${devWord()}</button></details>
  `;
  wireInstall();
  $('#cp').onclick = (e) => copy(code, e.target);
  if (C.cfg.desk) $('#fb').onclick = openFeedback;
  $('#reset').onclick = () => sheet({ title: `Forget this wallet on this ${devWord()}?`, body: '<p>Your test dollars and any loan stay recorded on the test network; only this device forgets the wallet. Copy the recovery code first if you may want it back.</p>', actions: [{ label: 'Keep it', onClick: closeSheet }, { label: 'Remove it', secondary: true, onClick: () => { C.forget(); location.hash = ''; location.reload(); } }] });
}

// On a wide screen the same link works here with Windows Hello or Touch ID; the panel offers the phone as the easier place.
function sidePanel() {
  const el = $('#side'); if (!el) return; const link = location.origin + location.pathname;
  const qr = qrcode(0, 'M'); qr.addData(link); qr.make();
  el.innerHTML = `<h2>Also on your phone</h2><p>Scan this with your phone's camera to open the same app there. Here it works too: your computer's fingerprint, face or PIN is the key.</p><div class="qr">${qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true })}</div><p>${esc(link)}</p>`;
  el.hidden = !window.matchMedia('(min-width: 900px)').matches;
  try { window.matchMedia('(min-width: 900px)').addEventListener('change', (e) => { el.hidden = !e.matches; }); } catch {}
}
let renderSeq = 0; const stale = (my) => my !== renderSeq;
const routes = { home: renderHome, ask: renderAsk, borrow: renderBorrow, repay: renderRepay, send: renderSend, receive: renderReceive, back: renderBack, help: renderHelp, credit: renderCredit };
export function render() {
  if (!S.cred) return renderWelcome();
  const r = (location.hash || '#home').slice(1).split('?')[0]; window.scrollTo(0, 0); const my = ++renderSeq;
  Promise.resolve().then(() => (routes[r] || renderHome)(my)).catch((e) => { app.innerHTML = `<div class="note bad">${esc(friendly(e))}</div><pre>${esc(String(e.message || e).slice(0, 300))}</pre>`; });
}
async function boot() {
  S.cred = C.loadCred(); if (!S.cred) return;
  S.account = await C.openAccount(S.client, S.cred); S.addr = await S.account.getAddress(); S.bundler = C.bundlerFor(S.client, S.account);
}
(async () => {
  try {
    if ('serviceWorker' in navigator && (location.protocol === 'https:' || /^(localhost|127\.0\.0\.1)$/.test(location.hostname))) navigator.serviceWorker.register('sw.js').catch(() => {});
    await C.loadConfig(); S.client = C.makeClient(); await boot();
    window.addEventListener('hashchange', render); render(); sidePanel();
    I.onChange(() => document.querySelectorAll('[data-install]').forEach((el) => { el.hidden = !I.available(); }));
    window.__d7 = { S, C, I, now }; // test hook
    if (I.askedByLink()) { I.dropLinkFlag(); if (I.available()) installSheet(); }
  } catch (e) { app.innerHTML = `<h1>Cannot start</h1><div class="note bad">${esc(friendly(e))}</div><pre>${esc(String(e.message || e).slice(0, 400))}</pre>`; }
})();
