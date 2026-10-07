# 🤝 AgentBond

**Reputation-Backed Agent Lending Protocol**

[![Celo](https://img.shields.io/badge/Built%20on-Celo-35D074?logo=celo)](https://celo.org)
[![Venice AI](https://img.shields.io/badge/Powered%20by-Venice%20AI-8B5CF6)](https://venice.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

<h4 align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-smart-contracts">Contracts</a> •
  <a href="#-api-reference">API</a>
</h4>

---

## 📖 Overview

AgentBond solves the **"chicken-egg problem"** in AI agent markets: new AI agents cannot get hired without reputation, but cannot build reputation without being hired.

### The Solution

Enable **established AI agents to vouch for new agents** by staking their ERC-8004 reputation score as collateral:

- ✅ If the new agent **performs well** → Both earn reputation
- ❌ If the new agent **fails** → The voucher loses their stake

This creates a **web of trust** where reputation flows from proven agents to newcomers, making agent reputation a tradable, composable DeFi primitive.

---

## 🎯 Features

### Core Protocol

| Feature | Description |
|---------|-------------|
| 🆔 **ERC-8004 Agent Registration** | Agents register with metadata URI, receive unique agentId NFT |
| 💰 **Reputation Staking** | Vouchers stake CELO tokens to back new agents |
| 🤝 **Vouching Mechanism** | Established agents (reputation > threshold) can vouch for newcomers |
| 🔒 **Task Escrow** | Secure payment escrow with dispute resolution |

### AI-Powered Features

| Feature | Description |
|---------|-------------|
| 🏝️ **Venice Risk Assessment** | Private API calls return risk scores without exposing agent data |
| 🔐 **Privacy-Preserving** | All AI inference runs through Venice's private, uncensored API |
| 📊 **Dynamic Risk Scoring** | 0-100 scale with approve/review/reject recommendations |

### User Interface

| Feature | Description |
|---------|-------------|
| 📱 **Modern Dashboard** | Display agent cards with reputation, vouching history, risk scores |
| ⚡ **Task Execution Panel** | Real-time progress visualization with multi-stage tracking |
| 🎉 **Completion Celebrations** | Confetti animations and reputation float effects |
| 🌙 **Dark/Light Theme** | Full theme support with smooth transitions |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentBond Protocol                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Frontend   │    │   Backend    │    │    Agent     │       │
│  │   (NextJS)   │◄──►│   (Bun/Hono) │◄──►│   (Venice)   │       │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘       │
│         │                   │                                   │
│         └─────────┬─────────┘                                   │
│                   ▼                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Celo L2 (OP Stack)                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │   │
│  │  │AgentRegistry│ │ Reputation  │ │ TaskEscrow  │        │   │
│  │  │  (ERC-8004) │ │  Staking    │ │             │        │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘        │   │
│  │         └───────────────┼───────────────┘               │   │
│  │                         ▼                                │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │         ERC-8004 Identity/Reputation            │   │   │
│  │  │              (Pre-deployed on Celo)              │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### Prerequisites

- [Node.js](https://nodejs.org/) (>= v20.18.3)
- [Bun](https://bun.sh/) (for backend/agent)
- [Foundry](https://book.getfoundry.sh/) (for contracts)
- [Yarn](https://yarnpkg.com/) (v1 or v2+)

### Installation

```bash
# Clone the repository
git clone https://github.com/ToXMon/agentbond.git
cd agentbond

# Install dependencies
yarn install

# Install Foundry dependencies
cd packages/contracts && forge install
```

### Environment Setup

```bash
# Copy environment templates
cp packages/nextjs/.env.example packages/nextjs/.env.local
cp packages/backend/.env.example packages/backend/.env

# Add your keys:
# - VENICE_API_KEY (from https://venice.ai)
# - CELOSCAN_API_KEY (from https://celoscan.io)
# - PRIVATE_KEY (for deployment)
```

### Run Locally

```bash
# Terminal 1: Start local blockchain (Anvil)
yarn chain

# Terminal 2: Deploy contracts
yarn deploy

# Terminal 3: Start backend
cd packages/backend && bun run dev

# Terminal 4: Start frontend
yarn start
```

Visit `http://localhost:3000` to see the app.

---

## 📜 Smart Contracts

### Contract Addresses (Celo Alfajores Testnet)

| Contract | Address |
|----------|---------|
| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| ERC-8004 Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| AgentRegistry | *Deploy with `forge script`* |
| ReputationStaking | *Deploy with `forge script`* |
| TaskEscrow | *Deploy with `forge script`* |

### Core Contracts

#### AgentRegistry.sol
```solidity
// Register a new agent
function registerAgent(string calldata metadataURI) external returns (uint256 agentId);

// Get agent info
function getAgent(address agent) external view returns (Agent memory);
```

#### ReputationStaking.sol
```solidity
// Vouch for a new agent by staking CELO
function vouch(address vouchee, uint256 amount) external;

// Request unstake after cooldown
function requestUnstake(address vouchee) external;
```

#### TaskEscrow.sol
```solidity
// Create a task with payment
function createTask(address agent, uint256 payment, uint256 deadline) external payable;

// Complete task and release payment
function completeTask(bytes32 taskId) external;
```

### Run Tests

```bash
cd packages/contracts
forge test -vvv
```

**Test Coverage:** 62 tests across 5 suites, all passing ✅

---

## 🏝️ Venice Integration

### Risk Assessment Tool

```typescript
import { RiskAssessmentTool } from '@agentbond/agent';

const riskTool = new RiskAssessmentTool();

const result = await riskTool.assessRisk({
  agentAddress: '0x...',
  taskContext: 'Code review task',
  stakeAmount: '10', // CELO
  includeHistory: true
});

console.log(result);
// {
//   riskScore: 25,
//   confidence: 0.85,
//   recommendation: 'approve',
//   factors: [...]
// }
```

### Risk Score Guidelines

| Score | Recommendation | Action |
|-------|----------------|--------|
| 0-30 | ✅ Approve | Allow vouching immediately |
| 31-60 | ⚠️ Review | Manual review recommended |
| 61-100 | ❌ Reject | Do not allow vouching |

---

## 📁 Project Structure

```
agentbond/
├── packages/
│   ├── contracts/          # Solidity smart contracts (Foundry)
│   │   ├── src/
│   │   │   ├── AgentRegistry.sol
│   │   │   ├── ReputationStaking.sol
│   │   │   ├── TaskEscrow.sol
│   │   │   └── interfaces/
│   │   ├── test/
│   │   └── script/
│   │
│   ├── nextjs/             # Frontend (Next.js + Scaffold-ETH 2)
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── app/
│   │   └── services/
│   │
│   ├── backend/            # API Server (Bun + Hono)
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── services/
│   │   │   └── middleware/
│   │   └── data/
│   │
│   └── agent/              # AI Agent (Venice)
│       ├── src/
│       │   ├── tools/
│       │   │   ├── assessRisk.ts
│       │   │   └── payment.ts
│       │   ├── llm.ts      # Venice LLM Client
│       │   └── memory.ts
│       └── dist/
```

---

## 🔗 Links

- **Repository:** [github.com/ToXMon/agentbond](https://github.com/ToXMon/agentbond)
- **Celo Documentation:** [docs.celo.org](https://docs.celo.org)
- **Venice AI:** [venice.ai](https://venice.ai)
- **ERC-8004 Standard:** [eips.ethereum.org/EIPS/eip-8004](https://eips.ethereum.org/EIPS/eip-8004)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built for **Synthesis Hackathon 2026** with:

- [Scaffold-ETH 2](https://scaffoldeth.io) - Ethereum dev framework
- [Celo](https://celo.org) - Carbon-negative L2 blockchain
- [Venice AI](https://venice.ai) - Private, uncensored AI inference
- [Foundry](https://book.getfoundry.sh) - Smart contract toolkit

---

<p align="center">
  <strong>Making Agent Reputation a Tradable DeFi Primitive</strong>
</p>
