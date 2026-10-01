"""Offline, assistant-only QLoRA pilot. Refuse truncation and existing output dirs."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['WANDB_DISABLED'] = 'true'
import torch
from transformers import Trainer, TrainingArguments, DataCollatorForSeq2Seq, set_seed
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from common import ROOT, MODEL, REVISION, load_model, messages

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--smoke', action='store_true'); ap.add_argument('--output', required=True)
    ap.add_argument('--experimental-draft', action='store_true',
        help='Permit only the pinned AES pilot draft for an explicitly experimental run; never imply dataset readiness.')
    ap.add_argument('--memory-lean', action='store_true',
        help='Use rank-8 query/value LoRA and no gradient accumulation for a 16 GiB GPU.')
    ap.add_argument('--epochs', type=float, default=2)
    ap.add_argument('--data', type=Path, required=True, help='Explicit reviewed AES-only dataset directory; no default historical dataset.')
    args = ap.parse_args()
    output = Path(args.output).resolve()
    if output.exists(): raise SystemExit('Use a fresh output directory; existing runs are preserved.')
    data_manifest = json.loads((args.data / 'manifest.json').read_text())
    if data_manifest.get('evaluation_only') is True:
        raise SystemExit('Evaluation-only dataset: never use held-out examples for training.')
    experimental_draft = args.experimental_draft and data_manifest.get('version') == 'aes-source-pilot-v1'
    if args.experimental_draft and not experimental_draft:
        raise SystemExit('--experimental-draft is limited to aes-source-pilot-v1.')
    if data_manifest.get('training_authorized') is False and not experimental_draft:
        raise SystemExit('Training has not been authorized for this dataset release.')
    if data_manifest.get('training_ready') is False and not experimental_draft:
        raise SystemExit('Dataset is a draft and not ready for retraining; see its manifest readiness_blockers.')
    if data_manifest.get('version') == 'aes-source-pilot-v1':
        for split, digest in data_manifest['sha256'].items():
            if hashlib.sha256((args.data / f'{split}.jsonl').read_bytes()).hexdigest() != digest:
                raise SystemExit('Dataset changed after audit: ' + split)
        if data_manifest['prompt_sha256'] != hashlib.sha256((ROOT / 'prompts/verify.txt').read_bytes()).hexdigest():
            raise SystemExit('Prompt changed after dataset audit.')
        if data_manifest['profile_sha256'] != hashlib.sha256((ROOT / 'profiles/aes128_gcm_tampering.json').read_bytes()).hexdigest():
            raise SystemExit('Profile changed after dataset audit.')
    # Active work is AES-only. Historical multi-profile runs remain on disk but
    # cannot silently become the next training run through this entry point.
    for split in ('train', 'validation'):
        for line in (args.data / f'{split}.jsonl').read_text().splitlines():
            row = json.loads(line)
            ids = [c['check_id'] for c in row['expected']['checks']]
            if row.get('profile_id', 'aes128-gcm-tampering-v1') != 'aes128-gcm-tampering-v1' or sorted(ids) != ['F01', 'F02', 'F03', 'F04', 'F05']:
                raise SystemExit('Only AES F01–F05 records are allowed in the active trainer. Mixed-scheme datasets are historical.')
            if row['messages'][:-1] != messages(row['source']):
                raise SystemExit('Training/runtime prompt mismatch: ' + row['id'])
            if json.loads(row['messages'][-1]['content']) != row['expected']:
                raise SystemExit('Assistant target differs from audited label: ' + row['id'])
    if not torch.cuda.is_available(): raise SystemExit('CUDA GPU required for this training configuration.')
    set_seed(42)
    tokenizer, model = load_model()
    datasets = {}
    for split in ('train', 'validation'):
        rows = [json.loads(line) for line in (args.data / f'{split}.jsonl').read_text().splitlines()]
        encoded = []
        for row in rows:
            full = tokenizer.apply_chat_template(row['messages'], tokenize=True, return_dict=False)
            prompt = tokenizer.apply_chat_template(row['messages'][:-1], tokenize=True, add_generation_prompt=True, return_dict=False)
            if full[:len(prompt)] != prompt: raise ValueError('Chat-template prefix mismatch')
            if len(full) > 3072: raise ValueError(f"Refusing to truncate {row['id']}: {len(full)} tokens")
            encoded.append({'input_ids': full, 'attention_mask': [1] * len(full), 'labels': [-100] * len(prompt) + full[len(prompt):]})
        datasets[split] = encoded
    print('Token lengths:', {s: [min(len(x['input_ids']) for x in rows), max(len(x['input_ids']) for x in rows)] for s, rows in datasets.items()}, flush=True)
    model = prepare_model_for_kbit_training(model, gradient_checkpointing_kwargs={'use_reentrant': False})
    lora_targets = ['q_proj', 'v_proj'] if args.memory_lean else ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']
    model = get_peft_model(model, LoraConfig(r=8 if args.memory_lean else 16, lora_alpha=16 if args.memory_lean else 32,
        lora_dropout=0.05, bias='none', task_type='CAUSAL_LM', target_modules=lora_targets))
    model.print_trainable_parameters(); model.config.use_cache = False
    probe_name, probe_weight = next((name, p) for name, p in model.named_parameters() if 'lora_B' in name)
    probe_before = probe_weight.detach().float().cpu().clone()
    config = TrainingArguments(output_dir=str(output), per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=1 if args.smoke or args.memory_lean else 4, num_train_epochs=args.epochs,
        max_steps=1 if args.smoke else -1, learning_rate=1e-4, lr_scheduler_type='cosine', warmup_steps=0 if args.smoke else 1,
        bf16=True, gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
        optim='paged_adamw_8bit', max_grad_norm=0.3, logging_steps=1, report_to='none',
        save_strategy='no' if args.smoke else 'epoch', save_total_limit=2, eval_strategy='no' if args.smoke else 'epoch',
        seed=42, dataloader_num_workers=0)
    train_rows = [max(datasets['train'], key=lambda row: len(row['input_ids']))] if args.smoke else datasets['train']
    trainer = Trainer(model=model, args=config, train_dataset=train_rows, eval_dataset=datasets['validation'],
        processing_class=tokenizer, data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100))
    result = trainer.train()
    if not torch.isfinite(torch.tensor(result.training_loss)): raise RuntimeError('Nonfinite training loss')
    probe_delta = (probe_weight.detach().float().cpu() - probe_before).abs().max().item()
    if not probe_delta > 0: raise RuntimeError('LoRA weight did not change; training step was not verified')
    trainer.save_model(str(output / 'adapter')); tokenizer.save_pretrained(output / 'adapter')
    metadata = {'base_model': MODEL, 'base_revision': REVISION, 'smoke_only': args.smoke,
        'experimental_unreviewed_pilot': experimental_draft, 'memory_lean': args.memory_lean,
        'dataset': json.loads((args.data / 'manifest.json').read_text()),
        'prompt_sha256': hashlib.sha256((ROOT / 'prompts/verify.txt').read_bytes()).hexdigest(),
        'multi_prompt_sha256': hashlib.sha256((ROOT / 'prompts/verify_multi.txt').read_bytes()).hexdigest(),
        'profile_sha256': hashlib.sha256((ROOT / 'profiles/aes128_gcm_tampering.json').read_bytes()).hexdigest(),
        'gpu': torch.cuda.get_device_name(0), 'peak_vram_gib': torch.cuda.max_memory_allocated() / 2**30,
        'weight_update_probe': {'parameter': probe_name, 'maximum_absolute_change': probe_delta},
        'packages': {p: importlib.metadata.version(p) for p in ('torch', 'transformers', 'peft', 'bitsandbytes', 'accelerate')},
        'metrics': result.metrics, 'training_args': config.to_dict(), 'log_history': trainer.state.log_history}
    (output / 'run.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'metrics': result.metrics, 'peak_vram_gib': metadata['peak_vram_gib']}, indent=2), flush=True)

if __name__ == '__main__': main()
