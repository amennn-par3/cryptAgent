import importlib.util
import json
from pathlib import Path

for name in ('ckks_missing_scale', 'ckks_configured_scale'):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / 'cases' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for value in (0.0, -3.25, 12.5):
        try:
            result = {'value': module.roundtrip(value)}
        except Exception as exc:
            result = {'error_type': type(exc).__name__, 'error': str(exc)}
        print(json.dumps({'case': name, 'input': value, **result}), flush=True)
