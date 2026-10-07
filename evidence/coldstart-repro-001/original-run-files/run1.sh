export PATH=/root/work/anvil_alpine:$PATH
cd /root/work/run_fork
TB=/root/work/run_fork/tb_1791408601/scenarios/cold-start-three-communities
R=https://sepolia.base.org
BN=47820167
USDC=0x036CbD53842c5426634e7929541eC2318f3dCF7e
P=0x73872B8fB7F1771C67911f03edc75aBdc9514973
python3 - <<'EOF'
import json
d=json.load(open("/root/work/run_fork/tb_1791408601/scenarios/cold-start-three-communities/public-wallets.json"))
print(json.dumps(d,indent=1)[:2500])
EOF
python3 $TB/run.py --self-test 2>&1 | tail -5
echo "--- roots at block"
python3 - <<'EOF'
import json,subprocess
d=json.load(open("/root/work/run_fork/tb_1791408601/scenarios/cold-start-three-communities/public-wallets.json"))
def walk(o,p=""):
    if isinstance(o,dict):
        for k,v in o.items(): yield from walk(v,p+"/"+k)
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from walk(v,p+"/%d"%i)
    elif isinstance(o,str) and o.startswith("0x") and len(o)==42: yield p,o
BN="47820167"; R="https://sepolia.base.org"; U="0x036CbD53842c5426634e7929541eC2318f3dCF7e"
def c(*a): return subprocess.check_output(["cast",*a,"--rpc-url",R],text=True).strip()
out=[]
for p,a in walk(d):
    bal=c("call",U,"balanceOf(address)(uint256)",a,"--block",BN).split()[0]
    n=c("nonce",a,"--block",BN)
    eth=c("balance",a,"--block",BN)
    out.append({"path":p,"addr":a,"usdc_raw":bal,"nonce":n,"eth_wei":eth})
    print(p,a,bal,n,eth)
json.dump(out,open("/root/work/run_fork/roots_at_block.json","w"),indent=1)
EOF
