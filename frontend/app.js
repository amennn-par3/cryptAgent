const $ = id => document.getElementById(id);
let session = null, busy = false, lastReport = null, submittedSource = '';
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function updateEditor() {
  const value = $('code').value;
  const lines = value ? value.split('\n').length : 0;
  const bytes = new TextEncoder().encode(value).length;
  $('source-meta').textContent = lines + ' lines · ' + bytes.toLocaleString() + ' bytes';
  $('line-numbers').textContent = Array.from({length: Math.max(lines, 1)}, (_, i) => i + 1).join('\n');
  $('verify').disabled = busy || !session;
}
function clearReport() {
  lastReport = null;
  $('report').hidden = true;
  $('download').hidden = true;
  $('empty-state').hidden = false;
}
async function refresh() {
  $('refresh').disabled = true;
  try {
    const response = await fetch('/api/status', {signal: AbortSignal.timeout(5000)});
    if (!response.ok) throw Error('Server unavailable');
    session = await response.json();
    $('model-status').textContent = session.model.message;
    document.querySelector('.connection').dataset.ready = String(session.model.state === 'ready');
  } catch {
    session = null;
    $('model-status').textContent = 'Cannot reach the local application. Check the startup terminal.';
    document.querySelector('.connection').dataset.ready = 'false';
  } finally { $('refresh').disabled = false; updateEditor(); }
}
function jump(start, end) {
  if ($('code').value !== submittedSource) return;
  const lines = submittedSource.split('\n');
  const from = lines.slice(0, start - 1).join('\n').length + (start > 1 ? 1 : 0);
  const to = lines.slice(0, end).join('\n').length;
  $('code').focus();
  $('code').setSelectionRange(from, to);
  $('code').scrollTop = Math.max(0, (start - 4) * 23);
}
function renderReport(report) {
  const root = $('report');
  root.replaceChildren(el('h3', 'verdict', report.headline), el('p', 'summary', report.summary),
    el('p', 'meta', 'AES-128-GCM · Source ' + report.sourceHash.slice(0, 16) + '…'));
  for (const finding of report.findings) {
    const card = el('article', 'finding');
    card.append(el('h4', '', finding.checkId + ' · ' + (finding.source === 'local_model' ? 'Model finding' : 'Source observation')));
    const line = el('button', '', 'Lines ' + finding.lineStart + (finding.lineEnd !== finding.lineStart ? '–' + finding.lineEnd : ''));
    line.addEventListener('click', () => jump(finding.lineStart, finding.lineEnd));
    card.append(line, el('pre', '', finding.quote), el('p', '', finding.explanation), el('p', '', finding.evidence));
    root.append(card);
  }
  root.append(el('h4', 'section-label', 'Five AES requirements'));
  const labels = {potential_issue: 'Potential issue', no_issue_identified: 'No issue identified',
    insufficient_context: 'Needs context', not_applicable: 'Outside scope', not_reviewed: 'Not reviewed'};
  for (const check of report.checks) {
    const row = el('div', 'check');
    const title = el('div', 'check-title');
    title.append(el('strong', '', check.id + ' · ' + check.title), el('span', '', labels[check.assessment] || 'Not reviewed'));
    row.append(title, el('p', 'reason', check.reason)); root.append(row);
  }
  root.append(el('p', 'meta', report.model.message), el('p', 'meta', 'Compilation and execution: not run. This review is not a security proof.'));
  $('empty-state').hidden = true; $('loading-state').hidden = true;
  root.hidden = false; $('download').hidden = false;
}
$('code').addEventListener('input', () => { clearReport(); updateEditor(); });
$('code').addEventListener('scroll', () => { $('line-numbers').scrollTop = $('code').scrollTop; });
$('code').addEventListener('keydown', event => {
  if (event.key === 'Tab' && !busy) {
    event.preventDefault();
    event.target.setRangeText('    ', event.target.selectionStart, event.target.selectionEnd, 'end');
    clearReport(); updateEditor();
  }
});
$('upload').addEventListener('click', () => $('file').click());
$('file').addEventListener('change', async () => {
  const file = $('file').files[0]; if (!file) return;
  try {
    if (file.size > 65536) throw Error('The source file must be at most 64 KiB.');
    if (!/\.(cpp|cc|cxx|h|hpp)$/i.test(file.name)) throw Error('Choose a C++ source or header file.');
    $('code').value = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer()).replace(/\r\n?/g, '\n');
    $('filename').textContent = file.name; $('request-error').hidden = true;
    clearReport(); updateEditor();
  } catch (error) { $('request-error').textContent = error.message; $('request-error').hidden = false; }
  $('file').value = '';
});
$('clear').addEventListener('click', () => {
  $('code').value = ''; $('filename').textContent = 'untitled.cpp';
  $('request-error').hidden = true; clearReport(); updateEditor();
});
$('refresh').addEventListener('click', refresh);
$('verify').addEventListener('click', async () => {
  if (busy || !session) return;
  const value = $('code').value.replace(/\r\n?/g, '\n');
  if (!value.trim() || value.includes('\0') || new TextEncoder().encode(value).length > 65536 || value.split('\n').length > 2000) {
    clearReport();
    $('request-error').textContent = 'Paste nonempty source, at most 64 KiB and 2,000 lines, with no null bytes. The AES profile remains fixed; unrelated code is not certified.';
    $('request-error').hidden = false;
    return;
  }
  busy = true; submittedSource = $('code').value.replace(/\r\n?/g, '\n'); $('code').value = submittedSource;
  $('code').readOnly = true; $('upload').disabled = true; $('clear').disabled = true;
  $('request-error').hidden = true; $('empty-state').hidden = true; $('report').hidden = true;
  $('loading-state').hidden = false; $('download').hidden = true; $('verify').textContent = 'Reviewing…'; updateEditor();
  try {
    const response = await fetch('/api/verify', {method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Session-Token': session.sessionToken},
      signal: AbortSignal.timeout(125000),
      body: JSON.stringify({code: submittedSource, profileId: session.profile.id, mode: 'verify'})});
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Review failed.');
    lastReport = data; renderReport(data);
  } catch (error) {
    $('request-error').textContent = error.name === 'TimeoutError' ? 'Review timed out. No verdict was produced.' : error.message;
    $('request-error').hidden = false; $('loading-state').hidden = true; clearReport();
  } finally {
    busy = false; $('code').readOnly = false; $('upload').disabled = false; $('clear').disabled = false;
    $('verify').textContent = 'Review AES code'; await refresh();
  }
});
$('download').addEventListener('click', () => {
  if (!lastReport) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastReport, null, 2)], {type: 'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'cryptagent-' + lastReport.id + '.json';
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
refresh(); updateEditor();
// Refresh loading/recovery status without interrupting an active review.
setInterval(() => { if (!busy && !$('refresh').disabled && session?.model.state !== 'ready') refresh(); }, 5000);
