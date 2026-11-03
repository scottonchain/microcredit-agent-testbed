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
let chainNow = null; // block time, so the screens agree with the pool even when the phone clock is wrong
const now = () => chainNow ?? Math.floor(Date.now() / 1000);
const dueLine = (l) => { const d = l.dueAt - now(); if (d >= 0) return `Due in ${days(d)} days (${new Date(l.dueAt * 1000).toLocaleDateString()}).`; const late = Math.max(1, Math.floor(-d / 86400)); return `Overdue by ${late} day${late === 1 ? '' : 's'}. Pay now. After 30 more days late the loan can be marked defaulted and anyone who backed you can lose their stake.`; };

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
async function run(title, calls, { retryIds, summary } = {}) {
  const steps = ['Approve with your fingerprint, face or screen lock', 'Sending to the test network', 'Done'];
  const draw = (i, extra = '') => sheet({ title, body: `<ul class="steps">${steps.map((s, k) => `<li class="${k < i ? 'done' : k === i ? 'on' : ''}">${k < i ? '✓ ' : ''}${s}</li>`).join('')}</ul>${extra}` });
  draw(0);
  let attempt = 0, lastErr = null;
  for (;;) {
    try {
      const r = await C.send(S.bundler, S.account, calls, (st) => draw(st === 'sign' ? 0 : 1));
      if (r.success) {
        let extra = ''; try { extra = summary ? await summary(r) : ''; } catch {}
        sheet({ title: 'Done', body: `<div class="note ok">${esc(title)} went through.</div>${extra}<p class="muted"><a href="${C.cfg.explorer}/tx/${r.txHash}" target="_blank" rel="noopener">View on the block explorer</a></p>`, actions: [{ label: 'OK', onClick: () => { closeSheet(); if (!location.hash.startsWith('#credit')) render(); } }] });
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
const androidWhereLine = () => `<p>Android puts the new icon in your <b>Apps</b> list (swipe up from the Home screen; it is on the last page, or search <b>Omnequa</b>). To put it on the Home screen: hold the icon, then tap <b>Add to Home</b>. On Samsung phones, <b>Home screen settings</b> has a switch, <b>Add new apps to Home screen</b>, that does this for every new app.</p>`;
const inAppLine = () => `<p>Opened this inside another app (Messages, WhatsApp, Gmail)? First choose <b>Open in ${I.isIOS() ? 'Safari' : 'Chrome'}</b> (or <b>Open in browser</b>) from that app's menu, then tap Add to home screen again.</p>`;
function installContent(k, hasWallet) {
  const inApp = I.inAppView();
  if (k === 'prompt') return { body: '<p>Your browser will ask to install the Omnequa test wallet. It then opens from its own icon, without the browser bars. There is nothing to download from an app store.</p>', actions: [{ label: 'Install', onClick: doInstall }, { label: 'Not now', secondary: true, onClick: closeInstall }] };
  if (k === 'ios') return { body: `${inApp ? inAppLine() : ''}<ol class="howto"><li>Tap the <b>Share</b> button (the square with an arrow pointing up), usually at the bottom of the screen; on iPad it is at the top.</li><li>Scroll down and tap <b>Add to Home Screen</b>.</li><li>Tap <b>Add</b>.</li></ol><p>Then open the app from its new icon. If it is already there, just open it.</p>${walletNote(hasWallet)}${inApp ? '' : inAppLine()}`, actions: [{ label: 'OK', onClick: closeInstall }] };
  return { body: `${inApp ? inAppLine() : ''}<p>In your browser’s menu look for <b>Install app</b>, <b>Add to Home screen</b>, <b>Add page to</b> (Samsung Internet), <b>Add to phone</b> or <b>Add to Dock</b>, then open the app from its new icon.</p>${I.isAndroid() ? androidWhereLine() : ''}<p class="muted">If it is already installed, open it from your home screen or app list. If there is nothing like that in the menu, keep using it here in the browser: nothing is lost.</p>${walletNote(hasWallet)}${inApp ? '' : inAppLine()}`, actions: [{ label: 'OK', onClick: closeInstall }] };
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
function header(title, back = true) { return `${back ? '<a class="back" href="#home">‹ Back</a>' : ''}<h1>${esc(title)}</h1>`; }

function renderWelcome() {
  app.innerHTML = `${header('Omnequa test wallet', false)}
  <p>A practice wallet for small test loans. It opens with your fingerprint, face or screen lock. No password, no seed words, no fees to pay.</p>
  <div class="card">${I.appleWebKit() ? (I.standalone()
    ? '<div class="note warn"><b>Already made a wallet in a browser on this device?</b> Tapping Create my wallet here makes a second, separate wallet; the first one’s test dollars stay in the first wallet. Instead, in that browser open Help, copy the recovery code, then tap <b>I already have a recovery code</b> below and paste it.</div>'
    : '<p class="muted">Made a wallet in the home-screen app already? Restore it with its recovery code (below) instead of creating a new one: a new wallet here would be a separate wallet with its own test dollars.</p>') : ''}<button id="create">Create my wallet</button><p class="muted">Your phone will ask you to create a passkey. It stays on your device and, if you use one, your password manager.</p></div>
  <details class="card"><summary>I already have a recovery code</summary><label for="rc">Recovery code</label><textarea id="rc" rows="3" autocapitalize="off" autocorrect="off" spellcheck="false"></textarea><button id="import" class="secondary" style="margin-top:8px">Restore wallet</button></details>
  ${installCard()}
  <p class="muted">Test network only. The dollars are test tokens with no real value.</p>`;
  wireInstall();
  $('#create').onclick = async () => {
    sheet({ title: 'Creating your wallet', body: '<p>Approve the passkey prompt on your phone.</p>' });
    try { const cred = await C.createPasskey('Omnequa test wallet'); C.saveCred(cred); await boot(); closeSheet(); go('home'); render(); }
    catch (e) { sheet({ title: 'Could not create the wallet', body: `<div class="note bad">${esc(friendly(e))}</div><details><summary>Technical details</summary><pre>${esc(String(e.message || e).slice(0, 400))}</pre></details>`, actions: [{ label: 'Close', onClick: closeSheet }] }); }
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
  const apr = Number(s.rate) / 100;
  app.innerHTML = `<h1>Your wallet</h1>
  <div class="card"><div class="muted">Test USDC in your wallet</div><div class="big" id="bal">${C.money(s.usdcBal)}</div>
    <div class="row" style="margin-top:8px"><span class="muted">${short(S.addr)}</span><button class="link" id="copyAddr">Copy address</button></div></div>
  <div class="card"><div class="muted">${active || waiting ? 'Your credit limit' : 'You can borrow up to'}</div><div class="big" id="avail">${C.money(active || waiting ? s.limit : s.available)}</div>
    ${C.cfg.desk && !s.defaulted ? (s.limit === 0n ? '<button id="gCredit">Ask the credit desk</button>' : '<button class="secondary" id="gCredit">Credit desk</button>') : ''}<p class="muted">${s.limit === 0n ? (C.cfg.desk ? 'You have no credit yet. Ask the credit desk: an AI officer answers in the app.' : 'You have no credit yet. <a href="#credit">How to get credit</a>') : active || waiting ? `You can borrow again after you pay this loan back. Interest is ${apr.toFixed(2)}% a year.` : `Your credit limit is ${C.money(s.limit)}. Interest is ${apr.toFixed(2)}% a year.`}</p></div>
  ${s.backedBy.length || s.youBack.length ? `<div class="card"><h2>Backing</h2>${s.backedBy.length ? `<div class="muted">Backed by</div>${s.backedBy.map((b) => `<div class="row"><span class="addr" style="border:0;padding:2px 0">${esc(short(b.who))}</span><b>${C.money(b.amount)}</b></div>`).join('')}` : ''}${s.youBack.length ? `<div class="muted" style="margin-top:8px">You back</div>${s.youBack.map((b) => `<div class="row"><span class="addr" style="border:0;padding:2px 0">${esc(short(b.who))}</span><span><b>${C.money(b.amount)}</b> <a href="#back?to=${esc(b.who)}">Change</a></span></div>`).join('')}<p class="muted">What you back is locked as a guarantee until your friend repays.</p>` : ''}</div>` : ''}
  ${waiting ? `<div class="note warn">A loan of ${C.money(waiting.principal)} was requested but not paid out.<div class="grid"><button id="finish">Finish it</button><button class="secondary" id="cancelReq">Cancel it</button></div></div>` : ''}
  ${active ? `<div class="card"><div class="muted">You owe</div><div class="big" id="owed">${C.money(C.ceilCent(active.owed))}</div><p class="${active.dueAt < now() ? 'note bad' : 'muted'}">${dueLine(active)} Interest grows a little each day.</p><button id="payNow">Pay back</button></div>` : ''}
  ${s.defaulted ? '<div class="note bad">This wallet has a defaulted loan and cannot borrow again.</div>' : ''}
  <div class="grid"><button id="gBorrow" ${active || waiting || s.defaulted ? 'disabled' : ''}>Borrow</button><button class="secondary" id="gRepay" ${active ? '' : 'disabled'}>Pay back</button>
  <button class="secondary" id="gSend">Send</button><button class="secondary" id="gReceive">Receive / get test dollars</button>
  <button class="secondary" id="gBack">Back a friend</button><button class="secondary" id="gHelp">Help</button></div>
  <p class="muted">${s.deployed ? '' : 'Your wallet is created on the network the first time you use it. '}Network fees are paid for you during the test.</p>`;
  $('#copyAddr').onclick = (e) => copy(S.addr, e.target);
  $('#gBorrow').onclick = () => go('borrow'); $('#gRepay').onclick = () => go('repay'); $('#gSend').onclick = () => go('send'); $('#gReceive').onclick = () => go('receive'); $('#gBack').onclick = () => go('back'); $('#gHelp').onclick = () => go('help');
  if (active) $('#payNow').onclick = () => go('repay');
  if ($('#gCredit')) $('#gCredit').onclick = () => go('credit');
  if (waiting) {
    $('#finish').onclick = () => run('Finish loan', [C.poolCall('disburseLoan', [waiting.id])]);
    $('#cancelReq').onclick = () => run('Cancel request', [C.poolCall('cancelLoan', [waiting.id])]);
  }
}

async function renderBorrow(my = renderSeq) {
  let s; try { s = await refresh(); } catch { s = S.snap; if (!s) throw new Error('Cannot reach the test network'); } if (stale(my)) return; const apr = Number(s.rate) / 100;
  app.innerHTML = `${header('Borrow')}
  <div class="card"><div class="muted">Available to borrow</div><div class="big">${C.money(s.available)}</div></div>
  <label for="amt">How much?</label><input id="amt" inputmode="decimal" placeholder="e.g. 10" autocomplete="off">
  <div class="grid" style="grid-template-columns:repeat(3,1fr)"><button class="secondary" data-p="0.25">25%</button><button class="secondary" data-p="0.5">50%</button><button class="secondary" data-p="1">Max</button></div>
  <div id="terms" class="note ok" hidden></div><div id="warn"></div>
  <button id="go" disabled>Borrow</button>
  <p class="muted">Term: 30 days. Interest: ${apr.toFixed(2)}% a year, simple. You get the money right away and repay it all at once or in parts.</p>`;
  const amt = $('#amt'), terms = $('#terms'), go_ = $('#go');
  const upd = () => {
    const v = C.parseUsd(amt.value); go_.disabled = true; terms.hidden = true; $('#warn').innerHTML = '';
    if (v === null || v === 0n) return;
    if (v > s.available) { $('#warn').innerHTML = `<div class="note warn">${s.available === 0n ? esc(friendly({ reason: 'NoCredit' })) : 'That is more than you can borrow right now (' + C.money(s.available) + ').'}</div>`; return; }
    const interest = (v * s.rate * 30n) / (10000n * 365n);
    terms.hidden = false; terms.innerHTML = `You receive <b>${C.money(v)}</b> now. In 30 days you owe about <b>${C.money(C.ceilCent(v + interest))}</b> (interest about ${C.money(C.ceilCent(interest))}). You will need that interest in your wallet to repay: get it from the faucet if you do not have it.`;
    go_.disabled = false;
  };
  amt.oninput = upd;
  document.querySelectorAll('[data-p]').forEach((b) => (b.onclick = () => { const p = Number(b.dataset.p); const v = (s.available * BigInt(Math.round(p * 100))) / 100n; amt.value = (Number(v) / 1e6).toFixed(2).replace(/\.00$/, ''); upd(); }));
  go_.onclick = async () => {
    const v = C.parseUsd(amt.value); if (!v) return;
    go_.disabled = true; const err = await C.preflight(S.client, S.addr, 'requestLoan', [v]);
    if (err) { refuse(err); go_.disabled = false; return; }
    const build = async () => { const id = await C.nextLoanId(S.client); return [C.poolCall('requestLoan', [v]), C.poolCall('disburseLoan', [id])]; };
    await run('Borrow ' + C.money(v), await build(), { retryIds: build, summary: async () => { const s2 = await refresh(); const l = C.openLoans(s2).find((x) => x.status === C.ST.Active); return l ? `<p>You now owe about <b>${C.money(C.ceilCent(l.owed))}</b>. It is due on <b>${new Date(l.dueAt * 1000).toLocaleDateString()}</b>. Interest grows a little each day, so pay back a few days early and keep a few dollars of test USDC for the interest.</p>` : ''; } });
  };
}

async function renderRepay(my = renderSeq) {
  let s; try { s = await refresh(); } catch { s = S.snap; if (!s) throw new Error('Cannot reach the test network'); } if (stale(my)) return; const l = s.loans.find((x) => x.status === C.ST.Active);
  if (!l) { app.innerHTML = `${header('Pay back')}<div class="card"><p>You have no loan to pay back.</p></div>`; return; }
  const quote = C.ceilCent(l.owed), pay = quote + C.headroom(l.principal); const short_ = quote > s.usdcBal ? quote - s.usdcBal : 0n;
  app.innerHTML = `${header('Pay back')}
  <div class="card"><div class="muted">You owe right now</div><div class="big">${C.money(quote)}</div><p class="muted">Borrowed ${C.money(l.principal)}. ${dueLine(l)} Your wallet has ${C.money(s.usdcBal)}.</p></div>
  ${short_ > 0n ? `<div class="note warn">You are ${C.money(short_ + C.CENT)} short. The interest is not in your wallet yet. Get test USDC from the faucet, then come back.<div class="grid"><button id="faucet">Open the faucet</button><button class="secondary" id="copyA">Copy my address</button></div></div>` : ''}
  <button id="all" ${short_ > 0n ? 'disabled' : ''}>Pay back everything</button>
  <details class="card"><summary>Pay only part</summary><label for="part">Amount</label><input id="part" inputmode="decimal" placeholder="e.g. 5"><button id="partGo" class="secondary" style="margin-top:8px">Pay this part</button></details>
  <p class="muted">A small buffer is approved so the interest that builds up while this is sent is covered. Only what you owe is taken.</p>`;
  if (short_ > 0n) { $('#faucet').onclick = () => { copy(S.addr); window.open(C.cfg.faucet, '_blank', 'noopener'); }; $('#copyA').onclick = (e) => copy(S.addr, e.target); }
  const doPay = async (amount, approveAmt) => {
    const allowance = await S.client.readContract({ address: C.cfg.usdc, abi: C.erc20Abi, functionName: 'allowance', args: [S.addr, C.cfg.pool] });
    const calls = []; if (allowance < approveAmt) calls.push(C.usdcCall('approve', [C.cfg.pool, approveAmt]));
    calls.push(C.poolCall('repayLoan', [l.id, amount]));
    const before = { bal: s.usdcBal, dues: await S.client.readContract({ address: C.cfg.pool, abi: C.poolAbi, functionName: 'duesPaid', args: [S.addr] }), limit: s.limit };
    await run('Pay back', calls, { summary: async () => {
      const s2 = await refresh(); const l2 = s2.loans.find((x) => x.id === l.id); const paid = before.bal - s2.usdcBal; const interest = paid > l.principal ? paid - l.principal : (l2 && l2.status === C.ST.Repaid ? 0n : null);
      const dues = (await S.client.readContract({ address: C.cfg.pool, abi: C.poolAbi, functionName: 'duesPaid', args: [S.addr] })) - before.dues;
      if (l2 && l2.status === C.ST.Repaid) return `<p>Loan closed. You paid <b>${C.money(paid)}</b>: ${C.money(l.principal)} borrowed plus about ${C.money(paid - l.principal)} interest.${dues > 0n ? ` ${C.money(dues)} of that interest counts toward your own credit, so your limit is now <b>${C.money(s2.limit)}</b>.` : ''} You can borrow again right away.</p>`;
      return `<p>You paid <b>${C.money(paid)}</b>. Still owed: <b>${C.money(C.ceilCent(l2 ? l2.owed : 0n))}</b>. Interest is paid first, then the amount borrowed.</p>`; } });
  };
  $('#all').onclick = () => doPay(pay, pay);
  $('#partGo').onclick = () => { const v = C.parseUsd($('#part').value); if (!v) return; if (v > s.usdcBal) return refuse('InsufficientBalance'); doPay(v, v); };
}

function renderSend() {
  const s = S.snap;
  app.innerHTML = `${header('Send')}
  <div class="card muted">Available: ${C.money(s?.usdcBal ?? 0n)}</div>
  <label for="to">To (wallet address)</label><input id="to" placeholder="0x…" autocapitalize="off" autocorrect="off" spellcheck="false">
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
  app.innerHTML = `${header('Receive and get test dollars')}
  <div class="card"><div class="qr">${qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true })}</div><div class="addr" id="addrBox">${esc(S.addr)}</div><button id="cp" class="secondary" style="margin-top:8px">Copy address</button></div>
  <div class="card"><h2>Get test dollars (USDC)</h2><ol><li>Copy your address above.</li><li>Open the Circle faucet, choose <b>Base Sepolia</b> and <b>USDC</b>, paste your address, and request.</li><li>Come back here. Your balance updates in a minute.</li></ol>
  <p class="muted">You need a few test dollars to pay interest when you repay. The faucet gives a small amount every couple of hours.</p><button id="fc">Open the faucet</button></div>`;
  $('#cp').onclick = (e) => copy(S.addr, e.target); $('#fc').onclick = () => { copy(S.addr); window.open(C.cfg.faucet, '_blank', 'noopener'); };
}

let chatTimer = null;
function stopChat() { if (chatTimer) { clearInterval(chatTimer); chatTimer = null; } }
async function renderCredit(my = renderSeq) {
  stopChat();
  if (!C.cfg.desk) return renderCreditManual();
  const maxLine = C.cfg.maxLine || 5;
  app.innerHTML = `${header('Credit desk')}
  <div class="card"><p class="muted">An AI credit officer reads what you write and answers here, usually within a minute or two. Everything written here is public on the test network, so no personal details, please.</p>
  <div id="chat" class="chat"><div class="muted">Loading…</div></div><div id="typing" class="muted" hidden>The credit officer is reading your message…</div></div>
  <div class="card" id="askBox"><label for="msg" class="muted">Your message</label><textarea id="msg" rows="3" maxlength="1000" placeholder="What is it for, how much (up to $${maxLine}), and when will you pay it back?"></textarea>
  <div class="grid"><button id="send">Send to the desk</button><button class="secondary" id="toBorrow" hidden>Borrow</button></div><div id="warn"></div></div>
  <details class="card"><summary>Or ask a friend to back you</summary><p>Send them your address. In their app they open <b>Back a friend</b> and enter it. What they lock becomes your limit.</p><div class="addr">${esc(S.addr)}</div><button class="secondary" id="cp" style="margin-top:8px">Copy address</button></details>`;
  $('#cp').onclick = (e) => copy(S.addr, e.target); $('#toBorrow').onclick = () => go('borrow');
  const greeting = `Hello, I am the credit officer at the Omnequa credit desk, an AI agent. Tell me what you would use a small loan for, how much you need (up to $${maxLine} in this test), and when you would pay it back.`;
  let lastLen = -1, lastBacking = -1n;
  const draw = async () => {
    let d; try { d = await C.deskState(S.client, S.addr); } catch (e) { if (stale(my)) return; $('#chat').innerHTML = `<div class="note bad">${esc(friendly(e))}</div>`; return; }
    if (stale(my)) { stopChat(); return; }
    if (d.thread.length === lastLen && d.backing === lastBacking) return; lastLen = d.thread.length; lastBacking = d.backing;
    const bubbles = [{ from: 1, text: greeting }, ...d.thread].map((m) => `<div class="bub ${m.from === 0 ? 'me' : 'desk'}">${esc(m.text)}</div>`).join('');
    const granted = d.backing > 0n ? `<div class="note ok" id="granted">The desk backs you with <b>${C.money(d.backing)}</b>. Your limit on the home screen includes it.</div>` : '';
    $('#chat').innerHTML = bubbles + granted; $('#typing').hidden = d.unanswered === 0;
    $('#toBorrow').hidden = d.backing === 0n; $('#send').disabled = d.unanswered >= 3;
    $('#warn').innerHTML = d.unanswered >= 3 ? '<div class="note warn">Please wait for the officer to answer before writing again.</div>' : d.freeStake === 0n && d.backing === 0n ? '<div class="note warn">The desk has no free stake right now, so it cannot grant new lines until some is added.</div>' : '';
  };
  await draw(); chatTimer = setInterval(() => { if (location.hash.startsWith('#credit')) draw(); else stopChat(); }, 4000);
  $('#send').onclick = async () => {
    const text = $('#msg').value.trim(); if (!text) return; if (text.length > 1000) { $('#warn').innerHTML = '<div class="note warn">Please keep it under 1000 characters.</div>'; return; }
    const r = await run('Send to the credit desk', [C.deskCall('say', [text])]); if (r && r.success) { $('#msg').value = ''; }
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

function renderHelp() {
  const code = C.recoveryCode(S.cred);
  app.innerHTML = `${header('Help')}
  <div class="card"><h2>How it works</h2><ol><li>You get test USDC from a faucet.</li><li>The credit desk (an AI credit officer, in the app) backs you with a small line, or a friend backs you.</li><li>You borrow up to your limit. You get the money at once.</li><li>You pay it back with a little interest. Paying back builds your history.</li></ol></div>
  <div class="card"><h2>Your recovery code</h2><p class="muted">Save this somewhere private. With it you can reopen this wallet on a new phone if your passkey syncs.</p><div class="addr" style="max-height:90px;overflow:auto">${esc(code)}</div><button id="cp" class="secondary" style="margin-top:8px">Copy recovery code</button></div>
  ${installCard()}
  <div class="card"><h2>Send feedback</h2><p>Tell us what confused you. Include what you tapped and what you saw. Never include real personal information.</p><button class="secondary" id="reset">Remove this wallet from this phone</button></div>
  <p class="muted">Wallet address: ${esc(S.addr)}</p>`;
  wireInstall();
  $('#cp').onclick = (e) => copy(code, e.target);
  $('#reset').onclick = () => sheet({ title: 'Remove wallet from this phone?', body: '<p>Make sure you saved your recovery code. Nothing on the network is deleted.</p>', actions: [{ label: 'Remove', onClick: () => { C.forget(); location.hash = ''; location.reload(); } }, { label: 'Keep it', secondary: true, onClick: closeSheet }] });
}

let renderSeq = 0; const stale = (my) => my !== renderSeq;
const routes = { home: renderHome, borrow: renderBorrow, repay: renderRepay, send: renderSend, receive: renderReceive, back: renderBack, help: renderHelp, credit: renderCredit };
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
    window.addEventListener('hashchange', render); render();
    I.onChange(() => document.querySelectorAll('[data-install]').forEach((el) => { el.hidden = !I.available(); }));
    window.__d7 = { S, C, I }; // test hook
    if (I.askedByLink()) { I.dropLinkFlag(); if (I.available()) installSheet(); }
  } catch (e) { app.innerHTML = `<h1>Cannot start</h1><div class="note bad">${esc(friendly(e))}</div><pre>${esc(String(e.message || e).slice(0, 400))}</pre>`; }
})();
