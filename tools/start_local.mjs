import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import {homedir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const windows = process.platform === 'win32';
const venvPython = windows ? ['Scripts', 'python.exe'] : ['bin', 'python'];
const candidates = [path.join(root, '.venv', ...venvPython), path.join(homedir(), 'crypto-llm', '.venv', ...venvPython)];
const python = process.env.CRYPTAGENT_PYTHON || candidates.find(existsSync) || (windows ? 'python' : 'python3');
const children = [];
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  process.exitCode = code;
  for (const child of children) if (child.exitCode === null) child.kill('SIGTERM');
  const timer = setTimeout(() => {
    for (const child of children) if (child.exitCode === null) child.kill('SIGKILL');
  }, 5000);
  timer.unref();
}
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => stop());
function start(command, args) {
  const child = spawn(command, args, {cwd: root, stdio: 'inherit', env: {...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONUNBUFFERED: '1'}});
  children.push(child);
  child.on('error', error => { console.error('Startup failed:', error.message); stop(1); });
  child.on('exit', code => { if (!stopping) stop(code || 1); });
}
console.log('AES-only local review. Python:', python);
console.log('Open http://127.0.0.1:8000. Model loading can take a minute. Ctrl+C stops both services.');
start(python, ['backend/local_model.py']);
start(process.execPath, ['backend/app.mjs']);
