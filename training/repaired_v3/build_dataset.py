"""Curated replacement, not an append-only expansion. Never uses evaluation for training."""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'training'))
from common import messages
spec=importlib.util.spec_from_file_location('definitions',ROOT/'training/expanded/build_dataset.py')
definitions=importlib.util.module_from_spec(spec); spec.loader.exec_module(definitions)
spec=importlib.util.spec_from_file_location('validator',ROOT/'training/expanded/validate_dataset.py')
validator=importlib.util.module_from_spec(spec); spec.loader.exec_module(validator)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return [json.loads(line) for line in path.read_text().splitlines()]

def build():
    ap=argparse.ArgumentParser(); ap.add_argument('--evidence',type=Path,required=True)
    evidence_path=ap.parse_args().evidence.resolve()
    evidence=json.loads(evidence_path.read_text())
    assert evidence['passed'] and len(evidence['cases'])==18
    old=ROOT/'training/expanded_v2/step2/data'
    old_manifest=json.loads((old/'manifest.json').read_text())
    assert sha(old/'train.jsonl')==old_manifest['sha256']['train']
    fresh=ROOT/'training/evaluation_v2/data'
    frozen=json.loads((fresh/'FREEZE.json').read_text())
    assert sha(fresh/'manifest.json')==frozen['manifest_sha256']
    for split in ('validation','test'): assert sha(fresh/f'{split}.jsonl')==frozen['dataset_sha256'][split]
    previous=read(old/'train.jsonl')
    train=[]; seen=set(); removed=[]
    for row in previous:
        normalized=' '.join(row['source'].split())
        if normalized in seen:
            removed.append(dict(id=row['id'],reason='whitespace_duplicate'))
            continue
        seen.add(normalized)
        if row['profile_id'].startswith('aes') or row['id'].endswith('_delegate'):
            train.append(row)
        else:
            removed.append(dict(id=row['id'],reason='partial_FHE_excerpt_superseded_by_complete_workflows'))
    fhe_good={
        'H01':'The shown valid integer domain is 0..100; encrypted addition represents its sum without overflow. CKKS uses explicit tolerance.',
        'H02':'The decrypted result is checked against the locally known sum; a changed result is not accepted. This is a toy local-reference check.',
        'H03':'The shown evaluator bundle contains no client/decryption key. Plaintext input and decrypted audit results remain client-local.',
        'H04':'The library profile parameters and required evaluation context are configured; encryption and decryption use the same key context.',
        'H05':'Both operands are checked against the documented bounded domain before key generation and encryption.'}
    bad_reasons={
        'arithmetic':'Subtraction is evaluated although the contract requires addition, so valid nonzero operands produce the wrong result.',
        'acceptance':'Acceptance ignores the independently known reference, including when the evaluator modifies the ciphertext result.',
        'secret':'The bundle provided to the untrusted evaluator includes the client/decryption key.',
        'setup':'The required context initialization is missing, so valid inputs fail before completing the requested encrypted computation.',
        'bounds':'Out-of-domain operands reach encryption and evaluation without the required range check.'}
    quotes={
        'ckks':{'arithmetic':'encrypted = a - b','acceptance':'accepted = True','secret':'save_secret_key=True',
                'setup':'a = ts.ckks_vector_from(worker, ts.ckks_vector(client, [left]).serialize())','bounds':'client = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,'},
        'tfhe':{'arithmetic':'let mut encrypted = &a - &b;','acceptance':'let accepted = true;',
                'secret':'client: Some(client.clone())','setup':'drop(bundle.server);',
                'bounds':'let (client, server) = generate_keys(ConfigBuilder::default().build());'},
        'bfv':{'arithmetic':'auto encrypted = cc->EvalSub(a, b);','acceptance':'bool accepted = true;',
               'secret':'WorkerBundle bundle{keys.publicKey, keys.secretKey};','setup':'auto keys = cc->KeyGen();',
               'bounds':'auto a = cc->Encrypt(bundle.publicKey, cc->MakePackedPlaintext({left}));'}}
    catalog=[]
    def record(name,path,profile,prefix,good,issues,unknown,family,native):
        source=path.read_text(); findings=[]; checks=[]
        for i in range(1,6):
            cid=f'{prefix}0{i}'
            if cid in issues:
                quote,reason=issues[cid]
                line=next(i+1 for i,text in enumerate(source.split('\n')) if quote in text)
                findings.append(dict(check_id=cid,line_start=line,line_end=line,quote=quote,rationale=reason))
                status='potential_issue'
            elif cid in unknown:
                reason=unknown[cid]; status='insufficient_context'
            else:
                reason=good[cid]; status='no_issue_identified'
            checks.append(dict(check_id=cid,assessment=status,reason=reason))
        answer=dict(scope='in_scope',checks=checks,findings=findings)
        validator.validate_answer(answer,source,[f'{prefix}0{i}' for i in range(1,6)])
        row=dict(id='v3_'+name,family=family,split='train',profile_id=profile['id'],source=source,
                 source_sha256=sha(path),expected=answer,label_origin='authored_complete_source_review',
                 native_evidence_status=native,
                 messages=messages(source,profile,ROOT/'prompts/verify_multi.txt')+[dict(role='assistant',content=json.dumps(answer))])
        train.append(row)
        catalog.append(dict(id=row['id'],source_path=str(path.relative_to(ROOT)),source_sha256=sha(path),native_evidence_status=native))
    for scheme in ('ckks','tfhe','bfv'):
        for variant in ('correct','arithmetic','acceptance','secret','setup','bounds'):
            name=scheme+'_'+variant; path=HERE/'cases'/(name+{'ckks':'.py','tfhe':'.rs','bfv':'.hpp'}[scheme])
            witness=next(c for c in evidence['cases'] if c['id']==name)
            assert witness['matches_expected_behavior'] and witness['source_sha256']==sha(path)
            issues={}; unknown={}
            if variant!='correct':
                cid={'arithmetic':'H01','acceptance':'H02','secret':'H03','setup':'H04','bounds':'H05'}[variant]
                issues[cid]=(quotes[scheme][variant],bad_reasons[variant])
            if variant=='setup':
                issues['H01']=(quotes[scheme][variant],bad_reasons[variant])
                unknown['H02']='The evaluation path cannot complete because setup fails; runtime result acceptance was not exercised.'
            record(name,path,definitions.PROFILES[scheme],'H',fhe_good,issues,unknown,'full-addition-workflow-v3','native_witnesses_passed')
    aes=json.loads((ROOT/'profiles/aes128_gcm_tampering.json').read_text())
    aes_good={'F01':'The complete bounded encrypt/decrypt paths preserve message length, including zero length; runtime confirmation is pending.',
              'F02':'Nonce, tag and AAD are supplied to GCM; negative decryption status is rejected. Native tamper tests are pending.',
              'F03':'Output is cleared first and assigned only after successful authentication; rejected scratch is wiped.',
              'F04':'A 16-byte key, 12-byte nonce and 16-byte tag are used; the single-threaded, noncopyable session consumes a nonwrapping nonce counter.',
              'F05':'Length bounds precede ULONG casts and output allocation; advertised capacity matches the allocated buffer.'}
    aes_issues={
        'empty':{'F01':('if(plain.empty()) return false;','Valid zero-length plaintext is rejected by the encryption wrapper.')},
        'authentication':{'F02':('status=0;','The authentication result is overwritten; length checks are not substitutes for checking authentication status.'),
                          'F03':('status=0;','Discarding authentication status can allow publication without confirmed authentication.')},
        'publication':{'F03':('output=scratch;','Caller output is populated before authentication status is checked and remains populated on rejection.')},
        'keysize':{'F04':('std::array<BYTE,32> material{};','The key has 32 bytes rather than the required 16-byte AES-128 key.')},
        'bounds':{'F05':('packet.ciphertext.resize(plain.size());','Encryption does not enforce the documented length bounds before allocation and narrowing lengths to ULONG.')}}
    for variant in ('correct','empty','authentication','publication','keysize','bounds'):
        name='aes_'+variant
        record(name,HERE/'cases'/(name+'.hpp'),aes,'F',aes_good,aes_issues.get(variant,{}),{},
               'complete-cng-session-v3','not_run_no_native_windows')
    # Reserve every old evaluation row as well as the frozen new evaluation.
    reserved=read(old/'validation.jsonl')+read(old/'regression.jsonl')+read(fresh/'validation.jsonl')+read(fresh/'test.jsonl')
    reserved_sources={' '.join(r['source'].split()) for r in reserved}
    reserved_families={r['family'] for r in reserved}
    seen=set(); ids=set()
    for row in train:
        normalized=' '.join(row['source'].split())
        assert normalized not in seen and normalized not in reserved_sources
        assert row['family'] not in reserved_families and row['id'] not in ids
        seen.add(normalized); ids.add(row['id'])
        prefix='F' if row['profile_id'].startswith('aes') else 'H'
        validator.validate_answer(row['expected'],row['source'],[f'{prefix}0{i}' for i in range(1,6)])
    dest=HERE/'data'; dest.mkdir(exist_ok=True)
    (dest/'train.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in train))
    for split in ('validation','test'): (dest/f'{split}.jsonl').write_bytes((fresh/f'{split}.jsonl').read_bytes())
    (dest/'regression.jsonl').write_bytes((old/'regression.jsonl').read_bytes())
    labels=collections.Counter(c['assessment'] for r in train for c in r['expected']['checks'])
    cells={}
    for row in train:
        for c in row['expected']['checks']:
            cells.setdefault(row['profile_id']+'/'+c['check_id'],collections.Counter())[c['assessment']]+=1
    assert all(c.get('potential_issue',0)>0 and c.get('no_issue_identified',0)>0 for c in cells.values())
    manifest=dict(version='curated-repair-v3',training_ready=False,training_authorized=False,
        counts={'train':len(train),'validation':6,'test':6,'regression':10},
        sha256={s:sha(dest/f'{s}.jsonl') for s in ('train','validation','test','regression')},
        parent_train_sha256=sha(old/'train.jsonl'),evaluation_freeze_sha256=sha(fresh/'FREEZE.json'),
        native_evidence_sha256=sha(evidence_path),new_sources=catalog,removed_from_new_release=removed,
        training_label_counts=dict(labels),coverage={k:dict(v) for k,v in cells.items()},
        readiness_blockers=['AES sources lack native Windows CNG evidence; no Windows machine is available.',
            'Frozen fresh evaluation covers only H03 validation and H05 test; broader evaluation is still needed.',
            'User has explicitly reserved training authorization for a later instruction.'],
        limitations=['Same-author synthetic workflows; variants are not independent implementations.',
            'Complete FHE workflows exercise a locally known-answer toy sum, not generic verifiable computation.',
            'AES no-issue labels describe source review only, not a native security certification.',
            'Existing evaluation sets stay reserved; no examples were moved from evaluation into training.'])
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'counts':manifest['counts'],'training_labels':dict(labels),'training_ready':False},indent=2))

if __name__=='__main__': build()
