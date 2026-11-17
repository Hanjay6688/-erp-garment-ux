"""Publish small P20 evidence files while the disposable worker is still running."""

from argparse import ArgumentParser
from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

from p20_evidence import (REMAINING_CASES, RESTORE_FLAGS, EvidenceError, Journal, ROOT, artifact_name,
                          need, read, receipt_valid, write_once)


TOOL = Path(__file__).parent
UPLOADER = TOOL / 'checkpoint_action/upload.mjs'
CAPTURED_ENVS = ('ACTIONS_RUNTIME_TOKEN', 'ACTIONS_RUNTIME_URL', 'ACTIONS_RESULTS_URL')
MARKER = re.compile(r'GLOBAL_(?:PARENT|ORDINARY)_PHASE ([A-Z0-9_]{3,80}) '
                    r'(STARTED|COMPLETED|FAILED)(?: elapsed_ms=[0-9]{1,10})?')
ACK = re.compile(rb'CP7_UPLOAD_OK ([1-9][0-9]{0,17}) ([a-f0-9]{64})')


def upload(path, name, node_home):
    env = {key: os.environ[key] for key in (*CAPTURED_ENVS, 'PATH') if key in os.environ}
    completed = subprocess.run(('node', UPLOADER, path, name, node_home),
                               env=env, capture_output=True, timeout=25, check=False)
    result = ACK.fullmatch(completed.stdout.splitlines()[-1]) if completed.stdout.splitlines() else None
    need(completed.returncode == 0 and result, 'P20_EVIDENCE_ARTIFACT_UPLOAD_FAILED')
    return int(result[1]), result[2].decode('ascii')


def publish(spool, identity, path, send):
    envelope = read(path)
    need(envelope['identity'] == identity and envelope['production_go'] is False
         and envelope['independent_acceptance'] is False and envelope['actual_case_credit'] == 0,
         'P20_EVIDENCE_OUTBOUND_IDENTITY_CHANGED')
    raw = path.read_bytes()
    need(len(raw) <= 12000, 'P20_EVIDENCE_OUTBOUND_SIZE_INVALID')
    name = artifact_name(identity, path.stem)
    ack_path = spool / 'receipts' / path.name
    need(not ack_path.exists(), 'P20_EVIDENCE_DUPLICATE_UPLOAD_REFUSED')
    try:
        artifact_id, archive_sha = send(path, name)
        ack = dict(status='UPLOADED', artifact_id=artifact_id, artifact_name=name,
                   archive_sha256=archive_sha, document_sha256=sha256(raw).hexdigest())
        need(receipt_valid(ack, name, raw), 'P20_EVIDENCE_ARTIFACT_RECEIPT_INVALID')
    except (EvidenceError, OSError, subprocess.TimeoutExpired):
        write_once(ack_path, dict(status='UPLOAD_FAILED', artifact_name=name))
        print(f'P20_EVIDENCE_UPLOAD_FAILED {path.stem}', flush=True)
        return False
    write_once(ack_path, ack)
    print(f'P20_EVIDENCE_UPLOADED {path.stem} artifact_id={artifact_id} sha256={ack["document_sha256"]}', flush=True)
    return True


class Progress:
    def __init__(self):
        self.offsets = {}
        self.phase = 'SUPERVISOR_START'
        self.phase_state = 'STARTED'
        self.last = time.monotonic()
        self.prior_cpu = None

    def scan(self, log):
        if not log.is_file():
            return
        offset = self.offsets.get(log, 0)
        with log.open('rb') as stream:
            stream.seek(offset)
            chunk = stream.read(65536)
        # Avoid publishing a partial or arbitrarily large log line.
        end = chunk.rfind(b'\n')
        if end < 0:
            if len(chunk) == 65536:
                self.offsets[log] = offset + len(chunk)
            return
        self.offsets[log] = offset + end + 1
        for line in chunk[:end].splitlines():
            match = MARKER.fullmatch(line.decode('ascii', errors='replace'))
            if match:
                self.phase, self.phase_state = match.groups()
                self.last = time.monotonic()
                print(line.decode('ascii'), flush=True)

    def sample(self, directory):
        with open('/proc/stat', encoding='ascii') as stream:
            cpu = [int(part) for part in stream.readline().split()[1:9]]
        ticks, idle = sum(cpu), sum(cpu[3:5])
        busy = None
        if self.prior_cpu and ticks > self.prior_cpu[0]:
            total_delta = ticks - self.prior_cpu[0]
            idle_delta = idle - self.prior_cpu[1]
            busy = round(100 * (total_delta - idle_delta) / total_delta, 1)
        self.prior_cpu = ticks, idle

        def kernel_counter(file, label):
            try:
                with open(file, encoding='ascii') as stream:
                    return next(int(line.split()[1]) for line in stream if line.startswith(label + ' '))
            except (OSError, StopIteration):
                return None

        available = kernel_counter('/proc/meminfo', 'MemAvailable:')
        total = kernel_counter('/proc/meminfo', 'MemTotal:')
        return dict(phase=self.phase, phase_state=self.phase_state,
                    seconds_since_progress=round(time.monotonic()-self.last),
                    cpu_busy_pct_since_sample=busy, load_average_1m=os.getloadavg()[0],
                    memory_available_mib=None if available is None else available // 1024,
                    memory_total_mib=None if total is None else total // 1024,
                    temp_disk_free_mib=shutil.disk_usage(directory).free // 2**20,
                    workspace_disk_free_mib=shutil.disk_usage(ROOT).free // 2**20,
                    host_oom_kill_count=kernel_counter('/proc/vmstat', 'oom_kill'),
                    cgroup_oom_kill_count=kernel_counter('/sys/fs/cgroup/memory.events', 'oom_kill'))


def restore_observation(returncode, directory):
    report_file = directory / 'CP7_GLOBAL_FIRST_SNAPSHOTS.json'
    try:
        report = read(report_file) if report_file.stat().st_size <= 16_000_000 else {}
    except (OSError, ValueError, EvidenceError):
        report = {}
    flags = {key: report.get(key) is True for key in RESTORE_FLAGS}
    flags['auth_restored_application_mappings_absent'] = (
        report.get('global_auth_cleanup', {}).get('restored_application_mappings_absent') is True)
    auth = report.get('global_auth_cleanup', {})
    uid_removed = auth.get('primary_application_mappings_absent') is True
    return dict(worker_exit=returncode, recovery_flags=flags,
                recovery_receipt_present=bool(report), primary_auth_mappings_absent=uid_removed,
                verified_actors=auth.get('verified_actors') if auth.get('verified_actors') in (0, 1, 2) else None,
                independent_terminal_receipt_required=True)


def worker_environment(spool):
    # The artifact service token belongs only to the publisher. The existing disposable
    # worker still receives the same ERP test configuration as before.
    return dict({key: value for key, value in os.environ.items()
                 if key not in CAPTURED_ENVS and key not in ('GH_TOKEN', 'GITHUB_TOKEN')
                 and not key.startswith(('ACTIONS_CACHE_', 'ACTIONS_ID_TOKEN_'))},
                P20_EVIDENCE_SPOOL=str(spool))


def run(mode, config, spool, node_home):
    identity = read(config)
    need(identity['mode'] == mode and str(identity['run_id']) == os.environ.get('GITHUB_RUN_ID')
         and identity['runner'] == os.environ.get('GITHUB_SHA'), 'P20_EVIDENCE_BROKER_IDENTITY_CHANGED')
    spool.mkdir(mode=0o700)
    for name in ('outbound', 'receipts'):
        (spool / name).mkdir(mode=0o700)
    write_once(spool / 'identity.json', identity)
    journal = Journal(spool)
    progress = Progress()

    def send(path, name):
        return upload(path, name, node_home)

    def record(stem, kind, payload):
        path = spool / 'outbound' / f'{stem}.json'
        write_once(path, journal.envelope(kind, payload))
        return publish(spool, identity, path, send)

    def fail():
        path = spool / 'publisher-failure.json'
        if not path.exists():
            write_once(path, dict(status='INCOMPLETE', code='P20_EVIDENCE_PUBLISHER_FAILED'))

    def drain():
        for path in sorted((spool / 'outbound').glob('*.json')):
            if not (spool / 'receipts' / path.name).exists() and not publish(spool, identity, path, send):
                fail()

    if not record('heartbeat-000', 'heartbeat', progress.sample(spool)):
        fail()
        return 1
    heartbeat = 1
    next_beat = time.monotonic() + 60
    command = ([sys.executable, '-u', '-B', ROOT / 'qualification/ordinary_run.py', 'supervise'] if mode == 'audit'
               else [sys.executable, '-u', '-B', TOOL / 'test_p20_evidence.py', 'crash-worker'])
    scratch = spool.parent / 'cp7-live-parent'
    supervisor_log = (scratch if mode == 'audit' else spool) / 'ordinary-supervise.log'
    worker_log = scratch / 'ordinary-worker.log'
    stop = []
    old = {sig: signal.signal(sig, lambda signum, _: stop.append(signum)) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        with supervisor_log.open('xb') as log:
            with subprocess.Popen(command, cwd=ROOT.parent if mode == 'audit' else ROOT,
                                  stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                  env=worker_environment(spool)) as child:
                sent_signal = False
                try:
                    while child.poll() is None:
                        if stop and not sent_signal:
                            child.send_signal(signal.SIGINT)
                            sent_signal = True
                        progress.scan(supervisor_log)
                        progress.scan(worker_log)
                        drain()
                        if not sent_signal and time.monotonic() >= next_beat and heartbeat <= 190:
                            if not record(f'heartbeat-{heartbeat:03d}', 'heartbeat', progress.sample(spool)):
                                fail()
                            next_beat = time.monotonic()+60
                            heartbeat += 1
                        time.sleep(0.15)
                except BaseException:
                    fail()
                    # The retained supervisor sends the worker through its existing
                    # recovery grace period and owns reaping the full process group.
                    if child.poll() is None:
                        child.send_signal(signal.SIGINT)
                    raise
                code = child.wait()
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)

    progress.scan(supervisor_log)
    progress.scan(worker_log)
    drain()
    if mode == 'audit':
        raw = restore_observation(code, ROOT.parent / 'global-candidate/cp6-proof/t3')
        kinds = [*(f'case-{case_id}' for case_id in REMAINING_CASES), 'oracle', 'worker-exit']
    else:
        raw = dict(worker_exit=code, recovery_receipt_present=False, test_only=True)
        kinds = ['smoke-before-kill', 'worker-exit']
    if not record('worker-exit', 'worker_exit', raw):
        fail()
    receipts = {}
    for stem in kinds:
        path = spool / 'receipts' / f'{stem}.json'
        if path.is_file():
            ack = read(path)
            data = (spool / 'outbound' / f'{stem}.json').read_bytes()
            if receipt_valid(ack, artifact_name(identity, stem), data):
                receipts[stem] = ack
    all_archived = len(receipts) == len(kinds) and not (spool / 'publisher-failure.json').exists()
    write_once(spool / 'summary.json',
               dict(identity=identity, all_archived=all_archived, receipts=receipts, worker_exit=code))
    if mode == 'smoke':
        need(code == -signal.SIGKILL and all_archived and
             not (spool / 'outbound/smoke-after-kill.json').exists(),
             'P20_EVIDENCE_SMOKE_KILL_OR_ARTIFACT_UNVERIFIED')
        # GitHub stores both artifacts before this disposable smoke can finish.
        print('P20_EVIDENCE_SMOKE_PASS worker_killed=true remote_acks=2 actual_erp_cases=0', flush=True)
        return 0
    return 0 if code == 0 and all_archived else 1


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('audit', 'smoke'))
    parser.add_argument('runner_temp', type=Path)
    args = parser.parse_args()
    base = args.runner_temp.resolve()
    try:
        return run(args.mode, base / 'p20-evidence-config.json', base / 'p20-evidence-spool',
                   base / 'p20-evidence-node')
    except (OSError, ValueError, EvidenceError):
        print('P20_EVIDENCE_BROKER_INCOMPLETE', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
