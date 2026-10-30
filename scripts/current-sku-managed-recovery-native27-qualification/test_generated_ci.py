"""Actual historical CI-output replay plus closed-source/tamper negatives."""
from pathlib import Path
from copy import deepcopy
import gzip
import importlib.util
import json
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


p0=load('closed_P0_outputs','generated_receipts.py')
sku=load('closed_SKU_outputs','generated_sku.py')


class Generated(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.here=self.root/'qualifier';self.here.mkdir()
        for file in ('GENERATED_RECEIPTS.json','SKU_GENERATED_RECEIPTS.json'):
            value=json.loads((HERE/file).read_bytes());(self.here/file).write_bytes((HERE/file).read_bytes())
            for name in value['producer_files']:
                p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        self.names=set()
        with zipfile.ZipFile(HERE/'evidence/BD2_P0_GENERATED_REFERENCE.zip')as archive:
            for name in archive.namelist():
                rel='cp6-proof/t3/'+name;p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.read(name));self.names.add(rel)
        p=self.root/'cp6-proof/t3/SKU_TARGETED_CLIENT.json';p.write_bytes(gzip.decompress((HERE/'evidence/BD2_CLIENT72_REFERENCE.json.gz').read_bytes()));self.names.add(str(p.relative_to(self.root)))

    def test_all_actual_bd2_P0_and_exact_old72_outputs_admit_no_new_credit(self):
        first,summary=p0.admit(self.root,self.here,self.names)
        second,client=sku.admit(self.root,self.here,self.names)
        self.assertEqual(set(first)|set(second),self.names)
        self.assertEqual(len(first),112);self.assertEqual(len(second),1)
        self.assertEqual(summary['artifact_attempts'],105)
        self.assertEqual(summary['Native_qualification_credit'],0);self.assertEqual(client['Native_credit'],0)

    def first_artifact(self):
        return next(self.root/name for name in sorted(self.names)if'/ARTIFACT_FETCH/'in name and name.endswith('.json'))

    def test_artifact_unknown_ID_or_modified_inherited_flag_refuses(self):
        p=self.first_artifact();value=json.loads(p.read_bytes());value['partial_stdout_forwarded']=True;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'INHERITED_FLAGS'):p0.admit(self.root,self.here,self.names)

    def test_unknown_source_or_arbitrary_JSON_remains_unaccepted(self):
        names=self.names|{'scripts/Injected.py','cp6-proof/t3/arbitrary.json'}
        first,_=p0.admit(self.root,self.here,names);second,_=sku.admit(self.root,self.here,names)
        self.assertFalse(names<=set(first)|set(second))

    def test_frozen_worktree_boolean_zero_tamper_refuses(self):
        p=self.root/'cp6-proof/t3/FROZEN_SOURCE_WORKTREES.json';value=json.loads(p.read_bytes());value['auditor_head_unchanged']=1;p.write_text(json.dumps(value))
        with self.assertRaises(ValueError):p0.admit(self.root,self.here,self.names)

    def test_untracked_output_symlink_refuses(self):
        p=self.root/'cp6-proof/t3/FROZEN_SOURCE_WORKTREES.json';raw=p.read_bytes();p.unlink();target=self.root/'payload';target.write_bytes(raw);p.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'SYMLINK'):p0.admit(self.root,self.here,self.names)

    def client(self):return self.root/'cp6-proof/t3/SKU_TARGETED_CLIENT.json'

    def test_skipped_failed_or_relabelled_clientcase_refuses(self):
        p=self.client();value=json.loads(p.read_bytes());value['testResults'][0]['assertionResults'][0]['status']='pending';p.write_text(json.dumps(value))
        with self.assertRaises(AssertionError):sku.admit(self.root,self.here,self.names)

    def test_client_count_bool_and_extra_path_refuse(self):
        p=self.client();value=json.loads(p.read_bytes());value['numFailedTests']=False;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(AssertionError,'SUMMARY_CHANGED'):sku.admit(self.root,self.here,self.names)

    def test_native21_partial_output_and_wrong_raw_bytes_refuse(self):
        config=json.loads((ROOT/'scripts/current-sku-combined-followup-qualification/CONFIG.json').read_bytes())['accepted_native7']
        rel='cp6-proof/t3/RETAINED_SKU21C/'+config['original']['name'];p=self.root/rel;p.parent.mkdir();p.write_bytes(b'BAD ORIGINAL')
        with self.assertRaisesRegex(AssertionError,'OUTPUT_SET'):sku.admit(self.root,self.here,self.names|{rel})
        names=set(self.names)
        for name in json.loads((HERE/'SKU_GENERATED_RECEIPTS.json').read_bytes())['retained21_files']:
            rel='cp6-proof/t3/RETAINED_SKU21C/'+name;(self.root/rel).write_bytes(b'BAD');names.add(rel)
        with self.assertRaisesRegex(AssertionError,'BYTES_CHANGED'):sku.admit(self.root,self.here,names)

    def test_native21_contract_cannot_change_without_frozen_reader(self):
        p=self.here/'SKU_GENERATED_RECEIPTS.json';value=json.loads(p.read_bytes());value['retained21_files']['ORIGINAL.zip']['sha256']='0'*64;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(AssertionError,'CONTRACT_DIFFERS_FROM_FROZEN_READER'):sku.admit(self.root,self.here,self.names)


if __name__=='__main__':unittest.main()
