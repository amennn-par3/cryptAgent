import ast
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def validate_answer(answer, source, ids):
    assert type(answer) is dict and set(answer)=={'scope','checks','findings'}
    assert answer['scope'] in ('in_scope','outside_scope','unclear')
    assert type(answer['checks']) is list and len(answer['checks'])==len(ids)
    assert {c['check_id'] for c in answer['checks']}==set(ids)
    assert len(answer['findings'])<=8
    assessments={}
    for check in answer['checks']:
        assert set(check)=={'check_id','assessment','reason'}
        assert check['assessment'] in ('potential_issue','no_issue_identified','insufficient_context','not_applicable')
        assert isinstance(check['reason'],str) and 0<len(check['reason'])<=800
        assessments[check['check_id']]=check['assessment']
    for f in answer['findings']:
        assert set(f)=={'check_id','line_start','line_end','quote','rationale'}
        assert type(f['line_start']) is int and type(f['line_end']) is int
        assert 1<=f['line_start']<=f['line_end']<=len(source.split('\n'))
        assert f['line_end']-f['line_start']<8
        assert isinstance(f['quote'],str) and 0<len(f['quote'])<=1200
        assert f['quote'] in '\n'.join(source.split('\n')[f['line_start']-1:f['line_end']])
        assert isinstance(f['rationale'],str) and 0<len(f['rationale'])<=800
        assert assessments[f['check_id']]=='potential_issue'
    for cid,status in assessments.items():
        if status=='potential_issue': assert any(f['check_id']==cid for f in answer['findings'])
    if answer['scope']=='outside_scope':
        assert not answer['findings'] and all(s=='not_applicable' for s in assessments.values())
    else: assert 'not_applicable' not in assessments.values()

def main():
    manifest=json.loads((HERE/'data/manifest.json').read_text())
    families={}; hashes={}; counts={}
    for split in ('train','validation','test'):
        path=HERE/f'data/{split}.jsonl'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['sha256'][split]
        rows=[json.loads(line) for line in path.read_text().splitlines()]; counts[split]=len(rows)
        assert len(rows)==manifest['counts'][split]
        for row in rows:
            assert families.setdefault(row['family'],split)==split
            assert hashes.setdefault(row['source_sha256'],split)==split
            assert hashlib.sha256(row['source'].encode()).hexdigest()==row['source_sha256']
            ids=[f'F0{i}' for i in range(1,6)] if row['profile_id'].startswith('aes') else [f'H0{i}' for i in range(1,6)]
            validate_answer(row['expected'],row['source'],ids)
            assert json.loads(row['messages'][-1]['content'])==row['expected']
            reconstructed='\n'.join(line['text'] for line in json.loads(row['messages'][-2]['content'])['untrusted_source'])
            assert reconstructed==row['source']
    for path in (HERE/'cases').glob('*.py'): ast.parse(path.read_text())
    print(json.dumps({'validation':'passed','counts':counts,'family_split_disjoint':True,'source_hashes_and_quotes':'passed'},indent=2))

if __name__=='__main__': main()
