// node --test scripts/test_circle_agent_rules.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { loadAllowlist } from './drip_rules.mjs';
import { extractRequestId, extractOtp, pickOtpMessages, parseAgentWallet, parseTransferId, decodeUsdc, decideAgentDrip } from './circle_agent_rules.mjs';

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

test('OTP candidates: after the request, from Circle, newest first', () => {
  const msgs = [
    { message_id: 'a', from: 'Circle <no-reply@circle.com>', subject: 'Your code', timestamp: '2026-11-02T20:00:30.000Z' },
    { message_id: 'b', from: 'Circle <no-reply@circle.com>', subject: 'Your code', timestamp: '2026-11-02T20:01:00.000Z' },
    { message_id: 'c', from: 'Hermes AI agent <hermes-909@agentmail.to>', subject: 'Transcript', timestamp: '2026-11-02T20:01:30.000Z' },
    { message_id: 'd', from: 'Circle <no-reply@circle.com>', subject: 'Old code', timestamp: '2026-11-02T19:00:00.000Z' },
  ];
  assert.deepEqual(pickOtpMessages(msgs, '2026-11-02T20:00:00.000Z').map((m) => m.message_id), ['b', 'a']);
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
});
