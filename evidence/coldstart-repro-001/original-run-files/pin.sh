export PATH=/root/work/anvil_alpine:$PATH
cd /root/work/run_fork
R=https://sepolia.base.org
P=0x73872B8fB7F1771C67911f03edc75aBdc9514973
USDC=0x036CbD53842c5426634e7929541eC2318f3dCF7e
PROV=0x554c6bB61eDF0CAfB90ff31813540369Cb0105e4
BN=$(cast block-number --rpc-url $R)
BN=$((BN-3))
echo BN $BN
python3 - <<EOF
import json,subprocess,hashlib
R="$R"; BN=$BN
def cast(*a):
    return subprocess.check_output(["cast",*a],text=True).strip()
blk=json.loads(cast("rpc","eth_getBlockByNumber",hex(BN),"false","--rpc-url",R))
out={"source_chain_id":84532,"fork_block_number":BN,"fork_block_hash":blk["hash"],"block_timestamp":int(blk["timestamp"],16),"contracts":{}}
for n,a in [("DecentralizedMicrocredit","$P"),("OracleScoreProvider","$PROV"),("USDC","$USDC")]:
    code=cast("code",a,"--block",str(BN),"--rpc-url",R)
    b=bytes.fromhex(code[2:])
    out["contracts"][n]={"address":a.lower(),"sha256":hashlib.sha256(b).hexdigest(),"keccak256":cast("keccak",code),"code_bytes":len(b)}
json.dump(out,open("source-code-hashes.json","w"),indent=2)
print(json.dumps(out,indent=2))
EOF
