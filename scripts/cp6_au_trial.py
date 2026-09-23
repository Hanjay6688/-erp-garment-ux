"""AU qualification preserves original oracles, AS/AT cases and adds master lifecycle controls."""
from datetime import date
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import traceback

import psycopg
import cp6_au_runtime as runtime
import cp6_at_trial as peer_trial
import cp6_au_cases as master
import cp6_au_races as master_races
import cp6_at_runtime as predecessor_runtime
import cp6_at_cases as temporal
import cp6_at_races as temporal_races
import cp6_as_cases as independent
import cp6_ar_runtime as ar
import cp6_ar_trial as inherited
import cp6_aq_runtime as aq
import cp6_ao_ap_installed as api
import cp6_ao_ap_maintenance as maintenance
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as predecessor
import cp6_successor_specs as specs
from cp6_ao_ap_inventory import function_pins

OUT=Path('cp6-proof/au')
BASE='a8a8771cdab3bec28f04600c86870142270e8487'
PG,ADMIN=predecessor.PG,predecessor.ADMIN


def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')


def source():
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()
    changed=subprocess.check_output(['git','diff','--name-only',BASE,head],text=True).splitlines()
    allowed={'.github/workflows/cp6-au-review.yml','.github/workflows/cp6-au-capture.yml','.github/workflows/cp6-au-qualification.yml','.github/workflows/cp6-au-identity-review.yml',
             'docs/cp6-au-review.md','docs/cp6-au-qualification.md','docs/evidence/cp6-au-schema-capture.json',
             str(runtime.build.MIGRATION),str(runtime.build.ROLLBACK),str(runtime.build.PINS),str(runtime.build.PROVENANCE)}
    allowed.update('scripts/cp6_au_'+name+'.py' for name in ('probe','identity_probe','capture','definitions','build','runtime','cases','races','trial','browser_fixture','browser_runtime'))
    allowed.add('scripts/cp6_au_browser_ui.mjs')
    assert set(changed)==allowed,('AU_SCOPE',changed)
    assert not subprocess.check_output(['git','diff','HEAD','--name-only'],text=True).strip(),'AU_TRACKED_WORKTREE_DIRTY'
    runtime.pins();specs.pins()
    result=dict(head=head,tree=tree,predecessor=BASE,changed_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in changed},
                original_oracle_sources=specs.pins()['oracle_sha256'],production_go=False,independent_acceptance=False)
    save('SOURCE',result)
    return result


def install_at():
    peer_trial.install_as()
    predecessor_runtime.change('install',PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])


def group(name,factory,stage='AU'):
    verify=runtime.verified if stage=='AU' else predecessor_runtime.verified
    report=dict(status='INCOMPLETE',stage=stage,cases={},production_go=False,independent_acceptance=False)
    save(name,report)
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        report['runtime_before']=verify(cur)
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
            cur.execute('savepoint at_case')
            try:row=operation()
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint at_case');api.admin(cur);cur.execute('release savepoint at_case')
            row['full_boundary_restored']=predecessor.snapshot(cur)==before
            if not row['full_boundary_restored']:row['status']='INCOMPLETE'
            report['cases'][key]=row;save(name,report)
            # New cases include full observations in the log for independent retrieval.
            detail=row if name in ('NEW_CASES','AT_CASES','AU_CASES') else {k:row.get(k) for k in ('status','error','traceback')}
            print(json.dumps(dict(group=name,case=key,**detail),default=str),flush=True)
        assert function_pins(cur)==catalog,'AT_CASE_FUNCTION_OR_ACL_MUTATION'
        conn.rollback();report['runtime_after']=verify(cur)
        report['complete_boundary_restored']=predecessor.snapshot(cur)==initial
        conn.rollback()
    report['counts']={s:sum(r['status']==s for r in report['cases'].values()) for s in ('PASS','CONTROL_PASS','DATE_POLICY_REVIEW_REQUIRED','COUNTEREXAMPLE','INCOMPLETE','BUG_PROVEN','GAP_PROVEN','FAIL')}
    if report['complete_boundary_restored'] and not any(report['counts'][s] for s in ('INCOMPLETE','BUG_PROVEN','GAP_PROVEN','FAIL')):
        report['status']='PROBE_COMPLETE' if stage=='AT' else 'WRITER_PASS_WITH_HISTORICAL_HOLD' if report['counts']['DATE_POLICY_REVIEW_REQUIRED'] else 'WRITER_PASS' if not report['counts']['COUNTEREXAMPLE'] else 'COUNTEREXAMPLE'
    save(name,report)
    return report


def ar_sequential(cur,today):
    cases=[]
    for kind in inherited.KINDS:
        cases.append((kind+'_ORIGINAL_PROBE',lambda k=kind:inherited.original_probe(cur,today,k)))
        for winner in ('imported','legacy'):
            cases.append((kind+'_'+winner.upper()+'_FIRST',lambda k=kind,w=winner:inherited.sequential(cur,today,k,w)))
        cases.append((kind+'_NONOVERLAP',lambda k=kind:inherited.nonoverlap(cur,today,k)))
    cases.append(('RPC_REPLAY_STALE_PAYLOAD_REVOKED',lambda:inherited.rpc_guards(cur,today)))
    return cases+inherited.inherited_cases(cur,today)


def qualify(report):
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:api.seed(cur)
    runtime.qualify(PG,ADMIN,OUT)
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
    runtime.refuse_post_use(PG,ADMIN,OUT)
    report['post_use_refusal']=json.loads((OUT/'AU_POST_USE_REFUSAL.json').read_text())
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:runtime.verified(cur)
    report['case_count']=len(seq['cases'])+len(report['races'])
    assert report['case_count']==174 and seq['status']=='WRITER_PASS'
    assert all(r['status']=='PASS' for r in report['races'].values())
    report['status']='WRITER_PASS'


def temporal_concurrency(report):
    # Old AR races intentionally commit ambiguous legacy opening fixtures.
    # Use a fresh clone instead of weakening their overlap refusal or deleting history.
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        api.seed(cur)
        predecessor.historical.prior.set_open_period(cur,date(2026,8,31))
    runtime.change('install',PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
    temporal_result=group('AT_CASES',temporal.cases)
    report['temporal_cases']={k:temporal_result[k] for k in ('status','counts')}
    assert len(temporal_result['cases'])==16 and temporal_result['status']=='WRITER_PASS',report['temporal_cases']
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
    assert all(r['status']=='PASS' for r in report['temporal_races'].values())
    masters=group('AU_CASES',master.cases)
    assert len(masters['cases'])==15 and masters['status']=='WRITER_PASS',masters['counts']
    report['master_cases']={k:masters[k] for k in ('status','counts')}
    report['master_races']={}
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        runtime.verified(cur);parent_before=predecessor.snapshot(cur)
    race_database='cp6_au_master_fixture'
    race_admin=ADMIN.rsplit('/',1)[0]+'/'+race_database
    try:
        subprocess.run(['docker','exec','supabase_db_cp5-local','createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',race_database],check=True)
        with psycopg.connect(race_admin) as conn,conn.cursor() as cur:
            runtime.verified(cur);before_catalog=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0]
            cur.execute('grant usage on schema erp to authenticated')
            fixture_catalog=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0]
            assert {k for k in before_catalog if before_catalog[k]!=fixture_catalog[k]}=={'SCHEMA:erp'}
            assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE'),has_schema_privilege('authenticated','erp','CREATE')").fetchone()==(True,False)
            assert function_pins(cur)==runtime.build.model()[3]['functions']
            report['master_fixture']=dict(database=race_database,only_catalog_delta='SCHEMA:erp authenticated USAGE',function_owner_acl_unchanged=True)
        for first in ('MASTER','OUTPUT','VALIDATION'):
            for commit in (False,True):
                key='MASTER_'+first+'_'+('COMMIT' if commit else 'ABORT')
                try:row=master_races.run(today,first,commit,race_admin)
                except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                report['master_races'][key]=row;save('TEMPORAL',report)
                print(json.dumps(dict(group='AU_CONCURRENCY',case=key,**row),default=str),flush=True)
        with psycopg.connect(race_admin) as conn,conn.cursor() as cur:
            cur.execute("set local search_path='';set local timezone='UTC'")
            observed=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0]
            assert observed==fixture_catalog,{k:[fixture_catalog.get(k),observed.get(k)] for k in set(observed)|set(fixture_catalog) if fixture_catalog.get(k)!=observed.get(k)}
            assert function_pins(cur)==runtime.build.model()[3]['functions']
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',race_database],check=True)
        with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
            runtime.verified(cur)
            assert predecessor.snapshot(cur)==parent_before
            assert cur.execute('select count(*) from pg_database where datname=%s',(race_database,)).fetchone()==(0,)
        report['master_fixture_parent_exactly_unchanged']=True
        report['master_fixture_clone_remaining']=0
    assert all(r['status']=='PASS' for r in report['master_races'].values())
    runtime.refuse_post_use(PG,ADMIN,OUT)
    report['post_use_refusal']=json.loads((OUT/'AU_POST_USE_REFUSAL.json').read_text())
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:runtime.verified(cur)
    report.update(status='WRITER_PASS',case_count=4)


def regress(report):
    runtime.change('install',PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
    expected={'business':dict(PASS=179,CONTROL_PASS=39,DATE_POLICY_REVIEW_REQUIRED=12),'imports':dict(PASS=31),'values':dict(PASS=65)}
    report['groups']={};report['calendar_policy']={}
    for name in ('business','imports','values'):
        result=group(name.upper(),lambda cur,today,g=name:[(k,lambda fn=fn:fn(cur)) for k,fn in specs.cases(g,today)])
        report['groups'][name]={k:result[k] for k in ('status','counts')}
        assert [k for k in result['cases']]==specs.pins()['groups'][name]['case_ids']
        assert {k:v for k,v in result['counts'].items() if v}==expected[name],report['groups'][name]
        if name=='business':
            for key,raw in result['cases'].items():
                if raw['status']=='DATE_POLICY_REVIEW_REQUIRED':report['calendar_policy'][key]=independent.calendar_policy(raw)
            save('CALENDAR_POLICY',report['calendar_policy'])
        save('REGRESSION',report)
    result=group('NEW_CASES',independent.new_cases)
    report['new_cases']={k:result[k] for k in ('status','counts')}
    assert len(result['cases'])==34 and result['status']=='WRITER_PASS',report['new_cases']
    assert len(report['calendar_policy'])==12 and all(r['status']=='PASS' for r in report['calendar_policy'].values()),report['calendar_policy']
    temporal_result=json.loads((OUT/'AT_CASES.json').read_text())
    report['temporal_cases']={k:temporal_result[k] for k in ('status','counts')}
    assert len(temporal_result['cases'])==16 and temporal_result['status']=='WRITER_PASS',report['temporal_cases']
    qualification=json.loads((OUT/'QUALIFY.json').read_text())
    assert qualification['status']=='WRITER_PASS' and qualification['case_count']==174
    assert qualification['primary_unchanged'] and qualification['clone_remaining']==0
    temporal_report=json.loads((OUT/'TEMPORAL.json').read_text())
    assert temporal_report['status']=='WRITER_PASS' and temporal_report['case_count']==4 and len(temporal_report['master_races'])==6
    assert temporal_report['primary_unchanged'] and temporal_report['clone_remaining']==0
    report.update(status='WRITER_PASS_WITH_12_PRESERVED_HISTORICAL_HOLD',original_cases=500,new_cases_count=34,additional_calendar_policy_checks=12,temporal_cases_count=16,temporal_real_races=4,master_cases_count=15,master_real_races=6)


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    s=source();report=dict(status='INCOMPLETE',phase=phase,head=s['head'],tree=s['tree'],production_go=False,independent_acceptance=False)
    save(phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(predecessor.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');primary=predecessor.snapshot(cur)
        install_at()
        {'qualify':qualify,'regression':regress,'temporal':temporal_concurrency}[phase](report)
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
    print(json.dumps({k:v for k,v in report.items() if k not in ('races','calendar_policy')},default=str),flush=True)
    assert report['status'].startswith('WRITER_PASS'),report.get('error','AT_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('qualify','regression','temporal'),required=True)
    run(parser.parse_args().phase)
