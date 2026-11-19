"""Physical restore drill on a new, network-isolated Supabase image. This job uses no ERP database."""
import hashlib,json,os,secrets,subprocess,time
from pathlib import Path

TAG='public.ecr.aws/supabase/postgres:17.6.1.165'
run=os.environ['GITHUB_RUN_ID'];assert run.isdecimal() and os.environ['GITHUB_REF']=='refs/heads/audit/astra-cp7-public-ffda'
base='astra-recovery-'+run
volumes=[base+'-source',base+'-restored']
configs=[base+'-source-config',base+'-restored-config']
report={'scope':'Supabase platform recovery, independent of the ERP installation','requested_erp':'ffda5cfceb7ebc196656baa650dffd18dd425047','erp_installed':False,'production_go':False}
env=dict(os.environ,POSTGRES_PASSWORD=secrets.token_urlsafe(32))

def docker(*args,stdin=None,check=True,timeout=220):
    p=subprocess.run(['docker',*args],input=stdin,capture_output=True,text=True,env=env,timeout=timeout)
    if check and p.returncode:
        # Keep public logs free of credentials, service configuration and SQL parameters.
        safe=next((word for word in ('manifest unknown','denied','no space left','connection refused','does not exist','must be owner','permission denied','not available','could not access file','unrecognized configuration parameter','not found','invalid ciphertext','decryption failed','unable to decrypt','job not found','could not find valid entry','invalid key','cannot unschedule','invalid message','wrong key') if word.lower()in p.stderr.lower()),'command failed')
        raise RuntimeError(f'{args[0]}: {safe}')
    return p.stdout.strip()

def query(sql):return docker('exec','-i','-u','postgres',base,'psql','-XAt','-v','ON_ERROR_STOP=1','-U','supabase_admin','-d','postgres',stdin=sql)

def start(volume):
    docker('run','--name',base,'--network','none','-d','-e','POSTGRES_PASSWORD','-v',volume+':/var/lib/postgresql/data','-v',configs[volumes.index(volume)]+':/etc/postgresql-custom',TAG,'postgres','-c','config_file=/etc/postgresql/postgresql.conf','-c','cron.database_name=postgres','-c','cron.launch_active_jobs=off')
    for _ in range(110):
        try:
            if query("select current_database()||':'||current_setting('server_version_num')")=='postgres:170006' and docker('inspect','-f','{{.State.Running}}',base)=='true':
                time.sleep(2);return
        except RuntimeError:pass
        time.sleep(.7)
    raise RuntimeError('PostgreSQL 17.6 not ready')

def stop():docker('stop','-t','50',base);docker('rm',base)

def status():
    rows=query("""select jsonb_build_object(
      'marker',(select state from astra_recovery_probe.marker where id=1),'extra',(select count(*) from astra_recovery_probe.marker where id=2),
      'vault_value_hash',(select encode(sha256(convert_to(decrypted_secret,'UTF8')),'hex') from vault.decrypted_secrets where name='astra-generated-test-value'),
      'job',(select jsonb_build_array(jobname,schedule,active) from cron.job where jobname='astra-offline-restore'),
      'job_runs',(select count(*) from cron.job_run_details where jobid=(select jobid from cron.job where jobname='astra-offline-restore')),
      'outbound_requests',(select count(*) from net.http_request_queue),'extensions',(select jsonb_object_agg(extname,extversion) from pg_extension where extname in ('pg_cron','pg_net','supabase_vault')),
      'network_proof',current_setting('cron.launch_active_jobs'))""")
    return json.loads(rows)

phase='pull official image'
try:
    docker('pull',TAG,timeout=320);report['image_digest']=json.loads(docker('image','inspect','-f','{{json .RepoDigests}}',TAG))[0]
    for v in volumes+configs:docker('volume','create',v)
    phase='start independent cluster';start(volumes[0]);phase='install vendor extensions'
    query('create extension if not exists pg_cron; create extension if not exists pg_net; create extension if not exists supabase_vault;')
    phase='prepare inactive scheduler and synthetic vault value'
    query("""begin; create schema astra_recovery_probe; create table astra_recovery_probe.marker(id integer primary key,state text not null); insert into astra_recovery_probe.marker values(1,'before');
      select vault.create_secret(md5(random()::text||clock_timestamp()::text),'astra-generated-test-value');
      select cron.schedule('astra-offline-restore','0 0 1 1 *','select 1'); select cron.alter_job((select jobid from cron.job where jobname='astra-offline-restore'),active:=false);commit;""")
    before=status();assert len(before['extensions'])==3 and before['job'][-1] is False and before['outbound_requests']==before['job_runs']==0 and before['vault_value_hash']
    phase='cold copy';stop()
    control=docker('run','--rm','--network','none','-v',volumes[0]+':/from:ro','-v',volumes[1]+':/to','-v',configs[0]+':/from-config:ro','-v',configs[1]+':/to-config','--entrypoint','sh',TAG,'-ecu',
            'test -s /from/PG_VERSION && test ! -e /from/postmaster.pid && cp -a /from/. /to/ && cp -a /from-config/. /to-config/ && chown postgres:postgres /to && chmod 700 /to && cmp /from/global/pg_control /to/global/pg_control && sha256sum /to/global/pg_control')
    report['cold_control_sha256']=control.split()[0]
    phase='restart original with configuration';start(volumes[0]);phase='advance marker and scheduler';query("update astra_recovery_probe.marker set state='after' where id=1;insert into astra_recovery_probe.marker values(2,'later');select cron.unschedule('astra-offline-restore');")
    phase='read after advance with vault';advanced=status();assert advanced['marker']=='after' and advanced['extra']==1 and advanced['job']is None;stop()
    phase='start restored data and configuration';start(volumes[1]);phase='compare restored data, scheduler and vault';after=status();assert after==before and after['marker']=='before' and not after['extra'];assert docker('inspect','-f','{{.HostConfig.NetworkMode}}',base)=='none';stop()
    report.update(extensions=after['extensions'],restored_original_row=True,later_row_absent=True,scheduled_job_restored_inactive=True,vault_test_value_matched=True,
                  configuration_volume_restored=True,scheduled_invocations=after['job_runs'],outbound_requests=after['outbound_requests'],network='none',status='PASS');phase='finished'
except Exception as exc:
    report.update(status='INCOMPLETE',error=str(exc)[:115] if type(exc)is RuntimeError else type(exc).__name__)
finally:
    docker('rm','-f',base,check=False)
    for v in volumes+configs:docker('volume','rm',v,check=False)
    report['phase']=phase;print('ASTRA_EXTENSION_RESTORE '+json.dumps(report,separators=(',',':')),flush=True)
if report['status']!='PASS':raise SystemExit(1)
