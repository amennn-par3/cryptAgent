"""Small deterministic checks of reviewed expressions; no repository code is imported."""
import argparse
import hashlib
import hmac
import json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True)
    out=ap.parse_args().out
    if out.exists(): raise SystemExit('Use a fresh evidence path.')
    key=b'public synthetic test key; not a production secret'
    algorithm=b'HMAC_SHA2'
    def mac(ad,msg): return hmac.new(key,algorithm+ad+msg.encode('utf-8'),hashlib.sha256).hexdigest()
    first=mac(b'a','bc'); second=mac(b'ab','c')
    assert first==second
    def framed(ad,msg):
        msg=msg.encode('utf-8')
        payload=algorithm+len(ad).to_bytes(8,'big')+ad+len(msg).to_bytes(8,'big')+msg
        return hmac.new(key,payload,hashlib.sha256).hexdigest()
    assert framed(b'a','bc')!=framed(b'ab','c')
    # RFC 5869 Appendix A.1; compare the first expand block for a 32-byte output.
    ikm=bytes.fromhex('0b'*22)
    salt=bytes.fromhex('000102030405060708090a0b0c')
    info=bytes.fromhex('f0f1f2f3f4f5f6f7f8f9')
    prk=hmac.new(salt,ikm,hashlib.sha256).digest()
    result=hmac.new(prk,info+b'\x01',hashlib.sha256).digest()
    assert prk.hex()=='077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5'
    assert result.hex()=='3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf'
    record=dict(repository_code_imported=False,repository_code_executed=False,
        tests=[dict(name='unframed_HMAC_field_collision',passed=True,first=dict(associated_data='a',message='bc'),
                    second=dict(associated_data='ab',message='c'),same_tag=True,
                    limitation='Confirms the generic field-binding defect, not an exploit against the JSON AEAD subclass.'),
               dict(name='length_prefix_remediation_distinguishes_fields',passed=True),
               dict(name='HKDF_SHA256_RFC5869_A1_first_block',passed=True,output_bytes=32,
                    source='https://www.rfc-editor.org/rfc/rfc5869#appendix-A.1')])
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__': main()
