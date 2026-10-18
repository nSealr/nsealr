"""Actual Git intake must exclude unselected histories and even dangling objects."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from admission import Recorder
from assemble import audit, git_environment, intake, read_git
from rehearse import PreflightError


class RestrictedIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.run_git('init', '--initial-branch=main', str(self.source))
        (self.source / 'public.txt').write_text('selected public source\n')
        self.run_git('-C', str(self.source), 'add', '.')
        self.run_git('-C', str(self.source), 'commit', '-m', 'public')
        self.public = read_git(self.source, 'rev-parse', 'HEAD').decode().strip()
        self.run_git('-C', str(self.source), 'switch', '-c', 'unselected-private')
        (self.source / 'private.txt').write_text('purpose-written synthetic private content\n')
        self.run_git('-C', str(self.source), 'add', '.')
        self.run_git('-C', str(self.source), 'commit', '-m', 'private')
        self.private = read_git(self.source, 'rev-parse', 'HEAD').decode().strip()
        self.private_blob = read_git(self.source, 'rev-parse', 'HEAD:private.txt').decode().strip()
        self.recorder = Recorder(self.root / 'execution')
        self.target = self.recorder.root / 'repository'
        self.objects, self.commits = intake(self.source, self.public, self.target, self.recorder)

    def run_git(self, *args, data=None):
        return subprocess.check_output(['git', '-c', 'init.templateDir=', '-c', 'commit.gpgsign=false', *args],
                                       input=data, env=git_environment(), stderr=subprocess.DEVNULL)

    def check(self):
        return audit(self.target, self.objects, self.commits, [], self.public)

    def test_only_selected_public_objects_arrive(self):
        self.assertTrue(self.check()['all_objects_reachable_and_allowed'])
        all_objects = read_git(self.target, 'cat-file', '--batch-all-objects', '--batch-check=%(objectname)').decode().splitlines()
        self.assertNotIn(self.private, all_objects)
        self.assertNotIn(self.private_blob, all_objects)
        self.assertFalse((self.target / 'private.txt').exists())
        self.assertEqual(read_git(self.target, 'remote'), b'')

    def test_unreachable_private_object_is_rejected_without_any_ref(self):
        self.run_git('-C', str(self.target), 'hash-object', '-w', '--stdin', data=b'purpose-written unselected private blob\n')
        with self.assertRaisesRegex(PreflightError, 'unselected/unreachable'):
            self.check()

    def test_unselected_branch_is_rejected(self):
        self.run_git('-C', str(self.target), 'fetch', '--no-tags', str(self.source), self.private+':refs/heads/unselected')
        with self.assertRaisesRegex(PreflightError, 'unselected target refs'):
            self.check()

    def test_existing_destination_is_rejected(self):
        with self.assertRaisesRegex(PreflightError, 'absent'):
            intake(self.source, self.public, self.target, self.recorder)

    def test_push_configuration_is_rejected(self):
        self.run_git('-C', str(self.target), 'config', 'remote.bad.pushurl', 'https://example.invalid/synthetic')
        with self.assertRaisesRegex(PreflightError, 'config'):
            self.check()

    def test_object_hardlink_is_rejected(self):
        obj = next(p for p in (self.target / '.git/objects').rglob('*') if p.is_file())
        os.link(obj, self.root / 'shared-object')
        with self.assertRaisesRegex(PreflightError, 'linked'):
            self.check()


if __name__ == '__main__':
    unittest.main()
