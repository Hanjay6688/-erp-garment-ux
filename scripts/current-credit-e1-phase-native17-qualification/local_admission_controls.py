"""Whole actual source/runtime admission with real archived Original inputs.

This optional LOCAL command never runs the engine, GET, database or Supabase.
Its audit hook refuses network, every non-Git subprocess and private Git heads.
Historical output files are copied, source bytes are never altered.
"""
from pathlib import Path
from hashlib import sha256
import argparse
import contextlib
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=('60280a9','e8a22138','824','ac68','3a0')


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],text=True,
        env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0'}).strip()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    overall_started=time.monotonic()
    attempts=[];report={'status':'INCOMPLETE','actual_Native':0,'actual_Auth_HTTP':0,'actual_browser':0,'actual_races':0,
        'guards':{'DB':True,'network':True,'non_Git_subprocess':True,'private_Git_heads':True},'checks':[],
        'started_at_UTC':datetime.now(timezone.utc).isoformat(),
        'caller':{'cwd':str(Path.cwd()),'argv':sys.argv[:],
                  'pipeline':'probe.runtime() then returned engine.admitted()',
                  'engine_execute_called':False,'inherited_argv_context':'exact frozen argv_boundary.py'}}
    initial=sys.argv;contents=initial[:]
    def refuse(label):
        attempts.append(label);raise AssertionError('E_PHASE_LOCAL_FORBIDDEN:'+label)
    def audit(event,values):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo'):refuse(event)
        if event=='subprocess.Popen':
            executable,command=values[:2]
            if Path(os.fsdecode(executable)).name!='git':refuse('subprocess:'+os.fsdecode(executable))
            if type(command)is not list and type(command)is not tuple:refuse('non_list_Git_command')
            if any(str(value)in ('fetch','pull','push','clone','checkout','reset','restore','update-ref','commit','add')for value in command):refuse('mutating_or_network_Git')
            for value in command:
                # Only actual object-bearing arguments can invoke a private object.
                head=str(value).split(':',1)[0].split('^',1)[0]
                if len(head)>=7 and all(c in '0123456789abcdef'for c in head)and any(head.startswith(p)for p in PRIVATE):refuse('private_Git_object:'+head)
    sys.addaudithook(audit)
    import psycopg
    psycopg.connect=lambda *a,**kw:refuse('psycopg.connect')
    env_raw=args.environment.read_bytes();env=json.loads(env_raw)
    if type(env)is not dict or not all(type(k)is str and type(v)is str for k,v in env.items()):raise ValueError('EXACT_ORIGINAL_ENVIRONMENT_REQUIRED')
    os.environ.update(env);os.environ.update(GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    cfg=json.loads((HERE/'CONFIG.json').read_bytes());head=git('rev-parse','HEAD')
    report.update(head=head,tree=git('rev-parse','HEAD^{tree}'),source_sha256=sha256((HERE/'SOURCE.json').read_bytes()).hexdigest(),
        Original_environment_sha256=sha256(env_raw).hexdigest(),Original_environment_keys=sorted(env))
    folder=ROOT/'cp6-proof/t3';parent_folder=ROOT/'cp6-proof';created_parent=not parent_folder.exists()
    if folder.exists()or folder.is_symlink():raise ValueError('LOCAL_CONTROL_REQUIRES_ABSENT_T3_OUTPUT_FOLDER')
    folder.mkdir(parents=True)
    try:
        for file in ('E8BE4_P0_REFERENCE.zip','E8BE4_LATER_REFERENCE.zip'):
            with zipfile.ZipFile(HERE/'evidence'/file)as archive:
                for name in archive.namelist():
                    relative=Path(name)
                    if relative.is_absolute()or'..'in relative.parts:raise ValueError('UNSAFE_REFERENCE_ARCHIVE')
                    p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.read(name))
        for name in ('D1_TARGETED_CLIENT.json','E1_TARGETED_CLIENT.json'):
            (folder/name).write_bytes(gzip.decompress((HERE/'evidence'/(name+'.gz')).read_bytes()))
        p=folder/'T3_PACKAGE_INSTALL.json';value=json.loads(p.read_bytes());value['run_identity'].update(tool_head=head,github_sha=head,workflow='CP7 A current E1 consumer phase fresh Native17');p.write_text(json.dumps(value))
        with tempfile.TemporaryDirectory(prefix='e_phase_actual_D1_raw_')as temp:
            originals=Path(temp)
            retained=ROOT/'scripts/current-credit-e1-current-d1-native17-qualification/retained-17ac'
            for key in ('original','native_group','package','package_files','backup_drill'):
                item=cfg['accepted_D1'][key]
                raw=gzip.decompress((retained/(item['name']+'.gz')).read_bytes())
                if len(raw)!=item['bytes']or sha256(raw).hexdigest()!=item['sha256']:raise ValueError('ACTUAL_D1_RAW_PIN_CHANGED')
                (originals/item['name']).write_bytes(raw)
            os.environ['CP7_E1_D1_ORIGINALS']=str(originals)
            probe=load('e_phase_actual_whole_probe',HERE/'probe.py')
            def whole():
                engine=probe.runtime();proof=engine.admitted()
                if engine.product.sources()!=proof['current_installation']:raise ValueError('NATURAL_PRODUCT_SOURCE_GRAPH_CHANGED')
                if len(engine.product.functions())!=41:raise ValueError('ACTUAL_DYNAMIC_PRIVATE41_REQUIRED')
                return proof
            started=time.monotonic();proof=whole()
            elapsed_ms=round((time.monotonic()-started)*1000)
            report['checks'].append({'name':'actual_runtime_and_real_Original_admission_with118generated_outputs','status':'PASS','seconds':elapsed_ms/1000,'elapsed_ms':elapsed_ms,
                'retained_D1':proof['retained_D1'],'private_functions':41,'current_E_files':proof['current_installation']['files'],
                'current_full_graph_sha256':sha256(json.dumps(proof['current_installation'],sort_keys=True).encode()).hexdigest(),
                'full_runtime_admission_status':proof['status']})
            source=load('e_phase_actual_full_closure',HERE/'source_check.py')
            before=source.check()['public_bytes_modes_snapshot_sha256']
            def negative(name,prepare,restore,token):
                started=time.monotonic()
                prepare()
                try:
                    try:whole()
                    except (ValueError,AssertionError)as error:
                        if token not in str(error):raise
                        report['checks'].append({'name':name,'status':'PASS_EXPECTED_REFUSAL','observed':str(error),
                                                'elapsed_ms':round((time.monotonic()-started)*1000)})
                    else:raise AssertionError('MISSING_WHOLE_CALLER_REFUSAL:'+name)
                finally:restore()
            unknown=ROOT/'scripts/e_phase_unexpected_source.py'
            if unknown.exists()or unknown.is_symlink():raise ValueError('UNEXPECTED_EXISTING_CONTROL_PATH')
            negative('unknown_code',lambda:unknown.write_text('raise RuntimeError("must never import")\n'),unknown.unlink,'UNKNOWN_SOURCE_OR_RECEIPT')
            extra=folder/'arbitrary.json'
            negative('arbitrary_JSON',lambda:extra.write_text('{"status":"PASS"}\n'),extra.unlink,'UNKNOWN_GENERATED_OUTPUT')
            target=folder/'FROZEN_SOURCE_WORKTREES.json';saved=target.read_bytes();held=originals/'held_leaf.json';held.write_bytes(saved)
            def leaf():target.unlink();target.symlink_to(held)
            def undo_leaf():target.unlink();target.write_bytes(saved)
            negative('receipt_leaf_symlink',leaf,undo_leaf,'GENERATED_SYMLINK')
            directory=folder/'ARTIFACT_FETCH';held_directory=originals/'held_artifacts'
            def ancestor():directory.rename(held_directory);directory.symlink_to(held_directory,target_is_directory=True)
            def undo_ancestor():directory.unlink();held_directory.rename(directory)
            negative('receipt_ancestor_symlink',ancestor,undo_ancestor,'GENERATED_SYMLINK')
            started=time.monotonic();proof=whole();elapsed_ms=round((time.monotonic()-started)*1000)
            after=source.check()['public_bytes_modes_snapshot_sha256']
            if before!=after:raise ValueError('PUBLIC_SOURCE_BEFORE_AFTER_CHANGED')
            report['checks'].append({'name':'post_restore_same_caller_full_runtime_and_Original_admission','status':'PASS','elapsed_ms':elapsed_ms,
                                    'public_snapshot_before':before,'public_snapshot_after':after})
        if attempts:raise ValueError('FORBIDDEN_ACCESS_WAS_ATTEMPTED')
        report.update(status='PASS_LOCAL_SOURCE_AND_REAL_ORIGINAL_ADMISSION_ONLY',forbidden_attempts=attempts,generated_outputs_copied=118,
            historical_output_identity_derivation=['tool_head','github_sha','workflow'],financial_oracles_changed=False)
    except BaseException as error:
        report.update(error=repr(error),forbidden_attempts=attempts)
        raise
    finally:
        if folder.is_dir()and not folder.is_symlink():shutil.rmtree(folder)
        if created_parent and parent_folder.exists()and not any(parent_folder.iterdir()):parent_folder.rmdir()
        initial[:]=contents;sys.argv=initial
        report.update(elapsed_ms=round((time.monotonic()-overall_started)*1000),finished_at_UTC=datetime.now(timezone.utc).isoformat(),
            cleanup={'t3_exists_immediately_after_removal':folder.exists(),'t3_symlink_immediately_after_removal':folder.is_symlink()},
            caller_argv_object_and_content_restored=(sys.argv is initial and sys.argv==contents))
        args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],checks=len(report['checks']),actual_Native=0,forbidden_attempts=attempts)))


if __name__=='__main__':main()
