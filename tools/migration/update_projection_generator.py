#!/usr/bin/env python3
"""Apply the concrete lint-safe test-data projection generator postimage."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 c=Changes(a.target);c.put('ci/project_core_fixtures.py',(a.author_repo/'tools/migration/templates/ci/project_core_fixtures.py').read_bytes());print(c.apply(a.output,'Emit projected grants directly without generated single-element loops'))
