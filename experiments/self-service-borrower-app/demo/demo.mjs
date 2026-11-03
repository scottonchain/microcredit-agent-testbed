#!/usr/bin/env node
// D7 gate 2 demonstration: an account that holds no ETH borrows from the recorded
// Base Sepolia pool, sends the USDC on, and repays, with gas paid in USDC through
// Circle Paymaster v0.8 (EntryPoint v0.8) and an EIP-7702 simple smart account.
//
// Modes:
//   --dry-run  (default) read-only: chain, contracts, the account's credit, the
//              exact calldata of every step, bundler reachability. No signing.
//   --live     needs OWNER_PRIVATE_KEY (a throwaway testnet key, never committed),
//              test USDC on that address, and a reachable bundler. Submits user
//              operations. UNTESTED in the authoring session: it had no funded key
//              and the public bundler host was denied by network policy.
//
// Addresses come from deployments/current.json (pool, lens, token) and from
// Circle's published paymaster table (recorded in the D7 direction document).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import {
  createPublicClient, http, encodeFunctionData, parseAbi, parseUnits, formatUnits,
  encodePacked, maxUint256, hexToBigInt, getAddress,
} from "viem";
import { baseSepolia } from "viem/chains";
import { privateKeyToAccount, generatePrivateKey } from "viem/accounts";
import { createBundlerClient, toSimple7702SmartAccount } from "viem/account-abstraction";

const here = dirname(fileURLToPath(import.meta.url));
const deployment = JSON.parse(readFileSync(resolve(here, "../../../deployments/current.json"), "utf8"));
if (deployment.chain_id !== 84532) throw new Error(`expected Base Sepolia (84532), got ${deployment.chain_id}`);

const RPC_URL = process.env.RPC_URL ?? deployment.rpc_url;
const BUNDLER_URL = process.env.BUNDLER_URL ?? `https://public.pimlico.io/v2/${deployment.chain_id}/rpc`;
const POOL = getAddress(deployment.pool);
const LENS = getAddress(deployment.lens);
const USDC = getAddress(deployment.token.address);
const PAYMASTER_V08 = "0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966"; // Circle, Base Sepolia, EntryPoint v0.8
const AMOUNT = parseUnits(process.env.AMOUNT ?? "5", 6);
const RECIPIENT = process.env.RECIPIENT ? getAddress(process.env.RECIPIENT) : null;

const poolAbi = parseAbi([
  "function getBorrowLimit(address) view returns (uint256 limit, uint256 available)",
  "function getFreeCredit(address) view returns (uint256 credit, uint256 stake)",
  "function stakeOf(address) view returns (uint256)",
  "function grantedCredit(address) view returns (uint256)",
  "function getLoanRate() view returns (uint256)",
  "function totalAssets() view returns (uint256)",
  "function getBorrowerLoanIds(address) view returns (uint256[])",
  "function stake(uint256 amount)",
  "function requestLoan(uint256 amount) returns (uint256)",
  "function disburseLoan(uint256 loanId)",
  "function repayLoan(uint256 loanId, uint256 amount)",
  "event LoanRequested(address indexed borrower, uint256 indexed loanId, uint256 amount, uint256 term)",
]);
const lensAbi = parseAbi([
  "function getOutstandingRoundedToCent(uint256 loanId) view returns (uint256)",
  "function getUtilisation() view returns (uint256)",
]);
const erc20Abi = parseAbi([
  "function balanceOf(address) view returns (uint256)",
  "function approve(address spender, uint256 amount) returns (bool)",
  "function transfer(address to, uint256 amount) returns (bool)",
  "function nonces(address) view returns (uint256)",
  "function name() view returns (string)",
  "function version() view returns (string)",
  "function permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)",
]);

const client = createPublicClient({ chain: baseSepolia, transport: http(RPC_URL) });
const live = process.argv.includes("--live");
const usd = (v) => `${formatUnits(v, 6)} USDC`;

async function codeSize(address) {
  const code = await client.getCode({ address });
  return code ? (code.length - 2) / 2 : 0;
}

async function probeBundler() {
  try {
    const r = await fetch(BUNDLER_URL, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_supportedEntryPoints", params: [] }),
    });
    const text = await r.text();
    return { http: r.status, body: text.slice(0, 200) };
  } catch (e) {
    return { error: String(e.cause?.message ?? e.message) };
  }
}

function plannedCalls(account, loanId = 0n, owed = 0n) {
  // Each step is one user operation; the paymaster pays its gas in USDC.
  return [
    { step: "1 approve stake", to: USDC, data: encodeFunctionData({ abi: erc20Abi, functionName: "approve", args: [POOL, AMOUNT] }) },
    { step: "1 stake own USDC as credit", to: POOL, data: encodeFunctionData({ abi: poolAbi, functionName: "stake", args: [AMOUNT] }) },
    { step: "2 request loan", to: POOL, data: encodeFunctionData({ abi: poolAbi, functionName: "requestLoan", args: [AMOUNT] }) },
    { step: "3 disburse loan <id from LoanRequested>", to: POOL, data: encodeFunctionData({ abi: poolAbi, functionName: "disburseLoan", args: [loanId] }) },
    { step: "4 send the borrowed USDC", to: USDC, data: encodeFunctionData({ abi: erc20Abi, functionName: "transfer", args: [RECIPIENT ?? account, AMOUNT] }) },
    { step: "5 approve repayment <outstanding from lens>", to: USDC, data: encodeFunctionData({ abi: erc20Abi, functionName: "approve", args: [POOL, owed] }) },
    { step: "5 repay", to: POOL, data: encodeFunctionData({ abi: poolAbi, functionName: "repayLoan", args: [loanId, owed] }) },
  ];
}

async function dryRun() {
  const key = process.env.OWNER_PRIVATE_KEY ?? generatePrivateKey();
  const owner = privateKeyToAccount(key);
  const account = owner.address;
  const [chainId, block, pmCode, poolCode, usdcBalance, limit, free, rate, assets, util, nonce] = await Promise.all([
    client.getChainId(), client.getBlockNumber(), codeSize(PAYMASTER_V08), codeSize(POOL),
    client.readContract({ address: USDC, abi: erc20Abi, functionName: "balanceOf", args: [account] }),
    client.readContract({ address: POOL, abi: poolAbi, functionName: "getBorrowLimit", args: [account] }),
    client.readContract({ address: POOL, abi: poolAbi, functionName: "getFreeCredit", args: [account] }),
    client.readContract({ address: POOL, abi: poolAbi, functionName: "getLoanRate" }),
    client.readContract({ address: POOL, abi: poolAbi, functionName: "totalAssets" }),
    client.readContract({ address: LENS, abi: lensAbi, functionName: "getUtilisation" }),
    client.readContract({ address: USDC, abi: erc20Abi, functionName: "nonces", args: [account] }),
  ]);
  const report = {
    mode: "dry-run (no signing, no sending)",
    chain: { id: chainId, block: block.toString(), rpc: RPC_URL },
    contracts: {
      pool: POOL, poolCodeBytes: poolCode, lens: LENS, usdc: USDC,
      circlePaymasterV08: PAYMASTER_V08, paymasterCodeBytes: pmCode,
    },
    account: {
      address: account, keySource: process.env.OWNER_PRIVATE_KEY ? "OWNER_PRIVATE_KEY" : "fresh random key, discarded",
      usdc: usd(usdcBalance), borrowLimit: usd(limit[0]), borrowAvailable: usd(limit[1]),
      freeCredit: usd(free[0]), stake: usd(free[1]), permitNonce: nonce.toString(),
      note: "a fresh account should show zero credit; staking its own USDC is what opens the first loan in this demo",
    },
    pool: { aprBps: rate.toString(), totalAssets: usd(assets), utilisationBps: util.toString() },
    amount: usd(AMOUNT),
    plannedUserOperations: plannedCalls(account),
    paymaster: {
      flow: "EIP-2612 permit on USDC to the paymaster (deadline MAX_UINT256), paymasterData = packed(0x00, usdc, permitAmount, signature); gas limits 200000 verification, 35000 postOp (Circle quickstart)",
      fee: "10% surcharge on gas, paid in USDC",
    },
    bundler: { url: BUNDLER_URL, probe: await probeBundler() },
    notClaimed: "No transaction, no funds, no demonstration of a person using it. A read-only readiness check.",
  };
  console.log(JSON.stringify(report, (_, v) => (typeof v === "bigint" ? v.toString() : v), 2));
}

async function liveRun() {
  // UNTESTED path (see header). Follows Circle's v0.8 quickstart shape.
  if (!process.env.OWNER_PRIVATE_KEY) throw new Error("--live needs OWNER_PRIVATE_KEY (throwaway testnet key)");
  const owner = privateKeyToAccount(process.env.OWNER_PRIVATE_KEY);
  const account = await toSimple7702SmartAccount({ client, owner });
  const [name, version] = await Promise.all([
    client.readContract({ address: USDC, abi: erc20Abi, functionName: "name" }),
    client.readContract({ address: USDC, abi: erc20Abi, functionName: "version" }).catch(() => "2"),
  ]);
  const paymaster = {
    async getPaymasterData() {
      const permitAmount = parseUnits("10", 6);
      const nonce = await client.readContract({ address: USDC, abi: erc20Abi, functionName: "nonces", args: [account.address] });
      const signature = await account.signTypedData({
        domain: { name, version, chainId: baseSepolia.id, verifyingContract: USDC },
        types: { Permit: [
          { name: "owner", type: "address" }, { name: "spender", type: "address" }, { name: "value", type: "uint256" },
          { name: "nonce", type: "uint256" }, { name: "deadline", type: "uint256" } ] },
        primaryType: "Permit",
        message: { owner: account.address, spender: PAYMASTER_V08, value: permitAmount, nonce, deadline: maxUint256 },
      });
      return {
        paymaster: PAYMASTER_V08,
        paymasterData: encodePacked(["uint8", "address", "uint256", "bytes"], [0, USDC, permitAmount, signature]),
        paymasterVerificationGasLimit: 200000n,
        paymasterPostOpGasLimit: 35000n,
        isFinal: true,
      };
    },
  };
  const bundler = createBundlerClient({
    account, client, paymaster,
    userOperation: {
      async estimateFeesPerGas({ bundlerClient }) {
        const { standard } = await bundlerClient.request({ method: "pimlico_getUserOperationGasPrice" });
        return { maxFeePerGas: hexToBigInt(standard.maxFeePerGas), maxPriorityFeePerGas: hexToBigInt(standard.maxPriorityFeePerGas) };
      },
    },
    transport: http(BUNDLER_URL),
  });
  const send = async (label, calls) => {
    const hash = await bundler.sendUserOperation({ account, calls, authorization: await owner.signAuthorization({ contractAddress: account.authorization.address, chainId: baseSepolia.id, nonce: await client.getTransactionCount({ address: owner.address }) }) });
    const receipt = await bundler.waitForUserOperationReceipt({ hash });
    console.log(label, "userOp", hash, "tx", receipt.receipt.transactionHash, receipt.success ? "ok" : "FAILED");
    return receipt;
  };
  const steps = plannedCalls(account.address);
  await send("stake", steps.slice(0, 2).map(({ to, data }) => ({ to, data })));
  const req = await send("requestLoan", [steps[2]].map(({ to, data }) => ({ to, data })));
  const ids = await client.readContract({ address: POOL, abi: poolAbi, functionName: "getBorrowerLoanIds", args: [account.address] });
  const loanId = ids[ids.length - 1];
  await send("disburse", [{ to: POOL, data: encodeFunctionData({ abi: poolAbi, functionName: "disburseLoan", args: [loanId] }) }]);
  await send("send", [{ to: USDC, data: encodeFunctionData({ abi: erc20Abi, functionName: "transfer", args: [RECIPIENT ?? owner.address, AMOUNT] }) }]);
  const owed = await client.readContract({ address: LENS, abi: lensAbi, functionName: "getOutstandingRoundedToCent", args: [loanId] });
  await send("repay", [
    { to: USDC, data: encodeFunctionData({ abi: erc20Abi, functionName: "approve", args: [POOL, owed] }) },
    { to: POOL, data: encodeFunctionData({ abi: poolAbi, functionName: "repayLoan", args: [loanId, owed] }) },
  ]);
  console.log("done; loan", loanId.toString(), "repaid", usd(owed), "request block", req.receipt.blockNumber.toString());
}

(live ? liveRun() : dryRun()).catch((e) => { console.error(e); process.exit(1); });
