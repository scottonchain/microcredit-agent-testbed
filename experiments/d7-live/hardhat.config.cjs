// Local fork of live Base Sepolia state for zero-cost simulation. Not a deploy tool.
module.exports = {
  solidity: '0.8.24',
  networks: {
    hardhat: {
      chainId: 84532,
      hardfork: 'cancun',
      chains: { 84532: { hardforkHistory: { london: 0, shanghai: 1, cancun: 2 } } },
      forking: { url: process.env.UPSTREAM_RPC || 'https://sepolia.base.org', ...(process.env.FORK_BLOCK ? { blockNumber: Number(process.env.FORK_BLOCK) } : {}) },
      accounts: { count: 4 },
      mining: { auto: true },
      allowUnlimitedContractSize: true,
    },
  },
};
