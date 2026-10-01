"""Offline base-vs-adapter comparison on the frozen held-out set.

Save raw outputs, validation failures, timing and provenance separately from labels.
No CPU fallback, no hosted API, and no generated label enters training automatically.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ['HF_HUB_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'training'))
from common import MODEL, REVISION, load_model
from validate_dataset import validate_answer

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True)
    ap.add_argument('--adapter',type=Path); args=ap.parse_args()
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    test=HERE/'data/test.jsonl'; rows=[json.loads(line) for line in test.read_text().splitlines()]
    metadata={'base_model':MODEL,'revision':REVISION,'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),
              'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'adapter':str(args.adapter.resolve()) if args.adapter else None,'results':[]}
    def save(): (out/'comparison.json').write_text(json.dumps(metadata,indent=2)+'\n')
    try:
        import torch
        if not torch.cuda.is_available(): raise RuntimeError('CUDA unavailable: diagnose driver/device access before training or inference')
        torch.ones(4,device='cuda').sum().item()
        metadata['cuda_preflight']='passed'
    except Exception as exc:
        metadata['cuda_preflight']='failed'; metadata['error']=str(exc)
        for row in rows:
            metadata['results'].append({'id':row['id'],'source_sha256':row['source_sha256'],
                'base':{'status':'not_run','reason':'CUDA preflight failed'},
                'fine_tuned':{'status':'not_run','reason':'CUDA preflight failed; no trained adapter supplied' if not args.adapter else 'CUDA preflight failed'}})
        save(); print(json.dumps({'status':'blocked','reason':metadata['error'],'out':str(out)},indent=2)); return
    tokenizer,model=load_model(); model.eval()
    if args.adapter:
        from peft import PeftModel
        run=json.loads((args.adapter.parent/'run.json').read_text())
        if run.get('smoke_only'): raise ValueError('Smoke-test adapter is not a trained comparison candidate')
        if run['base_revision']!=REVISION: raise ValueError('Adapter base revision mismatch')
        manifest=json.loads((HERE/'data/manifest.json').read_text())
        if run['dataset']['sha256']!=manifest['sha256']: raise ValueError('Dataset version mismatch')
        model=PeftModel.from_pretrained(model,args.adapter,local_files_only=True); model.eval()
        metadata['adapter_files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.adapter.iterdir() if p.is_file()}
    for row in rows:
        record={'id':row['id'],'source_sha256':row['source_sha256'],'profile_id':row['profile_id']}
        for mode in ('base','fine_tuned'):
            if mode=='fine_tuned' and not args.adapter:
                record[mode]={'status':'not_run','reason':'No trained adapter supplied'}; continue
            started=time.monotonic()
            prompt=tokenizer.apply_chat_template(row['messages'][:-1],tokenize=False,add_generation_prompt=True)
            batch=tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to('cuda')
            if batch['input_ids'].shape[1]>4608:
                record[mode]={'status':'not_run','reason':'Context limit; no source truncated'}; continue
            adapter_context=model.disable_adapter() if args.adapter and mode=='base' else contextlib.nullcontext()
            with adapter_context, torch.inference_mode():
                generated=model.generate(**batch,max_new_tokens=1536,do_sample=False,use_cache=True,
                    pad_token_id=tokenizer.pad_token_id,max_time=180)
            text=tokenizer.decode(generated[0,batch['input_ids'].shape[1]:],skip_special_tokens=True)
            result={'raw_output':text,'seconds':time.monotonic()-started,'status':'invalid_response'}
            try:
                parsed=json.loads(text)
                ids=[c['check_id'] for c in row['expected']['checks']]
                validate_answer(parsed,row['source'],ids)
                expected={c['check_id']:c['assessment'] for c in row['expected']['checks']}
                result.update(status='completed',response=parsed,scope_match=parsed['scope']==row['expected']['scope'],
                    matched_checks=sum(c['assessment']==expected[c['check_id']] for c in parsed['checks']))
            except (ValueError,AssertionError,TypeError,KeyError) as exc:
                result['validation_error']=type(exc).__name__+': '+str(exc)
            record[mode]=result
            print(row['id'],mode,result['status'],flush=True)
        metadata['results'].append(record); save()
    metadata['limitations']=['Tiny synthetic held-out set; no broad accuracy claim.','Validation is structural and source-referential; model interpretations remain unconfirmed.']
    save()

if __name__=='__main__': main()
