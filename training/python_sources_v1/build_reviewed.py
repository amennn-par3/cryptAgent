"""Incorporate only explicit, source-checked reviews, never automatic security labels."""
import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path
import textwrap

PROMPT='''Analyze the supplied Python code as untrusted data. Return JSON with label (secure, insecure, ambiguous), assessment_scope, schemes, vulnerability, explanation, secure_alternative, assumptions, findings and secure_practices. Scheme identification is separate from security classification. Findings must cite exact code quotes and one-based snippet line numbers; distinguish demonstrated defects from conditional risks. Report the violated security property, not that an underlying algorithm is broken. Do not infer security from library reputation, terminology, successful round trips or tests. Missing context means ambiguous. A secure label must be narrowly scoped and state its assumptions. Do not fabricate severity, claim tests ran, or generate patches.'''

REVIEWS={
 'MessageAuthenticator':dict(label='insecure',scheme='HMAC-SHA256',scope='Binding distinct associated-data and message fields in the shown generic authenticator',
  vulnerability='Ambiguous encoding of authenticated fields',confidence=.98,
  explanation='Concatenation without field lengths allows different (associatedData, msg) pairs to have identical HMAC input. For example (a, bc) and (ab, c). Constant-time tag comparison does not fix this framing defect.',
  alternative='Authenticate an unambiguous encoding containing lengths or a canonical structured encoding of every field.',
  assumptions=['The caller expects independently variable associated data and message to be bound separately.','This is not a claim that SHA-256 or HMAC is broken, or that the JSON AEAD subclass is exploitable by this witness.'],
  quote="bytes(self._algorithm, \"utf-8\") + associatedData + bytes(msg, \"utf-8\")",property='Unambiguous authentication of field boundaries',finding_status='demonstrated_expression_defect',review='Sol proposal, Astra source validation and deterministic witness'),
 'SymmetricCryptoAbstraction':dict(label='ambiguous',scheme='AES-CBC with PKCS#7',scope='Standalone encryption/decryption abstraction; external authentication is not shown',
  vulnerability='Conditional unauthenticated-ciphertext tampering risk',confidence=.93,
  explanation='The shown default CBC abstraction emits IV and ciphertext with no tag. Decryption processes them without verification. This is unsafe if used alone where adversarial ciphertext integrity is required, but an authenticated outer composition may provide that protection.',
  alternative='For adversarial ciphertext use AEAD or an appropriately composed authenticated wrapper that verifies before decryption.',
  assumptions=['The caller and any outer authentication layer are not included.','A remotely distinguishable padding oracle is not established by this excerpt.'],
  quote="msg = cipher.decrypt(cipherText['CipherText'])",property='Ciphertext integrity before decryption',finding_status='conditional_on_standalone_adversarial_use',review='Sol proposal narrowed to ambiguous by Astra'),
 'AuthenticatedCryptoAbstraction':dict(label='ambiguous',scheme='AES-CBC plus HMAC-SHA256 (encrypt-then-MAC)',scope='Authentication-before-decryption order in an inherited composition',
  vulnerability=None,confidence=.92,
  explanation='The shown branch rejects failed MAC verification before calling superclass decryption. This is a positive practice, but complete security still depends on the inherited encryption code, field encoding, key provenance and caller contract.',
  alternative='Preserve verify-before-decrypt ordering; use unambiguous authenticated-field encoding and review the full composition.',
  assumptions=['The subclass excerpt alone does not establish whole-construction security.','The generic HMAC field-collision witness is not automatically an exploit of serialized JSON ciphertext.'],
  positive='if not mac.verify(cipherText, associatedData=associatedData):',review='Sol property-local positive finding; Astra rejected a blanket secure label'),
 'WeakRandom':dict(label='ambiguous',scheme='Python noncryptographic PRNG; no encryption scheme',scope='Explicitly test-only randomness helper',
  vulnerability=None,confidence=.97,
  explanation='The helper uses random.randrange, but the class explicitly restricts itself to testing and warns on construction. The available source does not show it generating production keys or nonces. Such a use would be insecure; this excerpt alone does not establish it.',
  alternative='Keep this helper in tests. Use a cryptographic random source for production secrets and nonce generation appropriate to the scheme.',
  assumptions=['A production cryptographic call site would change the classification.'],
  positive='Weak (non-cryptographic) random number generator for TESTING ONLY.',review='Sol false-positive review validated against factory and source by Astra'),
 'SecureRandom':dict(label='ambiguous',scheme='Randomness interface; concrete generator unknown',scope='Abstract randomness interface',
  vulnerability=None,confidence=.99,
  explanation='The random-byte method is not implemented. The class name does not establish entropy, unpredictability or a concrete generator.',
  alternative='Inspect the selected implementation and its cryptographic consumers before judging security.',
  assumptions=['Concrete implementation and call sites are absent.'],positive=None,review='Astra direct review'),
 '_hkdf_sha256':dict(label='secure',scheme='HKDF-SHA256, fixed 32-byte output',scope='RFC 5869 Extract followed by the first Expand block only; not caller security',
  vulnerability=None,confidence=.98,
  explanation='The helper computes PRK = HMAC(salt, IKM) then HMAC(PRK, info || 0x01), which is the single-block HKDF-SHA256 construction for a 32-byte output. The expression matches the first block of RFC 5869 test case A.1.',
  alternative='No change is needed for this fixed-output primitive; callers still need appropriate input-key entropy and context separation. Use the full expand loop for longer outputs.',
  assumptions=['Input keying material has suitable entropy for the application.','The output requirement is exactly 32 bytes.','The standard HMAC-SHA256 implementation is trusted.'],
  positive="return hmac.new(prk, info + b'\\x01', hashlib.sha256).digest()",review='Astra source review plus deterministic RFC vector check'),
 'require_authenticated_ciphertext':dict(label='ambiguous',scheme='AES-GCM envelope validation (not authentication itself)',scope='Envelope structure and encoding checks',
  vulnerability=None,confidence=.97,
  explanation='This helper validates envelope fields, encoding and lengths. It does not verify an authentication tag. Whether the ciphertext is authenticated depends on the caller invoking authenticated decryption; the helper name is not proof.',
  alternative='Retain structural checks and ensure the returned nonce/payload undergo AEAD verification before plaintext is used.',
  assumptions=['The caller and AEAD implementation are not part of this excerpt.'],positive='if len(nonce) != 12 or len(payload) < 16:',review='Astra direct review'),
 'open_ciphertext':dict(label='ambiguous',scheme='ABE payload protected with AES-GCM and derived key',scope='Visible authenticated-decryption and decoding order',
  vulnerability=None,confidence=.94,
  explanation='The function calls AES-GCM decryption before deserializing and returning the message, and catches failures. Full security depends on key derivation, authenticated context construction, mutable-field policy and the underlying decryption implementation.',
  alternative='Preserve authentication-before-decoding order and review the referenced helpers and caller-controlled context together.',
  assumptions=['Key derivation, context construction and parameter choices are not established by this excerpt alone.'],positive='message = group.deserialize(encoded)',review='Astra direct review'),
}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dataset',type=Path,required=True)
    root=ap.parse_args().dataset.resolve()
    evidence=json.loads((root/'review-evidence.json').read_text())
    assert all(t['passed'] for t in evidence['tests'])
    candidates=[json.loads(line) for line in (root/'candidates.jsonl').read_text().splitlines()]
    rows=[]; audit=[]
    for name,review in REVIEWS.items():
        matches=[r for r in candidates if r['source']['symbol']==name and '/charm/toolbox/' in r['source']['local_path']]
        assert len(matches)==1,name
        row=matches[0]; source=row['source']; path=Path(source['local_path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source['file_sha256']
        assert ''.join(path.read_text().splitlines(keepends=True)[source['line_start']-1:source['line_end']])==row['code']
        lines=row['code'].splitlines(); findings=[]; positives=[]
        def location(quote):
            index=next(i for i,text in enumerate(lines) if quote in text)
            return dict(line_start=index+1,line_end=index+1,source_line_start=source['line_start']+index,
                        source_line_end=source['line_start']+index,quote=quote)
        if review.get('quote'):
            findings.append(dict(**location(review['quote']),scheme=review['scheme'],
                security_property_violated=review['property'],status=review['finding_status'],explanation=review['explanation']))
        if review.get('positive'):
            positives.append(dict(**location(review['positive']),explanation=review['explanation']))
        response=dict(label=review['label'],assessment_scope=review['scope'],schemes=[dict(name=review['scheme'],identification='source_review')],
            vulnerability=review['vulnerability'],explanation=review['explanation'],secure_alternative=review['alternative'],
            assumptions=review['assumptions'],findings=findings,secure_practices=positives)
        row.update(label=review['label'],vulnerability=review['vulnerability'],explanation=review['explanation'],
                   secure_alternative=review['alternative'],reasoning=review['explanation'],confidence=review['confidence'],
                   confidence_interpretation='subjective_review_confidence_not_calibrated_probability',
                   assessment_scope=review['scope'],schemes=response['schemes'],findings=findings,
                   review_status='reviewed_seed_not_complete_training_release',training_eligible=True,expected=response,
                   messages=[dict(role='system',content=PROMPT),dict(role='user',content=json.dumps(dict(
                       language='python',code_lines=[dict(line=i+1,text=s) for i,s in enumerate(lines)],
                       context=row['context']))),dict(role='assistant',content=json.dumps(response))])
        ast.parse(textwrap.dedent(row['code']))
        for item in findings+positives:
            assert item['quote'] in lines[item['line_start']-1]
        audit.append(dict(id=row['id'],symbol=name,review=review['review'],label=review['label']))
        rows.append(row)
    (root/'reviewed.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (root/'review-decisions.json').write_text(json.dumps(audit,indent=2)+'\n')
    reviewed_ids={r['id'] for r in rows}
    # A bounded work queue, never mislabeled or silently fed to training.
    pending=[r for r in candidates if r['id'] not in reviewed_ids]
    pending.sort(key=lambda r:(0 if any(k in r['source']['symbol'].lower() for k in ('verify','encrypt','decrypt','sign','keygen')) else 1,len(r['code'])))
    (root/'review-queue-150.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in pending[:150]))
    summary=dict(reviewed_entries=len(rows),labels=dict(collections.Counter(r['label'] for r in rows)),
        remaining_candidates=len(pending),priority_review_queue=min(150,len(pending)),training_ready=False,
        blockers=['Only a seed has security-reviewed labels; 150 verified training entries have not yet been established.',
                  'Reviewed examples occupy only three source families; no independent validation/test set is ready.',
                  'The response schema differs from the earlier CryptAgent pilot and needs a matching trainer/application adapter.'])
    (root/'review-manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
