// Pure signed-envelope verification. No clients, keys, network or broadcasting.
const { parseTransaction, recoverTransactionAddress, serializeTransaction, keccak256, isAddress } = require('viem');
const HALF_N = 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0n;
const SECP_N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141n;
const hex = (x) => typeof x === 'string' && /^0x[0-9a-fA-F]*$/.test(x) && x.length % 2 === 0;
const addr = (x) => { if (!isAddress(x,{strict:false})) throw Error('invalid address'); return x.toLowerCase(); };
const integer = (x) => { if (typeof x!=='bigint' || x<0n) throw Error('nonnegative bigint required'); return x; };
async function verifySigned(serialized, bound, limits, now) {
  if (!hex(serialized) || serialized.length>32768 || !serialized.startsWith('0x02')) throw Error('EIP1559 signed envelope required');
  if (!Number.isSafeInteger(now) || !Number.isSafeInteger(limits.expires) || now>=limits.expires) throw Error('expired envelope');
  const t=parseTransaction(serialized);
  if (t.type!=='eip1559' || t.r===undefined || t.s===undefined || ![0,1].includes(t.yParity)) throw Error('missing signature');
  if (BigInt(t.r)<=0n || BigInt(t.r)>=SECP_N || BigInt(t.s)<=0n || BigInt(t.s)>HALF_N) throw Error('invalid or malleable signature');
  // Canonical reserialization rejects alternate encodings/trailing bytes.
  if (serializeTransaction(t,{r:t.r,s:t.s,yParity:t.yParity}).toLowerCase()!==serialized.toLowerCase()) throw Error('noncanonical serialization');
  const sender=await recoverTransactionAddress({serializedTransaction:serialized});
  if (!Number.isSafeInteger(bound.chainId) || t.chainId!==bound.chainId || !Number.isSafeInteger(bound.nonce) || (t.nonce??0)!==bound.nonce ||
      addr(sender)!==addr(bound.from) || addr(t.to)!==addr(bound.to) || (t.value??0n)!==integer(bound.value) ||
      !hex(bound.data) || (t.data??'0x').toLowerCase()!==bound.data.toLowerCase()) throw Error('signed action differs from binding');
  if ((t.accessList??[]).length!==0) throw Error('unreviewed access list');
  const gas=integer(t.gas), fee=integer(t.maxFeePerGas??0n), tip=integer(t.maxPriorityFeePerGas??0n);
  if (gas===0n || gas>integer(limits.gas) || fee>integer(limits.maxFeePerGas) || tip>fee ||
      gas*fee>integer(limits.maxTotalFee)) throw Error('gas or fee budget exceeded');
  return {signatureValid:true,transactionHash:keccak256(serialized),sender:addr(sender),executionAllowed:false,
          reason:'CURRENT_CONSENT_POLICY_NONCE_AND_RELEASE_GATE_REQUIRED'};
}
module.exports={verifySigned};
