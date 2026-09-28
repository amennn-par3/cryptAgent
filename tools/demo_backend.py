"""Non-executing source-pattern demonstration. No LLM and no crypto verification."""
import argparse, hashlib, json
from pathlib import Path
from schema_check import validate
ROOT=Path(__file__).resolve().parents[1]
def local(path):
    p=(ROOT/path).resolve()
    if not p.is_relative_to(ROOT): raise ValueError('Path escapes cryptagent')
    return p
def read(path): return json.loads(local(path).read_text(encoding='utf-8'))
def assess(request):
    validate(request,read('phase2/schemas/request.schema.json'))
    if request['mode']!='assess': raise ValueError('Demo implements assess mode only')
    spec=read(request['spec_path'])
    validate(spec,read('phase2/schemas/spec.schema.json'))
    if request['profile_id']!=spec['profile_id']: raise ValueError('Profile mismatch')
    source=local(request['source_path']).read_bytes()
    text=source.decode('utf-8')
    suspicious='crypto_aead_xchacha20poly1305_ietf_decrypt(' in text and '(void)rc;' in text
    report={'schema_version':'1.0','mode':'demonstration','profile_id':request['profile_id'],
      'source_sha256':hashlib.sha256(source).hexdigest(),'overall':'inconclusive','execution':'not_executed',
      'results':[{'requirement_id':rid,'status':'inconclusive',
        'evidence_type':'static_heuristic' if suspicious and rid in ['C-04','E-01'] else 'none',
        'summary':'Suspected ignored authentication result; needs confirmed evidence.' if suspicious and rid in ['C-04','E-01'] else 'Required checks have not been executed.',
        'artifacts':['trace.json'] if suspicious and rid in ['C-04','E-01'] else []} for rid in spec['requirements']],
      'limitations':['No candidate execution or LLM call.','A narrow source pattern is not a verifier.','Missing native, memory, cleanup and timing evidence.']}
    validate(report,read('phase2/schemas/report.schema.json'))
    return report, {'events':['request_schema_valid','spec_schema_valid','profile_matched','source_hashed','heuristic_pattern_checked','verdict_inconclusive'],
                    'suspected_authentication_issue':suspicious,'candidate_executed':False}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--request',required=True); ap.add_argument('--out',default='demo-output'); args=ap.parse_args()
    report,trace=assess(read(args.request)); out=local(args.out); out.mkdir(parents=True,exist_ok=True)
    for name,value in [('report.json',report),('trace.json',trace)]:
        (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'overall':report['overall'],'candidate_executed':False,'suspected_issue':trace['suspected_authentication_issue'],'output':str(out)},indent=2))
if __name__=='__main__': main()
