"""Actual Git-bound negative/positive controls for the single contract artifact."""
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import verify_contracts as verifier


class ArtifactProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name);self.artifact=self.repo/'protocols/contracts/v1'
        self.files={'vectors/check.json':b'{"independent":true}\n','vectors/hidden/.gitkeep':b'',
                    'protocols/format.md':b'Explicit versioned contract\n','schemas/check.json':b'{}\n','examples/request.json':b'{}\n'}
        for path,data in self.files.items():
            p=self.artifact/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        self.git('init','-q');self.git('add','.');self.commit('Original selected bytes')
        self.original=self.git('rev-parse','HEAD').decode().strip()
        self.manifest={'artifact_format':1,'artifact_id':'nsealr-contracts-v1','source_commit':verifier.ORIGIN,
                       'initial_import_commit':self.original,'files':[{'path':p,'sha256':verifier.sha(d),'original_sha256':verifier.sha(d)} for p,d in self.files.items()]}
        self.write_manifest()
        self.valid_manifest=json.loads(json.dumps(self.manifest))
        self.git('add','.');self.commit('Explicit migration postimage')
        self.baseline=self.git('rev-parse','HEAD').decode().strip()
        consumers=json.dumps({name:['vectors/*.json'] for name in ['bridge','engine','pi']}).encode()
        (self.artifact/'consumers.json').write_bytes(consumers)
        for name,value in [('INITIAL_IMPORT',self.original),('BASELINE',self.baseline),('CONSUMERS_SHA256',verifier.sha(consumers))]:
            p=patch.object(verifier,name,value);p.start();self.addCleanup(p.stop)

    def git(self,*args):return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.STDOUT)
    def commit(self,message):self.git('-c','user.name=Artifact test','-c','user.email=test@example.invalid','commit','-qm',message)
    def write_manifest(self): (self.artifact/'manifest.json').write_text(json.dumps(self.manifest))
    def check(self):return verifier.validate(self.artifact,self.repo)
    def reject(self):
        with self.assertRaises((ValueError,subprocess.CalledProcessError)):self.check()
    def forge(self,path):
        rows=self.manifest['files'];self.manifest['files']=[r for r in rows if r['path']!=path]
        p=self.artifact/path
        if p.exists():self.manifest['files'].append({'path':path,'sha256':verifier.sha(p.read_bytes()),'original_sha256':verifier.sha(p.read_bytes())})
        self.write_manifest()
    def restore_manifest(self):
        self.manifest=json.loads(json.dumps(self.valid_manifest));self.write_manifest()
        self.assertEqual(self.check()['files'],5)

    def test_complete_artifact_counts_hidden_file(self):self.assertEqual(self.check()['files'],5)
    def test_missing_manifest_rejects_before_iteration(self):
        (self.artifact/'manifest.json').unlink();self.reject()
    def test_missing_manifest_and_versioned_vector_rejects(self):
        (self.artifact/'manifest.json').unlink();(self.artifact/'vectors/check.json').unlink();self.reject()
    def test_missing_normal_and_hidden_files_reject_even_with_forged_inventory(self):
        for path in ['vectors/check.json','vectors/hidden/.gitkeep']:
            with self.subTest(path=path):
                (self.artifact/path).unlink();self.reject();self.forge(path);self.reject()
                (self.artifact/path).write_bytes(self.files[path]);self.restore_manifest()
    def test_extra_normal_and_hidden_files_reject_even_with_forged_inventory(self):
        for path in ['vectors/extra.json','vectors/.extra']:
            with self.subTest(path=path):
                (self.artifact/path).write_bytes(b'{}');self.reject();self.forge(path);self.reject()
                (self.artifact/path).unlink();self.restore_manifest()
    def test_tampered_normal_and_hidden_files_reject_forged_digests(self):
        for path in ['vectors/check.json','vectors/hidden/.gitkeep']:
            with self.subTest(path=path):
                (self.artifact/path).write_bytes(b'forged');self.reject();self.forge(path);self.reject()
                (self.artifact/path).write_bytes(self.files[path]);self.restore_manifest()
    def test_new_git_commit_and_forged_manifest_cannot_replace_frozen_source(self):
        (self.artifact/'vectors/check.json').write_bytes(b'forged');self.forge('vectors/check.json')
        self.git('add','.');self.commit('Unreviewed rewrite');self.reject()
    def test_wrong_source_pin_or_inventory_rejects(self):
        valid=dict(self.manifest)
        for key,value in [('source_commit','0'*40),('initial_import_commit','0'*40),('files',[])]:
            with self.subTest(key=key):self.manifest={**valid,key:value};self.write_manifest();self.reject()
    def test_malformed_or_nonobject_manifest_rejects(self):
        for value in ['{','[]','null']:
            with self.subTest(value=value):(self.artifact/'manifest.json').write_text(value);self.reject()
    def test_missing_directory_rejects(self):
        (self.artifact/'examples/request.json').unlink();(self.artifact/'examples').rmdir();self.reject()
    def test_symlinked_data_manifest_and_root_reject(self):
        for relative in ['vectors/hidden/.gitkeep','manifest.json']:
            p=self.artifact/relative;data=p.read_bytes();p.unlink();p.symlink_to(self.artifact/'vectors/check.json')
            with self.subTest(path=relative):self.reject()
            p.unlink();p.write_bytes(data)
        alias=self.repo/'alias';alias.symlink_to(self.artifact,target_is_directory=True)
        with self.assertRaises(ValueError):verifier.validate(alias,self.repo)
    def test_symlinked_directory_rejects(self):
        p=self.artifact/'examples';p.rename(self.artifact/'old-examples');p.symlink_to(self.artifact/'old-examples',target_is_directory=True);self.reject()
    def test_committed_nonregular_file_rejects(self):
        p=self.artifact/'vectors/hidden/.gitkeep';p.unlink();p.symlink_to('../check.json')
        self.git('add','.');self.commit('Unsupported link');new=self.git('rev-parse','HEAD').decode().strip()
        p.unlink();p.write_bytes(b'')
        with patch.object(verifier,'BASELINE',new):
            with self.assertRaisesRegex(ValueError,'nonregular committed'):self.check()
    def test_duplicate_path_manifest_rejects(self):
        self.manifest['files'].append(self.manifest['files'][0]);self.write_manifest();self.reject()
    def test_wrong_original_hash_rejects(self):
        self.manifest['files'][0]['original_sha256']='0'*64;self.write_manifest();self.reject()
    def test_missing_partial_consumer_scope_rejects(self):
        (self.artifact/'consumers.json').unlink();self.reject()
    def test_reduced_consumer_scope_rejects(self):
        (self.artifact/'consumers.json').write_text('{"bridge":[],"engine":[],"pi":[]}');self.reject()
    def test_unmatched_declared_consumer_pattern_rejects(self):
        data=json.dumps({name:['vectors/missing/*.json'] for name in ['bridge','engine','pi']}).encode()
        (self.artifact/'consumers.json').write_bytes(data)
        with patch.object(verifier,'CONSUMERS_SHA256',verifier.sha(data)):self.reject()
    def test_stale_snapshot_is_rejected(self):
        p=self.repo/'tests/fixtures/specs';p.mkdir(parents=True);self.reject()
    def test_fully_valid_control_after_mutation_is_restored(self):
        p=self.artifact/'vectors/check.json';p.write_bytes(b'forged');self.reject();p.write_bytes(self.files['vectors/check.json'])
        self.assertEqual(self.check()['consumers'],['bridge','engine','pi'])


if __name__=='__main__':unittest.main()
