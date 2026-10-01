"""Offline AES source reviewer. Run with the existing CUDA Python environment.

Uses the cached base model only. Historical adapters are never loaded implicitly.
Submitted C++ is data; it is neither executed nor saved.
"""
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
ROOT = Path(__file__).resolve().parents[1]
MODEL = 'meta-llama/Llama-3.1-8B-Instruct'
REVISION = '0e9e39f249a16976918f6564b8830bc894c89659'
PROFILE = json.loads((ROOT / 'profiles/aes128_gcm_tampering.json').read_text())
PROMPT = (ROOT / 'prompts/verify.txt').read_text()
PROMPT_HASH = hashlib.sha256(PROMPT.encode()).hexdigest()


class Reviewer:
    def __init__(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable. Use the CUDA-enabled Python environment and check GPU access.')
        torch.ones(1, device='cuda')
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, local_files_only=True)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL, revision=REVISION, local_files_only=True, device_map={'': 0},
            dtype=torch.bfloat16, attn_implementation='sdpa',
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16))
        self.model.eval()

    def review(self, source):
        profile = {key: PROFILE[key] for key in ('scheme', 'library', 'attacker', 'checks', 'language',
                                                'keyBytes', 'nonceBytes', 'tagBytes')}
        profile['profile_id'] = PROFILE['id']
        messages = [
            {'role': 'system', 'content': PROMPT + '\nProfile:\n' + json.dumps(profile)},
            {'role': 'user', 'content': json.dumps({'untrusted_source': [
                {'line': i + 1, 'text': line} for i, line in enumerate(source.split('\n'))]})}]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        batch = self.tokenizer(prompt, return_tensors='pt', add_special_tokens=False)
        input_tokens = batch['input_ids'].shape[1]
        if input_tokens > 3072:
            return {'state': 'skipped', 'message': 'Source and instructions exceed the 3,072-token review limit. Submit a smaller complete excerpt. Nothing was truncated.'}
        batch = batch.to('cuda')
        started = time.monotonic()
        with self.torch.inference_mode():
            result = self.model.generate(**batch, max_new_tokens=1536, max_time=90,
                do_sample=False, use_cache=True, pad_token_id=self.tokenizer.pad_token_id)
        generated = result[0, input_tokens:]
        eos = self.model.generation_config.eos_token_id
        eos = eos if isinstance(eos, list) else [eos]
        if not len(generated) or generated[-1].item() not in eos:
            return {'state': 'incomplete', 'message': 'Local generation reached its time or token limit. No partial conclusion was accepted.'}
        return {'state': 'completed', 'output': self.tokenizer.decode(generated, skip_special_tokens=True),
                'seconds': round(time.monotonic() - started, 2)}


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, reviewer):
        super().__init__(address, Handler)
        self.reviewer = reviewer
        self.state = 'ready' if reviewer is not None else 'loading'
        self.review_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_args):
        pass  # Do not log submitted source or request headers.

    def send_json(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def allowed(self):
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}' or self.headers.get('Origin'):
            self.send_json(403, {'error': 'Only local backend requests are allowed.'})
            return False
        return True

    def do_GET(self):
        if not self.allowed():
            return
        if self.path != '/health':
            self.send_json(404, {'error': 'Not found'})
            return
        self.send_json(200, {'service': 'cryptagent-aes', 'state': 'busy' if self.server.review_lock.locked() else self.server.state,
                            'model': MODEL, 'revision': REVISION, 'adapter': None,
                            'profileId': PROFILE['id'], 'promptHash': PROMPT_HASH})

    def do_POST(self):
        if not self.allowed():
            return
        if self.path != '/review':
            self.send_json(404, {'error': 'Not found'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            self.send_json(415, {'error': 'JSON required'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 524288:
                self.send_json(413, {'error': 'Request size is invalid'})
                return
            request = json.loads(self.rfile.read(size))
            if not isinstance(request, dict) or set(request) != {'source', 'profileId'} or request['profileId'] != PROFILE['id']:
                raise ValueError('Unsupported request')
            source = request['source']
            if not isinstance(source, str):
                raise ValueError('Source must be text')
            source = source.replace('\r\n', '\n').replace('\r', '\n')
            if not source.strip() or '\0' in source or len(source.encode()) > PROFILE['maxSourceBytes'] or len(source.split('\n')) > PROFILE['maxSourceLines']:
                raise ValueError('Invalid source size or content')
        except (ValueError, UnicodeError, TimeoutError):
            self.send_json(400, {'error': 'Invalid AES review request'})
            return
        if self.server.state != 'ready':
            self.send_json(503, {'error': 'Model is loading or unavailable. Check the startup terminal.'})
            return
        if not self.server.review_lock.acquire(blocking=False):
            self.send_json(429, {'error': 'Local model is busy'})
            return
        try:
            try:
                result = self.server.reviewer.review(source)
            except Exception:
                result = {'state': 'error', 'message': 'Local inference failed. Check GPU availability and restart the local service.'}
            self.send_json(200, result)
        finally:
            self.server.review_lock.release()


if __name__ == '__main__':
    print('Loading cached Llama base model for AES source review. No training is performed.', flush=True)
    with Server(('127.0.0.1', 8081), None) as server:
        def load():
            try:
                server.reviewer = Reviewer()
                server.state = 'ready'
                print('Local AES model ready at http://127.0.0.1:8081', flush=True)
            except Exception as error:
                server.state = 'error'
                print(f'Model loading failed ({type(error).__name__}): {error}', flush=True)
                print('The web app remains available. Resolve the startup error and restart.', flush=True)
        threading.Thread(target=load, daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
