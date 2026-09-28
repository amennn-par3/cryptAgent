import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const run=promisify(execFile);
const root=new URL('./',import.meta.url);
const manifest=JSON.parse(await readFile(new URL('manifest.json',root),'utf8'));
const offlineOnly=process.argv.includes('--offline-only');
await mkdir(new URL('responses/',root),{recursive:true});
const records=[];
const clean=value=>String(value??'').replaceAll('|','\\|').replaceAll('\n',' ');
async function summary(){
 const lines=['# Cryptagent evaluation','',
 'Model: GPT-5.4, medium reasoning. These are source-review tests, not execution or formal proofs.',
 'Expected outcomes are test intentions, not independently established ground truth. No accuracy percentage is inferred.',
 '',
 '| Case | Intended outcome | Actual outcome | Model status | Matches intention |',
 '|---|---|---|---|---|'];
 for(const test of manifest.cases){
  const r=records.find(x=>x.id===test.id);
  lines.push('| '+[test.id+' '+test.name,test.expected,r?.actual||'Not run',r?.response?.model?.state||'—',r?(r.actual===test.expected?'Yes':'No'):'—'].map(clean).join(' | ')+' |');
 }
 for(const r of records){
  lines.push('','## '+r.id+' '+r.name,'',
   'Input: [C++ source](inputs/'+r.file+'). Response: [full JSON](responses/'+r.id+'.json).',
   '',r.response?.summary||r.transportError||'No summary.',
   '',...((r.response?.checks||[]).map(c=>'- '+c.id+' **'+c.assessment+'**: '+clean(c.reason))),
   '',...((r.response?.findings||[]).map(f=>'- Finding '+f.checkId+', lines '+f.lineStart+'–'+f.lineEnd+' ('+f.source+'): '+clean(f.explanation))));
 }
 await writeFile(new URL('results.md',root),lines.join('\n')+'\n');
 await writeFile(new URL('results.json',root),JSON.stringify({recordedAt:new Date().toISOString(),records},null,2));
}
for(const test of manifest.cases){
 try{records.push(JSON.parse(await readFile(new URL('responses/'+test.id+'.json',root),'utf8')));}catch{}
}
if(!records.some(r=>r.id==='10')){
 const test=manifest.cases.find(t=>t.id==='10');
 const inputPath=fileURLToPath(new URL('inputs/'+test.file,root));
 const verifierUrl=new URL('../backend/verifier.mjs',root).href;
 const script="const {readFile}=await import('node:fs/promises'); const {verify}=await import("+JSON.stringify(verifierUrl)+"); console.log(JSON.stringify(await verify(await readFile("+JSON.stringify(inputPath)+",'utf8'))));";
 const env={...process.env};delete env.OPENAI_API_KEY;
 const {stdout}=await run(process.execPath,['--input-type=module','-e',script],{env,timeout:20000,maxBuffer:1048576,windowsHide:true});
 const response=JSON.parse(stdout);
 const record={...test,recordedAt:new Date().toISOString(),route:'Separate production verifier process with OPENAI_API_KEY removed; no model request',actual:response.verdict,response};
 records.push(record);
 await writeFile(new URL('responses/10.json',root),JSON.stringify(record,null,2));
 await summary();console.log('10: '+record.actual+' ('+response.model.state+')');
}
if(offlineOnly){await summary();process.exit(0);}
const session=await (await fetch('http://127.0.0.1:8000/api/status',{signal:AbortSignal.timeout(15000)})).json();
if(session.model.state!=='ready'){await summary();console.log('WAITING_FOR_API_KEY: Connect the key in the app, then rerun this command. Nine live cases are not run.');process.exit(2);}
for(const test of manifest.cases.filter(t=>t.id!=='10')){
 if(records.some(r=>r.id===test.id))continue;
 console.log('Running '+test.id+' '+test.name);
 const code=await readFile(new URL('inputs/'+test.file,root),'utf8');
 let record={...test,recordedAt:new Date().toISOString(),route:'POST /api/verify on the live local app'};
 try{
  const result=await fetch('http://127.0.0.1:8000/api/verify',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':session.sessionToken},body:JSON.stringify({code,profileId:session.profile.id,mode:'verify'}),signal:AbortSignal.timeout(140000)});
  const response=await result.json();
  record={...record,httpStatus:result.status,actual:response.verdict||'transport_error',response};
 }catch(error){record={...record,actual:'transport_error',transportError:error.name==='TimeoutError'?'Local request timed out.':error.message};}
 records.push(record);
 await writeFile(new URL('responses/'+test.id+'.json',root),JSON.stringify(record,null,2));
 await summary();
 console.log(test.id+': '+record.actual+' ('+(record.response?.model?.state||'no model result')+')');
}
await summary();
console.log('Recorded '+records.length+' cases in evaluation/results.md and responses/.');
