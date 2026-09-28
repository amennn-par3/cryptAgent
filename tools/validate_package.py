import copy, hashlib, json
from pathlib import Path
from schema_check import validate
from demo_backend import assess, local
ROOT=Path(__file__).resolve().parents[1]
def read(name): return json.loads((ROOT/name).read_text(encoding='utf-8'))
def expect_invalid(value,schema):
    try: validate(value,schema)
    except ValueError: return
    raise AssertionError('Invalid input was accepted')
def main():
    spec=read('phase2/examples/spec.json'); schema=read('phase2/schemas/spec.schema.json')
    validate(spec,schema)
    invalid=copy.deepcopy(spec); invalid['scheme']='AES'; expect_invalid(invalid,schema)
    invalid=copy.deepcopy(spec); invalid['limits']['key_bytes']=31; expect_invalid(invalid,schema)
    invalid=copy.deepcopy(spec); invalid['requirements'][0]=invalid['requirements'][1]; expect_invalid(invalid,schema)
    invalid=copy.deepcopy(spec); invalid['extra']='unapproved'; expect_invalid(invalid,schema)
    invalid=copy.deepcopy(spec); del invalid['profile_id']; expect_invalid(invalid,schema)
    req=read('phase2/examples/assess_request.json'); report,trace=assess(req)
    assert report['overall']=='inconclusive' and trace['suspected_authentication_issue']
    ref=copy.deepcopy(req); ref['source_path']='phase2/cpp/cryptagent.cpp'
    rr,rt=assess(ref); assert rr['overall']=='inconclusive' and not rt['suspected_authentication_issue']
    try: local('../escape.json')
    except ValueError: pass
    else: raise AssertionError('Traversal allowed')
    cases=read('phase3/manifest.json')['cases']; splits=read('phase3/splits.json')
    assert len(cases)==150 and len({c['case_id'] for c in cases})==150
    assert sum(c['kind']=='reference' for c in cases)==30
    assert sum(c['kind']=='single_defect' for c in cases)==90
    assert sum(c['kind']=='multiple_defects' for c in cases)==30
    groups={}
    for c in cases:
        assert hashlib.sha256((ROOT/c['source_path']).read_bytes()).hexdigest()==c['source_sha256'],c['case_id']
        assert read(str(Path(c['source_path']).parent/'case.json'))==c
        assert set(c['expected_violations'])<=set(spec['requirements'])
        groups.setdefault(c['scenario_group'],set()).add(c['split'])
        assert c['case_id'] in splits['cases'][c['split']]
    assert len(groups)==30 and all(len(s)==1 for s in groups.values())
    assert [len(splits['cases'][x]) for x in ['development','validation','heldout']]==[90,30,30]
    assert len(read('phase3/pilot.json')['case_ids'])==15
    # Parse every JSON, including schemas/labels; semantic checks above cover the contracts.
    count=0
    for path in ROOT.rglob('*.json'):
        if 'build' not in path.parts:
            json.loads(path.read_text(encoding='utf-8')); count+=1
    print(json.dumps({'package_validation':'passed','json_files_parsed':count,'cases':150,
      'negative_schema_checks':5,'demo_checks':2,'path_escape_check':'passed',
      'native_crypto_executed':False,'independent_implementation_generalization':False},indent=2))
if __name__=='__main__': main()
