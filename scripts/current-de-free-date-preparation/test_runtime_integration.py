"""New FREE date process wiring only. Reuse old process controls and ERP evidence."""
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from hashlib import sha256
from unittest.mock import patch
import ast,importlib.util,json,os,subprocess,sys,tempfile,unittest,yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path=None):
    spec=importlib.util.spec_from_file_location(name,path or HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


class FREEDateProcessWiring(unittest.TestCase):
    def workflow_source_fixture(self,directory):
        source=load('source');root=Path(directory)
        here=root/'scripts/current-de-free-date-preparation';here.mkdir(parents=True)
        data=b'qualification template bytes\n';(here/'native3.workflow.yml.txt').write_bytes(data)
        active=root/source.WORKFLOW;active.parent.mkdir(parents=True)
        declaration={'files':{source.WORKFLOW:{'bytes':len(data),'sha256':sha256(data).hexdigest()}}}
        return source,root,here,active,data,declaration

    def test_unarmed_workflow_source_never_reads_parent(self):
        with tempfile.TemporaryDirectory()as directory:
            source,root,here,active,data,declaration=self.workflow_source_fixture(directory)
            with patch.object(source,'ROOT',root),patch.object(source,'HERE',here), \
                 patch.object(source,'actual_parent_receipt')as parent:
                self.assertIsNone(source.admit_workflow({'files':{}}));parent.assert_not_called()

    def test_stray_or_missing_workflow_refuses_before_parent(self):
        with tempfile.TemporaryDirectory()as directory:
            source,root,here,active,data,declaration=self.workflow_source_fixture(directory)
            with patch.object(source,'ROOT',root),patch.object(source,'HERE',here), \
                 patch.object(source,'actual_parent_receipt')as parent:
                active.write_bytes(data)
                with self.assertRaisesRegex(ValueError,'UNDECLARED_WORKFLOW_REFUSED'):
                    source.admit_workflow({'files':{}})
                active.unlink()
                with self.assertRaisesRegex(ValueError,'DECLARED_WORKFLOW_MISSING'):
                    source.admit_workflow(declaration)
                parent.assert_not_called()

    def test_exact_workflow_still_requires_actual_matching_parent(self):
        with tempfile.TemporaryDirectory()as directory:
            source,root,here,active,data,declaration=self.workflow_source_fixture(directory);active.write_bytes(data)
            with patch.object(source,'ROOT',root),patch.object(source,'HERE',here), \
                 patch.object(source,'actual_parent_receipt')as parent:
                parent.side_effect=ValueError('FREE_DATE_DE_ACTUAL_NATIVE30_PARENT_INTAKE_PENDING')
                with self.assertRaisesRegex(ValueError,'ACTUAL_NATIVE30_PARENT_INTAKE_PENDING'):
                    source.admit_workflow(declaration)
                parent.side_effect=None
                for field in('head','tree'):
                    receipt={'head':source.BASE,'tree':source.TREE};receipt[field]='wrong-parent'
                    parent.return_value=receipt
                    with self.assertRaisesRegex(ValueError,'EXACT_SOURCE_BASE_QUALIFICATION'):
                        source.admit_workflow(declaration)
                parent.return_value={'head':source.BASE,'tree':source.TREE}
                self.assertEqual(source.admit_workflow(declaration)['actual_case_credit'],0)
                parent.reset_mock()
                bad={'files':{source.WORKFLOW:{'bytes':len(data),'sha256':'0'*64}}}
                with self.assertRaisesRegex(ValueError,'EXACT_WORKFLOW_SOURCE_PIN_REQUIRED'):
                    source.admit_workflow(bad)
                parent.assert_not_called()
                (here/'native3.workflow.yml.txt').write_bytes(b'changed template')
                with self.assertRaisesRegex(ValueError,'MUST_EQUAL_REVIEWED_TEMPLATE'):
                    source.admit_workflow(declaration)
                parent.assert_not_called()

    def test_financial_validator_is_unchanged_and_supervision_stays_in_owning_gate(self):
        path='scripts/current-de-free-date-preparation/final_gate.py'
        old=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',
            'e686f804de40077465e40ef26d2f88d23fe18fab:'+path])
        names={'money','posted','case_boundary','validate'}
        selected=lambda raw:[ast.dump(n,include_attributes=False)for n in ast.parse(raw).body
            if isinstance(n,ast.FunctionDef)and n.name in names]
        self.assertEqual(selected(old),selected((HERE/'final_gate.py').read_bytes()))
        gate=load('final_gate');typed=load('supervision_typed_fields',
            ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
        from types import SimpleNamespace
        control=load('runtime_controls')
        good=dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit='control-head',github_run_id='control-run',
            github_run_attempt='1',worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,
            process_group_empty=True,process_tree_empty=True,signals=[],actual_case_credit=0,production_go=False,
            job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600)
        modules={'admission.py':SimpleNamespace(parent_receipt=lambda:None),
            'parents.py':typed,'native_free.py':SimpleNamespace(source_controls=lambda:{'case_ids':['control-only']}),
            'runtime_controls.py':control}
        with tempfile.TemporaryDirectory()as directory:
            out=Path(directory)
            for name in (gate.MAIN,gate.RAW,'T3_BACKUP_RESTORE_DRILL.json'):(out/name).write_text('{}')
            (out/'T3_PACKAGE_INSTALL.json').write_text('{"run_identity":{"run_id":"control-run"}}')
            (out/'FREE_DATE_RUNTIME_SUPERVISION.json').write_text(json.dumps(good))
            with patch.object(gate,'load',side_effect=lambda name,path:modules[path.name]), \
                 patch.object(gate,'validate',return_value={'actual_ERP_cases':0})as business:
                result=gate.gate(out,'control-head')
                self.assertEqual(result,{'actual_ERP_cases':0,
                    'runtime_supervision':{'status':'FREE_DATE_SUPERVISION_ACCEPTED','actual_case_credit':0}})
                business.assert_called_once()
                business.reset_mock();good['qualification_commit']='other-head'
                (out/'FREE_DATE_RUNTIME_SUPERVISION.json').write_text(json.dumps(good))
                with self.assertRaises(ValueError):gate.gate(out,'control-head')
                business.assert_not_called()

    def test_source_workflow_and_real_window_agree(self):
        self.assertTrue(load('runtime_controls').source_controls()['process_engine_unchanged'])
        raw,proof=load('workflow').derive();workflow=yaml.safe_load(raw);job=workflow['jobs']['p21'];steps=job['steps']
        self.assertEqual(len(steps),75)
        self.assertEqual(proof['unchanged_parent_steps'],66)
        self.assertEqual(job['timeout-minutes']*60,load('attempt_policy').JOB_BUDGET_SECONDS)
        self.assertNotIn('github.run_id',workflow['concurrency']['group'])
        self.assertIs(workflow['concurrency']['cancel-in-progress'],False)
        self.assertIn('FREE_DATE_JOB_START_MONOTONIC',steps[0]['run'])
        self.assertEqual(steps[2]['run'],'python -B scripts/current-de-free-date-preparation/attempt_policy.py --require-window\n')
        runtime=next(i for i,s in enumerate(steps)if s.get('name','').startswith('Run Native FREE date'))
        stop=next(i for i,s in enumerate(steps)if s.get('name')=='Remove disposable database')
        self.assertLess(runtime,stop)
        self.assertEqual(steps[runtime]['working-directory'],'writer')
        self.assertIn('current-de-free-date-preparation/runtime_supervisor.py',steps[runtime]['run'])
        self.assertIn('final_gate.py',steps[runtime]['run'])
        self.assertNotIn('--runtime',steps[runtime]['run'])
        self.assertLess(steps[stop]['run'].index('--allow-database-stop'),steps[stop]['run'].index('supabase'))
        self.assertEqual(steps[stop]['working-directory'],'base')
        retained=load('runtime_controls').source_controls()
        self.assertTrue(retained['retained_generator_matches_927'])
        log=next(s['run']for s in steps if s.get('name','').startswith('Preserve exact original JSON'))
        self.assertIn('FREE_DATE_RUNTIME_SUPERVISION.json',log)
        script=log.split("python - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]
        compile(script,'actual_FREE_original_receipt_retention','exec')

    def test_actual_entrypoint_routes_only_FREE_date_probe_and_receipt(self):
        supervisor=load('runtime_supervisor');self.assertEqual(supervisor.OUT.name,'FREE_DATE_RUNTIME_SUPERVISION.json')
        with tempfile.TemporaryDirectory()as directory:
            out=Path(directory)/supervisor.OUT.name;calls=[]
            def process(command,**kwargs):
                self.assertIs(json.loads(out.read_text())['process_tree_empty'],False)
                calls.append((command,kwargs))
                return dict(status='WORKER_COMPLETED_AND_REAPED',process_tree_empty=True)
            with patch.object(supervisor,'OUT',out),patch.object(sys,'argv',['supervisor']), \
                 patch.dict(os.environ,{'FREE_DATE_CONFIRM':'cp6_rollback','FREE_DATE_JOB_START_MONOTONIC':'100',
                    'GITHUB_RUN_ID':'process-control','GITHUB_RUN_ATTEMPT':'1'},clear=True), \
                 patch.object(supervisor.time,'monotonic',return_value=200), \
                 patch.object(supervisor,'supervise',side_effect=process), \
                 patch.object(supervisor.subprocess,'check_output',return_value='control-head\n'),redirect_stdout(StringIO()):
                self.assertEqual(supervisor.main(),0)
            self.assertEqual(calls,[([sys.executable,'-u','-B',str(HERE/'probe.py'),'--runtime'],
                dict(work_seconds=19700,recovery_seconds=1200))])
            self.assertEqual(json.loads(out.read_text())['github_run_id'],'process-control')
        with patch.object(sys,'argv',['supervisor']),patch.dict(os.environ,{'JOIN_CONFIRM':'cp6_rollback'},clear=True), \
             patch.object(supervisor,'supervise')as process:
            with self.assertRaisesRegex(ValueError,'EXPLICIT_LOCAL_DISPOSABLE'):supervisor.main()
            process.assert_not_called()

    def test_stop_guard_cannot_use_other_component_receipt(self):
        supervisor=load('runtime_supervisor')
        with tempfile.TemporaryDirectory()as directory:
            out=Path(directory)/'FREE_DATE_RUNTIME_SUPERVISION.json';out.write_text('{"process_tree_empty":false}')
            (out.parent/'JOIN_RUNTIME_SUPERVISION.json').write_text('{"process_tree_empty":true}')
            with patch.object(supervisor,'OUT',out),patch.object(sys,'argv',['supervisor','--allow-database-stop']):
                with self.assertRaisesRegex(ValueError,'DATABASE_STOP_REFUSED'):supervisor.main()

    def test_receipt_fields_cannot_hide_wrong_identity_or_incomplete_cleanup(self):
        control=load('runtime_controls')
        p=load('typed_original_fields',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
        good=dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit='control-head',github_run_id='control-run',
            github_run_attempt='1',worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,
            process_group_empty=True,process_tree_empty=True,signals=[],actual_case_credit=0,production_go=False,
            job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600)
        self.assertEqual(control.receipt(p,good,'control-head','control-run')['actual_case_credit'],0)
        for key in good:
            for kind in ('missing','changed'):
                with self.subTest(key=key,kind=kind):
                    bad=dict(good)
                    if kind=='missing':bad.pop(key)
                    else:bad[key]=[{'signal':'SIGINT'}]if key=='signals'else('changed'if good[key]is None else None)
                    with self.assertRaises((ValueError,KeyError)):control.receipt(p,bad,'control-head','control-run')
        for key in ('deadline_reached','orphaned_child','process_group_empty','process_tree_empty','production_go'):
            bad=dict(good);bad[key]=int(good[key])
            with self.assertRaises(ValueError):control.receipt(p,bad,'control-head','control-run')


class FREEDateActualParentModeControls(unittest.TestCase):
    def test_unbound_parent_requires_every_pending_entry_to_refuse_before_any_work(self):
        from types import SimpleNamespace
        check=load('check');calls=[]
        def pending():calls.append('pending');raise ValueError('FREE_DATE_DE_ACTUAL_NATIVE30_PARENT_INTAKE_PENDING')
        admission=SimpleNamespace(PARENT_HEAD=None,PARENT_RECEIPT=None,parent_receipt=pending)
        value=check.parent_controls(admission,[('parent_receipt',pending),('install_before_SQL',pending)])
        self.assertEqual(value['closed_before_ERP_or_SQL'],['parent_receipt','install_before_SQL'])
        self.assertTrue(value['unarmed_entry_controls_executed']);self.assertEqual(calls,['pending','pending'])
        with self.assertRaisesRegex(ValueError,'PENDING_ENTRY_WAS_OPENED'):
            check.parent_controls(admission,[('unexpectedly_open',lambda:{'MODEL_ONLY':True})])

    def test_bound_parent_validates_actual_receipt_without_executing_unarmed_factories(self):
        from types import SimpleNamespace
        check=load('check');calls=[]
        def accepted():calls.append('ACTUAL_RECEIPT_VALIDATOR');return{'labelled_synthetic_receipt':True}
        def must_not_run():raise AssertionError('UNARMED_FACTORY_WAS_EXECUTED_AFTER_ACTUAL_BINDING')
        admission=SimpleNamespace(PARENT_HEAD='a'*40,PARENT_RECEIPT={'MODEL_PIN':True},parent_receipt=accepted)
        value=check.parent_controls(admission,[('unarmed_factory',must_not_run)])
        self.assertEqual(calls,['ACTUAL_RECEIPT_VALIDATOR']);self.assertEqual(value['closed_before_ERP_or_SQL'],[])
        self.assertFalse(value['unarmed_entry_controls_executed']);self.assertEqual(value['actual_Native_cases'],0)

    def test_partial_or_invalid_actual_parent_cannot_bypass_receipt_validation(self):
        from types import SimpleNamespace
        check=load('check')
        for head,receipt in((None,{'MODEL_PIN':True}),('a'*40,None)):
            admission=SimpleNamespace(PARENT_HEAD=head,PARENT_RECEIPT=receipt,parent_receipt=lambda:None)
            with self.subTest(head=head),self.assertRaisesRegex(ValueError,'PARTIAL_ACTUAL_PARENT'):
                check.parent_controls(admission,[])
        def invalid():raise ValueError('LABELLED_ACTUAL_RECEIPT_HASH_MISMATCH')
        admission=SimpleNamespace(PARENT_HEAD='a'*40,PARENT_RECEIPT={'MODEL_PIN':True},parent_receipt=invalid)
        with self.assertRaisesRegex(ValueError,'LABELLED_ACTUAL_RECEIPT_HASH_MISMATCH'):check.parent_controls(admission,[])

if __name__=='__main__':unittest.main()
