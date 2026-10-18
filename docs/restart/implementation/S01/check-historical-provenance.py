#!/usr/bin/env python3
"""Verify the new provenance patch independently of the v1 consumer overlay."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tools/baseline'))
from bootstrap import Recorder, apply_lab_overlay, fetch, write_json

work = HERE/'.work/historical-control'
work.mkdir(parents=True, exist_ok=False)
recorder = Recorder(HERE/'followup-evidence/historical-commands', dict(os.environ))
lab_commit = '3303ab17a28ed32419576627d5abb93db3999635'
specs_commit = '8bb8cca71355bcf8d81a093bcee9f3fe6915b121'
core_commit = '9194e292aa8a3176874cc9bf5814cefc26b6fe1a'
fetch(recorder, 'lab', '/home/tux/nsealr/lab', lab_commit, work)
fetch(recorder, 'specs', '/home/tux/nsealr/specs', specs_commit, work)
(work/'evidence').mkdir()
for manifest, label in ((ROOT/'tools/baseline/overlays/lab-provenance.json', 'overlay'),
                        (ROOT/'tools/baseline/overlays/lab-provenance-followup.json', 'provenance-followup-overlay')):
    apply_lab_overlay(recorder, work, lab_commit, manifest, label)
firmware = work/'firmware'
firmware.mkdir()
archive = subprocess.check_output(['git', 'archive', core_commit, 'tests/fixtures/specs'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
    stream.extractall(firmware, filter='data')
spec = importlib.util.spec_from_file_location('historical_checker', work/'lab/scripts/check_fixture_snapshots.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
snapshot = firmware/'tests/fixtures/specs'
metadata_path = snapshot/'SOURCE.json'
original_metadata = metadata_path.read_bytes()
cases = []


def check(name, reject=False):
    try:
        detail = checker.compare_fixture_snapshots(org=work, repositories=('firmware',))
        rejected = False
    except checker.FixtureSnapshotError as exc:
        detail = str(exc)
        rejected = True
    cases.append({'case': name, 'expected_reject': reject, 'observed_reject': rejected,
                  'pass': rejected == reject, 'detail': detail})


check('historical_complete_snapshot')
metadata_path.unlink()
check('historical_missing_manifest', True)
vector = snapshot/'vectors/nip46-relay-steps/sign-event-response-step.json'
original_vector = vector.read_bytes()
vector.unlink()
check('historical_missing_manifest_and_vector', True)
vector.write_bytes(original_vector)
metadata_path.write_bytes(original_metadata)
metadata = json.loads(original_metadata)
hidden = next(key for key in metadata['files'] if Path(key).name == '.gitkeep')
path = snapshot/hidden
original_hidden = path.read_bytes()
path.write_bytes(b'forged historical dotfile\n')
metadata['files'][hidden] = hashlib.sha256(path.read_bytes()).hexdigest()
metadata_path.write_text(json.dumps(metadata))
check('historical_forged_dotfile_digest', True)
path.write_bytes(original_hidden)
metadata_path.write_bytes(original_metadata)
check('historical_restored')
current_manifest = ROOT/'tests/fixtures/specs/SOURCE.json'
metadata_path.write_bytes(current_manifest.read_bytes())
check('current_manifest_with_old_specs_rejects', True)
metadata_path.write_bytes(original_metadata)
v1_manifest = json.loads((HERE/'lab-metadata-v1.json').read_text())
v1_not_applied = all(hashlib.sha256((work/'lab'/name).read_bytes()).hexdigest() == hashes['before_sha256']
                     for name, hashes in v1_manifest['files'].items())
result = {'lab': lab_commit, 'specs': specs_commit, 'core': core_commit,
          'v1_overlay_not_applied': v1_not_applied, 'cases': cases,
          'pass': v1_not_applied and all(case['pass'] for case in cases)}
write_json(HERE/'followup-evidence/historical-result.json', result)
print(json.dumps(result, indent=2))
raise SystemExit(not result['pass'])
