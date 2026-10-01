"""Fresh evaluation-only sources. Never append these rows to training."""
import ast
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'training'))
from common import messages
spec = importlib.util.spec_from_file_location('definitions', ROOT/'training/expanded/build_dataset.py')
definitions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(definitions)
spec = importlib.util.spec_from_file_location('validator', ROOT/'training/expanded/validate_dataset.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def historical_rows():
    paths = [ROOT/'training/expanded/data'/f'{s}.jsonl' for s in ('train','validation','test')]
    paths += [ROOT/'training/expanded_v2/data/additions.jsonl', ROOT/'training/expanded_v2/step2/data/additions.jsonl']
    return paths, [json.loads(line) for p in paths for line in p.read_text().splitlines()]

def tokens(source):
    return re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]', source)

def build():
    if (HERE/'data/FREEZE.json').exists():
        raise SystemExit('This evaluation version is frozen. Create a new version instead of overwriting it.')
    paths, old = historical_rows()
    splits = {'validation': [], 'test': []}
    catalog, similarities = [], []
    for scheme in ('ckks','tfhe','bfv'):
        for kind, variants, split, target in [('telemetry',('leaky','redacted'),'validation','H03'),
                                               ('work',('unchecked','bounded'),'test','H05')]:
            for variant in variants:
                name = f'{scheme}_{kind}_{variant}'
                path = HERE/'cases'/(name+{'ckks':'.py','tfhe':'.rs','bfv':'.hpp'}[scheme])
                source = path.read_text()
                if scheme == 'ckks':
                    ast.parse(source)
                issue = variant in ('leaky','unchecked')
                if kind == 'telemetry':
                    reason = ('The decrypted confidential result is copied into telemetry forwarded to an untrusted operator.' if issue
                              else 'Only a fixed completion message is added to telemetry; decrypted values are returned locally and not included in the shown telemetry boundary.')
                    quote = {'ckks':'telemetry.append("result=" + repr(values))',
                             'tfhe':'telemetry.push(format!("result={}", value));',
                             'bfv':'telemetry.push_back("result=" + std::to_string(value));'}[scheme]
                    family = 'plaintext-telemetry-boundary-eval-v2'
                else:
                    reason = ('The caller-controlled iteration count is used without enforcing the documented work budget before evaluation.' if issue
                              else 'The iteration budget is checked before the shown evaluation loop; out-of-budget requests are rejected rather than evaluated.')
                    quote = {'ckks':'for _ in range(rounds):', 'tfhe':'for _ in 0..rounds {',
                             'bfv':'for (std::size_t i = 0; i < rounds; ++i) {'}[scheme]
                    family = 'evaluator-work-budget-eval-v2'
                findings = []
                if issue:
                    line = next(i+1 for i,text in enumerate(source.split('\n')) if quote in text)
                    findings.append(dict(check_id=target,line_start=line,line_end=line,quote=quote,rationale=reason))
                answer = dict(scope='in_scope', checks=[dict(check_id=f'H0{i}',
                    assessment=('potential_issue' if issue else 'no_issue_identified') if f'H0{i}'==target else 'insufficient_context',
                    reason=reason if f'H0{i}'==target else 'The surrounding application contract, key setup or lifecycle needed for this requirement is not provided.') for i in range(1,6)], findings=findings)
                validator.validate_answer(answer, source, [f'H0{i}' for i in range(1,6)])
                assert all(' '.join(source.split()) != ' '.join(row['source'].split()) for row in old)
                assert family not in {row['family'] for row in old}
                profile = definitions.PROFILES[scheme]
                row = dict(id=name,family=family,split=split,profile_id=profile['id'],source=source,
                           source_sha256=digest(path),expected=answer,target_check=target,
                           label_origin='authored_source_reasoning_not_model_predictions',
                           messages=messages(source,profile,ROOT/'prompts/verify_multi.txt')+[dict(role='assistant',content=json.dumps(answer))])
                splits[split].append(row)
                catalog.append(dict(id=name,scheme=scheme,kind=kind,variant=variant,split=split,family=family,
                    source_path=str(path.relative_to(ROOT)),source_sha256=digest(path),target_check=target,
                    target_assessment='potential_issue' if issue else 'no_issue_identified'))
                nearest = max(((difflib.SequenceMatcher(None,tokens(source),tokens(r['source']),autojunk=False).ratio(),r['id']) for r in old))
                similarities.append(dict(id=name,nearest_historical_id=nearest[1],token_sequence_similarity=round(nearest[0],4)))
    dest = HERE/'data'
    dest.mkdir(exist_ok=True)
    for split, rows in splits.items():
        (dest/f'{split}.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    info = dict(version='fresh-targeted-fhe-evaluation-v2',evaluation_only=True,training_ready=False,
        counts={s:len(rows) for s,rows in splits.items()},sha256={s:digest(dest/f'{s}.jsonl') for s in splits},
        historical_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        training_snapshot_sha256=digest(ROOT/'training/expanded_v2/step2/data/train.jsonl'),
        prompt_sha256=digest(ROOT/'prompts/verify_multi.txt'),cases=catalog,similarity_audit=similarities,
        model_evaluation_status='not_run',readiness_blockers=['Evaluation-only dataset: never use as training input.'],
        limitations=['Six rows per split, representing one semantic family per split across three languages.',
          'Authored by the same assistant; no independent-author or pretrained-data novelty claim.',
          'Validation targets H03 and test targets H05; aggregate results cannot represent H01-H05 coverage.',
          'No new AES/Windows CNG evaluation is included; existing AES regression data is unchanged.',
          'Token similarity is a diagnostic, not proof of semantic independence.',
          'These excerpts intentionally leave unrelated checks insufficient_context; score target checks separately.'])
    (dest/'manifest.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps({'counts':info['counts'],'evaluation_only':True,'model_evaluation':'not_run'},indent=2))

if __name__ == '__main__':
    build()
