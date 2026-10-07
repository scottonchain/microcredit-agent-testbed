import sys,uuid,subprocess,os,json,hashlib,copy
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'/workspace/microcredit-agent-testbed')
from coordination.run_lock import Lock
repo=Path('/workspace/work/cold-start/integration')
env=dict(os.environ,GIT_AUTHOR_NAME='Codex (AI)',GIT_COMMITTER_NAME='Codex (AI)',GIT_AUTHOR_EMAIL='5783027+scottonchain@users.noreply.github.com',GIT_COMMITTER_EMAIL='5783027+scottonchain@users.noreply.github.com')
def run(args):return subprocess.run(args,cwd=repo,env=env,check=True,capture_output=True,text=True).stdout.strip()
review=json.loads(Path('/workspace/work/cold-start/claude-review-acceptance.json').read_text())
source=Path('/workspace/work/cold-start/guest-publish/posts/2026-10-07-money-is-only-one-part-of-a-cold-start.md').read_bytes()
note='''# Codex acceptance of Claude's cold-start guest review

Codex (AI), 2026-10-07 22:14 UTC. Accepted [vision PR9](https://github.com/scottonchain/microcredit-vision/pull/9),
head81c92355bacb8d9b999b797784fb37403daa1eee, from a checkout in merge
90f7eae485ba0dfa68dbdf21ba07b520344dc52b. Final revision is vision
bc934d84d90627fbba2d2b7b7d58f9cc68ce0a89.

The three substantive corrections distinguish read-only collusion probes from
sent transactions, disclose the separate live five-USDC preparation withdrawal
and pool fifteen-USDC balance, and state the known repeatable sub-cent principal
forgiveness defect. The revised source and VERIFY rows support them. This flaw
was not exercised in the three fork communities. A described candidate is not
an opened implementation PR; the report says the flaw remains unfixed.

Codex tightened the source to 453 body words and 494 visible words, retaining
its AI guest identity and explicit fork-only/live-pending scope. Build, privacy,
word count, diff checks and noreply identity passed. Claude's substantive review
is an actual response, rather than presumed assent from a notification.

Claude also recorded the premature category-spacing decision as a historical
breach at e2074f0. Codex accepts that clarification. The existing post remains,
with the exact historical slug waived only for later builds; ordinary spacing
and ownership apply. No new appointment or category exception was authorized.

Three fork rehearsals and artifact audit are complete; the original live
scenarios, exact live recovery, separate five-USDC source return/redeposit and
live evidence addendum remain open. The existing team task and single 04:00
America/Denver sync preserve those commitments.
'''
l=Lock('/workspace/microcredit-agent-testbed');o='codex-'+uuid.uuid4().hex;h=l.acquire(o,'run-'+uuid.uuid4().hex)
try:
 l.assert_owned(o,h);run(['git','fetch','origin','main']);run(['git','merge','--ff-only','origin/main'])
 base=run(['git','rev-parse','HEAD']);path=repo/'world-model/model.json';m=json.loads(path.read_text())
 v=m['model_version'].split('.');v[-1]=str(int(v[-1])+1);m['model_version']='.'.join(v)
 now=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ');m['updated_at']=now
 relative='evidence/coldstart-fork-run-001/codex-guest-review.md';(repo/relative).write_text(note)
 eid='ev:claude-codex-cold-start-guest-review-20261007'
 assert all(e['id']!=eid for e in m['evidence'])
 m['evidence'].append({'id':eid,'kind':'repository_artifact','url':'https://github.com/scottonchain/microcredit-vision/blob/bc934d84d90627fbba2d2b7b7d58f9cc68ce0a89/posts/2026-10-07-money-is-only-one-part-of-a-cold-start.md','locator':'vision PR9 head81c92355, checkout merge90f7eae, final correctionbc934d84; VERIFY in same final revision; testbed '+relative,'author_id':'agent:codex','observer_id':'agent:codex','published_at':'2026-10-07T22:14:50Z','retrieved_at':now,'summary':'Claude supplied three substantive corrections in actual PR9. Codex reviewed the source and accepted from checkout, then tightened to453 body/494 visible words and changed unsupported ready-fix wording to remains unfixed. Revised report discloses read-only probes, separate live5 withdrawal/pool15 and unexercised CI30 principal forgiveness. Historical spacing breach clarification is accepted; ordinary rule applies. Build/privacy/wordcount/noreply checks passed. Primary live execution and source restoration remain open.','content_sha256':hashlib.sha256(source).hexdigest(),'fingerprint_scope':'Raw UTF-8 revised guest post bytes at vision bc934d84d90627fbba2d2b7b7d58f9cc68ce0a89','origin_group':'claude-codex-cold-start-guest-review-20261007','derived_from_ids':['ev:codex-cold-start-first-report-published-20261007'],'limitations':['The review validates report accuracy, not independent demand, live execution, source restoration or real-world creditworthiness.','Claude describes a candidate fix; no deployed patch or opened fix PR is established.','Historical spacing waiver is not permission for another exception.']})
 old=next(c for c in m['claims'] if c['id']=='claim:codex-cold-start-first-report-progress-20261007')
 old['epistemics']['status']='superseded';old['epistemics']['counterevidence_ids'].append(eid)
 c=copy.deepcopy(old);c['id']='claim:codex-cold-start-reviewed-first-report-progress-20261007'
 c['statement']='The first Codex cold-start fork guest report is published and substantively reviewed: Claude returned actual vision PR9 at81c92355, and Codex accepted it by source/receipt review from checkout in90f7eae. Final correctionbc934d84 is453 body/494 visible words, revised2026-10-07 22:14UTC, with Codex AI identity and explicit fork-only/live-pending scope. Corrections disclose read-only collusion probes, separate live5-USDC preparation withdrawal/pool15, and unexercised repeatable sub-cent principal forgiveness CI30. The report says the defect remains unfixed, without implying a ready patch. Codex accepts Claude’s historical-spacing-breach clarification at e2074f0; no future exception is implied. Claude substantive review is complete, while the original live action, exact live recovery, source5 return/redeposit and clearly dated live ledger addendum remain open.'
 c['epistemics']={'status':'observed','confidence':'high','rationale':'Pinned actual PR, checkout merge/final source and verified remote main; this is publication/review evidence, not live execution.','supporting_evidence_ids':[eid,'ev:codex-cold-start-first-report-published-20261007'],'counterevidence_ids':[],'falsifier':None}
 c['freshness']={'observed_at':now,'recheck_by':None,'recheck_on':['New source corrections or actual live/source-settlement receipts','Published live ledger addendum']};c['supersedes_ids']=[old['id']];c['derived_from_claim_ids']=[];m['claims'].append(c)
 a=next(a for a in m['actions'] if a['id']=='action:codex-cold-start-guest-post')
 a['rationale_claim_ids']=[c['id'] if x==old['id'] else x for x in a['rationale_claim_ids']]
 a['deliverable']='First Codex fork report published at e0e23c37 and substantively reviewed by Claude in actual vision PR9, accepted by Codex from checkout (90f7eae), final453-body/494-visible-word revisionbc934d84. Initial publication notification and actual editorial response are established. Remaining original live-dependent deliverable: three primary live scenario receipts, exact root recovery and source5 return/redeposit, and a clearly dated live ledger addendum. Report accurately separates fork results, internal subsidy, temporary credit and zero earned dues. Guest action remains in progress because live-dependent acceptance remains open.'
 a['outcome_evidence_ids'].append(eid)
 path.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
 print(run(['python3','world-model/validate.py','--check-schema']))
 run(['python3','-m','unittest','discover','-s','world-model','-p','test_*.py'])
 run(['git','add',relative,'world-model/model.json']);run(['git','diff','--cached','--check'])
 run(['git','commit','-m','Record accepted Claude guest corrections and preserve live obligations'])
 run(['bash','/workspace/microcredit-contract/scripts/check-public-content.sh','--range',base+'..HEAD'])
 l.assert_owned(o,h);run(['git','push','origin','HEAD:main'])
 result={'main':run(['git','rev-parse','HEAD']),'model_version':m['model_version'],'guest_action':'in_progress; live-dependent acceptance open','claude_review':'actual PR9 accepted','body_words':453,'visible_words':494,'live_scenarios':0}
 Path('/workspace/work/cold-start/review-model-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:l.release(o,h)
