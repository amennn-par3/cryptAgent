"""Report held-out agreement with authored labels, never security certification."""
import argparse
import hashlib
import json
from pathlib import Path

def summarize(path):
    data=json.loads(path.read_text())
    rows=data['results']
    test=Path(__file__).resolve().parent/'data/test.jsonl'
    if hashlib.sha256(test.read_bytes()).hexdigest()!=data['test_sha256']:
        raise ValueError('Test data no longer matches this recorded comparison')
    expected={r['id']:r['expected'] for r in (json.loads(line) for line in test.read_text().splitlines())}
    totals={}
    for mode in ('base','fine_tuned'):
        accepted=[r[mode] for r in rows if r.get(mode,{}).get('status')=='completed']
        totals[mode]={'accepted':len(accepted),'cases':len(rows),
            'scope_matches':sum(r.get('scope_match',False) for r in accepted),
            'check_matches':sum(r.get('matched_checks',0) for r in accepted),
            'total_check_slots':5*len(rows),
            'inference_seconds':sum(r.get(mode,{}).get('seconds',0) for r in rows)}
        for label,assessment in [('target_issues','potential_issue'),('target_controls','no_issue_identified')]:
            slots=[(r,c['check_id']) for r in rows for c in expected[r['id']]['checks'] if c['assessment']==assessment]
            matched=0
            for r,cid in slots:
                result=r.get(mode,{})
                if result.get('status')=='completed' and any(c['check_id']==cid and c['assessment']==assessment for c in result['response']['checks']): matched+=1
            totals[mode][label]={'matched':matched,'total':len(slots)}
    text=['# Base versus fine-tuned Llama: initial held-out pilot','',
        f"Base: `{data['base_model']}` at revision `{data['revision']}`.",
        f"Frozen test set SHA-256: `{data['test_sha256']}`.",'',
        '| Metric | Base | Fine-tuned |','|---|---:|---:|',
        f"| Accepted JSON and exact source references | {totals['base']['accepted']}/{len(rows)} | {totals['fine_tuned']['accepted']}/{len(rows)} |",
        f"| Scope matches to authored labels | {totals['base']['scope_matches']}/{len(rows)} | {totals['fine_tuned']['scope_matches']}/{len(rows)} |",
        f"| Requirement-label matches | {totals['base']['check_matches']}/{5*len(rows)} | {totals['fine_tuned']['check_matches']}/{5*len(rows)} |",
        f"| Targeted defect checks identified with valid references | {totals['base']['target_issues']['matched']}/{totals['base']['target_issues']['total']} | {totals['fine_tuned']['target_issues']['matched']}/{totals['fine_tuned']['target_issues']['total']} |",
        f"| Corrected target checks assessed as no issue | {totals['base']['target_controls']['matched']}/{totals['base']['target_controls']['total']} | {totals['fine_tuned']['target_controls']['matched']}/{totals['fine_tuned']['target_controls']['total']} |",
        f"| Total inference seconds | {totals['base']['inference_seconds']:.1f} | {totals['fine_tuned']['inference_seconds']:.1f} |",'',
        'Rejected/unavailable outputs contribute zero matches; the denominator includes all cases.',
        'Many nontarget labels are insufficient_context. High overall label agreement can therefore coexist with missed defects; inspect the targeted metrics.',
        'These are agreement counts on ten small authored examples, not broad accuracy or security certification.',
        'Labels emphasize selected defects; secondary implications and disagreements need independent review.',
        'The model cannot claim native execution. Native fixture witnesses are stored separately.','',
        '| Case | Base response | Base check matches | Fine-tuned response | Fine-tuned check matches |',
        '|---|---|---:|---|---:|']
    for row in rows:
        b=row.get('base',{}); f=row.get('fine_tuned',{})
        text.append(f"| {row['id']} | {b.get('status','missing')} | {b.get('matched_checks',0)}/5 | {f.get('status','missing')} | {f.get('matched_checks',0)}/5 |")
    text+=['','Raw model responses, timing, source hashes and validation errors are in [comparison.json](comparison.json).',
        'The test set was evaluated after training; these results must not be recycled as training targets.']
    (path.parent/'comparison.md').write_text('\n'.join(text)+'\n')
    print(json.dumps(totals,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('comparison',type=Path)
    summarize(ap.parse_args().comparison)
