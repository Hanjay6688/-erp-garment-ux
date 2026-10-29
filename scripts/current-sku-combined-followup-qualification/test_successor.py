"""Exact source transition and real retained failure controls; no DB/CI."""
from hashlib import sha256
from pathlib import Path
import gzip
import importlib.util
import json
import subprocess
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
transition=load('unit_exact_SKU_UTC_transition',HERE/'successor.py')
binder=load('unit_exact_SKU_UTC_binder',HERE/'bind.py')
gate=load('unit_exact_SKU_UTC_gate',HERE/'gate.py')
plan=load('unit_exact_SKU_UTC_plan',HERE/'plan.py')
preparation=load('unit_exact_SKU_preparation_fixture',HERE/'test_preparation.py')

def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])


class Successor(unittest.TestCase):
    def test_reviewed_eighteen_paths_have_only_two_product_attributes_and_same_native_business_oracles(self):
        proof=transition.admit_transition(git)
        self.assertEqual(len(proof['reviewed_paths']),18)
        self.assertFalse(proof['financial_quantity_value_inverse_oracles_changed'])
        self.assertEqual(proof['retained961_counts'],{'PASS':6,'INCOMPLETE':1})
        self.assertFalse(proof['retained961_usable_prerequisite'])

    def test_unreviewed_product_byte_or_extra_path_cannot_be_rebound(self):
        sql='scripts/cp7_sku_pair_conversion/conversion.sql'
        def altered(*args):
            raw=git(*args)
            if args==('show',transition.BASE+':'+sql):return raw+b'-- unreviewed\n'
            return raw
        with self.assertRaises(AssertionError):transition.admit_transition(altered)
        def extra(*args):
            raw=git(*args)
            return raw+b'src/Unallocated.tsx\n'if args==('diff','--name-only',transition.PRIOR,transition.BASE)else raw
        with self.assertRaises(AssertionError):transition.admit_transition(extra)

    def test_original961_six_pass_report_and_failed_package_never_unlock_repaired_source(self):
        folder=ROOT/'scripts/current-sku-pair-native-adapter/retained961'
        raw=gzip.decompress((folder/'CP7_SKU_PAIR_CONVERSION_NATIVE.json.gz').read_bytes())
        pkg=gzip.decompress((folder/'T3_PACKAGE_INSTALL.json.gz').read_bytes())
        cfg,_,_,sources=preparation.sample()
        for key,value in(('original',raw),('package',pkg)):
            cfg['accepted_native7'][key].update(bytes=len(value),sha256=sha256(value).hexdigest())
        with self.assertRaisesRegex(ValueError,'RETAINED_NATIVE7_NOT_PASS'):
            gate.admitted(cfg,raw,pkg,sources,plan.NATIVE_IDS)
        cfg['accepted_native7']['head']=transition.PRIOR
        with self.assertRaisesRegex(ValueError,'OTHER_NATIVE_PREREQUISITE'):
            gate.selected(cfg)
        checked_in=json.loads((HERE/'CONFIG.json').read_bytes())
        self.assertFalse(checked_in['retained_failed_native961']['usable_prerequisite'])
        if checked_in['accepted_native7'] is not None:
            self.assertEqual(checked_in['accepted_native7']['head'],gate.BASE)

    def test_missing_pending_run_or_missing_five_zone_observation_never_qualifies(self):
        cfg,raw,pkg,sources=preparation.sample();cfg['pending_run_id']=None
        with self.assertRaisesRegex(ValueError,'OTHER_NATIVE_PREREQUISITE'):gate.selected(cfg)
        for key in('preview_caller_zones_checked','all_preview_fields_equal_across_zones',
                   'preview_caller_setting_restored','posting_function_timezone'):
            cfg,raw,pkg,sources=preparation.sample()
            actual=json.loads(raw);actual['committed'][gate.NATIVE_CASE]['native']['cases'][gate.MIXED_CASE].pop(key)
            raw=json.dumps(actual).encode();cfg['accepted_native7']['original'].update(bytes=len(raw),sha256=sha256(raw).hexdigest())
            with self.assertRaisesRegex(ValueError,'EXACT_FIVE_ZONE_PREVIEW'):gate.admitted(cfg,raw,pkg,sources,plan.NATIVE_IDS)

    def test_prepared_pin_reconciliation_preserves_every_financial_callback_and_current21_native_byte(self):
        # Original private preparation commits are writer-only inputs. CI sees
        # their binder-verified immutable digests, not unavailable Git objects.
        source=json.loads((HERE/'SOURCE.json').read_bytes())
        originals=source['original_import_sha256']
        self.assertTrue(binder.RECONCILED<=set(originals))
        cost='scripts/current-sku-group-cost-qualification/'
        reversed_pin=(ROOT/cost/'cases.py').read_bytes().replace(binder.BASE.encode(),binder.PRIOR.encode())
        self.assertEqual(sha256(reversed_pin).hexdigest(),originals[cost+'cases.py'])
        old=json.loads((ROOT/'scripts/current-sku-pair-native-adapter/SOURCE.json').read_bytes())
        for name in set(old['files'])|{'scripts/current-sku-pair-native-adapter/SOURCE.json','.github/workflows/cp7-sku-pair-native.yml'}:
            self.assertEqual((ROOT/name).read_bytes(),git('show',gate.BASE+':'+name),name)
        for name,original in originals.items():
            if name not in binder.RECONCILED:self.assertEqual(sha256((ROOT/name).read_bytes()).hexdigest(),original,name)


if __name__=='__main__':unittest.main()
