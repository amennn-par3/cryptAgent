"""Offline native witnesses; exceptions are evidence, not successful round trips."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    paths = [p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py', '.rs', '.hpp', '.cpp', '.toml', '.lock', '.txt') and '__pycache__' not in p.parts]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    env = os.environ.copy()
    env.update(CARGO_HOME=str(ROOT/'runtime/cargo'), CARGO_TARGET_DIR=str(ROOT/'runtime/tfhe-build'),
               RUSTC=str(ROOT/'runtime/rust/bin/rustc'), LD_LIBRARY_PATH=str(ROOT/'runtime/openfhe/lib'),
               OMP_NUM_THREADS='4', RAYON_NUM_THREADS='4')
    commands, observations = [], []
    def run(label, argv, parse=False):
        start = time.monotonic()
        try:
            p = subprocess.run([str(x) for x in argv], cwd=ROOT, env=env, capture_output=True, timeout=600)
            rc, stdout, stderr = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as exc:
            rc, stdout, stderr = None, exc.stdout or b'', exc.stderr or b'timeout'
        (out/f'{label}.stdout').write_bytes(stdout)
        (out/f'{label}.stderr').write_bytes(stderr)
        commands.append(dict(label=label, argv=[str(x) for x in argv], exit_code=rc, seconds=time.monotonic()-start))
        if rc == 0 and parse:
            observations.extend(json.loads(line) for line in stdout.decode().splitlines() if line.startswith('{'))
        print(label, rc, flush=True)
        return rc == 0
    run('python-environment', [ROOT/'runtime/fhe-venv/bin/python', '-m', 'pip', 'freeze'])
    run('rust-version', [ROOT/'runtime/rust/bin/rustc', '--version'])
    run('cpp-version', ['g++', '--version'])
    run('openfhe-revision', ['git', '-C', ROOT/'runtime/openfhe-source', 'rev-parse', 'HEAD'])
    run('ckks', [ROOT/'runtime/fhe-venv/bin/python', HERE/'probe_ckks.py'], True)
    if run('rust-build', [ROOT/'runtime/rust/bin/cargo', 'build', '--locked', '--offline', '--release', '--manifest-path', HERE/'rust/Cargo.toml', '-j', '4']):
        run('tfhe', [ROOT/'runtime/tfhe-build/release/cryptagent-context-probes'], True)
    cmake = ROOT/'runtime/fhe-venv/bin/cmake'
    build = ROOT/'runtime/bfv-context-probes'
    if run('configure', [cmake, '-S', HERE/'cpp', '-B', build, '-DOpenFHE_DIR='+str(ROOT/'runtime/openfhe/lib/OpenFHE'), '-DCMAKE_BUILD_TYPE=Release']):
        if run('build', [cmake, '--build', build, '-j', '4']):
            for variant in ('missing', 'configured'):
                run('bfv-'+variant, [build/f'bfv_{variant}_pke'], True)
    results = []
    for scheme, setting, inputs in [('ckks','scale',[0.0,-3.25,12.5]), ('tfhe','server',[0,12,254]), ('bfv','pke',[0,-12,120])]:
        for variant in ('missing', 'configured'):
            name = f'{scheme}_{variant}_{setting}'
            rows = [r for r in observations if r['case'] == name]
            matches = len(rows) == 3 and [r['input'] for r in rows] == inputs
            if variant == 'missing':
                matches = matches and all('error_type' in r and 'value' not in r for r in rows)
                if scheme == 'ckks':
                    matches = matches and all(r.get('error') == 'no global scale' for r in rows)
                else:
                    log = out / ('tfhe.stderr' if scheme == 'tfhe' else 'bfv-missing.stderr')
                    diagnostic = 'The server key was not properly initialized.' if scheme == 'tfhe' else 'KeyGen operation has not been enabled.'
                    matches = matches and log.exists() and log.read_text().count(diagnostic) == 3
            else:
                matches = matches and all('value' in r and math.isclose(r['value'], r['input']+(1 if scheme=='tfhe' else 0), abs_tol=1e-5, rel_tol=1e-5) for r in rows)
            results.append(dict(case=name, observations=rows, matches_expected_behavior=matches))
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    success = all(r['matches_expected_behavior'] for r in results) and all(c['exit_code']==0 for c in commands)
    report = dict(passed=success, source_sha256=hashes, commands=commands, cases=results, model_called=False,
                  limitation='Concrete configuration/round-trip witnesses only, not a cryptographic security proof.')
    (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed':success, 'cases':len(results), 'observations':len(observations)}))
    if not success:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
