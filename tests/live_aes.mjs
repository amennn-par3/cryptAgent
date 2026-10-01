// Opt-in smoke checks against the running local base model. Not an accuracy benchmark.
import assert from 'node:assert/strict';
const endpoint = 'http://127.0.0.1:8000';
const cases = [
  ['unrelated_python', 'print("hello")'],
  ['declarations_only', '// Windows CNG AES-128-GCM integration\nBCRYPT_KEY_HANDLE key;\nBCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;'],
  ['ignored_status_excerpt', '// AES-128-GCM Windows CNG decryption excerpt.\nULONG written = 0;\n(void)BCryptDecrypt(key, ciphertext, size, &auth, nullptr, 0, output, capacity, &written, 0);\nreturn true;']
];
for (const [id, code] of cases) {
  const status = await (await fetch(endpoint + '/api/status')).json();
  assert.equal(status.model.state, 'ready', 'Start the local model and wait until ready.');
  const response = await fetch(endpoint + '/api/verify', {method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-Session-Token': status.sessionToken},
    body: JSON.stringify({code, profileId: status.profile.id, mode: 'verify'}), signal: AbortSignal.timeout(125000)});
  const report = await response.json();
  assert.equal(response.status, 200);
  assert.equal(report.checks.length, 5);
  assert.equal(report.candidateExecuted, false);
  assert.equal(report.model.sourceSentExternally, false);
  console.log(JSON.stringify({id, verdict: report.verdict, state: report.model.state,
    seconds: report.model.seconds, findings: report.findings.length,
    checks: report.checks.map(c => [c.id, c.assessment]), message: report.model.message}));
  assert.ok(['completed', 'partial'].includes(report.model.state), 'Live model must produce accepted structured output.');
}
