import json, urllib.request, urllib.error, hashlib, datetime, os
out = '/root/work/bootstrap-evidence'
os.makedirs(out, exist_ok=True)
log = []
def now(): return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def fetch(name, url, method='GET', body=None, headers=None):
    h = {'User-Agent': 'hermes-agent-909 research (AI agent)', 'Accept': '*/*'}
    if headers: h.update(headers)
    data = json.dumps(body).encode() if body is not None else None
    if data: h['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    t = now()
    try:
        r = urllib.request.urlopen(req, timeout=30)
        status, rh, raw = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        status, rh, raw = e.code, dict(e.headers), e.read()
    except Exception as e:
        status, rh, raw = None, {}, repr(e).encode()
    sha = hashlib.sha256(raw).hexdigest()
    open(f'{out}/{name}', 'wb').write(raw)
    safe = {k: v for k, v in rh.items() if k.lower() not in ('set-cookie', 'cookie')}
    entry = dict(name=name, url=url, method=method, request_body=body, read_utc=t, status=status, bytes=len(raw), sha256=sha, response_headers=safe)
    log.append(entry)
    print(name, status, len(raw), sha[:16])
    return status, rh, raw

fetch('bazaar_first100.json', 'https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?type=http&limit=100')
fetch('cdp_facilitator.html', 'https://docs.cdp.coinbase.com/x402/seller/facilitator')
fetch('acp_overview.html', 'https://os.virtuals.io/acp/overview')
fetch('acp_whitepaper.html', 'https://whitepaper.virtuals.io/about-virtuals/commerce-layer/technical-deep-dive')
fetch('acp_client_workflow.html', 'https://os.virtuals.io/acp/cli/client-workflow')
# unpaid probes of exa search (no payment header)
fetch('exa_unpaid_get.txt', 'https://stableenrich.dev/api/exa/search')
fetch('exa_unpaid_post.txt', 'https://stableenrich.dev/api/exa/search', 'POST', {"query": "microcredit", "numResults": 1})
json.dump(log, open(f'{out}/manifest.json', 'w'), indent=1)
