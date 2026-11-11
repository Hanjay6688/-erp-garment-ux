"""Replay the old cleanup admission and exercise the new receipt with real subprocesses."""
from hashlib import sha1, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading

import yaml

ROOT = Path(__file__).resolve().parent
AREA = 'scripts/current-sku-automatic-composite-preparation'
BASE = ROOT.parent / 'cp7-sku-checkpoint-integration/moving-timing/stage'
NEW = ROOT / 'successor'
WORKFLOW = '.github/workflows/cp7-sku-current-parent-money-automatic-native25.yml'


def load(path):
    spec = importlib.util.spec_from_file_location('reviewed_exact_' + path.parent.name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def old_reproduction(directory):
    observed = []
    files = sorted((ROOT/'exact-consumers').glob('scripts/*/runtime_supervisor.py'))
    for path in files:
        if "process_tree_empty" not in path.read_text():
            continue
        source = path.read_bytes()
        owner = load(path)
        owner.OUT = directory/'old-supervisor.json'
        owner.OUT.write_text(json.dumps(dict(status='WORKER_COMPLETED_AND_REAPED', process_tree_empty=True,
                                             github_run_id='900', github_run_attempt='1', qualification_commit='1'*40)))
        with patch.object(sys, 'argv', [str(path), '--allow-database-stop']), \
                patch.dict(os.environ, dict(GITHUB_RUN_ID='901', GITHUB_RUN_ATTEMPT='2', GITHUB_SHA='2'*40)):
            stale = owner.main()
            owner.OUT.unlink()
            missing = owner.main()
        assert stale == missing == 0
        observed.append(dict(path=str(path.relative_to(ROOT/'exact-consumers')), blob=sha1(
            b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest(),
            stale_other_run_accepted=True, missing_report_accepted=True))
    assert len(observed) == 5
    return observed


def real_subprocess_control(directory):
    raw = (ROOT/'runtime_supervisor_original.py').read_bytes()
    assert len(raw) == 8914 and sha256(raw).hexdigest() == 'af04570b8aecef5d7b0c9b1dfd5ab04942aec32fee8c2fdb908663108c97e149'
    original = load(ROOT/'runtime_supervisor_original.py')
    guard = load(NEW/AREA/'runtime_receipt.py')
    rows = []
    for run, interrupt in [('100', False), ('101', True)]:
        env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=guard.REPOSITORY,
                   GITHUB_RUN_ID=run, GITHUB_RUN_ATTEMPT='1', GITHUB_JOB='p21',
                   GITHUB_SHA='f'*40, RUNNER_TEMP=str(directory))
        receipt = guard.from_environment(env)
        receipt.prepare()
        receipt.claim_worker()
        timer = threading.Timer(0.20, os.kill, (os.getpid(), signal.SIGTERM))
        if interrupt:
            timer.start()
        try:
            args = ['import time; time.sleep(20)' if interrupt else 'pass']
            result = original.supervise([sys.executable, '-B', '-c', *args], work_seconds=3,
                                        recovery_seconds=0.4, orphan_seconds=0.3,
                                        terminate_seconds=0.3, poll_seconds=0.02)
        finally:
            timer.cancel()
            if interrupt:
                timer.join()
        assert result['process_tree_empty'] is True and result['process_group_empty'] is True, result
        assert result['external_signal'] == ('SIGTERM' if interrupt else None), result
        assert result['status'] == ('INCOMPLETE' if interrupt else 'WORKER_COMPLETED_AND_REAPED'), result
        assert result['actual_case_credit'] == 0
        result.update(github_run_id=run, github_run_attempt='1', qualification_commit='f'*40)
        path = directory/'worker-result.json'
        path.write_text(json.dumps(result))
        receipt.finish(path)
        receipt.authorize_stop()
        terminal = receipt.read('terminal.json')
        assert terminal['processes_reaped'] and terminal['restoration_verified'] is False
        rows.append(dict(status=result['status'], external_signal=result['external_signal'],
                         worker_exit=result['worker_exit'], process_tree_empty=result['process_tree_empty'],
                         cleanup_authorized=True, restoration_verified=False))
    return rows


def check_workflow():
    before = yaml.load((BASE/WORKFLOW).read_bytes(), Loader=yaml.BaseLoader)
    after = yaml.load((NEW/WORKFLOW).read_bytes(), Loader=yaml.BaseLoader)
    pre = before['jobs']['p21']['steps']
    post = after['jobs']['p21']['steps']
    assert len(pre) == len(post) == 83
    changed = [index for index, (a,b) in enumerate(zip(pre, post), 1) if a != b]
    assert changed == [71], changed
    assert 'test_runtime_receipt.py' in post[70]['run'] and 'checkpoint.py --source .' in post[70]['run']
    assert '--allow-database-stop' in post[81]['run']
    after['jobs']['p21']['steps'][70] = pre[70]
    assert before == after
    return dict(changed_workflow_steps=changed, original_steps=83, workflow_triggers_equal=True,
                database_start=73, worker_cleanup=82, canonical_upload=83, new_jobs=0)


if __name__ == '__main__':
    with TemporaryDirectory() as tmp:
        directory = Path(tmp)
        print(json.dumps(dict(legacy=old_reproduction(directory), real_process_controls=real_subprocess_control(directory),
                              workflow=check_workflow(), actual_database_commands=0,
                              actual_ERP_case_credit=0, restoration_verified=False), indent=2))
