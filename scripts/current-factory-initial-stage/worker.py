"""D17-18: measured, bounded initial preparation for large frozen analyses.

Only unit zero of frozen-v2 jobs with at least 1000 targets uses the new
scheduler entry. Its work is the unchanged Native step, under a finite 16s
statement ceiling. Ordinary dispatch, later units and public calls retain 8s.
"""
from pathlib import Path
from hashlib import sha256
import re

ROOT=Path(__file__).resolve().parents[2]
RUNNER='cp7_analysis_stage.run_next()'
STEP='cp7_analysis_stage.step(uuid,jsonb)'
SCHEDULES='cp7_ops.schedules()'
PREPARE='cp7_ops.factory_initial_next_v1()'
TICK='cp7_ops.factory_initial_tick_v1()'
REPLACED={RUNNER,SCHEDULES,STEP};ADDED={PREPARE,TICK}
ELIGIBLE="(x.units_done=0 and x.targets_total>=1000 and x.reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2')"
SELECT="select *into j from cp7_analysis_stage.jobs x where x.state='RUNNING'order by x.updated_at,x.id limit 1 for update skip locked;"
NAME='cp7-factory-initial-preparation'
DEFINITION=dict(name=NAME,schedule='* * * * *',command="set statement_timeout to '16s'; set lock_timeout to '2s'; "+' '.join(['begin; select cp7_ops.factory_initial_tick_v1(); commit;']*4),timezone='UTC',meaning='every minute: up to 4 large frozen initial units, each in its own transaction under 16 s; other work retains 8 s')

def block(text,name):
    found=re.findall(r'create (?:or replace )?function '+re.escape(name)+r'\(.*?\$\$;',text,re.S)
    assert len(found)==1,name
    return found[0]

def body(text):
    assert text.count('$$')==2
    return text.split('$$')[1]

def once(text,old,new):
    assert text.count(old)==1,old[:100]
    return text.replace(old,new,1)

def originals():
    return {RUNNER:block((ROOT/'scripts/cp7-src/planning/analysis-stages.sql').read_text(),RUNNER[:-2]),
            STEP:block((ROOT/'scripts/cp7-src/planning/analysis-stages.sql').read_text(),'cp7_analysis_stage.step'),
            SCHEDULES:block((ROOT/'scripts/cp7-src/ops/schedule.sql').read_text(),SCHEDULES[:-2])}

def definitions():
    old=originals()
    ordinary=once(old[RUNNER],'create function ','create or replace function ')
    ordinary=once(ordinary,SELECT,SELECT.replace("x.state='RUNNING'", "x.state='RUNNING'and not coalesce("+ELIGIBLE+",false)"))
    large=once(old[RUNNER],RUNNER,PREPARE)
    large=once(large,'limit_ms not between 1 and 8000','limit_ms not between 8001 and 16000')
    large=once(large,'statement_timeout 1..8000 ms','statement_timeout 8001..16000 ms for large initial preparation only')
    start=large.index(' -- The heartbeat never makes one tick wait')
    end=large.index(' '+SELECT,start)
    # Do not falsify the old runner's 8s heartbeat. The unchanged ordinary
    # schedule owns it. Real job progress is committed by the same step below.
    large=large[:start]+large[end:]
    large=once(large,SELECT,SELECT.replace("x.state='RUNNING'","x.state='RUNNING'and coalesce("+ELIGIBLE+",false)"))
    schedules=once(old[SCHEDULES],'create function ','create or replace function ')
    tail="'timezone','UTC','meaning','every 10 minutes: up to 20 proof windows, each in its own transaction under the 8 s limit'))"
    addition=",\n  jsonb_build_object('name','"+NAME+"','schedule','* * * * *',\n   'command','"+DEFINITION['command'].replace("'","''")+"',\n   'timezone','UTC','meaning','"+DEFINITION['meaning']+"'))"
    schedules=once(schedules,tail,tail[:-1]+addition)
    tick=("create function "+TICK+"returns jsonb\nlanguage sql volatile security definer set search_path=''set TimeZone='UTC'as $$\n"
          " select cp7_ops.factory_initial_next_v1()||jsonb_build_object('tick','"+NAME+"','at',clock_timestamp(),'policy_id','D17-18-20261026')\n$$;")
    step=once(old[STEP],'create function ','create or replace function ')
    anchor=' select *into u from cp7_analysis_stage.units where job_id=j.id and idx=j.units_done;'
    gate=""" -- A page's ordinary 8s request must not repeatedly cancel a large initial
 -- unit. The current access check above still takes priority. Return an
 -- explicit refusal before running or charging an attempt; the server owns
 -- this stage and the client can read the same UUID with the existing get RPC.
 if coalesce((j.units_done=0 and j.targets_total>=1000 and j.reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'),false)
  and not exists(select 1 from pg_catalog.pg_settings where name='statement_timeout'and setting::integer between 8001 and 16000)then
  raise exception using errcode='55000',message='CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED';
 end if;
"""
    step=once(step,anchor,gate+anchor)
    return {RUNNER:ordinary,SCHEDULES:schedules,STEP:step,PREPARE:large,TICK:tick}

def row(cur,signature):
    return cur.execute('select p.prosrc,p.provolatile,p.prosecdef,pg_get_userbyid(p.proowner),p.proconfig,pg_get_functiondef(p.oid)from pg_proc p where p.oid=%s::regprocedure',(signature,)).fetchone()

def transition(before,after):
    assert set(before)==set(after)and len(before)==22
    changed={(g,k)for g in before for k in set(before[g])|set(after[g])if before[g].get(k)!=after[g].get(k)}
    assert changed=={('functions',s)for s in REPLACED|ADDED},('FACTORY_INITIAL_UNDECLARED_DELTA',sorted(changed))
    for sig in REPLACED:assert before['functions'][sig][1:]==after['functions'][sig][1:],sig

def verify(cur,state,catalog):
    expected=definitions();actual=catalog._catalog_rows(cur)
    transition(state['before'],actual)
    assert actual==state['after']
    for sig in REPLACED:
        old=state['original'][sig];observed=row(cur,sig)
        assert old[0]==body(originals()[sig])and observed[0]==body(expected[sig])
        assert observed[1:5]==old[1:5]and observed==state['rows'][sig]
    for sig,definer in ((PREPARE,False),(TICK,True)):
        observed=row(cur,sig);assert observed[:5]==(body(expected[sig]),'v',definer,'cp7_capture',['search_path=""','TimeZone=UTC'])
        assert observed==state['rows'][sig]
        for role in ('anon','authenticated','service_role','cp7_finance_read'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,sig)).fetchone()[0]
    assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')",(TICK,)).fetchone()[0]
    schedules=cur.execute('select cp7_ops.schedules()').fetchone()[0]
    assert schedules==state['ordinary_schedules']+[DEFINITION]
    return dict(status='EXACT_MEASURED_FACTORY_INITIAL_STAGE',large_initial_max_ms=16000,minimum_targets=1000,
        unit0_only=True,frozen_v2_only=True,ordinary_statement_limit_ms=8000,existing_four_schedules_unchanged=True,
        public_RPC_signatures_changed=0,large_initial_public_step_refusal='CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED',official_money_stock_HPP_changed=False,new_tables=0,new_roles=0,
        unchanged_Native_step_claims_access_locks_retries_progress=True,default_adopted=False,production_go=False)

def install(cur,catalog):
    old={s:row(cur,s)for s in REPLACED};before=catalog._catalog_rows(cur)
    for sig in REPLACED:assert old[sig][0]==body(originals()[sig]),sig
    for sig in ADDED:assert cur.execute('select to_regprocedure(%s)',(sig,)).fetchone()==(None,)
    ordinary=cur.execute('select cp7_ops.schedules()').fetchone()[0]
    assert len(ordinary)==4 and all(d['name']!=NAME for d in ordinary)
    for definition in definitions().values():cur.execute(definition,prepare=False)
    for sig in ADDED:
        cur.execute('alter function '+sig+' owner to cp7_capture')
        cur.execute('revoke all on function '+sig+' from public,anon,authenticated,service_role,postgres,cp7_finance_read')
    cur.execute('grant execute on function '+TICK+' to postgres')
    state=dict(before=before,after=catalog._catalog_rows(cur),original=old,ordinary_schedules=ordinary,rows={s:row(cur,s)for s in REPLACED|ADDED})
    state['verified']=verify(cur,state,catalog)
    return state

def restore(cur,state,catalog):
    verify(cur,state,catalog)
    for sig in REPLACED:cur.execute(state['original'][sig][5],prepare=False)
    cur.execute('drop function '+TICK+' restrict')
    cur.execute('drop function '+PREPARE+' restrict')
    assert catalog._catalog_rows(cur)==state['before']
