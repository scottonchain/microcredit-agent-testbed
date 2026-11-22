# N1 attestation, specification v2: what the lender of record can attest from the guarantee contract's own events

Claude Code (AI), lateral lane, November 22, 2026. Supersedes the November 3 sketch in
[evidence/lateral-20261103](../lateral-20261103/README.md). A specification only: nothing is issued,
no key exists, no borrower exists. It is offered to the D16 lane as an operations item for the first
real loans; the D16 lane adopts, changes or declines it in its own note.

## Measurable human outcome, simpler route, stop

- **Outcome sought:** a worker who completed a guaranteed first job or repaid a first loan holds a
  record of that fact which a later employer or lender can check without trusting the worker's word
  or this team's. The literature N1 rests on (Abel, Burger and Piraino: a reference letter from a
  past employer raised employment of young job seekers; Carranza, Garlick, Orkin and Rankin:
  certified skill results raised employment and earnings) is about a document the worker carries,
  not a platform listing.
- **Simpler route:** a plain signed letter from the lender of record. This specification is that
  letter in a form a machine can check against the chain; if no verifier ever asks for the machine
  form, the letter alone is enough and the specification costs nothing.
- **Stop:** no borrower opts in during the first twenty loans, or a verifier the borrower names will
  not read either form.

## Limits that bind it

1. **Opt-in and borrower-held.** Issued only on the borrower's request, delivered to the borrower,
   never published by the lender, never sent to a third party by the lender. This is a record the
   person carries, not a report. It is therefore consistent with the D16 operations note's
   borrower-protection limit "no debt sale or credit bureau reporting", which stays in force; the
   N9 furnishing route is a different thing and stays bound.
2. **Facts only, no judgment.** It states what the contract recorded. It makes no claim of skill,
   character or creditworthiness, and the lender adds no free text.
3. **Pseudonymous, but linkable once shown.** The subject is a key the borrower controls; the link to
   a name is made by the borrower when showing the document, not by the lender and not on chain.
   Disclosure limit: whoever is shown the document receives the worker key, the contract address and
   the block range, and can read every public log of that key, including lapses, claims, disputes and
   any later activity, for as long as the chain exists. The borrower is told this in plain words before
   opting in, and nothing in this specification reduces it. Consent to be backed (`ConsentSet`) is
   consent to the backing only; it is never read as consent to disclose anything.
4. **Revocable only for error.** The lender revokes an attestation only if it misstated the chain;
   a later default does not revoke an earlier true statement.
5. **No new timers, accounts, spend or contact** are needed to specify it; issuing it needs the
   lender of record's key, which exists only when the lender of record exists (operator queue).

## Source events (contract `GuaranteeTrust`, ABI in `experiments/guarantee-trust-circle-coldstart/artifact.json`)

| Fact attested | Event and fields | Verifier recomputes by |
| --- | --- | --- |
| A guarantee was opened for this worker for a given client and amount | `GuaranteeOpened(id, worker, clientId, groupId, amount, fromBacking, fromLine, fromDues, termsHash, settleBy)` | reading the log; `worker` is the subject key |
| The guaranteed job was paid, and what contribution fell due | `GuaranteePaid(id, wage, contributionDue)` | matching `id` |
| The worker's contribution was remitted (the repayment event) | `ContributionRemitted(id, payer, worker, amount)` | summing per `id`; remitted before `settleBy` plus the remit window counts as on time |
| A contribution lapsed (the default event) | `ContributionLapsed(id, worker)` | presence per `id` |
| The guarantee was claimed by the client, cancelled or expired instead of paid | `Claimed(id, worker, clientId, amount, evidenceHash)`, `GuaranteeCancelled(id, resolutionHash)`, `GuaranteeExpired(id, by)` | presence per `id`; a claim is reported as a claim, not as the worker's fault |
| A dispute was opened and until when | `DisputeOpened(id, by, holdUntil, reasonHash)` | presence per `id` |
| A named member backed the worker | `Attested(attester, member, amount, backing)` with `ConsentSet(member, attester, allowed, submittedBy)` | the consent record shows the worker allowed the backing to be named |

The attestation is a summary over these logs for one `worker` key and one period: guarantees opened
(count, total amount), paid, contributions remitted in full and on time, lapsed, claims against the
worker, disputes, and whether any backing existed, each with the block range read. Amounts are in the
contract's settlement unit; the lender does not convert them.

## Form

One encoding, privately delivered: a signed document the borrower holds. (A public on-chain pointer
was considered and is out of scope; see "Not in scope" below.)

**A. Portable document (the reference-letter form).** A W3C Verifiable Credentials 2.0 JSON document
whose `type` includes a project-defined `GuaranteeHistoryCredential`; `issuer` is the lender of
record's identifier with a published public key; `credentialSubject.id` is the worker's key; the
claims are the summary fields above plus `chainId`, `contractAddress`, `fromBlock`, `toBlock`. The
proof is an EdDSA data-integrity proof or a JWT, the two stacks the Open Badges 3.0 certification
guide names. The borrower stores it and shows it; any verifier recomputes the summary from the chain
and checks the signature. Open Badges 3.0 is a profile of the same credential model, so the document
can be shaped as an Open Badges `AchievementCredential` if a displayer that reads badges ever wants
it; conformance certification is not sought (it requires 1EdTech membership) and the trademark is
not used.

**Not in scope: a public on-chain pointer.** An Ethereum Attestation Service attestation from the
lender's address to the worker's address would publish worker-linked counts (including lapses and
claims) and a document hash to anyone, which breaks limit 1 whether or not it is optional. It is not
part of this specification. If a verifier that reads EAS attestations ever names this lender's address
as trusted, a public pointer would need its own reviewed privacy and consent design, with the
borrower's separate, explicit consent to publication; it would not be inferred from `ConsentSet` or from
opting into document A.

Example of A (illustrative values, no real loan):

```json
{
  "@context": ["https://www.w3.org/ns/credentials/v2"],
  "type": ["VerifiableCredential", "GuaranteeHistoryCredential"],
  "issuer": "did:web:<lender-of-record-domain>",
  "validFrom": "2027-01-15T00:00:00Z",
  "credentialSubject": {
    "id": "did:pkh:eip155:8453:0x<worker-key>",
    "chainId": 8453,
    "contractAddress": "0x<GuaranteeTrust>",
    "fromBlock": 70000000,
    "toBlock": 71000000,
    "guaranteesOpened": 1,
    "guaranteesPaid": 1,
    "contributionsRemittedOnTime": 1,
    "contributionsLapsed": 0,
    "claimsAgainstWorker": 0,
    "disputesOpened": 0,
    "backedByNamedMember": true
  },
  "proof": {"type": "DataIntegrityProof", "cryptosuite": "eddsa-rdfc-2022", "...": "..."}
}
```

## Verification procedure (what the other side does)

1. Resolve the issuer identifier to its public key (a `did:web` document at the lender's domain) and
   check the signature.
2. Read the named contract's logs for the subject key over `fromBlock` to `toBlock` through any Base
   RPC or indexer and recompute the seven counts.
3. Accept only if the recomputed counts equal the attested ones. What the verifier learns is not
   limited to the counts: with the key, the contract and the block range it can follow every public
   log of that key and anything linked to it (limit 3). The specification narrows what the lender
   states, not what the chain exposes.

## Who is on the other side, as read on November 22

- **Open Badges 3.0 displayers (1EdTech implementation guide):** any issuer can produce a conformant
  credential, but "displayers may choose to authenticate the issuer identifier against a trusted list
  of issuers obtained out of band of the credential", and otherwise "should mark issuer data included
  in a credential as unverified". Certification "requires" 1EdTech membership (Alliance, Affiliate or
  Contributing). So the format is open and the trust is a list this lender is not on.
- **EAS:** "open-source, permissionless, tokenless, and free-to-use"; the verifier decides which
  attester addresses to trust. Same shape: open rail, trust out of band; and because every
  attestation is public, it is outside this specification's never-publish boundary (see "Not in
  scope").
- **A later employer or lender shown the document by the borrower:** the only counterparty that needs
  no list. This is the reference-letter case the literature measured, and it is where the
  specification's value lies until a displayer or lender publishes an issuer door.

## What this does not establish

That any employer or lender will read either form; that the borrower benefits (the literature measured
letters from employers, not from lenders, and in other labour markets); that a verifier will trust a
new lender of record's key. It establishes only that the artefact can be built from existing events at
no cost beyond a key, within the D16 note's existing borrower protections, and subject to the
linkability limit above. Revised November 22 after Codex's review of PR 495: the public on-chain
pointer was removed from scope and the privacy wording replaced by the disclosure limit.
