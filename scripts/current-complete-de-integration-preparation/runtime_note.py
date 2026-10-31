"""Bounded local runner diagnostics; never a business or restoration oracle."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import resource
import shutil
import sys
import threading
import time

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'cp6-proof/t3'


def sample(event,label):
    result=dict(event=event,label=label,utc=datetime.now(timezone.utc).isoformat(),
        monotonic_seconds=round(time.monotonic(),3),pid=os.getpid(),
        self_peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        reaped_children_peak_rss_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        diagnostics_only=True,actual_case_credit=0,production_go=False)
    try:
        memory={line.split(':',1)[0]:int(line.split()[1])for line in Path('/proc/meminfo').read_text().splitlines()
            if line.startswith(('MemTotal:','MemAvailable:'))}
        result['host_memory_KiB']=memory
        for name,path in [('workspace',HERE),('tmp',Path('/tmp'))]:
            value=shutil.disk_usage(path)
            result[name+'_disk_bytes']=dict(total=value.total,free=value.free)
        for name in ('memory.current','memory.max','memory.peak'):
            path=Path('/sys/fs/cgroup')/name
            if path.is_file():result['cgroup_'+name]=path.read_text().strip()
    except OSError as error:result['resource_read_error_type']=type(error).__name__
    return result


def emit(event,label):
    value=sample(event,label)
    raw=(json.dumps(value,sort_keys=True)+'\n').encode()
    try:
        OUT.mkdir(parents=True,exist_ok=True)
        path=OUT/'JOIN_RUNTIME_PROGRESS.jsonl'
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
        try:
            if os.write(descriptor,raw)!=len(raw):raise OSError('SHORT_DIAGNOSTIC_WRITE')
        finally:os.close(descriptor)
    except OSError as error:value['diagnostic_file_error_type']=type(error).__name__
    try:print(json.dumps(value,sort_keys=True),file=sys.stderr,flush=True)
    except OSError:pass
    return value


@contextmanager
def phase(label):
    emit('START',label)
    try:yield
    except BaseException as error:
        emit('RAISED_'+type(error).__name__,label)
        raise
    else:emit('RETURNED',label)


@contextmanager
def monitor(*,interval=30):
    if type(interval)is not int or not 1<=interval<=60:raise ValueError('JOIN_DIAGNOSTIC_INTERVAL')
    stop=threading.Event()
    def run():
        while not stop.wait(interval):emit('HEARTBEAT','OWNING_RUNTIME_PROCESS')
    worker=threading.Thread(target=run,name='joined-runner-diagnostics',daemon=True)
    emit('MONITOR_STARTED','OWNING_RUNTIME_PROCESS');worker.start()
    try:yield
    finally:
        stop.set();worker.join(timeout=1)
        emit('MONITOR_STOPPED','OWNING_RUNTIME_PROCESS')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--snapshot',action='store_true')
    args=parser.parse_args();value=emit('PRE_RUNTIME_RESOURCE_SNAPSHOT','NO_BUSINESS_CASE_EXECUTED')
    if args.snapshot:
        with (OUT/'JOIN_PRE_RUNTIME_RESOURCE.json').open('x')as stream:
            stream.write(json.dumps(value,indent=2)+'\n')
