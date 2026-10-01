"""Verify provenance and line mappings; flag structural clones without merging labels."""
import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path
import textwrap

class Shape(ast.NodeTransformer):
    def visit_Name(self,node): node.id='_identifier'; return node
    def visit_arg(self,node): node.arg='_argument'; return node
    def visit_FunctionDef(self,node): node.name='_function'; return self.clean(node)
    def visit_AsyncFunctionDef(self,node): node.name='_function'; return self.clean(node)
    def visit_ClassDef(self,node): node.name='_class'; return self.clean(node)
    def clean(self,node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str): node.body=node.body[1:]
        return node

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dataset',type=Path,required=True)
    root=ap.parse_args().dataset.resolve()
    candidates=[json.loads(s) for s in (root/'candidates.jsonl').read_text().splitlines()]
    reviewed=[json.loads(s) for s in (root/'reviewed.jsonl').read_text().splitlines()]
    ids=set(); exact=set(); shapes=collections.defaultdict(list); family_splits={}; file_splits={}
    source_cache={}; requires_enclosing_class=[]
    for row in candidates:
        assert row['id'] not in ids; ids.add(row['id'])
        assert row['AST_sha256'] not in exact; exact.add(row['AST_sha256'])
        assert row['label'] is None and row['training_eligible'] is False
        src=row['source']; path=Path(src['local_path'])
        if str(path) not in source_cache: source_cache[str(path)]=path.read_bytes()
        assert hashlib.sha256(source_cache[str(path)]).hexdigest()==src['file_sha256']
        assert hashlib.sha256(row['code'].encode()).hexdigest()==src['code_sha256']
        assert family_splits.setdefault(row['family'],row['proposed_split'])==row['proposed_split']
        assert file_splits.setdefault(str(path),row['proposed_split'])==row['proposed_split']
        try:
            tree=ast.parse(textwrap.dedent(row['code']))
        except IndentationError:
            # Unindented text inside multiline docstrings can defeat dedent;
            # preserve the exact source and supply its original class context.
            tree=ast.parse('class _Context:\n'+row['code'])
            requires_enclosing_class.append(row['id'])
        shape=hashlib.sha256(ast.dump(Shape().visit(tree),include_attributes=False).encode()).hexdigest()
        shapes[shape].append(row['id'])
    clone_groups=[dict(ids=members,action='manual_semantic_review_only') for members in shapes.values() if len(members)>1]
    labels_by_code=collections.defaultdict(set)
    for row in reviewed:
        assert row['id'] in ids and row['label'] in ('secure','insecure','ambiguous')
        assert 0<=row['confidence']<=1 and row['assessment_scope'] and row['explanation']
        response=json.loads(row['messages'][-1]['content'])
        assert response==row['expected'] and response['label']==row['label']
        lines=row['code'].splitlines()
        payload=json.loads(row['messages'][-2]['content'])
        assert [x['text'] for x in payload['code_lines']]==lines
        for f in response['findings']+response['secure_practices']:
            assert 1<=f['line_start']<=f['line_end']<=len(lines)
            assert f['quote'] in '\n'.join(lines[f['line_start']-1:f['line_end']])
            assert f['source_line_start']==row['source']['line_start']+f['line_start']-1
        if row['label']=='insecure': assert response['findings']
        labels_by_code[row['source']['code_sha256']].add(row['label'])
    contradictions=[key for key,values in labels_by_code.items() if len(values)>1]
    assert not contradictions
    report=dict(validation='passed',candidate_records=len(candidates),reviewed_records=len(reviewed),
                exact_AST_duplicates_retained=0,structural_clone_review_groups=len(clone_groups),
                reviewed_label_contradictions=contradictions,provenance_and_line_mapping='passed',
                proposed_family_and_file_split_isolation='passed',semantic_split_independence='not_established',
                snippets_requiring_enclosing_class=requires_enclosing_class,
                training_ready=False)
    (root/'structural-clone-review.json').write_text(json.dumps(clone_groups,indent=2)+'\n')
    (root/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    example=next(r for r in reviewed if r['source']['symbol']=='MessageAuthenticator')
    (root/'example-finding.json').write_text(json.dumps(dict(source=example['source'],**example['expected']),indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
