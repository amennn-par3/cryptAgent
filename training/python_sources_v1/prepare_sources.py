"""Read-only source inventory and AST extraction. Never auto-label a library secure."""
import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tokenize
from urllib.parse import urlsplit, urlunsplit

def digest(data): return hashlib.sha256(data).hexdigest()
def git(repo,*args):
    result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
    return result.stdout.strip() if result.returncode==0 else None
def safe_url(url):
    if not url: return None
    if '://' in url:
        p=urlsplit(url)
        return urlunsplit((p.scheme,p.hostname or '',p.path,'',''))
    return re.sub(r'^[^@]+@','',url)
def dump(path,rows):
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))

class WithoutDocs(ast.NodeTransformer):
    def visit_FunctionDef(self,node): return self.clean(node)
    def visit_AsyncFunctionDef(self,node): return self.clean(node)
    def visit_ClassDef(self,node): return self.clean(node)
    def clean(self,node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str):
            node.body=node.body[1:]
        return node

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--sources',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(); root=args.sources.resolve(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    repos=sorted(p.parent for p in root.glob('*/*/.git'))
    inventory=[]; candidates=[]; rejected=[]; duplicates=[]; scheme_index=[]; seen={}
    for repo in repos:
        rev=git(repo,'rev-parse','HEAD'); url=safe_url(git(repo,'remote','get-url','origin'))
        files=[p for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts]
        languages=collections.Counter(p.suffix.lower() or '(no extension)' for p in files)
        licenses=[]
        for p in sorted(repo.iterdir()):
            if p.is_file() and p.name.upper().startswith(('LICENSE','COPYING','COPYRIGHT')):
                licenses.append(dict(path=str(p.relative_to(repo)),sha256=digest(p.read_bytes())))
                dest=out/'licenses'/repo.parent.name/repo.name/p.name
                dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(p.read_bytes())
        inventory.append(dict(repository=str(repo.relative_to(root)),commit=rev,url=url,
            working_tree_clean=not bool(git(repo,'status','--porcelain')),file_extensions=dict(languages),
            python_files=sum(p.suffix=='.py' for p in files),license_files=licenses,
            license_status='root_text_preserved_not_a_file_level_rights_determination' if licenses else 'unresolved'))
        for path in sorted(p for p in files if p.suffix=='.py'):
            rel=str(path.relative_to(repo)); full_rel=str(path.relative_to(root))
            # Python generators/build scripts in native-library repos are not crypto implementations.
            relevant=('/charm/schemes/' in str(path) or '/charm/toolbox/' in str(path) or '/mcl/ffi/python/' in str(path))
            if not relevant or any(x in path.parts for x in ('test','tests','benchmark','benchmarks')) or path.name.endswith('_test.py'):
                rejected.append(dict(path=full_rel,reason='outside_selected_Python_implementation_scope')); continue
            try:
                with tokenize.open(path) as handle: source=handle.read()
                tree=ast.parse(source)
            except (SyntaxError,UnicodeError,ValueError) as error:
                rejected.append(dict(path=full_rel,reason='parse_or_encoding_failure',error_type=type(error).__name__)); continue
            if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',source):
                rejected.append(dict(path=full_rel,reason='potential_embedded_private_key_quarantined')); continue
            doc=ast.get_docstring(tree) or ''
            heading=next((s.strip('* ') for s in doc.splitlines() if s.strip()),None)
            title=re.search(r'\*\*Title:\*\*\s*(.*)',doc)
            declared=heading if heading and len(heading)<180 else None
            family_hint=title.group(1).strip(' "') if title else str(path.with_suffix('').relative_to(root)).removesuffix('_z')
            family='family-'+digest(family_hint.casefold().encode())[:16]
            split_number=int(digest(family.encode())[:8],16)%10
            split='test' if split_number==0 else 'validation' if split_number==1 else 'train'
            scheme_index.append(dict(path=full_rel,declared_scheme=declared,paper_title=title.group(1) if title else None,
                                     identification_status='metadata_hint_requires_review'))
            imports=[ast.get_source_segment(source,n) for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
            lines=source.splitlines(keepends=True)
            nodes=[]
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    if isinstance(node,ast.ClassDef) and node.end_lineno-node.lineno>160:
                        nodes.extend((n,node.name+'.'+n.name,'method_without_complete_class') for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)))
                    else: nodes.append((node,node.name,'class_excerpt' if isinstance(node,ast.ClassDef) else 'function_excerpt'))
            for node,name,context in nodes:
                start=min([node.lineno]+[d.lineno for d in node.decorator_list]); end=node.end_lineno
                code=''.join(lines[start-1:end])
                if len(code)<100 or end-start<3 or len(code)>18000:
                    rejected.append(dict(path=full_rel,symbol=name,reason='too_small_or_large_for_initial_review')); continue
                # Deduplicate AST-equivalent source, ignoring locations, comments and docstrings.
                import copy
                normalized=ast.dump(WithoutDocs().visit(copy.deepcopy(node)),include_attributes=False)
                canonical=digest(normalized.encode()); ident='py-'+digest((full_rel+':'+name).encode())[:20]
                if canonical in seen:
                    duplicates.append(dict(id=ident,path=full_rel,symbol=name,duplicate_of=seen[canonical],kind='AST_equal_ignoring_comments_docstrings')); continue
                seen[canonical]=ident
                candidates.append(dict(id=ident,code=code,language='python',task='cryptographic_security_analysis',
                    label=None,review_status='unreviewed_not_training_eligible',training_eligible=False,
                    scheme_hints=[declared] if declared else [],scheme_hint_basis='untrusted_module_documentation',
                    findings=[],source=dict(repository=url,commit=rev,repository_relative_path=rel,local_path=str(path),
                        symbol=name,line_start=start,line_end=end,file_sha256=digest(path.read_bytes()),code_sha256=digest(code.encode()),
                        licenses=licenses),context=dict(kind=context,imports=imports,missing=['caller assumptions','dependency implementations','deployment threat model']),
                    family=family,proposed_split=split,AST_sha256=canonical))
    dump(out/'candidates.jsonl',candidates); dump(out/'excluded.jsonl',rejected); dump(out/'duplicates.jsonl',duplicates)
    (out/'repositories.json').write_text(json.dumps(inventory,indent=2)+'\n')
    (out/'scheme_hints.json').write_text(json.dumps(scheme_index,indent=2)+'\n')
    summary=dict(repositories=len(repos),python_files=sum(r['python_files'] for r in inventory),candidates=len(candidates),
                 reviewed_training_entries=0,excluded=len(rejected),AST_duplicates=len(duplicates),
                 proposed_splits=dict(collections.Counter(r['proposed_split'] for r in candidates)),
                 training_ready=False,source_files_modified=False,source_code_executed=False,
                 warnings=['These are review candidates, not labeled training examples.',
                           'File/paper grouping is provisional; semantic-family leakage needs review before release.',
                           'Most native-code libraries contain only Python support scripts; native code is not relabeled Python.',
                           'License texts are preserved; upstream repositories are not blanket endorsements or security labels.'])
    (out/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
