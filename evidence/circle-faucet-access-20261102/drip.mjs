// drip.mjs: send a fixed amount of test USDC from the team test wallet to one address on Base Sepolia.
// DRAFT for the steward's review (evidence/circle-faucet-access-20261102). It becomes live only when a
// reviewed merge places drip-workflow.draft.yml under .github/workflows and points its copy step at this file.
// Environment: RECIPIENT (required), TEST_WALLET_PRIVATE_KEY (absent: dry run, read-only), RPC_URL,
// AMOUNT_USDC (default 5), MAX_RECIPIENT_USDC (default 5: refuse when the recipient already holds this much),
// FLOOR_USDC (default 50: refuse when the team wallet would fall below it). Exit 0 sent or dry run, 3 refused, 2 bad input.
import { JsonRpcProvider, Wallet, Contract, isAddress, getAddress, parseUnits, formatUnits } from 'ethers';

const USDC = '0x036CbD53842c5426634e7929541eC2318f3dCF7e';
const TEAM = '0x38e9845A1Df22c59Bfc693bf2CEAa3361158d6d1';
const RPC = process.env.RPC_URL || 'https://base-sepolia-rpc.publicnode.com';
const abi = ['function balanceOf(address) view returns (uint256)', 'function transfer(address,uint256) returns (bool)'];

const raw = process.env.RECIPIENT || '';
if (!isAddress(raw)) { console.error('RECIPIENT is not a valid address'); process.exit(2); }
const recipient = getAddress(raw);
const amount = parseUnits(process.env.AMOUNT_USDC || '5', 6);
const maxRecipient = parseUnits(process.env.MAX_RECIPIENT_USDC || '5', 6);
const floor = parseUnits(process.env.FLOOR_USDC || '50', 6);

const provider = new JsonRpcProvider(RPC, undefined, { batchMaxCount: 1 });
const net = await provider.getNetwork();
if (Number(net.chainId) !== 84532) { console.error(`wrong chain ${String(net.chainId)}`); process.exit(2); }
const usdc = new Contract(USDC, abi, provider);
const [recBal, teamBal, block] = await Promise.all([usdc.balanceOf(recipient), usdc.balanceOf(TEAM), provider.getBlockNumber()]);
const plan = { block, recipient, recipientUsdc: formatUnits(recBal, 6), teamUsdc: formatUnits(teamBal, 6), amountUsdc: formatUnits(amount, 6) };
const refuse = (why) => { console.log(JSON.stringify({ ...plan, refused: why })); process.exit(3); };
if (recipient.toLowerCase() === TEAM.toLowerCase()) refuse('recipient is the team wallet');
if (recBal >= maxRecipient) refuse('recipient already holds the cap');
if (teamBal - amount < floor) refuse('team wallet would fall below the floor');

const key = process.env.TEST_WALLET_PRIVATE_KEY;
if (!key) { console.log(JSON.stringify({ ...plan, dryRun: true })); process.exit(0); }
const wallet = new Wallet(key, provider);
if (wallet.address.toLowerCase() !== TEAM.toLowerCase()) { console.error('the key does not control the team wallet'); process.exit(2); }
const tx = await usdc.connect(wallet).transfer(recipient, amount);
console.log(JSON.stringify({ ...plan, hash: tx.hash, submitted: true }));
const receipt = await tx.wait(1);
console.log(JSON.stringify({ hash: receipt.hash, status: receipt.status, block: receipt.blockNumber }));
process.exit(receipt.status === 1 ? 0 : 1);
