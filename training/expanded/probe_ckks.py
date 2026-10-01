"""Execute only the six authored fixtures. No network or external keys."""
import importlib.util
import json
from pathlib import Path
import tenseal as ts

def load(name):
    path = Path(__file__).parent / 'cases' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                     coeff_mod_bit_sizes=[60, 40, 40, 60], n_threads=2)
context.global_scale = 2**40
encrypted = ts.ckks_vector(context, [1.25, 2.5])
roundtrip = encrypted.decrypt()
assert all(abs(a-b) < 1e-5 for a,b in zip(roundtrip, [1.25, 2.5]))
for suffix in ('private', 'public'):
    name = 'ckks_export_' + suffix
    blob = load(name).evaluator_context(context)
    received = ts.context_from(blob, n_threads=2)
    has_secret = received.has_secret_key()
    print(json.dumps({'case': name, 'property_satisfied': not has_secret, 'witness': {'evaluator_has_secret_key': has_secret}}), flush=True)
for suffix in ('any', 'result'):
    name = 'ckks_accept_any' if suffix == 'any' else 'ckks_validate_result'
    candidate = load(name)
    modified = encrypted + [10.0, 10.0]
    accepts_valid = candidate.accept_result(encrypted, [1.25, 2.5])
    accepts_wrong = candidate.accept_result(modified, [1.25, 2.5])
    print(json.dumps({'case': name, 'property_satisfied': accepts_valid and not accepts_wrong,
                      'witness': {'accepts_valid': accepts_valid, 'accepts_modified_result': accepts_wrong}}), flush=True)
for suffix in ('unbounded', 'bounded'):
    name = 'ckks_' + suffix
    candidate = load(name)
    valid = candidate.encrypt_job(context, [1.0, 2.0]).decrypt()
    accepts_valid = len(valid) == 2 and abs(valid[0] - 1) < 1e-5 and abs(valid[1] - 2) < 1e-5
    rejects_oversize = False
    try: candidate.encrypt_job(context, [1.0] * 5)
    except ValueError: rejects_oversize = True
    print(json.dumps({'case': name, 'property_satisfied': accepts_valid and rejects_oversize,
                      'witness': {'accepts_valid': accepts_valid, 'rejects_five_values': rejects_oversize}}), flush=True)
