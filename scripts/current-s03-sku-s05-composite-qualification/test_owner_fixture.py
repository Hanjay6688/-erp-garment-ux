"""Labelled fixture/source models, never Native or ERP business proof."""
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import importlib.util,json,subprocess,unittest,yaml

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('joined_owner_fixture_model',HERE/'owner_fixture.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
ROOT=HERE.parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location('owner_focus_control_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


class Cursor:
    def __init__(self,number=2,owner='owner1',cleanup=None,host='127.0.0.1'):
        self.connection=SimpleNamespace(info=SimpleNamespace(host=host,port=54322));self.cleanup=cleanup
        self.rows=[('id'+str(n),'owner'+str(n),True,'OWNER','role','OWNER',True)for n in range(1,number+1)]
        self.result=[];self.commands=[]
    def execute(self,sql,args=None):
        self.commands.append((sql,args))
        if sql=='select current_database()':self.result=[('cp6_rollback',)]
        elif sql.startswith('select session_user'):self.result=[('postgres',self.cleanup)]
        elif sql==helper.ROSTER:self.result=[r for r in self.rows if r[2]]
        elif sql==helper.ALL_TARGETS:self.result=list(self.rows)
        elif sql==helper.DEACTIVATE:
            self.result=[]
            for i,row in enumerate(self.rows):
                if row[0:2]==args and row[2]:
                    self.rows[i]=(row[0],row[1],False,*row[3:]);self.result=[(row[0],)]
        elif 'pg_advisory_xact_lock'in sql:self.result=[(None,)]
        else:raise AssertionError('UNDECLARED_MODEL_SQL:'+sql)
        return self
    def fetchone(self):return self.result[0]
    def fetchall(self):return deepcopy(self.result)


class OwnerFixtureControls(unittest.TestCase):
    def test_only_other_active_owner_flags_are_prepared_and_observed(self):
        for number in(1,2,4):
            with self.subTest(owners=number):
                cur=Cursor(number);original=deepcopy(cur.rows);events=[]
                helper.prepare_single_original_owner(cur,'owner1',events)
                self.assertEqual(cur.rows[0],original[0])
                self.assertEqual(cur.rows,[r if r[1]=='owner1'else(r[0],r[1],False,*r[3:])for r in original])
                self.assertEqual(len([x for x in cur.commands if x[0]==helper.DEACTIVATE]),number-1)
                self.assertIs(events[0]['original_last_owner_precondition_retained'],True)

    def test_missing_original_owner_refuses_before_any_update(self):
        cur=Cursor();before=deepcopy(cur.rows)
        with self.assertRaisesRegex(ValueError,'EXACT_ACTIVE_ORIGINAL'):helper.prepare_single_original_owner(cur,'missing',[])
        self.assertEqual(cur.rows,before);self.assertFalse(any(s==helper.DEACTIVATE for s,params in cur.commands))

    def test_synthetic_cleanup_escape_is_refused_before_any_update(self):
        cur=Cursor(cleanup='on');before=deepcopy(cur.rows)
        with self.assertRaisesRegex(ValueError,'NO_SYNTHETIC_CLEANUP'):helper.prepare_single_original_owner(cur,'owner1',[])
        self.assertEqual(cur.rows,before);self.assertFalse(any(s==helper.DEACTIVATE for s,params in cur.commands))

    def test_nonlocal_database_is_refused_before_any_statement(self):
        cur=Cursor(host='remote.example')
        with self.assertRaisesRegex(ValueError,'DISPOSABLE_DATABASE'):helper.prepare_single_original_owner(cur,'owner1',[])
        self.assertEqual(cur.commands,[])

    def test_private_source_preparation_keeps_original_single_owner_guard_and_callbacks(self):
        adapter,factory,proof=helper.prepared_sources()
        self.assertIn("if eligible!=[(owner,)]:",adapter)
        self.assertIn("lambda:cur.execute('update erp.app_users set is_active=false",adapter)
        self.assertIn("OWNER_ERROR,'42501'",adapter)
        self.assertIn('original_owner_fixture_observations',factory)
        self.assertEqual(proof['original_Native10_callback_changes'],0)
        compile(adapter,'owner-fixture-private-adapter','exec');compile(factory,'owner-fixture-private-factory','exec')

    def test_focused_component_and_whole_engine_only_select_the_one_original_callback(self):
        focus=load('owner_focus_native');text,proof=focus.prepared_sources()
        self.assertEqual(proof['original_business_callback_changes'],0)
        self.assertEqual(proof['planned_Native_cases'],1);self.assertIs(proof['whole_original_component_recovered'],True)
        self.assertIn("exact_group(actual, ('S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL',))",text)
        self.assertIn('__JOIN_FORCE_EXTRA_OWNER__(cursor,business,report)',text)
        raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        engine,scope=load('owner_focus_probe').derive(raw)
        self.assertIn("report['actual_Native_cases']=1",engine)
        self.assertIn("report['actual_browser_cases']=0",engine)
        self.assertIs(scope['whole_current_engine_recovered'],True)

    def test_focused_workflow_and_clock_match_and_original_full37_workflow_is_unchanged(self):
        record=json.loads((HERE/'OWNER_FOCUS_WORKFLOW_DERIVATION.json').read_bytes())
        original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',record['source_head']+':'+record['source_path']])
        self.assertEqual(original,(ROOT/record['source_path']).read_bytes())
        old=yaml.safe_load(original)['jobs']['p21']['steps']
        current=yaml.safe_load((ROOT/record['new_path']).read_bytes());job=current['jobs']['p21']
        self.assertEqual(current['on']['push']['branches'],['astra-a/s03-sku-owner-access-native1-20261031'])
        self.assertEqual(job['timeout-minutes'],90);self.assertEqual(sum(s in job['steps']for s in old),70)
        self.assertIn('owner_focus_attempt_policy.py --require-window',job['steps'][1]['run'])
        start=next(i for i,s in enumerate(job['steps'])if s.get('name')=='Start disposable database')
        self.assertTrue(any('owner_focus_probe.py --check'in s.get('run','')for s in job['steps'][:start]))
        policy=load('owner_focus_attempt_policy');self.assertEqual(policy.JOB_BUDGET_SECONDS,5400)
        original_policy=(ROOT/'scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py').read_bytes()
        self.assertEqual((HERE/'owner_focus_attempt_policy.py').read_bytes().replace(b'JOB_BUDGET_SECONDS = 90 * 60',b'JOB_BUDGET_SECONDS = 210 * 60',1),original_policy)
        boundary=datetime(2026,10,31,22,30,tzinfo=policy.WIB)
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):policy.require_window(boundary)
        self.assertEqual(policy.require_window(boundary-timedelta(seconds=1))['required_seconds'],5400)
        with self.assertRaisesRegex(ValueError,'AWARE'):policy.require_window(datetime(2026,10,31))


if __name__=='__main__':unittest.main()
