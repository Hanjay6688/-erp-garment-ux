"""Self-contained actual52eed output replays and tamper negatives; Native0."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class Generated(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.here=self.root/'qualifier';self.here.mkdir()
        for file in ('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json'):
            raw=(HERE/file).read_bytes();(self.here/file).write_bytes(raw)
            for name in json.loads(raw)['producer_files']:
                p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        gitdir=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--absolute-git-dir'],text=True,env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0'}).strip();(self.root/'.git').write_text('gitdir: '+gitdir+'\n')
        self.names=set()
        for file in ('S05_52EED_P0_REFERENCE.zip','S05_52EED_LATER_REFERENCE.zip'):
            with zipfile.ZipFile(HERE/'evidence'/file)as archive:
                for name in archive.namelist():
                    p=self.root/'cp6-proof/t3'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.read(name));self.names.add(str(p.relative_to(self.root)))
        p=self.root/'cp6-proof/t3/T3_PACKAGE_INSTALL.json';d=json.loads(p.read_bytes());head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,env={**os.environ,'GIT_NO_LAZY_FETCH':'1'}).strip();d['run_identity'].update(tool_head=head,github_sha=head,workflow='CP7 S05 lawful WIB and Owner fixture fresh Native10');p.write_text(json.dumps(d))
        self.p0=load('s05_generated_P0','generated_receipts.py');self.later=load('s05_generated_later','generated_later.py')

    def admit(self):
        a,first=self.p0.admit(self.root,self.here,self.names);b,second=self.later.admit(self.root,self.here,self.names);self.assertFalse(set(a)&set(b));return dict(a,**b),(first,second)

    def artifact(self):return next(self.root/n for n in sorted(self.names)if '/ARTIFACT_FETCH/'in n and n.endswith('.json'))

    def test_all111_actual_reference_outputs_self_contained_no_ambient_UUIDs(self):
        accepted,proof=self.admit();self.assertEqual(set(accepted),self.names);self.assertEqual(len(accepted),111)
        self.assertEqual(proof[0]['Native_qualification_credit'],0);self.assertEqual(proof[1]['actual_Native_credit'],0)
        self.assertFalse(json.loads((self.root/'cp6-proof/t3/T3_PACKAGE_INSTALL.json').read_bytes())['gate']['writer_runtime'])

    def test_missing_historical_UUID_is_not_replaced_by_current_worktree_receipt(self):
        self.artifact().unlink()
        with self.assertRaisesRegex(ValueError,'REGULAR_FILE_REQUIRED'):self.admit()

    def test_unknown_ID_and_retry_or_inherited_flags_refuse(self):
        p=self.artifact();d=json.loads(p.read_bytes());d['artifact_id']=1;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'ID_OR_ATTEMPT'):self.admit()

    def test_arbitrary_source_JSON_and_extra_clone_output_remain_unaccepted(self):
        self.names|={'scripts/unknown.py','cp6-proof/t3/arbitrary.json','cp6-proof/t3/CLONE_install.diff'}
        accepted,_=self.admit();self.assertFalse(self.names<=set(accepted))

    def test_leaf_symlink_refuses(self):
        p=self.artifact();raw=p.read_bytes();p.unlink();q=self.root/'payload';q.write_bytes(raw);p.symlink_to(q)
        with self.assertRaisesRegex(ValueError,'SYMLINK'):self.admit()

    def test_ancestor_symlink_refuses(self):
        p=self.root/'cp6-proof/t3/ARTIFACT_FETCH';q=self.root/'held';p.rename(q);p.symlink_to(q,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'SYMLINK'):self.admit()

    def test_bool_integer_aligned_and_changed_producer_refuse(self):
        p=self.root/'cp6-proof/t3/ALIGNED_CHAIN.json';d=json.loads(p.read_bytes());d['production_go']=0;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(AssertionError,'ALIGNMENT_PROVENANCE'):self.admit()

    def test_clone_source_bytes_or_identity_change_refuses(self):
        p=self.root/'cp6-proof/t3/CLONE_install.clone-erp.sql';p.write_bytes(b'changed')
        with self.assertRaisesRegex(AssertionError,'DIAGNOSTIC_BYTES_CHANGED'):self.admit()

    def test_source_declared_dispatch_allowed_other_workflow_denied(self):
        p=self.root/'cp6-proof/t3/T3_PACKAGE_INSTALL.json';d=json.loads(p.read_bytes());d['run_identity']['event']='workflow_dispatch';p.write_text(json.dumps(d));a,_=self.admit();self.assertEqual(set(a),self.names)
        d['run_identity']['workflow']='OTHER';p.write_text(json.dumps(d))
        with self.assertRaises(AssertionError):self.admit()


if __name__=='__main__':unittest.main()
