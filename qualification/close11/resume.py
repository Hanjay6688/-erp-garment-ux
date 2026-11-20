"""Reopen this runner's exact installed database locally, isolated from outbound services."""
import argparse,json,os,secrets,subprocess,sys,tempfile,tarfile,time
from pathlib import Path
from close11.checkpoint import unseal,digest
from close11.source import PRODUCT,TREE,check
from close11.frozen import verify_files

def main():
    ap=argparse.ArgumentParser()
    for v in ('installed','checkpoint'):ap.add_argument('--'+v,required=True,type=Path)
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--key',type=Path);group.add_argument('--receiver-key',type=Path)
    ap.add_argument('--request',type=Path);ap.add_argument('--reply',type=Path)
    ap.add_argument('--container-file',type=Path);ap.add_argument('--network',choices=('none','internal'),default='none')
    ap.add_argument('--socket-dir',type=Path)
    args=ap.parse_args()
    result=json.loads(args.installed.read_bytes())
    check((result['product'],result['tree'],result['status'])==(PRODUCT,TREE,'COMMITTED'),'CLOSE11_WRONG_SOURCE')
    check(digest(args.checkpoint)==result['checkpoint']['sha256'],'CLOSE11_ARCHIVE_HASH')
    label='cp7-ffda-audit-'+secrets.token_hex(5);tag=result['postgres_image'];check('@sha256:' in tag,'CLOSE11_UNPINNED_IMAGE')
    test_env=dict(os.environ,POSTGRES_PASSWORD=secrets.token_urlsafe(32))
    def docker(*parameters,**kw):
        return subprocess.run(['docker',*parameters],check=True,env=test_env,**kw)
    volumes=[label+'-data',label+'-config'];started=False;net=label+'-network' if args.network=='internal' else 'none'
    try:
        docker('pull',tag)
        if net!='none':docker('network','create','--internal',net)
        for name in volumes:docker('volume','create',name)
        cold=result.get('audit_baseline')=='COLD_GLOBAL_WITH_INACTIVE_NATIVE_JOBS'
        verify=verify_files(result)
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'cluster.tar.gz'
            session=None
            if args.receiver_key:
                from close11.audit_access import receive
                check(args.request and args.reply,'CLOSE11_MISSING_GRANT')
                session=receive(args.request,args.reply,args.receiver_key)
            unseal(args.checkpoint,archive,args.key,transferred_key=session)
            check(digest(archive)==result['checkpoint']['plaintext_sha256'],'CLOSE11_PLAINTEXT_HASH')
            with archive.open('rb') as stream:
                docker('run','--rm','-i','--network','none','-v',volumes[0]+':/restore/data','-v',volumes[1]+':/restore/config','--entrypoint','sh',tag,'-ec','tar -C /restore -xzf -; chmod 700 /restore/data; chown postgres:postgres /restore/data; '+verify,stdin=stream)
        socket_args=[]
        if args.socket_dir:
            target=args.socket_dir.resolve();check(not target.exists(),'CLOSE11_NEW_SOCKET_DIR_REQUIRED')
            target.mkdir(mode=0o700,parents=False)
            # Keep the parent private on the audit workstation. PostgreSQL owns the socket subdirectory.
            docker('run','--rm','--network','none','-v',str(target)+':/socket','--entrypoint','sh',tag,'-ec','chown postgres:postgres /socket; chmod 755 /socket')
            socket_args=['-v',str(target)+':/var/run/postgresql']
        docker('run',*socket_args,'--name',label,'--network',net,'-d','-e','POSTGRES_PASSWORD','-v',volumes[0]+':/var/lib/postgresql/data','-v',volumes[1]+':/etc/postgresql-custom',tag,'postgres','-c','config_file=/etc/postgresql/postgresql.conf','-c','cron.database_name='+('cp6_rollback' if cold else 'postgres'),'-c','cron.launch_active_jobs=off')
        started=True
        cli=['exec','-u','postgres',label,'psql','-U','supabase_admin','-d','cp6_rollback','-XAt','-v','ON_ERROR_STOP=1']
        for _ in range(80):
            try:
                n=docker(*cli,'-c',"select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'erp\\_%' escape '\\'",capture_output=True,text=True).stdout.strip()
                if int(n)>=362:break
            except (subprocess.CalledProcessError,ValueError):pass
            time.sleep(1)
        else:raise RuntimeError('CLOSE11_RESTORED_DATABASE_NOT_READY')
        fingerprint=docker(*cli,'-c','select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()::text',capture_output=True,text=True).stdout
        if result.get('server_catalogue_fingerprint'):
            check(json.loads(fingerprint)==result['server_catalogue_fingerprint'],'CLOSE11_RESTORED_FULL25')
        if args.container_file:args.container_file.write_text(label+'\n')
        print('Container '+label+' / database cp6_rollback / public RPCs '+str(n),flush=True)
        print('Run all four auditor cases here. The database and its volumes remain until the auditor removes them.',flush=True)
        print('docker exec -it -u postgres '+label+' psql -U supabase_admin -d cp6_rollback',flush=True)
        print('After evidence has been closed: docker rm -f '+label+' && docker volume rm '+' '.join(volumes),flush=True)
    except BaseException:
        if started:subprocess.run(['docker','rm','-f',label],capture_output=True)
        for vol in volumes:subprocess.run(['docker','volume','rm',vol],capture_output=True)
        if net!='none':subprocess.run(['docker','network','rm',net],capture_output=True)
        raise
if __name__=='__main__':main()
