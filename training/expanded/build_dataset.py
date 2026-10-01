"""Versioned multi-profile pilot. Pair members are never split across sets."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'training'))
from common import messages

HERE = Path(__file__).resolve().parent
CHECKS = [
    {'id': 'H01', 'title': 'Functional and numerical correctness', 'requirement': 'Honor the application arithmetic domain; CKKS comparisons use explicit tolerance and integer schemes respect their modulus.'},
    {'id': 'H02', 'title': 'Untrusted result handling', 'requirement': 'When the application requires correct results from an untrusted evaluator, do not equate decryptability with correct computation. In these toy jobs, compare to the independently known expected result.'},
    {'id': 'H03', 'title': 'Secret-key and plaintext boundaries', 'requirement': 'Do not send client/private/decryption keys or confidential plaintext to an untrusted evaluator. Public/evaluation/server keys may be shared.'},
    {'id': 'H04', 'title': 'Parameter and context handling', 'requirement': 'Use library security presets and compatible keys/contexts. Assess visible configuration; omitted setup is insufficient context.'},
    {'id': 'H05', 'title': 'Input and resource bounds', 'requirement': 'Enforce the documented input domain and resource budget before encryption, allocation or processing.'},
]
PROFILES = {
    'ckks': {'id': 'ckks-tenseal-review-v1', 'scheme': 'CKKS', 'language': 'Python', 'library': 'TenSEAL 0.3.16', 'parameters': {'poly_modulus_degree': 8192, 'coeff_mod_bit_sizes': [60,40,40,60], 'scale': 2**40}},
    'tfhe': {'id': 'tfhe-rs-review-v1', 'scheme': 'TFHE', 'language': 'Rust', 'library': 'TFHE-rs 1.4.3', 'parameters': 'ConfigBuilder::default(); CPU; integer API'},
    'bfv': {'id': 'bfv-openfhe-review-v1', 'scheme': 'BFV (lattice-based)', 'language': 'C++20', 'library': 'OpenFHE 1.4.2', 'parameters': {'plaintext_modulus': 65537, 'multiplicative_depth': 1, 'security': 'HEStd_128_classic'}},
}
for p in PROFILES.values():
    p.update(version='1.0.0', platform='Ubuntu 22.04 x86_64', checks=CHECKS,
             attacker='Untrusted evaluator, modified computation results, or adversarial application inputs',
             exclusions=['Primitive cryptanalysis', 'General proof of evaluator correctness', 'Side-channel certification'])

# id, pair/family, split, requirement, issue?, exact quote, authored rationale
CASES = [
    ('ckks_export_private','ckks-key-export','train','H03',True,'save_secret_key=True','The serialized context sent to the evaluator contains the secret decryption key.'),
    ('ckks_export_public','ckks-key-export','train','H03',False,'','The export explicitly excludes the secret key. This assesses only the shown export boundary.'),
    ('ckks_accept_any','ckks-result','test','H02',True,'return True','Any decryptable result is accepted without comparison to the independently known expected result.'),
    ('ckks_validate_result','ckks-result','test','H02',False,'','The toy client checks length, finite values and an explicit CKKS tolerance against its known answer.'),
    ('ckks_unbounded','ckks-input','train','H05',True,'return ts.ckks_vector(context, values)','The stated limit of four finite bounded inputs is not enforced before encryption.'),
    ('ckks_bounded','ckks-input','train','H05',False,'','The input count, finite values and magnitude limits are checked before encryption.'),
    ('tfhe_export_private','tfhe-key-export','train','H03',True,'decryption_key: Some(client)','The client decryption key is included in the bundle passed to the untrusted evaluator.'),
    ('tfhe_export_public','tfhe-key-export','train','H03',False,'','The exported bundle contains the public evaluation/server key and no decryption key.'),
    ('tfhe_wrapping_sum','tfhe-numeric','train','H01',True,'let answer: u8 =','The encrypted eight-bit sum wraps before widening; it cannot represent the specified ordinary sum up to 510.'),
    ('tfhe_widened_sum','tfhe-numeric','train','H01',False,'','Both operands are encrypted as sixteen-bit integers, sufficient for the sum of two eight-bit inputs.'),
    ('tfhe_accept_any','tfhe-result','test','H02',True,'true','The wrapper unconditionally accepts decrypted data and ignores the independently known expected answer.'),
    ('tfhe_validate_result','tfhe-result','test','H02',False,'','The decrypted value is compared with the independently computed expected value for this toy job.'),
    ('bfv_export_private','bfv-key-export','train','H03',True,'return {keys.publicKey, keys.secretKey};','The bundle crossing to the untrusted evaluator includes the private decryption key.'),
    ('bfv_export_public','bfv-key-export','train','H03',False,'','The exported bundle contains the public key and a null private key.'),
    ('bfv_unbounded_sum','bfv-numeric','validation','H01',True,'return cc->EvalAdd(a, b);','No bound prevents the integer sum from leaving the stated signed plaintext interval and wrapping modulo 65537.'),
    ('bfv_bounded_sum','bfv-numeric','validation','H01',False,'','The operands and their sum are range-checked before encryption, using widened arithmetic for the check.'),
    ('bfv_accept_any','bfv-result','test','H02',True,'return true;','The function accepts the result unconditionally without checking the expected value or decryption validity.'),
    ('bfv_validate_result','bfv-result','test','H02',False,'','The toy client checks decryption validity and compares the scalar value against its known expected result.'),
]

def build():
    dest = HERE / 'data'; dest.mkdir(exist_ok=True)
    splits = {s: [] for s in ('train','validation','test')}
    manifest = []
    for case, family, split, rid, issue, quote, rationale in CASES:
        scheme = case.split('_')[0]; suffix = {'ckks':'.py','tfhe':'.rs','bfv':'.hpp'}[scheme]
        path = HERE / 'cases' / (case + suffix); source = path.read_text()
        profile = PROFILES[scheme]
        findings = []
        if issue:
            line = next(i + 1 for i, text in enumerate(source.split('\n')) if quote in text)
            findings.append(dict(check_id=rid,line_start=line,line_end=line,quote=quote,rationale=rationale))
        answer = {'scope':'in_scope','checks':[{'check_id': c['id'],
            'assessment': ('potential_issue' if issue else 'no_issue_identified') if c['id']==rid else 'insufficient_context',
            'reason': rationale if c['id']==rid else 'This excerpt does not supply the complete implementation and lifecycle needed to assess this requirement.'} for c in CHECKS], 'findings':findings}
        row = {'id':case,'family':family,'profile_id':profile['id'],'split':split,'source':source,
               'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'expected':answer,
               'label_origin':'authored_targeted_source_review; see separate native observations',
               'messages':messages(source, profile, ROOT / 'prompts/verify_multi.txt')+[{'role':'assistant','content':json.dumps(answer)}]}
        splits[split].append(row)
        manifest.append({'id':case,'family':family,'split':split,'scheme':scheme,'profile_id':profile['id'],
                         'source_path':str(path.relative_to(ROOT)),'source_sha256':row['source_sha256'],
                         'requirement':rid,'expected_property_satisfied':not issue})
    # Keep the initial AES dataset intact; construct a separate combined dataset.
    for split in splits:
        for line in (ROOT / f'training/data/{split}.jsonl').read_text().splitlines():
            row = json.loads(line); row['profile_id']='aes128-gcm-tampering-v1'
            splits[split].append(row)
        (dest / f'{split}.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in splits[split]))
    all_families = [set(row['family'] for row in splits[s]) for s in splits]
    assert all(not (a & b) for i,a in enumerate(all_families) for b in all_families[i+1:])
    info = {'version':'multi-profile-pilot-v1','counts':{s:len(r) for s,r in splits.items()},
        'sha256':{s:hashlib.sha256((dest/f'{s}.jsonl').read_bytes()).hexdigest() for s in splits},
        'fhe_cases':manifest,'profiles':PROFILES,
        'limitations':['Small authored pilot; no independent-author or broad generalization claim.',
          'Fixed and defective counterparts stay together in the same split.',
          'Runtime probes establish only the named property for their concrete inputs.',
          'No target label is copied from Llama output. Original Python crypto-llm examples excluded.',
          'The FHE primitives are used for shallow computations here; bootstrapping/depth exhaustion is not tested.']}
    (dest/'manifest.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps({'counts':info['counts'],'fhe_cases':len(manifest)},indent=2))

if __name__ == '__main__': build()
