"""Native tests of complete authored FHE workflows; never runs a model."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
VARIANTS=('correct','arithmetic','acceptance','secret','setup','bounds')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out.resolve(); out.mkdir(parents=True,exist_ok=False)
    files=[p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py','.rs','.hpp','.cpp','.toml','.lock','.txt') and '__pycache__' not in p.parts]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    env=os.environ.copy(); env.update(CARGO_HOME=str(ROOT/'runtime/cargo'),CARGO_TARGET_DIR=str(ROOT/'runtime/tfhe-build'),
        RUSTC=str(ROOT/'runtime/rust/bin/rustc'),LD_LIBRARY_PATH=str(ROOT/'runtime/openfhe/lib'),OMP_NUM_THREADS='4',RAYON_NUM_THREADS='4')
    commands=[]; observed=[]
    def run(label,argv,parse=False):
        start=time.monotonic()
        try:
            p=subprocess.run([str(x) for x in argv],cwd=ROOT,env=env,capture_output=True,timeout=600)
            rc,stdout,stderr=p.returncode,p.stdout,p.stderr
        except subprocess.TimeoutExpired as exc:
            rc,stdout,stderr=None,exc.stdout or b'',exc.stderr or b'timeout'
        except OSError as exc:
            rc,stdout,stderr=None,b'',str(exc).encode()
        (out/f'{label}.stdout').write_bytes(stdout); (out/f'{label}.stderr').write_bytes(stderr)
        commands.append(dict(label=label,argv=[str(x) for x in argv],exit_code=rc,seconds=time.monotonic()-start))
        if parse and rc==0:
            observed.extend(json.loads(line) for line in stdout.decode().splitlines() if line.startswith('{'))
        print(label,rc,flush=True); return rc==0
    run('python-environment',[ROOT/'runtime/fhe-venv/bin/python','-m','pip','freeze'])
    run('rust-version',[ROOT/'runtime/rust/bin/rustc','--version'])
    run('cpp-version',['g++','--version'])
    run('openfhe-revision',['git','-C',ROOT/'runtime/openfhe-source','rev-parse','HEAD'])
    run('ckks',[ROOT/'runtime/fhe-venv/bin/python',HERE/'probe_ckks.py'],True)
    if run('rust-build',[ROOT/'runtime/rust/bin/cargo','build','--locked','--offline','--release','--manifest-path',HERE/'rust/Cargo.toml','-j','4']):
        for variant in VARIANTS:
            run('tfhe-'+variant,[ROOT/'runtime/tfhe-build/release/cryptagent-repaired-probes',variant],True)
    cmake=ROOT/'runtime/fhe-venv/bin/cmake'; build=ROOT/'runtime/bfv-repaired-probes'
    if run('configure',[cmake,'-S',HERE/'cpp','-B',build,'-DOpenFHE_DIR='+str(ROOT/'runtime/openfhe/lib/OpenFHE'),'-DCMAKE_BUILD_TYPE=Release']):
        if run('build',[cmake,'--build',build,'-j','4']):
            for variant in VARIANTS: run('bfv-'+variant,[build/f'bfv_{variant}'],True)
    results=[]
    trials=[(a,b,m) for a,b in [(3,4),(0,0),(100,100)] for m in (False,True)]+[(a,b,False) for a,b in [(-1,0),(101,0),(0,-1),(0,101)]]
    for scheme in ('ckks','tfhe','bfv'):
        for variant in VARIANTS:
            name=scheme+'_'+variant
            rows=[r for r in observed if r['case']==name]
            matches=len(rows)==10 and [(r['left'],r['right'],r['modified']) for r in rows]==trials
            for r in rows:
                valid=0<=r['left']<=100 and 0<=r['right']<=100
                status='input_rejected' if not valid and variant!='bounds' else 'setup_error' if variant=='setup' else 'ok'
                matches=matches and r.get('status')==status
                if status=='ok' and r.get('status')=='ok':
                    expected=r['left']+r['right'] if variant!='arithmetic' else r['left']-r['right']
                    expected+=7 if r['modified'] else 0
                    if scheme=='tfhe': expected%=65536
                    accept=True if variant=='acceptance' else math.isclose(expected,r['left']+r['right'],rel_tol=0,abs_tol=1e-5)
                    matches=matches and math.isclose(r['value'],expected,rel_tol=0,abs_tol=1e-5)
                    matches=matches and r['accepted']==accept and r['worker_has_secret']==(variant=='secret')
                if status=='setup_error' and scheme=='ckks':
                    matches=matches and r.get('error')=='no global scale'
            if variant=='setup' and scheme!='ckks':
                log=out/f'{scheme}-setup.stderr'
                needle='The server key was not properly initialized.' if scheme=='tfhe' else 'KeyGen operation has not been enabled.'
                matches=matches and log.exists() and log.read_text().count(needle)==6
            suffix={'ckks':'.py','tfhe':'.rs','bfv':'.hpp'}[scheme]
            source=HERE/'cases'/(name+suffix)
            results.append(dict(id=name,scheme=scheme,variant=variant,source_path=str(source.relative_to(ROOT)),source_sha256=hashes[str(source.relative_to(ROOT))],observations=rows,matches_expected_behavior=bool(matches)))
    success=all(r['matches_expected_behavior'] for r in results) and all(c['exit_code']==0 for c in commands)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    report=dict(passed=success,cases=results,commands=commands,input_sha256=hashes,model_called=False)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=success,cases=len(results),observations=len(observed))))
    if not success: raise SystemExit(1)

if __name__=='__main__': main()
