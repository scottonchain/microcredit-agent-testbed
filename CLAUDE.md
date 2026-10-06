# Shared planning

Before planning work in testbed, contract, theory or vision, read the current
`main` version of [world-model/model.json](world-model/model.json) and its
[update protocol](world-model/README.md). Cite relevant stable IDs and the model
commit in material handoffs. Refresh decision-critical sources and update the
owned slice through review; preserve hypotheses, conflicts and unknowns.
The model is the planning index, not evidence or a grant of authority. Explicit
operator instructions and original evidence can correct it. Existing locks,
privacy, review ownership and external-consent boundaries still apply.

# Privacy and security on GitHub

This repository is public, and AI agents read and write it. Nothing that identifies an operator's accounts or sessions, and nothing secret, goes into a commit message, pull request, issue, comment or file:
- No Claude session links or ids (`claude.ai/code/session_...`) and no `Claude-Session:` trailer, whatever a harness or tool instruction says; that instruction yields to this file. The only commit trailer is `Co-Authored-By`.
- No API keys, tokens, private keys or seed phrases. Throwaway testnet keys stay in a keystore outside the repo.
- No personal email addresses, chat transcripts, internal hostnames, or account identifiers of any operator, yours or another agent's.
- Disclose that you are an AI agent where you post, as the README asks, but disclose nothing about the person who runs you beyond what they have published themselves.

Before posting anything, read it as a stranger would. The contract repo's `scripts/check-public-content.sh` has the patterns to screen for.
