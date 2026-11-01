"""Only the new permanent wiring and receipt boundary; no ERP case credit."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path=None):
    spec = importlib.util.spec_from_file_location(name, path or HERE/(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class PermanentSupervision(unittest.TestCase):
    def test_exact_process_engine_and_prior_workflow_recovered(self):
        result = load('runtime_controls').verify()
        self.assertTrue(result['unchanged_process_engine'])
        old = yaml.safe_load(result['prior_workflow'])
        self.assertEqual(old['jobs']['p21']['timeout-minutes'], 120)
        self.assertEqual(result['job_seconds']-result['work_seconds']-
            result['restoration_reserve_seconds'], 600)

    def test_workflow_owns_runtime_before_database_cleanup(self):
        workflow = yaml.safe_load((ROOT/'.github/workflows/cp7-final-s03-sku-s05.yml').read_bytes())
        job = workflow['jobs']['p21']; steps = job['steps']
        self.assertEqual(job['timeout-minutes'], 360)
        self.assertIn('PERMANENT_JOB_START_MONOTONIC', steps[0]['run'])
        self.assertNotIn('github.run_id', workflow['concurrency']['group'])
        self.assertIs(workflow['concurrency']['cancel-in-progress'], False)
        runtime = next(i for i,s in enumerate(steps) if s.get('name','').startswith('Run actual permanent'))
        cleanup = next(i for i,s in enumerate(steps) if s.get('name')=='Remove disposable database')
        self.assertLess(runtime, cleanup)
        self.assertEqual(steps[runtime]['working-directory'], 'writer')
        self.assertIn('runtime_supervisor.py', steps[runtime]['run'])
        self.assertNotIn('--runtime', steps[runtime]['run'])
        self.assertIn('final_gate.py', steps[runtime]['run'])
        self.assertNotIn('continue-on-error', steps[runtime])
        self.assertLess(steps[cleanup]['run'].index('--allow-database-stop'),
            steps[cleanup]['run'].index('supabase stop'))
        self.assertEqual(steps[cleanup]['working-directory'], 'base')

    def test_supervisor_routes_only_own_probe_and_records_own_receipt(self):
        supervisor = load('runtime_supervisor')
        self.assertEqual(supervisor.OUT.name, 'PERMANENT_RUNTIME_SUPERVISION.json')
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/supervisor.OUT.name
            calls = []
            def observed(command, **kwargs):
                self.assertEqual(json.loads(out.read_text()),
                    {'status':'RUNTIME_STARTING','process_tree_empty':False})
                calls.append((command,kwargs))
                return dict(status='WORKER_COMPLETED_AND_REAPED',process_tree_empty=True)
            with patch.object(supervisor,'OUT',out), patch.object(sys,'argv',['supervisor']), \
                 patch.dict(os.environ,{'PERMANENT_S05_CONFIRM':'cp6_rollback',
                    'PERMANENT_JOB_START_MONOTONIC':'100','GITHUB_RUN_ID':'process-control',
                    'GITHUB_RUN_ATTEMPT':'1'},clear=True), \
                 patch.object(supervisor.time,'monotonic',return_value=200), \
                 patch.object(supervisor,'supervise',side_effect=observed), \
                 patch.object(supervisor.subprocess,'check_output',return_value='process-control-head\n'), \
                 redirect_stdout(StringIO()):
                self.assertEqual(supervisor.main(),0)
            self.assertEqual(calls,[([sys.executable,'-u','-B',str(HERE/'probe.py'),'--runtime'],
                dict(work_seconds=19700,recovery_seconds=1200))])
            receipt=json.loads(out.read_text())
            self.assertEqual(receipt['github_run_id'],'process-control')
            self.assertEqual(receipt['qualification_commit'],'process-control-head')
            self.assertEqual(receipt['artifact_reserve_seconds'],600)
        with patch.object(sys,'argv',['supervisor']), \
             patch.dict(os.environ,{'JOIN_CONFIRM':'cp6_rollback'},clear=True), \
             patch.object(supervisor,'supervise') as worker:
            with self.assertRaisesRegex(ValueError,'EXPLICIT_LOCAL_DISPOSABLE'):
                supervisor.main()
            worker.assert_not_called()

    def test_stop_guard_reads_own_receipt_not_join_receipt(self):
        supervisor = load('runtime_supervisor')
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'PERMANENT_RUNTIME_SUPERVISION.json'
            (out.parent/'JOIN_RUNTIME_SUPERVISION.json').write_text('{"process_tree_empty":true}')
            out.write_text('{"status":"RUNTIME_STARTING","process_tree_empty":false}')
            with patch.object(supervisor,'OUT',out), \
                 patch.object(sys,'argv',['supervisor','--allow-database-stop']):
                with self.assertRaisesRegex(ValueError,'DATABASE_STOP_REFUSED'):
                    supervisor.main()

    def test_final_gate_rejects_every_invalid_supervision_field(self):
        gate=load('final_gate')
        typed=load('typed_supervision_fields',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
        good=dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit='control-head',
            github_run_id='control-run',github_run_attempt='1',worker_exit=0,deadline_reached=False,
            external_signal=None,orphaned_child=False,process_group_empty=True,process_tree_empty=True,
            signals=[],actual_case_credit=0,production_go=False,job_budget_seconds=21600,
            work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600)
        self.assertEqual(gate.supervision(typed,good,'control-head','control-run')['actual_case_credit'],0)
        for key in good:
            with self.subTest(missing=key):
                bad=copy.deepcopy(good);bad.pop(key)
                with self.assertRaises((ValueError,KeyError)):
                    gate.supervision(typed,bad,'control-head','control-run')
            with self.subTest(changed=key):
                bad=copy.deepcopy(good)
                bad[key]=[{'signal':'SIGINT'}] if key=='signals' else ('changed' if good[key] is None else None)
                with self.assertRaises((ValueError,KeyError)):
                    gate.supervision(typed,bad,'control-head','control-run')
        for key in ('deadline_reached','orphaned_child','process_group_empty','process_tree_empty','production_go'):
            bad=copy.deepcopy(good);bad[key]=int(good[key])
            with self.assertRaises(ValueError):gate.supervision(typed,bad,'control-head','control-run')

    def test_actual_final_gate_requires_new_receipt_before_any_business_result(self):
        gate=load('final_gate')
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            (out/gate.MAIN).write_text('{}')
            (out/'T3_PACKAGE_INSTALL.json').write_text('{"run_identity":{"run_id":"control-run"}}')
            (out/'JOIN_RUNTIME_SUPERVISION.json').write_text('{}')
            with self.assertRaisesRegex(FileNotFoundError,'PERMANENT_RUNTIME_SUPERVISION'):
                gate.gate(out,'control-head')


if __name__=='__main__':unittest.main()
