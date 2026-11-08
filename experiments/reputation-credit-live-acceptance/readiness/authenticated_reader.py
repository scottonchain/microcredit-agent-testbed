"""Pinned read-only HTTPS acquisition. Never signs/sends or changes network policy.
Use only in an independently permitted runtime. TLS authenticates the endpoint,
not chain truth; optional independent-reader agreement is NOT a receipt proof.
"""
import hashlib
import json
import ssl
import re
import urllib.parse
import urllib.request
from canonical_adapter import quantity, words
from durable import address, txhash

READ_METHODS=frozenset({'eth_chainId','eth_blockNumber','eth_getBlockByNumber','eth_getBlockByHash',
 'eth_getTransactionByHash','eth_getTransactionReceipt','eth_getCode','eth_call','eth_getTransactionCount','eth_getStorageAt'})


def strict_json(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('duplicate JSON key')
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def thread_length(encoded):
    """Strict ABI Msg[](uint8 from,uint40 at,string text), discarding all text."""
    if not isinstance(encoded,str) or not re.fullmatch(r'0x(?:[0-9a-fA-F]{64})*',encoded):raise ValueError('thread ABI bytes')
    raw=bytes.fromhex(encoded[2:])
    def uint(start):
        if start<0 or start+32>len(raw):raise ValueError('truncated thread ABI')
        return int.from_bytes(raw[start:start+32],'big')
    if uint(0)!=32:raise ValueError('thread offset')
    count=uint(32)
    if count>80:raise ValueError('thread limit')
    cursor=64+32*count
    for i in range(count):
        if uint(64+32*i)!=cursor-64 or uint(cursor)>1 or uint(cursor+32)>=2**40 or uint(cursor+64)!=96:
            raise ValueError('noncanonical message tuple')
        size=uint(cursor+96)
        if size>1000:raise ValueError('message limit')
        end=cursor+128+((size+31)//32)*32
        if end>len(raw) or any(raw[cursor+128+size:end]):raise ValueError('message bounds/padding')
        cursor=end
    if cursor!=len(raw):raise ValueError('thread trailing bytes')
    return count


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise ValueError('RPC redirects forbidden')


class HTTPSReadRPC:
    def __init__(self,endpoint,*,approved_origins,timeout=10,max_bytes=8_000_000):
        u=urllib.parse.urlsplit(endpoint)
        if (u.scheme!='https' or u.username or u.password or u.query or u.fragment or
            not u.hostname or u.port not in (None,443) or u.path not in ('','/') or
            'https://'+u.hostname not in approved_origins):
            raise ValueError('exact approved credential-free HTTPS origin required')
        if not 0<timeout<=30 or not 0<max_bytes<=32_000_000: raise ValueError('bounded transport required')
        self.endpoint,self.timeout,self.max_bytes=endpoint,timeout,max_bytes
        # Default ProxyHandler respects the runtime's managed proxy environment;
        # do not install ProxyHandler({}) or change CA/proxy/network settings.
        self.opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    def call(self,method,params):
        if method not in READ_METHODS: raise ValueError('read-only RPC method required')
        return self._exchange(method,params)
    def _exchange(self,method,params):
        body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params},allow_nan=False).encode()
        if len(body)>100_000: raise ValueError('request too large')
        req=urllib.request.Request(self.endpoint,data=body,headers={'Content-Type':'application/json'},method='POST')
        with self.opener.open(req,timeout=self.timeout) as response:
            raw=response.read(self.max_bytes+1)
        if len(raw)>self.max_bytes: raise ValueError('response too large')
        value=strict_json(raw)
        if (not isinstance(value,dict) or value.get('jsonrpc')!='2.0' or type(value.get('id')) is not int or
            value['id']!=1 or 'error' in value or 'result' not in value): raise ValueError('invalid RPC response')
        return value['result']


class AuthenticatedSnapshots:
    """Source manifest is installed by the release owner, never request-supplied.
    Each code pin is SHA256 of exact deployed runtime INCLUDING immutable values.
    Two configured readers must agree on pinned observations. No fallback on denial.
    """
    def __init__(self,primary,policy,code_pins,*,witness=None,max_transactions=512,proxy_bindings=None):
        if not code_pins or not 0<max_transactions<=2048: raise ValueError('code pins and bounded inventory required')
        self.primary,self.witness,self.policy=primary,witness,policy
        self.pins={address(k):txhash(v) for k,v in code_pins.items()}
        if address(policy.pool) not in self.pins or address(policy.token) not in self.pins: raise ValueError('pool/token pins required')
        self.max_transactions=max_transactions
        self.proxy_bindings={}
        for proxy,binding in (proxy_bindings or {}).items():
            proxy=address(proxy);implementation=address(binding['implementation']);slot=txhash(binding['slot'])
            if proxy not in self.pins or implementation not in self.pins:raise ValueError('proxy and implementation code pins required')
            self.proxy_bindings[proxy]=(slot,implementation)
    def _call(self,method,params):
        if method not in READ_METHODS: raise ValueError('read only')
        value=self.primary.call(method,params)
        if self.witness is not None and self.witness.call(method,params)!=value:
            raise ValueError('independent reader disagreement; hold')
        return value
    def chain_id(self):
        chain=quantity(self._call('eth_chainId',[]))
        if chain!=self.policy.chain: raise ValueError('chain mismatch')
        return chain
    def head(self):
        # Moving heads need not match exactly: use the lower independently read
        # height, then compare immutable block identity at that exact height.
        self.chain_id();h=quantity(self.primary.call('eth_blockNumber',[]))
        if self.witness is not None:h=min(h,quantity(self.witness.call('eth_blockNumber',[])))
        return h
    def block_hash(self,n):
        if type(n) is not int or n<0: raise ValueError('block number required')
        b=self._call('eth_getBlockByNumber',[hex(n),False])
        if not b or quantity(b['number'])!=n: raise ValueError('missing block')
        return txhash(b['hash'])
    def _pins(self,block):
        anchor={'blockHash':block,'requireCanonical':True}
        for proxy,(slot,implementation) in self.proxy_bindings.items():
            raw=self._call('eth_getStorageAt',[proxy,slot,anchor])
            if words(raw,1)[0]!='0'*24+implementation[2:]:raise ValueError('proxy implementation changed')
        for target,expected in self.pins.items():
            raw=self._call('eth_getCode',[target,anchor])
            if not isinstance(raw,str) or not raw.startswith('0x') or len(raw)%2:raise ValueError('malformed runtime')
            code=bytes.fromhex(raw[2:])
            if not code or '0x'+hashlib.sha256(code).hexdigest()!=expected:raise ValueError('runtime identity mismatch')
    def _balance(self,block):
        result=self._call('eth_call',[{'to':address(self.policy.token),'data':'0x70a08231'+address(self.policy.pool)[2:].rjust(64,'0')},
                                     {'blockHash':block,'requireCanonical':True}])
        return hex(int(words(result,1)[0],16))
    def bundle(self,transaction):
        transaction=txhash(transaction);self.chain_id()
        t=self._call('eth_getTransactionByHash',[transaction])
        if t is None or t.get('blockNumber') is None:return None
        if txhash(t['hash'])!=transaction or quantity(t['chainId'])!=self.policy.chain:raise ValueError('transaction identity/domain mismatch')
        n=quantity(t['blockNumber']);h=txhash(t['blockHash'])
        block=self._call('eth_getBlockByNumber',[hex(n),False])
        if not block or txhash(block['hash'])!=h:raise ValueError('transaction reorg')
        ids=block['transactions']
        if not isinstance(ids,list) or not 0<len(ids)<=self.max_transactions or len(set(ids))!=len(ids) or transaction not in ids:
            raise ValueError('bounded complete transaction inventory required')
        receipts=[self._call('eth_getTransactionReceipt',[txhash(i)]) for i in ids]
        if any(r is None for r in receipts):raise ValueError('missing receipt; hold')
        head=self.head()
        if head-n+1<self.policy.confirmations:raise ValueError('unconfirmed')
        parent=txhash(block['parentHash'])
        if n==0 or self.block_hash(n-1)!=parent:raise ValueError('parent mismatch')
        self._pins(h)
        result={'chainId':hex(self.policy.chain),'block':block,'transaction':t,'receipts':receipts,
                'head':{'number':hex(head)},'canonicalHash':h,
                'before':{'blockHash':parent,'token':address(self.policy.token),'account':address(self.policy.pool),'balance':self._balance(parent)},
                'after':{'blockHash':h,'token':address(self.policy.token),'account':address(self.policy.pool),'balance':self._balance(h)}}
        if self.block_hash(n)!=h:raise ValueError('reorg during acquisition')
        return result

    def observe(self,transaction):
        """PendingJournal receipt interface; outcome, not backing-release proof."""
        b=self.bundle(transaction)
        if b is None:return None
        t=b['transaction'];n=quantity(t['transactionIndex'])
        if n>=len(b['receipts']):raise ValueError('receipt index mismatch')
        r=b['receipts'][n]
        if (txhash(r['transactionHash'])!=txhash(transaction) or quantity(r['transactionIndex'])!=n or
            txhash(r['blockHash'])!=b['canonicalHash'] or quantity(r['blockNumber'])!=quantity(b['block']['number'])):
            raise ValueError('receipt binding mismatch')
        status=quantity(r['status'])
        if status not in (0,1):raise ValueError('invalid receipt status')
        return {'hash':txhash(transaction),'transaction':{'chainId':hex(quantity(t['chainId'])),'from':address(t['from']),
          'to':address(t['to']),'nonce':hex(quantity(t['nonce'])),'value':hex(quantity(t['value'])),'data':t['input']},
          'status':status,'block':quantity(b['block']['number']),'block_hash':b['canonicalHash']}


class DeskSnapshots:
    """Real CreditDesk/pool scalar interfaces; never returns applicant message text."""
    def __init__(self,provider,desk,officer):
        self.provider,self.desk,self.officer=provider,address(desk),address(officer)
        if self.desk not in provider.pins:raise ValueError('exact desk runtime pin required')
    def block_hash(self,n):return self.provider.block_hash(n)
    def snapshot(self,borrower):
        borrower=address(borrower);p=self.provider
        n=p.head()-p.policy.confirmations+1
        if n<0:raise ValueError('confirmed block unavailable')
        block=p._call('eth_getBlockByNumber',[hex(n),False]);h=txhash(block['hash'])
        if quantity(block['number'])!=n:raise ValueError('wrong state block')
        p._pins(h);anchor={'blockHash':h,'requireCanonical':True}
        def call(target,selector,*args):
            return p._call('eth_call',[{'to':target,'data':selector+''.join(address(a)[2:].rjust(64,'0') for a in args)},anchor])
        def uint(target,selector,*args):return int(words(call(target,selector,*args),1)[0],16)
        def addr(selector):
            raw=words(call(self.desk,selector),1)[0]
            if raw[:24]!='0'*24:raise ValueError('noncanonical address')
            return address('0x'+raw[24:])
        pool=addr('0x16f0115b');token=addr('0x3e413bee');officer=addr('0xbc685ce0')
        if (pool,token,officer)!=(address(p.policy.pool),address(p.policy.token),self.officer):raise ValueError('desk wiring mismatch')
        secured,unsecured=(int(v,16) for v in words(call(pool,'0x4c00acbb',self.desk,borrower),2))
        credit,stake=(int(v,16) for v in words(call(pool,'0xec1e5d13',self.desk),2))
        thread=call(self.desk,'0xd0aac15e',borrower)
        # Validate ABI structure but never return or interpret message text.
        length=thread_length(thread)
        nonce=quantity(p._call('eth_getTransactionCount',[officer,anchor]))
        if any(quantity(p._call('eth_getTransactionCount',[officer,tag]))!=nonce for tag in ('latest','pending')):
            raise ValueError('officer has unconfirmed/unreconciled activity')
        result={'chain':p.policy.chain,'desk':self.desk,'pool':pool,'usdc':token,'officer':officer,'applicant':borrower,
         'timestamp':quantity(block['timestamp']),'block':n,'hash':h,'maxLine':uint(self.desk,'0xfee4412f'),
         'backing':secured+unsecured,'secured':secured,'unsecured':unsecured,'freeStake':stake,'freeCredit':credit,
         'nonce':nonce,'threadLength':length,'knownApplicant':uint(self.desk,'0x6133a9e3',borrower)>0,
         'defaultedLoans':uint(pool,'0x34ca3573',borrower)}
        if p.block_hash(n)!=h:raise ValueError('state changed during acquisition')
        return result
