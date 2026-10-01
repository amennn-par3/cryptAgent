"""New reviewed AES-only release; never rewrite historical data or multiply whitespace."""
import copy
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from common import ROOT, MODEL, REVISION, messages

DEST = ROOT / 'training/aes_source_pilot_v1/data'
PROFILE = 'aes128-gcm-tampering-v1'

def sha(value): return hashlib.sha256(value).hexdigest()

def update(row, cid, status, reason):
    check = next(c for c in row['expected']['checks'] if c['check_id'] == cid)
    check.update(assessment=status, reason=reason)
    if status != 'potential_issue':
        row['expected']['findings'] = [f for f in row['expected']['findings'] if f['check_id'] != cid]
    else:
        for f in row['expected']['findings']:
            if f['check_id'] == cid: f['rationale'] = reason

def main():
    if DEST.exists(): raise SystemExit('Release already exists; preserve it and make a new version.')
    inputs = {'train': ROOT / 'training/repaired_v3/data/train.jsonl',
              'validation': ROOT / 'training/data/validation.jsonl', 'test': ROOT / 'training/data/test.jsonl'}
    rows = {split: [copy.deepcopy(r) for r in map(json.loads, path.read_text().splitlines())
                   if r.get('profile_id', PROFILE) == PROFILE] for split, path in inputs.items()}
    for split, records in rows.items():
        for row in records:
            row['profile_id'] = PROFILE
            row['split'] = split
            row['native_evidence_status'] = 'not_run_no_native_windows'
            row['provenance'] = {'source_dataset': str(inputs[split].relative_to(ROOT)),
                'source_dataset_sha256': sha(inputs[split].read_bytes()), 'source_record_id': row['id'],
                'origin': 'project_authored_synthetic', 'review': 'static_source_review_2026-10-01',
                'not_an_independent_real_world_benchmark': True}
            # Avoid teaching that missing integration/lifecycle context is a proven defect.
            if row['id'] == 'counter_reset-0':
                update(row, 'F04', 'potential_issue', 'The counter is reset on every call. If the helper uses this nonce unchanged with the documented persistent session key, repeated encryption reuses the nonce; inspect the omitted helper to confirm.')
            if row['id'] == 'fixed_nonce-0':
                update(row, 'F04', 'potential_issue', 'A zero nonce is passed unchanged to BCryptEncrypt. Repeating this path under the same key would reuse a nonce; the omitted key lifecycle must be checked before concluding that reuse occurred.')
            if row['id'] == 'omitted_aad-0':
                update(row, 'F02', 'insufficient_context', 'The call authenticates no AAD. Empty AAD is valid; only a comment mentions caller AAD. The caller contract and actual AAD input are missing, so omission of required authenticated data is not established.')
            if row['id'] == 'capacity_lie-0':
                update(row, 'F05', 'potential_issue', 'For ciphertext longer than eight bytes, the advertised output capacity exceeds the eight-byte allocation. No bound establishing ciphertext.size() <= 8 is visible in this excerpt.')
            if row['id'] == 'reject_empty-0':
                update(row, 'F01', 'insufficient_context', 'The wrapper rejects empty input. GCM supports empty messages, but the supported-input contract is omitted; determine whether this wrapper is required to accept them before classifying a functional defect.')
            if row['id'].startswith('v3_aes_'):
                for check in row['expected']['checks']:
                    if check['assessment'] != 'no_issue_identified': continue
                    concise = {'F02': 'GCM receives nonce, tag and AAD; negative decryption status is rejected. Native tamper tests have not run.',
                               'F03': 'Output is cleared first and assigned only after successful status and length checks; rejected scratch is wiped.',
                               'F04': 'The shown single-threaded, noncopyable session uses a fresh 16-byte key, a nonwrapping 12-byte nonce counter and a 16-byte tag.'}
                    if check['check_id'] in concise: check['reason'] = concise[check['check_id']]
                if row['id'] != 'v3_aes_empty':
                    update(row, 'F01', 'insufficient_context', 'The decrypt API lacks an aliasing contract; output.clear() could alter ciphertext or AAD.')
                if row['id'] == 'v3_aes_authentication':
                    update(row, 'F02', 'potential_issue', 'Decryption status is overwritten before authentication failure is checked.')
                    update(row, 'F03', 'potential_issue', 'Output may be published without confirmed authentication.')
                if row['id'] != 'v3_aes_bounds':
                    update(row, 'F05', 'no_issue_identified', 'Visible bounds precede narrowing and allocation; CNG capacities match buffers.')
                if row['id'] == 'v3_aes_empty':
                    update(row, 'F01', 'potential_issue', 'This bounded session rejects empty plaintext despite its stated zero-to-4096-byte range.')
            row['messages'] = messages(row['source']) + [{'role': 'assistant', 'content': json.dumps(row['expected'], separators=(',', ':'))}]
            row['source_sha256'] = sha(row['source'].encode())
    # Keep every full-session mutation in one split. Exact/whitespace duplicates are forbidden.
    seen = {}; families = {}
    for split, records in rows.items():
        for row in records:
            key = re.sub(r'\s+', '', row['source'])
            if key in seen: raise ValueError('Duplicate source: ' + row['id'])
            seen[key] = row['id']
            family = row['family']
            if family in families and families[family] != split: raise ValueError('Family split leakage')
            families[family] = split
    flat = [r for records in rows.values() for r in records]
    scored = subprocess.run([str(ROOT / 'runtime/node-v22.23.3-linux-x64/bin/node'), str(ROOT / 'training/score_aes.mjs')],
        input=json.dumps([{**r, 'output': json.dumps(r['expected'])} for r in flat]), text=True, capture_output=True, check=True)
    audit = json.loads(scored.stdout)
    if any(not r['valid'] or not r['exact'] or r['state'] != 'completed' for r in audit):
        raise ValueError('Target fails production validator: ' + json.dumps([r for r in audit if not r['valid'] or not r['exact'] or r['state'] != 'completed']))
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, local_files_only=True)
    lengths = {}
    for row in flat:
        tokens = tokenizer.apply_chat_template(row['messages'], tokenize=True, return_dict=False)
        lengths[row['id']] = len(tokens)
        if len(tokens) > 3072: raise ValueError(f"Refusing truncation: {row['id']} has {len(tokens)} tokens")
    DEST.mkdir(parents=True)
    hashes = {}
    for split, records in rows.items():
        data = ''.join(json.dumps(r) + '\n' for r in records)
        (DEST / f'{split}.jsonl').write_text(data)
        hashes[split] = sha(data.encode())
    manifest = {'version': 'aes-source-pilot-v1', 'training_ready': False, 'training_authorized': False,
        'readiness_blockers': ['Independent full-session label review and fresh evaluation split remain outstanding.',
            'Training was deferred by the owner while selecting the appropriate dataset.'],
        'readiness_scope': 'Candidate AES source-review pilot, not production/security validation.',
        'profile_id': PROFILE, 'counts': {s: len(v) for s, v in rows.items()},
        'sha256': hashes, 'prompt_sha256': sha((ROOT / 'prompts/verify.txt').read_bytes()),
        'profile_sha256': sha((ROOT / 'profiles/aes128_gcm_tampering.json').read_bytes()),
        'token_lengths': lengths, 'normalized_unique_sources': len(seen),
        'families': {s: sorted({r['family'] for r in v}) for s, v in rows.items()},
        'train_assessment_counts': dict(Counter(c['assessment'] for r in rows['train'] for c in r['expected']['checks'])),
        'limitations': ['Synthetic excerpts and six related full-session variants; not 30 independent projects.',
            'Validation/test are historical development sets, excluded from this run but previously inspected in project experiments.',
            'Most omitted-context checks abstain; no whole-program secure/insecure labels are inferred.',
            'No native Windows execution. Dataset is too small for a generalization claim.']}
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__': main()
