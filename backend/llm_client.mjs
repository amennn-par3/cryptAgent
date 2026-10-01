import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateReview} from './review_contract.mjs';

// Fixed loopback destination: request data cannot select a remote provider.
const endpoint = 'http://127.0.0.1:8081';
const prompt = await readFile(new URL('../prompts/verify.txt', import.meta.url), 'utf8');
const promptHash = createHash('sha256').update(prompt).digest('hex');
const base = {provider: 'local', model: 'meta-llama/Llama-3.1-8B-Instruct', adapter: null, experimental: true, promptHash};

async function boundedJson(response) {
  if (!response.ok) {
    await response.body?.cancel();
    throw new Error('Local service returned HTTP ' + response.status);
  }
  const reader = response.body.getReader();
  let size = 0;
  const chunks = [];
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.length;
      if (size > 262144) { await reader.cancel(); throw new Error('Response exceeds limit'); }
      chunks.push(Buffer.from(value));
    }
  } finally { reader.releaseLock(); }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

export async function modelStatus() {
  try {
    const status = await boundedJson(await fetch(endpoint + '/health', {redirect: 'error', signal: AbortSignal.timeout(3000)}));
    if (status.service !== 'cryptagent-aes' || status.model !== base.model || status.promptHash !== promptHash || status.adapter !== null ||
        status.revision !== '0e9e39f249a16976918f6564b8830bc894c89659' ||
        status.profileId !== 'aes128-gcm-tampering-v1' || !['ready', 'busy', 'loading', 'error'].includes(status.state)) {
      throw new Error('Unexpected local service');
    }
    return {...base, revision: status.revision, state: status.state,
      message: {busy: 'Local Llama is reviewing a submission.',
        loading: 'Local Llama is loading. This page refreshes its status automatically.',
        error: 'Local model could not load. Check the startup terminal and restart after resolving the error.',
        ready: 'Local Llama is ready. Base model; AES fine-tuning is pending.'}[status.state]};
  } catch {
    return {...base, state: 'unavailable', message: 'Local model is starting or unavailable. Check the startup terminal, then refresh.'};
  }
}

export async function reviewWithModel(source, profile) {
  const status = await modelStatus();
  const empty = {findings: [], discarded: 0, sourceSent: false, sourceSentExternally: false};
  if (status.state !== 'ready') return {...status, ...empty};
  try {
    const result = await boundedJson(await fetch(endpoint + '/review', {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(110000),
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify({source, profileId: profile.id})
    }));
    if (result.state !== 'completed') {
      return {...status, ...empty, sourceSent: true, state: 'incomplete',
        message: typeof result.message === 'string' ? result.message.slice(0,400) : 'Local review did not complete.'};
    }
    if (typeof result.output !== 'string') throw new Error('Missing model output');
    const review = validateReview(JSON.parse(result.output), source);
    return {...status, ...review, sourceSent: true, sourceSentExternally: false,
      seconds: result.seconds, message: 'Local AES source review completed. Findings are advisory.'};
  } catch (error) {
    return {...status, ...empty, sourceSent: true, state: 'error', message: error.name === 'TimeoutError'
      ? 'Local review timed out. No model conclusion was accepted.'
      : 'Local model output was unavailable or failed validation. No model conclusion was accepted.'};
  }
}
