// node --test scripts/test_circle_agent_rules.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { loadAllowlist } from './drip_rules.mjs';
import { extractRequestId, extractOtp, otpFromMessage, pickOtpMessages, parseAgentWallet, parseTransferId, parseCliOutput, idempotencyKey, decodeUsdc, decideAgentDrip } from './circle_agent_rules.mjs';

const list = loadAllowlist(JSON.parse(readFileSync(new URL('./drip_allowlist.json', import.meta.url), 'utf8')));
const treasury = list.get('0x2aa4069f65931e8b35ed11ac493b1c3ab9917212');
const officer = list.get('0xb88dc88d538a754f57cab344c1e09d02c129fcf2');

test('request id comes from the init message', () => {
  const msg = 'OTP code sent to agent@example.test\nPlease run: circle wallet login --request 9d6a5a52-7275-4e92-a6c1-a1e71a0641716 --otp <code>';
  assert.equal(extractRequestId(msg), '9d6a5a52-7275-4e92-a6c1-a1e71a0641716');
  assert.equal(extractRequestId('no id here'), null);
});

test('one-time password is parsed in the full head-dash-digits form only', () => {
  assert.equal(extractOtp('Your Circle code is ABC-123456. It expires in 10 minutes.'), 'ABC-123456');
  assert.equal(extractOtp('code: xyz-654321'), 'XYZ-654321');
  assert.equal(extractOtp('just 123456'), null);
  assert.equal(extractOtp(''), null);
});

test('one-time password is read from the message as AgentMail returns it: subject, text fields, or HTML', () => {
  // Shape seen on 2026-11-03: subject and html only, no text field.
  assert.equal(otpFromMessage({ subject: 'QRS-246810 is your Circle Agent Wallet verification code (Testnet)', html: '<p>QRS-246810</p>' }), 'QRS-246810');
  assert.equal(otpFromMessage({ subject: 'Your code', text: 'Your code is TUV-135791.' }), 'TUV-135791');
  assert.equal(otpFromMessage({ subject: 'Your code', html: '<html><body><b>WXY</b>-<i>000000</i> no; <span>WXY-000001</span></body></html>' }), 'WXY-000001');
  assert.equal(otpFromMessage({ subject: 'Your code', html: '<p>nothing here</p>' }), null);
  assert.equal(otpFromMessage(null), null);
});

test('OTP candidates: after the request, from Circle, newest first', () => {
  const msgs = [
    { message_id: 'a', from: 'Circle <no-reply@circle.com>', subject: 'Your code', timestamp: '2026-11-02T20:00:30.000Z' },
    { message_id: 'b', from: 'Circle <no-reply@circle.com>', subject: 'Your code', timestamp: '2026-11-02T20:01:00.000Z' },
    { message_id: 'c', from: 'Hermes AI agent <hermes-909@agentmail.to>', subject: 'Transcript', timestamp: '2026-11-02T20:01:30.000Z' },
    { message_id: 'd', from: 'Circle <no-reply@circle.com>', subject: 'Old code', timestamp: '2026-11-02T19:00:00.000Z' },
  ];
  assert.deepEqual(pickOtpMessages(msgs, '2026-11-02T20:00:00.000Z', 120).map((m) => m.message_id), ['b', 'a']);
  assert.deepEqual(pickOtpMessages(msgs, '2026-11-02T20:00:00.000Z', 15, new Set(['a'])).map((m) => m.message_id), ['b']);
  assert.deepEqual(pickOtpMessages(msgs, '2026-11-02T20:00:50.000Z').map((m) => m.message_id), ['b']);
});

test('the CLI envelope: pretty-printed data and error objects, as the bundle prints them', () => {
  const init = JSON.stringify({ data: { message: 'OTP code sent to a@b.test\nPlease run: circle wallet login --request 0f50e465-c7c1-4e06-ac09-7fb20fb6b346 --otp <code>', warning: 'x' } }, null, 2);
  assert.equal(extractRequestId(parseCliOutput(init).data.message), '0f50e465-c7c1-4e06-ac09-7fb20fb6b346');
  const status = JSON.stringify({ data: { type: 'agent', mainnet: { tokenStatus: 'NOT_LOGGED_IN' }, testnet: { email: 'a@b.test', tokenStatus: 'VALID', expiresIn: '27d 3h' } } }, null, 2);
  assert.equal(parseCliOutput(status).data.testnet.tokenStatus, 'VALID');
  const list = JSON.stringify({ data: { wallets: [{ type: 'agent', address: '0xb88DC88d538a754f57cAB344C1E09d02C129fcf2', blockchain: 'BASE-SEPOLIA', createDate: '2026-11-02' }] } }, null, 2);
  assert.equal(parseAgentWallet(parseCliOutput(list).data, 'BASE-SEPOLIA'), '0xb88DC88d538a754f57cAB344C1E09d02C129fcf2');
  const transfer = JSON.stringify({ data: { id: 'c0ffee00-0000-4000-8000-000000000001', state: 'COMPLETE', txHash: '0xabc' } }, null, 2);
  assert.equal(parseTransferId(parseCliOutput(transfer).data), 'c0ffee00-0000-4000-8000-000000000001');
  const error = 'Error: Circle CLI Terms acceptance is required before use.\n' + JSON.stringify({ error: { code: 'PERMISSION_DENIED', message: 'Circle CLI Terms acceptance is required before use.', hint: 'Set CIRCLE_ACCEPT_TERMS=1' } }, null, 2);
  const e = parseCliOutput(error);
  assert.equal(e.data, null); assert.equal(e.error.code, 'PERMISSION_DENIED');
  assert.deepEqual(parseCliOutput('plain text, no json'), { data: null, error: null });
});

test('idempotency key is deterministic per recipient, amount and day, and UUID-shaped', () => {
  const k1 = idempotencyKey('0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212', 25, '2026-11-02');
  const k2 = idempotencyKey('0x2aa4069f65931e8b35ed11ac493b1c3ab9917212', 25, '2026-11-02');
  const k3 = idempotencyKey('0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212', 25, '2026-11-03');
  assert.equal(k1, k2); assert.notEqual(k1, k3);
  assert.match(k1, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test('agent wallet address for the chain, transfer id, balance decoding', () => {
  const json = { wallets: [{ type: 'agent', address: '0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212', blockchain: 'ARC-TESTNET' }, { type: 'agent', address: '0xb88DC88d538a754f57cAB344C1E09d02C129fcf2', blockchain: 'BASE-SEPOLIA' }] };
  assert.equal(parseAgentWallet(json, 'BASE-SEPOLIA'), '0xb88DC88d538a754f57cAB344C1E09d02C129fcf2');
  assert.equal(parseAgentWallet({ wallets: [] }, 'BASE-SEPOLIA'), null);
  assert.equal(parseTransferId({ transactionId: 'tx-1' }), 'tx-1');
  assert.equal(parseTransferId({ message: 'ok' }), null);
  assert.equal(decodeUsdc('0x' + (20_000_000).toString(16)), 20);
  assert.equal(decodeUsdc('0x'), 0);
  assert.equal(decodeUsdc('nope'), null);
});

test('agent drip decision follows the allowlist caps and the agent balance', () => {
  assert.deepEqual(decideAgentDrip({ entry: treasury, amount: 20, recipientBalance: 0, agentBalance: 20 }), { ok: true });
  assert.equal(decideAgentDrip({ entry: treasury, amount: 20, recipientBalance: 0, agentBalance: 19.9 }).ok, false);
  assert.equal(decideAgentDrip({ entry: officer, amount: 5, recipientBalance: 5, agentBalance: 20 }).ok, false);
  assert.equal(decideAgentDrip({ entry: officer, amount: 6, recipientBalance: 0, agentBalance: 20 }).ok, false);
  assert.equal(decideAgentDrip({ entry: null, amount: 5, recipientBalance: 0, agentBalance: 20 }).ok, false);
  assert.equal(decideAgentDrip({ entry: treasury, amount: 0, recipientBalance: 0, agentBalance: 20 }).ok, false);
  assert.equal(decideAgentDrip({ entry: treasury, amount: 5, recipientBalance: null, agentBalance: 20 }).ok, false);
  assert.equal(decideAgentDrip({ entry: treasury, amount: 5, recipientBalance: 0, agentBalance: NaN }).ok, false);
});
