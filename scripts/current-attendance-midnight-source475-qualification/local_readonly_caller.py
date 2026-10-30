"""Local whole-caller study: real Source/Original env, DB/network hard refused.

Writes are observed (paths/stacks only) to diagnose materializers, not excluded
from source admission. Run from the actual candidate cwd. Output/trace is saved
outside that repository; no product source, checker ROOT or result is replaced.
"""
from pathlib import Path
from hashlib import sha256
import argparse
import contextlib
import io
import json
import os
import runpy
import socket
import subprocess
import sys
import traceback
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
GIT_READ={'rev-parse','diff','status','ls-files','ls-tree','show','log','cat-file','check-attr'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('current-originals','runtime','probe-check'))
    parser.add_argument('--environment',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if Path.cwd().resolve()!=ROOT.resolve()or args.output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('S03_LAWFUL_STUDY_ACTUAL_CANDIDATE_CWD_AND_OUTSIDE_TRACE_REQUIRED')
    env=json.loads(args.environment.read_bytes())
    if set(env)!= {'D17_18_RETAINED_COMBINED_AF_DIRECTORY','CP7_VENDOR_BACKEND11_ORIGINALS',
            'D17_18_ACCEPTED_CONSISTENCY_DIRECTORY','D17_18_RETAINED_FOCUSED64_DIRECTORY',
            'D17_18_ACCEPTED_CONSISTENCY_FOCUSED_DIRECTORY'}:
        raise ValueError('S03_LAWFUL_STUDY_EXACT_REAL_FIVE_ORIGINAL_ENVIRONMENT_REQUIRED')
    os.environ.update(env);os.environ['GIT_NO_LAZY_FETCH']='1';os.environ['GIT_TERMINAL_PROMPT']='0'
    git=lambda *parts:subprocess.check_output(['git','-C',str(ROOT),*parts],text=True).strip()
    before=set(git('ls-files','--others','--exclude-standard').splitlines())
    head=git('rev-parse','HEAD');events=[];attempts=dict(DB=0,network=0,non_readonly_process=0)
    active=True
    def audit(event,values):
        if not active:return
        if event=='open':
            target,mode,flags=values
            writable=(isinstance(mode,str)and any(k in mode for k in 'wax+'))or(isinstance(flags,int)and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
            if writable and isinstance(target,(str,bytes)):
                name=os.fsdecode(target)
                frames=traceback.extract_stack(limit=12)[:-1]
                events.append(dict(event='open_write',path=str(Path(name).absolute()),
                    stack=[dict(file=f.filename,line=f.lineno,function=f.name)for f in frames]))
        elif event in ('os.mkdir','os.rename','os.remove'):
            events.append(dict(event=event,paths=[os.fsdecode(v)for v in values[:2]if isinstance(v,(str,bytes))]))
        elif event=='socket.connect':
            attempts['network']+=1;raise AssertionError('SOURCE_STUDY_NETWORK_FORBIDDEN')
        elif event=='subprocess.Popen':
            executable,command=values[:2]
            if not isinstance(command,(list,tuple))or Path(str(executable)).name!='git':
                attempts['non_readonly_process']+=1;raise AssertionError('SOURCE_STUDY_ONLY_READONLY_GIT_PROCESS_ALLOWED')
            parts=list(command[1:]);index=0
            while index<len(parts)and parts[index]in('-C','--git-dir','--work-tree'):
                index+=2
            if index>=len(parts)or parts[index]not in GIT_READ:
                attempts['non_readonly_process']+=1;raise AssertionError('SOURCE_STUDY_GIT_MUTATION_OR_NETWORK_FORBIDDEN')
    sys.addaudithook(audit)
    import psycopg
    def blocked_db(*a,**kw):
        attempts['DB']+=1;raise AssertionError('SOURCE_STUDY_DATABASE_FORBIDDEN')
    def blocked_network(*a,**kw):
        attempts['network']+=1;raise AssertionError('SOURCE_STUDY_NETWORK_FORBIDDEN')
    psycopg.connect=blocked_db;socket.create_connection=blocked_network;urllib.request.urlopen=blocked_network
    stdout,stderr=io.StringIO(),io.StringIO();status='PASS';error=None
    target=HERE/('probe.py'if args.mode=='probe-check'else'check.py')
    flags={'runtime':['--runtime'],'current-originals':['--current-originals'],'probe-check':['--check']}[args.mode]
    exact_argv=[str(target),*flags];sys.argv=exact_argv
    try:
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            runpy.run_path(str(target),run_name='__main__')
    except BaseException as caught:
        status='FAIL';error=dict(type=type(caught).__name__,message=str(caught),traceback=traceback.format_exc())
    finally:
        active=False
    after=set(git('ls-files','--others','--exclude-standard').splitlines())
    output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    out=stdout.getvalue().encode();err=stderr.getvalue().encode()
    output.with_suffix('.stdout').write_bytes(out);output.with_suffix('.stderr').write_bytes(err)
    report=dict(classification='LOCAL_REAL_WHOLE_SOURCE_ORIGINAL_CLI_WITH_DATABASE_AND_NETWORK_FORBIDDEN',
        status=status,head=head,cwd=str(ROOT),argv=exact_argv,real_Original_environment_keys=sorted(env),
        attempts=attempts,error=error,write_observations=events,
        untracked_before=sorted(before),untracked_after=sorted(after),new_untracked=sorted(after-before),
        stdout=dict(bytes=len(out),sha256=sha256(out).hexdigest()),stderr=dict(bytes=len(err),sha256=sha256(err).hexdigest()),
        source_results_projected=False,checker_ROOT_replaced=False,actual_Native_cases=0,production_go=False)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=status,trace=str(output),writes=len(events),new_untracked=len(after-before),attempts=attempts,error=error)))
    if status!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
