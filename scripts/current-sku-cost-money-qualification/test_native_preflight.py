"""Control prerequisite aggregation and transaction recovery; no ERP execution."""
from datetime import date,datetime,timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import importlib.util
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('money_native_preflight_under_test',HERE/'native_preflight.py')
subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
TODAY=date(2026,11,4)


class ModeledSQLFailure(Exception):
    sqlstate='42501'


class CursorModel:
    """Explicit protocol responses, never claims to evaluate PostgreSQL or ACLs."""
    def __init__(self):
        self.actor='admin';self.seen=[];self.rows=[];self.aborted=False;self.savepoints=[]
        self.functions=set(subject.REQUIRED_FUNCTIONS);self.denied=set();self.permissions=set()
        self.fail_actor=None;self.now=datetime(2026,11,4,9,tzinfo=ZoneInfo('Asia/Jakarta'))
        self.pcs=[('PCS',)];self.accounts={code:[(True,True,'REVENUE')]for code in('4100','5100')}
        self.location=(True,'FG_WAREHOUSE');self.master=(True,)*5
        self.mappings={key:[(True,True)]for key in subject.ACCOUNT_MAPPINGS}
        self.period=[(TODAY-timedelta(days=12),)]
        self.database_roles={name:('authenticated','authenticated')for name in subject.ACTOR_FUNCTIONS}

    def execute(self,sql,params=()):
        text=' '.join(sql.split());self.seen.append((self.actor,text,params))
        if text.startswith('rollback to savepoint '):
            self.aborted=False;self.actor=self.savepoints[-1];self.rows=[];return self
        if self.aborted:raise AssertionError('failed actor left transaction aborted')
        if text.startswith('savepoint '):self.savepoints.append(self.actor);self.rows=[]
        elif text.startswith('release savepoint '):self.savepoints.pop();self.rows=[]
        elif text=='select clock_timestamp()':self.rows=[(self.now,)]
        elif text.startswith('select to_regprocedure('):self.rows=[(params[0]in self.functions,)]
        elif text.startswith('select unit_code '):self.rows=self.pcs
        elif text.startswith('select is_active,is_postable,account_type'):self.rows=self.accounts[params[0]]
        elif text.startswith('select is_active,location_type '):self.rows=[self.location]if self.location else []
        elif 'from erp.accounting_account_mappings m' in text:self.rows=self.mappings[params[0]]
        elif 'from erp.products where id='in text:self.rows=[self.master]if self.master else []
        elif text.startswith('select closed_through '):self.rows=self.period
        elif text.startswith('select erp.has_permission('):
            if self.actor==self.fail_actor:
                self.aborted=True;raise ModeledSQLFailure('modeled permission read refusal')
            self.rows=[((self.actor,params[0])not in self.permissions,)]
        elif text.startswith('select has_schema_privilege(current_user,'):
            self.rows=[((self.actor,params[1])not in self.denied,)]
        elif text=='select erp.current_app_role()::text':self.rows=[('OWNER',)]
        elif text=='select current_user,session_user':self.rows=[self.database_roles[self.actor]]
        else:raise AssertionError('unmodeled query: '+text)
        return self

    def fetchone(self):return self.rows[0]if self.rows else None
    def fetchall(self):return self.rows


def business(cursor,changed_census=False):
    selected=[];captures=[]
    def choose(name):
        def select(cur):
            assert cur is cursor;selected.append(name);cur.actor=name
        return select
    def admin(cur):
        assert not cur.aborted;cur.actor='admin'
    def capture(cur):
        admin(cur);captures.append(cur.actor)
        return dict(catalog='explicit modeled census',data_and_sequences=2 if changed_census and len(captures)>1 else 1)
    n=SimpleNamespace(require_local=lambda cur:None,capture=capture,
        bc=SimpleNamespace(session=choose('accessory_operator')))
    f=SimpleNamespace(admin=admin,owner=choose('conversion_and_owner_native'),
        BASE=SimpleNamespace(LOCATION='fixture-location',BASE_PRODUCT='fixture-master'))
    actor=choose('sales_owner')
    moving=SimpleNamespace(sales_cmd=SimpleNamespace(auth=SimpleNamespace(actor=lambda cur,_:actor(cur))))
    return SimpleNamespace(n=n,f=f,moving=moving),selected,captures


class PrerequisiteAggregation(unittest.TestCase):
    def test_superuser_or_maintenance_context_cannot_pass_as_a_business_actor(self):
        cur=CursorModel()
        for name,role in zip(subject.ACTOR_FUNCTIONS,('postgres','service_role','cp6_maintenance_admission')):
            cur.database_roles[name]=(role,role)
        fixtures,selected,captures=business(cur)
        proof=subject.check(cur,TODAY,fixtures)
        self.assertEqual(proof['status'],'REFUSED')
        self.assertEqual(set(proof['errors']),{'ORDINARY_AUTHENTICATED_ACTOR_REQUIRED:'+name for name in subject.ACTOR_FUNCTIONS})
        self.assertEqual(selected,list(subject.ACTOR_FUNCTIONS));self.assertEqual(len(captures),2)
        self.assertEqual(cur.actor,'admin');self.assertEqual(cur.savepoints,[])
        self.assertTrue(all(row['role']=='OWNER'for row in proof['actors'].values()))
        self.assertTrue(all(v for row in proof['actors'].values()for v in row['direct_call_capabilities'].values()))

    def test_complete_direct_call_surface_is_checked_for_all_three_actors(self):
        cur=CursorModel();fixtures,selected,captures=business(cur)
        proof=subject.check(cur,TODAY,fixtures)
        self.assertEqual(proof['status'],'PASS');self.assertEqual(proof['errors'],[])
        self.assertEqual(len(proof['functions']),23)
        self.assertEqual(selected,list(subject.ACTOR_FUNCTIONS))
        self.assertEqual(sum(len(v['direct_call_capabilities'])for v in proof['actors'].values()),19)
        self.assertTrue(all(v for row in proof['actors'].values()for v in row['direct_call_capabilities'].values()))
        self.assertEqual(len(captures),2);self.assertEqual(cur.savepoints,[])
        self.assertEqual(cur.actor,'admin');self.assertEqual(proof['actual_ERP_cases'],0)

    def test_independent_function_actor_master_account_and_date_faults_are_reported_together(self):
        cur=CursorModel();fixtures,selected,_=business(cur)
        missing='public.erp_cp7_get_sales_returns_v1(jsonb)';cur.functions.remove(missing)
        denied='public.erp_save_accessory_service_action_v1(text,jsonb,uuid)'
        cur.denied.add(('accessory_operator',denied))
        permission='warehouse.brand_conversion.post';cur.permissions.add(('conversion_and_owner_native',permission))
        cur.pcs=[];cur.accounts['4100']=[(False,True,'REVENUE')]
        cur.location=None;cur.master=None;cur.mappings['COGS']=[];cur.period=[(TODAY,)]
        cur.now=datetime(2026,11,5,0,2,tzinfo=ZoneInfo('Asia/Jakarta'))
        proof=subject.check(cur,TODAY,fixtures)
        expected={
            'MISSING_FUNCTION:'+missing,'ACTOR_FUNCTION_CAPABILITY:sales_owner:'+missing,
            'ACTOR_FUNCTION_CAPABILITY:accessory_operator:'+denied,
            'ACTOR_PERMISSION:conversion_and_owner_native:'+permission,
            'ONE_ACTIVE_COUNT_PCS_REQUIRED','ACCOUNT_NOT_ACTIVE_POSTABLE:4100',
            'CANONICAL_ACTIVE_FG_WAREHOUSE_REQUIRED','CANONICAL_ACTIVE_EFFECTIVE_PRODUCT_MASTER_REQUIRED',
            'ACTIVE_POSTABLE_ACCOUNT_MAPPING_REQUIRED:COGS','EARLIEST_OPENING_FIXTURE_DAY_NOT_OPEN',
            'PLANNED_BUSINESS_DAY_CHANGED','POSITIVE_FIXTURE_WOULD_CROSS_WIB_DAY',
        }
        self.assertEqual(proof['status'],'REFUSED');self.assertEqual(set(proof['errors']),expected)
        self.assertEqual(selected,list(subject.ACTOR_FUNCTIONS));self.assertFalse(cur.aborted)
        self.assertFalse(any(params and params[-1]==missing for _,sql,params in cur.seen
            if sql.startswith('select has_schema_privilege(current_user,')))

    def test_failed_actor_transaction_recovers_before_other_actors_and_census(self):
        cur=CursorModel();cur.fail_actor='conversion_and_owner_native'
        fixtures,selected,captures=business(cur,changed_census=True)
        proof=subject.check(cur,TODAY,fixtures)
        self.assertEqual(proof['status'],'REFUSED')
        self.assertEqual(set(proof['errors']),{'ACTOR_CHECK_REFUSED:conversion_and_owner_native',
            'READ_ONLY_PREFLIGHT_CHANGED_CATALOG_ROWS_OR_SEQUENCES'})
        self.assertEqual(proof['actors']['conversion_and_owner_native']['sqlstate'],'42501')
        self.assertEqual(selected,list(subject.ACTOR_FUNCTIONS));self.assertEqual(len(captures),2)
        self.assertTrue(proof['actors']['accessory_operator']['direct_call_capabilities'])
        self.assertTrue(proof['actors']['sales_owner']['direct_call_capabilities'])
        self.assertEqual(cur.actor,'admin');self.assertEqual(cur.savepoints,[]);self.assertFalse(cur.aborted)


if __name__=='__main__':unittest.main()
