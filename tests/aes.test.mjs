import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateReview, checkIds} from '../backend/review_contract.mjs';
import {deriveAssessment, profile, verify} from '../backend/verifier.mjs';
import {reviewWithModel} from '../backend/llm_client.mjs';
import {createApp} from '../backend/app.mjs';

const source = 'auto status = BCryptDecrypt(key, ciphertext, size, &auth, 0, 0, out, capacity, &used, 0);\nreturn true;';
function answer() {
  return {scope: 'in_scope', checks: checkIds.map(check_id => ({check_id,
    assessment: check_id === 'F03' ? 'potential_issue' : 'insufficient_context',
    reason: check_id === 'F03' ? 'Failure status is not checked before returning success.' : 'Required setup is not supplied.'})),
    findings: [{check_id: 'F03', line_start: 2, line_end: 2, quote: 'return true;', rationale: 'Success is returned regardless of the decryption status.'}]};
}
test('accepts source-located AES findings', () => {
  const result = validateReview(answer(), source);
  assert.equal(result.state, 'completed');
  assert.equal(result.findings[0].source, 'local_model');
  assert.equal(deriveAssessment(result, []).verdict, 'potential_issues');
});
test('rejects mixed-scheme and repeated requirement IDs', () => {
  const mixed = answer(); mixed.checks[0].check_id = 'H01';
  assert.throws(() => validateReview(mixed, source));
  const repeated = answer(); repeated.checks[0].check_id = 'F02';
  assert.throws(() => validateReview(repeated, source));
});
test('invented quotations cannot support a vulnerability', () => {
  const value = answer(); value.findings[0].quote = 'not in the source';
  const result = validateReview(value, source);
  assert.equal(result.discarded, 1);
  assert.equal(result.findings.length, 0);
  assert.equal(result.assessments.find(c => c.checkId === 'F03').assessment, 'insufficient_context');
  assert.equal(deriveAssessment(result, []).verdict, 'insufficient_context');
});
test('rejects contradictory scope and does not turn missing evidence into a pass', () => {
  const outside = answer(); outside.scope = 'outside_scope';
  assert.throws(() => validateReview(outside, source));
  const missing = answer(); missing.findings = [];
  assert.equal(deriveAssessment(validateReview(missing, source), []).verdict, 'insufficient_context');
  assert.equal(deriveAssessment({state: 'error', message: 'failed'}, []).verdict, 'review_unavailable');
});
test('rejects a finding paired with a no-issue assessment', () => {
  const value = answer(); value.checks.find(c => c.check_id === 'F03').assessment = 'no_issue_identified';
  assert.throws(() => validateReview(value, source), /contradicts/);
});

const promptHash = createHash('sha256').update(await readFile(new URL('../prompts/verify.txt', import.meta.url))).digest('hex');
const health = {service: 'cryptagent-aes', model: 'meta-llama/Llama-3.1-8B-Instruct', state: 'ready', adapter: null,
  profileId: profile.id, promptHash, revision: '0e9e39f249a16976918f6564b8830bc894c89659'};

test('model client sends source only to the fixed loopback service', async t => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push(url); assert.equal(new URL(url).hostname, '127.0.0.1');
    assert.equal(options.redirect, 'error'); assert.ok(options.signal);
    if (url.endsWith('/health')) return Response.json(health);
    assert.deepEqual(JSON.parse(options.body), {source, profileId: profile.id});
    return Response.json({state: 'completed', output: JSON.stringify(answer()), seconds: 1});
  });
  const result = await reviewWithModel(source, profile);
  assert.equal(result.state, 'completed'); assert.equal(result.sourceSentExternally, false);
  assert.deepEqual(calls, ['http://127.0.0.1:8081/health', 'http://127.0.0.1:8081/review']);
});
test('offline or invalid local responses produce no accepted model verdict', async t => {
  let offline = true;
  t.mock.method(globalThis, 'fetch', async url => {
    if (offline) throw Error('offline');
    return Response.json(url.endsWith('/health') ? health : {state: 'completed', output: 'not JSON'});
  });
  let result = await reviewWithModel(source, profile);
  assert.equal(result.state, 'unavailable'); assert.equal(result.sourceSent, false);
  offline = false; result = await reviewWithModel(source, profile);
  assert.equal(result.state, 'error'); assert.deepEqual(result.findings, []);
});

test('arbitrary submissions get explicit reports when inference is unavailable', async t => {
  t.mock.method(globalThis, 'fetch', async () => { throw Error('offline'); });
  for (const code of ['print("hello")', 'int main() {}', source]) {
    const report = await verify(code);
    assert.equal(report.verdict, 'review_unavailable');
    assert.equal(report.checks.length, 5);
    assert.ok(report.checks.every(c => c.assessment === 'not_reviewed'));
    assert.equal(report.candidateExecuted, false);
    assert.equal(report.model.sourceSentExternally, false);
  }
});

test('valid outside-scope model responses are not cryptographic passes', async t => {
  const output = {scope: 'outside_scope', checks: checkIds.map(check_id => ({check_id,
    assessment: 'not_applicable', reason: 'Unrelated Python code, not Windows CNG AES-GCM.'})), findings: []};
  t.mock.method(globalThis, 'fetch', async url => Response.json(url.endsWith('/health') ? health :
    {state: 'completed', output: JSON.stringify(output)}));
  assert.equal((await verify('print("hello")')).verdict, 'outside_scope');
});

test('context limits, loading and model failure produce explicit non-verdicts', async t => {
  let state = 'loading';
  t.mock.method(globalThis, 'fetch', async url => Response.json(url.endsWith('/health') ? {...health, state} :
    {state: 'skipped', message: 'Prompt exceeds token limit. Nothing was truncated.'}));
  for (state of ['loading', 'error', 'busy', 'ready']) {
    const report = await verify(source);
    assert.equal(report.verdict, 'review_unavailable');
    assert.ok(report.model.message);
  }
});

test('HTTP app exposes only status and AES verification, with guarded input', async t => {
  t.mock.method(globalThis, 'fetch', async url => Response.json(url.endsWith('/health') ? health :
    {state: 'completed', output: JSON.stringify(answer()), seconds: 1}));
  const server = createApp();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const request = (method, route, value, token, extraHeaders = {}) => new Promise((resolve, reject) => {
    const data = value === undefined ? '' : JSON.stringify(value);
    const req = http.request({hostname: '127.0.0.1', port: server.address().port, path: route, method,
      headers: {Host: '127.0.0.1:8000', 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data),
        ...(token ? {'X-Session-Token': token} : {}), ...extraHeaders}}, res => {
      const chunks = []; res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => resolve({status: res.statusCode, data: JSON.parse(Buffer.concat(chunks))}));
    });
    req.on('error', reject); req.end(data);
  });
  const status = await request('GET', '/api/status');
  assert.equal(status.data.capabilities.llmReview, 'local');
  const token = status.data.sessionToken;
  const input = {code: source, profileId: profile.id, mode: 'verify'};
  assert.equal((await request('POST', '/api/model/connect', {apiKey: 'irrelevant'})).status, 404);
  assert.equal((await request('POST', '/api/generate', {})).status, 404);
  assert.equal((await request('POST', '/api/verify', input)).status, 403);
  assert.equal((await request('POST', '/api/verify', {...input, profileId: 'bfv-openfhe-review-v1'}, token)).status, 400);
  assert.equal((await request('POST', '/api/verify', {...input, mode: 'generate'}, token)).status, 400);
  assert.equal((await request('POST', '/api/verify', {...input, code: '\0'}, token)).status, 400);
  assert.equal((await request('POST', '/api/verify', {...input, code: 'x'.repeat(65537)}, token)).status, 400);
  assert.equal((await request('POST', '/api/verify', input, token, {Origin: 'https://example.com'})).status, 403);
  const result = await request('POST', '/api/verify', input, token);
  assert.equal(result.status, 200); assert.equal(result.data.verdict, 'potential_issues');
  assert.equal(result.data.candidateExecuted, false); assert.equal(result.data.checks.length, 5);
  assert.equal(result.data.model.provider, 'local');
});
