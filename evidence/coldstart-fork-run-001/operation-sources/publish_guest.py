import sys,uuid,subprocess,os,json,re
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,"/workspace/microcredit-agent-testbed")
from coordination.run_lock import Lock
repo="/workspace/work/cold-start/guest-publish"
env=dict(os.environ,GIT_AUTHOR_NAME="Codex (AI)",GIT_COMMITTER_NAME="Codex (AI)",GIT_AUTHOR_EMAIL="5783027+scottonchain@users.noreply.github.com",GIT_COMMITTER_EMAIL="5783027+scottonchain@users.noreply.github.com")
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True,env=env).stdout.strip()
l=Lock("/workspace/microcredit-agent-testbed");o="codex-"+uuid.uuid4().hex;h=l.acquire(o,"run-"+uuid.uuid4().hex)
try:
 l.assert_owned(o,h)
 run(["git","-C",repo,"fetch","origin","main"])
 current=run(["git","-C",repo,"rev-parse","HEAD"]);remote=run(["git","-C",repo,"rev-parse","origin/main"])
 if current != remote: raise RuntimeError("Blog main changed; reconcile before publication")
 p=Path(repo)/"posts/2026-10-07-money-is-only-one-part-of-a-cold-start.md"
 now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
 p.write_text(re.sub(r"(?m)^date: .*UTC$","date: "+now,p.read_text(),count=1))
 subprocess.run(["python","tools/build.py"],cwd=repo,env=env,check=True,capture_output=True,text=True)
 files=["posts/2026-10-07-money-is-only-one-part-of-a-cold-start.md","images/cold-start-three-communities.svg","evidence/2026-10-07-cold-start-scenarios.md","VERIFY.md","README.md","feed.xml","tags/README.md","tags/guest-post.md","tags/microcredit.md","tags/prototype.md","tools/build.py","tools/make_images.py"]
 run(["git","-C",repo,"add",*files]);run(["git","-C",repo,"diff","--cached","--check"])
 run(["git","-C",repo,"commit","-m","Publish Codex guest report on three cold-start fork rehearsals"])
 subprocess.run(["bash","/workspace/microcredit-contract/scripts/check-public-content.sh","--range","HEAD~1..HEAD"],cwd=repo,env=env,check=True)
 l.assert_owned(o,h)
 run(["git","-C",repo,"push","origin","HEAD:main"])
 sha=run(["git","-C",repo,"rev-parse","HEAD"])
 result={"commit":sha,"date":now,"post":"https://github.com/scottonchain/microcredit-vision/blob/main/posts/2026-10-07-money-is-only-one-part-of-a-cold-start.md","ledger":"https://github.com/scottonchain/microcredit-vision/blob/main/evidence/2026-10-07-cold-start-scenarios.md","scope":"three verified fork rehearsals; live task pending"}
 Path("/workspace/work/cold-start/guest-publication-receipt.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
finally:l.release(o,h)
