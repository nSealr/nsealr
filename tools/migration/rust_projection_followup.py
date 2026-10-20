#!/usr/bin/env python3
"""Complete the data-only style mapping and format declared Rust source."""
import argparse,subprocess
from pathlib import Path
from transforms import Changes

def apply(target,author,output):
    c=Changes(target)
    c.put('ci/project_core_fixtures.py',(author/'tools/migration/templates/ci/project_core_fixtures.py').read_bytes())
    for root in ['crates/nsealr-core','apps/desktop-simulator']:
        for path in sorted((target/root).rglob('*.rs')):
            if 'target' in path.relative_to(target).parts:continue
            before=path.read_bytes()
            after=subprocess.run(['rustfmt','--edition','2021','--emit','stdout'],input=before,capture_output=True,check=True).stdout
            if before!=after:c.put(path.relative_to(target).as_posix(),after)
    return c.apply(output,'Complete projected review styles and format migrated Rust source')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.author_repo,a.output))
