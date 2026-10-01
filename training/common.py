"""Shared offline model configuration and exact application prompt formatting."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "meta-llama/Llama-3.1-8B-Instruct"
REVISION = "0e9e39f249a16976918f6564b8830bc894c89659"

def messages(source, profile=None, prompt_path=None):
    profile = profile or json.loads((ROOT / 'profiles/aes128_gcm_tampering.json').read_text())
    selected = {k: profile[k] for k in ('scheme', 'library', 'attacker', 'checks')}
    if 'language' in profile: selected['language'] = profile['language']
    if 'parameters' in profile: selected['parameters'] = profile['parameters']
    for key in ('keyBytes', 'nonceBytes', 'tagBytes'):
        if key in profile: selected[key] = profile[key]
    selected['profile_id'] = profile['id']
    return [
        {'role': 'system', 'content': (prompt_path or ROOT / 'prompts/verify.txt').read_text() + '\nProfile:\n' + json.dumps(selected)},
        {'role': 'user', 'content': json.dumps({'untrusted_source': [{'line': i + 1, 'text': line} for i, line in enumerate(source.split('\n'))]})},
    ]

def load_model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, local_files_only=True, device_map={'': 0},
        dtype=torch.bfloat16, attn_implementation='sdpa',
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16))
    return tokenizer, model
