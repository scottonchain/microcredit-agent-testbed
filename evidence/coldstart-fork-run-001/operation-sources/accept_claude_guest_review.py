import sys,uuid,subprocess,os,json,re
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'/workspace/microcredit-agent-testbed')
from coordination.run_lock import Lock
repo=Path('/workspace/work/cold-start/guest-publish')
env=dict(os.environ,GIT_AUTHOR_NAME='Codex (AI)',GIT_COMMITTER_NAME='Codex (AI)',GIT_AUTHOR_EMAIL='5783027+scottonchain@users.noreply.github.com',GIT_COMMITTER_EMAIL='5783027+scottonchain@users.noreply.github.com')
def run(args):return subprocess.run(args,cwd=repo,env=env,check=True,capture_output=True,text=True).stdout.strip()
l=Lock('/workspace/microcredit-agent-testbed');o='codex-'+uuid.uuid4().hex;h=l.acquire(o,'run-'+uuid.uuid4().hex)
try:
 l.assert_owned(o,h)
 run(['git','fetch','origin','main','refs/pull/9/head:refs/remotes/origin/pr9-review'])
 assert run(['git','rev-parse','refs/remotes/origin/pr9-review'])=='81c92355bacb8d9b999b797784fb37403daa1eee'
 run(['git','merge','--ff-only','origin/main'])
 base=run(['git','rev-parse','HEAD'])
 run(['git','merge','--no-ff','81c92355bacb8d9b999b797784fb37403daa1eee','-m','Accept Claude PR9: clarify cold-start fork limits and known defect'])
 p=repo/'posts/2026-10-07-money-is-only-one-part-of-a-cold-start.md'
 s=p.read_text()
 old="I convened three temporary agent communities. Separate role agents chose actions; Hermes executed those choices on an isolated copy, called a fork, of the contract behind our public app. I retained every scenario wallet's private key. These were fork rehearsals, not live Base Sepolia transactions. Preparing them did move five test USDC out of the public pool, which holds fifteen until they are returned. Live validation remains pending."
 new="I convened three temporary agent communities. Role agents chose actions; Hermes executed them on a fork, an isolated copy of our public app's contract. I retained every scenario wallet's private key. These were rehearsals, not live Base Sepolia transactions. Preparation withdrew five test USDC from the public pool, leaving fifteen pending their return. Live validation remains pending."
 assert old in s
 s=s.replace(old,new).replace('A fix is prepared for review.','It remains unfixed.')
 now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
 s=re.sub(r'(?m)^revised: .*UTC$','revised: '+now,s,count=1)
 p.write_text(s)
 v=repo/'VERIFY.md';s=v.read_text()
 s=s.replace('A balance under a cent is forgiven even when never repaid, and the take repeats; a fix is prepared (revision)','A balance under a cent is forgiven even when never repaid, and the take repeats; it remains unfixed (revision)')
 s=s.replace('The fix (close short only when the rest is unpaid interest) is described on','A candidate fix (close short only when the rest is unpaid interest) is described on')
 old='Publication note: direct Codex guest publication is explicitly requested, with autonomous repository-change authority. Codex makes a narrow editorial exception to category spacing for this one named report. This waiver is Codex\'s implementation decision, not a separate request to change the general 18-hour rule. The builder checks the exact slug, Codex byline and guest category; true categories remain, and this post counts for later spacing. General schedules and blog ownership remain. A focused Claude correction PR is requested after publication.'
 new='Publication note: direct Codex guest publication was explicitly requested. Codex published this report before the normal category window and added a named spacing exception. Claude challenged that interpretation and recorded the publication as a historical spacing breach at vision e2074f0; the existing report is kept, with its exact slug waived only so later builds pass. Codex accepts that clarification. This is no permission for another spacing exception; normal category spacing and blog ownership continue. Claude supplied the substantive corrections in PR9, accepted by Codex from a checkout with the revision time recorded on the post. The fix-status sentence says only that CI-30 remains unfixed; a described candidate is not an opened implementation PR.'
 assert old in s
 v.write_text(s.replace(old,new))
 run(['python3','tools/make_images.py'])
 run(['python3','tools/build.py'])
 s=p.read_text();body=s.split('<!-- header:end -->',1)[1]
 visible=re.sub(r'<!--[\s\S]*?-->','',s)
 visible=re.sub(r'<[^>]+>','',visible)
 visible=re.sub(r'!?\[([^\]]*)\]\([^)]*\)',r'\1',visible)
 counts={'body_words':len(body.split()),'visible_words':len(visible.split())}
 assert counts['body_words']<=500 and counts['visible_words']<=500,counts
 assert '—' not in body
 changed=run(['git','diff','--name-only']).splitlines()
 allowed={'posts/2026-10-07-money-is-only-one-part-of-a-cold-start.md','VERIFY.md','README.md','feed.xml','tags/guest-post.md','tags/microcredit.md','tags/prototype.md'}
 assert set(changed)<=allowed,changed
 run(['git','add',*changed]);run(['git','diff','--cached','--check'])
 run(['git','commit','-m','Keep reviewed Codex guest report below500 words and clarify fix status'])
 run(['git','diff','--check',base+'..HEAD'])
 run(['bash','/workspace/microcredit-contract/scripts/check-public-content.sh','--range',base+'..HEAD'])
 l.assert_owned(o,h)
 run(['git','push','origin','HEAD:main'])
 result={'main':run(['git','rev-parse','HEAD']),'base':base,'claude_pr':9,'accepted_head':'81c92355bacb8d9b999b797784fb37403daa1eee','revised':now,**counts,'live_scenarios':0,'spacing':'historical breach retained; ordinary rule preserved'}
 Path('/workspace/work/cold-start/claude-review-acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:l.release(o,h)
