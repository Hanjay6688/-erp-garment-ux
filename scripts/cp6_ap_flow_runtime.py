"""Install the pinned package, serve only its disposable clone, then dispose it."""
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import json,os,subprocess,tempfile,time,traceback
import psycopg
import cp6_ao_ap_maintenance as maintenance
import cp6_ao_ap_runtime as runtime
from cp6_ao_ap_inventory import data
from cp6_ap_flow_fixture import PG,ADMIN,OUT

ROOT=Path(__file__).resolve().parents[1]
CONTROL='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
REST='cp6_ap_flow_rest'
def run(*cmd,**kwargs):return subprocess.check_output(cmd,text=True,**kwargs).strip()

def main():
    assert os.environ.get('CP6_AP_FLOW_CONFIRM')=='cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    report=dict(status='INCOMPLETE',production_go=False,independent_acceptance=False,hosted_migration_installed=False)
    def save(): (OUT/'RUNTIME.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    with psycopg.connect(CONTROL) as conn,conn.cursor() as cur:
        runtime.verified(cur,'AN');primary=data(cur)
        assert cur.execute('select count(*) from auth.users').fetchone()==(0,)
    try:
        for family in ('AO','AP'):
            maintenance.install(family=family,target_pgurl=PG,maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],report_path=OUT/(family+'_INSTALL.json'))
        run('python','scripts/cp6_ap_flow_fixture.py','seed')
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
        result=subprocess.run(['node','scripts/cp6_ap_flow_ui.mjs'],env=env,check=False)
        report['flow_exit_code']=result.returncode
        with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:report['unchanged_catalog_after_flow']=runtime.verified(cur,'AP')
        assert result.returncode==0,'AUTH_BROWSER_FLOW_FAILED'
        for name in ('FLOW','RACES'):
            evidence=json.loads((OUT/(name+'.json')).read_text())
            assert evidence['status']=='PASS',name
            assert len(evidence['cases'])==({'FLOW':29,'RACES':6}[name]),name
            assert all(c['status']=='PASS' for c in evidence['cases']),name
            report[name.lower()+'_cases']=len(evidence['cases'])
        report['status']='PASS'
    except Exception as exc:
        report.update(status='INCOMPLETE',error_type=type(exc).__name__,error=str(exc)[:500])
        raise
    finally:
        subprocess.run(['docker','rm','-f',REST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=False)
        with psycopg.connect(CONTROL) as conn,conn.cursor() as cur:
            report['primary_catalog']=runtime.verified(cur,'AN')
            report['primary_erp_data_unchanged']=data(cur)==primary
            report['auth_residue']=dict(cur.execute("select 'users',count(*) from auth.users union all select 'sessions',count(*) from auth.sessions union all select 'identities',count(*) from auth.identities union all select 'refresh_tokens',count(*) from auth.refresh_tokens").fetchall())
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        report['rest_remaining']=bool(run('docker','ps','-aq','--filter','name=^/'+REST+'$'))
        if not report['primary_erp_data_unchanged'] or any(report['auth_residue'].values()) or report['clone_remaining'] or report['rest_remaining']:report['status']='INCOMPLETE'
        save()
        assert report['status']=='PASS',report.get('error','FLOW_OR_CLEANUP_INCOMPLETE')
    print('AP real Auth/browser qualification PASS; disposable clone removed',flush=True)

if __name__=='__main__':main()
