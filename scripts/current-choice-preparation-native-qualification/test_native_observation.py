"""Negative guards for Native observations and the narrowly reviewed INFO."""
from pathlib import Path
from copy import deepcopy
import ast,importlib.util,sys,unittest

sys.dont_write_bytecode=True

HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE/'native_observation.py').read_text())
namespace={}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)
    and n.name in ('check_ready_get','check_claims')],type_ignores=[]),'native_observation.py','exec'),namespace)
spec=importlib.util.spec_from_file_location('private_advisor_review',HERE/'advisor_review.py')
advisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(advisor)


class Cursor:
    def __init__(self,own=1,foreign=0):self.counts=(own,foreign)
    def execute(self,query,args):
        assert args==('job',) and 'pg_backend_pid()'in query and 'classid::bigint<<32'in query
        assert 'CP7:FROZEN_CHOICE_PREP:'in query
        return self
    def fetchone(self):return self.counts


class Observations(unittest.TestCase):
    def test_same_transaction_ready_get_requires_exact_own_lock(self):
        result=dict(state='READY',worker_active=False,source_request='same',units_done=1)
        observed=namespace['check_ready_get'](Cursor(),{'row':{'id':'job'}},result,dict(result,worker_active=True))
        self.assertTrue(observed['all_other_fields_exact'])
    def test_missing_or_foreign_lock_rejected(self):
        for counts in ((0,0),(1,1)):
            with self.subTest(counts=counts),self.assertRaises(AssertionError):
                namespace['check_ready_get'](Cursor(*counts),{'row':{'id':'job'}},
                    dict(state='READY',worker_active=False),dict(state='READY',worker_active=True))
    def test_get_payload_or_worker_drift_rejected(self):
        result=dict(state='READY',worker_active=False,source_request='same',units_done=1)
        for change in ({'source_request':'other'},{'units_done':0},{'worker_active':False}):
            with self.subTest(change=change),self.assertRaises(AssertionError):
                namespace['check_ready_get'](Cursor(),{'row':{'id':'job'}},result,dict(result,worker_active=True,**change) if 'worker_active'not in change else dict(result,**change))
    def test_undefined_guc_to_empty_requires_effective_identity_equal(self):
        row=namespace['check_claims'](('claims','',None),('claims','',''),('actor',{'sub':'actor'}),('actor',{'sub':'actor'}))
        self.assertEqual(row['initially_undefined_to_empty'],[2])
    def test_all_three_nonnull_values_must_be_restored_exactly(self):
        before=('plural','sub','singular')
        for index in range(3):
            after=list(before);after[index]=''
            with self.subTest(index=index),self.assertRaises(AssertionError):
                namespace['check_claims'](before,after,('same',),('same',))
    def test_changed_effective_actor_refused_even_with_equal_raw_settings(self):
        with self.assertRaises(AssertionError):
            namespace['check_claims'](('a','',''),('a','',''),('one',),('two',))


class Advisors(unittest.TestCase):
    def proof(self):
        return dict(object=[advisor.SCHEMA,advisor.TABLE],owner='cp7_capture',rls=True,policies=[],
            public_schema_acl_empty=True,public_table_acl_empty=True,
            schema_usage={r:False for r in advisor.ROLES},
            table_privileges={r:{p:False for p in advisor.PRIVILEGES}for r in advisor.ROLES})
    def finding(self):
        return dict(name='rls_enabled_no_policy',level='INFO',metadata=dict(type='table',schema=advisor.SCHEMA,name=advisor.TABLE))
    def review(self,finding,proof=None):
        delta=dict(status='REVIEW_REQUIRED',added=[finding])
        def old(d,m):return dict(status='UNEXPLAINED_FINDINGS',unexplained=d['added'],gate=False)
        return advisor.review(delta,[],proof or self.proof(),old)
    def test_only_exact_verified_info_is_reviewed(self):
        result=self.review(self.finding())
        self.assertTrue(result['gate']);self.assertFalse(result['predecessor_disposition']['gate'])
        self.assertEqual(len(result['reviewed_new_private_info']),1)
    def test_warning_or_other_table_stays_blocked(self):
        for change in ({'level':'WARN'},{'metadata':dict(type='table',schema=advisor.SCHEMA,name='other')}):
            self.assertFalse(self.review(dict(self.finding(),**change))['gate'])
    def test_direct_privilege_or_disabled_rls_or_policy_refused(self):
        proofs=[]
        p=self.proof();p['table_privileges']['authenticated']['SELECT']=True;proofs.append(p)
        p=self.proof();p['schema_usage']['anon']=True;proofs.append(p)
        p=self.proof();p['rls']=False;proofs.append(p)
        p=self.proof();p['policies']=['new_policy'];proofs.append(p)
        p=self.proof();p['public_table_acl_empty']=False;proofs.append(p)
        for proof in proofs:
            with self.subTest(proof=proof),self.assertRaises(AssertionError):self.review(self.finding(),proof)


if __name__=='__main__':unittest.main()
