"""Self-contained failed8be4 output replays; no ambient historical UUID files."""
from pathlib import Path
from hashlib import sha256
import gzip
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
    s=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class Generated(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.here=self.root/'qualifier';self.here.mkdir()
        (self.here/'CONFIG.json').write_bytes((HERE/'CONFIG.json').read_bytes())
        for file in ('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json','E1_GENERATED_RECEIPTS.json'):
            raw=(HERE/file).read_bytes();(self.here/file).write_bytes(raw)
            for name in json.loads(raw)['producer_files']:
                p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        # Real git, read-only existing checkout metadata: no fake head or helper mock.
        gitdir=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--absolute-git-dir'],text=True,
            env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0'}).strip()
        (self.root/'.git').write_text('gitdir: '+gitdir+'\n')
        self.names=set()
        for file in ('E8BE4_P0_REFERENCE.zip','E8BE4_LATER_REFERENCE.zip'):
            with zipfile.ZipFile(HERE/'evidence'/file)as archive:
                for name in archive.namelist():
                    p=self.root/'cp6-proof/t3'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.read(name))
                    self.names.add(str(p.relative_to(self.root)))
        for name in ('D1_TARGETED_CLIENT.json','E1_TARGETED_CLIENT.json'):
            p=self.root/'cp6-proof/t3'/name;p.write_bytes(gzip.decompress((HERE/'evidence'/(name+'.gz')).read_bytes()))
            self.names.add(str(p.relative_to(self.root)))
        # Only this candidate's workflow/head identity is derived. Historical data,
        # restore, stages and failed writer values stay exactly as archived.
        p=self.root/'cp6-proof/t3/T3_PACKAGE_INSTALL.json';d=json.loads(p.read_bytes())
        head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,
            env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0'}).strip()
        d['run_identity'].update(tool_head=head,github_sha=head,workflow='CP7 A current E1 consumer phase fresh Native17')
        p.write_text(json.dumps(d))
        self.p0=load('e_phase_actual_P0','generated_receipts.py')
        self.e=load('e_phase_actual_E_outputs','generated_e1.py')
        self.later=load('e_phase_actual_later','generated_later.py')

    def admit(self):
        accepted={};proof={}
        for name,helper in (('P0',self.p0),('E',self.e),('later',self.later)):
            pins,summary=helper.admit(self.root,self.here,self.names)
            self.assertFalse(set(accepted)&set(pins));accepted.update(pins);proof[name]=summary
        return accepted,proof

    def artifact(self):return next(self.root/name for name in sorted(self.names)if '/ARTIFACT_FETCH/'in name and name.endswith('.json'))

    def alter(self,p,action):
        value=json.loads(p.read_bytes());action(value);p.write_text(json.dumps(value))

    def test_actual_archived_all_phases_replay_fresh_temporary_files(self):
        accepted,proof=self.admit();self.assertEqual(set(accepted),self.names)
        self.assertEqual(len(self.names),118);self.assertEqual(proof['E']['Native_credit'],0)
        self.assertEqual(proof['later']['actual_Native_credit'],0)
        self.assertEqual(proof['E']['unchanged_client_cases'],{'D1':20,'E1':111})
        package=json.loads((self.root/'cp6-proof/t3/T3_PACKAGE_INSTALL.json').read_bytes())
        self.assertFalse(package['gate']['writer_runtime'])

    def test_missing_historical_UUID_file_refuses_even_when_contract_and_new_UUID_exist(self):
        self.artifact().unlink()
        with self.assertRaisesRegex(ValueError,'REGULAR_FILE_REQUIRED'):self.admit()

    def test_unknown_artifact_or_inherited_flags_refuse(self):
        self.alter(self.artifact(),lambda d:d.update(artifact_id=1))
        with self.assertRaisesRegex(ValueError,'ID_OR_ATTEMPT'):self.admit()

    def test_arbitrary_source_JSON_and_extra_clone_file_remain_unaccepted(self):
        self.names|={'scripts/unknown.py','cp6-proof/t3/arbitrary.json','cp6-proof/t3/CLONE_install.erp.diff'}
        accepted,_=self.admit();self.assertFalse(self.names<=set(accepted))

    def test_leaf_symlink_refuses(self):
        p=self.artifact();raw=p.read_bytes();p.unlink();target=self.root/'raw';target.write_bytes(raw);p.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'SYMLINK'):self.admit()

    def test_ancestor_symlink_refuses(self):
        directory=self.root/'cp6-proof/t3/ARTIFACT_FETCH';target=self.root/'moved-artifacts';directory.rename(target);directory.symlink_to(target,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'SYMLINK'):self.admit()

    def test_boolean_zero_aligned_metadata_refuses(self):
        self.alter(self.root/'cp6-proof/t3/ALIGNED_CHAIN.json',lambda d:d.update(production_go=0))
        with self.assertRaisesRegex(AssertionError,'ALIGNMENT_PROVENANCE'):self.admit()

    def test_client_pending_case_or_false_integer_summary_refuses(self):
        p=self.root/'cp6-proof/t3/E1_TARGETED_CLIENT.json';self.alter(p,lambda d:d.update(numFailedTests=False))
        with self.assertRaisesRegex(AssertionError,'SUMMARY_CHANGED'):self.admit()

    def test_source_producer_changed_refuses(self):
        d=json.loads((self.here/'GENERATED_RECEIPTS.json').read_bytes());p=self.root/next(iter(d['producer_files']));p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'PRODUCER_CHANGED'):self.admit()

    def test_parent_download_partial_or_wrong_raw_set_refuses(self):
        name='cp6-proof/t3/RETAINED_E1_D1/CP7_CREDIT_DE_NATIVE13.json';p=self.root/name;p.parent.mkdir();p.write_bytes(b'BAD');self.names.add(name)
        with self.assertRaisesRegex(AssertionError,'PARENT_OUTPUT_SET'):self.admit()


if __name__=='__main__':unittest.main()
