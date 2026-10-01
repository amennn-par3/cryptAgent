"""Add evidence-backed H04 rows without modifying previous dataset versions."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
spec = importlib.util.spec_from_file_location('step1_builder', HERE.parent/'build_dataset.py')
step1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence', type=Path, required=True)
    evidence_path = ap.parse_args().evidence.resolve()
    evidence = json.loads(evidence_path.read_text())
    assert evidence['passed'] and len(evidence['cases']) == 6
    previous_manifest = json.loads((HERE.parent/'data/manifest.json').read_text())
    datasets = {}
    for split in ('train', 'validation', 'regression'):
        path = HERE.parent/f'data/{split}.jsonl'
        assert step1.digest(path) == previous_manifest['sha256'][split]
        datasets[split] = [json.loads(line) for line in path.read_text().splitlines()]
    descriptions = {
        'ckks': ('scale', 'return ts.ckks_vector(context, [value]).decrypt()[0]',
                 'The fresh CKKS context has no global scale and the vector constructor supplies none; encoding fails.',
                 'The context specifies the profile coefficient chain and a 2**40 global scale before encoding.'),
        'tfhe': ('server', 'let result = encrypted + 1u8;',
                 'The thread server key is explicitly removed and not reinstalled before homomorphic addition; evaluation panics.',
                 'The server key generated together with the client key is installed in the execution thread before evaluation.'),
        'bfv': ('pke', 'auto keys = cc->KeyGen();',
                'The context does not enable PKE before key generation; key generation throws instead of completing the round trip.',
                'The profile parameters and security preset are specified and PKE is enabled before generating and using the key pair.'),
    }
    additions = []
    for scheme, (setting, quote, bad_reason, good_reason) in descriptions.items():
        for variant in ('missing', 'configured'):
            name = f'{scheme}_{variant}_{setting}'
            path = HERE/'cases'/(name+{'ckks':'.py','tfhe':'.rs','bfv':'.hpp'}[scheme])
            source = path.read_text()
            assert step1.digest(path) == evidence['source_sha256'][str(path.relative_to(ROOT))]
            observed = next(c for c in evidence['cases'] if c['case']==name)
            assert observed['matches_expected_behavior']
            issue = variant == 'missing'
            reason = bad_reason if issue else good_reason
            findings = []
            if issue:
                line = next(i+1 for i,text in enumerate(source.split('\n')) if quote in text)
                findings.append(dict(check_id='H04',line_start=line,line_end=line,quote=quote,rationale=reason))
            answer = dict(scope='in_scope', checks=[dict(check_id=f'H0{i}',
                assessment=('potential_issue' if issue else 'no_issue_identified') if i==4 else 'insufficient_context',
                reason=reason if i==4 else 'The surrounding application contract and lifecycle needed for this check are not specified.') for i in range(1,6)], findings=findings)
            step1.validator.validate_answer(answer, source, [f'H0{i}' for i in range(1,6)])
            profile = step1.definitions.PROFILES[scheme]
            additions.append(dict(id=name, family='context-initialization-v2', split='train', profile_id=profile['id'],
                source=source, source_sha256=step1.digest(path), expected=answer,
                label_origin='authored_source_review_with_native_setup_witnesses',
                messages=step1.messages(source, profile, ROOT/'prompts/verify_multi.txt')+[dict(role='assistant',content=json.dumps(answer))]))
    datasets['train'] += additions
    families, hashes, ids = {}, {}, set()
    for split, rows in datasets.items():
        for row in rows:
            assert row['id'] not in ids
            ids.add(row['id'])
            assert families.setdefault(row['family'],split)==split
            assert hashes.setdefault(' '.join(row['source'].split()),split)==split
            assert hashlib.sha256(row['source'].encode()).hexdigest()==row['source_sha256']
            prefix='F' if row['profile_id'].startswith('aes') else 'H'
            step1.validator.validate_answer(row['expected'],row['source'],[f'{prefix}0{i}' for i in range(1,6)])
            assert json.loads(row['messages'][-1]['content'])==row['expected']
    dest=HERE/'data'
    dest.mkdir(exist_ok=True)
    datasets['additions']=additions
    for split,rows in datasets.items():
        path=dest/f'{split}.jsonl'
        if split in ('validation','regression'):
            path.write_bytes((HERE.parent/f'data/{split}.jsonl').read_bytes())
        else:
            path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    manifest=dict(version='multi-profile-v2-step2-draft',training_ready=False,
        counts={s:len(r) for s,r in datasets.items()},sha256={s:step1.digest(dest/f'{s}.jsonl') for s in datasets},
        parent_sha256=previous_manifest['sha256'],native_evidence_sha256=step1.digest(evidence_path),
        after_training_coverage=step1.coverage(datasets['train']),
        readiness_blockers=['Overall labels remain dominated by insufficient context.',
          'Independent validation and held-out implementations are still required.',
          'H04 coverage here tests initialization, not cross-context key misuse or weak custom security parameters.'],
        limitations=['All six additions share one train-only family.',
          'Setup exceptions do not demonstrate cryptanalytic attacks.',
          'Corrected examples have no identified H04 issue in their shown setup, not a whole-program security guarantee.'])
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'validation':'passed','counts':manifest['counts'],'training_ready':False},indent=2))

if __name__=='__main__':
    main()
