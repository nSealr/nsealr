#!/usr/bin/env python3
"""Execute the unchanged historical reproduction against corrected product.

Its former unexpected success is now expected to stop with ValueError at the
second validate after chmod0645. Only disposable public fixture Git changes.
"""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
RELATIVE = 'docs/restart/implementation/reviews/T01-provenance-component/reproduce-mode.py'
source = subprocess.check_output(['git', '--no-replace-objects', '-C', str(ROOT),
                                  'show', '910425654c6a6d65b348e4285a5d6d35ab049525:' + RELATIVE])
assert hashlib.sha256(source).hexdigest() == 'f04298e0e6d50aeea466876131ae556f560f72a2ad7903548ecfd3f31acab091'
# Preserve the original path depth used by that exact source to find ROOT.
filename = str(ROOT / RELATIVE)
exec(compile(source, filename, 'exec'), {'__name__': '__main__', '__file__': filename})
