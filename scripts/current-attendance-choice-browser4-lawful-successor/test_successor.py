"""Successor source/oracle controls only. Never Native/Auth/browser credit."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import inspect
import json
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def load(name,path=None):
    spec=importlib.util.spec_from_file_location('s03_lawful_browser_'+name,path or HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

class LawfulBrowserControls(unittest.TestCase):
    def test_explicit_helper_and_private_three_source_derivation_are_not_runtime_claims(self):
        meta=json.loads((HERE/'HELPER_SOURCE.json').read_bytes());raw=(HERE/meta['retained']).read_bytes()
        self.assertEqual(sha256(raw).hexdigest(),meta['sha256']);helper=load('lawful',HERE/meta['retained'])
        self.assertEqual(helper.API,'cp7.s03.lawful-fixture.v1');self.assertIsNone(meta['actual_qualified_binding'])
        business=load('business',HERE/'helper-source/business.py');_,proof=business.derive((ROOT/business.ORIGINAL).read_bytes())
        self.assertEqual(proof['counted_changes'],3);self.assertTrue(proof['original_eight_callbacks_unchanged'])
        self.assertFalse(proof['original_eleven_runtime_callbacks_byte_exact']);self.assertTrue(proof['reverse_restores_all_original_bytes'])
        reader,readerproof=business.substitute((HERE/'helper-source/ORIGINAL_READER3.py').read_bytes(),[(business.READER_BEFORE,business.READER_AFTER)])
        self.assertEqual(readerproof['counted_changes'],1);compile(reader,'local_source_only_reader','exec')

    def test_full_future_qualifier_source_map_is_explicit_additive_and_closed(self):
        binder=load('proof_binder');pin=dict(bytes=3,sha256='a'*64);old={'files':{'scripts/old.py':pin}}
        source={'files':dict(old['files'],**{'scripts/new.py':dict(bytes=4,sha256='b'*64)})}
        binding=dict(current_qualifier_source_count=2,full_current_qualifier_source_files=deepcopy(source['files']))
        self.assertEqual(binder.check_current_closure(source,binding,old),source['files'])
        for kind in('old_only','changed_old','missing','unknown','bool','unsafe'):
            s,b=deepcopy(source),deepcopy(binding)
            if kind=='old_only':s=deepcopy(old);b.update(current_qualifier_source_count=1,full_current_qualifier_source_files=deepcopy(old['files']))
            elif kind=='changed_old':s['files']['scripts/old.py']['sha256']='c'*64;b['full_current_qualifier_source_files']=deepcopy(s['files'])
            elif kind=='missing':s['files'].pop('scripts/new.py')
            elif kind=='unknown':s['files']['scripts/extra.py']=pin
            elif kind=='bool':b['current_qualifier_source_count']=True
            else:s['files']['../escape.py']=s['files'].pop('scripts/new.py');b['full_current_qualifier_source_files']=deepcopy(s['files'])
            with self.subTest(kind=kind),self.assertRaises(ValueError):binder.check_current_closure(s,b,old)

    def test_p2_and_cancellation_paths_preserve_money_oracles_and_no_old_global_patch(self):
        source=(HERE/'fixture.py').read_text();cases=(HERE/'cases.mjs').read_text()
        self.assertIn("r['lawful'].earned(cur, s, output, Decimal('20.02'), core=core",source)
        self.assertNotIn('f.earned(cur, m, output',source);self.assertIn("r['lawful'].reopen_source(cur, source, core=r['core']",source)
        self.assertIn("Decimal('1000.03')",source);self.assertIn("Decimal('600.02')",source);self.assertIn("Decimal('400.01')",source)
        for needle in('100003n','60002n','40001n','2002n','1201n','801n','OWN_CANCEL_FULL_FG_ROWS_RESTORE_EXACT','ORDINARY_CANCEL_FULL_FG_ROWS_RESTORE_EXACT'):
            self.assertIn(needle,cases)
        self.assertNotIn('setval(',source);self.assertNotIn('lawful.earned =',source)

    def test_all_counted_browser_adaptations_reverse_exact_frozen_parent_bytes(self):
        proof=load('derive_successor').verify()
        self.assertTrue(proof['all_parent_bytes_restored']);self.assertGreater(proof['counted_changes'],0)
        self.assertFalse(proof['Native_SQL_changed']);self.assertFalse(proof['frozen_runtime7_changed'])

    def test_cancellation_helper_requires_exact_post_allocation_snapshot(self):
        helper=load('lawful_snapshot_API',HERE/'helper-source/lawful_fixture.py')
        parameter=inspect.signature(helper.assert_cancelled).parameters.get('after_allocation')
        self.assertIsNotNone(parameter,'Pre-cancel raw journal/HPP snapshot must be bound explicitly')
        self.assertIs(parameter.default,inspect.Parameter.empty)
        source=(HERE/'fixture.py').read_text();cases=(HERE/'cases.mjs').read_text()
        self.assertIn('after_allocation=posted',source)
        self.assertIn('after_allocation:ownBeforeCancel.finished_native[po]',cases)
        self.assertIn('after_allocation:ordinaryBeforeCancel.finished_native[po]',cases)

if __name__=='__main__':unittest.main(verbosity=2)
