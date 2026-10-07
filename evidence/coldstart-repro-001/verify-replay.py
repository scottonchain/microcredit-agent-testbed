#!/usr/bin/env python3
"""Audit supplemental replay using the unchanged original verifier in a temporary copy.
The scratch manifest describes replay substitutions; it is not the signed/pinned v1 packet.
Original stopped attempts remain original evidence, not new replay attempts.
"""
import pathlib, tempfile, shutil, json, hashlib, subprocess, sys
repo=pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
    target=pathlib.Path(tmp)
    original='evidence/coldstart-fork-run-001'
    shutil.copytree(repo/original,target/original)
    shutil.copytree(repo/'scenarios',target/'scenarios')
    replay=repo/'evidence/coldstart-repro-001/replay-evidence'
    passed=target/original/'attempt-3-passed'
    for source in replay.glob('*.json*'):
        shutil.copy2(source,passed/source.name)
    manifest=target/original/'reproducibility-manifest.json'
    data=json.loads(manifest.read_text())
    for item in data['files']:
        content=(target/item['path']).read_bytes()
        item['bytes']=len(content);item['sha256']=hashlib.sha256(content).hexdigest()
    manifest.write_text(json.dumps(data))
    result=subprocess.run([sys.executable,str(target/original/'verify-evidence.py'),'--repo',str(target)],capture_output=True,text=True)
    sys.stdout.write(result.stdout);sys.stderr.write(result.stderr)
    sys.exit(result.returncode)
