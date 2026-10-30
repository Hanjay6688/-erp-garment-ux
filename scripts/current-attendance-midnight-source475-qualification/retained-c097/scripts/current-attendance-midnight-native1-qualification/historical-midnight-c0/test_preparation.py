"""Pure/local-model controls only; no DB, server, Auth or Native execution."""
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


m=load('s03_midnight_local_controls',HERE/'cases.py')
o=m.oracle
a=m.admission


def models():
    p=o.fixed_plan(date(2026,10,29))
    source=dict(day=date(2026,10,24),contractor='CID',capture=dict(source_binding='a'*64,
        native_manifest=dict(period_start='2026-10-24',period_end='2026-10-24',numerator_cents=100003,
        denominator_qty=0,sources=[dict(contractor_id='CID',payroll_id='PAYROLL',policy_version_id='POLICY',
        original_debit_journal_line_id='ORIGINAL_DEBIT',attendance_amount_cents=100003)],destinations=[])))
    events=[]
    for label,key,day in(('BEFORE','before_us',p['left']),('AFTER','after_us',p['right'])):
        events.append(dict(event_id='EVENT_'+label,work_id='WORK_'+label,po_id='PO',group_id='GROUP',
            contractor_id='CID',work_contractor_id='CID',kind='SELESAI_DIJAHIT',qty=5,work_status='POSTED',
            event_epoch_us=p[key],work_epoch_us=p[key],wib_day=str(day),utc_day=str(p['left'])))
    return p,source,events,dict(decision_id='DECISION')


def preview_model(source,decision,start,end,events):
    dest=[dict(sewing_terminal_event_id=e['event_id'],source_work_completion_id=e['work_id'],contractor_id='CID',
        po_id='PO',cutting_group_id='GROUP',physical_at_epoch_us=e['event_epoch_us'],sewing_qty=5,policy_version_id='POLICY',
        contractor_role_snapshot='MANDOR',attendance_required_snapshot=True,is_special_snapshot=False)for e in events]
    native=dict(period_start=str(start),period_end=str(end),numerator_cents=0,denominator_qty=len(events)*5,sources=[],destinations=dest)
    carried=dict(status='READY',manifest=dict(period_start=str(source['day']),period_end=str(source['day']),
        output_start=str(start),output_end=str(end),decision_id='DECISION',source_binding='a'*64,
        numerator_cents=100003,denominator_qty=len(events)*5,sources=source['capture']['native_manifest']['sources'],
        source_native_manifest=source['capture']['native_manifest'],destinations=dest,
        output_destination_facts=dict(destinations=dest,denominator_qty=len(events)*5)))
    public=dict(action='ALLOCATE',decision_id='DECISION',payload=dict(period_start=str(source['day']),period_end=str(source['day']),
        output_start=str(start),output_end=str(end)),amount_cents='100003',amount='1000.03',source_count='1',
        denominator_qty=str(len(events)*5),source_binding='a'*64,economic_date=str(end),can_apply=True,business_DML=False)
    return native,carried,public


class ZoneCursor:
    def __init__(self):self.zone='Asia/Jakarta';self.commands=[];self.result=None;self.failed=False
    def execute(self,statement,args=()):
        self.commands.append((statement,args))
        if self.failed and not statement.startswith('rollback to savepoint '):raise RuntimeError('MODEL_SQL_TRANSACTION_ABORTED')
        if statement.startswith('rollback to savepoint '):self.failed=False
        if statement=='show TimeZone':self.result=self.zone
        if "set_config('TimeZone','UTC'"in statement:self.zone='UTC';self.result=self.zone
        if "set_config('TimeZone',%s"in statement:self.zone=args[0];self.result=self.zone
        return self
    def fetchone(self):return(self.result,)


class OracleControls(unittest.TestCase):
    def test_fixed_dates_and_one_microsecond_pair_straddle_WIB_not_UTC_day(self):
        for today in(date(2026,10,29),date(2024,3,3),date(2026,1,2)):
            p=o.fixed_plan(today)
            self.assertEqual(p['after_us']-p['before_us'],1)
            self.assertEqual(p['before'].date(),p['after'].date())
            self.assertNotEqual(p['before'].astimezone(o.WIB).date(),p['after'].astimezone(o.WIB).date())
            self.assertEqual((p['after'].hour,p['after'].minute,p['after'].second),(17,0,0))
    def test_naive_or_non_date_fixture_clock_is_refused(self):
        with self.assertRaisesRegex(ValueError,'AWARE_INSTANT'):o.epoch_us(datetime(2026,10,29))
        with self.assertRaisesRegex(ValueError,'BUSINESS_TODAY_DATE'):o.fixed_plan(datetime(2026,10,29))
    def test_exact_two_posted_native_facts_same_source_contractor_are_required(self):
        p,s,e,_=models();o.assert_events(e,p,s)
        for key,value in(('contractor_id','OTHER'),('work_contractor_id','OTHER'),('qty',10),('work_status','DRAFT'),('event_epoch_us',p['before_us']+1000)):
            bad=deepcopy(e);bad[0][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):o.assert_events(bad,p,s)
    def test_three_exact_destination_sets_keep_one_original_source_budget(self):
        p,s,e,d=models();o.assert_events(e,p,s)
        for start,end,events,den in((p['left'],p['left'],e[:1],5),(p['right'],p['right'],e[1:],5),(p['left'],p['right'],e,10)):
            n,c,u=preview_model(s,d,start,end,events)
            self.assertEqual(o.assert_manifest(n,c,u,s,d,start,end,events)['denominator'],den)
    def test_UTC_day_filter_or_wrong_policy_or_wrong_source_is_detected(self):
        p,s,e,d=models();n,c,u=preview_model(s,d,p['left'],p['left'],e[:1])
        for mutation in('UTC_BOTH','POLICY','SOURCE','EPOCH'):
            nn,cc,uu=deepcopy((n,c,u))
            if mutation=='UTC_BOTH':nn['destinations']+=preview_model(s,d,p['right'],p['right'],e[1:])[0]['destinations'];nn['denominator_qty']=10
            if mutation=='POLICY':nn['destinations'][0]['policy_version_id']='UNBOUND_POLICY'
            if mutation=='SOURCE':cc['manifest']['numerator_cents']=100004
            if mutation=='EPOCH':nn['destinations'][0]['physical_at_epoch_us']+=1
            with self.subTest(mutation=mutation),self.assertRaises(AssertionError):o.assert_manifest(nn,cc,uu,s,d,p['left'],p['left'],e[:1])
    def test_public_closed_wire_budget_scope_and_private_context_are_checked(self):
        p,s,e,d=models();n,c,u=preview_model(s,d,p['left'],p['right'],e)
        for key,value in(('context',{}),('amount_cents','100004'),('denominator_qty','20'),('business_DML',True),('source_binding','b'*64)):
            bad=deepcopy(u);bad[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):o.assert_manifest(n,c,bad,s,d,p['left'],p['right'],e)


class ApiControls(unittest.TestCase):
    def test_timezone_is_UTC_inside_and_original_zone_restored_on_success(self):
        cur=ZoneCursor()
        with m.timezone_restored(cur)as original:self.assertEqual((original,cur.zone),('Asia/Jakarta','UTC'))
        self.assertEqual(cur.zone,'Asia/Jakarta')
        self.assertFalse(any(sql.startswith('rollback')for sql,_ in cur.commands))
    def test_SQL_error_rolls_back_zone_scope_restores_and_preserves_original_error(self):
        cur=ZoneCursor()
        with self.assertRaisesRegex(RuntimeError,'MODEL_NATIVE_FAILURE'):
            with m.timezone_restored(cur):cur.failed=True;raise RuntimeError('MODEL_NATIVE_FAILURE')
        self.assertEqual(cur.zone,'Asia/Jakarta')
        self.assertTrue(any(sql.startswith('rollback to savepoint ')for sql,_ in cur.commands))
    def test_contractor_fixture_value_restores_even_when_native_chain_refuses(self):
        prod=SimpleNamespace(CONTRACTOR='PREEXISTING_CID')
        src=SimpleNamespace(chain=SimpleNamespace(production=prod),two_size_fixture=lambda *args,**kwargs:(_ for _ in()).throw(RuntimeError('MODEL_NATIVE_DATE_REFUSAL')))
        f=SimpleNamespace(hp=SimpleNamespace(cp17=lambda:SimpleNamespace(instal=SimpleNamespace(wip_source=SimpleNamespace(b=src)))))
        p,s,_,_=models()
        with self.assertRaisesRegex(RuntimeError,'MODEL_NATIVE_DATE_REFUSAL'):m.output_pair(None,f,s,p)
        self.assertEqual(prod.CONTRACTOR,'PREEXISTING_CID')
    def test_occupied_fixed_pair_refuses_before_any_fixture_and_has_no_retry(self):
        cur=ZoneCursor();calls=[]
        with patch.object(m,'one',return_value=True):
            with self.assertRaisesRegex(ValueError,'FIXED_QUIET_PAIR_UNAVAILABLE'):m.require_quiet_fixed_days(cur,SimpleNamespace(admin=lambda c:calls.append('admin')),models()[0])
        self.assertEqual(calls,['admin'])
        text=(HERE/'cases.py').read_text()
        for banned in('session_replication_role','update erp.','delete from erp.','setval('):self.assertNotIn(banned,text.lower())
    def test_no_accepted_original_pin_refuses_before_cursor_or_product_import(self):
        class NoCursor:
            def __getattr__(self,key):raise AssertionError('LOCAL_CONTROL_MUST_NOT_TOUCH_CURSOR:'+key)
        with patch.object(m,'originals',side_effect=AssertionError('NO_PRODUCT_IMPORT_BEFORE_GATE')):
            with self.assertRaisesRegex(ValueError,'RETAINED_NATIVE11_PIN_PENDING'):
                m.cases(NoCursor(),date(2026,10,29),state={},evidence={},fresh_original11={},retained_original={})
    def test_factory_declares_one_additional_case_without_running_fixture(self):
        verify_calls=[];original=SimpleNamespace(f=SimpleNamespace(composition=SimpleNamespace(verify=lambda cur,state:verify_calls.append(state)or{'model_only':True})))
        with patch.object(m.admission,'admit',return_value={'MODEL_ONLY_NOT_ACTUAL':True}),patch.object(m,'originals',return_value=original),patch.object(m,'run_boundary',side_effect=AssertionError('NO_FIXTURE_DURING_DECLARATION')):
            result=m.cases(None,date(2026,10,29),state={'sources':'LOCAL_MODEL'},evidence={},fresh_original11={},retained_original={})
        self.assertEqual([name for name,_ in result],[m.ID]);self.assertTrue(callable(result[0][1]));self.assertEqual(len(verify_calls),1)


class AdmissionControls(unittest.TestCase):
    def group(self):return dict(status='PASS',planned_case_ids=list(a.original_ids()),complete_boundary_restored=True,
        counts=dict(PASS=11,FAIL=0,INCOMPLETE=0),cases={key:dict(status='PASS')for key in a.original_ids()})
    def test_original11_exact_ids_integer_counts_and_failures_are_closed(self):
        ids=a.original_ids();group=self.group();a.admit_group(group,ids)
        for kind in('missing','fail','count','bool','status','plan','boundary'):
            bad=deepcopy(group)
            if kind=='missing':bad['cases'].pop(ids[0])
            if kind=='fail':bad['cases'][ids[0]]['status']='INCOMPLETE'
            if kind=='count':bad['counts']['PASS']=10
            if kind=='bool':bad['counts']['FAIL']=False
            if kind=='status':bad['status']='INCOMPLETE'
            if kind=='plan':bad['planned_case_ids']=bad['planned_case_ids'][:-1]
            if kind=='boundary':bad['complete_boundary_restored']=False
            with self.subTest(kind=kind),self.assertRaises(ValueError):a.admit_group(bad,ids)
    def test_all80_frozen_files_and_exact_own_sources_are_bound(self):
        manifest=a.sources();self.assertEqual(len(manifest['frozen_component_and_original11_files']),80)
        with TemporaryDirectory()as directory:
            root=Path(directory);own=root/'new'
            own.mkdir()
            for name in a.OWN_FILES:(own/name).write_bytes((HERE/name).read_bytes())
            for name in manifest['frozen_component_and_original11_files']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((a.ROOT/name).read_bytes())
            path=own/'SOURCE.json';path.write_text(json.dumps(manifest));a.sources(root,path)
            target=root/'scripts/current-attendance-period-choice-qualification/cases.py';target.write_text(target.read_text()+'\n# mutation control\n')
            with self.assertRaisesRegex(ValueError,'FROZEN_FILE_CHANGED'):a.sources(root,path)
            target.write_bytes((a.ROOT/'scripts/current-attendance-period-choice-qualification/cases.py').read_bytes())
            (own/'oracle.py').write_text('mutated source')
            with self.assertRaisesRegex(ValueError,'OWN_FILE_CHANGED'):a.sources(root,path)
    def test_retained_raw_and_package_gate_positive_and_negative_models(self):
        # Deliberate disposable LOCAL MODELS, not fabricated qualification evidence.
        group=self.group();source={'LOCAL_MODEL_NOT_CURRENT_INSTALLATION':True}
        doc=dict(status='PASS',classification='LOCAL_MODEL_ONLY',actual_Native_cases=11,qualification_commit='MODEL_COMMIT',
                 original11=group,source=source,**{field:True for field in a.ORIGINAL_GATES})
        package=dict(status='ALL_STAGES_INSTALLED',classification='LOCAL_MODEL_ONLY',gate={key:True for key in a.PACKAGE_GATES})
        with TemporaryDirectory()as directory:
            native=Path(directory)/'model-native.json';pkg=Path(directory)/'model-package.json'
            def pin(path,document):
                raw=json.dumps(document).encode();path.write_bytes(raw);return dict(encoding='raw',raw_bytes=len(raw),raw_sha256=a.sha(raw))
            np=pin(native,doc);np.update(qualification_commit='MODEL_COMMIT',Native_group_path=['original11'],installation_source_path=['source'])
            pp=pin(pkg,package);manifest=dict(accepted_original11=np,accepted_package_original=pp)
            with patch.object(a,'sources',return_value=manifest):
                result=a.admit(group,{'native':native,'package':pkg},state_sources=source)
                self.assertEqual(result['additional_Native_credit_before_execution'],0)
                with self.assertRaisesRegex(ValueError,'INSTALLATION_SOURCE_CHANGED'):a.admit(group,{'native':native,'package':pkg},state_sources={'changed':True})
                native.write_bytes(native.read_bytes()+b' ')
                with self.assertRaisesRegex(ValueError,'RETAINED_RAW_CHANGED'):a.admit(group,{'native':native,'package':pkg},state_sources=source)
                pin(native,doc)
                bad=deepcopy(package);bad['gate']['backup_restore_drill']=False;manifest['accepted_package_original']=pin(pkg,bad)
                with self.assertRaisesRegex(ValueError,'PACKAGE5_REQUIRED'):a.admit(group,{'native':native,'package':pkg},state_sources=source)


if __name__=='__main__':unittest.main()
