import importlib.util
import json
from pathlib import Path
import tenseal as ts

def load(name):
    path=Path(__file__).parent/'cases'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

ctx=ts.context(ts.SCHEME_TYPE.CKKS,poly_modulus_degree=8192,
               coeff_mod_bit_sizes=[60,40,40,60],n_threads=2)
ctx.global_scale=2**40
references=([1.5,2.5],[0.0,-3.0],[50.0,25.0])
for variant in ('any','all'):
    name='ckks_batch_'+variant; candidate=load(name); observations=[]
    for expected in references:
        cipher=ts.ckks_vector(ctx,expected)
        scenarios={'valid':cipher,'one_modified':cipher+[0.0,1.0],
                   'both_modified':cipher+[1.0,1.0], 'short':ts.ckks_vector(ctx,[expected[0]])}
        for scenario,result in scenarios.items():
            observations.append({'scenario':scenario,'reference':expected,
                'accepted':candidate.verify_batch(result,list(expected)), 'expected_acceptance':scenario=='valid'})
    print(json.dumps({'case':name,'observations':observations}),flush=True)
load('ckks_batch_delegate')
print(json.dumps({'case':'ckks_batch_delegate','status':'not_run_missing_validation_callback'}))
