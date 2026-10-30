"""Real same-process source/Original caller controls. Never Native/DB/browser."""
from hashlib import sha1, sha256
from pathlib import Path
import argparse
import importlib.util
import json
import os
import stat
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = Path('cp6-proof/t3/S03_PARENT14_ORIGINALS')


def snapshot():
    """Every current tracked regular byte/mode/inode, against its real Git blob."""
    raw = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'ls-tree', '-r', '-z', 'HEAD'])
    rows = {}
    for entry in raw.split(b'\0'):
        if not entry: continue
        header, value = entry.split(b'\t', 1); mode, kind, blob = header.decode().split(); name = value.decode()
        path = ROOT / name; info = path.lstat()
        if kind != 'blob' or mode not in ('100644', '100755') or not stat.S_ISREG(info.st_mode):
            raise ValueError('S03_BOUND_PHYSICAL_REGULAR_TRACKED_SOURCE_REQUIRED:' + name)
        if stat.S_IMODE(info.st_mode) != (0o755 if mode == '100755' else 0o644):
            raise ValueError('S03_BOUND_TRACKED_MODE_CHANGED:' + name)
        digest = sha1(b'blob ' + str(info.st_size).encode() + b'\0'); content = sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk); content.update(chunk)
        if digest.hexdigest() != blob:
            raise ValueError('S03_BOUND_CURRENT_GIT_BLOB_CHANGED:' + name)
        rows[name] = dict(blob=blob, sha256=content.hexdigest(), bytes=info.st_size,
            mode=mode, inode=info.st_ino, device=info.st_dev)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args(argv); out = args.output_directory.resolve()
    if Path.cwd().resolve() != ROOT.resolve() or out.is_relative_to(ROOT.resolve()):
        raise ValueError('S03_BOUND_MATRIX_REAL_CWD_OUTSIDE_PROOF_REQUIRED')
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'MATRIX.json').exists():
        raise ValueError('S03_BOUND_FIRST_MATRIX_OVERWRITE_REFUSED')
    spec = importlib.util.spec_from_file_location('s03_bound_actual_sameprocess_source_runner', HERE / 'local_no_db_source.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    started = time.monotonic(); phases = []; restoration = []; before = snapshot()
    (out / 'TRACKED_BEFORE.json').write_text(json.dumps(before, indent=2) + '\n')
    parent_argv, parent_values = sys.argv, sys.argv[:]

    def whole(name, code=None, path=None):
        target = out / (name + '.json'); elapsed = time.monotonic(); raised = None
        try:
            runner.main(['--environment', str(args.environment.resolve()), '--output', str(target)])
        except SystemExit as caught:
            raised = caught.code
        report = json.loads(target.read_bytes())
        if report['forbidden_attempts'] or report['DB'] or report['actual_Native_cases'] or report['actual_browser_cases']:
            raise AssertionError('S03_BOUND_MATRIX_FORBIDDEN_RUNTIME_ATTEMPT')
        if report['subprocess_git'] != '/usr/bin/git' or report['caller_argv_restored'] is not True:
            raise AssertionError('S03_BOUND_MATRIX_REAL_GIT_AND_ARGV_REQUIRED')
        if code is None:
            if report['status'] != 'PASS' or raised is not None:
                raise AssertionError('S03_BOUND_ACTUAL_WHOLE_POSITIVE_FAILED:' + str(report['error']))
        else:
            error = report['error'] or {}
            if (report['status'] != 'FAIL' or raised != 1 or error.get('type') != 'ValueError'
                    or code not in error.get('message', '') or path not in error.get('message', '')):
                raise AssertionError('S03_BOUND_NAMED_PATH_SPECIFIC_WHOLE_REFUSAL_MISSING:' + name + ':' + str(error))
        phases.append(dict(name=name, status='PASS', expected_refusal=code, expected_path=path,
            receipt=str(target), receipt_sha256=sha256(target.read_bytes()).hexdigest(),
            elapsed_ms=round((time.monotonic() - elapsed) * 1000), actual_new_Native_Auth_browser_credit=0))

    def unknown(name, relative, raw):
        path = ROOT / relative
        if path.exists() or path.is_symlink(): raise ValueError('S03_BOUND_CONTROL_COLLISION:' + relative)
        try:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
            whole(name, 'S03_BROWSER4_UNDECLARED_CURRENT_WHOLE_SOURCE_DELTA', relative)
        finally:
            path.unlink(missing_ok=True)
        if path.exists() or path.is_symlink(): raise AssertionError('S03_BOUND_UNKNOWN_CONTROL_NOT_RESTORED')
        restoration.append(dict(control=name, path=relative, removed=True))

    status = 'PASS'; error = None
    try:
        whole('INITIAL_REAL_FIVE_ENV_ALL_SIX_ORIGINALS')
        unknown('UNKNOWN_CODE_REFUSED', 'scripts/S03_BOUND_UNKNOWN_CONTROL.py', b'pass\n')
        unknown('UNKNOWN_JSON_REFUSED', 'cp6-proof/t3/S03_BOUND_UNKNOWN_CONTROL.json', b'{}\n')
        relative = str(PREFIX / 'INPUT_RECEIPT.json'); target = ROOT / relative
        original = target.read_bytes(); mode = stat.S_IMODE(target.lstat().st_mode)
        held = out / 'HELD_RECEIPT.json'; held.write_bytes(original)
        try:
            target.unlink(); target.symlink_to(held)
            if not target.is_symlink(): raise AssertionError('S03_BOUND_LEAF_SYMLINK_NOT_CONSTRUCTED')
            whole('ORIGINAL_RECEIPT_LEAF_SYMLINK_REFUSED', 'S03_BOUND_INPUT_SYMLINK', relative)
        finally:
            if target.is_symlink(): target.unlink()
            if not target.exists(): target.write_bytes(original); target.chmod(mode)
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or target.is_symlink() or target.read_bytes() != original or stat.S_IMODE(info.st_mode) != mode:
            raise AssertionError('S03_BOUND_LEAF_RESTORATION_NOT_EXACT')
        restoration.append(dict(control='leaf', path=relative, regular=True, symlink=False,
            bytes=len(original), sha256=sha256(original).hexdigest(), mode=oct(mode)))
        folder = ROOT / PREFIX; held_directory = out / 'HELD_ORIGINAL_DIRECTORY_RESTORE_ONLY'
        folder_info = folder.lstat()
        if held_directory.exists(): raise ValueError('S03_BOUND_HELD_DIRECTORY_COLLISION')
        try:
            folder.rename(held_directory); folder.symlink_to(held_directory, target_is_directory=True)
            if not folder.is_symlink(): raise AssertionError('S03_BOUND_ANCESTOR_SYMLINK_NOT_CONSTRUCTED')
            whole('ORIGINAL_ANCESTOR_SYMLINK_REFUSED', 'S03_BOUND_INPUT_SYMLINK', str(PREFIX))
        finally:
            if folder.is_symlink(): folder.unlink()
            if held_directory.exists() and not folder.exists(): held_directory.rename(folder)
        info = folder.lstat()
        if (folder.is_symlink() or not stat.S_ISDIR(info.st_mode)
                or (info.st_ino, info.st_dev, info.st_mode) != (folder_info.st_ino, folder_info.st_dev, folder_info.st_mode)
                or (folder / 'INPUT_RECEIPT.json').read_bytes() != original):
            raise AssertionError('S03_BOUND_ANCESTOR_RESTORATION_NOT_EXACT')
        restoration.append(dict(control='ancestor', path=str(PREFIX), real_directory=True, symlink=False,
            inode_preserved=True, receipt_sha256=sha256(original).hexdigest()))
        whole('POST_RESTORE_REAL_FIVE_ENV_ALL_SIX_ORIGINALS')
        after = snapshot()
        (out / 'TRACKED_AFTER.json').write_text(json.dumps(after, indent=2) + '\n')
        if before != after: raise AssertionError('S03_BOUND_WHOLE_TRACKED_BYTES_MODES_INODES_CHANGED')
        if sys.argv is not parent_argv or sys.argv != parent_values:
            raise AssertionError('S03_BOUND_MATRIX_PARENT_ARGV_NOT_RESTORED')
    except BaseException as caught:
        status = 'FAIL'; error = dict(type=type(caught).__name__, message=str(caught), traceback=traceback.format_exc())
    report = dict(status=status, classification='ACTUAL_SAME_PROCESS_SOURCE_ORIGINAL_CLI_NOT_NATIVE_OR_BROWSER',
        head=subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        tree=subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'rev-parse', 'HEAD^{tree}'], text=True).strip(),
        cwd=str(ROOT), argv=[str(HERE / 'probe.py'), '--check-actual-source'], phases=phases,
        restores=restoration, complete_tracked_files=len(before), complete_tracked_bytes_modes_inodes_unchanged=(status == 'PASS'),
        environment_sha256=sha256(args.environment.read_bytes()).hexdigest(),
        checker_ROOT_or_product_method_override=False, real_Git='/usr/bin/git', DB=0, Native=0, browser=0,
        elapsed_ms=round((time.monotonic() - started) * 1000), error=error)
    (out / 'MATRIX.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=status, phases=len(phases), output=str(out / 'MATRIX.json'), error=error)))
    if status != 'PASS': raise SystemExit(1)


if __name__ == '__main__':
    main()
