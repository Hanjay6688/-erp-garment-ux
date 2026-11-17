"""Archive small, synthetic P21 receipts while the owning worker is running."""

from hashlib import sha256
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import monotonic, sleep

from audit.codex import p20_evidence as evidence
from . import installed, mode


ROOT = Path(__file__).absolute().parents[2]
LABELS = ('installed-schema', *installed.CHECKS, 'worker-exit')
CONTRACT = 'cp7.writer.p21.install-checkpoint.v1'


def identity(run_id, runner):
    return dict(run_id=run_id, runner=runner, attempt=1, product=mode.PRODUCT, tree=mode.PRODUCT_TREE,
                switch_roll_head=os.environ['CP7_P21_SWITCH_ROLL_HEAD'],
                switch_roll_tree=os.environ['CP7_P21_SWITCH_ROLL_TREE'])


def current_identity():
    return identity(int(os.environ['GITHUB_RUN_ID']), os.environ['GITHUB_SHA'])


def envelope(label, details):
    return dict(contract=CONTRACT, identity=current_identity(), label=label, details=details,
                created_at=evidence.stamp(), installed_P21_acceptance=False, production_go=False)


def record_case(label, proof):
    evidence.need(label in ('installed-schema', *installed.CHECKS), 'CP7_P21_CHECKPOINT_LABEL')
    # Never publish Planner payloads, raw catalogue rows, user IDs, or SQL error text.
    details = {key: value for key, value in proof.items() if type(value) is bool}
    details['status'] = proof['status']
    if proof.get('first_failure'):
        code = proof['first_failure']['code']
        if safe_code(code):
            details['first_failure'] = code
    path = Path(os.environ['RUNNER_TEMP']) / 'cp7-live-parent/p21-checkpoints/outbound' / (label + '.json')
    evidence.write_once(path, envelope(label, details))


def safe_code(code):
    return isinstance(code, str) and evidence.CODE.fullmatch(code) is not None


def artifact_name(proof):
    return f"writer-p21-{proof['identity']['run_id']}-1-{proof['label']}"


def validate(path, run):
    raw = path.read_bytes()
    evidence.need(len(raw) <= 12000, 'CP7_P21_CHECKPOINT_SIZE')
    proof = evidence.read(path)
    evidence.need(proof['identity'] == identity(run['run_id'], run['head'])
                  and proof['contract'] == CONTRACT and path.stem == proof['label']
                  and proof['label'] in (*LABELS, 'progress-start')
                  and proof['installed_P21_acceptance'] is proof['production_go'] is False,
                  'CP7_P21_CHECKPOINT_IDENTITY')
    return proof, raw


def archived(spool, run):
    proofs = {}
    for label in (*LABELS, 'progress-start'):
        try:
            path = spool / 'outbound' / f'{label}.json'
            proof, raw = validate(path, run)
            ack = evidence.read(spool / 'receipts' / path.name)
            if not evidence.receipt_valid(ack, artifact_name(proof), raw):
                return {}
            proofs[label] = ack
        except (OSError, KeyError, ValueError, evidence.EvidenceError):
            return {}
    return proofs


def main():
    import ordinary_run

    # Reuse the bounded, previously exercised transport and progress scanner.
    sys.path.insert(0, str(ROOT / 'qualification/audit/codex'))
    from p20_publish import (CAPTURED_ENVS, EvidenceError, Progress, restore_observation, upload)

    evidence.need(mode.enabled(), 'CP7_P21_DISPOSABLE_MODE_REQUIRED')
    run = ordinary_run.identity()
    work, scratch, output = ordinary_run.paths()
    spool = scratch / 'p21-checkpoints'
    node_home = Path(os.environ['RUNNER_TEMP']) / 'p20-evidence-node'
    (spool / 'outbound').mkdir(parents=True, mode=0o700)
    (spool / 'receipts').mkdir(mode=0o700)

    def drain():
        for path in sorted((spool / 'outbound').glob('*.json')):
            target = spool / 'receipts' / path.name
            if target.exists():
                continue
            proof, raw = validate(path, run)
            name = artifact_name(proof)
            try:
                artifact_id, archive_sha = upload(path, name, node_home)
            except (EvidenceError, OSError, subprocess.TimeoutExpired):
                evidence.write_once(target, dict(status='UPLOAD_FAILED', artifact_name=name))
                print(f'CP7_P21_CHECKPOINT_UPLOAD_FAILED {path.stem}', flush=True)
            else:
                ack = dict(status='UPLOADED', artifact_id=artifact_id, artifact_name=name,
                           archive_sha256=archive_sha, document_sha256=sha256(raw).hexdigest())
                evidence.write_once(target, ack)
                print(f'CP7_P21_CHECKPOINT_UPLOADED {path.stem} artifact={artifact_id}', flush=True)

    progress = Progress()
    evidence.write_once(spool / 'outbound/progress-start.json', envelope('progress-start', progress.sample(spool)))
    drain()
    start_receipt = evidence.read(spool / 'receipts/progress-start.json')
    evidence.need(start_receipt['status'] == 'UPLOADED', 'CP7_P21_CHECKPOINT_STORAGE_REQUIRED')
    log_path = scratch / 'ordinary-supervise.log'
    cmd = [sys.executable, '-u', '-B', str(ROOT / 'qualification/ordinary_run.py'), 'supervise']
    env = {key: value for key, value in os.environ.items()
           if key not in (*CAPTURED_ENVS, 'GH_TOKEN', 'GITHUB_TOKEN')
           and not key.startswith(('ACTIONS_CACHE_', 'ACTIONS_ID_TOKEN_'))}
    interrupted = []
    signals = (signal.SIGINT, signal.SIGTERM)
    previous = {sig: signal.signal(sig, lambda signum, _: interrupted.append(signum)) for sig in signals}
    try:
        with log_path.open('xb') as log, subprocess.Popen(cmd, cwd=work, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, env=env) as child:
            sent = False
            next_progress = monotonic() + 60
            try:
                while child.poll() is None:
                    if interrupted and not sent:
                        child.send_signal(signal.SIGINT)
                        sent = True
                    progress.scan(log_path)
                    progress.scan(scratch / 'ordinary-worker.log')
                    drain()
                    if monotonic() >= next_progress:
                        print(f'CP7_P21_PROGRESS {progress.phase} {progress.phase_state} '
                              f'seconds={round(monotonic() - progress.last)}', flush=True)
                        next_progress = monotonic() + 60
                    sleep(0.2)
            except BaseException:
                if child.poll() is None:
                    child.send_signal(signal.SIGINT)
                raise
            code = child.wait()
        progress.scan(log_path)
        progress.scan(scratch / 'ordinary-worker.log')
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    evidence.write_once(spool / 'outbound/worker-exit.json', envelope('worker-exit', restore_observation(code, output)))
    drain()
    return 0 if code == 0 and archived(spool, run) else 1


if __name__ == '__main__':
    raise SystemExit(main())
