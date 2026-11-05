"""Offline-tested canonical-interface decoder. NO network or signing implementation.

An independently authenticated provider must supply complete block/receipt/state
snapshots. This code checks consistency, not RPC authenticity or receipt-trie
proofs. It conservatively supports direct repayLoan ONLY; complex cases HOLD.
Selectors/topics derived using Ethereum Keccak256, never SHA3-256.
"""
from decimal import Decimal
import re
from durable import Observation, address, txhash

TRANSFER='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
REPAID='0xc7ce0a35f17b490de2a317e7fecb2cae86b1abffb03800b2f492823521382698'
APPLIED='0x79cc0b6d59d041321d365afff1d2b489f2e14c096f2e9ebd04b662c0230b0c5f'
REPAY='8a700b53'
REPLY='3c034716'


def quantity(value):
    if not isinstance(value,str) or not re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)',value):
        raise ValueError('canonical RPC quantity required')
    n=int(value,16)
    if n>=2**256: raise ValueError('uint256 overflow')
    return n


def words(value, count):
    if not isinstance(value,str) or not re.fullmatch(r'0x[0-9a-fA-F]*',value) or len(value)!=2+64*count:
        raise ValueError('exact ABI words required')
    return [value[2+i*64:2+(i+1)*64].lower() for i in range(count)]


def topic_address(value):
    word=words(value,1)[0]
    if word[:24]!='0'*24: raise ValueError('noncanonical address padding')
    return address('0x'+word[24:])


def decimal_units(value):
    return str(Decimal(value)/Decimal(1_000_000))


def repayment_observation(bundle, policy, requested_tx, requested_event, now):
    """Require a complete block and unambiguous net pool cash for one direct repay.

    Parent/end-block balance difference is transaction-local only because EVERY
    other transaction receipt is checked for pool activity and token movements.
    Same-transaction withdrawals, refunds, donations and batched repayments hold.
    Caller supplies a lookup key, never an amount or fabricated approval flag.
    """
    chain=quantity(bundle['chainId'])
    if chain!=policy.chain: raise ValueError('wrong chain')
    block=bundle['block']; head=bundle['head']; transaction=bundle['transaction']
    number=quantity(block['number']); block_hash=txhash(block['hash'])
    if type(now) is not int or not -120<=now-quantity(block['timestamp'])<=900:
        raise ValueError('stale or future evidence')
    if quantity(head['number'])-number+1<policy.confirmations: raise ValueError('shallow evidence')
    if txhash(bundle['canonicalHash'])!=block_hash: raise ValueError('noncanonical block')
    if txhash(transaction['hash'])!=txhash(requested_tx): raise ValueError('transaction mismatch')
    if quantity(transaction['chainId'])!=chain or quantity(transaction['value'])!=0:
        raise ValueError('transaction domain/value mismatch')
    if address(transaction['to'])!=address(policy.pool): raise ValueError('not direct pool call')
    payer=address(transaction['from'])
    if payer==address(policy.pool): raise ValueError('self payment')
    data=transaction['input']
    if not isinstance(data,str) or not data.lower().startswith('0x'+REPAY): raise ValueError('unsupported method')
    call=words('0x'+data[10:],2)
    loan,maximum=map(lambda w:int(w,16),call)
    if maximum==0: raise ValueError('zero request')
    hashes=[txhash(h) for h in block['transactions']]
    if len(hashes)!=len(set(hashes)) or txhash(requested_tx) not in hashes: raise ValueError('invalid block inventory')
    receipts=bundle['receipts']
    if len(receipts)!=len(hashes): raise ValueError('incomplete block receipts')
    candidate=None; seen_logs=set()
    for i,(h,receipt) in enumerate(zip(hashes,receipts)):
        if (txhash(receipt['transactionHash'])!=h or quantity(receipt['transactionIndex'])!=i or
            quantity(receipt['blockNumber'])!=number or txhash(receipt['blockHash'])!=block_hash):
            raise ValueError('receipt block/order mismatch')
        status=quantity(receipt['status'])
        if status not in (0,1): raise ValueError('invalid receipt status')
        if h==txhash(requested_tx):
            if status!=1: raise ValueError('failed repayment')
            candidate=receipt
        for log in receipt['logs']:
            index=quantity(log['logIndex'])
            if index in seen_logs: raise ValueError('duplicate block log index')
            seen_logs.add(index)
            if (log.get('removed') is not False or txhash(log['transactionHash'])!=h or
                quantity(log['transactionIndex'])!=i or txhash(log['blockHash'])!=block_hash or
                quantity(log['blockNumber'])!=number): raise ValueError('log provenance mismatch')
            emitter=address(log['address']); topics=log['topics']
            if not isinstance(topics,list) or not topics: raise ValueError('invalid topics')
            if h!=txhash(requested_tx):
                if emitter==address(policy.pool): raise ValueError('other pool activity in block')
                if emitter==address(policy.token) and topics[0].lower()==TRANSFER:
                    if len(topics)!=3: raise ValueError('bad transfer ABI')
                    if address(policy.pool) in (topic_address(topics[1]),topic_address(topics[2])):
                        raise ValueError('other pool cash movement in block')
    if (quantity(transaction['transactionIndex'])!=hashes.index(txhash(requested_tx)) or
        txhash(transaction['blockHash'])!=block_hash or quantity(transaction['blockNumber'])!=number):
        raise ValueError('transaction block mismatch')
    repaid=[]; applied=[]; cash=[]
    for log in candidate['logs']:
        topics=log['topics']; emitter=address(log['address']); tag=topics[0].lower()
        if emitter==address(policy.pool) and tag==REPAID:
            if len(topics)!=3: raise ValueError('bad LoanRepaid ABI')
            repaid.append((log,topic_address(topics[1]),int(words(topics[2],1)[0],16),int(words(log['data'],1)[0],16)))
        if emitter==address(policy.pool) and tag==APPLIED:
            if len(topics)!=2: raise ValueError('bad RepaymentApplied ABI')
            applied.append((log,int(words(topics[1],1)[0],16),*[int(w,16) for w in words(log['data'],3)]))
        if emitter==address(policy.token) and tag==TRANSFER:
            if len(topics)!=3: raise ValueError('bad Transfer ABI')
            src,dst=topic_address(topics[1]),topic_address(topics[2])
            value=int(words(log['data'],1)[0],16)
            if address(policy.pool) in (src,dst): cash.append((log,src,dst,value))
    if len(repaid)!=1 or len(applied)!=1 or len(cash)!=1: raise ValueError('ambiguous cash or repayment allocation')
    rl,borrower,rloan,paid=repaid[0]
    al,aloan,interest,principal,fee=applied[0]
    tl,src,dst,transferred=cash[0]
    if (type(requested_event) is not int or requested_event!=quantity(rl['logIndex']) or
        loan!=rloan or loan!=aloan or principal<=0 or interest+principal!=paid or fee>interest or
        paid>maximum or transferred!=paid or src!=payer or dst!=address(policy.pool) or
        not quantity(tl['logIndex'])<quantity(al['logIndex'])<quantity(rl['logIndex'])):
        raise ValueError('loan/principal/transfer binding mismatch')
    for state,expected_hash in [(bundle['before'],txhash(block['parentHash'])),(bundle['after'],block_hash)]:
        if (txhash(state['blockHash'])!=expected_hash or address(state['token'])!=address(policy.token) or
            address(state['account'])!=address(policy.pool)):
            raise ValueError('balance snapshot binding mismatch')
    if quantity(bundle['after']['balance'])-quantity(bundle['before']['balance'])!=paid:
        raise ValueError('net pool cash does not match paid amount')
    return Observation(chain,txhash(requested_tx),number,block_hash,1,'repayment',address(policy.pool),
                       address(policy.token),borrower,str(loan),decimal_units(principal),dst,
                       decimal_units(paid),requested_event,quantity(tl['logIndex']),src)


class CanonicalReader:
    """Adapter to Ledger's reader interface. Provider is trusted, never applicant code.
    No provider or RPC implementation is shipped; tests provide fixed snapshots.
    """
    def __init__(self, provider, policy, clock):
        self.provider,self.policy,self.clock=provider,policy,clock
    def chain_id(self): return self.provider.chain_id()
    def head(self): return self.provider.head()
    def block_hash(self,n): return self.provider.block_hash(n)
    def observe(self,transaction,event_index):
        bundle=self.provider.bundle(transaction)
        if bundle is None: return None
        return repayment_observation(bundle,self.policy,transaction,event_index,self.clock())
