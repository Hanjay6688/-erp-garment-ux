"""Adapter tests, not Native database qualification."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from cp7_catalog_state import canonical_public_state,exact_public_catalog

class ExactCatalog(unittest.TestCase):
    def setUp(self):
        self.raw=dict(relations=[['x','r']],functions=[['b()','bbb'],['a()','aaa']],rows={'x':'1:fff'},extra_acl='retained')
    def test_only_physical_order_changes(self):
        other=deepcopy(self.raw);other['functions'].reverse()
        self.assertEqual(canonical_public_state(self.raw),canonical_public_state(other))
        self.assertEqual(self.raw['functions'][0],['b()','bbb'])
        self.assertEqual(canonical_public_state(self.raw)['extra_acl'],'retained')
    def test_actual_member_hash_acl_or_row_change_still_fails(self):
        for field,value in [('functions',[['b()','different'],['a()','aaa']]),('relations',[]),('rows',{'x':'0:fff'}),('extra_acl','changed')]:
            other=deepcopy(self.raw);other[field]=value
            self.assertNotEqual(canonical_public_state(self.raw),canonical_public_state(other))
        other=deepcopy(self.raw);other['functions'].append(['a()','aaa'])
        self.assertNotEqual(canonical_public_state(self.raw),canonical_public_state(other))
    def test_wrapper_records_only_exact_order_equivalence_and_restores(self):
        raws=[deepcopy(self.raw),deepcopy(self.raw)];raws[1]['functions'].reverse();reader=lambda _cur:raws.pop(0);runner=SimpleNamespace(public_state=reader)
        with exact_public_catalog(runner)as audit:
            self.assertEqual(runner.public_state(None),runner.public_state(None))
        self.assertIs(runner.public_state,reader);self.assertEqual(audit['snapshots_checked'],2);self.assertEqual(len(audit['physical_order_only_changes']),1);self.assertEqual(audit['dropped_fields'],[])
    def test_exception_restores_frozen_reader(self):
        reader=lambda _cur:deepcopy(self.raw);runner=SimpleNamespace(public_state=reader)
        with self.assertRaises(RuntimeError):
            with exact_public_catalog(runner):raise RuntimeError('Controlled failure')
        self.assertIs(runner.public_state,reader)
    def test_full_locations_distinguish_tuple_movement_from_new_oid(self):
        raws=[deepcopy(self.raw),deepcopy(self.raw)];raws[1]['functions'].reverse()
        reader=lambda _cur:raws.pop(0);runner=SimpleNamespace(public_state=reader)
        class Cur:
            rows=[('101','a()','(1,1)','aaa','owner'),('102','b()','(1,2)','bbb','owner')]
            def execute(self,_query):return self
            def fetchall(self):return deepcopy(self.rows)
        cur=Cur()
        with exact_public_catalog(runner,retain_raw=True,retain_locations=True)as audit:
            before=runner.public_state(cur);cur.rows[0]=('101','a()','(2,1)','aaa','owner')
            self.assertEqual(before,runner.public_state(cur))
        self.assertIs(runner.public_state,reader)
        self.assertEqual(len(audit['raw_snapshots'][0]['public_function_locations']),2)
        pair=audit['function_location_comparisons'][0]
        self.assertTrue(pair['exact_signature_oid_owner_unchanged']);self.assertEqual(len(pair['changed_locations']),1)
    def test_unchanged_hash_never_excuses_new_oid_owner_or_missing_location(self):
        for replacement in [('201','a()','(1,1)','aaa','owner'),('101','a()','(1,1)','aaa','foreign-owner'),None]:
            reader=lambda _cur:deepcopy(self.raw);runner=SimpleNamespace(public_state=reader)
            class Cur:
                rows=[('101','a()','(1,1)','aaa','owner'),('102','b()','(1,2)','bbb','owner')]
                def execute(self,_query):return self
                def fetchall(self):return deepcopy(self.rows)
            cur=Cur()
            with self.assertRaises(AssertionError):
                with exact_public_catalog(runner,retain_raw=True,retain_locations=True):
                    runner.public_state(cur)
                    if replacement is None:cur.rows.pop(0)
                    else:cur.rows[0]=replacement
                    runner.public_state(cur)
            self.assertIs(runner.public_state,reader)

if __name__=='__main__':unittest.main()
