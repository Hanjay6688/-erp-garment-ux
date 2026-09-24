"""T3 browser check: the unchanged AU browser flow (real Auth/JWT -> public PostgREST -> the existing UI, 10 cases) on
the combined candidate, with the frontend of this candidate branch.

Called by scripts/cp6_t3_package_run.py (mode browser) after the committed release package and AW/AX T1 are installed
on the hosted-faithful clone. It seeds the AU browser fixture (CP6_T3_BROWSER=1: the fixture checks the combined
candidate instead of the AU-only catalog), serves only the clone through a separate PostgREST container, builds and
serves this branch's UI and runs scripts/cp6_au_browser_ui.mjs unchanged. Every created Auth user and the PostgREST
container are removed. Label: T3_PREP (not release evidence).
"""
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import json,os,shutil,subprocess,tempfile

AUDITOR=Path(__file__).resolve().parents[1]
BASE=AUDITOR.parent/'base'/'cp5-local'
REST='cp6_t3_browser_rest'


def run_cmd(*cmd,**kwargs):return subprocess.check_output(cmd,text=True,**kwargs).strip()


def run(out):
    report=dict(label='T3_PREP_BROWSER',status='INCOMPLETE',frontend='candidate branch checkout (auditor)',production_go=False,
                release_evidence=False)
    env=dict(os.environ,CP6_AU_BROWSER_CONFIRM='cp6_rollback',CP6_T3_BROWSER='1')
    try:
        seeded=subprocess.run(['python','scripts/cp6_au_browser_fixture.py','seed'],cwd=AUDITOR,env=env,capture_output=True,text=True)
        report['seed']=dict(exit=seeded.returncode,stderr=seeded.stderr[-2000:])
        assert seeded.returncode==0,'T3_BROWSER_SEED_FAILED'
        values={}
        for line in run_cmd('supabase','status','--workdir',str(BASE),'-o','env',stderr=subprocess.DEVNULL).splitlines():
            key,sep,value=line.partition('=')
            if sep:values[key]=value.strip('"')
        assert values['API_URL']=='http://127.0.0.1:54321'
        for key in ('ANON_KEY','SERVICE_ROLE_KEY'):print('::add-mask::'+values[key],flush=True)
        names=run_cmd('docker','ps','--format','{{.Names}}').splitlines()
        original=next(n for n in names if n.startswith('supabase_rest_'))
        inspected=json.loads(run_cmd('docker','inspect',original))[0]
        config=dict(x.split('=',1) for x in inspected['Config']['Env'])
        uri=urlsplit(config['PGRST_DB_URI'])
        config['PGRST_DB_URI']=urlunsplit((uri.scheme,uri.netloc,'/cp6_rollback',uri.query,uri.fragment))
        config.update(PGRST_DB_SCHEMAS='public',PGRST_SERVER_PORT='3000')
        network=next(iter(inspected['NetworkSettings']['Networks']))
        with tempfile.NamedTemporaryFile(mode='w',prefix='cp6-t3-rest-',delete=True) as envfile:
            envfile.write(''.join(f'{k}={v}\n' for k,v in sorted(config.items())));envfile.flush()
            run_cmd('docker','run','-d','--name',REST,'--network',network,'--env-file',envfile.name,'-p','127.0.0.1:54329:3000',inspected['Config']['Image'])
        flow_env=dict(env,SUPABASE_ANON_KEY=values['ANON_KEY'],SUPABASE_SERVICE_ROLE_KEY=values['SERVICE_ROLE_KEY'])
        result=subprocess.run(['node','scripts/cp6_au_browser_ui.mjs'],cwd=AUDITOR,env=flow_env,check=False)
        report['flow_exit_code']=result.returncode
        flow=AUDITOR/'cp6-proof/au-browser/FLOW.json'
        evidence=json.loads(flow.read_text()) if flow.exists() else {}
        Path(out).parent.mkdir(parents=True,exist_ok=True)
        if flow.exists():shutil.copy(flow,Path(out).parent/'T3_BROWSER_FLOW.json')
        report['cases']={c['id']:c['status'] for c in evidence.get('cases',[])}
        report['flow_status']=evidence.get('status');report['console_errors']=len(evidence.get('console_errors',[]))
        verify=subprocess.run(['python','scripts/cp6_au_browser_fixture.py','verify'],cwd=AUDITOR,env=env,capture_output=True,text=True)
        report['candidate_verified_after_flow']=verify.returncode==0 and json.loads(verify.stdout.splitlines()[-1]).get('stage')
        ok=(result.returncode==0 and evidence.get('status')=='PASS' and len(report['cases'])==10
            and all(s=='PASS' for s in report['cases'].values()) and report['candidate_verified_after_flow']=='T3_PACKAGE_PLUS_AW_AX_T1')
        report['status']='PASS' if ok else 'FAIL'
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc)[:1500])
    finally:
        subprocess.run(['docker','rm','-f',REST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        report['rest_remaining']=bool(run_cmd('docker','ps','-aq','--filter','name=^/'+REST+'$'))
        Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(dict(t3_browser=report),default=str)[:6000],flush=True)
    return report
