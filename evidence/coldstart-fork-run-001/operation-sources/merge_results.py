import sys, uuid, subprocess, os, json, hashlib
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, '/workspace/microcredit-agent-testbed')
from coordination.run_lock import Lock

repo = Path('/workspace/work/cold-start/integration')
env = dict(os.environ, GIT_AUTHOR_NAME='Codex (AI)', GIT_COMMITTER_NAME='Codex (AI)',
           GIT_AUTHOR_EMAIL='5783027+scottonchain@users.noreply.github.com',
           GIT_COMMITTER_EMAIL='5783027+scottonchain@users.noreply.github.com')
def run(args, cwd=repo):
    return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()

audit = '''# Codex artifact audit: three cold-start fork communities

Codex (AI), 2026-10-07. Reviewed public evidence at commit
`17eb6df0b7ed5457b3a5a9bfaf4b0a21700d5835`, produced by Hermes with the unchanged
helper at `a5a4d951df7e18056dd870db16fd642331f0e8e8`.

**Verdict: the proposed ordinary fork claims pass the artifact audit.**
Execution and upstream provenance remain supplied by Hermes. This review checks
published artifacts independently; it supplies no independent live-node proof.

The reviewer checked all 292 journal digests and links, including the completion
checkpoint followed by 14 stop-impersonation cleanup records. All 59 successful
local mined transactions matched their recorded intents and receipts. Loan IDs
18, 19 and 20 came from those local receipts; each received the complete
1,000,000-unit principal, 2, 1 and 1 seconds after disbursement respectively.
Scenario lenders withdrew their full share positions. Every terminal scenario
actor had zero financial obligation, backing, dues, credit line and held budget.
Completed-loan histories and provider epochs changed.

Initial and final aggregate root USDC were exactly 20,000,000 units. The full
original pool snapshot remained unchanged: 15,000,000 assets/cash/token units,
15,000,000,000,000 existing shares, and Avery score and held budget 920,000.
The eight specific rejection checks matched their expected selectors. The first
two gas-guard attempts contained zero mined transactions; the passing attempt
changed only the local Anvil minimum-priority-fee setting.

All execution was on fork chain 31337, copying Base Sepolia block 47820167 and
hash `0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078`.
The fork node was reported stopped by Hermes. No live funds moved in these runs.

Internal modeled payment, the peer's one-USDC endowment and the compulsory cure
do not establish independent income, borrower reliability, actual default
behavior, economic fraud resistance or human benefit. No interest-boundary or
short-payment branch ran. CI-30 is still open. Live scenario execution, root's
live recovery and the separate five-USDC source return/redeposit remain open.
'''

lock = Lock('/workspace/microcredit-agent-testbed')
owner, execution = 'codex-' + uuid.uuid4().hex, 'run-' + uuid.uuid4().hex
head = lock.acquire(owner, execution)
try:
    lock.assert_owned(owner, head)
    run(['git', 'fetch', 'origin', 'main', 'codex/supplemental-fork-results-20261007', 'coldstart-fork-run-001-evidence'])
    run(['git', 'merge', '--ff-only', 'origin/main'])
    base = run(['git', 'rev-parse', 'HEAD'])
    run(['git', 'add', 'scenarios/cold-start-three-communities/README.md'])
    run(['git', 'commit', '-m', 'Document executed Anvil gas setting without relaxing guard'])
    run(['git', 'merge', '--no-ff', '05bb4606ae032017419d59667b8797b5c4318c70', '-m', 'Merge PR36: fork observations and actual first guest publication'])
    run(['git', 'merge', '--no-ff', '17eb6df0b7ed5457b3a5a9bfaf4b0a21700d5835', '-m', 'Integrate Hermes three-community fork evidence'])

    relative = 'evidence/coldstart-fork-run-001/codex-artifact-audit.md'
    (repo / relative).write_text(audit)
    path = repo / 'world-model/model.json'
    model = json.loads(path.read_text())
    assert model['model_version'] == '0.1.66'
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    model['model_version'], model['updated_at'] = '0.1.67', now
    audit_eid = 'ev:codex-three-community-fork-artifact-audit-20261007'
    model['evidence'].append({
        'id': audit_eid, 'kind': 'repository_artifact',
        'url': 'https://github.com/scottonchain/microcredit-agent-testbed/blob/main/' + relative,
        'locator': relative + '; original reviewed artifact commit17eb6df0b7ed5457b3a5a9bfaf4b0a21700d5835',
        'author_id': 'agent:codex', 'observer_id': 'agent:codex',
        'published_at': now, 'retrieved_at': now,
        'summary': 'Codex independently checked the published fork artifacts: all292 journal links/digests, completion checkpoint and14 cleanup records,59 matching local receipts/intents, full1-USDC repayments and lender withdrawals, all actor financial positions cleared, exact20-USDC recovery, unchanged original15-USDC pool snapshot and Avery920000. Eight specific rejection checks matched. No material discrepancy; execution/upstream provenance remain Hermes-supplied, not independent live-node proof.',
        'content_sha256': hashlib.sha256(audit.encode()).hexdigest(),
        'fingerprint_scope': 'Raw UTF-8 codex-artifact-audit.md bytes',
        'origin_group': 'hermes-three-community-fork-run-001',
        'derived_from_ids': ['ev:hermes-three-community-fork-artifact-20261007'],
        'limitations': ['Independent artifact checking does not create another execution witness or establish live-node/source provenance.', 'Fork execution does not settle live recovery or source return/redeposit.', 'Controlled internal payments and compulsory cure establish no independent income, reliability, default behavior, fraud resistance or human benefit.']
    })
    claim = next(c for c in model['claims'] if c['id'] == 'claim:codex-three-community-fork-result-20261007')
    old = 'Root’s receipt/journal audit is pending; this is reported supplemental execution, not independent validation or primary live completion.'
    assert old in claim['statement']
    claim['statement'] = claim['statement'].replace(old, 'The subsequent Codex internal artifact audit passed all292 linked records,59 receipts and recovery checks without material discrepancy. Execution and upstream provenance are still Hermes-supplied; independent artifact checking is not independent live-node proof or primary live completion.')
    claim['epistemics']['supporting_evidence_ids'].append(audit_eid)
    claim['epistemics']['rationale'] += ' Codex separately checked the published artifacts, not an independent execution or live node.'
    claim['freshness']['observed_at'] = now
    for evidence in model['evidence']:
        if evidence['id'] in ('ev:hermes-three-community-fork-receipt-20261007', 'ev:hermes-three-community-fork-artifact-20261007'):
            evidence['limitations'] = [s.replace('Root is reviewing the actual receipts and journal; this update records Hermes’s execution report and published artifacts, not a completed independent validation.', 'Codex subsequently checked the published receipts/journal and found no material discrepancy; source provenance and execution remain Hermes-supplied, without independent live-node proof.') for s in evidence['limitations']]
    action = next(a for a in model['actions'] if a['id'] == 'action:codex-three-cold-start-communities')
    action['deliverable'] = action['deliverable'].replace('root receipt/journal audit is pending.', 'Codex internal artifact audit passed without material discrepancy; execution/source provenance remain supplied by Hermes.')
    action['outcome_evidence_ids'].append(audit_eid)
    path.write_text(json.dumps(model, indent=2, ensure_ascii=False) + '\n')
    print(run(['python3', 'world-model/validate.py', '--check-schema']))
    print(run(['python3', '-m', 'unittest', 'discover', '-s', 'world-model', '-p', 'test_*.py']))
    run(['git', 'add', relative, 'world-model/model.json'])
    run(['git', 'commit', '-m', 'Record independent artifact audit with live validation still open'])
    run(['git', 'diff', '--check', base + '..HEAD'])
    print(run(['bash', '/workspace/microcredit-contract/scripts/check-public-content.sh', '--range', base + '..HEAD']))
    lock.assert_owned(owner, head)
    run(['git', 'push', 'origin', 'HEAD:main'])
    result = {'main': run(['git', 'rev-parse', 'HEAD']), 'base': base, 'model_version': '0.1.67', 'merged_pr': 36, 'artifact_audit': relative, 'fork_scenarios': 3, 'live_scenarios': 0}
    (Path('/workspace/work/cold-start') / 'results-integration-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
finally:
    lock.release(owner, head)
