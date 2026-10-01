// Quotes establish source location, not the correctness of a model opinion.
export const checkIds = ['F01', 'F02', 'F03', 'F04', 'F05'];
const assessments = ['potential_issue', 'no_issue_identified', 'insufficient_context', 'not_applicable'];
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const exactKeys = (value, keys) => object(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const text = (value, limit) => typeof value === 'string' && value.trim().length > 0 && value.length <= limit;

export function validateReview(parsed, source) {
  if (!exactKeys(parsed, ['scope', 'checks', 'findings']) ||
      !['in_scope', 'outside_scope', 'unclear'].includes(parsed.scope) ||
      !Array.isArray(parsed.checks) || parsed.checks.length !== checkIds.length ||
      !Array.isArray(parsed.findings) || parsed.findings.length > 8) throw new Error('Invalid review structure');
  const seen = new Set();
  for (const check of parsed.checks) {
    if (!exactKeys(check, ['check_id', 'assessment', 'reason']) || !checkIds.includes(check.check_id) ||
        seen.has(check.check_id) || !assessments.includes(check.assessment) || !text(check.reason, 800)) {
      throw new Error('Invalid requirement assessment');
    }
    seen.add(check.check_id);
  }
  if (parsed.scope === 'outside_scope' && (parsed.findings.length || parsed.checks.some(c => c.assessment !== 'not_applicable'))) throw new Error('Contradictory scope');
  if (parsed.scope !== 'outside_scope' && parsed.checks.some(c => c.assessment === 'not_applicable')) throw new Error('Applicable requirement omitted');
  if (parsed.findings.some(f => !object(f) || !parsed.checks.some(c => c.check_id === f.check_id && c.assessment === 'potential_issue'))) {
    throw new Error('Finding contradicts requirement assessment');
  }
  const lines = source.split('\n');
  const findings = [];
  let discarded = 0;
  for (const finding of parsed.findings) {
    if (!exactKeys(finding, ['check_id', 'line_start', 'line_end', 'quote', 'rationale']) ||
        !checkIds.includes(finding.check_id) ||
        !parsed.checks.some(c => c.check_id === finding.check_id && c.assessment === 'potential_issue') ||
        !Number.isInteger(finding.line_start) || !Number.isInteger(finding.line_end) ||
        finding.line_start < 1 || finding.line_end < finding.line_start || finding.line_end > lines.length ||
        finding.line_end - finding.line_start > 7 || !text(finding.quote, 1200) || !text(finding.rationale, 800) ||
        !lines.slice(finding.line_start - 1, finding.line_end).join('\n').includes(finding.quote)) {
      discarded++;
      continue;
    }
    findings.push({checkId: finding.check_id, title: 'Potential issue', kind: 'hypothesis', source: 'local_model',
      lineStart: finding.line_start, lineEnd: finding.line_end, quote: finding.quote,
      explanation: finding.rationale, evidence: 'Source quote checked; security interpretation requires review.'});
  }
  return {scope: parsed.scope, findings, discarded, state: discarded ? 'partial' : 'completed',
    assessments: parsed.checks.map(c => {
      const unsupported = c.assessment === 'potential_issue' && !findings.some(f => f.checkId === c.check_id);
      return {checkId: c.check_id, assessment: unsupported ? 'insufficient_context' : c.assessment,
        reason: unsupported ? 'The proposed issue had no valid source reference; more evidence is needed.' : c.reason};
    })};
}
