# AgentCash GTM Agent

A sales and go-to-market agent that builds prospect lists, enriches leads with real data, monitors social signals, and sends personalized outreach. Powered by [AgentCash](https://agentcash.dev) pay-per-call APIs.

No API keys. No subscriptions. Fund your wallet with USDC and start selling.

## What It Does

**Prospect Discovery** — Finds companies and people matching your ideal customer profile using Apollo and Exa search.

**Lead Enrichment** — Fills in verified emails, phone numbers, LinkedIn profiles, company context, and talking points using Apollo, Minerva, Clado, and Hunter.

**Social Intelligence** — Monitors Twitter, Instagram, Reddit, and TikTok for buying signals — hiring posts, funding announcements, pain-point discussions.

**Company Research** — Scrapes company websites and searches news for personalization hooks.

**Outreach** — Drafts and sends personalized cold emails via StableEmail. No SMTP setup, no sender domain configuration.

**Pipeline Management** — Tracks every lead through stages (researched → enriched → contacted → replied → meeting → closed) with automated stale-lead detection.

## Setup

### 1. Get an AgentCash wallet

```bash
npx agentcash@latest onboard
```

This creates a wallet at `~/.agentcash/wallet.json` and gives you deposit addresses for USDC on Base and Solana.

### 2. Fund your wallet

Deposit USDC to your Base or Solana address. $10-20 is enough to build and contact a pipeline of 50+ leads.

### 3. Deploy on Pinata Agents

1. Fork this repo to your company's GitHub
2. Import it at [agents.pinata.cloud](https://agents.pinata.cloud)
3. Add your `X402_PRIVATE_KEY` secret (the private key from `~/.agentcash/wallet.json`)
4. Deploy

### 4. Configure your ICP

Edit `workspace/data/icp.json` with your target customer profile — industry, company size, target titles, geography, pain points, and disqualifiers.

### 5. Fill in USER.md

Tell the agent about yourself, your company, what you sell, and your outreach preferences in `workspace/USER.md`.

## Cost Estimates

All API calls are pay-per-request in USDC. No minimums, no monthly fees.

| Workflow | Estimated Cost |
|----------|---------------|
| Research 10 companies | ~$0.70 |
| Build 50-person prospect list | ~$2.50 |
| Full enrichment per lead | ~$0.09 |
| Verify 50 emails | ~$1.50 |
| Send 50 outreach emails | ~$1.00 |
| Full pipeline (50 leads, enriched + emailed) | ~$8-12 |

## Scheduled Tasks

| Task | Schedule | What it does |
|------|----------|-------------|
| Morning Pipeline Review | 9am weekdays | Summarizes pipeline status, flags stale leads and enrichment gaps |
| Social Signal Scan | 2pm weekdays | Checks top prospects for buying signals on social media |
| Weekly ICP Research | 10am Mondays | Finds 10 new companies matching ICP, adds to pipeline |

## Data APIs Used

| Provider | Via | What for |
|----------|-----|----------|
| Apollo | stableenrich.dev | People/company search and enrichment |
| Minerva | stableenrich.dev | Deep person identity and demographics |
| Clado | stableenrich.dev | Email/phone from LinkedIn profiles |
| Hunter | stableenrich.dev | Email deliverability verification |
| Exa | stableenrich.dev | Semantic web search, LinkedIn discovery |
| Firecrawl | stableenrich.dev | Website scraping for company context |
| Serper | stableenrich.dev | Google News for recent activity |
| StableSocial | stablesocial.dev | Twitter/Instagram/TikTok/Reddit data |
| StableEmail | stableemail.dev | Send outreach emails |

## File Structure

```
manifest.json                        # Agent config
workspace/
  SOUL.md                            # Agent personality and sales principles
  AGENTS.md                          # Workflow procedures and pipeline management
  IDENTITY.md                        # Agent identity
  TOOLS.md                           # API reference and pricing cheat sheet
  HEARTBEAT.md                       # Periodic monitoring tasks
  USER.md                            # Your profile and preferences
  data/
    icp.json                         # Ideal Customer Profile definition
    pipeline.json                    # Lead pipeline (source of truth)
    campaigns.json                   # Outreach templates and campaign tracking
    outreach-log.json                # Record of all emails sent
```

## Example Prompts

- "Find 20 Series A SaaS companies in the US with 50-200 employees"
- "Enrich the top 10 leads in my pipeline with verified emails"
- "Check what our top prospects are posting about on Twitter"
- "Draft personalized outreach for all enriched leads, referencing their recent funding round"
- "Show me pipeline stats — how many leads per stage?"
- "What's my wallet balance?"

## Requirements

- USDC balance on Base or Solana (deposit via the addresses from `npx agentcash@latest accounts`)
- An `X402_PRIVATE_KEY` secret configured in your Pinata Agent
