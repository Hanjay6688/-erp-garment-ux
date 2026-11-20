"""Prepare the inactive ERP scheduler on the isolated physical copy and retain it for audit."""
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time

from .binding import diagnostic
from .checkpoint import digest,seal
from .audit_access import envelope
from .source import HERE,PRODUCT,TREE,check,sha

def provision(work,temporary_root):
    path=work/'close11-evidence/installed.json';receipt=json.loads(path.read_bytes())
    source=temporary_root/'close11-private-source/cluster.tar.gz';check(digest(source)==receipt['checkpoint']['plaintext_sha256'],'CLOSE11_PREPARE_ARCHIVE')
    run=os.environ['GITHUB_RUN_ID'];tag=receipt['postgres_image'];label='close11-audit-'+run
    check(run.isdecimal() and (receipt['product'],receipt['tree'])==(PRODUCT,TREE) and '@sha256:' in tag,'CLOSE11_PREPARE_IDENTITY')
    data=label+'-data';config=label+'-config';step='audit volumes'
    test_env=dict(os.environ,POSTGRES_PASSWORD=secrets.token_urlsafe(32))
    def docker(*args,stdin=None,out=None,timeout=360):
        proc=subprocess.run(['docker',*args],input=stdin,stdout=subprocess.PIPE if out is None else out,stderr=subprocess.PIPE,timeout=timeout,env=test_env)
        if proc.returncode:
            msg=proc.stderr.decode(errors='replace').lower()
            allowed=('no space left','no such file','not found','permission denied','does not exist','must be owner','not available','cannot be loaded','database system is starting up','database system is in recovery','not permitted','wrong database','authentication failed','manifest','could not access','could not connect','invalid checkpoint','does not match')
            reason=next((s for s in allowed if s in msg),'exit '+str(proc.returncode))
            raise ValueError('CLOSE11_PG_CONTAINER '+step+' '+reason)
        return proc.stdout.decode().strip() if out is None else None
    def sql(stmt,db='cp6_rollback'):
        return docker('exec','-i','-u','postgres',label,'psql','-U','supabase_admin','-d',db,'-XAtq','-v','ON_ERROR_STOP=1',stdin=stmt.encode())
    flags=['-v',data+':/restore/data','-v',config+':/restore/config']
    try:
        for item in (data,config):docker('volume','create',item)
        step='copy verified physical source'
        with source.open('rb') as stream:
            subprocess.run(['docker','run','--rm','-i','--network','none',*flags,'--entrypoint','sh',tag,'-ec',
                'tar -C /restore -xzf -; chmod 700 /restore/data; chown postgres:postgres /restore/data; pg_verifybackup /restore/data'],
                stdin=stream,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=480,check=True)
        step='start physical copy'
        docker('run','-d','-e','POSTGRES_PASSWORD','--network','none','--name',label,'-v',data+':/var/lib/postgresql/data','-v',config+':/etc/postgresql-custom',
               tag,'postgres','-c','config_file=/etc/postgresql/postgresql.conf','-c','cron.database_name=cp6_rollback','-c','cron.launch_active_jobs=off')
        for _ in range(90):
            try:
                if sql('select current_setting(\'server_version_num\')')=='170006':break
            except ValueError:pass
            time.sleep(1)
        else:raise ValueError('CLOSE11_RESTORED_GLOBAL_START')
        step='verify sealed catalogue'
        def fingerprint():return json.loads(sql('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()'))
        check(fingerprint()==receipt['server_catalogue_fingerprint'],'CLOSE11_COLD_SEAL_BEFORE_SCHEDULER')
        check(sql("select current_setting('cron.launch_active_jobs')||':'||current_setting('cron.database_name')")=='off:cp6_rollback','CLOSE11_SCHEDULER_BOUNDS')
        step='install three inactive product schedules'
        sql('create extension if not exists pg_cron;')
        jobs=json.loads(sql('select cp7_alert_native.schedules()'))
        if isinstance(jobs,dict):jobs=jobs.get('jobs',jobs.get('schedules'))
        check(isinstance(jobs,list) and len(jobs)==3 and {j['name'] for j in jobs}=={'erp-wa-send','erp-wa-analysis','erp-wa-collect'},'CLOSE11_NATIVE_SCHEDULER_DEFINITIONS')
        sql("""begin;
            do $prepare$ declare j jsonb; old cron.job%rowtype; begin
            for j in select value from jsonb_array_elements(cp7_alert_native.schedules()) loop
                select * into old from cron.job where jobname=j->>'name' and username='postgres';
                if not found then
                    perform cron.schedule_in_database(j->>'name',j->>'schedule',j->>'command',current_database(),'postgres',false);
                elsif old.database<>current_database() or old.schedule<>j->>'schedule' or old.command<>j->>'command' then
                    raise exception 'CLOSE11_SCHEDULER_DRIFT';
                elsif old.active then perform cron.alter_job(old.jobid, active:=false);
                end if;
            end loop;
            end $prepare$;
            commit;""")
        info=json.loads(sql("""select jsonb_build_object(
            'scheduler_database',current_setting('cron.database_name'),
            'scheduler_mode',current_setting('cron.launch_active_jobs'),
            'jobs',(select jsonb_agg(jsonb_build_object('name',j.jobname,'database',j.database,'active',j.active,'command_sha256',encode(sha256(convert_to(j.command,'UTF8')),'hex')) order by j.jobname) from cron.job j where j.jobname in ('erp-wa-collect','erp-wa-analysis','erp-wa-send') and j.username='postgres'),
            'extensions',(select jsonb_object_agg(extname,extversion) from pg_extension where extname in ('pg_cron','supabase_vault','pg_net')),
            'vault_reader',to_regclass('vault.decrypted_secrets') is not null,
            'source_events',(select count(*) from cron.job_run_details d join cron.job j on j.jobid=d.jobid where j.jobname like 'erp-wa-%'))"""))
        check(info['vault_reader'] and {'pg_cron','supabase_vault'}<=info['extensions'].keys() and len(info['jobs'])==3 and all(j['active'] is False and j['database']=='cp6_rollback' for j in info['jobs']),'CLOSE11_AUDIT_SERVICES')
        check(fingerprint()==receipt['server_catalogue_fingerprint'],'CLOSE11_COLD_SEAL_AFTER_SCHEDULER')
        check(docker('inspect','-f','{{.HostConfig.NetworkMode}}',label)=='none','CLOSE11_OFFLINE_COPY')
        step='cold checkpoint'
        docker('stop','-t','60',label)
        control=docker('run','--rm','--network','none',*flags,'--entrypoint','sh',tag,'-ec','test ! -e /restore/data/postmaster.pid; LC_ALL=C pg_controldata /restore/data | grep -Eq "Database cluster state:[[:space:]]+shut down$"; sha256sum /restore/data/global/pg_control').split()[0]
        check(re.fullmatch(r'[0-9a-f]{64}',control),'CLOSE11_COLD_CONTROL')
        target=work/'close11-audit-checkpoint/global-ffda.cp7'
        with tempfile.TemporaryDirectory(dir=temporary_root) as td:
            archive=Path(td)/'database.tar.gz';new=target.with_suffix('.next')
            with archive.open('xb') as out:docker('run','--rm','--network','none',*flags,'--entrypoint','sh',tag,'-ec','tar -C /restore -czf - data config',out=out,timeout=600)
            det=seal(archive,new,HERE/'auditor-public.pem')
            det['plaintext_sha256']=digest(archive)
            # Keep the first archive intact until the full offline handoff succeeds.
            os.replace(new,target)
        receipt.update(checkpoint=det,envelope_sha256=sha(envelope(target)),source_cluster_verified=True,
                       audit_baseline='COLD_GLOBAL_WITH_INACTIVE_NATIVE_JOBS',cold_control_sha256=control,
                       cluster_services=info,catalogue_verified_after_scheduler=True)
        staged=path.with_suffix('.new');staged.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');os.replace(staged,path)
        print('COMMITTED_GLOBAL_AUDITOR_READY full25=verified scheduler_jobs=3 outbound_network=none auditor_cases=0')
    except Exception as exc:
        diagnostic(step,exc);raise
    finally:
        subprocess.run(['docker','rm','-f',label],capture_output=True)
        for v in (data,config):subprocess.run(['docker','volume','rm',v],capture_output=True)
        source.unlink(missing_ok=True)

if __name__=='__main__':provision(Path(os.environ['GITHUB_WORKSPACE']),Path(os.environ['RUNNER_TEMP']))
