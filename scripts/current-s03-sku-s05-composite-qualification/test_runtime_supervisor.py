"""Real child-process controls; no database, financial or browser case credit."""
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeSupervision(unittest.TestCase):
    def run_worker(self, script, *, work=2, recovery=.2):
        return load('runtime_supervisor').supervise(
            [sys.executable, '-B', '-c', script], work_seconds=work,
            recovery_seconds=recovery, orphan_seconds=.1,
            terminate_seconds=.1, poll_seconds=.01)

    def test_success_and_original_nonzero_exit_are_distinct(self):
        for exit_code in (0, 7):
            value = self.run_worker('raise SystemExit('+str(exit_code)+')')
            self.assertEqual(value['worker_exit'], exit_code)
            self.assertEqual(value['status'], 'INCOMPLETE' if exit_code else 'WORKER_COMPLETED_AND_REAPED')
            self.assertTrue(value['process_group_empty'])
            self.assertEqual(value['signals'], [])
            self.assertEqual(value['actual_case_credit'], 0)

    def test_deadline_waits_for_finally_before_returning_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)/'restored.txt'
            script = ('import time\nfrom pathlib import Path\ntry:\n time.sleep(10)\n'
                      'finally:\n time.sleep(.1)\n Path('+repr(str(marker))+').write_text("finally-finished")\n')
            value = self.run_worker(script, work=.2, recovery=1)
            self.assertEqual(marker.read_text(), 'finally-finished')
            self.assertEqual(value['status'], 'INCOMPLETE')
            self.assertTrue(value['deadline_reached'])
            self.assertTrue(value['process_group_empty'])
            self.assertEqual([x['signal'] for x in value['signals']], ['SIGINT'])

    def test_orphan_is_reaped_even_if_worker_claims_zero(self):
        script = ('import subprocess,sys,time\n'
                  'subprocess.Popen([sys.executable,"-c","import time; time.sleep(10)"])\n'
                  'time.sleep(.1)\n')
        value = self.run_worker(script)
        self.assertEqual(value['worker_exit'], 0)
        self.assertTrue(value['orphaned_child'])
        self.assertTrue(value['process_group_empty'])
        self.assertEqual(value['status'], 'INCOMPLETE')

    def test_unresponsive_group_is_killed_and_reaped(self):
        script = ('import signal,time\n'
                  'signal.signal(signal.SIGINT,signal.SIG_IGN)\n'
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                  'time.sleep(10)\n')
        value = self.run_worker(script, work=.2)
        self.assertEqual([x['signal'] for x in value['signals']], ['SIGINT','SIGTERM','SIGKILL'])
        self.assertTrue(value['process_group_empty'])
        self.assertEqual(value['status'], 'INCOMPLETE')

    def test_child_that_starts_new_session_cannot_escape_cleanup(self):
        script = ('import subprocess,sys,time\n'
                  'subprocess.Popen([sys.executable,"-c","import time; time.sleep(.5)"],start_new_session=True)\n'
                  'time.sleep(.1)\n')
        value = self.run_worker(script, recovery=1)
        self.assertEqual(value['worker_exit'], 0)
        self.assertTrue(value['orphaned_child'])
        self.assertTrue(value['process_tree_empty'])
        self.assertEqual(value['status'], 'INCOMPLETE')

    def test_invalid_budget_never_starts_worker(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.assertRaisesRegex(ValueError, 'FINITE_PROCESS_BUDGET'):
                self.run_worker('raise AssertionError("must not execute")', work=value)

    def test_database_stop_refuses_missing_or_unfinished_tree_proof(self):
        supervisor = load('runtime_supervisor')
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'receipt.json'
            with patch.object(supervisor,'OUT',out), patch.object(sys,'argv',['supervisor','--allow-database-stop']):
                # No launch marker means runtime was never started.
                self.assertEqual(supervisor.main(),0)

                for value in ({'status':'RUNTIME_STARTING'}, {'process_tree_empty':False}, {'process_tree_empty':1}):
                    out.write_text(json.dumps(value))
                    with self.assertRaisesRegex(ValueError,'DATABASE_STOP_REFUSED'):
                        supervisor.main()
                out.write_text(json.dumps({'process_tree_empty':True}))
                self.assertEqual(supervisor.main(),0)

    def test_external_cancel_cannot_pass_even_when_worker_exits_zero(self):
        value = self.run_worker('import os,signal\nos.kill(os.getppid(),signal.SIGTERM)\n')
        self.assertEqual(value['external_signal'],'SIGTERM')
        self.assertEqual(value['status'],'INCOMPLETE')
        self.assertTrue(value['process_tree_empty'])

    def test_real_day_guard_matches_complete_job_budget(self):
        policy = load('attempt_policy')
        self.assertEqual(policy.JOB_BUDGET_SECONDS, 360*60)
        self.assertEqual(policy.require_window(datetime(2026,11,1,10,59,tzinfo=timezone.utc))['required_seconds'], 360*60)
        for hour, minute in ((11,0), (16,59)):
            with self.assertRaisesRegex(ValueError, 'INSUFFICIENT_WIB_DAY_WINDOW'):
                policy.require_window(datetime(2026,11,1,hour,minute,tzinfo=timezone.utc))
        with self.assertRaisesRegex(ValueError, 'AWARE_REAL_CLOCK'):
            policy.require_window(datetime(2026,11,1))

    def test_workflow_supervision_precedes_cleanup_and_has_reserve(self):
        import yaml
        workflow = yaml.safe_load((HERE.parents[1]/'.github/workflows/cp7-s03-sku-s05-composite.yml').read_text())
        job = workflow['jobs']['p21'];steps = job['steps']
        self.assertEqual(job['timeout-minutes'], 360)
        self.assertIn('JOIN_JOB_START_MONOTONIC', steps[0]['run'])
        runtime = next(i for i,s in enumerate(steps) if 'runtime_supervisor.py' in s.get('run',''))
        cleanup = next(i for i,s in enumerate(steps) if s.get('name')=='Remove disposable database')
        self.assertLess(runtime, cleanup)
        self.assertNotIn('continue-on-error', steps[runtime])
        self.assertIn('final_gate.py', steps[runtime]['run'])
        self.assertNotIn('github.run_id', workflow['concurrency']['group'])
        supervisor = load('runtime_supervisor')
        self.assertEqual(supervisor.JOB_SECONDS-supervisor.WORK_SECONDS-supervisor.RECOVERY_SECONDS, 600)


if __name__ == '__main__':
    unittest.main()
