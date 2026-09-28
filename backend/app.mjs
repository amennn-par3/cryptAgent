import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {profile,verify} from './verifier.mjs';
import {modelStatus,connectModel} from './llm_client.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const token=randomBytes(32).toString('hex');let active=0;
const assets=new Map([['/',['frontend/index.html','text/html; charset=utf-8']],['/styles.css',['frontend/styles.css','text/css; charset=utf-8']],['/app.js',['frontend/app.js','text/javascript; charset=utf-8']]]);
function headers(res){res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('Cache-Control','no-store');res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'");}
function json(res,status,data){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(data));}
async function body(req){const parts=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>524288){const e=new Error('Request too large');e.status=413;throw e;}parts.push(chunk);}try{return JSON.parse(Buffer.concat(parts).toString('utf8'));}catch{const e=new Error('Invalid JSON');e.status=400;throw e;}}
export function createApp(){return http.createServer({requestTimeout:150000,headersTimeout:10000,maxHeaderSize:8192},async(req,res)=>{
 headers(res);
 if(!['127.0.0.1:8000','localhost:8000'].includes(req.headers.host)){json(res,403,{error:'Invalid host'});return;}
 if(req.headers.origin&&!['http://127.0.0.1:8000','http://localhost:8000'].includes(req.headers.origin)){json(res,403,{error:'Cross-origin requests are not allowed'});return;}
 const route=(req.url||'/').split('?')[0];
 try{
  if(req.method==='GET'&&assets.has(route)){const [file,type]=assets.get(route);res.writeHead(200,{'Content-Type':type});res.end(await readFile(path.join(root,file)));return;}
  if(req.method==='GET'&&route==='/api/status'){json(res,200,{profile,model:await modelStatus(),sessionToken:token,capabilities:{sourceReview:true,llmReview:'openai_api_key_required',nativeExecution:false,generation:false,learning:false}});return;}
  if(req.method==='POST'&&(route==='/api/verify'||route==='/api/model/connect')){
   const supplied=req.headers['x-session-token'];
   if(typeof supplied!=='string'||!/^[0-9a-f]{64}$/.test(supplied)||!timingSafeEqual(Buffer.from(supplied),Buffer.from(token))){json(res,403,{error:'Reload the page to refresh your local session.'});return;}
   if(!req.headers['content-type']?.startsWith('application/json')){json(res,415,{error:'JSON required'});return;}
   if(active>=2){json(res,429,{error:'Two reviews are already running. Please wait.'});return;}
   const data=await body(req);
   if(route==='/api/model/connect'){
    if(!data||Array.isArray(data)||typeof data!=='object'||Object.keys(data).some(k=>k!=='apiKey')||typeof data.apiKey!=='string'||data.apiKey.length>512){json(res,400,{error:'Invalid connection request.'});return;}
    active++;try{json(res,200,{model:await connectModel(data.apiKey)});}catch{json(res,400,{error:'Use a valid API-key format.'});}finally{active--;}return;
   }
   if(!data||Array.isArray(data)||typeof data!=='object'||Object.keys(data).some(k=>!['code','profileId','mode'].includes(k))||data.profileId!==profile.id||data.mode!=='verify'||typeof data.code!=='string'){json(res,400,{error:'Unsupported request or profile.'});return;}
   const source=data.code.replace(/\r\n?/g,'\n');
   if(!source.trim()||source.includes('\0')||Buffer.byteLength(source)>profile.maxSourceBytes||source.split('\n').length>profile.maxSourceLines){json(res,400,{error:'Use nonempty C++ source, at most 64 KiB and 2,000 lines, with no null bytes.'});return;}
   active++;try{json(res,200,await verify(source));}finally{active--;}return;
  }
  json(res,404,{error:'Not found'});
 }catch(e){if(!res.headersSent)json(res,e.status||500,{error:e.status?e.message:'Review could not complete. No security conclusion was produced.'});else res.end();}
});}
if(typeof process!=='undefined'&&process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const server=createApp();server.requestTimeout=150000;server.headersTimeout=10000;
 server.on('error',e=>{console.error(e.code==='EADDRINUSE'?'Port 8000 is already in use.':e.message);process.exitCode=1;});
 server.listen(8000,'127.0.0.1',()=>console.log('Cryptagent is ready at http://127.0.0.1:8000'));
}
