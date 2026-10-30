"""Actual source CLI with real Originals; DB/network/non-readonly Git forbidden."""
from pathlib import Path
from hashlib import sha256
import argparse
import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
READONLY_GIT = {'rev-parse', 'diff', 'status', 'ls-files', 'ls-tree', 'show', 'cat-file', 'log', 'check-attr'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if Path.cwd().resolve() != ROOT.resolve() or args.output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('S03_BOUND_ACTUAL_CWD_OUTSIDE_PROOF_REQUIRED')
    rawenv = args.environment.read_bytes(); env = json.loads(rawenv)
    expected = {'D17_18_RETAINED_COMBINED_AF_DIRECTORY', 'CP7_VENDOR_BACKEND11_ORIGINALS',
                'D17_18_ACCEPTED_CONSISTENCY_DIRECTORY', 'D17_18_RETAINED_FOCUSED64_DIRECTORY',
                'D17_18_ACCEPTED_CONSISTENCY_FOCUSED_DIRECTORY'}
    if set(env) != expected or any(type(value) is not str for value in env.values()):
        raise ValueError('S03_BOUND_ACTUAL_FIVE_ORIGINAL_ENVIRONMENTS_REQUIRED')
    os.environ.update(env); os.environ.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0', PATH='/usr/bin:/bin')
    active = True; attempts = []; writes = []
    def audit(event, values):
        if not active: return
        if event.startswith('socket.') and event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo'):
            attempts.append(event); raise AssertionError('S03_BOUND_SOURCE_NETWORK_FORBIDDEN')
        if event == 'subprocess.Popen':
            executable, command = values[:2]
            if Path(os.fsdecode(executable)).name != 'git' or not isinstance(command, (list, tuple)):
                attempts.append('process'); raise AssertionError('S03_BOUND_READONLY_REAL_GIT_ONLY')
            parts = list(command[1:]); offset = 0
            while offset < len(parts) and parts[offset] in ('-C', '--git-dir', '--work-tree'): offset += 2
            if offset >= len(parts) or parts[offset] not in READONLY_GIT:
                attempts.append('git-mutation'); raise AssertionError('S03_BOUND_READONLY_REAL_GIT_ONLY')
        if event == 'open':
            target, mode, flags = values
            writable = isinstance(mode, str) and any(value in mode for value in 'wax+')
            writable = writable or isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writable and isinstance(target, (str, bytes)): writes.append(os.fsdecode(target))
    sys.addaudithook(audit)
    import psycopg
    def forbidden_db(*args, **kwargs):
        attempts.append('DB'); raise AssertionError('S03_BOUND_SOURCE_DB_FORBIDDEN')
    psycopg.connect = forbidden_db
    target = HERE / 'probe.py'; original = sys.argv; values = original[:]
    actual = [str(target), '--check-actual-source']; sys.argv = actual
    stdout, stderr = io.StringIO(), io.StringIO(); error = None; status = 'PASS'
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            runpy.run_path(str(target), run_name='__main__')
        if sys.argv is not actual or actual != [str(target), '--check-actual-source']:
            raise AssertionError('S03_BOUND_SOURCE_ARGV_NOT_RESTORED')
    except BaseException as caught:
        status = 'FAIL'; error = dict(type=type(caught).__name__, message=str(caught), traceback=traceback.format_exc())
    finally:
        original[:] = values; sys.argv = original; active = False
    output = args.output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    out, err = stdout.getvalue().encode(), stderr.getvalue().encode()
    output.with_suffix('.stdout').write_bytes(out); output.with_suffix('.stderr').write_bytes(err)
    git = lambda *parts: subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *parts], text=True).strip()
    report = dict(status=status, classification='ACTUAL_ALL6_ORIGINALS_CANONICAL15_SOURCE_ONLY_NO_DB',
        head=git('rev-parse', 'HEAD'), tree=git('rev-parse', 'HEAD^{tree}'), cwd=str(ROOT), argv=[str(target), '--check-actual-source'],
        Original_environment_keys=sorted(env), Original_environment_sha256=sha256(rawenv).hexdigest(),
        forbidden_attempts=attempts, observed_write_paths=writes, error=error,
        stdout=dict(bytes=len(out), sha256=sha256(out).hexdigest()), stderr=dict(bytes=len(err), sha256=sha256(err).hexdigest()),
        actual_browser_cases=0, actual_Native_cases=0, DB=0, checker_ROOT_replaced=False,
        product_sources_or_method_overridden=False, subprocess_git='/usr/bin/git',
        caller_argv_restored=(sys.argv is original and original == values))
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=status, path=str(output), attempts=attempts, error=error)))
    if status != 'PASS': raise SystemExit(1)


if __name__ == '__main__':
    main()
