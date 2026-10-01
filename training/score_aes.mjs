// Shared production validator, not regex extraction of model answers.
import {validateReview} from '../backend/review_contract.mjs';
let input = ''; for await (const chunk of process.stdin) input += chunk;
const results = JSON.parse(input).map(row => {
  try {
    const parsed = JSON.parse(row.output);
    const accepted = validateReview(parsed, row.source);
    const expected = row.expected;
    const expectedIssues = expected.checks.filter(c => c.assessment === 'potential_issue');
    const predictedIssues = accepted.assessments.filter(c => c.assessment === 'potential_issue');
    const correct = expected.checks.filter(c => accepted.assessments.some(p => p.checkId === c.check_id && p.assessment === c.assessment)).length;
    const tp = predictedIssues.filter(p => expectedIssues.some(c => c.check_id === p.checkId)).length;
    const located = expectedIssues.filter(c => accepted.findings.some(p => p.checkId === c.check_id &&
      expected.findings.some(f => f.check_id === c.check_id && p.lineStart <= f.line_end && p.lineEnd >= f.line_start))).length;
    return {id: row.id, valid: true, state: accepted.state, correctChecks: correct,
      scopeCorrect: accepted.scope === expected.scope, exact: correct === 5 && accepted.scope === expected.scope,
      tp, fp: predictedIssues.length - tp, fn: expectedIssues.length - tp, located, expectedIssues: expectedIssues.length,
      review: accepted};
  } catch (error) {
    const count = row.expected.checks.filter(c => c.assessment === 'potential_issue').length;
    return {id: row.id, valid: false, error: error.message, correctChecks: 0, scopeCorrect: false,
      exact: false, tp: 0, fp: 0, fn: count, located: 0, expectedIssues: count};
  }
});
console.log(JSON.stringify(results));
