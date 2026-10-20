"""Actual Git-bound negative/positive controls for the single contract artifact."""
import hashlib
import os
import shutil
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
            dest=self.artifact/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        self.git('-c','init.templateDir=','init','-q','--initial-branch=main');self.git('add','.');self.commit('Original selected bytes')
        self.original=self.git('rev-parse','HEAD').decode().strip()
        header={'artifact_format':1,'artifact_id':'nsealr-contracts-v1','source_commit':verifier.ORIGIN,
                'initial_import_commit':self.original,'consumer_coverage':{k:'Explicit independent coverage' for k in ['python','rust','typescript']},
                'generation':'Fixed independent expectations','retirement':'Historical card retirement retained','wire_versions':'Artifact1 separate from wire2'}
        legacy={**header,'files':[{'path':path,'sha256':verifier.sha(data),'original_sha256':verifier.sha(data),'adaptation':None} for path,data in self.files.items()]}
        (self.artifact/'manifest.json').write_text(json.dumps(legacy))
        (self.artifact/'adaptation.json').write_bytes(b'{"historical_retirement":"cards"}\n')
        self.git('add','.');self.commit('Explicit migration postimage')
        self.baseline=self.git('rev-parse','HEAD').decode().strip()
        rows=[]
        for path,data in self.files.items():
            old={'mode':'100644','sha256':verifier.sha(data)}
            if path=='schemas/check.json':
                current=b'{"format2":true}\n';(self.artifact/path).write_bytes(current)
                disposition,adaptation,now='modified_t01','Declared T01 change',{'mode':'100644','sha256':verifier.sha(current)}
            elif path=='examples/request.json':
                (self.artifact/path).unlink();disposition,adaptation,now='retired_t01','Explicit replacement obligation',None
            else:disposition,adaptation,now='maintained',None,dict(old)
            rows.append({'path':path,'disposition':disposition,'original':dict(old),'baseline':dict(old),'current':now,'adaptation':adaptation})
        authored=b'{"authored":true}\n';(self.artifact/'examples/authored.json').write_bytes(authored)
        rows.append({'path':'examples/authored.json','disposition':'authored_t01','original':None,'baseline':None,
                     'current':{'mode':'100644','sha256':verifier.sha(authored)},'adaptation':'New independent T01 input'})
        self.manifest={**header,'artifact_format':2,'files':rows};self.write_manifest()
        self.valid_manifest=json.loads(json.dumps(self.manifest))
        consumers=json.dumps({name:['vectors/*.json'] for name in ['bridge','engine','pi']}).encode()
        (self.artifact/'consumers.json').write_bytes(consumers)
        (self.artifact/'LICENSE').write_bytes(b'Fixture-only license context\n')
        self.git('add','.');self.commit('Reviewed fixture artifact')
        self.candidate=self.git('rev-parse','HEAD').decode().strip()
        self.tree=self.git('rev-parse','HEAD:protocols/contracts/v1').decode().strip()
        for name,value in [('INITIAL_IMPORT',self.original),('SOURCE_POSTIMAGE',self.original),('BASELINE',self.baseline),('ARTIFACT_TREE_OID',self.tree)]:
            controlled=patch.object(verifier,name,value);controlled.start();self.addCleanup(controlled.stop)

    def trust_current_tree(self):
        # Tests alone deliberately pin real malformed fixture trees to exercise
        # schema/source semantics after byte binding. No production override.
        self.git('add','-A');self.commit('Explicit test-only fixture tree')
        oid=self.git('rev-parse','HEAD:protocols/contracts/v1').decode().strip()
        return patch.object(verifier,'ARTIFACT_TREE_OID',oid)

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
        (self.artifact/'examples/authored.json').unlink();(self.artifact/'examples').rmdir();self.reject()
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
        self.manifest['files'][0]['original']['sha256']='0'*64;self.write_manifest();self.reject()
    def test_missing_partial_consumer_scope_rejects(self):
        (self.artifact/'consumers.json').unlink();self.reject()
    def test_reduced_consumer_scope_rejects(self):
        (self.artifact/'consumers.json').write_text('{"bridge":[],"engine":[],"pi":[]}');self.reject()
    def test_unmatched_declared_consumer_pattern_rejects(self):
        data=json.dumps({name:['vectors/missing/*.json'] for name in ['bridge','engine','pi']}).encode()
        (self.artifact/'consumers.json').write_bytes(data)
        with self.trust_current_tree():self.reject()
    def test_stale_snapshot_is_rejected(self):
        p=self.repo/'tests/fixtures/specs';p.mkdir(parents=True);self.reject()
    def test_fully_valid_control_after_mutation_is_restored(self):
        p=self.artifact/'vectors/check.json';p.write_bytes(b'forged');self.reject();p.write_bytes(self.files['vectors/check.json'])
        self.assertEqual(self.check()['consumers'],['bridge','engine','pi'])

    def test_rewritten_history_validates_from_only_cold_main_with_historical_metadata(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);rewritten=root/'rewritten';rewritten.mkdir()
            def run(repo,*args):
                return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.STDOUT)
            def commit(message):
                run(rewritten,'add','-A')
                run(rewritten,'-c','user.name=Rebase regression','-c','user.email=rebase@example.invalid','commit','-qm',message)
                return run(rewritten,'rev-parse','HEAD').decode().strip()
            def copy_commit(source):
                artifact=rewritten/'protocols/contracts/v1'
                if artifact.exists():shutil.rmtree(artifact)
                names=self.git('ls-tree','-r','--name-only',source,'--','protocols/contracts/v1').decode().splitlines()
                for name in names:
                    path=rewritten/name;path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(self.git('show',source+':'+name))
            run(rewritten,'-c','init.templateDir=','init','-q','--initial-branch=main')
            copy_commit(self.original);adopted_source=commit('Permanent rewritten original')
            copy_commit(self.baseline);adopted_baseline=commit('Permanent rewritten baseline')
            self.assertEqual(run(rewritten,'rev-parse',adopted_source+'^{tree}'),self.git('rev-parse',self.original+'^{tree}'))
            self.assertEqual(run(rewritten,'rev-parse',adopted_baseline+'^{tree}'),self.git('rev-parse',self.baseline+'^{tree}'))
            run(rewritten,'checkout','-qb','author')
            copy_commit(self.candidate);old_author=commit('Author artifact before normal rebase')
            approved=run(rewritten,'rev-parse','HEAD:protocols/contracts/v1').decode().strip()
            self.assertEqual(approved,self.tree)
            run(rewritten,'checkout','-q','main');(rewritten/'unrelated-main.txt').write_text('Main advanced independently')
            commit('Independent main advance')
            run(rewritten,'checkout','-q','author')
            run(rewritten,'-c','user.name=Rebase regression','-c','user.email=rebase@example.invalid','rebase','main')
            rebased=run(rewritten,'rev-parse','HEAD').decode().strip();self.assertNotEqual(rebased,old_author)
            self.assertEqual(run(rewritten,'rev-parse','HEAD:protocols/contracts/v1').decode().strip(),approved)
            run(rewritten,'checkout','-q','main');run(rewritten,'merge','--ff-only','author')
            main=run(rewritten,'rev-parse','HEAD').decode().strip()
            cold=root/'cold';subprocess.check_output(['git','-c','init.templateDir=','init','-q','--initial-branch=intake',str(cold)],stderr=subprocess.STDOUT)
            run(cold,'fetch','--no-tags','--no-write-fetch-head',str(rewritten),main+':refs/heads/main');run(cold,'checkout','-q','main')
            self.assertEqual(run(cold,'for-each-ref','--format=%(refname)').splitlines(),[b'refs/heads/main'])
            self.assertEqual(run(cold,'remote'),b'')
            for name in ['objects/info/alternates','shallow','info/grafts']:
                self.assertFalse((cold/'.git'/name).exists())
            for historical in [self.original,self.baseline,self.candidate,old_author]:
                absent=subprocess.run(['git','-C',str(cold),'cat-file','-e',historical+'^{commit}'],capture_output=True)
                self.assertEqual(absent.returncode,128)
            for anchor in [adopted_source,adopted_baseline]:run(cold,'merge-base','--is-ancestor',anchor,main)
            self.assertEqual(run(cold,'cat-file','-t',approved).strip(),b'tree')
            reachable={line.split()[0].decode() for line in run(cold,'rev-list','--objects','main').splitlines()}
            self.assertIn(approved,reachable)
            metadata=json.loads((cold/'protocols/contracts/v1/manifest.json').read_bytes())
            self.assertEqual(metadata['initial_import_commit'],self.original)
            with patch.object(verifier,'SOURCE_POSTIMAGE',adopted_source),patch.object(verifier,'BASELINE',adopted_baseline):
                self.assertEqual(verifier.validate(cold/'protocols/contracts/v1',cold)['files'],5)
                for name in ['SOURCE_POSTIMAGE','BASELINE','ARTIFACT_TREE_OID']:
                    with patch.object(verifier,name,'0'*40),self.assertRaises((ValueError,subprocess.CalledProcessError)):
                        verifier.validate(cold/'protocols/contracts/v1',cold)
                target=cold/'protocols/contracts/v1/vectors/check.json';original=target.read_bytes();target.write_bytes(b'forged')
                with self.assertRaises(ValueError):verifier.validate(cold/'protocols/contracts/v1',cold)
                target.write_bytes(original);self.assertEqual(verifier.validate(cold/'protocols/contracts/v1',cold)['files'],5)
            print(json.dumps({'control':'actual_rebase_cold_main_only','old_import_metadata':self.original,
                              'old_baseline':self.baseline,'old_candidate':self.candidate,'old_author':old_author,
                              'all_four_old_commit_cat_file_exits':128,'adopted_source':adopted_source,
                              'adopted_baseline':adopted_baseline,'rebased_main':main,'approved_subtree':approved,
                              'subtree_equal_before_after_actual_rebase':True,'subtree_reachable_from_main':True,
                              'original_and_baseline_whole_trees_equal':True,'only_ref':'refs/heads/main',
                              'extra_remote_alternate_shallow_or_graft':False,'valid_then_tamper_then_restore':[5,'REJECT',5]},sort_keys=True))

    def test_missing_runtime_source_or_postimage_anchor_rejects(self):
        for name in ['SOURCE_POSTIMAGE','BASELINE']:
            with self.subTest(anchor=name),patch.object(verifier,name,'0'*40):self.reject()

    def test_wrong_runtime_source_bytes_reject_even_when_current_data_is_valid(self):
        path=self.artifact/'vectors/check.json';path.write_bytes(b'wrong source')
        self.git('add','.');self.commit('Wrong source anchor')
        wrong=self.git('rev-parse','HEAD').decode().strip();path.write_bytes(self.files['vectors/check.json'])
        with patch.object(verifier,'SOURCE_POSTIMAGE',wrong):self.reject()

    def test_wrong_runtime_postimage_manifest_rejects_current_valid_manifest(self):
        self.manifest['unreviewed_note']='forged baseline';self.write_manifest()
        self.git('add','.');self.commit('Wrong postimage anchor')
        wrong=self.git('rev-parse','HEAD').decode().strip()
        self.manifest=json.loads(json.dumps(self.valid_manifest));self.write_manifest()
        with patch.object(verifier,'BASELINE',wrong):self.reject()


    def test_four_dispositions_have_independent_counts_and_source_roles(self):
        result=self.check()
        self.assertEqual((result['artifact_format'],result['records'],result['files'],result['retired']),(2,6,5,1))
        self.assertEqual([row['disposition'] for row in self.manifest['files']],
                         ['maintained','maintained','maintained','modified_t01','retired_t01','authored_t01'])
        self.assertEqual(self.manifest['initial_import_commit'],self.original)
        self.assertIsNone(self.manifest['files'][-1]['original'])
        self.assertIsNone(self.manifest['files'][-1]['baseline'])

    def test_unbound_and_nonliteral_pins_never_fall_back_to_head_or_environment(self):
        with patch.object(verifier,'ARTIFACT_TREE_OID',None),patch.object(verifier,'git') as reader,patch.dict(os.environ,{'NSEALR_ARTIFACT_TREE_OID':self.tree}):
            with self.assertRaisesRegex(ValueError,'unbound'):self.check()
            reader.assert_not_called()
        for value in ['HEAD','HEAD:protocols/contracts/v1','0'*40,self.candidate,self.tree.upper()]:
            with self.subTest(value=value),patch.object(verifier,'ARTIFACT_TREE_OID',value):self.reject()

    def test_strict_json_and_unknown_fields_even_in_deliberately_pinned_fixture(self):
        valid=json.dumps(self.valid_manifest)
        bodies=[b'{',b'[]',b'null',b'\xff',b'\xef\xbb\xbf'+valid.encode(),valid.encode()+b' {}',
                valid.replace('"artifact_format": 2','"artifact_format": 2,"\\u0061rtifact_format":2').encode(),
                valid.replace('"artifact_format": 2','"artifact_format": 2.0').encode(),
                valid.replace('"artifact_format": 2','"artifact_format": true').encode(),
                valid.replace('"artifact_format": 2','"artifact_format": NaN').encode()]
        for value in bodies:
            with self.subTest(raw=value[:45]):
                (self.artifact/'manifest.json').write_bytes(value)
                with self.trust_current_tree():self.reject()
                self.restore_manifest()
        mutations=[lambda v:v.update(extra=True),lambda v:v.update(files=None),
                   lambda v:v.update(files=['invalid']),lambda v:v['consumer_coverage'].update(extra='x'),
                   lambda v:v['files'][0].update(original_sha256='0'*64),
                   lambda v:v['files'][0]['current'].update(extra=True),
                   lambda v:v['files'][0]['current'].update(mode=[]),
                   lambda v:v['files'][0]['current'].update(sha256='A'*64)]
        for mutate in mutations:
            self.manifest=json.loads(valid);mutate(self.manifest);self.write_manifest()
            with self.trust_current_tree():self.reject()
            self.restore_manifest()

    def test_disposition_dependent_null_hash_mode_and_tombstone_rules(self):
        mutations=[lambda r:r[0].update(disposition='unknown'),
                   lambda r:r[0].update(adaptation='Changed inherited adaptation'),
                   lambda r:r[0]['current'].update(mode='100755'),
                   lambda r:r[0]['original'].update(sha256='0'*64),
                   lambda r:r[0]['baseline'].update(sha256='0'*64),
                   lambda r:r[3].update(current=dict(r[3]['baseline'])),
                   lambda r:r[3].update(adaptation=None),
                   lambda r:r[4].update(current=dict(r[4]['baseline'])),
                   lambda r:r.pop(4),
                   lambda r:r[5].update(original=dict(r[0]['original'])),
                   lambda r:r[5].update(baseline=dict(r[0]['baseline'])),
                   lambda r:r[5].update(current=None),
                   lambda r:r[0].update(disposition='authored_t01',original=None,baseline=None,adaptation='False authorship')]
        for index,mutate in enumerate(mutations):
            with self.subTest(case=index):
                self.manifest=json.loads(json.dumps(self.valid_manifest));mutate(self.manifest['files']);self.write_manifest()
                with self.trust_current_tree():self.reject()
                self.restore_manifest()

    def test_unsafe_or_nondata_paths_reject_without_normalization(self):
        for path in ['../escape','/absolute','vectors//x','vectors/./x','vectors/../x',
                     'vectors\\x','vectors/x\0','vectors/x\n','docs/new.json','vectors/']:
            with self.subTest(path=path):
                self.manifest['files'][0]['path']=path;self.write_manifest()
                with self.trust_current_tree():self.reject()
                self.restore_manifest()

    def test_unclassified_new_data_and_retired_path_reappearance_reject(self):
        for path in ['vectors/authored-but-unclassified.json','examples/request.json']:
            with self.subTest(path=path):
                (self.artifact/path).write_bytes(b'{}')
                with self.trust_current_tree():self.reject()
                (self.artifact/path).unlink();self.restore_manifest()

    def test_entire_metadata_modes_hidden_extras_empty_dirs_and_special_files(self):
        for relative in ['LICENSE','adaptation.json']:
            path=self.artifact/relative;data=path.read_bytes();path.write_bytes(b'tampered');self.reject();path.write_bytes(data)
        path=self.artifact/'LICENSE';path.chmod(0o755);self.reject();path.chmod(0o644)
        extra=self.artifact/'__pycache__';extra.mkdir();self.reject()
        (extra/'ignored.pyc').write_bytes(b'cache');self.reject();(extra/'ignored.pyc').unlink();extra.rmdir()
        fifo=self.artifact/'named-pipe';os.mkfifo(fifo);self.reject();fifo.unlink()
        self.assertEqual(self.check()['files'],5)

    def test_approved_nonregular_metadata_and_rewritten_historical_adaptation_reject(self):
        path=self.artifact/'LICENSE';data=path.read_bytes();path.unlink();path.symlink_to('vectors/check.json')
        with self.trust_current_tree():self.reject()
        path.unlink();path.write_bytes(data)
        path=self.artifact/'adaptation.json';data=path.read_bytes();path.write_bytes(b'{"history":"rewritten"}')
        with self.trust_current_tree():self.reject()
        path.write_bytes(data);self.assertEqual(self.check()['files'],5)

    def test_legitimate_modified_executable_mode_is_bound_and_restoration_passes(self):
        path=self.artifact/'schemas/check.json';path.chmod(0o755)
        self.manifest['files'][3]['current']['mode']='100755';self.write_manifest()
        with self.trust_current_tree():self.assertEqual(self.check()['files'],5)
        path.chmod(0o644);self.restore_manifest()

    def test_strict_consumer_structure_patterns_and_retired_only_match_reject(self):
        path=self.artifact/'consumers.json';original=path.read_bytes()
        bad=[{'bridge':['vectors/*.json'],'engine':['vectors/*.json']},
             {'bridge':['vectors/*.json'],'engine':['vectors/*.json'],'pi':['vectors/*.json'],'extra':['vectors/*.json']}]
        for patterns in [[],['vectors/*.json','vectors/*.json'],['examples/request.json'],['../vectors/*'],[1],None]:
            bad.append({name:patterns for name in ['bridge','engine','pi']})
        for value in bad:
            with self.subTest(value=value):
                path.write_text(json.dumps(value))
                with self.trust_current_tree():self.reject()
                path.write_bytes(original);self.assertEqual(self.check()['files'],5)

    def test_schema_valid_forged_new_commit_still_cannot_define_its_own_tree(self):
        path=self.artifact/'vectors/check.json';path.write_bytes(b'{"forged":true}')
        self.manifest['files'][0].update(disposition='modified_t01',adaptation='Unreviewed rewrite',
            current={'mode':'100644','sha256':verifier.sha(path.read_bytes())})
        self.write_manifest();self.git('add','-A');self.commit('Schema-valid forged HEAD')
        self.assertNotEqual(self.git('rev-parse','HEAD:protocols/contracts/v1').decode().strip(),self.tree)
        self.reject()

    def test_git_replace_ref_cannot_substitute_the_literal_approved_tree(self):
        path=self.artifact/'vectors/check.json';path.write_bytes(b'{"forged":true}')
        self.manifest['files'][0].update(disposition='modified_t01',adaptation='Unreviewed replacement',
            current={'mode':'100644','sha256':verifier.sha(path.read_bytes())})
        self.write_manifest();self.git('add','-A');self.commit('Malicious replacement tree')
        replacement=self.git('rev-parse','HEAD:protocols/contracts/v1').decode().strip()
        self.git('replace',self.tree,replacement);self.reject()

    def test_git_owner_execution_mode_change_rejects_even_with_other_execution_bits(self):
        self.git('config','core.filemode','true')
        path=self.artifact/'LICENSE';relative='protocols/contracts/v1/LICENSE'
        path.chmod(0o755)
        with self.trust_current_tree():
            approved=self.git('ls-tree','HEAD','--',relative).split()[0].decode()
            self.assertEqual(approved,'100755')
            for permissions in (0o645,0o654,0o644,0o744,0o760):
                with self.subTest(permissions=oct(permissions)):
                    path.chmod(permissions);self.git('add','--',relative)
                    actual_git=self.git('ls-files','--stage','--',relative).split()[0].decode()
                    print(json.dumps({'control':'owner_execution_mode','approved_git_mode':approved,
                                      'observed_POSIX_permissions':oct(permissions),'actual_git_index_mode':actual_git,
                                      'expected_accept':actual_git==approved},sort_keys=True))
                    if actual_git==approved:self.assertEqual(self.check()['files'],5)
                    else:self.reject()

    def test_nonowner_execution_and_other_permissions_do_not_invent_git_mode_changes(self):
        self.git('config','core.filemode','true')
        path=self.artifact/'LICENSE';relative='protocols/contracts/v1/LICENSE'
        approved=self.git('ls-tree',self.candidate,'--',relative).split()[0].decode()
        self.assertEqual(approved,'100644')
        for permissions in (0o645,0o654,0o600,0o664,0o644):
            with self.subTest(permissions=oct(permissions)):
                path.chmod(permissions);self.git('add','--',relative)
                actual_git=self.git('ls-files','--stage','--',relative).split()[0].decode()
                self.assertEqual(actual_git,approved)
                print(json.dumps({'control':'nonowner_permissions_not_git_mode','approved_git_mode':approved,
                                  'observed_POSIX_permissions':oct(permissions),'actual_git_index_mode':actual_git,
                                  'expected_accept':True},sort_keys=True))
                self.assertEqual(self.check()['files'],5)


if __name__=='__main__':unittest.main()
