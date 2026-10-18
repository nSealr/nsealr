"""Boundary tests for evidence isolation and failure preservation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bootstrap import Recorder, download, environment


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


if __name__ == '__main__':
    unittest.main()
