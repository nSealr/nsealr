"""Boundary tests for evidence isolation and failure preservation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bootstrap import Recorder, apply_lab_overlay, apply_lab_overlays, download, environment, sha256


class BootstrapTests(unittest.TestCase):
    def test_occupied_destination_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            marker = target/'keep'
            marker.write_text('unchanged')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('bootstrap.py')), str(target)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already exists', result.stderr)
            self.assertEqual(list(target.iterdir()), [marker])
            self.assertEqual(marker.read_text(), 'unchanged')

    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'source'
            source.write_bytes(b'untrusted replacement')
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                download({'url':source.as_uri(), 'sha256':'0'*64}, Path(tmp)/'output')

    def test_inherited_override_and_tool_paths_are_removed(self):
        with patch.dict(os.environ, {'PATH':'/bad/cache/bin', 'MAKEFLAGS':'PYTHON=/bad/python', 'NODE_OPTIONS':'--no-warnings', 'NSEALR_LIVE_E2E':'1', 'PIP_INDEX_URL':'https://invalid.example'}):
            result = environment(Path('/isolated'))
        for name in ('MAKEFLAGS', 'NODE_OPTIONS', 'NSEALR_LIVE_E2E', 'PIP_INDEX_URL'):
            self.assertNotIn(name, result)
        self.assertNotIn('/bad', result['PATH'])
        self.assertEqual(result['npm_config_store_dir'], '/isolated/.tools/cache/pnpm')
        self.assertEqual(result['PIP_NO_INDEX'], '1')
        self.assertEqual(result['HOME'], os.environ['HOME'])

    def test_failure_exit_and_both_output_streams_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recorder = Recorder(root/'evidence', dict(os.environ))
            code = recorder.run('negative', [sys.executable, '-c', 'import sys; print("out"); print("diagnostic", file=sys.stderr); sys.exit(7)'], root, required=False)
            self.assertEqual(code, 7)
            result = json.loads((root/'evidence/commands.json').read_text())[0]
            self.assertEqual(result['exit_code'], 7)
            output = (root/'evidence'/result['log']).read_text()
            self.assertIn('diagnostic', output)
            self.assertIn('out', output)


class OverlayBoundaryTests(unittest.TestCase):
    """Real Git patches verify ordering and rejection without private sources."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.lab = self.root/'lab'
        self.lab.mkdir()
        self.target = self.lab/'selected.txt'
        self.target.write_text('zero\n')
        self.git('init', '-q')
        self.git('add', 'selected.txt')
        self.git('-c', 'user.name=Overlay test', '-c', 'user.email=test@invalid.example',
                 'commit', '-qm', 'Independent patch preimage')
        self.commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.here = self.root/'tools/baseline'
        self.manifests = [self.here/'overlays/lab-provenance.json',
                          self.root/'docs/restart/implementation/S01/lab-metadata-v1.json',
                          self.here/'overlays/lab-provenance-followup.json']
        before = 'zero\n'
        for manifest, after in zip(self.manifests, ('one\n', 'two\n', 'three\n')):
            manifest.parent.mkdir(parents=True, exist_ok=True)
            patch_file = manifest.with_suffix('.patch')
            patch_file.write_text(f'diff --git a/selected.txt b/selected.txt\n'
                                  f'--- a/selected.txt\n+++ b/selected.txt\n@@ -1 +1 @@\n-{before}+{after}')
            import hashlib
            manifest.write_text(json.dumps({'commit': self.commit, 'patch_sha256': sha256(patch_file),
                'files': {'selected.txt': {'before_sha256': hashlib.sha256(before.encode()).hexdigest(),
                                           'after_sha256': hashlib.sha256(after.encode()).hexdigest()}}}))
            before = after
        self.recorder = Recorder(self.root/'evidence/commands', dict(os.environ))

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.lab, stderr=subprocess.STDOUT)

    def apply_one(self, commit=None):
        apply_lab_overlay(self.recorder, self.root, commit or self.commit, self.manifests[0], 'overlay')

    def apply_defaults(self):
        with patch('bootstrap.HERE', self.here), patch('bootstrap.SOURCE', self.root):
            apply_lab_overlays(self.recorder, self.root, self.commit)

    def test_default_applies_all_three_in_order_and_records_each(self):
        self.apply_defaults()
        self.assertEqual(self.target.read_text(), 'three\n')
        for name, manifest in zip(('overlay', 'metadata-v1-overlay', 'provenance-followup-overlay'), self.manifests):
            self.assertEqual(json.loads((self.root/f'evidence/{name}.json').read_text()),
                             json.loads(manifest.read_text()))

    def test_wrong_declared_commit_is_rejected_before_mutation(self):
        with self.assertRaisesRegex(ValueError, 'source/patch pin'):
            self.apply_one('0'*40)
        self.assertEqual(self.target.read_text(), 'zero\n')
        self.assertEqual(self.recorder.results, [])

    def test_wrong_actual_commit_is_rejected_before_mutation(self):
        self.git('-c', 'user.name=Overlay test', '-c', 'user.email=test@invalid.example',
                 'commit', '--allow-empty', '-qm', 'Different source')
        with self.assertRaisesRegex(ValueError, 'source/patch pin'):
            self.apply_one()
        self.assertEqual(self.target.read_text(), 'zero\n')

    def test_modified_patch_is_rejected_before_mutation(self):
        self.manifests[0].with_suffix('.patch').write_text('tampered\n')
        with self.assertRaisesRegex(ValueError, 'source/patch pin'):
            self.apply_one()
        self.assertEqual(self.target.read_text(), 'zero\n')

    def test_modified_preimage_is_rejected_before_patch(self):
        self.target.write_text('changed\n')
        with self.assertRaisesRegex(ValueError, 'preimage mismatch'):
            self.apply_one()
        self.assertEqual(self.target.read_text(), 'changed\n')
        self.assertEqual(self.recorder.results, [])

    def test_wrong_output_hash_is_rejected_and_not_recorded_as_pass(self):
        manifest = json.loads(self.manifests[0].read_text())
        manifest['files']['selected.txt']['after_sha256'] = '0'*64
        self.manifests[0].write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'output mismatch'):
            self.apply_one()
        self.assertFalse((self.root/'evidence/overlay.json').exists())

    def test_missing_followup_is_not_silently_skipped(self):
        self.manifests[2].unlink()
        with self.assertRaises(FileNotFoundError):
            self.apply_defaults()
        self.assertFalse((self.root/'evidence/provenance-followup-overlay.json').exists())


if __name__ == '__main__':
    unittest.main()
