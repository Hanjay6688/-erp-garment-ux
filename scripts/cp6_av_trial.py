"""AV rev2 on exact AU: every original oracle, AS/AT/AU groups and races, verified against the AV catalog.

Runs from the frozen AU writer checkout (ca7f095). Case declarations, oracles
and race schedules are imported unchanged from the AU trial and its pinned
predecessors; only the installed runtime (AU then AV) and the catalog
verification (AV) differ. Expected counts are AU's recorded outcome, so any
movement is reported per case for explicit disposition instead of being
absorbed. No oracle is edited and no historical HOLD is resolved here.
"""
from collections import Counter
from datetime import date
from pathlib import Path
import argparse,json,os,subprocess,sys,traceback
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
FROZEN='ca7f09556397801c50a2277bdb65b1bf019f9a05'
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_au_trial as au
import cp6_au_runtime as au_runtime
import cp6_av_runtime as runtime
import cp6_au_cases as master
import cp6_au_races as master_races
import cp6_at_cases as temporal
import cp6_at_races as temporal_races
import cp6_as_cases as independent
import cp6_ar_trial as inherited
import cp6_ao_ap_installed as api
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as predecessor
import cp6_successor_specs as specs
from cp6_ao_ap_inventory import function_pins

OUT=AUDITOR/'cp6-proof/av-trial'
PG,ADMIN=predecessor.PG,predecessor.ADMIN
# AU's recorded outcome for the same declarations (AU qualification, run 35822980561).
EXPECTED={'business':dict(PASS=179,CONTROL_PASS=39,DATE_POLICY_REVIEW_REQUIRED=12),'imports':dict(PASS=31),'values':dict(PASS=65)}


def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')


def control():
    return os.environ['CP6_ADMISSION_CONTROL_PGURL']


def install_au():
    au.install_at()
    return au_runtime.change('install',PG,control())['status']


def group(name,factory):
    report=dict(status='INCOMPLETE',stage='AV',cases={},production_go=False,independent_acceptance=False)
    save(name,report)
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        report['runtime_before']=runtime.verified(cur)
        initial=predecessor.snapshot(cur);catalog=function_pins(cur)
        if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:cur.execute('grant usage on schema erp to authenticated')
        if not initial['erp']['app_users']['count']:api.seed(cur)
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        predecessor.historical.prior.set_open_period(cur,date(2026,8,31))
        cases=factory(cur,today)
        report['planned_case_ids']=[k for k,_ in cases]
        for key,operation in cases:
            before=predecessor.snapshot(cur)
            cur.execute('savepoint av_case')
            try:row=operation()
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint av_case');api.admin(cur);cur.execute('release savepoint av_case')
            row['full_boundary_restored']=predecessor.snapshot(cur)==before
            if not row['full_boundary_restored']:row['status']='INCOMPLETE'
            report['cases'][key]=row;save(name,report)
            detail=row if row.get('status') not in ('PASS','CONTROL_PASS','DATE_POLICY_REVIEW_REQUIRED') else {k:row.get(k) for k in ('status',)}
            print(json.dumps(dict(group=name,case=key,**detail),default=str),flush=True)
        assert function_pins(cur)==catalog,'AV_CASE_FUNCTION_OR_ACL_MUTATION'
        conn.rollback();report['runtime_after']=runtime.verified(cur)
        report['complete_boundary_restored']=predecessor.snapshot(cur)==initial
        conn.rollback()
    report['counts']=dict(Counter(r['status'] for r in report['cases'].values()))
    bad=any(report['counts'].get(s) for s in ('INCOMPLETE','BUG_PROVEN','GAP_PROVEN','FAIL'))
    report['status']='INCOMPLETE' if bad or not report['complete_boundary_restored'] else 'COUNTEREXAMPLE' if report['counts'].get('COUNTEREXAMPLE') else 'WRITER_PASS'
    save(name,report)
    return report


def regression(report):
    report['au_install']=install_au()
    report['av_install']=runtime.change('install',PG,control())['status']
    report['groups']={};report['calendar_policy']={};report['moved_cases']={}
    for name in ('business','imports','values'):
        result=group(name.upper(),lambda cur,today,g=name:[(k,lambda fn=fn:fn(cur)) for k,fn in specs.cases(g,today)])
        report['groups'][name]={k:result[k] for k in ('status','counts')}
        assert [k for k in result['cases']]==specs.pins()['groups'][name]['case_ids']
        report['groups'][name]['matches_au_outcome']=result['counts']==EXPECTED[name]
        if not report['groups'][name]['matches_au_outcome']:
            report['moved_cases'][name]={k:r['status'] for k,r in result['cases'].items() if r['status'] not in EXPECTED[name]}
        if name=='business':
            for key,raw in result['cases'].items():
                if raw['status']=='DATE_POLICY_REVIEW_REQUIRED':report['calendar_policy'][key]=independent.calendar_policy(raw)
        save('REGRESSION',report)
    result=group('NEW_CASES',independent.new_cases)
    report['new_cases']={k:result[k] for k in ('status','counts')}
    same=all(report['groups'][g]['matches_au_outcome'] for g in report['groups']) and len(result['cases'])==34 and result['status']=='WRITER_PASS'
    same=same and len(report['calendar_policy'])==12 and all(r['status']=='PASS' for r in report['calendar_policy'].values())
    report['status']='WRITER_PASS_WITH_12_PRESERVED_HISTORICAL_HOLD' if same else 'DISPOSITION_REQUIRED'


def ar_sequential(cur,today):
    return au.ar_sequential(cur,today)


def qualify(report):
    report['au_install']=install_au()
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:api.seed(cur)
    report['av_package']=runtime.qualify(PG,ADMIN)
    seq=group('AR_SEQUENTIAL',ar_sequential)
    report['sequential']={k:seq[k] for k in ('status','counts')}
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        runtime.verified(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    races=[]
    for kind in inherited.KINDS:
        for winner in ('imported','legacy'):
            races.append(('CONCURRENT_'+kind+'_'+winner.upper()+'_FIRST',lambda k=kind,w=winner:inherited.concurrency(today,k,w)))
    for winner in ('imported','legacy'):
        for same in (False,True):
            races.append((('SAME_HEADER_' if same else 'WINNER_ABORT_')+winner.upper(),lambda w=winner,s=same:inherited.concurrency(today,'MATERIAL',w,commit=s,same_header=s)))
    for variant in ('REPLAY','PAYLOAD','ACTION'):
        races.append(('REQUEST_CONCURRENT_'+variant,lambda v=variant:inherited.request_concurrency(today,v)))
    races.append(('STALE_SNAPSHOT_ISOLATION',lambda:inherited.isolation_guard(today)))
    report['races']={}
    for name,operation in races:
        try:row=operation()
        except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
        report['races'][name]=row;save('QUALIFY',report)
        print(json.dumps(dict(group='AR_CONCURRENCY',case=name,**row),default=str),flush=True)
    report['post_use_refusal']=runtime.refuse_post_use(PG,ADMIN)
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:runtime.verified(cur)
    report['case_count']=len(seq['cases'])+len(report['races'])
    ok=report['case_count']==174 and seq['status']=='WRITER_PASS' and all(r['status']=='PASS' for r in report['races'].values())
    report['status']='WRITER_PASS' if ok else 'DISPOSITION_REQUIRED'


def temporal_phase(report):
    report['au_install']=install_au()
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        api.seed(cur);predecessor.historical.prior.set_open_period(cur,date(2026,8,31))
    report['av_install']=runtime.change('install',PG,control())['status']
    temporal_result=group('AT_CASES',temporal.cases)
    report['temporal_cases']={k:temporal_result[k] for k in ('status','counts')}
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        runtime.verified(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    report['temporal_races']={}
    for first in ('MASTER','OUTPUT'):
        for commit in (False,True):
            name='TEMPORAL_'+first+'_'+('COMMIT' if commit else 'ABORT')
            try:row=temporal_races.run(today,first,commit)
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            report['temporal_races'][name]=row;save('TEMPORAL',report)
            print(json.dumps(dict(group='AT_CONCURRENCY',case=name,**row),default=str),flush=True)
    masters=group('AU_CASES',master.cases)
    report['master_cases']={k:masters[k] for k in ('status','counts')}
    report['master_races']={}
    race_database='cp6_av_master_fixture'
    race_admin=ADMIN.rsplit('/',1)[0]+'/'+race_database
    try:
        subprocess.run(['docker','exec','supabase_db_cp5-local','createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',race_database],check=True)
        with psycopg.connect(race_admin) as conn,conn.cursor() as cur:
            runtime.verified(cur);conn.rollback()
            cur.execute('grant usage on schema erp to authenticated')
        for first in ('MASTER','OUTPUT','VALIDATION'):
            for commit in (False,True):
                key='MASTER_'+first+'_'+('COMMIT' if commit else 'ABORT')
                try:row=master_races.run(today,first,commit,race_admin)
                except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                report['master_races'][key]=row;save('TEMPORAL',report)
                print(json.dumps(dict(group='AU_CONCURRENCY',case=key,**row),default=str),flush=True)
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',race_database],check=True)
        with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
            runtime.verified(cur)
            report['master_fixture_clone_remaining']=cur.execute('select count(*) from pg_database where datname=%s',(race_database,)).fetchone()[0]
    ok=(len(temporal_result['cases'])==16 and temporal_result['status']=='WRITER_PASS' and len(masters['cases'])==15 and masters['status']=='WRITER_PASS'
        and all(r['status']=='PASS' for r in report['temporal_races'].values()) and all(r['status']=='PASS' for r in report['master_races'].values())
        and not report['master_fixture_clone_remaining'])
    report['status']='WRITER_PASS' if ok else 'DISPOSITION_REQUIRED'


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==FROZEN,'AV_TRIAL_WRITER_NOT_FROZEN_AU'
    report=dict(status='INCOMPLETE',phase=phase,production_go=False,independent_acceptance=False,
                auditor_head=subprocess.check_output(['git','-C',str(AUDITOR),'rev-parse','HEAD'],text=True).strip(),
                av_pins=runtime.pins()['migration_sha256'],original_oracle_sources=specs.pins()['oracle_sha256'])
    save(phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(predecessor.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');primary=predecessor.snapshot(cur)
        {'qualify':qualify,'regression':regression,'temporal':temporal_phase}[phase](report)
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
        print(json.dumps(dict(phase=phase,error=str(exc),traceback=traceback.format_exc())),flush=True)
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(predecessor.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and predecessor.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        save(phase.upper(),report)
    print(json.dumps(dict(av_trial_phase=phase,**{k:v for k,v in report.items() if k not in ('races','calendar_policy')}),default=str),flush=True)
    assert report['status']!='INCOMPLETE',report.get('error','AV_TRIAL_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('qualify','regression','temporal'),required=True)
    run(parser.parse_args().phase)
