"""Offline, source-only comparison of the cached base model and AES pilot adapter.

Never executes submitted C++ or modifies training data. Raw outputs are retained
even when malformed. Production validation/scoring is run separately afterward.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'training'))
from common import MODEL, REVISION, load_model, messages
from cases import CASES

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--adapter', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    adapter = args.adapter.resolve()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit('Use a new output path; previous comparisons are preserved.')
    run = json.loads((adapter.parent / 'run.json').read_text())
    if run['base_revision'] != REVISION or run['smoke_only'] or not run['experimental_unreviewed_pilot']:
        raise SystemExit('Wrong adapter or smoke-only run.')
    previous = [json.loads(line) for split in ('train', 'validation', 'test')
                for line in (ROOT / f'training/aes_source_pilot_v1/data/{split}.jsonl').read_text().splitlines()]
    prior = {re.sub(r'\s+', '', row['source']) for row in previous}
    current = [re.sub(r'\s+', '', c['source']) for c in CASES]
    if len(CASES) != 20 or len(set(current)) != 20 or any(s in prior for s in current):
        raise SystemExit('Case count, duplicate, or exact source-overlap check failed.')
    for c in CASES:
        for check, quote in {**c['issues'], **c['controls'], **c['abstentions']}.items():
            if check not in ('F01', 'F02', 'F03', 'F04', 'F05') or quote not in c['source']:
                raise SystemExit('Invalid target quote in ' + c['id'])
        if (set(c['issues']) & set(c['controls'])) or (set(c['issues']) & set(c['abstentions'])) or (set(c['controls']) & set(c['abstentions'])):
            raise SystemExit('Conflicting target in ' + c['id'])
    import torch
    if not torch.cuda.is_available():
        raise SystemExit('CUDA required; stop the CryptAgent model service before this comparison.')
    tokenizer, model = load_model()
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, adapter, local_files_only=True)
    model.eval()
    metadata = dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    base_model=MODEL, base_revision=REVISION,
                    adapter=str(adapter), adapter_sha256=digest((adapter / 'adapter_model.safetensors').read_bytes()),
                    cases_sha256=digest((Path(__file__).with_name('cases.py')).read_bytes()),
                    prompt_sha256=digest((ROOT / 'prompts/verify.txt').read_bytes()),
                    profile_sha256=digest((ROOT / 'profiles/aes128_gcm_tampering.json').read_bytes()),
                    training_overlap='no_exact_or_whitespace_normalized_source_overlap',
                    test_policy='not_training_data; synthetic source-only review; no native Windows execution',
                    results=[])
    out.mkdir(parents=True)
    def save():
        (out / 'raw_results.json').write_text(json.dumps(metadata, indent=2) + '\n')
    for index, c in enumerate(CASES, 1):
        row = dict(c, source_sha256=digest(c['source'].encode()), predictions={})
        prompt = tokenizer.apply_chat_template(messages(c['source']), tokenize=False, add_generation_prompt=True)
        batch = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to('cuda')
        tokens = batch['input_ids'].shape[1]
        row['prompt_tokens'] = tokens
        for mode in ('base', 'adapter'):
            if tokens > 3072:
                row['predictions'][mode] = {'state': 'skipped_context_limit'}
                continue
            started = time.monotonic()
            context = model.disable_adapter() if mode == 'base' else contextlib.nullcontext()
            try:
                with context, torch.inference_mode():
                    result = model.generate(**batch, max_new_tokens=1536, max_time=90,
                        do_sample=False, use_cache=True, pad_token_id=tokenizer.pad_token_id)
                generated = result[0, tokens:]
                eos = model.generation_config.eos_token_id
                eos = eos if isinstance(eos, list) else [eos]
                complete = bool(len(generated) and generated[-1].item() in eos)
                row['predictions'][mode] = dict(state='completed' if complete else 'incomplete',
                    text=tokenizer.decode(generated, skip_special_tokens=True),
                    new_tokens=len(generated), seconds=round(time.monotonic() - started, 2))
            except Exception as error:
                row['predictions'][mode] = dict(state='error', error=type(error).__name__ + ': ' + str(error),
                                                seconds=round(time.monotonic() - started, 2))
            print(f'{index:02d}/20 {c["id"]} {mode}: {row["predictions"][mode]["state"]} '
                  f'{row["predictions"][mode].get("seconds", 0)}s', flush=True)
        metadata['results'].append(row)
        save()
    print('Saved', out / 'raw_results.json', flush=True)

if __name__ == '__main__':
    main()
