#!/usr/bin/env python3
"""Repeat the preserved independent mutation probe with the third overlay.

The original probe bytes and mutation functions remain unchanged. This wrapper
adds the follow-up immediately after the original two overlays and chooses an
owned output directory. No network, package installation or fixture edits escape
the disposable probe directory.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
original = HERE/'followup-evidence/reviewer-probe.py'
assert hashlib.sha256(original.read_bytes()).hexdigest() == '39bce90e92a473930768d7b92aa76b70c8163ad495ea8fbdd1e9976e65ab4caf'
spec = importlib.util.spec_from_file_location('original_review_probe', original)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
probe.HERE = HERE/'followup-evidence'
probe.ROOT = ROOT
probe.WORK = HERE/'.work/corrected-review-probe'
probe.CANDIDATE = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
probe.PINS['firmware'] = probe.CANDIDATE
run_original = probe.run
followup = ROOT/'tools/baseline/overlays/lab-provenance-followup.patch'


def run(argv, cwd):
    result = run_original(argv, cwd)
    if argv[:2] == ['git', 'apply'] and argv[-1].endswith('/lab-metadata-v1.patch') and '--check' not in argv:
        run_original(['git', 'apply', '--check', str(followup)], cwd)
        run_original(['git', 'apply', str(followup)], cwd)
    return result


probe.run = run
status = probe.main()
result_path = probe.HERE/'probe-result.json'
result = json.loads(result_path.read_text())
result['additional_overlay_sha256'] = hashlib.sha256(followup.read_bytes()).hexdigest()
result['original_probe_sha256'] = hashlib.sha256(original.read_bytes()).hexdigest()
(probe.HERE/'green-probe-result.json').write_text(json.dumps(result, indent=2)+'\n')
result_path.unlink()
raise SystemExit(status)
