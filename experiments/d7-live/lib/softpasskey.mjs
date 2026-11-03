// A software WebAuthn authenticator for Node: stands in for navigator.credentials.create/get so the passkey smart wallet
// can be exercised headlessly in scripts. Produces the same data shapes a real authenticator returns.
import { generateKeyPairSync, createHash, createSign, randomBytes, createPrivateKey } from 'node:crypto';

const b64u = (buf) => Buffer.from(buf).toString('base64url');
const sha256 = (b) => createHash('sha256').update(b).digest();

export class SoftAuthenticator {
  // Persist and restore keys so a headless agent keeps the same passkey between processes.
  toJSON() { return { rpId: this.rpId, origin: this.origin, signCount: this.signCount, keys: [...this.keys].map(([id, k]) => ({ id, pem: k.export({ type: 'pkcs8', format: 'pem' }) })) }; }
  static fromJSON(o) { const a = new SoftAuthenticator({ rpId: o.rpId, origin: o.origin }); a.signCount = o.signCount || 0; for (const k of o.keys) a.keys.set(k.id, createPrivateKey(k.pem)); return a; }
  constructor({ rpId = 'localhost', origin = 'http://localhost' } = {}) {
    this.rpId = rpId; this.origin = origin; this.keys = new Map(); this.signCount = 0; this.uvFails = false; this.calls = 0;
  }
  createFn = async () => {
    const { publicKey, privateKey } = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
    const spki = publicKey.export({ type: 'spki', format: 'der' });
    const id = b64u(randomBytes(32));
    this.keys.set(id, privateKey);
    return { id, rawId: Buffer.from(id, 'base64url'), type: 'public-key', response: { getPublicKey: () => spki.buffer.slice(spki.byteOffset, spki.byteOffset + spki.byteLength) } };
  };
  getFn = async (options) => {
    this.calls++;
    const pk = options.publicKey; const ids = (pk.allowCredentials || []).map((c) => b64u(c.id));
    const id = ids.find((i) => this.keys.has(i)) || [...this.keys.keys()][0];
    if (!id) throw new Error('NotAllowedError: no credential');
    if (this.uvFails) throw new Error('NotAllowedError: user verification failed');
    const clientDataJSON = Buffer.from(JSON.stringify({ type: 'webauthn.get', challenge: b64u(pk.challenge), origin: this.origin, crossOrigin: false }));
    const flags = Buffer.from([0x05]); const cnt = Buffer.alloc(4); cnt.writeUInt32BE(++this.signCount);
    const authenticatorData = Buffer.concat([sha256(Buffer.from(pk.rpId || this.rpId)), flags, cnt]);
    const signer = createSign('SHA256'); signer.update(Buffer.concat([authenticatorData, sha256(clientDataJSON)]));
    const signature = signer.sign(this.keys.get(id)); // DER
    const ab = (b) => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
    return { id, rawId: Buffer.from(id, 'base64url'), type: 'public-key', response: { authenticatorData: ab(authenticatorData), clientDataJSON: ab(clientDataJSON), signature: ab(signature) } };
  };
}
