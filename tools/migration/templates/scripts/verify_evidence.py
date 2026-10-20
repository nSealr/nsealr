#!/usr/bin/env python3
"""Check frozen source equivalence and current navigation; the graph owns task policy."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]
SOURCE='f2ef70f522af4977e15f81554a8c6eadcdbe8097'
CONTRACTS={'docs/restart/product-contract.md':'docs/product/contract.md',
           'docs/restart/client-qualification.md':'docs/product/client-qualification.md',
           **{'docs/restart/implementation/P01/'+n+'.md':'docs/product/'+n+'.md' for n in ('requirements','event-review-contract','threat-models')}}
RELOCATIONS={**CONTRACTS,'docs/restart/work-items.json':'plan/work-items.json'}


def sha(data):return hashlib.sha256(data).hexdigest()


def path_at(root,path):
    if not isinstance(path,str) or not path or path.startswith('/') or any(p in {'.','..','.git',''} for p in path.split('/')) or '\\' in path:
        raise ValueError('unsafe evidence/current path')
    result=root/path
    if result.resolve()!=result.absolute() or not result.is_file():raise ValueError('missing/nonregular/aliased evidence or current path: '+path)
    return result


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL)


def objects(root,commit):
    rows={}
    for row in git(root,'ls-tree','-rz','--full-tree',commit).split(b'\0'):
        if row:
            meta,name=row.split(b'\t',1);mode,kind,blob=meta.decode().split();rows[name.decode()]={'mode':mode,'kind':kind,'blob':blob}
    return rows


def relocated(text,old,new):
    def replace(m):
        raw=m[2];parsed=urlsplit(raw)
        if parsed.scheme or parsed.netloc or not parsed.path:return m[0]
        resolved=posixpath.normpath(posixpath.join(posixpath.dirname(old),parsed.path))
        relative=posixpath.relpath(RELOCATIONS.get(resolved,resolved),posixpath.dirname(new))
        if parsed.fragment:relative+='#'+parsed.fragment
        return m[1]+relative+m[3]
    return re.sub(r'(\[[^\]\n]*\]\()([^\s)]+)(\))',replace,text)


def validate(root=ROOT,expected_source=SOURCE):
    root=root.resolve();index=json.loads(path_at(root,'plan/evidence-index.json').read_bytes());plan=json.loads(path_at(root,'plan/work-items.json').read_bytes())
    if (root/'docs/restart/work-items.json').exists():raise ValueError('second live task graph')
    if index['source_identity']['commit']!=expected_source or index['source_commit']!=expected_source:raise ValueError('wrong historical source commit')
    if index['relocations']!=RELOCATIONS:raise ValueError('unreviewed relocation aliases')
    original=objects(root,expected_source);current=objects(root,'HEAD')
    if git(root,'rev-parse',expected_source+'^{tree}').decode().strip()!=index['source_identity']['tree']:raise ValueError('historical tree mismatch')
    original_plan=json.loads(git(root,'show',expected_source+':docs/restart/work-items.json'))
    historical_bound={row['path']:row['sha256'] for task in original_plan['tasks'] if task.get('status') in {'verified','integrated'} for row in task['result_artifacts']}
    bound={}
    for task in plan['tasks']:
        if task.get('status') in {'verified','integrated'}:
            for row in task['result_artifacts']:
                if row['path'] in bound and bound[row['path']]!=row['sha256']:raise ValueError('contradictory graph evidence')
                bound[row['path']]=row['sha256']
    if any(bound.get(path)!=value for path,value in historical_bound.items()):raise ValueError('historical graph evidence changed')
    artifacts=index['artifacts'];names=[r['path'] for r in artifacts]
    if len(names)!=len(set(names)) or set(names)!=set(historical_bound):raise ValueError('missing/duplicate closed evidence closure entry')
    # Later closed tasks remain governed by the full canonical validator. This
    # migration index preserves its original closure; it is not a second ledger.
    batch=subprocess.Popen(['git','-C',str(root),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    cache={}
    def blob(oid):
        if oid not in cache:
            batch.stdin.write((oid+'\n').encode());batch.stdin.flush();header=batch.stdout.readline().decode().split()
            if len(header)!=3 or header[:2]!=[oid,'blob']:raise ValueError('missing historical blob')
            cache[oid]=batch.stdout.read(int(header[2]));assert batch.stdout.read(1)==b'\n'
        return cache[oid]
    try:
        for row in artifacts:
            path=row['path'];physical=path_at(root,path)
            if row['current_unchanged_path']!=path or row['original_commit']!=expected_source:raise ValueError('evidence alias/source mismatch')
            if row['mode'] not in {'100644','100755'} or original.get(path)!={k:row[k] for k in ('mode','kind','blob')}:raise ValueError('wrong historical blob/mode')
            if current.get(path)!=original[path] or sha(blob(row['blob']))!=bound[path] or row['sha256']!=bound[path] or sha(physical.read_bytes())!=bound[path]:raise ValueError('frozen evidence bytes changed')
        contracts=index['current_contracts']
        if len(contracts)!=len(CONTRACTS) or {r['source_path']:r['current_path'] for r in contracts}!=CONTRACTS:raise ValueError('duplicate/missing current contract owner')
        for row in contracts:
            old,new=row['source_path'],row['current_path'];source=blob(original[old]['blob']);data=path_at(root,new).read_bytes()
            if sha(source)!=row['source_sha256']:raise ValueError('contract source attribution mismatch')
            initial=relocated(source.decode(),old,new).encode()
            if sha(initial)!=row['initial_relocated_sha256']:raise ValueError('initial contract projection mismatch')
            if row['equivalent_under_link_relocation']:
                if data!=initial:raise ValueError('modified current contract falsely attributed to old review')
            elif bound.get(new)!=sha(data):
                raise ValueError('changed current contract needs its own closed graph evidence/review')
        navigation=index['current_navigation']
        if len(navigation)!=len(set(navigation)) or not set(CONTRACTS.values())<=set(navigation):raise ValueError('current navigation aliases or missing owner')
        for name in navigation:
            text=path_at(root,name).read_text();text=re.sub(r'(?ms)^```.*?^```[^\n]*','',text)
            for raw in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)',text):
                parsed=urlsplit(raw)
                if parsed.scheme or parsed.netloc or not parsed.path:continue
                resolved=(root/name).parent/unquote(parsed.path)
                if not resolved.resolve().is_relative_to(root) or not resolved.exists():raise ValueError('dangling/escaping current link: '+name)
                if resolved.resolve()==root/'docs/restart/work-items.json':raise ValueError('current link points at retired task graph')
        return {'closed_files':len(artifacts),'current_contracts':len(contracts),'current_navigation_files':len(navigation),'frozen_source':expected_source}
    finally:
        batch.stdin.close();batch.stdout.close();batch.wait()


if __name__=='__main__':
    try:print(json.dumps(validate(),sort_keys=True))
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as error:
        print('ERROR:',error);raise SystemExit(1)
