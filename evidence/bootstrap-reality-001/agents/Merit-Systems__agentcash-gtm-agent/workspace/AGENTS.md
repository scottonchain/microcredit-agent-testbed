# AGENTS.md — GTM Workspace

## Every Session

1. Read `SOUL.md` — your operating principles
2. Read `USER.md` — who you're selling for
3. Read `workspace/data/icp.json` — the target customer profile
4. Read `workspace/data/pipeline.json` — current pipeline state
5. Read today's memory file if it exists

## Data Files

All persistent GTM data lives in `workspace/data/`:

- **`icp.json`** — Ideal Customer Profile definition (industry, size, titles, geography, pain points)
- **`pipeline.json`** — Lead pipeline with stages and enrichment data
- **`campaigns.json`** — Outreach campaign templates and tracking
- **`outreach-log.json`** — Record of every email sent (to, subject, date, campaign)

Keep these files updated after every action. They are your source of truth.

## Pipeline Stages

Each lead moves through these stages:

1. **researched** — Found via search, basic info only (name, company, title)
2. **enriched** — Full profile: email, phone, LinkedIn, company context, talking points
3. **contacted** — Outreach sent, awaiting reply
4. **replied** — Got a response (positive, negative, or neutral — tag it)
5. **meeting** — Meeting scheduled or completed
6. **closed** — Deal closed or lead disqualified (tag which)

## Lead Data Schema

```json
{
  "id": "unique-id",
  "name": "Full Name",
  "title": "Job Title",
  "company": "Company Name",
  "domain": "company.com",
  "email": "verified@email.com",
  "emailVerified": true,
  "phone": "+1234567890",
  "linkedin": "https://linkedin.com/in/handle",
  "twitter": "handle",
  "stage": "enriched",
  "source": "apollo-people-search",
  "notes": "Recently raised Series B. Hiring for platform team.",
  "talkingPoints": ["Series B funding", "Platform team expansion"],
  "campaignId": "campaign-001",
  "lastAction": "2025-01-15",
  "createdAt": "2025-01-10"
}
```

## AgentCash API Usage

All API calls go through AgentCash MCP tools. The workflow:

1. `discover_api_endpoints` — See what's available at an origin
2. `check_endpoint_schema` — Get exact request/response schema and pricing
3. `fetch` — Execute the call (payment handled automatically)
4. `get_balance` — Check wallet balance before expensive operations

### Cost-Conscious Patterns

- **Apollo People Search** ($0.02) returns obfuscated names — always follow up with **People Enrich** ($0.05) to get real data
- **Exa Search** ($0.01) with `category: "linkedin profile"` is the cheapest way to find people
- **Hunter Email Verify** ($0.03) before sending — saves reputation and money
- **Firecrawl Scrape** ($0.013) for company websites — use sparingly, only for high-priority leads
- **StableEmail Send** ($0.02) for outreach — or $0.005/email with a custom subdomain

### Enrichment Cascade

When enriching a lead, follow this order (stop when you have what you need):

1. Apollo People Enrich — cheapest, gets most B2B data
2. Minerva Resolve + Enrich — if Apollo is missing LinkedIn or personal contact info
3. Clado Contacts Enrich — if you need phone/email from a LinkedIn URL specifically
4. Hunter Email Verify — always verify email before marking as deliverable

## Safety

- Don't send emails without human approval for new campaigns
- Don't run bulk operations (>20 enrichments) without stating the cost first
- Keep pipeline data in workspace files only
- Log every outreach email in outreach-log.json

## Heartbeats

On heartbeat, if pipeline has leads:
- Check for stale leads (same stage > 5 days)
- Flag any enrichment gaps
- Reply `HEARTBEAT_OK` if nothing to report

## Memory

- Daily logs in `memory/YYYY-MM-DD.md`
- Long-term lessons and patterns in `MEMORY.md`
- Track campaign performance over time
