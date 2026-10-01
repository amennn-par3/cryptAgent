"""Read-only release audit. Freeze evidence, never promote a dataset automatically."""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
from common import ROOT, MODEL, REVISION

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--evidence-root',type=Path,required=True)
    ap.add_argument('--check-tokens',action='store_true')
    args=ap.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('schema_validator',ROOT/'training/expanded/validate_dataset.py')
    validator=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    draft=ROOT/'training/expanded_v2/step2/data'
    fresh=ROOT/'training/evaluation_v2/data'
    manifests={}
    snapshots={}
    def capture(path):
        snapshots[str(path.relative_to(ROOT))]=sha(path)
    for directory in (ROOT/'training/expanded/data',ROOT/'training/expanded_v2/data',draft,fresh):
        path=directory/'manifest.json'
        capture(path)
        m=json.loads(path.read_text())
        manifests[str(directory.relative_to(ROOT))]=m
        for split,expected in m['sha256'].items():
            data=directory/f'{split}.jsonl'
            capture(data)
            require(sha(data)==expected,f'Dataset hash mismatch: {data}')
    dm=manifests[str(draft.relative_to(ROOT))]
    fm=manifests[str(fresh.relative_to(ROOT))]
    frozen=json.loads((fresh/'FREEZE.json').read_text())
    capture(fresh/'FREEZE.json')
    capture(ROOT/'prompts/verify_multi.txt')
    require(frozen['manifest_sha256']==sha(fresh/'manifest.json'),'Frozen manifest changed')
    require(frozen['dataset_sha256']==fm['sha256'],'Frozen split hashes changed')
    require(frozen['prompt_sha256']==sha(ROOT/'prompts/verify_multi.txt'),'Frozen prompt changed')
    require(fm['training_snapshot_sha256']==sha(draft/'train.jsonl'),'Training changed since evaluation isolation audit')
    datasets={}
    locations={'train':draft/'train.jsonl','old_validation':draft/'validation.jsonl',
               'regression':draft/'regression.jsonl','fresh_validation':fresh/'validation.jsonl','fresh_test':fresh/'test.jsonl'}
    families={}; normalized={}; ids=set(); totals={}; normalized_counts={}
    coverage={}
    for split,path in locations.items():
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        datasets[split]=rows
        totals[split]=len(rows)
        for row in rows:
            require(row['id'] not in ids,f'Duplicate ID {row["id"]}')
            ids.add(row['id'])
            require(families.setdefault(row['family'],split)==split,'Family crosses active splits')
            canonical=' '.join(row['source'].split())
            require(normalized.setdefault(canonical,split)==split,'Normalized source crosses active splits')
            require(hashlib.sha256(row['source'].encode()).hexdigest()==row['source_sha256'],'Source hash mismatch')
            prefix='F' if row['profile_id'].startswith('aes') else 'H'
            validator.validate_answer(row['expected'],row['source'],[f'{prefix}0{i}' for i in range(1,6)])
            require(json.loads(row['messages'][-1]['content'])==row['expected'],'Assistant target mismatch')
            payload=json.loads(row['messages'][-2]['content'])
            require('\n'.join(line['text'] for line in payload['untrusted_source'])==row['source'],'Prompt source mismatch')
        normalized_counts[split]=len({' '.join(r['source'].split()) for r in rows})
        cells={}
        for row in rows:
            for check in row['expected']['checks']:
                key=row['profile_id']+'/'+check['check_id']
                cell=cells.setdefault(key,collections.Counter())
                cell[check['assessment']]+=1
        coverage[split]={key:dict(value) for key,value in sorted(cells.items())}
    # Current sources for all native-backed fixtures, and their recorded results.
    evidence_names=['cryptagent-native-run-02','cryptagent-dataset-step1-native-02',
                    'cryptagent-dataset-step2-native-02','cryptagent-step3-native-01']
    evidence_hashes={}; witnessed={}; incomplete=set()
    for name in evidence_names:
        path=args.evidence_root/name/'results.json'
        evidence_hashes[name]=sha(path)
        evidence=json.loads(path.read_text())
        require(all(c['exit_code']==0 for c in evidence['commands']),f'Failed native command in {name}')
        if name=='cryptagent-step3-native-01':
            require(sha(path)==frozen['native_evidence_sha256'],'Evaluation evidence differs from freeze')
        for case in evidence['cases']:
            identifier=case.get('id',case.get('case'))
            require(case.get('matches_authored_expectation',case.get('matches_expected_behavior')) is True,
                    f'Native witness mismatch: {identifier}')
            source_path=case.get('source_path')
            if source_path is None:
                source_path=next(p for p in evidence['source_sha256'] if Path(p).stem==identifier)
            path=ROOT/source_path
            expected_hash=case.get('source_sha256',evidence.get('source_sha256',{}).get(source_path))
            require(sha(path)==expected_hash,f'Native fixture changed: {source_path}')
            capture(path)
            observed=case.get('observation') or {}
            if observed.get('status')=='not_run_missing_validation_callback':
                incomplete.add(identifier)
            else:
                witnessed[identifier]=expected_hash
    token_stats={'checked':False}
    if args.check_tokens:
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,local_files_only=True)
        token_stats={'checked':True,'base_revision':REVISION,'by_split':{}}
        for split,rows in datasets.items():
            sizes=[]
            for row in rows:
                full=tokenizer.apply_chat_template(row['messages'],tokenize=True,return_dict=False)
                prefix=tokenizer.apply_chat_template(row['messages'][:-1],tokenize=True,add_generation_prompt=True,return_dict=False)
                require(full[:len(prefix)]==prefix,'Assistant masking prefix mismatch')
                require(len(full)<=3072,'Example would require truncation')
                sizes.append(len(full))
            token_stats['by_split'][split]={'minimum':min(sizes),'maximum':max(sizes),'rows':len(rows)}
    targets=list(coverage['train'])
    missing_train=[key for key in targets if not all(coverage['train'][key].get(label,0)>0 for label in ('potential_issue','no_issue_identified'))]
    missing_test=[key for key in targets if not all(coverage['fresh_test'].get(key,{}).get(label,0)>0 for label in ('potential_issue','no_issue_identified'))]
    labels=collections.Counter(c['assessment'] for r in datasets['train'] for c in r['expected']['checks'])
    native_train=[r['id'] for r in datasets['train'] if r['id'] in witnessed]
    unexecuted_train=[r['id'] for r in datasets['train'] if r['id'] in incomplete]
    without_native=[r['id'] for r in datasets['train'] if r['id'] not in witnessed and r['id'] not in incomplete]
    blockers=[]
    if missing_train: blockers.append(f'{len(missing_train)}/20 training profile/check cells lack both an issue and a corrected label.')
    if missing_test: blockers.append(f'{len(missing_test)}/20 profile/check cells lack paired fresh-test coverage.')
    if labels['insufficient_context']>sum(labels.values())/2:
        blockers.append('Most training check labels are insufficient_context; this can reward blanket abstention.')
    if without_native: blockers.append(f'{len(without_native)} training rows have no linked native witness in the audited evidence (currently AES/CNG).')
    blockers.append('Fresh evaluation has only one semantic family per split; it is not a broad independent benchmark.')
    require(dm['training_ready'] is False,'Draft was unexpectedly promoted')
    report=dict(decision='NOT_READY_FOR_RETRAINING',integrity_checks='passed',
        policy='Conservative project release checks, not a statistical guarantee or universal minimum dataset size.',
        counts=totals,unique_normalized_sources=normalized_counts,
        family_counts={s:len({r['family'] for r in rows}) for s,rows in datasets.items()},
        training_label_counts=dict(labels),insufficient_context_fraction=labels['insufficient_context']/sum(labels.values()),
        coverage=coverage,missing_training_issue_control_pairs=missing_train,missing_fresh_test_issue_control_pairs=missing_test,
        training_native_executed=len(native_train),training_explicitly_unexecuted=len(unexecuted_train),
        training_without_linked_native_evidence=without_native,token_checks=token_stats,
        blockers=blockers,snapshot_sha256=snapshots,evidence_sha256=evidence_hashes,
        source_audit_sha256=sha(Path(__file__)),model_inference_run=False,training_run=False)
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Step 4: dataset readiness audit','','Decision: **NOT READY FOR RETRAINING**. Integrity checks passed; coverage did not.','',
           '## Counts','',f"Training: {totals['train']}; old validation: {totals['old_validation']}; regression: {totals['regression']}; fresh validation: {totals['fresh_validation']}; fresh test: {totals['fresh_test']}.",'',
           '## Training coverage','', '| Profile / check | Issue | Corrected | Insufficient context | Not applicable |','|---|---:|---:|---:|---:|']
    for key,cell in coverage['train'].items():
        values=[cell.get(label,0) for label in ('potential_issue','no_issue_identified','insufficient_context','not_applicable')]
        lines.append('| '+key+' | '+' | '.join(map(str,values))+' |')
    lines+=['','## Release blockers','']+['- '+b for b in blockers]
    lines+=['','## Integrity and evidence','',
            'All versioned dataset hashes, active split family/source separation, answer schemas, exact quotes and source reconstruction passed.',
            f"Native witnesses cover {len(native_train)} training rows; {len(unexecuted_train)} incomplete-callback rows are deliberately unexecuted, not passes.",
            'The fresh evaluation freeze and its native evidence hash remain valid. No model predictions were made.',
            'Tokenizer and assistant-prefix checks: '+('passed for all 85 active rows.' if args.check_tokens else 'not run.'),
            'This report pins an audit snapshot; it does not promote or merge the draft into a training release.',
            '', '[Full matrix, hashes and token counts](audit.json)']
    (out/'audit.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:report[k] for k in ('decision','integrity_checks','counts','training_label_counts','blockers')},indent=2))

if __name__=='__main__':
    main()
