// The persona's only tool: node p.mjs <port> <command> [words...]. Prints what a person would see.
const [port, cmd, ...args] = process.argv.slice(2);
if (!port || !cmd) { console.log('usage: node p.mjs <port> look | tap <words> | type <box> <text> | press <key> | back | reload | home | wait <s> | scroll [up] | days <n> | tabs | switch <n> | closetab | shot | done'); process.exit(1); }
const r = await fetch(`http://127.0.0.1:${port}/`, { method: 'POST', body: JSON.stringify({ cmd, args }) }).then((x) => x.json()).catch((e) => ({ error: 'the phone is not answering: ' + e.message }));
if (r.error) { console.log('PROBLEM: ' + r.error); process.exit(0); }
if (r.bye) { console.log('Phone closed.'); process.exit(0); }
if (r.tabs) { console.log(r.tabs.map((t) => `${t.current ? '>' : ' '} tab ${t.n}: ${t.url}`).join('\n')); process.exit(0); }
if (r.logs) { console.log(r.logs.join('\n') || '(no messages)'); process.exit(0); }
if (r.shot && !r.screen && !r.dialog) { console.log('screenshot: ' + r.shot); process.exit(0); }
const lines = [];
lines.push(`[tab ${r.tab}] ${r.title || ''}  ${r.url || ''}`);
if (r.note) lines.push('NOTE: ' + r.note);
if (r.today) lines.push('(today, by this phone\'s calendar: ' + r.today + ')');
if (r.banner) lines.push('(banner at the top) ' + r.banner.trim());
if (r.dialog) { lines.push('--- A BOX IS OPEN ON TOP OF THE SCREEN ---'); lines.push(r.dialog.trim()); lines.push('--- behind it, the screen shows ---'); }
else lines.push('--- SCREEN ---');
lines.push((r.screen || '').trim() || '(blank)');
if (r.pageHeight > r.viewportHeight + 40) lines.push(`(the page continues below; you are ${Math.round(100 * Math.min(1, (r.scrollY + r.viewportHeight) / r.pageHeight))}% of the way down; "scroll" to see more)`);
lines.push('--- THINGS YOU CAN TAP OR TYPE IN ---');
for (const c of r.controls || []) { const extra = [c.disabled ? 'greyed out' : '', c.kind === 'field' ? `currently: "${c.value}"` : '', c.open === true ? 'open' : c.open === false ? 'closed' : '', c.opensNewTab ? 'opens a new tab' : ''].filter(Boolean).join(', '); lines.push(`  [${c.kind}] ${c.name}${extra ? '  (' + extra + ')' : ''}`); }
if (!(r.controls || []).length) lines.push('  (nothing)');
lines.push('--- screenshot: ' + r.shot);
console.log(lines.join('\n'));
