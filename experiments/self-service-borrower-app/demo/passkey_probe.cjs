// D7 gate 2: headless passkey probe. Creates a P-256 WebAuthn credential and signs a
// challenge with the preinstalled browser's virtual authenticator, against a page served
// from localhost (WebAuthn needs a secure context). No chain, no key file, no network.
// Run: python3 -m http.server 8765 --bind 127.0.0.1 (in any directory with an index.html), then node passkey_probe.cjs
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('WebAuthn.enable');
  const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
    options: { protocol: 'ctap2', transport: 'internal', hasResidentKey: true, hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true },
  });
  await page.goto('http://localhost:8765/');
  const result = await page.evaluate(async () => {
    const cred = await navigator.credentials.create({ publicKey: {
      challenge: new Uint8Array(32), rp: { name: 'omnequa demo', id: 'localhost' },
      user: { id: new Uint8Array(16), name: 'tester', displayName: 'tester' },
      pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
      authenticatorSelection: { residentKey: 'required', userVerification: 'required' } } });
    const pk = cred.response.getPublicKey ? cred.response.getPublicKey() : null;
    const assertion = await navigator.credentials.get({ publicKey: { challenge: new Uint8Array(32).fill(7), rpId: 'localhost', allowCredentials: [{ type: 'public-key', id: cred.rawId }], userVerification: 'required' } });
    return { credIdBytes: cred.rawId.byteLength, alg: cred.response.getPublicKeyAlgorithm ? cred.response.getPublicKeyAlgorithm() : null, spkiBytes: pk ? pk.byteLength : null, sigBytes: assertion.response.signature.byteLength, authDataBytes: assertion.response.authenticatorData.byteLength };
  });
  console.log(JSON.stringify({ authenticatorId: !!authenticatorId, ...result }));
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
