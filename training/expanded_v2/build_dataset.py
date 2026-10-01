"""Draft v2 addition. Keep the evaluated v1 dataset and predictions immutable."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V1=ROOT/'training/expanded'
sys.path.insert(0,str(ROOT/'training'))
from common import messages
spec=importlib.util.spec_from_file_location('v1_definitions',V1/'build_dataset.py')
definitions=importlib.util.module_from_spec(spec); spec.loader.exec_module(definitions)
spec=importlib.util.spec_from_file_location('v1_validator',V1/'validate_dataset.py')
validator=importlib.util.module_from_spec(spec); spec.loader.exec_module(validator)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def coverage(rows):
    counter=collections.Counter((r['profile_id'],c['check_id'],c['assessment']) for r in rows for c in r['expected']['checks'])
    return {profile:{cid:{a:counter[profile,cid,a] for a in ('potential_issue','no_issue_identified','insufficient_context','not_applicable')}
                     for cid in sorted({c['check_id'] for r in rows if r['profile_id']==profile for c in r['expected']['checks']})}
            for profile in sorted({r['profile_id'] for r in rows})}

def build():
    old=json.loads((V1/'data/manifest.json').read_text())
    for split in ('train','validation','test'):
        if digest(V1/f'data/{split}.jsonl')!=old['sha256'][split]: raise ValueError('v1 dataset changed')
    previous={s:[json.loads(line) for line in (V1/f'data/{s}.jsonl').read_text().splitlines()] for s in old['counts']}
    old_normalized={' '.join(r['source'].split()) for rows in previous.values() for r in rows}
    additions=[]; catalog=[]
    for scheme in ('ckks','tfhe','bfv'):
        for variant in ('any','all','delegate'):
            name=f'{scheme}_batch_{variant}'
            path=HERE/'cases'/(name+{'ckks':'.py','tfhe':'.rs','bfv':'.hpp'}[scheme])
            source=path.read_text(); assert ' '.join(source.split()) not in old_normalized
            findings=[]
            if variant=='any':
                quote={'ckks':'return any(matches)', 'tfhe':'.any(|(item, want)|',
                    'bfv':'return values.at(0) == expected[0] || values.at(1) == expected[1];'}[scheme]
                line=next(i+1 for i,text in enumerate(source.split('\n')) if quote in text)
                reason='The acceptance predicate needs only one matching component, so a partly modified batch can be accepted despite the requirement that every checked component match.'
                findings=[dict(check_id='H02',line_start=line,line_end=line,quote=quote,rationale=reason)]
                assessment='potential_issue'
            elif variant=='all':
                reason='Every required component is compared to the locally known reference; a mismatch prevents acceptance. This is a toy local-reference check, not a general proof of outsourced computation.'
                assessment='no_issue_identified'
            else:
                reason='The decision is delegated to a caller-provided validation callback whose implementation is missing. It is not possible to establish whether it checks every result component.'
                assessment='insufficient_context'
            answer={'scope':'in_scope','checks':[dict(check_id=c['id'],
                assessment=assessment if c['id']=='H02' else 'insufficient_context',
                reason=reason if c['id']=='H02' else 'The excerpt does not supply the full setup, computation and lifecycle needed to assess this requirement.') for c in definitions.CHECKS],
                'findings':findings}
            validator.validate_answer(answer,source,[f'H0{i}' for i in range(1,6)])
            profile=definitions.PROFILES[scheme]
            record={'id':name,'family':'batch-component-predicate-v2', 'profile_id':profile['id'],
                'split':'train','source':source,'source_sha256':digest(path),'expected':answer,
                'label_origin':'authored_source_reasoning_with_separate_native_witnesses',
                'messages':messages(source,profile,ROOT/'prompts/verify_multi.txt')+[{'role':'assistant','content':json.dumps(answer)}]}
            additions.append(record)
            catalog.append({'id':name,'variant':variant,'scheme':scheme,'family':record['family'],
                'source_path':str(path.relative_to(ROOT)),'source_sha256':record['source_sha256'],
                'target':'H02','target_assessment':assessment,
                'execution_policy':'no_callback_supplied_do_not_execute' if variant=='delegate' else 'authored_fixture_only'})
    dest=HERE/'data'; dest.mkdir(exist_ok=True)
    files={'train':previous['train']+additions,'validation':previous['validation'],'regression':previous['test'],'additions':additions}
    for split,rows in files.items():
        if split in ('validation','regression'):
            origin='test' if split=='regression' else split
            (dest/f'{split}.jsonl').write_bytes((V1/f'data/{origin}.jsonl').read_bytes())
        else: (dest/f'{split}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    manifest={'version':'multi-profile-v2-step1-draft','training_ready':False,
        'counts':{k:len(v) for k,v in files.items()}, 'sha256':{k:digest(dest/f'{k}.jsonl') for k in files},
        'v1_sha256':old['sha256'],'new_cases':catalog,
        'before_training_coverage':coverage(previous['train']),'after_training_coverage':coverage(files['train']),
        'readiness_blockers':['Most nontarget labels are still insufficient_context; full implementations and balanced labels are needed.',
            'H04 lacks targeted training examples for every FHE profile; several other profile/check cells are empty.',
            'New independently structured validation and held-out implementations are not prepared yet.'],
        'limitations':['All nine additions share one semantic family and remain in training; they are not nine independent implementations.',
            'Existing v1 test data is preserved byte-for-byte as regression, never imported into training.',
            'No new model output or evaluated test source was used as a label.',
            'An all-component comparison with locally known results is a narrow toy contract, not generic FHE authentication.']}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'version':manifest['version'],'counts':manifest['counts'],'training_ready':False},indent=2))

if __name__=='__main__': build()
