"""Audit split isolation and native evidence; optionally seal an evaluation version."""
import argparse
import collections
import json
from pathlib import Path
from build_dataset import HERE, ROOT, digest, historical_rows, validator

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--evidence',type=Path,required=True)
    ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--freeze',action='store_true')
    args=ap.parse_args()
    if args.report.exists(): raise SystemExit('Use a fresh report path.')
    m=json.loads((HERE/'data/manifest.json').read_text())
    freeze_path=HERE/'data/FREEZE.json'
    if freeze_path.exists():
        frozen=json.loads(freeze_path.read_text())
        assert frozen['manifest_sha256']==digest(HERE/'data/manifest.json')
        assert frozen['dataset_sha256']==m['sha256']
        assert frozen['prompt_sha256']==m['prompt_sha256']
        assert frozen['native_evidence_sha256']==digest(args.evidence)
    assert m['evaluation_only'] is True and m['training_ready'] is False
    assert m['model_evaluation_status']=='not_run'
    paths, old=historical_rows()
    for path in paths:
        assert digest(path)==m['historical_sha256'][str(path.relative_to(ROOT))]
    train=ROOT/'training/expanded_v2/step2/data/train.jsonl'
    assert digest(train)==m['training_snapshot_sha256']
    assert digest(ROOT/'prompts/verify_multi.txt')==m['prompt_sha256']
    old_ids={r['id'] for r in old}
    old_sources={' '.join(r['source'].split()) for r in old}
    old_families={r['family'] for r in old}
    ids=set(); sources={}; families={}; counts={}; labels={}
    evidence=json.loads(args.evidence.read_text())
    assert evidence['passed'] is True and evidence['model_called'] is False
    assert evidence['manifest_sha256']==digest(HERE/'data/manifest.json')
    assert len(evidence['cases'])==12
    assert all(c['exit_code']==0 for c in evidence['commands'])
    catalog={c['id']:c for c in m['cases']}
    assert len(catalog)==12
    for split in ('validation','test'):
        path=HERE/f'data/{split}.jsonl'
        assert digest(path)==m['sha256'][split]
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows)==m['counts'][split]==6
        counts[split]=len(rows); counter=collections.Counter()
        for row in rows:
            case=catalog[row['id']]
            assert row['id'] not in ids | old_ids
            ids.add(row['id'])
            assert row['split']==case['split']==split
            assert row['family']==case['family'] and row['family'] not in old_families
            assert families.setdefault(row['family'],split)==split
            normalized=' '.join(row['source'].split())
            assert normalized not in old_sources and normalized not in sources
            sources[normalized]=split
            source_path=ROOT/case['source_path']
            assert source_path.read_text()==row['source']
            assert digest(source_path)==row['source_sha256']==case['source_sha256']
            assert evidence['source_sha256'][case['source_path']]==row['source_sha256']
            observed=[r for r in evidence['cases'] if r['id']==row['id']]
            assert len(observed)==1 and observed[0]['matches_expected_behavior'] is True
            validator.validate_answer(row['expected'],row['source'],[f'H0{i}' for i in range(1,6)])
            assert json.loads(row['messages'][-1]['content'])==row['expected']
            payload=json.loads(row['messages'][-2]['content'])
            assert '\n'.join(line['text'] for line in payload['untrusted_source'])==row['source']
            target=next(c for c in row['expected']['checks'] if c['check_id']==row['target_check'])
            assert target['assessment']==case['target_assessment']
            counter[target['assessment']]+=1
        assert counter=={'potential_issue':3,'no_issue_identified':3}
        labels[split]=dict(counter)
    result=dict(validation='passed',counts=counts,target_labels=labels,
                exact_and_whitespace_duplicates=False,family_split_disjoint=True,
                previous_training_unchanged=True,native_cases=12,native_observations=44,
                model_inference_run=False,limitations=m['limitations'])
    if args.freeze:
        freeze_path=HERE/'data/FREEZE.json'
        if freeze_path.exists(): raise SystemExit('Evaluation version already frozen; do not overwrite.')
        record=dict(version=m['version'],dataset_sha256=m['sha256'],
                    manifest_sha256=digest(HERE/'data/manifest.json'),
                    prompt_sha256=m['prompt_sha256'],native_evidence_sha256=digest(args.evidence),
                    policy='Never train on these sources or variants. Validation may guide tuning; test is reserved for the agreed evaluation. After test-driven changes, retire it to regression.',
                    limitation='A small targeted set authored by the same assistant, not an independently authored benchmark.')
        freeze_path.write_text(json.dumps(record,indent=2)+'\n')
        result['evaluation_frozen']=True
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
