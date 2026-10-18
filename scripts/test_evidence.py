"""Tamper controls for frozen evidence, one graph and current contract attribution."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from verify_evidence import CONTRACTS,RELOCATIONS,objects,relocated,sha,validate


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.git('init','-q');self.git('config','user.name','Synthetic proof');self.git('config','user.email','proof@example.invalid')
        for path in ['proof.txt',*CONTRACTS]:self.put(path,b'Purpose-written source fixture.\n')
        self.git('add','.');self.git('-c','commit.gpgsign=false','commit','-qm','historical source');self.source=self.git('rev-parse','HEAD').decode().strip()
        rows=objects(self.root,self.source)
        self.index={'source_commit':self.source,'source_identity':{'commit':self.source,'tree':self.git('rev-parse','HEAD^{tree}').decode().strip()},
            'relocations':RELOCATIONS,'artifacts':[],'current_contracts':[],'current_navigation':list(CONTRACTS.values())}
        bound=[]
        for path,info in rows.items():
            data=(self.root/path).read_bytes();bound.append({'path':path,'sha256':sha(data)})
            self.index['artifacts'].append({'path':path,'current_unchanged_path':path,'original_commit':self.source,'sha256':sha(data),**info})
        for old,new in CONTRACTS.items():
            data=relocated((self.root/old).read_text(),old,new).encode();self.put(new,data)
            self.index['current_contracts'].append({'source_path':old,'current_path':new,'source_sha256':sha((self.root/old).read_bytes()),'initial_relocated_sha256':sha(data),'equivalent_under_link_relocation':True})
        self.put('plan/work-items.json',json.dumps({'tasks':[{'status':'integrated','result_artifacts':bound}]}).encode());self.save()
        self.git('add','.');self.git('-c','commit.gpgsign=false','commit','-qm','current navigation')

    def git(self,*args):return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL)
    def put(self,path,data):p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    def save(self):self.put('plan/evidence-index.json',json.dumps(self.index).encode())
    def check(self):return validate(self.root,self.source)
    def fails(self,needle):
        with self.assertRaisesRegex(ValueError,needle):self.check()

    def test_original_source_and_current_projection_pass(self):self.assertEqual(self.check()['closed_files'],6)
    def test_changed_frozen_bytes_fail_and_exact_restore_passes(self):
        original=(self.root/'proof.txt').read_bytes();self.put('proof.txt',b'tampered');self.fails('frozen evidence');self.put('proof.txt',original);self.check()
    def test_missing_closure_entry_fails(self):self.index['artifacts'].pop();self.save();self.fails('closure')
    def test_duplicate_closure_entry_fails(self):self.index['artifacts'].append(copy.deepcopy(self.index['artifacts'][0]));self.save();self.fails('closure')
    def test_escaping_alias_fails(self):self.index['artifacts'][0]['current_unchanged_path']='../escape';self.save();self.fails('alias')
    def test_wrong_source_commit_fails(self):self.index['source_commit']='a'*40;self.save();self.fails('source commit')
    def test_wrong_source_blob_fails(self):self.index['artifacts'][0]['blob']='b'*40;self.save();self.fails('historical blob')
    def test_dangling_current_navigation_fails(self):
        self.put('current.md',b'[bad](missing.md)');self.index['current_navigation'].append('current.md');self.save();self.fails('dangling')
    def test_second_graph_fails(self):self.put('docs/restart/work-items.json',b'{}');self.fails('second live')
    def test_changed_current_contract_cannot_claim_old_review(self):
        self.put('docs/product/contract.md',b'Changed requirement');self.fails('falsely attributed')
    def test_changed_current_contract_needs_distinct_closed_evidence(self):
        self.put('docs/product/contract.md',b'Changed requirement');self.index['current_contracts'][0]['equivalent_under_link_relocation']=False;self.save();self.fails('own closed')
    def test_current_contract_alias_rejected(self):self.index['current_contracts'][0]['current_path']='../escape';self.save();self.fails('contract owner')


if __name__=='__main__':unittest.main()
