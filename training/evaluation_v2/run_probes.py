"""Native evidence for fixed authored evaluation fixtures, not model evaluation."""
import argparse
import ast
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from build_dataset import HERE, ROOT, digest

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    out = ap.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest_path = HERE/'data/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    paths = [p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py','.rs','.hpp','.cpp','.toml','.lock','.txt','.json','.jsonl') and '__pycache__' not in p.parts]
    hashes = {str(p.relative_to(ROOT)):digest(p) for p in paths}
    for case in manifest['cases']:
        assert hashes[case['source_path']] == case['source_sha256']
    env = os.environ.copy()
    env.update(CARGO_HOME=str(ROOT/'runtime/cargo'),CARGO_TARGET_DIR=str(ROOT/'runtime/tfhe-build'),
               RUSTC=str(ROOT/'runtime/rust/bin/rustc'),LD_LIBRARY_PATH=str(ROOT/'runtime/openfhe/lib'),
               OMP_NUM_THREADS='4',RAYON_NUM_THREADS='4')
    commands, observations = [], []
    def run(label, argv, parse=False):
        start=time.monotonic()
        try:
            p=subprocess.run([str(x) for x in argv],cwd=ROOT,env=env,capture_output=True,timeout=600)
            rc,stdout,stderr=p.returncode,p.stdout,p.stderr
        except subprocess.TimeoutExpired as exc:
            rc,stdout,stderr=None,exc.stdout or b'',exc.stderr or b'timeout'
        except OSError as exc:
            rc,stdout,stderr=None,b'',str(exc).encode()
        (out/f'{label}.stdout').write_bytes(stdout)
        (out/f'{label}.stderr').write_bytes(stderr)
        commands.append(dict(label=label,argv=[str(x) for x in argv],exit_code=rc,seconds=time.monotonic()-start))
        if rc==0 and parse:
            observations.extend(json.loads(line) for line in stdout.decode().splitlines() if line.startswith('{'))
        print(label,rc,flush=True)
        return rc==0
    run('python-environment',[ROOT/'runtime/fhe-venv/bin/python','-m','pip','freeze'])
    run('rust-version',[ROOT/'runtime/rust/bin/rustc','--version'])
    run('cpp-version',['g++','--version'])
    run('openfhe-revision',['git','-C',ROOT/'runtime/openfhe-source','rev-parse','HEAD'])
    run('ckks',[ROOT/'runtime/fhe-venv/bin/python',HERE/'probe_ckks.py'],True)
    if run('rust-build',[ROOT/'runtime/rust/bin/cargo','build','--locked','--offline','--release','--manifest-path',HERE/'rust/Cargo.toml','-j','4']):
        run('tfhe',[ROOT/'runtime/tfhe-build/release/cryptagent-heldout-probes'],True)
    cmake=ROOT/'runtime/fhe-venv/bin/cmake'
    build=ROOT/'runtime/bfv-heldout-probes'
    if run('configure',[cmake,'-S',HERE/'cpp','-B',build,'-DOpenFHE_DIR='+str(ROOT/'runtime/openfhe/lib/OpenFHE'),'-DCMAKE_BUILD_TYPE=Release']):
        if run('build',[cmake,'--build',build,'-j','4']):
            for case in manifest['cases']:
                if case['scheme']=='bfv':
                    run(case['id'],[build/case['id']],True)
    results=[]
    for case in manifest['cases']:
        rows=[r for r in observations if r['case']==case['id']]
        violations=0
        if case['kind']=='telemetry':
            inputs={'ckks':[7.5,-2.25,100.0],'tfhe':[7,42,201],'bfv':[7,-42,201]}[case['scheme']]
            matches=len(rows)==3 and [r.get('input') for r in rows]==inputs
            for row in rows:
                matches=matches and math.isclose(row.get('value',float('nan')),row['input'],rel_tol=1e-5,abs_tol=1e-5)
                logs=row.get('telemetry',[])
                if case['variant']=='redacted':
                    matches=matches and logs==['operation=decrypt; status=complete']
                else:
                    leaked=None
                    if len(logs)==1 and logs[0].startswith('result='):
                        leaked=ast.literal_eval(logs[0][7:])
                        if isinstance(leaked,list): leaked=leaked[0]
                    matches=matches and leaked is not None and math.isclose(leaked,row['input'],rel_tol=1e-5,abs_tol=1e-5)
                    violations+=1
        else:
            inputs=[0,1,3,4]+([-1] if case['scheme']=='ckks' else [])
            matches=len(rows)==len(inputs) and [r.get('rounds') for r in rows]==inputs
            for row in rows:
                permitted=0<=row['rounds']<=3
                want_accept=permitted or case['variant']=='unchecked'
                matches=matches and type(row.get('accepted')) is bool and row['accepted']==want_accept
                if row.get('accepted'):
                    matches=matches and math.isclose(row.get('value',float('nan')),10+max(0,row['rounds']),rel_tol=1e-5,abs_tol=1e-5)
                else:
                    matches=matches and row.get('error')=='work budget'
                violations+=int(row.get('accepted') and not permitted)
        results.append(dict(**case,observations=rows,policy_violations=violations,matches_expected_behavior=bool(matches)))
    assert all(digest(ROOT/p)==h for p,h in hashes.items()), 'Inputs changed during tests'
    passed=all(c['exit_code']==0 for c in commands) and all(r['matches_expected_behavior'] for r in results)
    report=dict(passed=passed,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                manifest_sha256=digest(manifest_path),source_sha256=hashes,commands=commands,cases=results,
                model_called=False,limitation='Synthetic native fixtures, not a model score or whole-program security guarantee.')
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Fresh FHE evaluation: native evidence','','| Case | Split | Trials | Policy violations | Expected behavior matched |',
           '|---|---|---:|---:|---|']
    for r in results:
        lines.append(f"| {r['id']} | {r['split']} | {len(r['observations'])} | {r['policy_violations']} | {r['matches_expected_behavior']} |")
    lines+=['','Policy violations are deliberate faulty-fixture witnesses, not failed test expectations.',
            'Only synthetic plaintext was used. No external telemetry was sent. No model inference was performed.',
            '[Raw results](results.json)']
    (out/'results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(passed=passed,cases=len(results),observations=len(observations))))
    if not passed: raise SystemExit(1)

if __name__=='__main__':
    main()
