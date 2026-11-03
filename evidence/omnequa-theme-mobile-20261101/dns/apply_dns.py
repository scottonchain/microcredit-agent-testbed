"""Move omnequa.org from the OpenAI Sites host to GitHub Pages at GoDaddy.

Run from a session whose network proxy injects the GoDaddy personal access
token for api.godaddy.com (the Authorization header below is a placeholder the
proxy replaces). Writes zone-current.json must exist beside this script from a
prior read; the script re-reads the zone, refuses to start if it differs, and
re-reads again before every write. Receipts go to write-results.json and the
final zone to zone-after.json. Credentials are never written.
"""
import datetime
import json
import pathlib
import subprocess
import sys
import urllib.parse

ZONE = 'https://api.godaddy.com/v3/domains/zones/omnequa.org/dns-records'
H = ['-H', 'Authorization: Bearer placeholder', '-H', 'Accept: application/json',
     '-H', 'Content-Type: application/json']
HERE = pathlib.Path(__file__).resolve().parent
TOUCHED = {('A', '@'), ('CNAME', 'www'), ('TXT', '_openai-site-verification'),
           ('TXT', '_cf-custom-hostname'), ('TXT', '_openai-site-verification.www'),
           ('TXT', '_cf-custom-hostname.www')}


def call(method, url, body=None):
    cmd = ['curl', '-sS', '-m', '40', '-X', method, '-o', '/dev/stdout', '-w', '\n%{http_code}', *H, url]
    if body is not None:
        cmd += ['--data', json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    txt, code = out.rsplit('\n', 1)
    try:
        res = json.loads(txt) if txt.strip() else None
    except ValueError:
        res = txt[:300]
    return int(code), res


def read():
    code, res = call('GET', ZONE + '?limit=100')
    assert code == 200, (code, res)
    assert all(l['rel'] != 'next' for l in res['links']), 'pagination needed'
    return res['items']


def key(r):
    return (r['type'], r['name'], str(r.get('data')).rstrip('.'))


def frozen(items):
    return {json.dumps(r, sort_keys=True) for r in items if (r['type'], r['name']) not in TOUCHED}


baseline = json.load(open(HERE / 'zone-current.json'))
cur = read()
assert {key(r) for r in cur} == {key(r) for r in baseline} and len(cur) == len(baseline), 'zone changed since the recorded read'
untouched = frozen(cur)
print('zone matches recorded read:', len(cur), 'records;', len(untouched), 'untouched records guarded')
log = []


def find(items, t, n, d):
    m = [r for r in items if r['type'] == t and r['name'] == n and str(r.get('data')).rstrip('.') == d.rstrip('.')]
    assert len(m) == 1, (t, n, d, len(m))
    return m[0]


def step(desc, method, lookup, body=None):
    items = read()
    assert frozen(items) == untouched, 'an untouched record changed, stopping'
    url = ZONE
    if lookup:
        url = ZONE + '/' + urllib.parse.quote(find(items, *lookup)['recordId'], safe='')
    code, res = call(method, url, body)
    log.append({'time': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'step': desc,
                'method': method, 'url': url, 'record': body, 'status': code, 'result': res})
    (HERE / 'write-results.json').write_text(json.dumps(log, indent=1) + '\n')
    print(f'{desc}: HTTP {code}', json.dumps(res)[:120] if res else '')
    if code not in (200, 201, 204):
        print('STOP: non-2xx response')
        sys.exit(1)


step('apex A 1 -> 185.199.108.153', 'PUT', ('A', '@', '162.159.143.30'),
     {'type': 'A', 'name': '@', 'data': '185.199.108.153', 'ttl': 3600})
step('apex A 2 -> 185.199.109.153', 'PUT', ('A', '@', '172.66.3.26'),
     {'type': 'A', 'name': '@', 'data': '185.199.109.153', 'ttl': 3600})
step('apex A add 185.199.110.153', 'POST', None, {'type': 'A', 'name': '@', 'data': '185.199.110.153', 'ttl': 3600})
step('apex A add 185.199.111.153', 'POST', None, {'type': 'A', 'name': '@', 'data': '185.199.111.153', 'ttl': 3600})
step('www CNAME -> scottonchain.github.io', 'PUT', ('CNAME', 'www', 'custom-domains.chatgpt.site'),
     {'type': 'CNAME', 'name': 'www', 'data': 'scottonchain.github.io.', 'ttl': 3600})
for name in ['_openai-site-verification', '_cf-custom-hostname',
             '_openai-site-verification.www', '_cf-custom-hostname.www']:
    items = read()
    m = [r for r in items if r['type'] == 'TXT' and r['name'] == name]
    assert len(m) == 1, (name, len(m))
    step(f'delete TXT {name}', 'DELETE', ('TXT', name, m[0]['data']))

final = read()
(HERE / 'zone-after.json').write_text(json.dumps(final, indent=1) + '\n')
print('\nfinal zone:', len(final), 'records; untouched identical:', frozen(final) == untouched)
for r in sorted(final, key=lambda r: (r['type'], r['name'])):
    if (r['type'], r['name']) in TOUCHED:
        print(f" {r['type']:6} {r['name']:8} {r['data']}")
