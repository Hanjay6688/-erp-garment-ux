"""Own the runtime process group until restoration has finished or failed.

This is execution control, never an ERP success oracle. A deadline, signal,
nonzero worker exit or surviving child always refuses qualification.
"""
from pathlib import Path
import ctypes
import json
import math
import os
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JOB_SECONDS = 360 * 60
WORK_SECONDS = 330 * 60
RECOVERY_SECONDS = 20 * 60
OUT = ROOT/'cp6-proof/t3/JOIN_RUNTIME_SUPERVISION.json'


def own_children():
    # Linux subreaper: orphaned fixtures/Node processes stay owned by this
    # supervisor, rather than leaking into the following cleanup steps.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'JOIN_CHILD_SUBREAPER_REQUIRED')


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def reap_group(pgid):
    while True:
        try:
            pid, _ = os.waitpid(-pgid, os.WNOHANG)
        except ChildProcessError:
            return
        if not pid:
            return


def children_remaining():
    # Call only before launching, or after Popen has reaped the direct worker.
    # waitpid observes children in our PID namespace, unlike a host-mounted
    # /proc. It also detects adopted descendants that start a new session.
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return False
        if not pid:
            return True


def supervise(command, *, work_seconds, recovery_seconds, orphan_seconds=10,
              terminate_seconds=10, poll_seconds=0.2):
    if any(not math.isfinite(v) or v <= 0 for v in
           (work_seconds, recovery_seconds, orphan_seconds, terminate_seconds, poll_seconds)):
        raise ValueError('JOIN_POSITIVE_FINITE_PROCESS_BUDGET_REQUIRED')
    own_children()
    if children_remaining():
        raise ValueError('JOIN_SUPERVISOR_MUST_OWN_ONLY_ITS_WORKER_TREE')
    started = time.monotonic()
    result = dict(status='INCOMPLETE', deadline_reached=False, external_signal=None,
                  orphaned_child=False, signals=[], worker_exit=None,
                  process_group_empty=False, process_tree_empty=False,
                  actual_case_credit=0, production_go=False)
    requested = []
    previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    for s in previous:
        signal.signal(s, lambda sig, frame: requested.append(sig))
    process = None
    try:
        process = subprocess.Popen(command, start_new_session=True)
        result['worker_pid'] = process.pid
        deadline = started + work_seconds
        stop_at = None
        root_exited = None
        termination_at = None

        def send(sig, reason):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
            result['signals'].append(dict(signal=signal.Signals(sig).name, reason=reason,
                                          elapsed_seconds=round(time.monotonic()-started, 3)))

        while True:
            now = time.monotonic()
            code = process.poll()
            if code is not None:
                result['worker_exit'] = code
                root_exited = now if root_exited is None else root_exited
                reap_group(process.pid)
                if not group_exists(process.pid) and not children_remaining():
                    result['process_group_empty'] = True
                    result['process_tree_empty'] = True
                    if now >= deadline:
                        result['deadline_reached'] = True
                    if requested:
                        result['external_signal'] = signal.Signals(requested[0]).name
                    break
            if stop_at is None:
                reason = None
                if requested:
                    result['external_signal'] = signal.Signals(requested[0]).name
                    reason = 'EXTERNAL_CANCELLATION'
                elif now >= deadline:
                    result['deadline_reached'] = True
                    reason = 'RESTORATION_RESERVE_STARTED'
                elif root_exited is not None and now-root_exited >= orphan_seconds:
                    result['orphaned_child'] = True
                    reason = 'CHILD_SURVIVED_WORKER'
                if reason:
                    stop_at = now
                    send(signal.SIGINT, reason)
            elif termination_at is None and now-stop_at >= recovery_seconds:
                termination_at = now
                send(signal.SIGTERM, 'RESTORATION_GRACE_EXHAUSTED')
            elif termination_at is not None and now-termination_at >= terminate_seconds:
                send(signal.SIGKILL, 'PROCESS_GROUP_DID_NOT_EXIT')
                # Reap the direct child before any adopted descendants.
                process.wait(timeout=terminate_seconds)
                result['worker_exit'] = process.returncode
                reap_group(process.pid)
                until = time.monotonic()+terminate_seconds
                while group_exists(process.pid) or children_remaining():
                    send(signal.SIGKILL, 'REAP_ADOPTED_DESCENDANTS')
                    reap_group(process.pid)
                    if time.monotonic() >= until:
                        break
                    time.sleep(poll_seconds)
                result['process_group_empty'] = not group_exists(process.pid)
                result['process_tree_empty'] = not group_exists(process.pid) and not children_remaining()
                break
            time.sleep(poll_seconds)
        if (result['worker_exit'] == 0 and not result['signals']
                and not result['external_signal'] and not result['deadline_reached']
                and not result['orphaned_child'] and result['process_group_empty']
                and result['process_tree_empty']):
            result['status'] = 'WORKER_COMPLETED_AND_REAPED'
    finally:
        # An unexpected error also refuses the following database-stop guard.
        # Kill the owned group; this path never grants success.
        if process is not None and group_exists(process.pid):
            send(signal.SIGKILL, 'SUPERVISOR_EXCEPTION_CLEANUP')
            process.wait(timeout=terminate_seconds)
            reap_group(process.pid)
        for s, handler in previous.items():
            signal.signal(s, handler)
    result['elapsed_seconds'] = round(time.monotonic()-started, 3)
    return result


def main():
    if sys.argv[1:] == ['--allow-database-stop']:
        if OUT.exists():
            observed = json.loads(OUT.read_text())
            if observed.get('process_tree_empty') is not True:
                raise ValueError('JOIN_DATABASE_STOP_REFUSED_WHILE_RUNTIME_MAY_BE_ALIVE')
        return 0
    if sys.argv[1:]:
        raise ValueError('JOIN_FIXED_RUNTIME_COMMAND_ONLY')
    if os.environ.get('JOIN_CONFIRM') != 'cp6_rollback':
        raise ValueError('JOIN_EXPLICIT_LOCAL_DISPOSABLE_CONFIRMATION_REQUIRED')
    job_start = float(os.environ['JOIN_JOB_START_MONOTONIC'])
    now = time.monotonic()
    if not math.isfinite(job_start) or not 0 < job_start <= now:
        raise ValueError('JOIN_REAL_JOB_START_REQUIRED')
    remaining = job_start + WORK_SECONDS - now
    if remaining <= 0:
        raise ValueError('JOIN_RUNTIME_BUDGET_EXHAUSTED_BEFORE_START')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(status='RUNTIME_STARTING', process_tree_empty=False))+'\n')
    try:
        result = supervise([sys.executable, '-u', '-B', str(HERE/'probe.py'), '--runtime'],
                           work_seconds=remaining, recovery_seconds=RECOVERY_SECONDS)
    except BaseException as error:
        result = dict(status='INCOMPLETE', process_tree_empty=False,
                      supervisor_error=type(error).__name__+': '+str(error), actual_case_credit=0)
    result.update(job_budget_seconds=JOB_SECONDS, work_budget_seconds=WORK_SECONDS,
                  recovery_reserve_seconds=RECOVERY_SECONDS,
                  artifact_reserve_seconds=JOB_SECONDS-WORK_SECONDS-RECOVERY_SECONDS,
                  qualification_commit=subprocess.check_output(
                      ['/usr/bin/git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                  github_run_id=os.environ.get('GITHUB_RUN_ID'),
                  github_run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'WORKER_COMPLETED_AND_REAPED' else 124


if __name__ == '__main__':
    sys.exit(main())
