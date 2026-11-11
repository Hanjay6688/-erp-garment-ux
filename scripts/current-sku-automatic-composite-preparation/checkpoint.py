"""Diagnostic-only snapshots. Never grants case, recovery or acceptance credit."""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import monotonic_ns, process_time_ns
import argparse
import json
import os
import re
import subprocess
import tempfile

RECEIPTS = (
    'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_PREREQUISITE_FILES.json',
    'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER_PREREQUISITES.json',
    'SKU_CURRENT_MANDOR17_ORIGINAL_ADMISSION.json',
)
SUPERVISION_REPORT = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_RUNTIME_SUPERVISION.json'
TERMINAL_REPORTS = (SUPERVISION_REPORT, 'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json')
PACKAGE_CHECKS = ('installed', 'primary_unchanged', 'security_advisors', 'backup_restore_drill', 'writer_runtime')
BACKUP_CHECKS = ('restore_errors_only_pg_cron', 'catalog_explained', 'data_identical',
                 'engine_answer_present', 'engine_equal')
SENSITIVE_KEYS = {'password', 'secret', 'apikey', 'api_key', 'access_token',
                  'refresh_token', 'service_role_key', 'dsn', 'pgurl'}


def safe_receipt(value):
    if isinstance(value, dict):
        require(not (set(key.lower() for key in value) & SENSITIVE_KEYS), 'SENSITIVE_RECEIPT_REFUSED')
        for item in value.values():
            safe_receipt(item)
    elif isinstance(value, list):
        for item in value:
            safe_receipt(item)
    elif isinstance(value, str):
        require(not re.search(r'://[^/\s]+:[^@\s]+@', value), 'CREDENTIAL_URL_REFUSED')


def admission_receipts(root):
    result = {}
    for name in RECEIPTS:
        path = root / 'cp6-proof' / 't3' / name
        require(not any(p.is_symlink() for p in (path, *path.parents)), 'RECEIPT_SYMLINK_REFUSED')
        require(path.is_file() and path.stat().st_size <= 2 * 1024 * 1024, 'BOUNDED_ADMISSION_RECEIPT_REQUIRED:' + name)
        raw = path.read_bytes()
        value = json.loads(raw)
        require(isinstance(value, dict), 'OBJECT_RECEIPT_REQUIRED')
        safe_receipt(value)
        result[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest(),
                            original_utf8=raw.decode('utf-8'))
    return result


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(env):
    result = {key: env.get(key, '') for key in
              ('GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT')}
    require(result['GITHUB_REPOSITORY'] == 'Hanjay6688/-erp-garment-ux', 'WRONG_REPOSITORY')
    require(re.fullmatch(r'[0-9a-f]{40}', result['GITHUB_SHA']), 'FULL_CANDIDATE_SHA_REQUIRED')
    for key in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'):
        require(re.fullmatch(r'[1-9][0-9]*', result[key]), 'POSITIVE_RUN_IDENTITY_REQUIRED')
    return result


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args],
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH='1'),
                                   stderr=subprocess.PIPE, timeout=30).decode().strip()


def source_checkpoint(root, env):
    """Observe source identity only; prior admission still owns all assertions."""
    root = Path(root).absolute()
    require(not any(p.is_symlink() for p in (root, *root.parents)), 'SOURCE_SYMLINK_REFUSED')
    ident = identity(env)
    head = git(root, 'rev-parse', 'HEAD')
    require(head == ident['GITHUB_SHA'], 'CANDIDATE_HEAD_MISMATCH')
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'TRACKED_SOURCE_DIRTY')
    return dict(schema='CP7_DIAGNOSTIC_CHECKPOINT_V1', identity=ident,
                checkpoint='BEFORE_DISPOSABLE_DATABASE', source_head=head,
                source_tree=git(root, 'rev-parse', 'HEAD^{tree}'),
                admission_receipts=admission_receipts(root),
                observed_at_utc=datetime.now(timezone.utc).isoformat(),
                status='DIAGNOSTIC_ONLY', actual_case_credit=0,
                restoration_verified=False, independent_acceptance=False,
                production_go=False)


def terminal_observation(root, env):
    """Keep small diagnostic facts available even if artifact creation fails."""
    ident = identity(env)
    head, run, attempt = (ident[key] for key in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'))
    originals, reports = {}, {}
    for name in TERMINAL_REPORTS:
        path = root / name
        require(not any(p.is_symlink() for p in (path, *path.parents)), 'TERMINAL_REPORT_SYMLINK_REFUSED')
        if not path.exists():
            continue
        require(path.is_file(), 'TERMINAL_REGULAR_REPORT_REQUIRED')
        with path.open('rb') as source:
            raw = source.read(2 * 1024 * 1024 + 1)
        require(len(raw) <= 2 * 1024 * 1024, 'TERMINAL_REPORT_TOO_LARGE')
        reports[name] = json.loads(raw)
        require(type(reports[name]) is dict, 'TERMINAL_REPORT_OBJECT_REQUIRED')
        originals[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    result = dict(event='SKU_TERMINAL_LOG_CHECKPOINT', identity=ident, originals=originals,
                  actual_case_credit=0, restoration_verified=False, canonical_archive_verified=False)
    worker = reports.get(SUPERVISION_REPORT)
    if worker is not None:
        require([worker.get(key) for key in ('qualification_commit', 'github_run_id', 'github_run_attempt')]
                == [head, run, attempt], 'TERMINAL_WORKER_WRONG_RUN_OR_ATTEMPT')
        result['worker'] = {key: worker.get(key) for key in
                            ('worker_exit', 'deadline_reached', 'orphaned_child', 'process_group_empty',
                             'process_tree_empty')}
        require(all(value is None or type(value) in (int, bool) for value in result['worker'].values()),
                'TERMINAL_WORKER_TYPED_STATUS_REQUIRED')
    package = reports.get('T3_PACKAGE_INSTALL.json')
    if package is not None:
        bound = package.get('run_identity') or {}
        require([bound.get(key) for key in ('tool_head', 'github_sha', 'run_id', 'run_attempt')]
                == [head, head, run, attempt], 'TERMINAL_PACKAGE_WRONG_RUN_OR_ATTEMPT')
        result['package_checks'] = {key: (package.get('gate') or {}).get(key) is True for key in PACKAGE_CHECKS}
    backup = reports.get('T3_BACKUP_RESTORE_DRILL.json')
    if backup is not None:
        data = backup.get('data') or {}
        tables = data.get('tables')
        result['backup'] = dict(checks={key: (backup.get('checks') or {}).get(key) is True for key in BACKUP_CHECKS},
                                identical=backup.get('status') == 'RESTORED_IDENTICAL',
                                zero_row_differences=data.get('differ') == {},
                                observed_tables=tables if type(tables) is int else None)
    return result


def immutable_json(path, value):
    """Fsync then atomically link without replacing any existing receipt."""
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'OUTPUT_SYMLINK_REFUSED')
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd, temporary = tempfile.mkstemp(prefix='.checkpoint-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.link(temporary, path)  # EEXIST preserves earlier receipts, including failed attempts.
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        os.unlink(temporary)
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


@contextmanager
def observe_parent_phase(name):
    """Record the real call in the job log without affecting its transaction."""
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        yield
        return
    try:
        ident = identity(os.environ)
    except ValueError:
        # The pre-database checkpoint validates identity. A diagnostic in the
        # installer cannot replace a result or interrupt its recovery.
        yield
        return

    started = monotonic_ns()
    cpu_started = process_time_ns()

    def emit(state):
        event = dict(event='SKU_PARENT_INSTALL_PHASE', phase=name, state=state,
                     run=ident['GITHUB_RUN_ID'], attempt=ident['GITHUB_RUN_ATTEMPT'],
                     head=ident['GITHUB_SHA'], actual_case_credit=0, restoration_verified=False)
        if state != 'STARTED':
            event['elapsed_ms'] = (monotonic_ns() - started) // 1_000_000
            event['process_cpu_ms'] = (process_time_ns() - cpu_started) // 1_000_000
        try:
            print(json.dumps(event, sort_keys=True), flush=True)
        except OSError:
            # A broken log stream cannot interrupt an installer or its recovery.
            pass

    emit('STARTED')
    try:
        yield
    except BaseException:
        emit('FAILED')
        raise
    else:
        emit('COMPLETED')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = source_checkpoint(args.source, os.environ)
    pin = immutable_json(args.output, result)
    from runtime_receipt import from_environment
    from_environment().prepare()
    print(json.dumps(dict(status='DIAGNOSTIC_CHECKPOINT_WRITTEN', receipt=pin,
                          actual_case_credit=0, restoration_verified=False)), flush=True)


if __name__ == '__main__':
    main()
