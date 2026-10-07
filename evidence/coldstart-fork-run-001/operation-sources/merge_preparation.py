import sys,uuid,subprocess,os,json
sys.path.insert(0,"/workspace/microcredit-agent-testbed")
from coordination.run_lock import Lock
repo="/workspace/work/cold-start/integration"
env=dict(os.environ,GIT_AUTHOR_NAME="Codex (AI)",GIT_COMMITTER_NAME="Codex (AI)",GIT_AUTHOR_EMAIL="5783027+scottonchain@users.noreply.github.com",GIT_COMMITTER_EMAIL="5783027+scottonchain@users.noreply.github.com")
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True,env=env).stdout.strip()
l=Lock("/workspace/microcredit-agent-testbed");o="codex-"+uuid.uuid4().hex;h=l.acquire(o,"run-"+uuid.uuid4().hex)
try:
 l.assert_owned(o,h)
 run(["git","-C",repo,"fetch","origin","main"])
 run(["git","-C",repo,"merge","--ff-only","origin/main"])
 base=run(["git","-C",repo,"rev-parse","HEAD"])
 run(["git","-C",repo,"merge","--no-ff","a5a4d951df7e18056dd870db16fd642331f0e8e8","-m","Merge PR34: guarded cold-start fork preparation"])
 run(["git","-C",repo,"merge","--no-ff","7fac1bd96f1cd37f46d729a7a12a3fb73e91afc8","-m","Merge PR35: reconcile temporary cold-start source allocation"])
 run(["git","-C",repo,"diff","--check",base+"..HEAD"])
 subprocess.run(["bash","/workspace/microcredit-contract/scripts/check-public-content.sh","--range",base+"..HEAD"],cwd=repo,env=env,check=True)
 l.assert_owned(o,h)
 run(["git","-C",repo,"push","origin","HEAD:main"])
 print(json.dumps({"main":run(["git","-C",repo,"rev-parse","HEAD"]),"base":base,"prs":[34,35],"method":"checkout merges, explicit noreply identity, protected lease"}))
finally:l.release(o,h)
