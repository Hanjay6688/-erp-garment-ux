"""Fail-closed authority boundaries; these are not database execution credit."""
from copy import deepcopy
import unittest
from cp7_current_choice_preparation import installation as product
from cp7_current_choice_preparation import retention_access as stage


class RetentionAuthority(unittest.TestCase):
    def setUp(self):
        self.before={group:{}for group in product.catalog.QUERIES}
        for key,owner in stage.COLUMNS.items():
            self.before['relations'][key.split(':')[0]]=[owner,'r','p',True,False]
            self.before['columns'][key]=['run_id',3,'uuid',True,'','','p','',-1,None,None,'-',None,None]
        self.after=deepcopy(self.before)
        for key in stage.COLUMNS:
            self.after['columns'][key]=stage.expected_column(key,self.before['columns'][key])

    def test_exact_column_only_delta_is_admitted(self):
        stage.admit_transition(self.before,self.after)
        product.admit_delta(stage,self.before,self.after,dict(catalog=stage.own(self.after)))
        self.assertEqual(sum(len(rows)for rows in stage.own(self.after).values()),2)

    def test_any_extra_or_missing_authority_is_refused(self):
        key=next(iter(stage.COLUMNS));table=key.split(':')[0]
        mutations=[
            lambda x:x['columns'][key].__setitem__(12,['cp7_capture=rw/'+stage.COLUMNS[key]]),
            lambda x:x['columns'][key].__setitem__(12,['cp7_capture=r*/'+stage.COLUMNS[key]]),
            lambda x:x['columns'][key].__setitem__(12,['authenticated=r/'+stage.COLUMNS[key]]),
            lambda x:x['columns'][key].__setitem__(12,['cp7_capture=r/postgres']),
            lambda x:x['columns'][key].__setitem__(12,None),
            lambda x:x['relations'][table].__setitem__(3,False),
            lambda x:x['memberships'].__setitem__('cp7_plan_writer:postgres:supabase_admin',[False,True,True]),
            lambda x:x['functions'].__setitem__('public.undeclared()',['body']),
        ]
        for mutate in mutations:
            changed=deepcopy(self.after);mutate(changed)
            with self.assertRaises(ValueError):stage.admit_transition(self.before,changed)
            with self.assertRaises(ValueError):product.admit_delta(stage,self.before,changed,dict(catalog=stage.own(changed)))

    def test_existing_column_grant_or_changed_owner_refused(self):
        key=next(iter(stage.COLUMNS));table=key.split(':')[0]
        for field,value in [('column',[]),('column',['another=r/'+stage.COLUMNS[key]]),('owner','postgres')]:
            before=deepcopy(self.before)
            if field=='column':before['columns'][key][12]=value
            else:before['relations'][table][0]=value
            with self.assertRaises(ValueError):stage.admit_transition(before,self.after)

    def test_installation_does_not_admit_rows_or_sequence_changes(self):
        before={'erp.journal_entries':[1,'unchanged'],'sequence:erp.nota':[2,True]}
        product._data_transition('RETENTION_REFERENCE_ACCESS',before,deepcopy(before))
        for key,value in [('erp.journal_entries',[2,'changed']),('sequence:erp.nota',[3,True])]:
            with self.assertRaises(ValueError):product._data_transition('RETENTION_REFERENCE_ACCESS',before,{**before,key:value})


if __name__=='__main__':unittest.main()
