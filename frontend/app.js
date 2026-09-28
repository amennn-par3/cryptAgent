const $=id=>document.getElementById(id);
let session=null,busy=false,lastReport=null,submittedSource='';
function el(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
function updateEditor(){const value=$('code').value,lines=value?value.split('\n').length:0,bytes=new TextEncoder().encode(value).length;$('source-meta').textContent=lines+' lines · '+bytes.toLocaleString()+' bytes';$('line-numbers').textContent=Array.from({length:Math.max(lines,1)},(_,i)=>i+1).join('\n');$('verify').disabled=busy||!session||!value.trim()||bytes>65536||lines>2000;}
const connectionBanner=el('div','connection-banner');
connectionBanner.setAttribute('role','status');
connectionBanner.setAttribute('aria-live','polite');
document.querySelector('.profile-panel').before(connectionBanner);
function showConnection(model){
 const ready=model?.state==='ready';
 connectionBanner.dataset.state=ready?'ready':'pending';
 connectionBanner.replaceChildren(el('strong','',ready?'✓ Access confirmed':model?.state==='missing_key'?'API key required':'Connection needs attention'),el('span','',ready?'GPT-5.4 · Medium — ready for code review.':model?.message||'Could not reach the local server. Click Refresh to retry.'));
 $('model-status').textContent='GPT-5.4 · Medium · '+(ready?'Access confirmed':model?.state==='missing_key'?'API key required':'Connection needs attention');
 $('connection-message').classList.toggle('connection-success',ready);
 if(ready)$('connection-message').textContent='✓ Access confirmed. Your key is connected for this server session. The input field is cleared for privacy — you do not need to enter it again. Paste your code and click Verify code.';
}
async function refresh(){try{const response=await fetch('/api/status');if(!response.ok)throw Error('Server unavailable');session=await response.json();showConnection(session.model);}catch{session=null;showConnection(null);}updateEditor();}
function jump(start,end){if($('code').value!==submittedSource)return;const lines=submittedSource.split('\n');const from=lines.slice(0,start-1).join('\n').length+(start>1?1:0),to=lines.slice(0,end).join('\n').length;$('code').focus();$('code').setSelectionRange(from,to);$('code').scrollTop=Math.max(0,(start-4)*23);}
function renderReport(report){const root=$('report');root.replaceChildren();root.append(el('span','verdict-tag',({potential_issues:'POTENTIAL ISSUES',no_issues_identified:'NO ISSUES IDENTIFIED',insufficient_context:'INSUFFICIENT CONTEXT',outside_scope:'OUTSIDE SCOPE',review_unavailable:'REVIEW UNAVAILABLE'})[report.verdict]||'ASSESSMENT UNAVAILABLE'),el('h3','report-title',report.headline),el('p','report-summary',report.summary),el('div','report-meta','Source '+report.sourceHash.slice(0,16)+'… · Profile '+report.profileVersion));
 root.append(el('div','report-section','Source review · '+report.findings.length+' items'));
 if(!report.findings.length)root.append(el('div','notice','No source concerns were returned by the available reviewers. This does not establish that the code is safe.'));
 for(const f of report.findings){const card=el('article','finding');card.append(el('div','finding-label',f.source==='openai_model'?'AI HYPOTHESIS · UNCONFIRMED':'SOURCE OBSERVATION · UNCONFIRMED'),el('h4','',f.title));const line=el('button','line-button','Lines '+f.lineStart+(f.lineEnd!==f.lineStart?'–'+f.lineEnd:''));line.addEventListener('click',()=>jump(f.lineStart,f.lineEnd));card.append(line,el('pre','',f.quote),el('p','',f.explanation),el('p','',f.evidence));root.append(card);}
 root.append(el('div','report-section','Assessment by requirement'));
 for(const check of report.checks){const row=el('div','check-row');row.append(el('span','',check.title),el('span','',({potential_issue:'Potential issue',no_issue_identified:'No issue identified',insufficient_context:'Needs context',not_applicable:'Outside scope',not_reviewed:'Not reviewed'})[check.assessment]||'Not reviewed'));root.append(row,el('p','check-reason',check.reason));}
 root.append(el('div','report-section','Independent verification'),el('div','notice','Execution: '+(report.execution?.status||'not_run')+'. Formal verification: '+(report.formalVerification?.status||'not_run')+'. A source-review assessment is not a proof of security.'));
 root.append(el('div','report-section','AI & scope'),el('div','notice',report.model.message+' '+report.limitations.join(' ')));
 $('empty-state').hidden=true;$('loading-state').hidden=true;root.hidden=false;$('download').hidden=false;
}
$('code').addEventListener('input',updateEditor);$('code').addEventListener('scroll',()=>{$('line-numbers').scrollTop=$('code').scrollTop;});
$('code').addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();const t=e.target;t.setRangeText('    ',t.selectionStart,t.selectionEnd,'end');updateEditor();}});
$('upload').addEventListener('click',()=>$('file').click());
$('file').addEventListener('change',async()=>{const file=$('file').files[0];if(!file)return;try{if(file.size>65536)throw Error('The source file must be at most 64 KiB.');if(!/\.(cpp|cc|cxx|h|hpp)$/i.test(file.name))throw Error('Choose a C++ source or header file.');$('code').value=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());$('filename').textContent=file.name;$('request-error').hidden=true;updateEditor();}catch(e){$('request-error').textContent=e.message;$('request-error').hidden=false;}$('file').value='';});
$('clear').addEventListener('click',()=>{$('code').value='';$('filename').textContent='untitled.cpp';$('report').hidden=true;$('empty-state').hidden=false;$('download').hidden=true;$('request-error').hidden=true;lastReport=null;updateEditor();});
$('refresh').addEventListener('click',refresh);
$('verify').addEventListener('click',async()=>{if(busy||!session)return;busy=true;submittedSource=$('code').value;$('code').readOnly=true;$('upload').disabled=true;$('clear').disabled=true;$('request-error').hidden=true;$('empty-state').hidden=true;$('report').hidden=true;$('loading-state').hidden=false;$('download').hidden=true;$('verify-label').textContent='Reviewing…';updateEditor();
 try{const response=await fetch('/api/verify',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':session.sessionToken},signal:AbortSignal.timeout(135000),body:JSON.stringify({code:submittedSource,profileId:session.profile.id,mode:'verify'})});const data=await response.json();if(!response.ok)throw Error(data.error||'Review failed.');lastReport=data;renderReport(data);}catch(e){$('request-error').textContent=e.name==='TimeoutError'?'Review timed out. No verdict was produced.':e.message;$('request-error').hidden=false;$('loading-state').hidden=true;$('empty-state').hidden=false;lastReport=null;}finally{busy=false;$('code').readOnly=false;$('upload').disabled=false;$('clear').disabled=false;$('verify-label').textContent='Verify code';updateEditor();}
});
$('download').addEventListener('click',()=>{if(!lastReport)return;const url=URL.createObjectURL(new Blob([JSON.stringify(lastReport,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='cryptagent-'+lastReport.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

$('connect-form').addEventListener('submit',async event=>{
 event.preventDefault();if(!session){$('connection-message').textContent='Connecting to the local server. Please try again shortly.';await refresh();return;}
 const apiKey=$('api-key').value;$('api-key').value='';
 $('connect-model').disabled=true;$('disconnect-model').disabled=true;
 $('connection-message').classList.remove('connection-success');
 $('connection-message').textContent='Checking GPT-5.4 access… The key field was cleared for privacy.';
 try{
  const response=await fetch('/api/model/connect',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':session.sessionToken},body:JSON.stringify({apiKey}),signal:AbortSignal.timeout(15000)});
  const result=await response.json();
  if(!response.ok)throw Error(result.error||'Connection failed.');
  await refresh();
  if(result.model.state!=='ready'){$('connection-message').classList.remove('connection-success');$('connection-message').textContent=result.model.message+' The key field was cleared for privacy.';}
 }catch(e){$('connection-message').textContent=e.name==='TimeoutError'?'Connection check timed out.':e.message;}
 finally{$('connect-model').disabled=false;$('disconnect-model').disabled=false;}
});
$('disconnect-model').addEventListener('click',async()=>{
 if(!session)return;
 try{
  const response=await fetch('/api/model/connect',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':session.sessionToken},body:JSON.stringify({apiKey:''}),signal:AbortSignal.timeout(15000)});
  if(!response.ok)throw Error();
  $('api-key').value='';$('connection-message').textContent='API key removed from this server session.';
  await refresh();
 }catch{$('connection-message').textContent='Could not disconnect. Try again.';}
});
refresh().then(()=>{if(session?.model.state==='missing_key')$('model-setup').open=true;});updateEditor();
