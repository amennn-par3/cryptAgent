import importlib.util
import json
from pathlib import Path
import tenseal as ts

def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent/'cases'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                     coeff_mod_bit_sizes=[60,40,40,60], n_threads=2)
context.global_scale = 2**40
for variant in ('leaky', 'redacted'):
    name = 'ckks_telemetry_'+variant
    candidate = load(name)
    for value in (7.5, -2.25, 100.0):
        telemetry = []
        result = candidate.client_result(ts.ckks_vector(context, [value]), telemetry)
        print(json.dumps(dict(case=name, input=value, value=result[0], telemetry=telemetry)), flush=True)
for variant in ('unchecked', 'bounded'):
    name = 'ckks_work_'+variant
    candidate = load(name)
    for rounds in (0, 1, 3, 4, -1):
        cipher = ts.ckks_vector(context, [10.0])
        try:
            answer = candidate.evaluate(cipher, rounds).decrypt()[0]
            result = dict(accepted=True, value=answer)
        except ValueError as exc:
            result = dict(accepted=False, error=str(exc))
        print(json.dumps(dict(case=name, rounds=rounds, **result)), flush=True)
