"""Bounded pre-test image startup; retain every attempt and return to GHCR.

The first actual faa attempt hit a transient GHCR limit, followed by three ECR
quota failures. Retry the unchanged startup at most four times; only attempt
two uses ECR. No ERP test, source/oracle, timeout or image tag is changed.
"""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from time import sleep
import json,os,subprocess

START=['supabase','start','--workdir','cp5-local','-x',
    'realtime,imgproxy,studio,postgres-meta,edge-runtime,logflare,vector,supavisor']
STOP=['supabase','stop','--workdir','cp5-local','--no-backup']
REGISTRIES=(None,'public.ecr.aws',None,None)


def start(directory,*,run=subprocess.run,pause=sleep,environment=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    base=dict(os.environ if environment is None else environment)
    receipt=dict(status='INCOMPLETE',scope='DISPOSABLE_STARTUP_BEFORE_ERP_TESTS',
        maximum_attempts=4,image_tags_changed=False,ERP_tests_retried=False,attempts=[])

    def save():
        (directory/'STARTUP_ATTEMPTS.json').write_text(json.dumps(receipt,indent=2)+'\n')

    def logged(command,path,env):
        with path.open('wb')as stream:result=run(command,env=env,stdout=stream,stderr=subprocess.STDOUT,check=False)
        raw=path.read_bytes()
        return dict(exit_code=result.returncode,log=path.name,bytes=len(raw),sha256=sha256(raw).hexdigest())

    for number,registry in enumerate(REGISTRIES,1):
        env=dict(base);env.pop('SUPABASE_INTERNAL_IMAGE_REGISTRY',None)
        if registry is not None:env['SUPABASE_INTERNAL_IMAGE_REGISTRY']=registry
        attempt=dict(number=number,registry=registry or 'default_ghcr',status='RUNNING',
            started_at_utc=datetime.now(timezone.utc).isoformat())
        receipt['attempts'].append(attempt);save()
        attempt['start']=logged(START,directory/f'attempt-{number}-start.log',env)
        if attempt['start']['exit_code']==0:
            attempt['status']='PASS';receipt['status']='PASS';save()
            print(json.dumps(dict(disposable_startup='PASS',attempt=number,registry=attempt['registry'])),flush=True)
            return receipt
        attempt['status']='FAILED';save()
        print((directory/attempt['start']['log']).read_text(errors='replace')[-8000:],flush=True)
        attempt['stop']=logged(STOP,directory/f'attempt-{number}-stop.log',env);save()
        if number<4:pause(number*60)
    save();raise RuntimeError('DISPOSABLE_STARTUP_EXHAUSTED_FOUR_RETAINED_ATTEMPTS')


if __name__=='__main__':
    start(Path('../auditor/cp6-proof/t3/disposable-startup-attempts'))
