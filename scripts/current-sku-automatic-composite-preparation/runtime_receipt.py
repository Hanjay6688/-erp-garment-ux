"""Authorize disposable database cleanup from the current worker's local receipt."""
from pathlib import Path
import json
import os
import re
import tempfile


REPOSITORY = 'Hanjay6688/-erp-garment-ux'
RECEIPT_LIMIT = 64 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def regular(path):
    require(not any(part.is_symlink() for part in (path, *path.parents)), 'CP7_RUNTIME_RECEIPT_SYMLINK')
    return path


def read_json(path):
    with regular(path).open('rb') as source:
        raw = source.read(RECEIPT_LIMIT + 1)
    require(len(raw) <= RECEIPT_LIMIT, 'CP7_RUNTIME_RECEIPT_TOO_LARGE')
    value = json.loads(raw)
    require(type(value) is dict, 'CP7_RUNTIME_RECEIPT_OBJECT_REQUIRED')
    return value


class RuntimeReceipt:
    def __init__(self, directory, identity):
        self.directory = directory
        self.identity = identity

    def write_once(self, filename, phase, **fields):
        target = regular(self.directory / filename)
        body = dict(identity=self.identity, phase=phase, actual_case_credit=0,
                    restoration_verified=False, **fields)
        fd, temporary = tempfile.mkstemp(prefix='.runtime-', dir=self.directory)
        try:
            with os.fdopen(fd, 'wb') as receipt:
                receipt.write((json.dumps(body, sort_keys=True) + '\n').encode())
                receipt.flush()
                os.fsync(receipt.fileno())
            os.link(temporary, target)
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            os.unlink(temporary)

    def read(self, filename):
        try:
            value = read_json(self.directory / filename)
        except FileNotFoundError as error:
            raise ValueError('CP7_RUNTIME_RECEIPT_MISSING:' + filename) from error
        require(value.get('identity') == self.identity, 'CP7_RUNTIME_RECEIPT_WRONG_RUN_OR_ATTEMPT')
        return value

    def prepare(self):
        regular(self.directory).mkdir(mode=0o700, parents=True, exist_ok=True)
        self.write_once('prepared.json', 'PREPARED_BEFORE_DATABASE')

    def require_prepared(self):
        require(self.read('prepared.json').get('phase') == 'PREPARED_BEFORE_DATABASE',
                'CP7_RUNTIME_PREPARED_RECEIPT_REQUIRED')

    def claim_worker(self):
        self.require_prepared()
        # Cleanup and the worker compete for the same immutable decision.
        self.write_once('decision.json', 'WORKER_CLAIMED')

    def finish(self, report_path):
        self.require_prepared()
        require(self.read('decision.json').get('phase') == 'WORKER_CLAIMED',
                'CP7_RUNTIME_WORKER_CLAIM_REQUIRED')
        report = read_json(report_path)
        keys = ('github_run_id', 'github_run_attempt', 'qualification_commit')
        require([report.get(key) for key in keys] == [self.identity[key] for key in ('run', 'attempt', 'head')],
                'CP7_RUNTIME_SUPERVISION_WRONG_RUN_OR_ATTEMPT')
        require(report.get('status') in ('WORKER_COMPLETED_AND_REAPED', 'INCOMPLETE'),
                'CP7_RUNTIME_SUPERVISION_TERMINAL_REQUIRED')
        reaped = (report.get('process_tree_empty') is True and report.get('process_group_empty') is True
                  and type(report.get('worker_exit')) is int)
        self.write_once('terminal.json', 'WORKER_TERMINAL', processes_reaped=reaped)
        return report

    def authorize_stop(self):
        self.require_prepared()
        try:
            self.write_once('decision.json', 'STOP_BEFORE_WORKER')
        except FileExistsError:
            decision = self.read('decision.json').get('phase')
            if decision == 'STOP_BEFORE_WORKER':
                return
            require(decision == 'WORKER_CLAIMED', 'CP7_RUNTIME_STOP_DECISION_INVALID')
            terminal = self.read('terminal.json')
            require(terminal.get('phase') == 'WORKER_TERMINAL' and terminal.get('processes_reaped') is True,
                    'CP7_RUNTIME_STOP_REQUIRES_REAPED_WORKER')


def from_environment(env=None):
    env = os.environ if env is None else env
    identity = dict(repo=env.get('GITHUB_REPOSITORY', ''), run=env.get('GITHUB_RUN_ID', ''),
                    attempt=env.get('GITHUB_RUN_ATTEMPT', ''), job=env.get('GITHUB_JOB', ''),
                    head=env.get('GITHUB_SHA', ''))
    require(env.get('GITHUB_ACTIONS') == 'true' and identity['repo'] == REPOSITORY
            and re.fullmatch('[1-9][0-9]*', identity['run']) and re.fullmatch('[1-9][0-9]*', identity['attempt'])
            and re.fullmatch('[a-zA-Z_][a-zA-Z0-9_-]*', identity['job'])
            and re.fullmatch('[0-9a-f]{40}', identity['head']), 'CP7_RUNTIME_ACTUAL_JOB_IDENTITY_REQUIRED')
    temporary = Path(env.get('RUNNER_TEMP', ''))
    require(temporary.is_absolute() and regular(temporary).is_dir(), 'CP7_RUNTIME_RUNNER_TEMP_REQUIRED')
    name = '{run}-{attempt}-{job}'.format_map(identity)
    return RuntimeReceipt(temporary / 'cp7-runtime-receipts' / name, identity)
