"""Omitted fixture setup regression controls; simulated DB is not ERP evidence."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy,importlib.util,sys,unittest

HERE=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location('foundation_regression_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class Cursor:
    def __init__(self,f):
        self.f=f;self.users=0;self.owner=0;self.refs={n:False for n in f.REQUIRED}
        self.connection=SimpleNamespace(info=SimpleNamespace(host='127.0.0.1',port=54322))
        self.catalog={n:{} for n in load('final_gate').ALL22};self.usage=False;self.acl=('original ACL',)
        self.roles={'erp.app_roles':[{'role_code':'OWNER','is_active':True}],
            'erp.app_role_permissions':[{'permission_key':'synthetic-only'}]};self.writes=[];self.seed_count=0
    def execute(self,sql,args=None):
        if sql=='select current_database()':self.row=('cp6_rollback',)
        elif sql=='select count(*) from erp.app_users':self.row=(self.users,)
        elif sql=="select count(*) from erp.app_roles where role_code='OWNER'and is_active":self.row=(1,)
        elif 'where u.auth_user_id=%s' in sql:self.row=(self.owner,)
        elif sql.startswith('select exists(select 1 from '):
            table=sql.split(' from ',1)[1].split()[0]
            assert args==(self.f.REQUIRED[table],)
            self.row=(self.refs[table],)
        elif sql=="select nspacl::text from pg_namespace where nspname='erp'":self.row=self.acl
        elif sql.startswith('select coalesce(jsonb_agg'):
            self.row=(copy.deepcopy(self.roles[sql.split(' from ',1)[1].split()[0]]),)
        elif sql=="select has_schema_privilege('authenticated','erp','USAGE')":self.row=(self.usage,)
        elif sql=='grant usage on schema erp to authenticated':self.usage=True;self.writes.append(sql)
        else:raise AssertionError('UNEXPECTED_SQL:'+sql)
        return self
    def fetchone(self):return self.row
    def seed(self):
        self.seed_count+=1;self.users=1;self.owner=1;self.refs={n:True for n in self.refs}

@contextmanager
def catalog_scope(cur):yield

def run_prepare(f,cursor,seed=None):
    catalog=SimpleNamespace(_catalog_rows=lambda cur:copy.deepcopy(cur.catalog))
    product=SimpleNamespace(runtime=lambda:[catalog],verify=lambda cur,state:None)
    original=SimpleNamespace(admin=lambda cur:None,seed=seed or(lambda cur:cur.seed()))
    report={}
    with patch.dict(sys.modules,{'cp6_ao_ap_installed':original}):
        f.prepare(cursor,product,{},SimpleNamespace(product_catalog=catalog_scope),report)
    return report

class FixtureFoundationControls(unittest.TestCase):
    def test_original_seed_and_transitive_include_bytes_are_checked_without_ERP_import(self):
        value=load('foundation').preflight()
        self.assertEqual(value['seed'],'cp6_ao_ap_installed.seed');self.assertEqual(value['Native_case_credit'],0)
        self.assertEqual(len(value['files']),7)

    def test_empty_setup_seeds_once_existing_setup_never_reseeds(self):
        f=load('foundation');cur=Cursor(f)
        plan=f.check_before_install(cur);self.assertFalse(plan['database_mutated']);self.assertEqual(cur.writes,[])
        first=run_prepare(f,cur);self.assertTrue(first['seed_called']);self.assertEqual(cur.seed_count,1)
        second=run_prepare(f,cur);self.assertFalse(second['seed_called']);self.assertEqual(cur.seed_count,1)
        self.assertEqual(first['actual_all22_before'],first['actual_all22_after'])

    def test_nonempty_user_or_partial_master_state_refuses_before_any_seed_or_grant(self):
        for mutation in ('users_only','material_only','missing_material'):
            f=load('foundation');cur=Cursor(f)
            if mutation=='users_only':cur.users=1
            elif mutation=='material_only':cur.refs['erp.materials']=True
            else:cur.seed();cur.refs['erp.materials']=False
            before=cur.seed_count
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,'PARTIAL_OR_FOREIGN'):
                run_prepare(f,cur)
            self.assertEqual(cur.seed_count,before);self.assertEqual(cur.writes,[])

    def test_seed_must_actually_supply_every_master_and_owner(self):
        f=load('foundation');cur=Cursor(f)
        with self.assertRaisesRegex(ValueError,'COMPLETE_ORIGINAL_FOUNDATION'):
            run_prepare(f,cur,seed=lambda cur:None)
        self.assertEqual(cur.writes,[])

    def test_seed_cannot_leave_trigger_catalog_ACL_or_protected_role_changes(self):
        for mutation in ('trigger','ACL','role'):
            f=load('foundation');cur=Cursor(f)
            def seed(c):
                c.seed()
                if mutation=='trigger':c.catalog['triggers']['synthetic-not-restored']=['D']
                elif mutation=='ACL':c.acl=('changed ACL',)
                else:c.roles['erp.app_roles'][0]['is_active']=False
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):run_prepare(f,cur,seed)

    def test_remote_connection_and_untyped_state_are_refused(self):
        f=load('foundation');cur=Cursor(f);cur.connection.info.host='example.invalid'
        with self.assertRaisesRegex(ValueError,'LOCAL_DISPOSABLE'):f.check_before_install(cur)
        cur.connection.info.host='localhost';state=f.observe(cur);state['app_users']=False
        with self.assertRaisesRegex(ValueError,'TYPED'):f.classify(state)

    def test_final_gate_rejects_missing_changed_or_falsely_credited_foundation(self):
        spec=importlib.util.spec_from_file_location('focused_existing_synthetic_fixture',HERE/'test_followup.py')
        tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
        for mutation in ('missing','before','roles','source','credit','seed'):
            gate,p,*values=tests.fixture();part=values[0]['committed'][gate.CASE];setup=part['fixture_foundation']
            if mutation=='missing':part.pop('fixture_foundation')
            elif mutation=='before':values[0]['fixture_foundation_precheck']['initial']={'app_users':1}
            elif mutation=='roles':setup['protected_role_data_after']={'changed':[]}
            elif mutation=='source':setup['source']=dict(setup['source'],files={})
            elif mutation=='credit':setup['Native_case_credit']=1
            else:setup['seed_called']=False
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):gate.validate(*values,p)

if __name__=='__main__':unittest.main()
