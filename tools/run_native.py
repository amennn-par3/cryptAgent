"""Native runner for inspected bundled fixtures. NOT an untrusted-code sandbox."""
import argparse, hashlib, json, os, platform, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pilot',action='store_true'); ap.add_argument('--case'); ap.add_argument('--out',default='native-results'); args=ap.parse_args()
    if os.name!='nt': raise SystemExit('Native Windows required')
    inc=os.environ.get('CRYPTAGENT_SODIUM_INCLUDE'); lib=os.environ.get('CRYPTAGENT_SODIUM_LIBRARY')
    if not inc or not lib or not (Path(inc)/'sodium.h').is_file() or not Path(lib).is_file():
        raise SystemExit('Dependency missing: follow WINDOWS_SETUP.md; no native assessment performed')
    cmake=shutil.which('cmake')
    if not cmake: raise SystemExit('Open Developer PowerShell for VS 2022 with CMake available')
    out=(ROOT/args.out).resolve()
    if not out.is_relative_to(ROOT): raise SystemExit('Output must remain inside cryptagent')
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'phase3/manifest.json').read_text())['cases']
    if args.pilot:
        pilot=json.loads((ROOT/'phase3/pilot.json').read_text())['case_ids']; manifest=[c for c in manifest if c['case_id'] in pilot]
    if args.case: manifest=[c for c in manifest if c['case_id']==args.case]
    if not manifest: raise SystemExit('No matching cases')
    environment={'os':platform.platform(),'machine':platform.machine(),'sodium_library_sha256':sha(lib),'sodium_umbrella_header_sha256':sha(Path(inc)/'sodium.h'),'library_path':str(Path(lib).resolve()),'cmake':subprocess.check_output([cmake,'--version'],text=True),'complete_dependency_pin':False,'note':'Record SDK/compiler versions, sodium version, whole archive hash and signature separately.'}
    (out/'environment.json').write_text(json.dumps(environment,indent=2),encoding='utf-8')
    results=[]
    for case in manifest:
        dest=out/case['case_id']; dest.mkdir(exist_ok=True)
        source=ROOT/case['source_path']
        if sha(source)!=case['source_sha256']: raise SystemExit('Fixture source changed: '+case['case_id'])
        row={'case_id':case['case_id'],'source_sha256':sha(source),'status':'inconclusive','commands':[],'expected_labels_not_used_as_verdict':True}
        def run(argv,label,timeout=180):
            try:
                p=subprocess.run(argv,capture_output=True,timeout=timeout)
                record={'label':label,'argv':[str(x) for x in argv],'exit_code':p.returncode,'timeout':False}
                (dest/(label+'.stdout')).write_bytes(p.stdout); (dest/(label+'.stderr')).write_bytes(p.stderr)
            except subprocess.TimeoutExpired as e:
                record={'label':label,'argv':[str(x) for x in argv],'exit_code':None,'timeout':True}
                (dest/(label+'.stdout')).write_bytes(e.stdout or b''); (dest/(label+'.stderr')).write_bytes(e.stderr or b'')
            row['commands'].append(record); return record
        build=dest/'build'
        cfg=run([cmake,'-S',str(ROOT),'-B',str(build),'-A','x64','-DSODIUM_INCLUDE_DIR='+inc,'-DSODIUM_LIBRARY='+lib,'-DCANDIDATE_SOURCE='+str(source)],'configure')
        if cfg['exit_code']==0:
            compiled=run([cmake,'--build',str(build),'--config','Release'],'build')
            if compiled['exit_code']==0:
                exe=build/'Release/fixture_test.exe'; observations=[]
                checks=sorted(set(['roundtrip','tamper','aad','fixed-nonce','fixed-key','empty','boundary','oversize-plaintext','oversize-aad','malformed','wrong-key','log']))
                for check in checks:
                    r=run([str(exe),check,str(case['plaintext_bytes']),str(case['aad_bytes'])],check,30)
                    stderr=(dest/(check+'.stderr')).read_bytes()
                    stdout=(dest/(check+'.stdout')).read_bytes()
                    if r['exit_code']==10 and b'VIOLATION:' in stdout: observations.append({'check':check,'result':'contract_violation_observed'})
                    elif r['exit_code']!=0: observations.append({'check':check,'result':'inconclusive_execution_error'})
                    elif check=='log' and stderr: observations.append({'check':check,'result':'unexpected_stderr_requires_review'})
                    else: observations.append({'check':check,'result':'selected_check_passed'})
                row['observations']=observations
                row['status']='fails_selected_checks' if any(x['result']=='contract_violation_observed' for x in observations) else 'inconclusive'
                row['limitation']='Selected tests cannot establish all mandatory security properties; labels require evidence review.'
        (dest/'result.json').write_text(json.dumps(row,indent=2),encoding='utf-8'); results.append(row)
        print(case['case_id'],row['status'],flush=True)
    (out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
if __name__=='__main__': main()
