"""Pure census/history and closed-parent controls, not actual HTTP/race proof."""
from datetime import date
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock,patch
import copy,sys,unittest
from . import access_cases as cases,admission

def census():
    return dict(catalog={str(n):{}for n in range(22)},
        data_and_all_sequences={'erp.journal_lines':[2,'money'],'erp.app_users':[1,'actor'],
            'sequence:erp.audit_logs_id_seq':['10',True],
            'cp7_accessory_nonpayable.category_versions_v1':[1,'history'],
            'cp7_accessory_nonpayable.date_requests_v1':[1,'requests']},
        date_versions=[dict(id='v1',day='2026-11-01')],date_requests=[dict(request_id='r1',intent='old')])

class AccessPreparationControls(unittest.TestCase):
    def test_factories_remain_closed_before_any_connection_or_domain_import(self):
        for factory in(cases.http_cases,cases.races):
            with self.subTest(factory=factory.__name__),self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
                factory(object(),date(2026,11,1),state={})
        for name in('PARENT_HEAD','PARENT_TREE','PARENT_RUN','PARENT_JOB','PARENT_RECEIPT'):
            self.assertIsNone(getattr(admission,name))

    def test_full_census_refuses_unrelated_money_sequence_key_or_catalog_change(self):
        for mode in('money','sequence','extra_key','catalog','private_history'):
            before=census();after=copy.deepcopy(before)
            if mode=='money':after['data_and_all_sequences']['erp.journal_lines']=[2,'wrong']
            elif mode=='sequence':after['data_and_all_sequences']['sequence:erp.audit_logs_id_seq']=['11',True]
            elif mode=='extra_key':after['data_and_all_sequences']['erp.hidden']=[1,'unproven']
            elif mode=='catalog':after['catalog']['0']={'new':'grant'}
            else:after['date_requests'][0]['intent']='changed'
            with self.subTest(mode=mode),self.assertRaises(ValueError):cases.require_changes(before,after)
        before=census();self.assertEqual(cases.require_changes(before,copy.deepcopy(before)),[])
        after=copy.deepcopy(before);after['data_and_all_sequences']['cp7_accessory_nonpayable.date_requests_v1']=[2,'new']
        self.assertEqual(cases.require_changes(before,after,{'cp7_accessory_nonpayable.date_requests_v1'}),
            ['cp7_accessory_nonpayable.date_requests_v1'])

    def test_append_only_oracle_refuses_erased_changed_duplicate_or_extra_history(self):
        before=census();after=copy.deepcopy(before);after['date_versions'].append(dict(id='v2',day='2026-11-02'))
        cases.require_append(before,after,'date_versions','id',['v2'])
        for mode in('erased','changed','duplicate','extra'):
            bad=copy.deepcopy(after)
            if mode=='erased':bad['date_versions'].pop(0)
            elif mode=='changed':bad['date_versions'][0]['day']='2026-11-03'
            elif mode=='duplicate':bad['date_versions'].append(copy.deepcopy(bad['date_versions'][1]))
            else:bad['date_versions'].append(dict(id='v3',day='2026-11-04'))
            with self.subTest(mode=mode),self.assertRaises(ValueError):cases.require_append(before,bad,'date_versions','id',['v2'])

    def test_command_retains_exact_reviewed_actor_source_epoch_and_explicit_date(self):
        workspace=dict(actor='owner',access_epoch='epoch',current_source=dict(id='event',version='35'),timeline_token='timeline')
        body=cases.payload(workspace,date(2026,11,2),'Reviewed physical GOOD policy date')
        self.assertEqual(body,dict(contract_version='cp7.good-policy-date-command.v1',actor='owner',access_epoch='epoch',
            effective_from='2026-11-02',source_event_id='event',expected_current_version='35',
            expected_timeline='timeline',reason='Reviewed physical GOOD policy date',reviewed=True))

class ObservationAndWaitPreparationControls(unittest.TestCase):
    """Preparation/clock controls, not actual Auth, SQL, or two-session credit."""
    def test_observation_keeps_complete_census_and_refuses_any_raw_catalog_drift(self):
        groups=census()['catalog'];data=census()['data_and_all_sequences']
        catalog=SimpleNamespace(_catalog_rows=Mock(return_value=copy.deepcopy(groups)),
            _data=Mock(return_value=data))
        product=SimpleNamespace(runtime=lambda:(None,None,None,None,catalog),verify=Mock())
        modules=SimpleNamespace(product=product,control=SimpleNamespace(product_catalog=lambda cur:nullcontext()),
            bc=SimpleNamespace(api=SimpleNamespace(admin=lambda cur:None)))
        cur=SimpleNamespace(execute=Mock(return_value=SimpleNamespace(fetchall=lambda:[])))
        state={'after':copy.deepcopy(groups)}
        value=cases.capture_observed(cur,modules,state)
        self.assertEqual(value['catalog'],groups);self.assertEqual(value['data_and_all_sequences'],data)
        product.verify.assert_not_called()
        cases.capture(cur,modules,state);product.verify.assert_called_once_with(cur,state)
        for mode in('removed','changed','added'):
            bad=copy.deepcopy(groups)
            if mode=='removed':bad.pop('0')
            elif mode=='added':bad['23']={}
            else:bad['0']={'function':'changed'}
            catalog._catalog_rows.return_value=bad;catalog._data.reset_mock()
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'EXACT_INSTALLED_ALL22'):
                cases.capture_observed(cur,modules,state)
            catalog._data.assert_not_called()

    def test_race_preparation_finishes_before_live_command_timeout(self):
        test=self;contexts=[];active=False;payloads=[];counter=0
        workspace=dict(actor='owner',access_epoch='epoch',current_source=dict(id='event',version='1'),timeline_token='timeline')
        class LiveCommand(Exception):pass
        class PgError(Exception):pass
        class Cursor:
            def __init__(self,pid):self.pid=pid
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self,sql,args=None):
                if 'erp_cp7_get_good_policy_dates_v1'in sql:return SimpleNamespace(fetchone=lambda:(workspace,))
                if 'pg_backend_pid'in sql:return SimpleNamespace(fetchone=lambda:(self.pid,))
                if 'erp_cp7_save_good_policy_date_v1'in sql:
                    payloads.append(cases.json.loads(args[0]));raise LiveCommand('BEGIN_LIVE_COMMAND')
                return SimpleNamespace(fetchone=lambda:(None,))
        class Connection:
            def __init__(self,pid):self.cur=Cursor(pid)
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def cursor(self):return self.cur
            def commit(self):pass
            def rollback(self):pass
        def connect(**kwargs):
            nonlocal counter
            counter+=1;return Connection(counter)
        modules=SimpleNamespace(master=SimpleNamespace(role_actor=lambda cur,role:'owner'),
            bc=SimpleNamespace(session=lambda cur,subject:None,api=SimpleNamespace(admin=lambda cur:None)))
        def context(cur,state,mode):
            test.assertFalse(active,'Source preparation happened after the live timeout began')
            contexts.append(cur.pid);return modules
        class Future:
            def __init__(self,fn,args):self.fn=fn;self.args=args
            def result(self,timeout):test.assertEqual(timeout,25);return self.fn(*self.args)
        class Pool:
            def __init__(self,max_workers):test.assertEqual(max_workers,2)
            def __enter__(self):
                nonlocal active
                test.assertEqual(len(contexts),3);active=True;return self
            def __exit__(self,*args):
                nonlocal active
                active=False;return False
            def submit(self,fn,*args):return Future(fn,args)
        def wait(timeout):test.assertEqual(timeout,8)
        with patch.object(cases,'context',side_effect=context),patch.object(cases,'capture',return_value=census()),\
            patch.object(cases,'ThreadPoolExecutor',Pool),patch.object(cases,'Barrier',return_value=SimpleNamespace(wait=wait)),\
            patch.dict(sys.modules,{'psycopg':SimpleNamespace(Error=PgError)}):
            with self.assertRaisesRegex(LiveCommand,'BEGIN_LIVE_COMMAND'):
                cases.race(SimpleNamespace(connect=connect),date(2026,11,3),{},same_request=True)
        self.assertEqual(len(contexts),3)
        self.assertEqual(payloads[0]['effective_from'],'2026-11-04')

    def test_http_wait_prepares_observer_before_lock_and_captures_before_release(self):
        test=self;locked=False;active_user=True;contexts=[];connections=0;write_days=[]
        workspace=dict(actor='owner',access_epoch='epoch',current_source=dict(id='event',version='1'),timeline_token='timeline')
        class User:
            auth_user_id='actual-test-subject-placeholder'
            def rpc(self,name,args):
                if name==cases.READ:return dict(status=200,body=workspace)
                write_days.append(args['p_payload']['effective_from'])
                if len(write_days)==1:return dict(status=200,body=dict(status='SAVED'))
                test.assertFalse(locked);test.assertFalse(active_user)
                return dict(status=403,body=dict(code='42501',message='NONPAYABLE_SETTINGS_DENIED'))
        class Cursor:
            def __init__(self,number):self.number=number
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self,sql,args=None):
                nonlocal locked,active_user
                one=None;many=[]
                if 'pg_backend_pid'in sql:one=(101,)
                elif 'pg_advisory_xact_lock'in sql:locked=True
                elif 'pg_stat_activity'in sql:many=[(202,'Lock','advisory',cases.WRITE)]
                elif 'select u.id::text'in sql:one=('owner-app',active_user,'OWNER')
                elif 'update erp.app_users'in sql:active_user=False
                return SimpleNamespace(fetchone=lambda:one,fetchall=lambda:many)
        class Connection:
            def __init__(self,number):self.number=number;self.cur=Cursor(number)
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def cursor(self):return self.cur
            def commit(self):pass
            def rollback(self):
                nonlocal locked
                if self.number==0:locked=False
        def connect(**kwargs):
            nonlocal connections
            result=Connection(connections);connections+=1;return result
        modules=SimpleNamespace(bc=SimpleNamespace(api=SimpleNamespace(admin=lambda cur:None)))
        def context(cur,state,mode):
            test.assertFalse(locked,'Heavy verification happened inside the live wait')
            contexts.append(cur.number);return modules
        revoked=census()
        def observe(*args):test.assertTrue(locked);test.assertFalse(active_user);return revoked
        def after(*args):test.assertFalse(locked);return revoked
        class Future:
            def __init__(self,fn,args):self.fn=fn;self.args=args
            def done(self):return False
            def result(self,timeout):test.assertEqual(timeout,25);return self.fn(*self.args)
        class Pool:
            def __init__(self,max_workers):test.assertEqual(max_workers,1)
            def __enter__(self):test.assertEqual(len(contexts),2);return self
            def __exit__(self,*args):return False
            def submit(self,fn,*args):return Future(fn,args)
        http=SimpleNamespace(login=lambda *args:User(),connect=connect)
        with patch.object(cases,'context',side_effect=context),patch.object(cases,'capture_observed',side_effect=observe),\
            patch.object(cases,'http_capture',side_effect=after),patch.object(cases,'ThreadPoolExecutor',Pool),\
            patch.object(cases,'retain',return_value=dict(status='LOCAL_CONTROL_ONLY')):
            result=cases.http_revoke_wait(http,date(2026,11,3),{})
        self.assertEqual(contexts,[0,1]);self.assertEqual(write_days,['2026-11-05','2026-11-05'])
        self.assertFalse(locked);self.assertEqual(result['actual_refusal_after_wait']['body']['code'],'42501')

if __name__=='__main__':unittest.main()

