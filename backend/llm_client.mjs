import {readFile} from 'node:fs/promises';
const ENDPOINT='https://api.openai.com/v1';
const MODEL='gpt-5.4';
const EFFORT='medium';
const prompt=await readFile(new URL('../prompts/verify.txt',import.meta.url),'utf8');
// The browser can configure a key for this server session. Never persist or return it.
let apiKey=typeof process!=='undefined'?(process.env.OPENAI_API_KEY||'').trim():'';
let cached=null;
const schema={type:'object',additionalProperties:false,required:['scope','checks','findings'],properties:{
 scope:{type:'string',enum:['in_scope','outside_scope','unclear']},
 checks:{type:'array',minItems:5,maxItems:5,items:{type:'object',additionalProperties:false,required:['check_id','assessment','reason'],properties:{
  check_id:{type:'string',enum:['F01','F02','F03','F04','F05']},
  assessment:{type:'string',enum:['potential_issue','no_issue_identified','insufficient_context','not_applicable']},
  reason:{type:'string',minLength:1,maxLength:800}
 }}},
 findings:{type:'array',maxItems:8,items:{type:'object',additionalProperties:false,required:['check_id','line_start','line_end','quote','rationale'],properties:{
  check_id:{type:'string',enum:['F01','F02','F03','F04','F05']},line_start:{type:'integer',minimum:1},line_end:{type:'integer',minimum:1},
  quote:{type:'string',minLength:1,maxLength:1200},rationale:{type:'string',minLength:1,maxLength:800}
 }}}
}};
function base(){return {model:MODEL,reasoningEffort:EFFORT,provider:'OpenAI API',digest:null};}
function failureMessage(status){return status===401?'The OpenAI API key was rejected.':status===403||status===404?'This API project cannot access GPT-5.4. No other model will be used.':status===429?'OpenAI reported a rate or quota limit. Check the API project billing and limits.':'The OpenAI API request failed. No model conclusion was accepted.';}
async function boundedJson(response,maxBytes){
  if(!response.ok){await response.body?.cancel();const e=new Error(failureMessage(response.status));e.apiStatus=response.status;throw e;}
  const reader=response.body.getReader();let total=0;const chunks=[];
  try{while(true){const {done,value}=await reader.read();if(done)break;total+=value.length;if(total>maxBytes){await reader.cancel();throw new Error('Response exceeds limit');}chunks.push(Buffer.from(value));}}finally{reader.releaseLock();}
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
async function checkAccess(key){
  if(!key)return {...base(),state:'missing_key',message:'Connect an OpenAI API key to enable GPT-5.4 · Medium.'};
  try{const data=await boundedJson(await fetch(ENDPOINT+'/models/'+MODEL,{headers:{Authorization:'Bearer '+key},redirect:'error',signal:AbortSignal.timeout(10000)}),65536);
    if(data.id!==MODEL)throw new Error('Unexpected model identity');
    return {...base(),state:'ready',message:'GPT-5.4 access confirmed. Reviews use medium reasoning only.'};
  }catch(e){return {...base(),state:e.apiStatus===401?'invalid_key':e.apiStatus===403||e.apiStatus===404?'access_denied':'error',message:e.apiStatus?failureMessage(e.apiStatus):'Could not confirm OpenAI access. Check the network connection and API project.'};}
}
export async function connectModel(key){
  if(typeof key!=='string'||key.length>512)throw new Error('Invalid key format');
  const candidate=key.trim();
  if(candidate===''){apiKey='';cached=null;return modelStatus();}
  if(!/^[\x21-\x7e]{20,512}$/.test(candidate))throw new Error('Invalid key format');
  const result=await checkAccess(candidate);
  if(result.state==='ready'){apiKey=candidate;cached={at:Date.now(),status:result};}
  return result;
}
export async function modelStatus(){
  if(!apiKey)return {...base(),state:'missing_key',message:'Connect an OpenAI API key to enable GPT-5.4 · Medium.'};
  if(cached&&Date.now()-cached.at<30000)return cached.status;
  const result=await checkAccess(apiKey);cached={at:Date.now(),status:result};return result;
}
export async function reviewWithModel(source,profile){
  const status=await modelStatus();
  if(status.state!=='ready')return {...status,findings:[],discarded:0,sourceSent:false};
  let sourceSent=false;
  try{
    const input=[{role:'developer',content:prompt},{role:'developer',content:JSON.stringify({profile_id:profile.id,scheme:profile.scheme,library:profile.library,attacker:profile.attacker,checks:profile.checks})},{role:'user',content:JSON.stringify({untrusted_source:source.split('\n').map((text,i)=>({line:i+1,text}))})}];
    if(Buffer.byteLength(JSON.stringify(input),'utf8')>262144)return {...status,state:'skipped',message:'The full request exceeds the application limit. Nothing was truncated or sent.',findings:[],discarded:0,sourceSent:false};
    sourceSent=true;
    const response=await fetch(ENDPOINT+'/responses',{method:'POST',headers:{Authorization:'Bearer '+apiKey,'Content-Type':'application/json'},redirect:'error',signal:AbortSignal.timeout(120000),body:JSON.stringify({model:MODEL,reasoning:{effort:EFFORT},store:false,truncation:'disabled',max_output_tokens:8000,input,text:{format:{type:'json_schema',name:'cryptographic_review',strict:true,schema}}})});
    const requestId=response.headers.get('x-request-id');
    const data=await boundedJson(response,262144);
    if(data.status!=='completed')return {...status,state:'incomplete',message:'The model response did not complete. No partial findings were accepted.',findings:[],discarded:0,sourceSent,requestId};
    if(data.reasoning?.effort&&data.reasoning.effort!==EFFORT)throw new Error('Unexpected reasoning effort');
    const content=(data.output||[]).filter(x=>x.type==='message').flatMap(x=>x.content||[]);
    if(content.some(x=>x.type==='refusal'))return {...status,state:'refused',message:'The model declined this request. No findings were invented.',findings:[],discarded:0,sourceSent,requestId};
    const parsed=JSON.parse(content.filter(x=>x.type==='output_text').map(x=>x.text).join(''));
    if(!parsed||Object.keys(parsed).some(k=>!['scope','checks','findings'].includes(k))||!Array.isArray(parsed.findings)||parsed.findings.length>8)throw new Error('Invalid findings');
    if(!['in_scope','outside_scope','unclear'].includes(parsed.scope)||!Array.isArray(parsed.checks)||parsed.checks.length!==profile.checks.length)throw new Error('Invalid assessment');
    const seen=new Set();
    for(const check of parsed.checks){
      if(!check||Object.keys(check).some(k=>!['check_id','assessment','reason'].includes(k))||!profile.checks.some(c=>c.id===check.check_id)||seen.has(check.check_id)||!['potential_issue','no_issue_identified','insufficient_context','not_applicable'].includes(check.assessment)||typeof check.reason!=='string'||!check.reason.trim()||check.reason.length>800)throw new Error('Invalid check assessment');
      seen.add(check.check_id);
    }
    if(parsed.scope==='outside_scope'&&(parsed.findings.length||parsed.checks.some(c=>c.assessment!=='not_applicable')))throw new Error('Contradictory scope');
    if(parsed.scope==='in_scope'&&parsed.checks.some(c=>c.assessment==='not_applicable'))throw new Error('Missing applicable check');
    if(parsed.findings.some(f=>!parsed.checks.some(c=>c.check_id===f.check_id&&c.assessment==='potential_issue')))throw new Error('Finding contradicts assessment');
    const lines=source.split('\n'),valid=[];let discarded=0;
    for(const f of parsed.findings){
      if(!f||Object.keys(f).some(k=>!['check_id','line_start','line_end','quote','rationale'].includes(k))||!profile.checks.some(c=>c.id===f.check_id)||!Number.isInteger(f.line_start)||!Number.isInteger(f.line_end)||f.line_start<1||f.line_end<f.line_start||f.line_end>lines.length||f.line_end-f.line_start>7||typeof f.quote!=='string'||!f.quote.trim()||f.quote.length>1200||typeof f.rationale!=='string'||!f.rationale.trim()||f.rationale.length>800||!lines.slice(f.line_start-1,f.line_end).join('\n').includes(f.quote)){discarded++;continue;}
      valid.push({checkId:f.check_id,title:'AI review hypothesis',kind:'hypothesis',source:'openai_model',lineStart:f.line_start,lineEnd:f.line_end,quote:f.quote,explanation:f.rationale,evidence:'Exact quote validated. Interpretation has not been independently confirmed.'});
    }
    const assessments=parsed.checks.map(c=>({
      checkId:c.check_id,assessment:c.assessment==='potential_issue'&&!valid.some(f=>f.checkId===c.check_id)?'insufficient_context':c.assessment,
      reason:c.assessment==='potential_issue'&&!valid.some(f=>f.checkId===c.check_id)?'The proposed issue had no valid source reference; more evidence is needed.':c.reason
    }));
    return {...status,scope:parsed.scope,assessments,state:discarded?'partial':'completed',findings:valid,discarded,sourceSent,requestId,resolvedModel:data.model,responseId:data.id,usage:data.usage,message:discarded?'Some AI findings were rejected because their references were invalid.':'GPT-5.4 · Medium review completed. Interpretations remain unconfirmed hypotheses.'};
  }catch(e){if(e.apiStatus===401)cached=null;return {...status,state:'error',message:e.apiStatus?failureMessage(e.apiStatus):e.name==='TimeoutError'?'The GPT-5.4 review timed out. No model conclusion was accepted.':'The GPT-5.4 response could not be validated. No model findings were accepted.',findings:[],discarded:0,sourceSent};}
}
