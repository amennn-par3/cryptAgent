import {createHash,randomUUID} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {reviewWithModel} from './llm_client.mjs';
import {nativeEvidence} from './native_checks.mjs';
export const profile=JSON.parse(await readFile(new URL('../profiles/aes128_gcm_tampering.json',import.meta.url),'utf8'));
const rules=[
 {re:/\(void\)\s*BCryptDecrypt\s*\(/,id:'F03',title:'Discarded-status pattern',why:'The source text matches a discarded decryption-status pattern. Confirm that it is executable code and establish how authentication failure is handled.'},
 {re:/^\s*BCryptDecrypt\s*\(/,id:'F03',title:'Standalone decryption call',why:'This line starts a standalone decryption call. Inspect the surrounding control flow to establish whether authentication status is checked.'},
 {re:/\b(?:nonce|iv)\w*\s*(?:\[[^\]]*\])?\s*=\s*\{\s*0?\s*\}/i,id:'F04',title:'Zero initialization near a nonce or IV',why:'A zero initializer appears here. This is not proof of nonce reuse: establish whether a fresh value replaces it before each encryption.'},
 {re:/\b(?:printf|fprintf|cout|cerr|puts)\b.*\b(?:plaintext|secret|key)\b/i,id:'F03',title:'Possible sensitive-output path',why:'Output-related and secret-related identifiers appear on the same line. Confirm actual data flow and whether the output is authorized.'},
 {re:/BCRYPT_CHAIN_MODE_ECB|EVP_aes_\d+_ecb/,id:'F02',title:'ECB mode reference',why:'The source contains an ECB mode identifier. Determine whether the active encryption path matches the selected AES-GCM profile.'}
];
function sourceObservations(source){
 const findings=[];source.split('\n').forEach((line,i)=>{if(line.trim().startsWith('//'))return;for(const rule of rules){if(rule.re.test(line))findings.push({checkId:rule.id,title:rule.title,kind:'observation',source:'source_pattern',lineStart:i+1,lineEnd:i+1,quote:line,explanation:rule.why,evidence:'Pattern present in submitted source; runtime behavior unverified.'});}});return findings.slice(0,20);
}
export function deriveAssessment(model,observations){
 const finished=['completed','partial'].includes(model.state);
 if(!finished)return {verdict:'review_unavailable',headline:'AI review could not complete',summary:model.message+' Source observations, if present, remain available.'};
 if(model.scope==='outside_scope')return {verdict:'outside_scope',headline:'Outside the selected profile',summary:'The AI review classified this submission outside Windows CNG AES-128-GCM. No cryptographic pass or fail was assigned.'};
 if(model.findings.length||observations.length)return {verdict:'potential_issues',headline:'Potential issues need attention',summary:'Source observations or AI findings require review. These are not confirmed vulnerabilities; inspect the cited lines and per-check explanations.'};
 if(model.scope!=='in_scope'||model.discarded||model.assessments.some(c=>c.assessment!=='no_issue_identified'))return {verdict:'insufficient_context',headline:'More code or context is needed',summary:'The review could not assess every profile requirement. The check explanations identify missing evidence.'};
 return {verdict:'no_issues_identified',headline:'No issues identified in this review',summary:'The AI reviewer found no concerns across the five source-review checks. This is not an execution result or a security proof.'};
}
export async function verify(source){
 const sourceHash=createHash('sha256').update(source).digest('hex');
 const observations=sourceObservations(source);
 const model=await reviewWithModel(source,profile);
 const outcome=deriveAssessment(model,observations);
 const checks=profile.checks.map(check=>{
  const review=model.assessments?.find(c=>c.checkId===check.id);
  return {...check,assessment:review?.assessment||'not_reviewed',reason:review?.reason||'The AI review did not produce a validated assessment.',evidenceType:'llm_source_review'};
 });
 return {reportVersion:'2.0',id:randomUUID(),createdAt:new Date().toISOString(),profileId:profile.id,profileVersion:profile.version,
  profileHash:createHash('sha256').update(JSON.stringify(profile)).digest('hex'),sourceHash,sourceLines:source.split('\n').length,
  scope:model.scope||'unassessed',...outcome,assessmentType:'source_review',
  findings:[...observations,...model.findings],checks,verificationChecks:nativeEvidence(profile),
  execution:{status:'not_run',reason:'Tool installation deferred.'},formalVerification:{status:'not_run',reason:'Formal verifier installation deferred.'},
  model:{...model,findings:undefined,assessments:undefined},candidateExecuted:false,
  limitations:['Assessments are based on source inspection and may be incorrect.','Compilation, execution and formal verification have not run.','No issues identified does not mean proven secure or deployable.'],
  learning:{enabled:false,phase:'Awaiting first reviewed testing phase',policyVersion:'1.0'},
  provenance:{policy:'The backend derives assessments from validated model output. Model claims are never formal evidence.',sourceStored:false}};
}
