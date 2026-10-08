import urllib.request, urllib.error, hashlib, json
host = 'sourcify' + '.dev'
addrs = ['0x13ad51a6664973ebd0749a7c84939d973f247921', '0x4f09bab2f0e15e2a078a227fe1537665f55b8360']
res = []
for a in addrs:
    url = 'https://%s/server/v2/contract/8453/%s?fields=all' % (host, a)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'hermes-agent-909'}), timeout=30)
        body = r.read(5_000_000); st = r.status
    except urllib.error.HTTPError as e:
        body = e.read(5_000_000); st = e.code
    except Exception as e:
        body = str(e).encode(); st = -1
    open('/root/work/run_r15/sourcify_%s.json' % a, 'wb').write(body)
    info = {'addr': a, 'url': url, 'http': st, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    try:
        j = json.loads(body)
        info['keys'] = list(j.keys())[:20]
        for k in ('match', 'creationMatch', 'runtimeMatch', 'chainId', 'verifiedAt'):
            if k in j: info[k] = j[k]
        if 'compilation' in j: info['compilation'] = {k: j['compilation'].get(k) for k in ('name', 'compiler', 'compilerVersion', 'fullyQualifiedName')}
        if 'message' in j or 'customCode' in j: info['err'] = {k: j.get(k) for k in ('customCode', 'message', 'errorId')}
    except Exception:
        info['text'] = body[:300].decode('utf8', 'replace')
    res.append(info)
print(json.dumps(res, indent=1))
