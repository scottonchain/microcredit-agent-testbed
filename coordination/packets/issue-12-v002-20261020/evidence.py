#!/usr/bin/env python3
"""Offline evidence for the v002 invocation packet. Usage: evidence.py CHECKOUT BASELINE CANDIDATE VERIFY_CMD_JSON.
Reads files and runs only the verify argv and read-only git/python on them. No network, no writes outside a temp dir."""
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path

checkout, baseline, candidate, verify_json = sys.argv[1:5]
sys.path.insert(0, str(Path(checkout) / 'coordination'))
import issue12_archive_index as ai
import issue12_oda_archive as oda

old = Path(baseline).read_bytes()
new = Path(candidate).read_bytes()
argv = json.loads(Path(verify_json).read_text())
out = {}


def run_verify(argv_, o, n):
    with tempfile.TemporaryDirectory() as d:
        po, pn = Path(d) / 'old', Path(d) / 'new'
        po.write_bytes(o)
        pn.write_bytes(n)
        a = [p.replace('{old}', str(po)).replace('{new}', str(pn)) for p in argv_]
        return subprocess.run(a, capture_output=True, text=True, cwd=checkout).returncode


# 1. the exact verify argv on the reviewed pair, and on pairs it must refuse
out['verify_exact'] = {
    'baseline_to_candidate': run_verify(argv, old, new),
    'baseline_to_baseline': run_verify(argv, old, old),
    'candidate_as_old': run_verify(argv, new, new),
    'candidate_to_baseline': run_verify(argv, new, old),
}

# 2. semantic core of the same argv (hash pins removed) against mutated candidates
core = list(argv)
core[2] = '\n'.join(l for l in argv[2].split('\n') if 'sha256sum "$old"' not in l and 'sha256sum "$new"' not in l)
if argv[:2] != ['bash', '-c'] or core[2] == argv[2] or 'sha256sum' in core[2]:
    raise SystemExit('the hash pins were not removed from the semantic core')
text = new.decode('utf-8')
_, state, _ = ai.split_body(text)
mut = {}
mut['core_unmutated'] = new
other = [k for k in state if k != 'operator_directed_actions'][-1]
mut['other_key_renamed'] = text.replace('"' + other + '":', '"' + other + 'x":', 1).encode()
mut['other_value_changed'] = text.replace(ai.compact(state[other]), ai.compact(state[other]) + ' ', 1).encode() if not isinstance(state[other], str) else text.replace(ai.compact(state[other]), '"X' + state[other] + '"', 1).encode()
inline = [k for k, v in state['operator_directed_actions'].items() if k != '_archive' and not oda.is_stub(v)]
first_inline = inline[0]
mut['inline_entry_changed'] = text.replace('"' + first_inline + '":{', '"' + first_inline + '":{"zz":1,', 1).encode()
stubbed = [k for k, v in state['operator_directed_actions'].items() if k != '_archive' and oda.is_stub(v)]
mut['stub_status_changed'] = text.replace('"' + stubbed[2] + '":{"archived":true', '"' + stubbed[2] + '":{"archived":true,"status":"X"', 1).encode()
mut['stub_archived_false'] = text.replace('"' + stubbed[0] + '":{"archived":true', '"' + stubbed[0] + '":{"archived":false', 1).encode()
mut['pointer_index_sha_changed'] = text.replace('5f9f26a3f723a2b3', '5f9f26a3f723a2b4', 1).encode()
mut['pointer_commit_changed'] = text.replace('"index_commit":"b3dbe424', '"index_commit":"b3dbe425', 1).encode()
mut['whitespace_after_colon'] = text.replace('"_archive":', '"_archive": ', 1).encode()
mut['trailing_text_added'] = (text + ' ').encode()
res = {}
for name, body in mut.items():
    if body is None:
        res[name] = 'NOT_APPLICABLE'
        continue
    res[name] = {'changed': body != new, 'exit': run_verify(core, old, body)}
out['semantic_core_mutations'] = res

# 3. independent field-level comparison (does not use oda.resolve)
_, so, _ = ai.split_body(old.decode('utf-8'))
_, sn, _ = ai.split_body(text)
oo, on = so['operator_directed_actions'], sn['operator_directed_actions']
others_equal = {k: so[k] == sn[k] for k in so if k != 'operator_directed_actions'}
out['independent'] = {
    'top_level_keys_equal': list(so) == list(sn),
    'non_oda_keys': len(others_equal),
    'non_oda_all_equal_decoded': all(others_equal.values()),
    'non_oda_all_equal_compact': all(ai.compact(so[k]) == ai.compact(sn[k]) for k in others_equal),
    'oda_key_order_equal_after_pointer': [k for k in oo if k != '_archive'] == [k for k in on if k != '_archive'],
    'pointer_old': oo['_archive'], 'pointer_new': on['_archive'],
    'newly_stubbed': [k for k in on if k != '_archive' and oda.is_stub(on[k]) and not oda.is_stub(oo[k])],
    'already_stubbed_unchanged': all(on[k] == oo[k] for k in oo if k != '_archive' and oda.is_stub(oo[k])),
    'inline_entries_after': inline,
    'inline_entries_byte_identical': all(ai.compact(on[k]) == ai.compact(oo[k]) for k in inline),
}
# bytes outside the operator_directed_actions value are identical
marker = '"operator_directed_actions":'
bo, bn = old.decode('utf-8'), text
io, inn = bo.index(marker), bn.index(marker)


def span_end(s, start):
    i = s.index('{', start)
    depth, instr, esc = 0, False, False
    for j in range(i, len(s)):
        c = s[j]
        if instr:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return j + 1
    raise SystemExit('unbalanced')


eo, en = span_end(bo, io), span_end(bn, inn)
out['independent']['bytes_before_oda_equal'] = bo[:io] == bn[:inn]
out['independent']['bytes_after_oda_equal'] = bo[eo:] == bn[en:]
out['independent']['oda_span_chars'] = {'old': eo - io, 'new': en - inn}

# 4. sizes and hashes
out['sizes'] = {'baseline_chars': len(bo), 'candidate_chars': len(bn), 'limit': ai.LIMIT, 'headroom': ai.LIMIT - len(bn),
                'baseline_sha256': hashlib.sha256(old).hexdigest(), 'candidate_sha256': hashlib.sha256(new).hexdigest(),
                'verify_cmd_sha256': hashlib.sha256(Path(verify_json).read_bytes()).hexdigest()}
print(json.dumps(out, indent=2, sort_keys=True))
