#!/usr/bin/env python3
"""Declare only the maintainer's current operational model policy; keep task history."""
import argparse
import json
from pathlib import Path

from assemble import read_git
from rehearse import canonical
from transforms import Changes

POLICY_SOURCE = '7c9b9a9d6e1874c7a5b09cee1daaec48fc08085e'


def apply(target: Path, author: Path, output: Path) -> str:
    change = Changes(target)
    for path in ('AGENTS.md', 'docs/restart/execution.md'):
        source = read_git(author, 'show', POLICY_SOURCE + ':' + path).decode()
        current = (target / path).read_text()
        old_lines = current.splitlines()
        new_lines = source.splitlines()
        prefix = '- The maintainer\'s latest model policy' if path == 'AGENTS.md' else 'A Codex coordinator'
        replacement = next(line for line in new_lines if line.startswith(prefix))
        old = next(line for line in old_lines if ('requested specialist configuration' in line if path == 'AGENTS.md' else line.startswith(prefix)))
        change.put(path, current.replace(old, replacement, 1).encode())
    graph_path = 'plan/work-items.json'
    graph_bytes = (target / graph_path).read_bytes()
    graph = json.loads(graph_bytes)
    source = json.loads(read_git(author, 'show', POLICY_SOURCE + ':docs/restart/work-items.json'))
    if 'execution_model_policy' in graph:
        raise ValueError('model policy already present; reconcile explicitly')
    policy = source['execution_model_policy']
    policy['integration'] = ('Declared operational-policy-only A02 transformation under the latest maintainer authority. '
        'Source main f2 remains frozen; task records, historical O01 evidence and the unmerged pause task reconciliation are unchanged. '
        'Candidate policy awaits distinct review and normal adoption.')
    # Preserve every existing graph byte; append only one top-level policy field.
    ending = b'\n}\n'
    if not graph_bytes.endswith(ending):
        raise ValueError('unexpected graph formatting')
    addition = canonical({'execution_model_policy': policy}).removeprefix(b'{\n').removesuffix(ending)
    result = graph_bytes.removesuffix(ending) + b',\n' + addition + ending
    proposed = json.loads(result)
    if {k: v for k, v in proposed.items() if k != 'execution_model_policy'} != graph:
        raise ValueError('policy changes existing graph data')
    change.put(graph_path, result)
    return change.apply(output, 'Apply latest maintainer Sol xhigh operational policy preserving historical task evidence')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target', type=Path, required=True)
    p.add_argument('--author-repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(apply(a.target, a.author_repo, a.output))
