"""Source/budget/false-credit controls only. Synthetic gate values are not ERP proof."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from unittest.mock import patch
import copy,importlib.util,json,socket,subprocess,unittest,yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-s03-sku-s05-composite-qualification'

def load(name,path=None):
    spec=importlib.util.spec_from_file_location('focused_local_control_'+name,path or HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def fixture():
    gate=load('final_gate');p=load('typed',PARENT/'parents.py')
    ids=['S05_SKU_NORMAL_APP_DESKTOP_SOURCE_AND_LATE_REPLY','S05_SKU_NORMAL_APP_MOBILE390_UNKNOWN_ZERO_AND_CURRENT_ACCESS']
    proof={'receipt':{'missing_case_ids':ids},'synthetic_gate_fixture_not_actual_runtime':True}
    catalog={k:{}for k in gate.ALL22};catalog['relations']={'erp.synthetic':['synthetic','r']}
    catalog['sequences']={f'erp.synthetic_{i}':[]for i in range(15)}
    data={'erp.synthetic':[0,'0'*64],**{'sequence:'+n:['0',False]for n in catalog['sequences']}}
    boundary=dict(actual_all22=catalog,full_data_and_sequences=data)
    browser=dict(status='RUN_COMPLETE',counts={'PASS':2},planned_case_ids=ids,real_auth=True,
        jwt_signed_by_runtime=False,host_exit=0,host_status='RUN_COMPLETE',database_remaining=0,console_errors=0,
        auth_cleanup_failures=[],session_leaks=[],auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True),
        cases={name:dict(status='PASS')for name in ids},script_sha256=sha256((PARENT/'browser.mjs').read_bytes()).hexdigest())
    fresh=dict(status='PASS',actual_browser_cases=2,actual_Native_cases=0,browser=browser,
        reader_post_browser_inverse={'synthetic':True},copy_catalog_admissions=[dict(all22_groups_equal_original_install=True)])
    component=dict(status='PASS',business_counts={'PASS':2},business_cases={name:dict(status='PASS')for name in ids},
        actual_Native_cases=0,actual_browser_cases=2,retained_Native_cases=31,retained_S03_browser_cases=4,
        retained_case_count=35,candidate_case_coverage=37,retained_cases_are_not_fresh=True,
        used_guard_refused_before_DDL=True,Afui_positive_HPP_zero_reimbursement_coverage=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False,
        retained35=proof,fresh_S05_browser2=fresh,used_inverse_refusal_before=boundary,
        used_inverse_refusal_after=copy.deepcopy(boundary))
    head='f'*40
    main=dict(status='PASS',qualification_commit=head,required_case_ids=[gate.CASE],required_case_ids_pass=True,
        actual_Native_cases=0,actual_browser_cases=2,actual_business_cases=2,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        retained_Native_cases=31,retained_S03_browser_cases=4,retained_cases_are_not_fresh=True,
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False,committed={gate.CASE:component},
        baseline_role_cleanup=dict(baseline_roles_exact=True),baseline_restore=dict(unexplained=[],
            only_pg_cron_errors=True,database_owner_acl_and_settings_preserved=True))
    package=dict(gate=dict(p.GATES),run_identity=dict(tool_head=head,github_sha=head,run_attempt='1',run_id='synthetic-only'))
    backup=dict(status='RESTORED_IDENTICAL',checks={k:True for k in
        ('restore_errors_only_pg_cron','catalog_explained','data_identical','engine_answer_present','engine_equal')},data={'differ':{}})
    supervision=dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,github_run_attempt='1',
        worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,signals=[],process_group_empty=True,
        process_tree_empty=True,job_budget_seconds=7200,work_budget_seconds=5400,recovery_reserve_seconds=1200,
        artifact_reserve_seconds=600,actual_case_credit=0,production_go=False,github_run_id='synthetic-only')
    return gate,p,main,package,backup,supervision,head,proof

class FocusedControls(unittest.TestCase):
    def test_workflow_keeps_all_unchanged_setup_restore_and_bounded_job_routing(self):
        record=json.loads((HERE/'WORKFLOW_ORIGIN.json').read_bytes())
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',record['source_commit']+':'+record['source_path']])
        self.assertEqual(sha256(raw).hexdigest(),record['source_sha256'])
        before=yaml.safe_load(raw);current=yaml.safe_load((ROOT/'.github/workflows/cp7-s05-css-followup.yml').read_bytes())
        a=before['jobs']['p21'];b=current['jobs']['p21']
        self.assertEqual(len(a['steps']),77);self.assertEqual(len(b['steps']),77)
        self.assertEqual(b['timeout-minutes'],120);self.assertEqual(b['env'],a['env'])
        self.assertEqual(current['permissions'],before['permissions'])
        self.assertEqual(current['on']['push']['branches'],['astra-a/s05-css-followup-20261101'])
        self.assertEqual(b['if'],"github.ref == 'refs/heads/astra-a/s05-css-followup-20261101'")
        changed=[i for i,(x,y)in enumerate(zip(a['steps'],b['steps']))if x!=y]
        self.assertEqual(changed,record['changed_steps']);self.assertEqual(len(record['unchanged_steps']),69)
        for index in record['unchanged_steps']:self.assertEqual(a['steps'][index],b['steps'][index])
        run=b['steps'][70]['run']
        self.assertIn('current-s05-css-followup-qualification/runtime_supervisor.py',run)
        self.assertIn('current-s05-css-followup-qualification/final_gate.py',run)
        self.assertNotIn('current-s03-sku-s05-composite-qualification/runtime_supervisor.py',run)

    def test_actual_Root_retention_and_complete_source_admitted_without_network_or_ERP_import(self):
        with patch.object(socket,'create_connection',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            value=load('admission').retained()
        self.assertEqual(len(value['receipt']['retained_cases']),35)
        self.assertFalse(value['receipt']['full37_qualified'])
        self.assertEqual(value['receipt']['fresh_case_credit'],0)
        self.assertTrue(value['source_invariance']['retained35_source_invariance'])

    def test_complete_engine_roundtrip_and_missing_count_anchor_refuses(self):
        module=load('engine');raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text,proof=module.derive(raw);compile(text,'focused_synthetic_engine_control','exec')
        self.assertTrue(proof['complete_original_recovered']);self.assertEqual(proof['additional_counted_changes'],1)
        with self.assertRaisesRegex(ValueError,'ANCHOR'):module.derive(raw.replace(b"report['actual_Native_cases']=7",b'changed',1))

    def test_real_WIB_window_accepts_above_full_job_and_refuses_exact_boundary(self):
        policy=load('attempt_policy')
        self.assertEqual(policy.require_window(datetime(2026,11,1,14,59,59,tzinfo=timezone.utc))['required_seconds'],7200)
        for at in (datetime(2026,11,1,15,tzinfo=timezone.utc),datetime(2026,11,1,16,tzinfo=timezone.utc)):
            with self.subTest(at=at),self.assertRaisesRegex(ValueError,'INSUFFICIENT_REAL_WIB'):policy.require_window(at)
        with self.assertRaisesRegex(ValueError,'AWARE_REAL_CLOCK'):policy.require_window(datetime(2026,11,1))
        self.assertEqual(policy.WORK_SECONDS+policy.RECOVERY_SECONDS+policy.ARTIFACT_SECONDS,policy.JOB_SECONDS)

    def test_supervisor_counts_all_setup_time_and_refuses_invalid_or_exhausted_start(self):
        module=load('runtime_supervisor');self.assertEqual(module.remaining(100,400,5400),5100)
        for start,now in ((0,1),(2,1),(float('nan'),3),(1,float('inf')),(1,5401)):
            with self.subTest(start=start,now=now),self.assertRaises(ValueError):module.remaining(start,now,5400)

    def test_synthetic_complete_gate_keeps_only_two_fresh_cases(self):
        gate,p,*values=fixture();value=gate.validate(*values,p)
        self.assertEqual(value['fresh_cases'],2);self.assertEqual(value['retained_cases'],35)
        self.assertTrue(value['retained_cases_are_not_fresh'])

    def test_fresh_native_or_boolean_counts_cannot_hide_retained_credit(self):
        for field,value in (('actual_Native_cases',31),('actual_Native_cases',False),('actual_browser_cases',6),('actual_business_cases',37),('retained_cases_are_not_fresh',False)):
            gate,p,*values=fixture();values[0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):gate.validate(*values,p)

    def test_missing_old_case_binding_or_fresh_browser_failure_refuses(self):
        gate,p,*values=fixture();part=values[0]['committed'][gate.CASE];part['retained35']=dict(part['retained35'],changed=True)
        with self.assertRaises(ValueError):gate.validate(*values,p)
        for mutation in ('missing','failure','auth_leak','rollover','retry'):
            gate,p,*values=fixture();browser=values[0]['committed'][gate.CASE]['fresh_S05_browser2']['browser']
            if mutation=='missing':browser['cases'].pop(next(iter(browser['cases'])))
            elif mutation=='failure':next(iter(browser['cases'].values()))['status']='INCOMPLETE'
            elif mutation=='auth_leak':browser['auth_counts']['after']=[1,0,0,0]
            elif mutation=='rollover':next(iter(browser['cases'].values()))['business_day_rollover']=True
            else:browser['business_day_retried']=True
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):gate.validate(*values,p)

    def test_incomplete_package_backup_or_live_process_refuses(self):
        for mutation in ('package','backup','process','deadline','reserve'):
            gate,p,*values=fixture()
            if mutation=='package':values[1]['gate']['writer_runtime']=False
            elif mutation=='backup':values[2]['checks'].pop('engine_equal')
            elif mutation=='process':values[3]['process_tree_empty']=False
            elif mutation=='deadline':values[3]['deadline_reached']=True
            else:values[3]['recovery_reserve_seconds']=0
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):gate.validate(*values,p)

    def test_dropped_catalog_table_sequence_or_untyped_hash_refuses(self):
        for mutation in ('catalog','table','sequence','sequence_abi','row_abi'):
            gate,p,*values=fixture();part=values[0]['committed'][gate.CASE]
            for which in ('used_inverse_refusal_before','used_inverse_refusal_after'):
                b=part[which]
                if mutation=='catalog':b['actual_all22'].pop('roles')
                elif mutation=='table':b['full_data_and_sequences'].pop('erp.synthetic')
                elif mutation=='sequence':b['full_data_and_sequences'].pop('sequence:erp.synthetic_0')
                elif mutation=='sequence_abi':b['full_data_and_sequences']['sequence:erp.synthetic_0']=[0,False]
                else:b['full_data_and_sequences']['erp.synthetic']=[True,'0'*64]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):gate.validate(*values,p)

if __name__=='__main__':unittest.main()
