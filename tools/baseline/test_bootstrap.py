"""Boundary tests for evidence isolation and failure preservation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bootstrap import Recorder, download, environment, fetch, sha256


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


class ProductSourceTests(unittest.TestCase):
    def test_exact_selected_history_available_without_unselected_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(source),*args],stderr=subprocess.STDOUT).strip().decode()
            git('init','-q');(source/'public.txt').write_text('public source\n');git('add','public.txt');git('-c','user.name=Test','-c','user.email=test@invalid.example','commit','-qm','public');selected=git('rev-parse','HEAD')
            git('checkout','-qb','unselected');(source/'excluded.txt').write_text('synthetic excluded source\n');git('add','excluded.txt');git('-c','user.name=Test','-c','user.email=test@invalid.example','commit','-qm','unselected');excluded=git('rev-parse','HEAD')
            git('checkout','--detach',selected)
            rec=Recorder(root/'evidence',dict(os.environ));fetch(rec,'nsealr',str(source),selected,root)
            self.assertEqual(subprocess.check_output(['git','-C',str(root/'nsealr'),'rev-parse','HEAD'],text=True).strip(),selected)
            result=subprocess.run(['git','-C',str(root/'nsealr'),'cat-file','-e',excluded],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((root/'nsealr/excluded.txt').exists())

    def test_missing_selected_commit_preserves_fetch_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';subprocess.run(['git','init','-q',str(source)],check=True)
            recorder=Recorder(root/'evidence',dict(os.environ))
            with self.assertRaisesRegex(RuntimeError,'fetch exited'):
                fetch(recorder,'nsealr',str(source),'0'*40,root)
            self.assertNotEqual(recorder.results[-1]['exit_code'],0)
            self.assertEqual(recorder.results[-1]['label'],'nsealr-fetch')


class SuiteSourceCorrespondenceTests(unittest.TestCase):
    def exercise(self,mutate):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'nsealr';source.mkdir()
            (source/'tracked.txt').write_text('original')
            recipe='test:\n\t'+('echo changed >> tracked.txt' if mutate else 'true')+'\ncargo-test:\n\ttrue\n'
            (source/'Makefile').write_text(recipe)
            subprocess.run(['git','init','-q',str(source)],check=True)
            subprocess.run(['git','-C',str(source),'add','.'],check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Test','-c','user.email=test@invalid.example','commit','-qm','fixture'],check=True)
            commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
            for name,data in [('environment.json',dict(os.environ)),('source-commits.json',{'nsealr':commit}),('source-state.json',{'nsealr':{'status':'','diff_sha256':__import__('hashlib').sha256(b'').hexdigest()}})]:
                (root/name).write_text(json.dumps(data))
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),str(root),'--smoke'],capture_output=True,text=True)
            record=json.loads((root/'evidence/smoke/result.json').read_text())
            self.assertEqual(result.returncode,1 if mutate else 0)
            self.assertEqual(record['all_passed'],not mutate)
            self.assertEqual(record['source_changed_after'],['nsealr'] if mutate else [])
    def test_successful_command_that_changes_source_fails_acceptance(self):self.exercise(True)
    def test_successful_command_preserving_source_passes(self):self.exercise(False)


if __name__ == '__main__':
    unittest.main()
