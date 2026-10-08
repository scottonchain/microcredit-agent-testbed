import json, urllib.request, hashlib, time
S = json.load(open('/root/work/run_r14/scope.json'))
URL = "https://base-rpc.publicnode.com"
n = 0
log = []
t0 = time.time()
def rpc(m, p):
    global n
    n += 1
    assert n <= 40, "budget"
    assert time.time() - t0 < 300
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "id": n, "method": m, "params": p}).encode(), headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        r = {"error": "transport: " + str(e)[:150]}
    log.append({"method": m, "params": p, "resp": r})
    return r
out = {"started": time.strftime('%FT%TZ', time.gmtime()), "rpc": URL}
cid = rpc("eth_chainId", [])
out["chainId"] = cid.get("result")
blk = rpc("eth_getBlockByNumber", ["latest", False])["result"]
bn = blk["number"]
out["block"] = {"number": int(bn, 16), "hash": blk["hash"], "timestamp": int(blk["timestamp"], 16)}
def call(to, data):
    r = rpc("eth_call", [{"to": to, "data": data}, bn])
    return r.get("result") if "result" in r else ("ERR:" + json.dumps(r.get("error"))[:120])
res = {}
for rd in S["staticReads"]:
    res[rd["signature"].split("(")[0].replace("function ", "") + "@" + rd["target"][:8]] = call(rd["target"], rd["data"])
out["static"] = res
def addr(x):
    return "0x" + x[-40:] if x and x.startswith("0x") and len(x) >= 66 else None
strat = "0xede4dd6758634007eb1f4cf8a203bf237a44ea4c"
code = rpc("eth_getCode", [strat, bn]).get("result", "")
out["strategy_code_len"] = (len(code) - 2) // 2
out["strategy_code_hex"] = code[:120]
out["strategy_codehash"] = hashlib.sha3_256(b"").hexdigest() and None
try:
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256); k.update(bytes.fromhex(code[2:])); out["strategy_codehash"] = "0x" + k.hexdigest()
except Exception:
    out["strategy_codehash"] = "keccak lib unavailable"
impl = None
if code.startswith("0x363d3d373d3d3d363d73") and len(code) == 2 + 45 * 2:
    impl = "0x" + code[22:62]
    out["eip1167_impl"] = impl
    ic = rpc("eth_getCode", [impl, bn]).get("result", "")
    out["impl_code_len"] = (len(ic) - 2) // 2
    try:
        k = keccak.new(digest_bits=256); k.update(bytes.fromhex(ic[2:])); out["impl_codehash"] = "0x" + k.hexdigest()
    except Exception:
        pass
out["gasPrice"] = rpc("eth_gasPrice", []).get("result")
fc = addr(res.get("beefyFeeConfig@0xede4dd")); g = addr(res.get("gauge@0xede4dd")); rp = addr(res.get("rewardPool@0xede4dd"))
out["feeconfig"], out["gauge"], out["rewardPool"] = fc, g, rp
dep = {}
for rd in S["dependentReads"]:
    name = rd["signature"].split("(")[0].replace("function ", "")
    if name == "getFees":
        tgt = fc
    else:
        tgt = g if g and int(g, 16) else (rp if rp and int(rp, 16) else None)
    if not tgt or not int(tgt, 16):
        dep[name] = "SKIPPED: no target"; continue
    dep[name] = call(tgt, rd["data"])
out["dependent"] = dep
out["rpc_count"] = n
out["finished"] = time.strftime('%FT%TZ', time.gmtime())
json.dump({"summary": out, "raw": log}, open('/root/work/run_r14/r14_raw.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
