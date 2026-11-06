"""Canonical inventory acquisition and conservative installed reconciliation probes.
No caller-supplied completeness flag or release authority. Full state equality is
intentional: new activity requires a new independently reconciled private baseline.
Trusted runtime attestations are not a distributed lock or cryptographic proof.
"""
import hashlib
import json
from durable import address, txhash, units
from canonical_adapter import words, quantity

S={'budget':'37295b41','pool':'16f0115b','totalCap':'16450092','controllerCap':'f6818471',
   'groupCap':'bd6e3c4a','totalUsed':'b2e2c75f','stopped':'75f12b21','grants':'b869cea3',
   'revoked':'fa01dc06','controllerUsed':'02cef3f8','groupUsed':'3a24c9ee',
   'ids':'5c1bf865','loan':'504006ca','terms':'0634612f','backed':'d388fb6e','backings':'f198f8b9',
   'lent':'227a09c4','reserved':'9f308512','lenderCash':'6e21ccab','firstLossReserve':'2a544a84',
   'totalImpaired':'77c15895','protocolFees':'1ad8b03b','totalStaked':'817b1cd2','totalUnclaimedPayouts':'126dd6ef','balance':'70a08231'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def abi_address(word):
    if word[:24]!='0'*24:raise ValueError('noncanonical ABI address')
    return address('0x'+word[24:])


def array(raw,width,limit):
    if not isinstance(raw,str) or not raw.startswith('0x') or (len(raw)-2)%64:raise ValueError('array encoding')
    w=words(raw,(len(raw)-2)//64)
    if len(w)<2 or int(w[0],16)!=32:raise ValueError('array offset')
    n=int(w[1],16)
    if n>limit or len(w)!=2+n*width:raise ValueError('bounded complete array required')
    return [w[2+i*width:2+(i+1)*width] for i in range(n)]


class CanonicalInventory:
    def __init__(self,provider,budget,borrowers,*,limit=512):
        self.p=provider;self.budget=address(budget)
        self.borrowers=sorted(address(x) for x in borrowers)
        if len(set(self.borrowers))!=len(self.borrowers) or len(self.borrowers)>limit:raise ValueError('unique bounded registry')
        if self.budget not in provider.pins:raise ValueError('budget code pin required')
        if type(limit)is not int or not 1<=limit<=4096:raise ValueError('inventory limit')
        self.limit=limit
    def snapshot(self):
        p=self.p;n=p.head()-p.policy.confirmations+1
        if n<0:raise ValueError('no confirmed state')
        block=p._call('eth_getBlockByNumber',[hex(n),False]);h=txhash(block['hash'])
        if quantity(block['number'])!=n:raise ValueError('block mismatch')
        p._pins(h);anchor={'blockHash':h,'requireCanonical':True};pool=address(p.policy.pool)
        def call(to,name,*args):
            return p._call('eth_call',[{'to':to,'data':'0x'+S[name]+''.join(x.removeprefix('0x').zfill(64) for x in args)},anchor])
        def uint(to,name,*args):return int(words(call(to,name,*args),1)[0],16)
        if abi_address(words(call(pool,'budget'),1)[0])!=self.budget or abi_address(words(call(self.budget,'pool'),1)[0])!=pool:
            raise ValueError('budget wiring')
        budget={k:uint(self.budget,k) for k in ('totalCap','controllerCap','groupCap','totalUsed','stopped')}
        if budget['stopped'] not in (0,1) or budget['totalUsed']>budget['totalCap']:raise ValueError('budget state')
        ids=[int(x[0],16) for x in array(call(pool,'ids'),1,self.limit)]
        # Canonical source appends sequential IDs forever, including cancellations.
        if ids!=list(range(1,len(ids)+1)):raise ValueError('incomplete canonical loan enumeration')
        loans={};gross=0
        for i in ids:
            w=words(call(pool,'loan',hex(i)),5);who=abi_address(w[2]);principal=int(w[0],16)
            if who not in self.borrowers or principal<=0 or int(w[4],16) not in (0,1):raise ValueError('untracked loan')
            terms=[int(x,16) for x in words(call(pool,'terms',hex(i)),5)]
            if terms[0] not in (1,2,3,4,5) or bool(int(w[4],16))!=(terms[0] in (1,2)):raise ValueError('loan lifecycle mismatch')
            loans[str(i)]={'terms':terms,'borrower':who,'principal':principal,'outstanding':int(w[1],16),'rate':int(w[3],16),'open':int(w[4],16)}
            gross+=principal
        if gross!=budget['totalUsed']:raise ValueError('origination history/budget mismatch')
        backed=[abi_address(x[0]) for x in array(call(pool,'backed'),1,self.limit)]
        if len(set(backed))!=len(backed) or set(backed)-set(self.borrowers):raise ValueError('untracked backed borrower')
        backing={}
        for who in sorted(backed):
            rows=array(call(pool,'backings',who),3,32)
            entries=[{'backer':abi_address(w[0]),'secured':int(w[1],16),'unsecured':int(w[2],16)} for w in rows]
            if len({x['backer'] for x in entries})!=len(entries):raise ValueError('duplicate backer')
            if any(x['unsecured'] for x in entries):raise ValueError('unsecured backing unsupported')
            backing[who]=sorted(entries,key=lambda x:x['backer'])
        grants={};controllers={};groups={}
        for who in self.borrowers:
            w=words(call(self.budget,'grants',who),5);c,g='0x'+w[0],'0x'+w[1];cap,used,expiry=map(lambda x:int(x,16),w[2:])
            revoked=uint(self.budget,'revoked',who)
            if revoked not in (0,1) or used>cap or cap>min(budget['totalCap'],budget['controllerCap'],budget['groupCap']):raise ValueError('grant state')
            grants[who]={'controller':c,'group':g,'cap':cap,'used':used,'expiry':expiry,'revoked':revoked}
            controllers[c]=uint(self.budget,'controllerUsed',c);groups[g]=uint(self.budget,'groupUsed',g)
            if used!=sum(x['principal'] for x in loans.values() if x['borrower']==who):raise ValueError('borrower gross mismatch')
        if any(v>budget['controllerCap'] for v in controllers.values()) or any(v>budget['groupCap'] for v in groups.values()):raise ValueError('scope cap exceeded')
        if sum(controllers.values())!=gross or sum(groups.values())!=gross:raise ValueError('scope aggregate mismatch')
        cash={k:uint(pool,k) for k in ('lenderCash','firstLossReserve','totalImpaired','protocolFees','totalStaked','totalUnclaimedPayouts')}
        cash['tokenBalance']=uint(address(p.policy.token),'balance',pool)
        state={'cash':cash,'pool':pool,'budget_address':self.budget,'budget':budget,'loans':loans,'backing':backing,
               'grants':grants,'controllers':controllers,'groups':groups,'lent':uint(pool,'lent'),'reserved':uint(pool,'reserved')}
        if p.block_hash(n)!=h:raise ValueError('inventory reorg')
        return {'chain':p.policy.chain,'block':n,'hash':h,'timestamp':quantity(block['timestamp']),'state':state}


class InventoryProbe:
    """Installed expected digest must come from private ledger/receipt reconciliation.
    Never update it merely because fresh chain state differs. Unknown unused grants
    cannot be enumerated by this ABI: registry completeness is a custody/issuer gate.
    """
    def __init__(self,source,expected_digest,*,clock,quiescent):
        self.source,self.expected,self.clock,self.quiescent=source,expected_digest,clock,quiescent
    def __call__(self):
        try:
            if self.quiescent() is not True:return False
            s=self.source.snapshot();now=self.clock();b=s['state']['budget'];p=self.source.p.policy
            if type(now)is not int or not 0<=now-s['timestamp']<=120:return False
            if b['stopped'] or b['totalCap']>min(units(p.gross_total),units(p.net_total)):return False
            if b['controllerCap']>min(units(p.gross_controller),units(p.net_controller)):return False
            if b['groupCap']>min(units(p.gross_group),units(p.net_group)):return False
            return digest(s['state'])==self.expected and self.quiescent() is True
        except Exception:return False


class LeaseProbe:
    """Trusted supervisor's current exclusive-custody record, not an IPC claim.
    Existing repository execution-owner config alone is insufficient. This adapter
    checks an expected generation but cannot fence a second holder of a signing key.
    """
    def __init__(self,authority,*,owner,generation,source_revision,clock):
        self.authority,self.owner,self.generation,self.revision,self.clock=authority,owner,generation,source_revision,clock
    def __call__(self):
        try:
            r=self.authority();now=self.clock()
            return (set(r)=={'owner','generation','source_revision','issued_at','expires_at','drained','exclusive_custody','relaunch_fenced'}
                and r['owner']==self.owner and type(r['generation'])is int and r['generation']==self.generation
                and r['source_revision']==self.revision and type(now)is int and type(r['issued_at'])is int
                and type(r['expires_at'])is int and r['issued_at']<=now<r['expires_at']<=r['issued_at']+120
                and all(r[k] is True for k in ('drained','exclusive_custody','relaunch_fenced')))
        except Exception:return False
