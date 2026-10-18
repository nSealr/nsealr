#!/usr/bin/env python3
"""Declare and commit explicit local A02 transformations; retain replayable patches."""
from __future__ import annotations
import argparse
from pathlib import Path
import os
import subprocess

from admission import Recorder
from assemble import git_environment, read_git, tree
from rehearse import canonical, decode_json, digest, safe_path, write_private


class Changes:
    def __init__(self, target: Path):
        self.target = target
        if read_git(target, 'status', '--porcelain'):
            raise ValueError('transformation must start from a clean target')
        self.before = read_git(target, 'rev-parse', 'HEAD').decode().strip()
        self.original = tree(target, self.before)
        self.updates = {}

    def put(self, path: str, data: bytes, mode: str | None = None):
        path = safe_path(path)
        if mode is None:
            mode = self.original.get(path, {}).get('mode', '100644')
        self.updates[path] = (data, mode)

    def remove(self, path: str):
        if path not in self.original:
            raise ValueError('cannot remove missing source')
        self.updates[safe_path(path)] = (None, None)

    def apply(self, output: Path, label: str):
        recorder = Recorder(output)
        records = []
        for path, (data, mode) in sorted(self.updates.items()):
            before = self.target / path
            old = before.read_bytes() if path in self.original else None
            if old == data and self.original.get(path, {}).get('mode') == mode:
                continue
            records.append(dict(path=path, before_sha256=digest(old) if old is not None else None,
                                before_mode=self.original.get(path, {}).get('mode'),
                                after_sha256=digest(data) if data is not None else None, after_mode=mode))
        declaration = dict(source_commit=self.before, stage=label, changes=records,
                           claim='Exact declared paths/preimages/postimages; acceptance is recorded separately.')
        # Write and verify the declaration before touching any target path.
        write_private(output/'declaration.json', canonical(declaration))
        for row in records:
            path = self.target / row['path']
            if row['before_sha256'] is not None and digest(path.read_bytes()) != row['before_sha256']:
                raise ValueError('preimage changed before transformation')
            data, mode = self.updates[row['path']]
            if data is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data); path.chmod(0o755 if mode=='100755' else 0o644)
        recorder.run('stage-declared-paths', ['git','-C',str(self.target),'add','--',*[r['path'] for r in records]], output, env=git_environment())
        patch = read_git(self.target, 'diff', '--cached', '--binary', '--full-index', '--find-renames')
        write_private(output/'change.patch', patch)
        recorder.run('commit-declared-transformation', ['git','-C',str(self.target),'-c','commit.gpgsign=false','commit','-m',label],output,env=git_environment())
        after = read_git(self.target, 'rev-parse','HEAD').decode().strip()
        write_private(output/'result.json',canonical(dict(**declaration,target_commit=after,target_tree=read_git(self.target,'rev-parse','HEAD^{tree}').decode().strip(),patch_sha256=digest(patch))))
        return after


def relocate_links(text: str, old: str, new: str, relocations: dict) -> str:
    import posixpath,re
    from urllib.parse import urlsplit
    def replace(match):
        raw=match[2]; parsed=urlsplit(raw)
        if parsed.scheme or parsed.netloc or not parsed.path:return match[0]
        resolved=posixpath.normpath(posixpath.join(posixpath.dirname(old),parsed.path))
        destination=relocations.get(resolved,resolved)
        relative=posixpath.relpath(destination,posixpath.dirname(new))
        if parsed.fragment:relative+='#'+parsed.fragment
        return match[1]+relative+match[3]
    return re.sub(r'(\[[^\]\n]*\]\()([^\s)]+)(\))',replace,text)


def plan_stage(target: Path, author_repo: Path, output: Path):
    change=Changes(target)
    package='732f742422cb26e7f215613f56a6c90acc6f73dc'
    prefix='docs/restart/implementation/A02/'
    closure=decode_json(read_git(author_repo,'show',package+':'+prefix+'admission-evidence/closed-evidence.json'))
    frozen={r['path'] for r in closure['artifacts']}
    contract_sources={
      'docs/restart/product-contract.md':'docs/product/contract.md',
      'docs/restart/client-qualification.md':'docs/product/client-qualification.md',
      **{'docs/restart/implementation/P01/'+name+'.md':'docs/product/'+name+'.md' for name in ['requirements','event-review-contract','threat-models']}}
    relocations={**contract_sources,'docs/restart/work-items.json':'plan/work-items.json'}
    change.put('plan/work-items.json',(target/'docs/restart/work-items.json').read_bytes());change.remove('docs/restart/work-items.json')
    validator=(target/'scripts/validate_restart_plan.py').read_text().replace('ROOT / "docs/restart/work-items.json"','ROOT / "plan/work-items.json"')
    change.put('scripts/validate_restart_plan.py',validator.encode())
    contract_rows=[]
    for old,new in contract_sources.items():
        before=(target/old).read_bytes();after=relocate_links(before.decode(),old,new,relocations).encode();change.put(new,after)
        contract_rows.append(dict(source_path=old,current_path=new,source_sha256=digest(before),initial_relocated_sha256=digest(after),equivalent_under_link_relocation=True,
                                 meaning='Current editable normative path. Original P01 review covers frozen source requirements; link relocation introduces no new product acceptance.'))
    navigation=['AGENTS.md','README.md']+[str(p.relative_to(target)) for p in sorted((target/'docs/restart').glob('*.md')) if str(p.relative_to(target)) not in frozen]
    navigation+=['docs/restart/implementation/README.md','docs/restart/implementation/handoff.md']
    for path in navigation:
        if path in frozen:raise ValueError('frozen evidence cannot become editable navigation')
        text=(target/path).read_text()
        if path in ['docs/restart/implementation/README.md','docs/restart/implementation/handoff.md']:
            text=read_git(author_repo,'show',package+':'+path).decode()
        text=relocate_links(text,path,path,relocations)
        text=text.replace('`docs/restart/work-items.json`','`plan/work-items.json`').replace('`work-items.json`','`plan/work-items.json`')
        text=text.replace('is the foundation graph until A02 moves it atomically to `plan/`','is the canonical foundation graph')
        change.put(path,text.encode())
    current_readme='''# Current product requirements

These are the current normative document paths: [contract](contract.md),
[requirements](requirements.md), [event review](event-review-contract.md),
[threat models](threat-models.md) and [client qualification](client-qualification.md).
The [single task graph](../../plan/work-items.json) records acceptance and integration.

The initial content derives from reviewed P01 source. The [evidence index](../../plan/evidence-index.json)
binds exact original bytes and the declared link relocation. Original reviewed P01
files under `docs/restart/implementation/P01/` and the two old restart index documents
are immutable historical evidence. They are not a second current contract owner.
Future substantive edits require ordinary task review; the original P01 review
must never be presented as reviewing changed current requirements.
'''
    change.put('docs/product/README.md',current_readme.encode());navigation+=list(contract_sources.values())+['docs/product/README.md']
    closure.update(graph_path='plan/work-items.json',current_contracts=contract_rows,current_navigation=navigation,relocations=relocations,
                   purpose='Derived source/evidence equivalence and navigation only; plan/work-items.json is the only task-state authority.')
    change.put('plan/evidence-index.json',canonical(closure))
    for filename in ['verify_evidence.py','test_evidence.py']:
        change.put('scripts/'+filename,(author_repo/'tools/migration/templates/scripts'/filename).read_bytes())
    make=(target/'Makefile').read_text().replace('python3 scripts/validate_restart_plan.py\n','python3 scripts/validate_restart_plan.py\n\tpython3 scripts/verify_evidence.py\n\tpython3 -m unittest discover -s scripts -p \'test_evidence.py\'\n')
    change.put('Makefile',make.encode())
    for path in change.updates:
        if path in frozen:raise ValueError('declared transformation touches frozen evidence')
    return change.apply(output,'Move single task authority and separate current contracts from frozen evidence')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['plan']);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(plan_stage(a.target,a.author_repo,a.output))
