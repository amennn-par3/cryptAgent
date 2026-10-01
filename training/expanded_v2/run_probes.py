"""Build/execute only the new authored fixtures and record all observations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import datetime

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args()
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((HERE/'data/manifest.json').read_text())
    files=[HERE/'probe_ckks.py',HERE/'rust/Cargo.toml',HERE/'rust/Cargo.lock',HERE/'rust/src/main.rs',
        HERE/'cpp/CMakeLists.txt',HERE/'cpp/main.cpp',HERE/'cpp/delegate.cpp']+[ROOT/c['source_path'] for c in manifest['new_cases']]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for c in manifest['new_cases']: assert hashes[c['source_path']]==c['source_sha256']
    env=os.environ.copy(); env.update(CARGO_HOME=str(ROOT/'runtime/cargo'),CARGO_TARGET_DIR=str(ROOT/'runtime/tfhe-build'),
        RUSTC=str(ROOT/'runtime/rust/bin/rustc'),LD_LIBRARY_PATH=str(ROOT/'runtime/openfhe/lib'),RAYON_NUM_THREADS='4',OMP_NUM_THREADS='4')
    runs=[]; observed={}
    def run(label,argv,parse=False):
        start=time.monotonic()
        try:
            proc=subprocess.run([str(x) for x in argv],cwd=ROOT,env=env,capture_output=True,timeout=600)
            rc,stdout,stderr=proc.returncode,proc.stdout,proc.stderr
        except subprocess.TimeoutExpired as exc: rc,stdout,stderr=None,exc.stdout or b'',exc.stderr or b'timeout'
        except OSError as exc: rc,stdout,stderr=None,b'',str(exc).encode()
        (out/f'{label}.stdout').write_bytes(stdout); (out/f'{label}.stderr').write_bytes(stderr)
        runs.append({'label':label,'argv':[str(x) for x in argv],'exit_code':rc,'seconds':time.monotonic()-start})
        if parse and rc==0:
            for line in stdout.decode().splitlines():
                if line.startswith('{'):
                    record=json.loads(line); assert record['case'] not in observed
                    observed[record['case']]=record
        print(label,rc,flush=True); return rc==0
    run('python-environment',[ROOT/'runtime/fhe-venv/bin/python','-m','pip','freeze'])
    run('rust-version',[ROOT/'runtime/rust/bin/rustc','--version'])
    run('cpp-version',['g++','--version'])
    run('openfhe-revision',['git','-C',ROOT/'runtime/openfhe-source','rev-parse','HEAD'])
    run('ckks',[ROOT/'runtime/fhe-venv/bin/python',HERE/'probe_ckks.py'],True)
    if run('rust-build',[ROOT/'runtime/rust/bin/cargo','build','--locked','--offline','--release','--manifest-path',HERE/'rust/Cargo.toml','-j','4']):
        run('tfhe',[ROOT/'runtime/tfhe-build/release/cryptagent-batch-probes'],True)
    cmake=ROOT/'runtime/fhe-venv/bin/cmake'; build=ROOT/'runtime/bfv-batch-probes'
    if run('bfv-configure',[cmake,'-S',HERE/'cpp','-B',build,'-DOpenFHE_DIR='+str(ROOT/'runtime/openfhe/lib/OpenFHE'),'-DCMAKE_BUILD_TYPE=Release']):
        if run('bfv-build',[cmake,'--build',build,'-j','4']):
            for variant in ('any','all'): run('bfv-'+variant,[build/f'bfv_batch_{variant}'],True)
            observed['bfv_batch_delegate']={'case':'bfv_batch_delegate','status':'not_run_missing_validation_callback','syntax':'compiled'}
    rows=[]
    for case in manifest['new_cases']:
        result=observed.get(case['id']); matches=False
        if result and case['variant']=='delegate': matches=result.get('status')=='not_run_missing_validation_callback'
        elif result:
            trials=result.get('observations',[])
            expected_scenarios={'valid','one_modified','both_modified'} | ({'short'} if case['scheme']!='bfv' else set())
            assert len(trials)==len(expected_scenarios)*3
            assert {t['scenario'] for t in trials}==expected_scenarios
            assert all(type(t['accepted']) is bool for t in trials)
            mismatches=[t for t in trials if t['accepted']!=t['expected_acceptance']]
            matches=(not mismatches) if case['variant']=='all' else len(mismatches)==3 and all(t['scenario']=='one_modified' and t['accepted'] for t in mismatches)
        rows.append({**case,'observation':result,'matches_authored_expectation':matches})
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items()),'Inputs changed during execution'
    report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':hashlib.sha256((HERE/'data/manifest.json').read_bytes()).hexdigest(),
        'input_sha256':hashes,'commands':runs,'cases':rows,'model_called':False,
        'limitation':'Concrete fixture behavior only. Incomplete callback cases are not executed or treated as secure.'}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    text=['# Step 1: FHE batch-result witnesses','', '| Case | Label | Runtime observations | Evidence matches label |','|---|---|---|---|']
    for row in rows:
        obs=row['observation'] or {}; trials=obs.get('observations',[])
        status=f"{len(trials)} input scenarios; {sum(t['accepted']!=t['expected_acceptance'] for t in trials)} policy violations" if trials else obs.get('status','not completed')
        text.append(f"| {row['id']} | {row['target_assessment']} | {status} | {row['matches_authored_expectation']} |")
    text+=['','No training or model inference was run. Old test data was not modified.','[Raw results and command logs](results.json)']
    (out/'results.md').write_text('\n'.join(text)+'\n')
    print(json.dumps({'cases':len(rows),'matches':sum(r['matches_authored_expectation'] for r in rows),'out':str(out)},indent=2))
    if not all(r['matches_authored_expectation'] for r in rows): raise SystemExit(1)

if __name__=='__main__': main()
