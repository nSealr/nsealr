"""Command-boundary controls only; actual Cargo negative evidence is separate."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
spec = importlib.util.spec_from_file_location('audit_rust', ROOT / 'scripts/audit_rust.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditControls(unittest.TestCase):
    def exercise(self, codes, inherited=None):
        calls = []
        def run(argv, *, cwd, env):
            self.assertTrue(cwd.exists())
            calls.append((argv, cwd, env))
            return subprocess.CompletedProcess(argv, codes[len(calls) - 1])
        original = dict(os.environ)
        with patch.dict(os.environ, inherited or {}), patch.object(audit.subprocess, 'run', run), contextlib.redirect_stdout(io.StringIO()):
            result = audit.audit(ROOT)
        self.assertEqual(dict(os.environ), original)
        self.assertFalse(calls[0][1].exists(), 'temporary audit data cleaned after success or failure')
        return result, calls

    def test_success_runs_three_real_manifests_and_preserves_policy(self):
        result, calls = self.exercise([0] * 6)
        self.assertEqual(result, 0)
        self.assertEqual(len(calls), 6)
        for index, (argv, cwd, env) in enumerate(calls):
            self.assertEqual(argv[argv.index('--manifest-path') + 1], str(ROOT / audit.MANIFESTS[index % 3]))
            self.assertEqual(argv[argv.index('--config') + 1], str(ROOT / 'deny.toml'))
            self.assertIn('--locked', argv)
            self.assertEqual(env['RUSTUP_TOOLCHAIN'], '1.95.0')
            self.assertEqual(env['CARGO_REGISTRIES_CRATES_IO_PROTOCOL'], 'sparse')
            self.assertEqual(Path(env['CARGO_HOME']), calls[0][1] / 'cargo')
            if index < 3:
                self.assertFalse(cwd.is_relative_to(ROOT))
                self.assertEqual(argv[argv.index('fetch'):], ['fetch', 'index', 'db'] if index == 0 else ['fetch', 'index'])
            else:
                self.assertEqual(cwd, ROOT)
                self.assertIn('--offline', argv)
                self.assertEqual(argv[argv.index('check'):], ['check', '--deny', 'index-failure'])

    def test_each_data_or_check_failure_stops_dependents_and_propagates(self):
        for failure_at in range(6):
            with self.subTest(failure_at=failure_at):
                result, calls = self.exercise([0] * failure_at + [17])
                self.assertEqual(result, 17)
                self.assertEqual(len(calls), failure_at + 1)

    def test_existing_offline_request_is_not_bypassed(self):
        result, calls = self.exercise([1], {'CARGO_NET_OFFLINE': 'true'})
        self.assertEqual(result, 1)
        self.assertEqual(calls[0][2]['CARGO_NET_OFFLINE'], 'true')

    def test_each_invocation_has_a_distinct_cache(self):
        _, first = self.exercise([1])
        _, second = self.exercise([1])
        self.assertNotEqual(first[0][2]['CARGO_HOME'], second[0][2]['CARGO_HOME'])


if __name__ == '__main__':
    unittest.main()
