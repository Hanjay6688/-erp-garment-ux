"""Local source/catalog/undo controls; no actual DB/Auth/Native credit."""
from pathlib import Path
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace as NS
import hashlib,importlib.util,json,sys,unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_attendance_period_choice import catalog_contract as contract,native_delta as delta

def model():
    """Synthetic full22, with explicitly modelled metadata, not Native capture."""
    ids=json.loads((HERE/'NEW_CATALOG_IDENTITIES.json').read_bytes())['objects']
    before={group:{'existing:'+group:['retained',None]}for group in ids}
    definitions={sig:'patched:'+sig for sig in delta.SIGNATURES}
    before['functions']={sig:['original:'+sig,'postgres','retained-ACL',None]for sig in definitions}
    after=deepcopy(before)
    for group,names in ids.items():
        for name in names:after[group][name]=['new declared object']
    for sig,body in definitions.items():after['functions'][sig][0]=body
    return before,after,definitions

class SourceBoundary(unittest.TestCase):
    def test_full22_exact_additive_inventory_and_all15_captures(self):
        contract.transition(*model())
        self.assertEqual(len(contract.declared_functions()),36)
        self.assertEqual(len(delta.SIGNATURES),15);self.assertEqual(len(delta.NATIVE_SIGNATURES),12)
        self.assertEqual(len(delta.CLONES),2)
    def test_rogue_addition_in_every_catalog_group_fails_including_own_schema(self):
        for group in model()[0]:
            with self.subTest(group=group):
                before,after,definitions=model();after[group]['cp7_attendance_choice.rogue']=['undeclared']
                with self.assertRaisesRegex(ValueError,'EXACT_NEW_IDENTITIES'):contract.transition(before,after,definitions)
    def test_existing_rows_deletion_or_acl_metadata_mutation_fail(self):
        for group in model()[0]:
            before,after,definitions=model();key=next(iter(before[group]));after[group].pop(key)
            with self.subTest(group=group),self.assertRaisesRegex(ValueError,'UNDECLARED_CATALOG'):contract.transition(before,after,definitions)
        before,after,definitions=model();sig=next(iter(definitions));after['functions'][sig][-1]='GRANT EXECUTE TO PUBLIC'
        with self.assertRaisesRegex(ValueError,'UNDECLARED_CATALOG'):contract.transition(before,after,definitions)
    def test_missing_native_delta_or_only21_groups_refuses(self):
        before,after,definitions=model();sig=next(iter(definitions));after['functions'][sig]=before['functions'][sig]
        with self.assertRaisesRegex(ValueError,'EXACT_CHANGED_CAPTURE15'):contract.transition(before,after,definitions)
        before,after,definitions=model();before.pop('roles');after.pop('roles')
        with self.assertRaisesRegex(ValueError,'ALL22_REQUIRED'):contract.transition(before,after,definitions)
    def test_counted_native_anchors_and_distinct_clone_operation_are_fail_closed(self):
        originals=json.loads((HERE/'SOURCE_DERIVED_NATIVE_ABI.json').read_bytes())['definitions']
        patched=delta.patched(originals);clones=delta.clones(originals)
        self.assertEqual(set(patched),set(delta.SIGNATURES));self.assertTrue(all(patched[k]!=originals[k]for k in patched))
        self.assertIn("'cp7_s03_native_create_carry_pool_v1'",clones[delta.CLONES[0]])
        self.assertNotIn("v_operation constant text := 'create_attendance_hpp_pool_v1';",clones[delta.CLONES[0]])
        with self.assertRaisesRegex(ValueError,'ANCHOR'):delta.once('xx','x','y','duplicate')
        damaged=dict(originals);damaged[delta.APPROVE]=damaged[delta.APPROVE].replace('perform erp._cp3_lock_business_period(p.period_start,p.period_end);','')
        with self.assertRaisesRegex(ValueError,'ANCHOR'):delta.patched(damaged)
    def test_source_derived_abi_provenance_is_exact_and_is_not_runtime_capture(self):
        abi=json.loads((HERE/'SOURCE_DERIVED_NATIVE_ABI.json').read_bytes())
        self.assertFalse(abi['actual_current_runtime_capture']);self.assertFalse(abi['current_runtime_verified'])
        for signature,definition in abi['definitions'].items():
            self.assertEqual(hashlib.sha256(definition.encode()).hexdigest(),abi['provenance'][signature]['exported_definition_sha256'])
        for signature,row in abi['local_reference_definitions'].items():
            expected=row.get('definition_sha256',row.get('P00_definition_sha256'))
            self.assertEqual(hashlib.sha256(row['definition'].encode()).hexdigest(),expected,signature)
        for name,expected in abi['input_files'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected)
        spec=json.loads((HERE/'NEW_CATALOG_IDENTITIES.json').read_bytes())
        self.assertEqual(hashlib.sha256((ROOT/spec['query_owner']).read_bytes()).hexdigest(),spec['query_owner_sha256'])
    def test_early_approval_guards_preserve_lock_order_fresh_access_and_later_native_steps(self):
        originals=json.loads((HERE/'SOURCE_DERIVED_NATIVE_ABI.json').read_bytes())['definitions'];patched=delta.patched(originals)
        facade=patched[delta.FACADE];native=patched[delta.APPROVE]
        raw="perform pg_advisory_xact_lock(hashtextextended(p.contractor_id::text,0));"
        period='perform erp._cp3_lock_business_period(p.period_start,p.period_end);'
        claim='perform cp7_attendance_choice.assert_period_unclaimed_v1(p.period_start,p.period_end);'
        self.assertLess(facade.index('for update;'),facade.index(raw))
        self.assertLess(facade.index(raw),facade.index(period));self.assertLess(facade.index(period),facade.index(claim))
        self.assertLess(facade.index('settlement_access(p_action) is distinct from a',facade.index(period)),facade.index(claim))
        self.assertLess(facade.index(claim),facade.index('perform 1 from erp.payroll_work_items'))
        self.assertLess(facade.index(claim),facade.index('perform cp7_payroll.rebuild_nonwork(p.id);'))
        # Existing later permission/token/meaning/Native checks still occur.
        self.assertEqual(facade.count('settlement_access(p_action) is distinct from a'),originals[delta.FACADE].count('settlement_access(p_action) is distinct from a')+1)
        self.assertEqual(native.count(claim),2)
        before=native.index('perform erp.recalculate_payroll(p_payroll_id);')
        self.assertLess(native.index(period),native.index('perform erp.require_owner_admin();',native.index(period)))
        self.assertLess(native.index(claim),before);self.assertGreater(native.rindex(claim),before)
    def test_frozen13_financial_access_bodies_clones_and_old11_case_assertions_remain_exact(self):
        frozen=json.loads((HERE/'evidence/READER15_FROZEN13_SOURCE_BINDING.json').read_bytes())
        originals=json.loads((HERE/'SOURCE_DERIVED_NATIVE_ABI.json').read_bytes())['definitions'];patched=delta.patched(originals)
        for signature,expected in frozen['financial13_original_sha256'].items():self.assertEqual(hashlib.sha256(originals[signature].encode()).hexdigest(),expected,signature)
        for signature,expected in frozen['financial13_derived_sha256'].items():self.assertEqual(hashlib.sha256(patched[signature].encode()).hexdigest(),expected,signature)
        for signature,expected in frozen['unchanged_two_clone_sha256'].items():self.assertEqual(hashlib.sha256(delta.clones(originals)[signature].encode()).hexdigest(),expected,signature)
        self.assertEqual(hashlib.sha256((HERE/'choice.sql').read_bytes()).hexdigest(),frozen['frozen_choice_sql_sha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/current-attendance-period-choice-qualification/cases.py').read_bytes()).hexdigest(),frozen['original11_cases_sha256'])
        for signature in delta.READER_SIGNATURES:
            damaged=dict(originals);damaged[signature]=damaged[signature].replace('return jsonb_build_object(', 'return /* damaged anchor */ jsonb_build_object(',1)
            with self.subTest(signature=signature),self.assertRaisesRegex(ValueError,'ANCHOR'):delta.patched(damaged)

class PreuseGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cp7_attendance_period_choice import composition
        cls.module=composition
    def harness(self,changed=None):
        calls=[];before_data={'erp.business':[1,'hash'],'sequence:erp.number':['8',True]}
        pristine={**before_data,'cp7_attendance_choice.decisions_v1':[0,'empty']}
        current=deepcopy(pristine)
        if changed:current[changed]=['changed']
        @contextmanager
        def atomic(cur):calls.append('atomic-enter');yield;calls.append('atomic-exit')
        @contextmanager
        def owner(cur,name):calls.append('owner:'+name);yield
        def execute(sql,*args,**kwargs):
            calls.append(sql)
            if sql=='drop schema cp7_attendance_choice cascade':current.clear();current.update(before_data)
            return NS(fetchone=lambda:(None,))
        catalog=NS(_lock_tables=lambda cur:calls.append('lock-all-tables'),_data=lambda cur:deepcopy(current),
                   _catalog_rows=lambda cur:{'exact':'old'})
        base=NS(atomic=atomic,predecessor=NS(predecessor=NS(_locks=lambda cur:calls.append('global-lock'))))
        state=dict(preuse_data_and_sequences=pristine,before_data=before_data,before={'exact':'old'},
                   originals={k:'ORIGINAL '+k for k in delta.SIGNATURES},predecessor={})
        return NS(calls=calls,state=state,cur=NS(execute=execute),runtime=lambda:(None,None,None,base,catalog),owner=owner)
    def test_business_row_or_sequence_use_refuses_before_any_inverse_ddl(self):
        for changed in('erp.business','sequence:erp.number','cp7_attendance_choice.decisions_v1'):
            h=self.harness(changed)
            with self.subTest(changed=changed),patch.object(self.module,'runtime',h.runtime),patch.object(self.module,'verify',lambda *args:None),patch.object(self.module,'as_owner',h.owner):
                with self.assertRaisesRegex(ValueError,self.module.USED_ERROR):self.module.rollback_delta_preuse(h.cur,h.state)
            self.assertEqual(h.calls,['atomic-enter','global-lock','lock-all-tables'])
    def test_pristine_undo_restores15_originals_and_only3_public_rpcs_then_schema(self):
        h=self.harness()
        @contextmanager
        def ddl_scope(cur):yield {'before':[]}
        with patch.object(self.module,'runtime',h.runtime),patch.object(self.module,'verify',lambda *args:None),patch.object(self.module,'as_owner',h.owner),patch.object(self.module,'existing_schema_ddl',ddl_scope),patch.object(self.module.predecessor,'verify',lambda *args:{'parent':'model'}):
            result=self.module.rollback_delta_preuse(h.cur,h.state)
        self.assertTrue(result['used_guard_before_DDL'])
        ddl=[s for s in h.calls if s.startswith('ORIGINAL ')or s.startswith('drop ')]
        self.assertEqual(ddl,[*h.state['originals'].values(),*['drop function '+sig for sig in contract.PUBLIC],'drop schema cp7_attendance_choice cascade'])
    def test_nonpostgres_existing_reader_owner_refuses_before_any_ddl(self):
        for signature in delta.READER_SIGNATURES:
            before,_,_=model();before['functions'][signature][1]='unexpected_owner';calls=[]
            @contextmanager
            def atomic(cur):yield
            base=NS(atomic=atomic,predecessor=NS(predecessor=NS(_locks=lambda cur:calls.append('lock'))))
            catalog=NS(_catalog_rows=lambda cur:before,_data=lambda cur:{})
            cur=NS(execute=lambda *args,**kwargs:(_ for _ in()).throw(AssertionError('DDL_BEFORE_OWNER_GUARD')))
            with self.subTest(signature=signature),patch.object(self.module,'runtime',lambda:(None,None,None,base,catalog)),patch.object(self.module.predecessor,'verify',lambda *args:{}):
                with self.assertRaisesRegex(ValueError,'OWNER_CHANGED'):self.module.install_delta(cur,{})
            self.assertEqual(calls,['lock'])
    def test_mutated_capture_or_derivation_refuses_before_catalog_read_or_inverse_ddl(self):
        originals=json.loads((HERE/'SOURCE_DERIVED_NATIVE_ABI.json').read_bytes())['definitions']
        before={'functions':{sig:[body,'postgres']for sig,body in originals.items()}}
        pristine=dict(sources={'own':'local model'},predecessor={'sources':{'parent':'local model'},'after':before},
            before=before,parent_binding='sealed',parent_proof={},originals=originals,
            definitions=delta.patched(originals),clones=delta.clones(originals))
        catalog=NS(_authority=lambda cur:None,_catalog_rows=lambda cur:(_ for _ in()).throw(AssertionError('TOO_LATE_CATALOG_READ')))
        for field in('originals','definitions','clones'):
            state=deepcopy(pristine);state[field][next(iter(state[field]))]+='\nMUTATED'
            with self.subTest(field=field),patch.object(self.module,'runtime',lambda:(None,None,None,None,catalog)),patch.object(self.module,'sources',lambda:pristine['sources']),patch.object(self.module.predecessor,'sources',lambda:pristine['predecessor']['sources']),patch.object(self.module,'binding',lambda *args:'sealed'):
                with self.assertRaisesRegex(ValueError,'ACTUAL_CAPTURE_OR_DERIVATION_CHANGED'):self.module.verify(None,state)

if __name__=='__main__':unittest.main()
