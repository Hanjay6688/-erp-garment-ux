"""Local whole actual Source/Original caller negatives and restored positives.

Run only in an isolated clean sparse candidate checkout. No checker/product
function or source dictionary is mocked. The child hard refuses DB/network.
Temporary fault insertion is undone byte-for-byte; original files are retained
outside the candidate during leaf/ancestor link counterexamples.
"""
from pathlib import Path
from hashlib import sha256
import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def snapshot(path):
    """Actual regular bytes/modes; never follow a leaf or descendant link."""
    if path.is_symlink():raise AssertionError('S03_LAWFUL_RESTORE_STILL_A_LINK:'+str(path))
    paths=[path]if path.is_file()else[path,*sorted(path.rglob('*'))]
    result={}
    for entry in paths:
        if entry.is_symlink():raise AssertionError('S03_LAWFUL_RESTORE_DESCENDANT_LINK:'+str(entry))
        name='.'if entry==path else str(entry.relative_to(path))
        row=dict(mode=entry.stat().st_mode&0o7777,kind='file'if entry.is_file()else'directory')
        if entry.is_file():
            raw=entry.read_bytes();row.update(bytes=len(raw),sha256=sha256(raw).hexdigest())
        result[name]=row
    return result


@contextlib.contextmanager
def source_link_fault(target,held):
    """Restore even when unlink/rename/symlink construction or caller raises."""
    before=snapshot(target);directory=target.is_dir();saved=None if directory else target.read_bytes()
    if held.exists()or held.is_symlink():raise AssertionError('S03_LAWFUL_HELD_PATH_EXISTS')
    if not directory:held.write_bytes(saved)
    try:
        # Held originals survive an unexpected restore error; automatic temp
        # cleanup must never erase the sole moved source.
        if directory:target.rename(held)
        else:target.unlink()
        target.symlink_to(held,target_is_directory=directory)
        if not target.is_symlink():raise AssertionError('S03_LAWFUL_LINK_FAULT_NOT_MATERIALIZED')
        yield before
    finally:
        if target.is_symlink():target.unlink()
        if target.exists():
            if snapshot(target)!=before:raise AssertionError('S03_LAWFUL_UNEXPECTED_EXISTING_RESTORE_TARGET')
        elif directory:held.rename(target)
        else:
            target.write_bytes(saved);target.chmod(before['.']['mode'])
        if snapshot(target)!=before:raise AssertionError('S03_LAWFUL_SOURCE_BYTES_MODES_NOT_RESTORED')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if Path.cwd().resolve()!=ROOT.resolve()or args.output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('S03_LAWFUL_MATRIX_ACTUAL_CANDIDATE_CWD_OUTSIDE_OUTPUT_REQUIRED')
    folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=False);receipts=[]
    path=HERE/'local_readonly_caller.py'
    spec=importlib.util.spec_from_file_location('s03_lawful_same_process_actual_cli_observer',path)
    observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
    def invoke(name,mode,expected,*,refusal_prefix=None,refusal_path=None):
        output=folder/(name+'.json')
        command=[mode,'--environment',str(args.environment.resolve()),'--output',str(output)]
        exit_code=0
        # Same runpy CLI/argv/cwd, no child-process filesystem handoff during
        # link faults. The original checker/ROOT/product sources stay intact.
        with contextlib.redirect_stdout(io.StringIO()):
            try:observer.main(command)
            except SystemExit as error:exit_code=error.code
        report=json.loads(output.read_bytes())
        if any(report['attempts'].values()):raise AssertionError(('SOURCE_STUDY_FORBIDDEN_ATTEMPT',report['attempts']))
        if (exit_code==0)!=(expected=='PASS')or report['status']!=expected:
            raise AssertionError(('S03_LAWFUL_MATRIX_UNEXPECTED_RESULT',name,report['error']))
        if expected=='FAIL'and report['error']['type']not in('ValueError','AssertionError'):
            raise AssertionError(('S03_LAWFUL_MATRIX_WRONG_FAILURE',name,report['error']))
        if expected=='FAIL'and(not report['error']['message'].startswith(refusal_prefix)
                or refusal_path not in report['error']['message']):
            raise AssertionError(('S03_LAWFUL_MATRIX_WRONG_SOURCE_REFUSAL_PATH',name,report['error']))
        receipts.append(dict(id=name,mode=mode,status=report['status'],error=report['error'],
            expected_refusal_prefix=refusal_prefix,expected_refusal_path=refusal_path,
            report=str(output),writes=len(report['write_observations']),new_untracked=report['new_untracked']))
        print(json.dumps(dict(case=name,status='EXPECTED_'+expected)),flush=True)
    invoke('INITIAL_REAL_RUNTIME','runtime','PASS')
    invoke('SAME_ARGV_RUNTIME_REPLAY','runtime','PASS')
    invoke('ACTUAL_PROBE_CHECK','probe-check','PASS')
    for name,relative,body in [('UNKNOWN_CODE','scripts/s03_unknown_source_negative.py',b'raise RuntimeError("NEVER_EXECUTE_UNKNOWN_SOURCE")\n'),
            ('UNKNOWN_JSON','cp6-proof/t3/S03_FORGED_SOURCE_NEGATIVE.json',b'{"status":"PASS","actual_Native_cases":14}\n')]:
        path=ROOT/relative
        if path.exists()or path.is_symlink():raise ValueError('S03_LAWFUL_NEGATIVE_PATH_ALREADY_EXISTS')
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            path.write_bytes(body)
            invoke(name,'runtime','FAIL',refusal_prefix='S03_NATIVE14_UNKNOWN_SOURCE_OR_GENERATED_OUTPUT:',refusal_path=relative)
        finally:
            if path.exists():path.unlink()
        invoke(name+'_RESTORED_POSITIVE','runtime','PASS')
    for name,target in [('LEAF_SOURCE_LINK',HERE/'lawful_fixture.py'),('ANCESTOR_SOURCE_LINK',HERE/'retained-9ac-first')]:
        held=folder/(name+'_held_original');assert not held.exists()and not held.is_symlink()
        with source_link_fault(target,held)as before:
            invoke(name,'runtime','FAIL',refusal_prefix='S03_NATIVE14_SOURCE_SYMLINK:',refusal_path=str(target.relative_to(ROOT)))
        restored=snapshot(target)
        (folder/(name+'_RESTORE.json')).write_text(json.dumps(dict(path=str(target),
            real_directory=target.is_dir(),regular_file=target.is_file(),is_symlink=target.is_symlink(),
            before=before,after=restored,exact_bytes_modes_restored=True),indent=2)+'\n')
        invoke(name+'_RESTORED_POSITIVE','runtime','PASS')
    summary=dict(classification='ACTUAL_WHOLE_SOURCE_ORIGINAL_CALLER_NEGATIVES_NOT_DATABASE_QUALIFICATION',
        status='PASS',receipts=receipts,actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        source_results_projected=False,checker_ROOT_replaced=False,
        same_process_actual_CLI_faults=True,production_go=False)
    (folder/'MATRIX.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',controls=len(receipts),report=str(folder/'MATRIX.json'),actual_Native_cases=0)))


if __name__=='__main__':main()
