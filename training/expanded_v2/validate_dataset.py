"""Validate the draft without promoting it to a train-ready dataset."""
import ast
import collections
import json
from build_dataset import HERE, ROOT, V1, digest, validator


def main():
    manifest = json.loads((HERE / 'data/manifest.json').read_text())
    assert manifest['training_ready'] is False
    families, hashes, identifiers, datasets = {}, {}, set(), {}
    for split in ('train', 'validation', 'regression'):
        path = HERE / f'data/{split}.jsonl'
        assert digest(path) == manifest['sha256'][split]
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        datasets[split] = rows
        assert len(rows) == manifest['counts'][split]
        for row in rows:
            assert row['id'] not in identifiers
            identifiers.add(row['id'])
            assert families.setdefault(row['family'], split) == split
            assert hashes.setdefault(row['source_sha256'], split) == split
            import hashlib
            assert hashlib.sha256(row['source'].encode()).hexdigest() == row['source_sha256']
            prefix = 'F' if row['profile_id'].startswith('aes') else 'H'
            validator.validate_answer(row['expected'], row['source'], [f'{prefix}0{i}' for i in range(1, 6)])
            assert json.loads(row['messages'][-1]['content']) == row['expected']
            payload = json.loads(row['messages'][-2]['content'])
            assert '\n'.join(line['text'] for line in payload['untrusted_source']) == row['source']
    for old_split in ('train', 'validation', 'test'):
        assert digest(V1 / f'data/{old_split}.jsonl') == manifest['v1_sha256'][old_split]
    assert (HERE / 'data/validation.jsonl').read_bytes() == (V1 / 'data/validation.jsonl').read_bytes()
    assert (HERE / 'data/regression.jsonl').read_bytes() == (V1 / 'data/test.jsonl').read_bytes()
    path = HERE / 'data/additions.jsonl'
    assert digest(path) == manifest['sha256']['additions']
    additions = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(additions) == manifest['counts']['additions'] == 9
    assert datasets['train'][-9:] == additions
    previous = [json.loads(line) for line in (V1 / 'data/train.jsonl').read_text().splitlines()]
    assert datasets['train'][:-9] == previous
    targets = collections.Counter()
    for row, case in zip(additions, manifest['new_cases']):
        assert row['id'] == case['id']
        source_path = ROOT / case['source_path']
        assert source_path.read_text() == row['source']
        assert digest(source_path) == case['source_sha256']
        check = next(c for c in row['expected']['checks'] if c['check_id'] == 'H02')
        assert check['assessment'] == case['target_assessment']
        targets[check['assessment']] += 1
        if source_path.suffix == '.py':
            ast.parse(row['source'])
    assert targets == {'potential_issue': 3, 'no_issue_identified': 3, 'insufficient_context': 3}
    print(json.dumps({'validation': 'passed', 'counts': manifest['counts'],
                      'new_H02_labels': dict(targets), 'family_split_disjoint': True,
                      'v1_preserved': True, 'training_ready': False}, indent=2))


if __name__ == '__main__':
    main()
