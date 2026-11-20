"""Copy a checkpointed test cluster, including WAL, while its container is frozen."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import tempfile
from .source import check

SOURCE='supabase_db_cp5-local'

def problem(phase,stderr,code):
    message=stderr.decode(errors='replace').lower()
    for signal in ('no pg_hba.conf entry','could not translate host','no space left','permission denied','no such file','not found','already paused','paused','could not access','invalid mount','not supported','operation not permitted','password authentication failed','is not running','unrecognized option','unable to','does not exist'):
        if signal in message:return ValueError('CLOSE11_COPY '+phase+' '+signal)
    return ValueError('CLOSE11_COPY '+phase+' exit '+str(code))

def docker(phase,args,*,input_file=None,output_file=None,timeout=180):
    proc=subprocess.run(['docker',*args],stdin=input_file,stdout=subprocess.PIPE if output_file is None else output_file,stderr=subprocess.PIPE,timeout=timeout)
    if proc.returncode:raise problem(phase,proc.stderr,proc.returncode)
    if output_file is None:return proc.stdout.decode().strip()

def psql(phase,statement):
    return docker(phase,['exec','-u','postgres',SOURCE,'psql','-XAtq','-v','ON_ERROR_STOP=1','-U','supabase_admin','-d','postgres','-c',statement])

def inventory(archive):
    members=cfg=wal=0;control=version=None
    with tarfile.open(archive,'r|gz') as contents:
        for member in contents:
            name=member.name.removeprefix('./');members+=1
            if name=='data/PG_VERSION':version=contents.extractfile(member).read().strip()
            if name=='data/global/pg_control':control=hashlib.file_digest(contents.extractfile(member),'sha256').hexdigest()
            if name.startswith('config/') and member.isfile():cfg+=1
            if member.isfile() and len(PurePosixPath(name).name)==24 and name.startswith('data/pg_wal/'):wal+=1
            check(name!='data/postmaster.pid','CLOSE11_COPY_STALE_PROCESS_ID')
    check(version==b'17' and control and cfg and wal,'CLOSE11_COPY_PGDATA_CONFIG_WAL')
    return dict(source_control_sha256=control,source_archive_entries=members,configuration_files=cfg,wal_segments=wal)

def verify_files(receipt):
    if receipt.get('audit_baseline')=='COLD_GLOBAL_WITH_INACTIVE_NATIVE_JOBS':
        pin=receipt['cold_control_sha256']
    elif receipt.get('source_backup_kind')=='FROZEN_GLOBAL_WITH_WAL':
        pin=receipt['source_control_sha256']
    else:
        return 'pg_verifybackup /restore/data'
    check(re.fullmatch(r'[0-9a-f]{64}',pin),'CLOSE11_COPY_CONTROL_PIN')
    return 'test ! -e /restore/data/postmaster.pid && echo "'+pin+'  /restore/data/global/pg_control" | sha256sum --check --status && pg_controldata /restore/data >/dev/null'

def freeze(raw,image):
    datadir=PurePosixPath(psql('data directory','show data_directory'))
    check(datadir.is_absolute() and datadir!=PurePosixPath('/'),'CLOSE11_COPY_DATA_DIRECTORY')
    mounts=json.loads(docker('source mounts',['inspect','-f','{{json .Mounts}}',SOURCE]))
    possible=[m for m in mounts if m['Type'] in ('bind','volume') and datadir.is_relative_to(PurePosixPath(m['Destination']))]
    check(possible,'CLOSE11_COPY_DATA_MOUNT');mount=max(possible,key=lambda m:len(m['Destination']))
    rel=datadir.relative_to(mount['Destination']);src=mount.get('Name') if mount['Type']=='volume' else str(PurePosixPath(mount['Source'])/rel)
    check(src and ',' not in src and '..' not in rel.parts,'CLOSE11_COPY_MOUNT_SOURCE')
    spec='type='+mount['Type']+',source='+src+',destination=/snapshot/data,readonly'
    if mount['Type']=='volume' and rel.parts:spec+=',volume-subpath='+str(rel)
    script='set -eu; test -s /snapshot/data/PG_VERSION; test ! -L /snapshot/data/pg_wal; mkdir -m 700 /snapshot/config; tar -xpf - -C /snapshot/config; tar -C /snapshot --exclude=data/postmaster.pid --exclude=data/postmaster.opts -czf - data config'
    psql('checkpoint','checkpoint')
    with tempfile.TemporaryFile() as config:
        docker('read Vault configuration',['exec','-u','0',SOURCE,'tar','-C','/etc/postgresql-custom','-cf','-','.'],output_file=config)
        config.seek(0)
        docker('flush test storage',['exec','-u','0',SOURCE,'sync'])
        docker('pause disposable source',['pause',SOURCE])
        try:
            with raw.open('xb') as destination:
                docker('copy frozen volume',['run','--rm','-i','--network','none','--user','0','--mount',spec,'--entrypoint','sh',image,'-ec',script],input_file=config,output_file=destination,timeout=720)
        finally:
            docker('resume disposable source',['unpause',SOURCE])
    check(psql('verify source resumed','select 1')=='1','CLOSE11_COPY_SOURCE_RESUMED')
    return dict(source_backup_kind='FROZEN_GLOBAL_WITH_WAL',source_checkpoint_observed=True,source_resumed=True,**inventory(raw))

def probe():
    """Exercise the copy and WAL recovery before the costly ERP installation on this runner."""
    import secrets,time
    from .binding import write,diagnostic
    image=docker('source image',['inspect','-f','{{.Image}}',SOURCE]);run=os.environ['GITHUB_RUN_ID'];check(run.isdecimal(),'CLOSE11_COPY_PROBE_ID')
    label='writer-close11-copy-probe-'+run;data=label+'-data';cfg=label+'-config';step='test copy probe';started=False
    try:
        with tempfile.TemporaryDirectory(dir=os.environ['RUNNER_TEMP']) as td:
            archive=Path(td)/'cluster.tar.gz';result=freeze(archive,image)
            for item in (data,cfg):docker('probe volume',['volume','create',item]);
            with archive.open('rb') as src:docker('extract probe volume',['run','--rm','-i','--network','none','--user','0','-v',data+':/restore/data','-v',cfg+':/restore/config','--entrypoint','sh',image,'-ec','tar -C /restore -xzf -; chmod 700 /restore/data; chown postgres:postgres /restore/data; '+verify_files(result)],input_file=src,timeout=360)
            stmt=['docker','run','-d','--network','none','-e','POSTGRES_PASSWORD','--name',label,'-v',data+':/var/lib/postgresql/data','-v',cfg+':/etc/postgresql-custom',image,'postgres','-c','config_file=/etc/postgresql/postgresql.conf','-c','cron.launch_active_jobs=off']
            e=dict(os.environ,POSTGRES_PASSWORD=secrets.token_urlsafe(32));subprocess.run(stmt,env=e,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True);started=True
            for _ in range(90):
                try:
                    if docker('query probe',['exec','-u','postgres',label,'psql','-U','supabase_admin','-d','postgres','-XAt','-c',"select current_setting('server_version_num')||':'||pg_is_in_recovery()::text"])=='170006:false':break
                except ValueError:pass
                time.sleep(1)
            else:raise ValueError('CLOSE11_COPY_PROBE_RECOVERY_FAILED')
            write('copy-probe.json',dict(result,postgres='17.6',restored_initial_cluster=True,product_installed_at_probe=False,auditor_cases=0))
            print('Verified PostgreSQL 17.6 read after WAL recovery on the disposable source copy',flush=True)
    except Exception as ex:diagnostic(step,ex);raise
    finally:
        if started:subprocess.run(['docker','rm','-f',label],capture_output=True)
        for n in (data,cfg):subprocess.run(['docker','volume','rm',n],capture_output=True)

if __name__=='__main__':probe()
