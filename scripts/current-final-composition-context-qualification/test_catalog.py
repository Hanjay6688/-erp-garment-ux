"""Offline mutation controls over declared catalogue excerpts; Native credit zero."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('final_context_offline_controls',HERE/'catalog.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class ContextCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory=json.loads((HERE/'INVENTORY.json').read_bytes())

    def setUp(self):
        self.expected=deepcopy(self.inventory['narrow_profiles']['S03'])
        # Explicit local excerpt: omitted unrelated catalogue classes are empty.
        # This tests this narrow comparison, never whole installed-state proof.
        self.catalog={key:{}for key in c.ALL22}
        self.catalog.update(deepcopy(self.expected['catalog']))
        self.table='cp7_attendance_choice.cancel_context_v1'

    def refusal(self,changed,code='CHANGED'):
        with self.assertRaisesRegex(ValueError,code):c.validate(changed,self.expected)

    def test_narrow_exact_profiles_and_complete_source_membership(self):
        for key,expected in self.inventory['narrow_profiles'].items():
            excerpt={name:{}for name in c.ALL22};excerpt.update(deepcopy(expected['catalog']))
            result=c.validate(excerpt,expected)
            self.assertEqual(result['contexts'],52);self.assertEqual(result['actual_Native_credit'],0)
            self.assertIsNone(result['runtime_entry']);self.assertFalse(result['raw_ACL_authority_bound'])
        self.assertEqual(len(self.inventory['original30_specs']),30)
        self.assertEqual(len(self.inventory['actual_common51']),51)
        self.assertEqual(len(self.inventory['proposed_exact56']),56)
        self.assertFalse(self.inventory['full_final_catalogue_captured'])

    def test_read_only_comparison_does_not_mutate_either_argument(self):
        before=deepcopy((self.catalog,self.expected));c.validate(self.catalog,self.expected)
        self.assertEqual((self.catalog,self.expected),before)

    def test_unknown_empty_context_never_hides_behind_schema_prefix(self):
        for schema in ('cp7_credit','cp7_unknown','erp','external_custom'):
            v=deepcopy(self.catalog);name=schema+'.unexpected_empty_context'
            v['relations'][name]=deepcopy(v['relations'][self.table])
            v['columns'][name+':transaction_id']=deepcopy(v['columns'][self.table+':transaction_id'])
            self.refusal(v,'EXACT_MEMBERSHIP')

    def test_foreign_unlogged_and_wrong_typed_transaction_candidates_stay_visible(self):
        for kind,persistence,typ in [('f','p','bigint'),('r','u','bigint'),('p','p','bigint'),('r','p','text')]:
            v=deepcopy(self.catalog);name='cp7_credit.unknown_context'
            row=deepcopy(v['relations'][self.table]);row[1]=kind;row[2]=persistence;v['relations'][name]=row
            row=deepcopy(v['columns'][self.table+':transaction_id']);row[2]=typ;v['columns'][name+':transaction_id']=row
            self.assertIn(name,c.discover(v));self.refusal(v,'EXACT_MEMBERSHIP')

    def test_missing_or_renamed_known_transaction_column_refuses(self):
        for mode in ('missing','renamed'):
            v=deepcopy(self.catalog);row=v['columns'].pop(self.table+':transaction_id')
            if mode=='renamed':row[0]='renamed_tx';v['columns'][self.table+':renamed_tx']=row
            self.refusal(v,'EXACT_MEMBERSHIP')

    def test_all_relation_owner_RLS_kind_persistence_ACL_metadata_are_exact(self):
        for index,value in [(0,'service_role'),(1,'p'),(2,'u'),(3,False),(4,True),(6,'f'),(7,['fillfactor=80'])]:
            v=deepcopy(self.catalog);v['relations'][self.table][index]=value;self.refusal(v)
        v=deepcopy(self.catalog);v['relations'][self.table][12].append(['anon','postgres','SELECT',False]);self.refusal(v)

    def test_boolean_and_integer_catalog_values_are_never_equal(self):
        for group,key,index in [('relations',self.table,3),('columns',self.table+':actor',3),('roles','postgres',0)]:
            v=deepcopy(self.catalog);v[group][key][index]=int(v[group][key][index]);self.refusal(v)

    def test_column_default_raw_ACL_type_and_nullability_changes_refuse(self):
        for index,value in [(2,'text'),(3,False),(4,'a'),(5,'s'),(12,[]),(13,'gen_random_uuid()')]:
            v=deepcopy(self.catalog);v['columns'][self.table+':actor'][index]=value;self.refusal(v)

    def test_constraint_policy_trigger_deletion_and_metadata_drift_refuse(self):
        for group in ('constraints','policies','triggers'):
            key=next(k for k in self.catalog[group]if k.startswith(self.table+':'))
            v=deepcopy(self.catalog);v[group].pop(key);self.refusal(v)
            v=deepcopy(self.catalog);v[group][key][-1]='EXPLICIT_MUTATED_CATALOG_DOUBLE';self.refusal(v)

    def test_index_on_only_and_quoted_names_are_retained(self):
        for target in ('cp7_attendance_choice.cancel_context_v1','ONLY cp7_attendance_choice.cancel_context_v1',
                       '"cp7_attendance_choice"."cancel_context_v1"','ONLY "cp7_attendance_choice".cancel_context_v1'):
            v=deepcopy(self.catalog);key='cp7_attendance_choice.extra_index'
            v['indexes'][key]=['CREATE INDEX extra_index ON '+target+' USING btree (actor)',True,True,True,False,False]
            self.assertIn(key,c.select(v)['catalog']['indexes']);self.refusal(v)

    def test_schema_raw_observation_limit_and_expanded_grant_changes(self):
        self.assertFalse(self.expected['raw_schema_and_relation_ACLs_observed'])
        v=deepcopy(self.catalog);v['schemas']['cp7_attendance_choice'][1].append(['anon','postgres','USAGE',False]);self.refusal(v)

    def test_indirect_membership_and_non_owner_role_drift_cannot_be_omitted(self):
        v=deepcopy(self.catalog);v['memberships']['postgres:anon:postgres']=[False,True,True];self.refusal(v)
        v=deepcopy(self.catalog);v['roles']['anon'][6]=True;self.refusal(v)

    def test_historical_transaction_facts_remain_in_inventory(self):
        for name in ('cp7_credit.initial_refund_operations','cp7_credit.native_empty_operations',
                     'cp7_credit.source_operation_materializations_v1','cp7_attendance_choice.cancel_context_v1'):
            self.assertIn(name,self.expected['names'])
        self.assertFalse(self.expected['all_transaction_tables_are_ephemeral'])
        self.assertFalse(self.expected['active_row_authority_decided'])

    def test_runtime_cannot_touch_cursor_or_infer_approval_from_metadata(self):
        class Cursor:
            def __getattribute__(self,name):raise AssertionError('CURSOR_MUST_NOT_BE_TOUCHED')
        with self.assertRaisesRegex(ValueError,'RUNTIME_CLOSED'):
            c.require_runtime(Cursor(),{'status':'PASS','runtime_entry':'FORGED','actual_Native_credit':56})


if __name__=='__main__':unittest.main(verbosity=2)
