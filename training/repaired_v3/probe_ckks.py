import importlib.util
import json
from pathlib import Path

for variant in ("correct", "arithmetic", "acceptance", "secret", "setup", "bounds"):
    name = "ckks_" + variant
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent/"cases"/(name+".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trials = [(a,b,m) for a,b in [(3,4),(0,0),(100,100)] for m in [False,True]]
    trials += [(a,b,False) for a,b in [(-1,0),(101,0),(0,-1),(0,101)]]
    for left,right,modified in trials:
        try:
            result = dict(status="ok", **module.run_job(left,right,modified))
        except ValueError as exc:
            result = dict(status="input_rejected" if str(exc)=="input domain" else "setup_error", error=str(exc))
        print(json.dumps(dict(case=name,left=left,right=right,modified=modified,**result)),flush=True)
