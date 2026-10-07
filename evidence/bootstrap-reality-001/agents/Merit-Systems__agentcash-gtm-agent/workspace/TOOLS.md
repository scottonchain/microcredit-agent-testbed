# TOOLS.md — AgentCash API Reference

All data access runs through AgentCash MCP tools. No API keys needed — payment is automatic from your USDC wallet.

## Origins

| Origin | What it does | Key endpoints |
|--------|-------------|---------------|
| stableenrich.dev | People & company data | Apollo search/enrich, Minerva, Clado, Exa, Firecrawl, Hunter |
| stablesocial.dev | Social media data | Twitter/Instagram/TikTok/Reddit profiles, posts, followers |
| stableemail.dev | Email sending | Send emails, custom subdomains, inboxes |

## Quick Pricing Reference

| Action | Endpoint | Cost |
|--------|----------|------|
| Find companies | Apollo org-search | $0.02 |
| Find people | Apollo people-search | $0.02 |
| Enrich a person | Apollo people-enrich | $0.05 |
| Enrich a company | Apollo org-enrich | $0.05 |
| Find LinkedIn profiles | Exa search (category: linkedin profile) | $0.01 |
| Scrape a website | Firecrawl scrape | $0.013 |
| Web search | Exa search | $0.01 |
| Google News | Serper news | $0.04 |
| Verify email | Hunter email-verifier | $0.03 |
| Resolve person identity | Minerva resolve | $0.02 |
| Deep person enrich | Minerva enrich | $0.05 |
| Contact info from LinkedIn | Clado contacts-enrich | $0.20 |
| Social media profile | StableSocial (any) | $0.06 |
| Send email | StableEmail send | $0.02 |
| Send from subdomain | StableEmail subdomain/send | $0.005 |

## Cost Estimates for Common Workflows

- **Research 10 companies:** ~$0.20 (org-search) + ~$0.50 (org-enrich) = ~$0.70
- **Build 50-person prospect list:** ~$0.02 (search) + ~$2.50 (enrich 50) = ~$2.52
- **Full lead enrichment (1 person):** ~$0.05 (Apollo) + $0.03 (email verify) + $0.013 (company scrape) = ~$0.09
- **Send 50 outreach emails:** ~$1.00 (generic) or ~$0.25 (custom subdomain)
- **Full pipeline build (50 leads, enriched + emailed):** ~$8-12

## Important Patterns

- Apollo People Search returns obfuscated names. Always enrich with people-enrich to get real data.
- Verify org IDs with org-search before filtering people-search by organization_ids.
- StableSocial uses async 2-step: POST to trigger ($0.06) -> poll GET /api/jobs?token=... (free with SIWX).
- Exa with `category: "linkedin profile"` is the cheapest way to discover people ($0.01).
