"""Record builds and native witnesses for the authored allowlisted fixtures only.

This is not an untrusted-code execution service. Never accept arbitrary input paths.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); args = ap.parse_args()
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((HERE / 'data/manifest.json').read_text())
    inputs = [HERE/'probe_ckks.py',HERE/'cpp/main.cpp',HERE/'cpp/CMakeLists.txt',HERE/'rust/src/main.rs',HERE/'rust/Cargo.toml',HERE/'rust/Cargo.lock']
    harness_hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs if p.exists()}
    for row in manifest['fhe_cases']:
        if hashlib.sha256((ROOT/row['source_path']).read_bytes()).hexdigest() != row['source_sha256']:
            raise ValueError('Dataset source hash mismatch: '+row['id'])
    env = os.environ.copy()
    env['CARGO_HOME'] = str(ROOT/'runtime/cargo')
    env['CARGO_TARGET_DIR'] = str(ROOT/'runtime/tfhe-build')
    env['RUSTC'] = str(ROOT/'runtime/rust/bin/rustc')
    env['LD_LIBRARY_PATH'] = str(ROOT/'runtime/openfhe/lib')
    env['RAYON_NUM_THREADS'] = '4'; env['OMP_NUM_THREADS'] = '4'
    commands = []; observations = {}
    def run(label, argv, timeout=600, parse=False):
        start = time.monotonic()
        try:
            proc = subprocess.run([str(x) for x in argv], cwd=ROOT, env=env, capture_output=True, timeout=timeout)
            rc, stdout, stderr, state = proc.returncode, proc.stdout, proc.stderr, 'completed'
        except subprocess.TimeoutExpired as exc:
            rc, stdout, stderr, state = None, exc.stdout or b'', exc.stderr or b'', 'timeout'
        except OSError as exc:
            rc, stdout, stderr, state = None, b'', str(exc).encode(), 'unavailable'
        (out/(label+'.stdout')).write_bytes(stdout); (out/(label+'.stderr')).write_bytes(stderr)
        commands.append({'label':label,'argv':[str(x) for x in argv], 'exit_code':rc,'state':state,'seconds':time.monotonic()-start})
        print(label, state, rc, flush=True)
        if parse and rc == 0:
            for line in stdout.decode().splitlines():
                if line.startswith('{'):
                    value = json.loads(line)
                    if value['case'] in observations: raise ValueError('Duplicate probe result')
                    if type(value.get('property_satisfied')) is not bool: raise ValueError('Invalid probe result')
                    observations[value['case']] = value
        return rc == 0
    run('python-version', [ROOT/'runtime/fhe-venv/bin/python','--version'])
    run('python-packages', [ROOT/'runtime/fhe-venv/bin/python','-m','pip','freeze'])
    run('rust-version', [ROOT/'runtime/rust/bin/rustc','--version'])
    run('cpp-version', ['g++','--version'])
    run('openfhe-revision', ['git','-C',ROOT/'runtime/openfhe-source','rev-parse','HEAD'])
    run('ckks', [ROOT/'runtime/fhe-venv/bin/python', HERE/'probe_ckks.py'], parse=True)
    if run('rust-build', [ROOT/'runtime/rust/bin/cargo','build','--release','--locked','--offline',
                         '--manifest-path',HERE/'rust/Cargo.toml','-j','4']):
        run('tfhe', [ROOT/'runtime/tfhe-build/release/cryptagent-tfhe-probes'], parse=True)
    cmake = ROOT/'runtime/fhe-venv/bin/cmake'
    if run('bfv-configure', [cmake,'-S',HERE/'cpp','-B',ROOT/'runtime/bfv-probes',
                '-DOpenFHE_DIR='+str(ROOT/'runtime/openfhe/lib/OpenFHE'),'-DCMAKE_BUILD_TYPE=Release']):
        if run('bfv-build',[cmake,'--build',ROOT/'runtime/bfv-probes','-j','4']):
            for row in manifest['fhe_cases']:
                if row['scheme']=='bfv': run(row['id'],[ROOT/'runtime/bfv-probes'/row['id']], parse=True)
    rows = []
    for case in manifest['fhe_cases']:
        observed = observations.get(case['id'])
        rows.append({**case,'native_status':'completed' if observed else 'not_completed',
            'observation':observed, 'matches_authored_expectation': observed['property_satisfied']==case['expected_property_satisfied'] if observed else None,
            'base_model':{'status':'not_run'},'fine_tuned_model':{'status':'not_run'}})
    # Hash harnesses and lock files as well as candidate source.
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest for p,digest in harness_hashes.items()):
        raise RuntimeError('Harness changed during run; rerun in a fresh directory')
    report = {'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'dataset_version':manifest['version'],
        'manifest_sha256':hashlib.sha256((HERE/'data/manifest.json').read_bytes()).hexdigest(),
        'harness_sha256':harness_hashes,
        'commands':commands,'cases':rows,
        'limitations':['Concrete synthetic inputs only; a passing probe is not whole-program certification.',
            'Native results are separate from authored labels and model predictions.',
            'Key-export probes observe bundle contents; there is no network transfer.',
            'Result comparisons use toy locally known answers, not a general FHE integrity protocol.',
            'Base/fine-tuned model comparison has not run; CUDA recovery and completed training are required.']}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    md = ['# CryptAgent expanded native fixture results','',
          '| Case | Expected property | Observed property | Match |','|---|---|---|---|']
    for row in rows:
        expected = 'satisfied' if row['expected_property_satisfied'] else 'violated'
        actual = ('satisfied' if row['observation']['property_satisfied'] else 'violated') if row['observation'] else 'not completed'
        md.append(f"| {row['id']} | {expected} | {actual} | {row['matches_authored_expectation']} |")
    md += ['', 'These are narrow runtime witnesses, not model accuracy or security certification.',
           'Base-Llama and fine-tuned-Llama outputs are not yet available. No predictions are fabricated.']
    (out/'results.md').write_text('\n'.join(md)+'\n')
    print(json.dumps({'cases':len(rows),'completed':sum(r['native_status']=='completed' for r in rows),
        'matched':sum(r['matches_authored_expectation'] is True for r in rows),'out':str(out)},indent=2))
    if any(r['matches_authored_expectation'] is not True for r in rows): raise SystemExit(1)

if __name__ == '__main__': main()
