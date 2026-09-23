"""Install the pinned package, serve only its disposable clone, then dispose it."""
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import json,os,subprocess,tempfile
import psycopg
import cp6_ao_ap_runtime as prior
import cp6_au_runtime as runtime
import cp6_au_trial as trial
import cp6_successor_regression as boundary
PG=boundary.PG
ADMIN=boundary.ADMIN
OUT=Path('cp6-proof/au-browser')

REST='cp6_au_browser_rest'
def run(*cmd,**kwargs):return subprocess.check_output(cmd,text=True,**kwargs).strip()

def main():
    assert os.environ.get('CP6_AU_BROWSER_CONFIRM')=='cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    source=trial.source()
    report=dict(status='INCOMPLETE',head=source['head'],tree=source['tree'],production_go=False,independent_acceptance=False,hosted_migration_installed=False)
    OUT.mkdir(parents=True,exist_ok=True)
    def save(): (OUT/'RUNTIME.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
        prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        assert cur.execute('select count(*) from auth.users').fetchone()==(0,)
    try:
        trial.install_at()
        runtime.change('install',PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        run('python','scripts/cp6_au_browser_fixture.py','seed')
        values={}
        for line in run('supabase','status','--workdir','../base/cp5-local','-o','env',stderr=subprocess.DEVNULL).splitlines():
            key,sep,value=line.partition('=')
            if sep:values[key]=value.strip('"')
        assert values['API_URL']=='http://127.0.0.1:54321'
        for key in ('ANON_KEY','SERVICE_ROLE_KEY'):print('::add-mask::'+values[key],flush=True)
        names=run('docker','ps','--format','{{.Names}}').splitlines()
        original=next(n for n in names if n.startswith('supabase_rest_'))
        inspected=json.loads(run('docker','inspect',original))[0]
        config=dict(x.split('=',1) for x in inspected['Config']['Env'])
        uri=urlsplit(config['PGRST_DB_URI'])
        config['PGRST_DB_URI']=urlunsplit((uri.scheme,uri.netloc,'/cp6_rollback',uri.query,uri.fragment))
        config.update(PGRST_DB_SCHEMAS='public',PGRST_SERVER_PORT='3000')
        network=next(iter(inspected['NetworkSettings']['Networks']))
        with tempfile.NamedTemporaryFile(mode='w',prefix='cp6-flow-rest-',delete=True) as envfile:
            envfile.write(''.join(f'{k}={v}\n' for k,v in sorted(config.items())));envfile.flush()
            run('docker','run','-d','--name',REST,'--network',network,'--env-file',envfile.name,'-p','127.0.0.1:54329:3000',inspected['Config']['Image'])
        env=dict(os.environ,SUPABASE_ANON_KEY=values['ANON_KEY'],SUPABASE_SERVICE_ROLE_KEY=values['SERVICE_ROLE_KEY'])
        result=subprocess.run(['node','scripts/cp6_au_browser_ui.mjs'],env=env,check=False)
        report['flow_exit_code']=result.returncode
        with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:report['unchanged_catalog_after_flow']=runtime.verified(cur)
        assert result.returncode==0,'AUTH_BROWSER_FLOW_FAILED'
        evidence=json.loads((OUT/'FLOW.json').read_text())
        assert evidence['status']=='PASS' and len(evidence['cases'])==10
        assert all(c['status']=='PASS' for c in evidence['cases'])
        report['browser_cases']=len(evidence['cases'])
        run('docker','rm','-f',REST)
        runtime.refuse_post_use(PG,ADMIN,OUT)
        report['status']='PASS'
    except Exception as exc:
        report.update(status='INCOMPLETE',error_type=type(exc).__name__,error=str(exc)[:500])
        raise
    finally:
        subprocess.run(['docker','rm','-f',REST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=False)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            report['primary_catalog']=prior.verified(cur,'AN')
            report['primary_unchanged']=boundary.snapshot(cur)==primary
            report['auth_residue']=dict(cur.execute("select 'users',count(*) from auth.users union all select 'sessions',count(*) from auth.sessions union all select 'identities',count(*) from auth.identities union all select 'refresh_tokens',count(*) from auth.refresh_tokens").fetchall())
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        report['rest_remaining']=bool(run('docker','ps','-aq','--filter','name=^/'+REST+'$'))
        if not report['primary_unchanged'] or any(report['auth_residue'].values()) or report['clone_remaining'] or report['rest_remaining']:report['status']='INCOMPLETE'
        save()
        assert report['status']=='PASS',report.get('error','FLOW_OR_CLEANUP_INCOMPLETE')
    print('AT real Auth/browser qualification PASS; disposable clone removed',flush=True)

if __name__=='__main__':main()
