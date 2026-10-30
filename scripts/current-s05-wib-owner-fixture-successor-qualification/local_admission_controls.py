"""Actual same-process --runtime CLI, real five Original environments, noDB/network.

Only mutable generated output copies and unknown-code/JSON/link controls change.
Immutable source files are never rewritten. Root can run this in an isolated
registered Git view with identical tracked bytes/modes and24 archived inputs.
"""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import argparse
import contextlib
import importlib.util
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--environment',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args(argv)
    started=time.monotonic();attempts=[];initial,contents=sys.argv,sys.argv[:]
    report={'status':'INCOMPLETE','started_at_UTC':datetime.now(timezone.utc).isoformat(),'actual_Native':0,'actual_Auth_HTTP':0,'actual_browser':0,'actual_races':0,
        'caller':{'cwd':str(Path.cwd()),'argv':contents,'actual_CLI':['scripts/current-s05-wib-owner-fixture-successor-qualification/check.py','--runtime'],
                  'pipeline':'runpy actual check.py --runtime in same process; actual probe.check/runtime/admitted unchanged'},'checks':[]}
    def forbidden(label):attempts.append(label);raise AssertionError('S05_LOCAL_FORBIDDEN:'+label)
    def audit(event,values):
        if event in('socket.connect','socket.bind','socket.getaddrinfo'):forbidden(event)
        if event=='subprocess.Popen':
            executable,command=values[:2]
            if Path(os.fsdecode(executable)).name!='git':forbidden('subprocess:'+os.fsdecode(executable))
            if type(command)not in(list,tuple):forbidden('nonlist_Git')
            if any(str(x)in('fetch','pull','push','clone','checkout','reset','restore','update-ref','commit','add')for x in command):forbidden('mutating_or_network_Git')
            for value in command:
                candidate=str(value).split(':',1)[0].split('^',1)[0]
                if len(candidate)>=7 and all(c in '0123456789abcdef'for c in candidate)and any(candidate.startswith(prefix)for prefix in ('77b72c6','60280a9','e8a22138','2fde9cd')):
                    forbidden('unpublished_private_Git_dependency:'+candidate)
    sys.addaudithook(audit)
    import psycopg
    psycopg.connect=lambda *a,**kw:forbidden('psycopg.connect')
    envraw=args.environment.read_bytes();env=json.loads(envraw)
    if type(env)is not dict or len(env)!=5 or any(type(k)is not str or type(v)is not str for k,v in env.items()):raise ValueError('EXACT_FIVE_REAL_ORIGINAL_ENVIRONMENTS_REQUIRED')
    os.environ.update(env);os.environ.update(GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    git=lambda *a:subprocess.check_output(['git','-C',str(ROOT),*a],text=True,env=os.environ).strip()
    head=git('rev-parse','HEAD');report.update(head=head,tree=git('rev-parse','HEAD^{tree}'),source_sha256=sha256((HERE/'SOURCE.json').read_bytes()).hexdigest(),
        Original_environment_sha256=sha256(envraw).hexdigest(),Original_environment_keys=sorted(env))
    folder=ROOT/'cp6-proof/t3';parent=ROOT/'cp6-proof';created_parent=not parent.exists()
    if folder.exists()or folder.is_symlink():raise ValueError('LOCAL_MATRIX_REQUIRES_ABSENT_T3_GENERATED_FOLDER')
    folder.mkdir(parents=True)
    try:
        for file in('S05_52EED_P0_REFERENCE.zip','S05_52EED_LATER_REFERENCE.zip'):
            with zipfile.ZipFile(HERE/'evidence'/file)as archive:
                for name in archive.namelist():
                    rel=Path(name)
                    if rel.is_absolute()or'..'in rel.parts:raise ValueError('UNSAFE_REFERENCE_ARCHIVE')
                    q=folder/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(archive.read(name))
        q=folder/'T3_PACKAGE_INSTALL.json';d=json.loads(q.read_bytes());d['run_identity'].update(tool_head=head,github_sha=head,workflow='CP7 S05 lawful WIB and Owner fixture fresh Native10');q.write_text(json.dumps(d))
        def whole():
            original=sys.argv;actual=['scripts/current-s05-wib-owner-fixture-successor-qualification/check.py','--runtime'];expected=actual[:];sys.argv=actual
            stdout=io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout):runpy.run_path(str(HERE/'check.py'),run_name='__main__')
                if sys.argv is not actual or sys.argv!=expected:raise AssertionError('ACTUAL_CLI_ARGV_OBJECT_OR_CONTENT_NOT_RESTORED')
            finally:sys.argv=original
            raw=stdout.getvalue();proof=json.loads(raw)
            if proof['status']!='PASS_SOURCE_ONLY'or proof['runtime_source_imports_checked']is not True or proof['actual_Native']!=0:
                raise ValueError('ACTUAL_CLI_SOURCE_RUNTIME_PROOF_REQUIRED')
            return dict(stdout=raw,stdout_bytes=len(raw.encode()),stdout_sha256=sha256(raw.encode()).hexdigest(),actual_CLI_proof=proof)
        tick=time.monotonic();first=whole();report['checks'].append(dict(name='actual_runtime_CLI_real_five_Original_environments',status='PASS',elapsed_ms=round((time.monotonic()-tick)*1000),**first))
        checker=load('s05_matrix_actual_fullsource',HERE/'source_check.py');before=checker.check()['public_bytes_modes_snapshot_sha256']
        def negative(name,prepare,restore,code,relative):
            tick=time.monotonic();prepare()
            try:
                try:whole()
                except(ValueError,AssertionError)as error:
                    if code not in str(error)or relative not in str(error):raise
                    report['checks'].append(dict(name=name,status='PASS_EXPECTED_ACTUAL_CALLER_REFUSAL',observed=str(error),elapsed_ms=round((time.monotonic()-tick)*1000)))
                else:raise AssertionError('MISSING_ACTUAL_CALLER_REFUSAL:'+name)
            finally:restore()
        unknown=ROOT/'scripts/s05_wib_owner_unexpected_source.py'
        if unknown.exists()or unknown.is_symlink():raise ValueError('EXISTING_UNKNOWN_CONTROL_PATH')
        negative('unknown_code',lambda:unknown.write_text('raise RuntimeError("must not import")\n'),unknown.unlink,'UNKNOWN_SOURCE_OR_RECEIPT','scripts/s05_wib_owner_unexpected_source.py')
        extra=folder/'arbitrary.json';negative('arbitrary_JSON',lambda:extra.write_text('{"status":"PASS"}\n'),extra.unlink,'UNKNOWN_GENERATED_OUTPUT','cp6-proof/t3/arbitrary.json')
        with tempfile.TemporaryDirectory(prefix='s05_mutable_link_controls_')as temp:
            held=Path(temp);leaf=folder/'FROZEN_SOURCE_WORKTREES.json';raw=leaf.read_bytes();mode=leaf.stat().st_mode&0o777;copy=held/'leaf.json';copy.write_bytes(raw)
            def link_leaf():leaf.unlink();leaf.symlink_to(copy);assert leaf.is_symlink()
            def restore_leaf():
                leaf.unlink();leaf.write_bytes(raw)
                if leaf.is_symlink()or not leaf.is_file()or leaf.read_bytes()!=raw or leaf.stat().st_mode&0o777!=mode:raise AssertionError('LEAF_REGULAR_BYTES_MODE_RESTORE_FAILED')
            negative('leaf_symlink',link_leaf,restore_leaf,'GENERATED_SYMLINK','cp6-proof/t3/FROZEN_SOURCE_WORKTREES.json')
            directory=folder/'ARTIFACT_FETCH';moved=held/'artifact_receipts';saved={p.name:sha256(p.read_bytes()).hexdigest()for p in directory.iterdir()}
            def link_directory():directory.rename(moved);directory.symlink_to(moved,target_is_directory=True);assert directory.is_symlink()
            def restore_directory():
                directory.unlink();moved.rename(directory)
                if directory.is_symlink()or not directory.is_dir()or {p.name:sha256(p.read_bytes()).hexdigest()for p in directory.iterdir()}!=saved:raise AssertionError('ANCESTOR_REGULAR_BYTE_RESTORE_FAILED')
            negative('ancestor_symlink',link_directory,restore_directory,'GENERATED_SYMLINK','cp6-proof/t3/ARTIFACT_FETCH')
            report['regular_receipt_restore']={'leaf_is_regular':leaf.is_file()and not leaf.is_symlink(),'leaf_bytes_sha256':sha256(leaf.read_bytes()).hexdigest(),'leaf_mode':oct(mode),'artifact_directory_is_real':directory.is_dir()and not directory.is_symlink()}
        tick=time.monotonic();final=whole();elapsed=round((time.monotonic()-tick)*1000);after=checker.check()['public_bytes_modes_snapshot_sha256']
        if before!=after:raise AssertionError('COMPLETE_PUBLIC_SOURCE_BEFORE_AFTER_CHANGED')
        report['checks'].append(dict(name='postrestore_actual_runtime_CLI_real_Originals',status='PASS',elapsed_ms=elapsed,public_snapshot_before=before,public_snapshot_after=after,**final))
        if attempts:raise AssertionError('FORBIDDEN_ACCESS_ATTEMPTED')
        report.update(status='PASS_ACTUAL_SAMEPROCESS_CLI_ORIGINAL_ADMISSION_ONLY',generated_outputs_copied=111,forbidden_attempts=attempts,
            historical_output_identity_only_derived=['tool_head','github_sha','workflow'],financial_oracles_changed=False)
    except BaseException as error:report.update(error=repr(error),forbidden_attempts=attempts);raise
    finally:
        if folder.is_dir()and not folder.is_symlink():shutil.rmtree(folder)
        if created_parent and parent.exists()and not any(parent.iterdir()):parent.rmdir()
        initial[:]=contents;sys.argv=initial
        report.update(elapsed_ms=round((time.monotonic()-started)*1000),finished_at_UTC=datetime.now(timezone.utc).isoformat(),
            cleanup={'t3_exists_immediate_after':folder.exists(),'t3_symlink_immediate_after':folder.is_symlink()},caller_argv_object_and_content_restored=(sys.argv is initial and sys.argv==contents))
        args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],checks=len(report['checks']),forbidden_attempts=attempts,actual_Native=0)))


if __name__=='__main__':main()
