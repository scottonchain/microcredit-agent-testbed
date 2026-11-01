import qrcode from 'qrcode-generator';
import * as C from './core.js';
import { friendly } from './errors.js';

const $ = (s) => document.querySelector(s);
const app = $('#app');
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const S = { client: null, cred: null, account: null, addr: null, bundler: null, snap: null };
const short = (a) => a.slice(0, 6) + '…' + a.slice(-4);
const days = (secs) => Math.max(0, Math.ceil(secs / 86400));
let chainNow = null; // block time, so the screens agree with the pool even when the phone clock is wrong
const now = () => chainNow ?? Math.floor(Date.now() / 1000);
const dueLine = (l) => { const d = l.dueAt - now(); if (d >= 0) return `Due in ${days(d)} days (${new Date(l.dueAt * 1000).toLocaleDateString()}).`; const late = Math.max(1, Math.floor(-d / 86400)); return `Overdue by ${late} day${late === 1 ? '' : 's'}. Pay now. After 30 more days late the loan can be marked defaulted and anyone who backed you can lose their stake.`; };

function sheet({ title, body = '', actions = [] }) {
  $('#overlayTitle').textContent = title; $('#overlayBody').innerHTML = body;
  const box = $('#overlayActions'); box.innerHTML = '';
  actions.forEach((a) => { const b = document.createElement('button'); b.textContent = a.label; if (a.secondary) b.className = 'secondary'; b.onclick = a.onClick; box.appendChild(b); });
  $('#overlay').hidden = false;
}
const closeSheet = () => { $('#overlay').hidden = true; };
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
        sheet({ title: 'Done', body: `<div class="note ok">${esc(title)} went through.</div>${extra}<p class="muted"><a href="${C.cfg.explorer}/tx/${r.txHash}" target="_blank" rel="noopener">View on the block explorer</a></p>`, actions: [{ label: 'OK', onClick: () => { closeSheet(); render(); } }] });
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

// ---------- screens ----------
function header(title, back = true) { return `${back ? '<a class="back" href="#home">‹ Back</a>' : ''}<h1>${esc(title)}</h1>`; }

function renderWelcome() {
  app.innerHTML = `${header('Omnequa test wallet', false)}
  <p>A practice wallet for small test loans. It opens with your fingerprint, face or screen lock. No password, no seed words, no fees to pay.</p>
  <div class="card"><button id="create">Create my wallet</button><p class="muted">Your phone will ask you to create a passkey. It stays on your device and, if you use one, your password manager.</p></div>
  <details class="card"><summary>I already have a recovery code</summary><label for="rc">Recovery code</label><textarea id="rc" rows="3" autocapitalize="off" autocorrect="off" spellcheck="false"></textarea><button id="import" class="secondary" style="margin-top:8px">Restore wallet</button></details>
  <p class="muted">Test network only. The dollars are test tokens with no real value.</p>`;
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

async function renderHome() {
  app.innerHTML = `<h1>Your wallet</h1><div class="card"><div class="muted">Loading…</div></div>`;
  let s; try { s = await refresh(); } catch (e) { app.innerHTML = `<h1>Your wallet</h1><div class="note bad">${esc(friendly(e))}</div><button id="retry">Try again</button>`; $('#retry').onclick = renderHome; return; }
  const loans = C.openLoans(s); const active = loans.find((l) => l.status === C.ST.Active); const waiting = loans.find((l) => l.status === C.ST.Requested);
  const apr = Number(s.rate) / 100;
  app.innerHTML = `<h1>Your wallet</h1>
  <div class="card"><div class="muted">Test USDC in your wallet</div><div class="big" id="bal">${C.money(s.usdcBal)}</div>
    <div class="row" style="margin-top:8px"><span class="muted">${short(S.addr)}</span><button class="link" id="copyAddr">Copy address</button></div></div>
  <div class="card"><div class="muted">${active || waiting ? 'Your credit limit' : 'You can borrow up to'}</div><div class="big" id="avail">${C.money(active || waiting ? s.limit : s.available)}</div>
    <p class="muted">${s.limit === 0n ? 'You have no credit yet. <a href="#credit">How to get credit</a>' : active || waiting ? `You can borrow again after you pay this loan back. Interest is ${apr.toFixed(2)}% a year.` : `Your credit limit is ${C.money(s.limit)}. Interest is ${apr.toFixed(2)}% a year.`}</p></div>
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
  if (waiting) {
    $('#finish').onclick = () => run('Finish loan', [C.poolCall('disburseLoan', [waiting.id])]);
    $('#cancelReq').onclick = () => run('Cancel request', [C.poolCall('cancelLoan', [waiting.id])]);
  }
}

async function renderBorrow() {
  const s = S.snap || (await refresh()); const apr = Number(s.rate) / 100;
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

async function renderRepay() {
  const s = S.snap || (await refresh()); const l = s.loans.find((x) => x.status === C.ST.Active);
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
    const cur = await C.preflight(S.client, S.addr, 'repayLoan', [l.id, amount]);
    const allowance = await S.client.readContract({ address: C.cfg.usdc, abi: C.erc20Abi, functionName: 'allowance', args: [S.addr, C.cfg.pool] });
    const calls = []; if (allowance < approveAmt) calls.push(C.usdcCall('approve', [C.cfg.pool, approveAmt]));
    calls.push(C.poolCall('repayLoan', [l.id, amount]));
    const r = await run('Pay back', calls);
    if (r?.success) { const s2 = await refresh(); const l2 = s2.loans.find((x) => x.id === l.id); if (l2 && l2.status === C.ST.Repaid) { /* done sheet already shown */ } }
    return cur;
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

function renderCredit() {
  const msg = `@HermesCRBot please issue a test credit line to ${S.addr}`;
  app.innerHTML = `${header('Get credit')}
  <div class="card"><h2>How credit works here</h2><p>You can borrow only against credit that exists. Nobody can make it up. Credit comes from two places:</p>
  <ul><li><b>A friend backs you.</b> They lock some of their own test USDC as a guarantee for you. Your limit goes up by what they lock.</li><li><b>A test credit line.</b> The test operator can grant a line for the experiment.</li></ul></div>
  <div class="card"><h2>Ask a friend to back you</h2><p>Send them your address. In their app they open <b>Back a friend</b> and enter it.</p><div class="addr">${esc(S.addr)}</div><button class="secondary" id="cp" style="margin-top:8px">Copy address</button></div>
  <div class="card"><h2>Request a test credit line</h2><p>Post this message as a comment on the test thread. The test operator replies and grants a line.</p><div class="addr">${esc(msg)}</div><div class="grid"><button id="cpm" class="secondary">Copy message</button><a class="btn" href="${C.cfg.creditRequestIssue}" target="_blank" rel="noopener">Open the thread</a></div></div>`;
  $('#cp').onclick = (e) => copy(S.addr, e.target); $('#cpm').onclick = (e) => copy(msg, e.target);
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
  <div class="card"><h2>How it works</h2><ol><li>You get test USDC from a faucet.</li><li>A friend backs you, or the test operator grants a line.</li><li>You borrow up to your limit. You get the money at once.</li><li>You pay it back with a little interest. Paying back builds your history.</li></ol></div>
  <div class="card"><h2>Your recovery code</h2><p class="muted">Save this somewhere private. With it you can reopen this wallet on a new phone if your passkey syncs.</p><div class="addr" style="max-height:90px;overflow:auto">${esc(code)}</div><button id="cp" class="secondary" style="margin-top:8px">Copy recovery code</button></div>
  <div class="card"><h2>Send feedback</h2><p>Tell us what confused you. Include what you tapped and what you saw. Never include real personal information.</p><button class="secondary" id="reset">Remove this wallet from this phone</button></div>
  <p class="muted">Wallet address: ${esc(S.addr)}</p>`;
  $('#cp').onclick = (e) => copy(code, e.target);
  $('#reset').onclick = () => sheet({ title: 'Remove wallet from this phone?', body: '<p>Make sure you saved your recovery code. Nothing on the network is deleted.</p>', actions: [{ label: 'Remove', onClick: () => { C.forget(); location.hash = ''; location.reload(); } }, { label: 'Keep it', secondary: true, onClick: closeSheet }] });
}

const routes = { home: renderHome, borrow: renderBorrow, repay: renderRepay, send: renderSend, receive: renderReceive, back: renderBack, help: renderHelp, credit: renderCredit };
export function render() {
  if (!S.cred) return renderWelcome();
  const r = (location.hash || '#home').slice(1).split('?')[0]; window.scrollTo(0, 0);
  Promise.resolve().then(() => (routes[r] || renderHome)()).catch((e) => { app.innerHTML = `<div class="note bad">${esc(friendly(e))}</div><pre>${esc(String(e.message || e).slice(0, 300))}</pre>`; });
}
async function boot() {
  S.cred = C.loadCred(); if (!S.cred) return;
  S.account = await C.openAccount(S.client, S.cred); S.addr = await S.account.getAddress(); S.bundler = C.bundlerFor(S.client, S.account);
}
(async () => {
  try {
    await C.loadConfig(); S.client = C.makeClient(); await boot();
    window.addEventListener('hashchange', render); render();
    window.__d7 = { S, C }; // test hook
    if ('serviceWorker' in navigator && /^(localhost|127\.0\.0\.1)$|^https:/.test(location.hostname) || location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(() => {});
  } catch (e) { app.innerHTML = `<h1>Cannot start</h1><div class="note bad">${esc(friendly(e))}</div><pre>${esc(String(e.message || e).slice(0, 400))}</pre>`; }
})();
