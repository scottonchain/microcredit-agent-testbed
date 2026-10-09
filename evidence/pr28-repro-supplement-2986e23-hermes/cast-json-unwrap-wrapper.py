#!/usr/bin/env python3
# Test-harness shim (not repo code): forge/cast 1.8.4 wraps --json output as {"schema_version","success","data",...};
# the 2986e23 rehearsal script expects the bare payload. Unwrap .data when the envelope is present, pass everything else through.
import subprocess, sys, json
REAL = "<FOUNDRY_1.8.4>/cast"
p = subprocess.run([REAL] + sys.argv[1:], capture_output=True, text=True)
out = p.stdout
if "--json" in sys.argv[1:] or "-j" in sys.argv[1:]:
    try:
        d = json.loads(out)
        if isinstance(d, dict) and "schema_version" in d and "data" in d:
            out = json.dumps(d["data"]) + "\n"
    except Exception:
        pass
sys.stdout.write(out)
sys.stderr.write(p.stderr)
sys.exit(p.returncode)
