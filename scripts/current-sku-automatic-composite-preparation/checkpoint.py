"""Diagnostic-only snapshots. Never grants case, recovery or acceptance credit."""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
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

    def emit(state):
        event = dict(event='SKU_PARENT_INSTALL_PHASE', phase=name, state=state,
                     run=ident['GITHUB_RUN_ID'], attempt=ident['GITHUB_RUN_ATTEMPT'],
                     head=ident['GITHUB_SHA'], actual_case_credit=0, restoration_verified=False)
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
    print(json.dumps(dict(status='DIAGNOSTIC_CHECKPOINT_WRITTEN', receipt=pin,
                          actual_case_credit=0, restoration_verified=False)), flush=True)


if __name__ == '__main__':
    main()
