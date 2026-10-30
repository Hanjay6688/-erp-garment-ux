"""Real bound source/Original/runtime callers and named faults, same argv/cwd."""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import io
import json
from midnight_common import HERE, ROOT, NS
from source_fault import snapshot, source_link_fault


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if Path.cwd().resolve() != ROOT.resolve() or args.output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('MIDNIGHT_MATRIX_ACTUAL_CWD_OUTSIDE_OUTPUT_REQUIRED')
    folder = args.output.resolve(); folder.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('midnight_actual_sameprocess_cli_observer', HERE / 'local_readonly_caller.py')
    observer = importlib.util.module_from_spec(spec); spec.loader.exec_module(observer)
    receipts = []

    def invoke(name, mode, *, closed=False, refusal=None, path=None):
        output = folder / (name + '.json'); exit_code = 0
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                observer.main([mode, '--environment', str(args.environment.resolve()), '--output', str(output)])
            except SystemExit as error:
                exit_code = error.code
        report = json.loads(output.read_bytes())
        if any(report['attempts'].values()):
            raise AssertionError(('MIDNIGHT_MATRIX_FORBIDDEN_ATTEMPT', report['attempts']))
        if closed or refusal:
            message = report.get('error', {}).get('message', '')
            expected = 'MIDNIGHT_NATIVE1_CLOSED_ACTUAL_SUCCESSOR14_SIX_ORIGINALS_REQUIRED' if closed else refusal
            if (exit_code != 1 or report['status'] != 'FAIL' or not message.startswith(expected)
                    or (path is not None and path not in message)
                    or report['error']['type'] not in ('ValueError', 'AssertionError')):
                raise AssertionError(('MIDNIGHT_WRONG_NAMED_CLOSED_OR_SOURCE_REFUSAL', name, report['error']))
            status = 'EXPECTED_CLOSED' if closed else 'EXPECTED_SOURCE_REFUSAL'
        else:
            if exit_code or report['status'] != 'PASS':
                raise AssertionError(('MIDNIGHT_ACTUAL_CURRENT475_ORIGINAL_POSITIVE_FAILED', name, report['error']))
            status = 'PASS_CURRENT475_ORIGINALS_ONLY_NOT_NATIVE'
        receipts.append(dict(id=name, status=status, report=str(output), actual_error=report['error'],
            actual_argv=report['argv'], cwd=report['cwd'], head=report['head'],
            DB_network_process_attempts=report['attempts'], new_untracked=report['new_untracked']))
        print(json.dumps(dict(case=name, status=status)), flush=True)

    invoke('INITIAL_CURRENT475_REAL_ORIGINALS', 'current-originals')
    invoke('ACTUAL_BOUND_RUNTIME', 'runtime')
    invoke('ACTUAL_BOUND_PROBE_CHECK', 'probe-check')
    for name, relative, raw in (
            ('UNKNOWN_CODE', 'scripts/midnight_unknown_source_negative.py', b'raise RuntimeError("NEVER_EXECUTE")\n'),
            ('UNKNOWN_JSON', 'cp6-proof/t3/MIDNIGHT_FORGED_SOURCE_NEGATIVE.json', b'{"status":"PASS","actual_Native_cases":14}\n')):
        target = ROOT / relative
        if target.exists() or target.is_symlink():
            raise AssertionError('MIDNIGHT_NEGATIVE_PATH_ALREADY_EXISTS:' + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(raw)
            invoke(name, 'runtime', refusal='MIDNIGHT_UNKNOWN_SOURCE_OR_RECEIPT:', path=relative)
        finally:
            target.unlink()
        invoke(name + '_RESTORED_POSITIVE', 'runtime')
    for name, target in (('LEAF_LINK', HERE / 'FIRST_LOCKED_C097_COUNTER.json'),
                         ('ANCESTOR_LINK', HERE / 'retained-c097')):
        held = folder / (name + '_held_original')
        with source_link_fault(target, held) as before:
            if not target.is_symlink():
                raise AssertionError('MIDNIGHT_SAME_PROCESS_LINK_MUST_EXIST_IMMEDIATELY_BEFORE_CALLER')
            invoke(name, 'runtime', refusal='MIDNIGHT_SOURCE_SYMLINK:', path=str(target.relative_to(ROOT)))
        after = snapshot(target)
        if before != after or target.is_symlink():
            raise AssertionError('MIDNIGHT_SOURCE_RESTORE_NOT_EXACT')
        (folder / (name + '_RESTORE.json')).write_text(json.dumps(dict(path=str(target), before=before, after=after,
            regular_or_directory=True, is_symlink=False, exact_bytes_modes_restored=True), indent=2) + '\n')
        invoke(name + '_RESTORED_POSITIVE', 'runtime')
    invoke('FINAL_REAL_CURRENT475_ORIGINALS', 'current-originals')
    invoke('FINAL_BOUND_PROBE_CHECK', 'probe-check')
    summary = dict(status='PASS', classification='REAL_SOURCE475_ORIGINALS_AND_BOUND_RUNTIME_SOURCE_ONLY_NOT_NATIVE',
        controls=len(receipts), receipts=receipts, same_process_actual_argv_cwd=True,
        checker_ROOT_replaced=False, source_results_projected=False,
        accepted_parent14_head='3c0c5defe55e48cf6f221c868594dd6676d17170',
        actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
        DB_network_nonreadonly_process_attempts=0, production_go=False, independent_acceptance=False)
    (folder / 'MATRIX.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', controls=len(receipts), path=str(folder / 'MATRIX.json'))))


if __name__ == '__main__':
    main()
