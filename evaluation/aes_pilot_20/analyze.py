"""Score fixed probe assertions through CryptAgent's production review validator.

Untargeted checks are deliberately not counted as false positives: these short
excerpts may contain additional, unadjudicated issues. Human review is required.
"""
import collections
import json
from pathlib import Path
import subprocess
from cases import CASES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / 'results_20261001'
raw = json.loads((RESULTS / 'raw_results.json').read_text())
by_id = {row['id']: row for row in raw['results']}
check_ids = ('F01', 'F02', 'F03', 'F04', 'F05')
rows = []
for c in CASES:
    lines = c['source'].splitlines()
    checks = []
    findings = []
    for check_id in check_ids:
        if c['scope'] == 'outside_scope':
            assessment = 'not_applicable'
        elif check_id in c['issues']:
            assessment = 'potential_issue'
            quote = c['issues'][check_id]
            line = next(i for i, value in enumerate(lines, 1) if quote in value)
            findings.append(dict(check_id=check_id, line_start=line, line_end=line,
                                 quote=quote, rationale=c['note'] or 'Visible concern.'))
        elif check_id in c['abstentions'] or c['scope'] == 'unclear':
            assessment = 'insufficient_context'
        elif check_id in c['controls']:
            assessment = 'no_issue_identified'
        else:
            assessment = 'insufficient_context'
        checks.append(dict(check_id=check_id, assessment=assessment,
                           reason=c['note'] or 'The excerpt does not show the complete integration.'))
    expected = dict(scope=c['scope'], checks=checks, findings=findings)
    for mode in ('base', 'adapter'):
        prediction = by_id[c['id']]['predictions'][mode]
        rows.append(dict(id=c['id'] + '::' + mode, source=c['source'], expected=expected,
                         output=prediction.get('text', '')))
node = ROOT / 'runtime/node-v22.23.3-linux-x64/bin/node'
scorer = ROOT / 'training/score_aes.mjs'
proc = subprocess.run([str(node), str(scorer)], input=json.dumps(rows), text=True,
                      capture_output=True, check=True)
scores = json.loads(proc.stdout)
if len(scores) != 40:
    raise SystemExit('Unexpected comparison count')
by_score = {row['id']: row for row in scores}
details = []
counts = {mode: collections.Counter() for mode in ('base', 'adapter')}
for c in CASES:
    item = dict(id=c['id'], scope=c['scope'], issues=c['issues'],
                controls=c['controls'], abstentions=c['abstentions'], note=c['note'])
    for mode in ('base', 'adapter'):
        score = by_score[c['id'] + '::' + mode]
        result = by_id[c['id']]['predictions'][mode]
        review = score.get('review', {})
        assessments = {x['checkId']: x['assessment'] for x in review.get('assessments', [])}
        issue_hits = {}
        for check_id, quote in c['issues'].items():
            expected_line = next(i for i, line in enumerate(c['source'].splitlines(), 1) if quote in line)
            located = any(f['checkId'] == check_id and quote in f['quote'] and
                          f['lineStart'] <= expected_line <= f['lineEnd']
                          for f in review.get('findings', []))
            issue_hits[check_id] = bool(score['valid'] and assessments.get(check_id) == 'potential_issue' and located)
            counts[mode]['issue_targets'] += 1
            counts[mode]['issue_hits'] += issue_hits[check_id]
        control_hits = {check_id: bool(score['valid'] and assessments.get(check_id) != 'potential_issue')
                        for check_id in c['controls']}
        for hit in control_hits.values():
            counts[mode]['control_targets'] += 1
            counts[mode]['control_hits'] += hit
        abstention_hits = {check_id: bool(score['valid'] and assessments.get(check_id) == 'insufficient_context')
                           for check_id in c['abstentions']}
        for hit in abstention_hits.values():
            counts[mode]['abstention_targets'] += 1
            counts[mode]['abstention_hits'] += hit
        counts[mode]['valid_outputs'] += bool(score['valid'] and score['state'] == 'completed')
        counts[mode]['scope_hits'] += bool(score['valid'] and score['scopeCorrect'])
        counts[mode]['cases'] += 1
        counts[mode]['seconds'] += result.get('seconds', 0)
        item[mode] = dict(inference_state=result['state'], valid=score['valid'],
                          validator_state=score.get('state'), error=score.get('error'),
                          scope=review.get('scope'), assessments=assessments,
                          findings=review.get('findings', []), discarded=review.get('discarded'),
                          issue_hits=issue_hits, control_hits=control_hits,
                          abstention_hits=abstention_hits, seconds=result.get('seconds', 0))
    details.append(item)
report = dict(provenance={k: raw[k] for k in ('created_at', 'base_model', 'base_revision', 'adapter',
            'adapter_sha256', 'cases_sha256', 'prompt_sha256', 'profile_sha256', 'training_overlap', 'test_policy')},
              counts={mode: dict(value) for mode, value in counts.items()}, details=details,
              interpretation='Targeted source-review assertions, not whole-program correctness or native execution. Untargeted findings require human adjudication.')
(RESULTS / 'assessment.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report['counts'], indent=2))
for item in details:
    print(item['id'], 'expected', ','.join(item['issues']) or '-', 'base', item['base']['issue_hits'],
          'adapter', item['adapter']['issue_hits'], 'valid', item['base']['valid'], item['adapter']['valid'])
