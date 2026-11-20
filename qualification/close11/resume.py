"""Reopen this runner's exact installed database locally, isolated from outbound services."""
import argparse,json,os,secrets,subprocess,sys,tempfile,tarfile,time
from pathlib import Path
from close11.checkpoint import unseal,digest
from close11.source import PRODUCT,TREE,check

def main():
    ap=argparse.ArgumentParser()
    for v in ('installed','checkpoint','key'):ap.add_argument('--'+v,required=True,type=Path)
    args=ap.parse_args()
    result=json.loads(args.installed.read_bytes())
    check((result['product'],result['tree'],result['status'])==(PRODUCT,TREE,'COMMITTED'),'CLOSE11_WRONG_SOURCE')
    check(digest(args.checkpoint)==result['checkpoint']['sha256'],'CLOSE11_ARCHIVE_HASH')
    label='cp7-ffda-audit-'+secrets.token_hex(5);tag=result['postgres_image'];check('@sha256:' in tag,'CLOSE11_UNPINNED_IMAGE')
    def docker(*parameters,**kw):
        return subprocess.run(['docker',*parameters],check=True,**kw)
    volumes=[label+'-data',label+'-config'];started=False
    try:
        docker('pull',tag)
        for name in volumes:docker('volume','create',name)
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'cluster.tar.gz';unseal(args.checkpoint,archive,args.key)
            check(digest(archive)==result['checkpoint']['plaintext_sha256'],'CLOSE11_PLAINTEXT_HASH')
            with archive.open('rb') as stream:
                docker('run','--rm','-i','--network','none','-v',volumes[0]+':/restore/data','-v',volumes[1]+':/restore/config','--entrypoint','sh',tag,'-ec','tar -C /restore -xzf -; chmod 700 /restore/data; chown postgres:postgres /restore/data; gosu postgres pg_verifybackup /restore/data',stdin=stream)
        docker('run','--name',label,'--network','none','-d','-v',volumes[0]+':/var/lib/postgresql/data','-v',volumes[1]+':/etc/postgresql-custom',tag,'postgres','-c','config_file=/etc/postgresql/postgresql.conf','-c','cron.database_name=postgres','-c','cron.launch_active_jobs=off')
        started=True
        cli=['exec','-u','postgres',label,'psql','-U','supabase_admin','-d','cp6_rollback','-XAt','-v','ON_ERROR_STOP=1']
        for _ in range(80):
            try:
                n=docker(*cli,'-c',"select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'erp\\_%' escape '\\'",capture_output=True,text=True).stdout.strip()
                if int(n)>=362:break
            except (subprocess.CalledProcessError,ValueError):pass
            time.sleep(1)
        else:raise RuntimeError('CLOSE11_RESTORED_DATABASE_NOT_READY')
        print('Container '+label+' / database cp6_rollback / public RPCs '+str(n),flush=True)
        print('Run all four auditor cases here. The database and its volumes remain until the auditor removes them.',flush=True)
        print('docker exec -it -u postgres '+label+' psql -U supabase_admin -d cp6_rollback',flush=True)
        print('After evidence has been closed: docker rm -f '+label+' && docker volume rm '+' '.join(volumes),flush=True)
    except BaseException:
        if started:subprocess.run(['docker','rm','-f',label],capture_output=True)
        for vol in volumes:subprocess.run(['docker','volume','rm',vol],capture_output=True)
        raise
if __name__=='__main__':main()
