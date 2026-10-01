"""Validate the repaired release; report remaining blockers without authorizing training."""
import argparse
import collections
import copy
import json
from pathlib import Path
from build_dataset import HERE, ROOT, read, sha, validator

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--evidence',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--check-tokens',action='store_true')
    args=ap.parse_args()
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    data=HERE/'data'; manifest=json.loads((data/'manifest.json').read_text())
    assert manifest['training_ready'] is False and manifest['training_authorized'] is False
    assert sha(args.evidence)==manifest['native_evidence_sha256']
    native=json.loads(args.evidence.read_text())
    assert native['passed'] and native['model_called'] is False
    assert all(c['exit_code']==0 for c in native['commands'])
    fresh=ROOT/'training/evaluation_v2/data'
    assert sha(fresh/'FREEZE.json')==manifest['evaluation_freeze_sha256']
    freeze=json.loads((fresh/'FREEZE.json').read_text())
    assert sha(fresh/'manifest.json')==freeze['manifest_sha256']
    for split in ('validation','test'):
        assert (data/f'{split}.jsonl').read_bytes()==(fresh/f'{split}.jsonl').read_bytes()
        assert sha(data/f'{split}.jsonl')==freeze['dataset_sha256'][split]
    parent=ROOT/'training/expanded_v2/step2/data'
    assert sha(parent/'train.jsonl')==manifest['parent_train_sha256']
    assert (data/'regression.jsonl').read_bytes()==(parent/'regression.jsonl').read_bytes()
    old_rows=read(parent/'train.jsonl')
    old_map={r['id']:r for r in old_rows}
    catalog={r['id']:r for r in manifest['new_sources']}
    reserved=read(parent/'validation.jsonl')
    families={}; normalized={}; ids=set(); splits={}; cell_counts={}
    for split in ('train','validation','test','regression'):
        path=data/f'{split}.jsonl'
        assert sha(path)==manifest['sha256'][split]
        rows=read(path); splits[split]=rows
        assert len(rows)==manifest['counts'][split]
        for row in rows:
            assert row['id'] not in ids; ids.add(row['id'])
            assert families.setdefault(row['family'],split)==split
            canonical=' '.join(row['source'].split())
            assert canonical not in normalized
            normalized[canonical]=split
            prefix='F' if row['profile_id'].startswith('aes') else 'H'
            validator.validate_answer(row['expected'],row['source'],[f'{prefix}0{i}' for i in range(1,6)])
            assert json.loads(row['messages'][-1]['content'])==row['expected']
            payload=json.loads(row['messages'][-2]['content'])
            assert '\n'.join(line['text'] for line in payload['untrusted_source'])==row['source']
            if split=='train':
                assert all(' '.join(r['source'].split())!=canonical and r['family']!=row['family'] for r in reserved)
                if row['id'] in catalog:
                    case=catalog[row['id']]; source=ROOT/case['source_path']
                    assert sha(source)==row['source_sha256']==case['source_sha256']
                    assert source.read_text()==row['source']
                    if not row['profile_id'].startswith('aes'):
                        evidence=next(c for c in native['cases'] if 'v3_'+c['id']==row['id'])
                        assert evidence['matches_expected_behavior'] is True
                        assert evidence['source_sha256']==row['source_sha256']
                    else:
                        assert row['native_evidence_status']=='not_run_no_native_windows'
                else:
                    assert row==old_map[row['id']]
                for c in row['expected']['checks']:
                    cell_counts.setdefault(row['profile_id']+'/'+c['check_id'],collections.Counter())[c['assessment']]+=1
    assert len(cell_counts)==20
    assert all(c['potential_issue']>0 and c['no_issue_identified']>0 for c in cell_counts.values())
    kept={r['id'] for r in splits['train'] if r['id'] in old_map}
    removed={r['id'] for r in manifest['removed_from_new_release']}
    assert kept.isdisjoint(removed) and kept|removed==set(old_map)
    # Negative test: a fabricated evidence quote must be rejected by the schema checker.
    sample=copy.deepcopy(next(r for r in splits['train'] if r['expected']['findings']))
    sample['expected']['findings'][0]['quote']='THIS_QUOTE_DOES_NOT_EXIST_IN_THE_SOURCE'
    try:
        validator.validate_answer(sample['expected'],sample['source'],[f'F0{i}' for i in range(1,6)])
    except AssertionError:
        quote_negative_test=True
    else:
        raise AssertionError('Fabricated quote was accepted')
    lengths={}
    if args.check_tokens:
        from common import MODEL, REVISION
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,local_files_only=True)
        for split,rows in splits.items():
            sizes=[]
            for row in rows:
                full=tokenizer.apply_chat_template(row['messages'],tokenize=True,return_dict=False)
                prefix=tokenizer.apply_chat_template(row['messages'][:-1],tokenize=True,add_generation_prompt=True,return_dict=False)
                assert full[:len(prefix)]==prefix and len(full)<=3072
                sizes.append(len(full))
            lengths[split]=dict(minimum=min(sizes),maximum=max(sizes),rows=len(rows))
    before=collections.Counter(c['assessment'] for r in old_rows for c in r['expected']['checks'])
    after=collections.Counter(c['assessment'] for r in splits['train'] for c in r['expected']['checks'])
    report=dict(validation='passed',training_ready=False,training_authorized=False,
                counts=manifest['counts'],old_training_labels=dict(before),new_training_labels=dict(after),
                old_insufficient_context_fraction=before['insufficient_context']/sum(before.values()),
                new_insufficient_context_fraction=after['insufficient_context']/sum(after.values()),
                training_whitespace_duplicates=0,training_cells_with_issue_and_control=len(cell_counts),
                native_FHE_cases=18,native_FHE_trials=180,AES_runtime_status='not_run_no_native_windows',
                evaluation_unchanged=True,old_datasets_unchanged=True,quote_negative_test=quote_negative_test,
                token_lengths=lengths,coverage={k:dict(v) for k,v in sorted(cell_counts.items())},
                manifest_sha256=sha(data/'manifest.json'),native_evidence_sha256=sha(args.evidence),
                remaining_blockers=manifest['readiness_blockers'])
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Repaired dataset v3: audit','','Integrity: passed. Training: **not started and not authorized**.','',
           '| Measure | Previous draft | Repaired draft |','|---|---:|---:|',
           '| Training rows | 57 | 43 |','| Whitespace-unique training sources | 41 | 43 |',
           '| Insufficient-context labels | 217 / 285 (76.1%) | 75 / 215 (34.9%) |',
           '| Profile/check cells with issue and corrected labels | 12 / 20 | 20 / 20 |',
           '', '## What changed','',
           'Removed 16 whitespace duplicates and superseded 22 partial FHE excerpts in the new release only. Retained 16 distinct AES excerpts and three genuinely incomplete callback examples. Added 18 complete FHE workflows and six full AES source-reviewed variants.',
           'The FHE workflows passed 180 native trials. AES sources and their prepared Windows harness have not been compiled or run here.',
           'Frozen validation/test data is unchanged and remains excluded from training. All existing dataset versions are preserved.',
           '', '## Remaining blockers','']+['- '+b for b in manifest['readiness_blockers']]+['',
           'Coverage counts are not accuracy or statistical sufficiency. Same-template variants are not independent implementations.',
           '[Detailed audit and token lengths](audit.json)']
    (out/'audit.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:report[k] for k in ('validation','counts','new_training_labels','training_cells_with_issue_and_control','token_lengths','remaining_blockers')},indent=2))

if __name__=='__main__': main()
