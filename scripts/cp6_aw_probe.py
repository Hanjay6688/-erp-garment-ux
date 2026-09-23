"""AW T1_FAMILY probe: per-date close readiness engine (S06/B04) and GPT findings P-01..P-04, before and after.

Label T1_FAMILY (owner decision A+B, handoff §18/§19): targeted family evidence on the disposable chain
AN -> AS/AT -> AU -> AV, never release evidence. Phase 'before' observes AU + AV; phase 'after' additionally installs
supabase/dev/cp6_aw_t1_family.sql and replays the same cases. Expected outcomes come from the owner policy (handoff
§14 no. 3, §16.4, §19) and docs/cp6-aw-design.md, never from observed behaviour.

Business actions use the ordinary authenticated owner RPCs. Administrative fixtures are labelled and used only where
no business RPC exists: moving closed_through (set_open_period), a NULL laundry rate (legacy/import state), stock
history that the posting guards refuse, and the neutralisation of seed facts that are open items for the engine.
Every case runs inside the group's rolled-back savepoint (r1.group); nothing is committed to the clone.
"""
from collections import Counter
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,TimeoutError as FutureTimeout
import argparse,hashlib,json,os,queue,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_au_r1_probe as r1
import cp6_au_runtime as au_runtime
import cp6_av_runtime as av_runtime
import cp6_ao_ap_installed as api
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as boundary
import cp6_aw_definitions as aw

OUT=AUDITOR/'cp6-proof/aw'
r1.OUT=OUT
chain=r1.chain
AW_SQL=AUDITOR/'supabase/dev/cp6_aw_t1_family.sql'
LABEL='T1_FAMILY'


def installed(cur):
    return cur.execute("select to_regprocedure('erp.period_readiness_v1(date,date)') is not null").fetchone()[0]


def aw_verified(cur):
    """T1 verification: markers plus the exact text of every function AW owns (pg_get_functiondef form)."""
    marks=cur.execute("select array_agg(version order by version) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw')").fetchone()[0]
    assert marks==['v2.6.20av','v2.6.20aw'],('AW_T1_MARKERS',marks)
    texts={**aw.NEW_FUNCTIONS,**aw.FUNCTIONS,**aw.PUBLIC_FUNCTIONS}
    drift=[k for k,t in texts.items() if cur.execute('select pg_get_functiondef(%s::regprocedure)',(k,)).fetchone()[0]!=t]
    assert not drift,('AW_T1_FUNCTION_TEXT_DRIFT',drift)
    return dict(stage='AV_PLUS_AW_T1',label=LABEL,functions=len(texts),sql_sha256=hashlib.sha256(AW_SQL.read_bytes()).hexdigest())


def install_aw():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:
        cur.execute(AW_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=aw_verified(cur);conn.rollback()
    return result


# ---------------------------------------------------------------- engine, report and close helpers

def preflight(cur,day):
    if not installed(cur):return None
    api.admin(cur)
    return cur.execute('select erp.accounting_close_preflight_v1(%s)',(day,)).fetchone()[0]


def codes(r,own=None):
    """Blocker codes, optionally only those whose reference mentions one of the own fixture ids."""
    if r is None:return None
    rows=r['blockers']
    if own:rows=[b for b in rows if any(str(x) in json.dumps(b['reference']) for x in own)]
    return sorted({b['code'] for b in rows})


def report(cur,day):
    api.ordinary(cur)
    snap=cur.execute('select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(day,day,day)).fetchone()[0]
    api.admin(cur)
    dc=find(snap,'data_confidence') or {}
    return dict(status=dc.get('status'),filing=dc.get('filing'),changed_since_filing=dc.get('changed_since_filing'),
                blockers=[b.get('code') for b in (dc.get('blockers') or [])])


def find(value,key):
    if isinstance(value,dict):
        if key in value:return value[key]
        for v in value.values():
            r=find(v,key)
            if r is not None:return r
    if isinstance(value,list):
        for v in value:
            r=find(v,key)
            if r is not None:return r
    return None


def close(cur,day,reason):
    """Ordinary owner close. On refusal r1.peer.attempt proves the complete boundary is unchanged (atomic refusal)."""
    def op():
        api.ordinary(cur)
        return cur.execute('select erp.close_accounting_through(%s,%s)',(day,reason)).fetchone()[0]
    result,error=r1.peer.attempt(cur,op)
    return ('ACCEPTED' if error is None else (error.get('message') or '').split(':')[0]),error


def control(cur):
    api.admin(cur)
    closed=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    filings=cur.execute('select count(*) from erp.accounting_close_filings_v1').fetchone()[0] if installed(cur) else None
    return dict(closed_through=str(closed),filings=filings)


# ---------------------------------------------------------------- fixtures

def contractor_with_worker(cur,joined,name):
    """New MANDOR contractor (attendance required) and one DAILY worker through the owner roster RPC."""
    api.admin(cur);c=uuid.uuid4()
    cur.execute("""insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required)
        values(%s,%s,%s,'MANDOR',true)""",(c,'AW-'+c.hex[:12],name))
    api.ordinary(cur)
    w=cur.execute('select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=str(c),
        worker_code='AW-'+uuid.uuid4().hex[:8],worker_name=name+' worker',job_description='Jahit',pay_scheme='DAILY',
        initial_daily_rate=100,rate_effective_from=str(joined),joined_at=str(joined),is_active=True,reason='AW T1 probe worker')),
        uuid.uuid4())).fetchone()[0]
    api.admin(cur)
    return c,uuid.UUID(str(find(w,'worker_id')))


def employed_workers(cur,contractor,day):
    api.admin(cur)
    return [r[0] for r in cur.execute("""select w.id from erp.contractor_workers w where w.contractor_id=%s
        and w.pay_scheme in('DAILY','HYBRID') and erp.worker_is_employed_on(w.id,%s) order by w.id""",(contractor,day)).fetchall()]


def post_attendance(cur,contractor,start,end,status='OFF'):
    """Owner saves and posts one attendance period covering every employed worker-day (existing rule: holidays OFF)."""
    days=[start+timedelta(days=i) for i in range((end-start).days+1)]
    lines=[dict(worker_id=str(w),attendance_date=str(d),status=status) for d in days for w in employed_workers(cur,contractor,d)]
    if not lines:return None
    api.ordinary(cur)
    p=cur.execute('select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=str(contractor),
        period_number='AW-'+uuid.uuid4().hex[:16],period_start=str(start),period_end=str(end),pay_date=str(end),
        reason='AW T1 attendance',attendance=lines)),uuid.uuid4())).fetchone()[0]
    posted=cur.execute('select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',
        (find(p,'period_id'),'AW T1 attendance posted',uuid.uuid4(),find(p,'row_version'))).fetchone()[0]
    api.admin(cur)
    return dict(period_id=find(posted,'period_id'),row_version=find(posted,'row_version'),days=len(days),lines=len(lines))


def reverse_attendance(cur,period):
    api.ordinary(cur)
    r=cur.execute('select public.erp_reverse_attendance_period_v1(%s,%s,%s,%s)',
        (period['period_id'],'AW T1 correction after close',uuid.uuid4(),period['row_version'])).fetchone()[0]
    api.admin(cur);return r


def quiet_seed(cur,start,end,exclude=()):
    """Clear seed open items for [start,end] the way the owner would, with owner RPCs where they exist:
    record OFF for every attendance-required seed contractor, approve due payrolls, and take eligible seed work into
    an approved payroll. Administrative only where no RPC exists (payroll header insert, as the harness does)."""
    done=dict(attendance=[],approved=[],work_payrolls=[],refused=[])
    api.admin(cur)
    for (c,) in cur.execute("""select c.id from erp.contractors c where c.attendance_required and c.id<>all(%s::uuid[])
        and exists(select 1 from erp.contractor_workers w where w.contractor_id=c.id and w.pay_scheme in('DAILY','HYBRID')) order by c.id""",
        ([str(x) for x in exclude],)).fetchall():
        try:
            cur.execute('savepoint aw_quiet')
            p=post_attendance(cur,c,start,end)
            cur.execute('release savepoint aw_quiet')
            if p:done['attendance'].append(dict(contractor=str(c),**{k:p[k] for k in ('days','lines')}))
        except psycopg.Error as exc:
            cur.execute('rollback to savepoint aw_quiet');api.admin(cur)
            done['refused'].append(dict(step='attendance',contractor=str(c),message=exc.diag.message_primary))
    for (pid,) in cur.execute("select id from erp.payroll_settlements where status in('DRAFT','CALCULATED','REVIEW') and period_end<=%s order by id",(end,)).fetchall():
        try:
            cur.execute('savepoint aw_quiet');chain.prior.as_owner(cur)
            cur.execute('select erp.populate_payroll_draft(%s)',(pid,));cur.execute('select erp.approve_payroll(%s)',(pid,))
            api.admin(cur);cur.execute('release savepoint aw_quiet');done['approved'].append(str(pid))
        except psycopg.Error as exc:
            cur.execute('rollback to savepoint aw_quiet');api.admin(cur)
            done['refused'].append(dict(step='approve',payroll=str(pid),message=exc.diag.message_primary))
    cash=cur.execute('select id from erp.cash_accounts where is_active order by cash_account_code limit 1').fetchone()[0]
    for c,lo,hi in cur.execute(f"""select e.contractor_id,min((e.eligible_at at time zone 'Asia/Jakarta')::date),max((e.eligible_at at time zone 'Asia/Jakarta')::date)
        from erp.v_payroll_eligible_work_lines e where e.remaining_qty>0 and e.eligible_at<%s and e.contractor_id<>all(%s::uuid[]) group by 1 order by 1""",
        (chain.production.at(end+timedelta(days=1),0),[str(x) for x in exclude])).fetchall():
        try:
            cur.execute('savepoint aw_quiet');pid=uuid.uuid4()
            cur.execute("""insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_cash_account_id,payment_date,manual_adjustment,notes)
                values(%s,%s,%s,%s,%s,'DRAFT',%s,%s,0,'AW T1 seed work payroll')""",(pid,'AW-'+pid.hex[:12],c,lo,hi,cash,hi))
            chain.prior.as_owner(cur)
            cur.execute('select erp.populate_payroll_draft(%s)',(pid,));cur.execute('select erp.approve_payroll(%s)',(pid,))
            api.admin(cur);cur.execute('release savepoint aw_quiet');done['work_payrolls'].append(dict(contractor=str(c),start=str(lo),end=str(hi)))
        except psycopg.Error as exc:
            cur.execute('rollback to savepoint aw_quiet');api.admin(cur)
            done['refused'].append(dict(step='work_payroll',contractor=str(c),message=exc.diag.message_primary))
    return done


def blockers_brief(r):
    if r is None:return None
    return [dict(code=b['code'],severity=b['severity'],impact=b['impact_date'],ref={k:b['reference'].get(k) for k in list(b['reference'])[:4]})
            for b in r['blockers']][:60]


# ---------------------------------------------------------------- cases

def discovery(cur,today):
    """Observation only: what the seed already holds for the engine, and what remains after quiet_seed."""
    boundary.historical.prior.set_open_period(cur,today-timedelta(days=4))
    before=preflight(cur,today-timedelta(days=1))
    quiet=quiet_seed(cur,today-timedelta(days=3),today-timedelta(days=1))
    after=preflight(cur,today-timedelta(days=1))
    return dict(status='OBSERVED',seed_blockers=blockers_brief(before),seed_counts=before and {k:before[k] for k in ('status','blocker_count','critical_count','policy_count','recalc_count')},
                quiet=quiet,after_quiet=blockers_brief(after),after_quiet_status=after and after['status'],
                integrity_emitted=integrity_names(cur))


def integrity_names(cur):
    api.admin(cur)
    rows=cur.execute("""select 'v268',check_name,severity,issue_count from erp.run_v268_financial_report_checks()
        union all select 'v267',check_name,severity,issue_count from erp.run_v267_financial_truth_checks()
        union all select 'int',check_name,severity,issue_count from erp.run_integrity_checks()""").fetchall()
    return [dict(src=s,name=n,severity=v,issues=i) for s,n,v,i in rows if i and v in ('CRITICAL','ERROR')]


def registry_native(cur,today):
    """Every CRITICAL/ERROR name the native runners emit in any row must be in the registry (no UNCLASSIFIED)."""
    if not installed(cur):return dict(status='NOT_APPLICABLE',reason='registry exists only with AW')
    api.admin(cur)
    names={r[0] for r in cur.execute("""select check_name from erp.run_v268_financial_report_checks() where severity in('CRITICAL','ERROR')
        union select check_name from erp.run_v267_financial_truth_checks() where severity in('CRITICAL','ERROR')
        union select check_name from erp.run_integrity_checks() where severity in('CRITICAL','ERROR')""").fetchall()}
    registry={r[0] for r in cur.execute('select check_name from erp.period_integrity_check_registry_v1()').fetchall()}
    missing=sorted(names-registry)
    return dict(status='PASS' if not missing else 'FAIL',emitted_names=len(names),registry=len(registry),missing=missing,
                expected='Every name the native runners can emit (issue count zero or not) is classified')


def p01_reverse_after_close(cur,today):
    """P-01: OFF recorded, close, reverse the attendance, then report and next close must see the gap; re-record clears it."""
    c0,d1,d2,d3=today-timedelta(days=4),today-timedelta(days=3),today-timedelta(days=2),today-timedelta(days=1)
    boundary.historical.prior.set_open_period(cur,c0)
    contractor,worker=contractor_with_worker(cur,d1,'AW P01')
    quiet=quiet_seed(cur,d1,d3,exclude=[contractor])
    period=post_attendance(cur,contractor,d1,d3)
    first=close(cur,d2,'AW P01 close with complete attendance')
    reverse_attendance(cur,period)
    report_d2=report(cur,d2)
    pre_d3=preflight(cur,d3)
    second=close(cur,d3,'AW P01 close after attendance reversal')
    state=control(cur)
    post_attendance(cur,contractor,d1,d3)
    pre_fixed=preflight(cur,d3)
    observed=dict(first_close=first[0],report_d2_status=report_d2['status'],changed_since_filing=report_d2['changed_since_filing'],
                  own_blockers=codes(pre_d3,[worker]),second_close=second[0],state_after_refusal=state,
                  after_rerecord=codes(pre_fixed,[worker]),residual_seed=codes(pre_fixed))
    if not installed(cur):
        row=dict(status='COUNTEREXAMPLE' if second[0]=='ACCEPTED' else 'CONTROL_PASS',
                 expected='Owner rule: a reversed attendance day after close must block the next close; frozen AU+AV accepts it')
    else:
        ok=(first[0]=='ACCEPTED' and pre_d3 and 'ATTENDANCE_CELL_MISSING' in codes(pre_d3,[worker]) and second[0]=='CLOSE_BLOCKED'
            and state['closed_through']==str(d2) and state['filings']==1 and report_d2['changed_since_filing'] is True
            and 'ATTENDANCE_CELL_MISSING' not in codes(pre_fixed,[worker]))
        row=dict(status='PASS' if ok else 'FAIL',expected=dict(first_close='ACCEPTED',own_blockers_include='ATTENDANCE_CELL_MISSING',
                 second_close='CLOSE_BLOCKED',closed_through=str(d2),filings=1,changed_since_filing=True,after_rerecord_without='ATTENDANCE_CELL_MISSING'))
    return dict(**row,observed=observed,quiet=quiet,first_close_error=first[1],second_close_error=second[1],
                fixture='ordinary owner RPCs for roster, attendance save/post/reverse and close; closed_through moved administratively')


def recost_fixture(cur,today,backdate):
    f=chain.production.estimated_receipt(cur,today)
    class OrdinaryDraftCursor:
        def __getattr__(self,name):return getattr(cur,name)
        def execute(self,query,params=None,**kwargs):
            if 'insert into erp.work_completion_events(' in str(query) or 'insert into erp.work_completion_lines(' in str(query):chain.peer.ordinary(cur)
            return cur.execute(query,params,**kwargs)
    chain.production.partial_production(OrdinaryDraftCursor(),f)
    api.admin(cur)
    if backdate:chain.prior.post_purchase(cur,f['material'],chain.production.at(f['purchase_day'],22),unit_price=12)
    api.admin(cur)
    q=cur.execute("select status,attempt_count,recalc_from from erp.cost_recalc_queue where entity_type='PO' and entity_id=%s and status in('PENDING','RUNNING','FAILED')",(f['po'],)).fetchall()
    return f,q


def recost_in_period(cur,today,backdate):
    """S06: a backdated purchase re-costs a PO whose consumption is inside the period; close must refuse atomically."""
    f,queue=recost_fixture(cur,today,backdate)
    d=f['purchase_day']+timedelta(days=1)
    pre=preflight(cur,d)
    closed=close(cur,d,'AW recost gate')
    own=codes(pre,[f['po']])
    observed=dict(queue=[list(map(str,r)) for r in queue],own_blockers=own,close=closed[0],state=control(cur))
    if backdate:
        if not installed(cur):
            status='COUNTEREXAMPLE' if closed[0]=='ACCEPTED' else 'CONTROL_PASS'
        else:
            status='PASS' if queue and 'RECOST_PENDING' in own and closed[0]=='CLOSE_BLOCKED' else 'FAIL'
        expected='A pending recost of a PO with facts on or before D blocks close (owner policy); refusal is atomic'
    else:
        status='CONTROL_PASS' if not queue and (pre is None or 'RECOST_PENDING' not in (own or [])) else 'FAIL'
        expected='Control: without the backdated purchase there is no recost row for the PO'
    return dict(status=status,expected=expected,observed=observed,close_error=closed[1],
                fixture='real purchase, cutting, production and backdated purchase RPCs (harness recipe); closed_through moved by estimated_receipt')


def laundry_null_rate(cur,today):
    f=r1.production(cur,today)
    api.admin(cur)
    line=cur.execute('select id from erp.laundry_delivery_lines where delivery_id=%s',(f['delivery'],)).fetchone()[0]
    cur.execute('update erp.laundry_delivery_lines set estimated_rate_snapshot=null where id=%s',(line,))
    return f,line


def p02_estimate(cur,today):
    """P-02: the owner estimate refuses non-finite and invalid numbers with no residue; a valid estimate clears the blocker."""
    f,line=laundry_null_rate(cur,today)
    d=today-timedelta(days=1)
    pre=preflight(cur,d)
    if not installed(cur):
        return dict(status='NOT_APPLICABLE',reason='owner estimate RPC exists only with AW',unknown_rate_line=str(line))
    refused={}
    for value in ('NaN','Infinity','-Infinity','-1','1.005','10000000000000000'):
        def op(v=value):
            api.ordinary(cur)
            return cur.execute('select public.erp_set_laundry_rate_owner_estimate_v1(%s,%s::numeric,%s)',(line,v,'AW P02 invalid')).fetchone()[0]
        result,error=r1.peer.attempt(cur,op)
        refused[value]=bool(error and 'LAUNDRY_ESTIMATE_RATE_INVALID' in (error.get('message') or ''))
    api.admin(cur)
    residue=cur.execute('select (select count(*) from erp.laundry_rate_owner_estimates_v1 where delivery_line_id=%s),(select estimated_rate_snapshot from erp.laundry_delivery_lines where id=%s)',(line,line)).fetchone()
    api.ordinary(cur)
    good=cur.execute('select public.erp_set_laundry_rate_owner_estimate_v1(%s,7.50,%s)',(line,'AW P02 owner estimate')).fetchone()[0]
    api.admin(cur)
    after=preflight(cur,d)
    again=r1.peer.attempt(cur,lambda:(api.ordinary(cur),cur.execute('select public.erp_set_laundry_rate_owner_estimate_v1(%s,8,%s)',(line,'AW P02 overwrite')).fetchone()[0]))[1]
    rate=cur.execute('select estimated_rate_snapshot from erp.laundry_delivery_lines where id=%s',(line,)).fetchone()[0]
    ok=(all(refused.values()) and residue==(0,None) and 'LAUNDRY_PRICE_UNKNOWN' in codes(pre,[line])
        and 'LAUNDRY_PRICE_UNKNOWN' not in codes(after,[line]) and str(rate)=='7.50' and again and 'ALREADY_KNOWN' in (again.get('message') or ''))
    return dict(status='PASS' if ok else 'FAIL',refused=refused,residue=[residue[0],str(residue[1])],before=codes(pre,[line]),estimate=good,
                after=codes(after,[line]),rate_after=str(rate),overwrite_refusal=again,
                fixture='real laundry chain; the delivery rate set to NULL administratively (legacy/import state, no RPC produces it)')


def p04_fg_same_instant(cur,today,minus_first):
    """P-04: -1 then +1 at one physical instant is a negative prefix in the posting guard's order (administrative history)."""
    if not installed(cur):return dict(status='NOT_APPLICABLE',reason='dated FG detector exists only with AW')
    api.admin(cur)
    row=cur.execute("select id,product_id from erp.fg_lots order by produced_at,id limit 1").fetchone()
    if row is None:
        # No lot exists at this point of the seed: create one administratively (same labelled fixture class).
        product=chain.base.create_product(cur,'AWP04-'+uuid.uuid4().hex[:10]);lot=uuid.uuid4()
        cur.execute("set local session_replication_role=replica")
        cur.execute("""insert into erp.fg_lots(id,lot_number,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
            values(%s,%s,%s,1,0,%s,true,'OTHER')""",(lot,'AWP04-'+lot.hex[:10],product,chain.production.at(today-timedelta(days=10),8)))
        cur.execute("set local session_replication_role=origin")
    else:lot,product=row
    loc=uuid.uuid4()
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'AW P04 empty FG location','FG_WAREHOUSE',true)",(loc,'AW-'+loc.hex[:12]))
    at=chain.production.at(today-timedelta(days=3),10)
    cur.execute("set local session_replication_role=replica")
    for i,q in enumerate((-1,1) if minus_first else (1,-1)):
        cur.execute("""insert into erp.fg_stock_movements(product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,source_id,physical_at,system_created_at)
            values(%s,%s,%s,'GRADE_A','ADJUSTMENT',%s,0,'AW_P04_FIXTURE',%s,%s,%s)""",(product,lot,loc,q,uuid.uuid4(),at,at+timedelta(seconds=i+1)))
    cur.execute("set local session_replication_role=origin")
    same=preflight(cur,today-timedelta(days=3));earlier=preflight(cur,today-timedelta(days=4))
    own=lambda r:sorted({b['reference'].get('level') for b in r['blockers'] if b['code']=='FG_QTY_NEGATIVE_ASOF' and b['reference'].get('location_id')==str(loc)})
    observed=dict(on_day=own(same),day_before=own(earlier))
    expected=dict(on_day=['LOT','SKU'] if minus_first else [],day_before=[])
    return dict(status=('PASS' if minus_first else 'CONTROL_PASS') if observed==expected else 'FAIL',expected=expected,observed=observed,
                fixture='administrative movements with triggers disabled (the posting guard refuses this history on ordinary paths)')


def access(cur,today):
    """Non-owner callers are refused with no effect; the owner facade returns exactly the backend preflight."""
    if not installed(cur):return dict(status='NOT_APPLICABLE',reason='facades exist only with AW')
    d=today-timedelta(days=1)
    def anon():
        api.admin(cur);cur.execute('set local role anon')
        return cur.execute('select public.erp_accounting_close_preflight_v1(%s)',(d,)).fetchone()[0]
    def stranger(fn,args):
        def op():
            api.admin(cur)
            cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':str(uuid.uuid4()),'role':'authenticated'}),))
            cur.execute('set local session authorization authenticated')
            return cur.execute(f'select {fn}',args).fetchone()[0]
        return op
    results={}
    for name,op in (('anon_preflight',anon),('stranger_preflight',stranger('public.erp_accounting_close_preflight_v1(%s)',(d,))),
                    ('stranger_close',stranger('public.erp_close_accounting_through_v1(%s,%s)',(d,'AW access'))),
                    ('stranger_estimate',stranger('public.erp_set_laundry_rate_owner_estimate_v1(%s,%s,%s)',(uuid.uuid4(),1,'AW access')))):
        result,error=r1.peer.attempt(cur,op)
        results[name]=dict(refused=error is not None,sqlstate=error and error.get('sqlstate'))
    api.ordinary(cur)
    facade=cur.execute('select public.erp_accounting_close_preflight_v1(%s)',(d,)).fetchone()[0]
    api.admin(cur)
    backend=cur.execute('select erp.accounting_close_preflight_v1(%s)',(d,)).fetchone()[0]
    ok=all(v['refused'] for v in results.values()) and facade==backend
    return dict(status='PASS' if ok else 'FAIL',results=results,facade_equals_backend=facade==backend)


RACE_DB='cp6_aw_race'


def race_setup(admin,today,verify):
    """Committed fixtures in the race copy only: seed, open period, quiet seed, one contractor with posted attendance."""
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        report=dict(runtime=verify(cur));conn.rollback()
        cur.execute('grant usage on schema erp to authenticated')
        if not cur.execute('select count(*) from erp.app_users').fetchone()[0]:api.seed(cur)
        conn.commit()
    return report


def two_sessions(admin,first_op,second_op,commit):
    """Holder runs first_op and keeps its transaction open; a worker runs second_op; then the holder commits or aborts."""
    ready=queue.Queue()
    def worker():
        try:
            with psycopg.connect(admin) as conn,conn.cursor() as cur:
                cur.execute("set local lock_timeout='20s';set local statement_timeout='60s'")
                ready.put(cur.execute('select pg_backend_pid()').fetchone()[0])
                result=second_op(cur);conn.commit();return dict(ok=True,result=result)
        except psycopg.Error as exc:return dict(ok=False,sqlstate=exc.sqlstate,message=exc.diag.message_primary)
    with psycopg.connect(admin) as holder,holder.cursor() as hcur,ThreadPoolExecutor(max_workers=1) as pool:
        hpid=hcur.execute('select pg_backend_pid()').fetchone()[0]
        held=first_op(hcur)
        future=pool.submit(worker);wpid=ready.get(timeout=20)
        try:early=future.result(timeout=6)
        except FutureTimeout:
            early=None
            contention=dict(kind='BLOCKED',holder_blocks_worker=hcur.execute('select %s=any(pg_blocking_pids(%s))',(hpid,wpid)).fetchone()[0])
        else:contention=dict(kind='NO_CONTENTION')
        (holder.commit if commit else holder.rollback)()
        outcome=early if early is not None else future.result(timeout=90)
    return held,contention,outcome


def attendance_race(admin,today,first,commit):
    """Attendance reversal versus close of the same days (neither reads the other's lock): both orders, commit and abort."""
    c0,d1,d3=today-timedelta(days=4),today-timedelta(days=3),today-timedelta(days=1)
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        boundary.historical.prior.set_open_period(cur,c0)
        contractor,worker=contractor_with_worker(cur,d1,'AW race')
        quiet=quiet_seed(cur,d1,d3,exclude=[contractor])
        period=post_attendance(cur,contractor,d1,d3)
        ready_before=preflight(cur,d3)['status']
        conn.commit()
    def do_close(cur):
        api.ordinary(cur);r=cur.execute('select erp.close_accounting_through(%s,%s)',(d3,'AW race close')).fetchone()[0];api.admin(cur);return 'CLOSED'
    def do_reverse(cur):
        api.ordinary(cur)
        cur.execute('select public.erp_reverse_attendance_period_v1(%s,%s,%s,%s)',(period['period_id'],'AW race reversal',uuid.uuid4(),period['row_version']))
        api.admin(cur);return 'REVERSED'
    ops=dict(CLOSE=do_close,REVERSE=do_reverse);other='REVERSE' if first=='CLOSE' else 'CLOSE'
    held,contention,outcome=two_sessions(admin,ops[first],ops[other],commit)
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        state=control(cur)
        reversed_=cur.execute("select status from erp.attendance_periods where id=%s",(period['period_id'],)).fetchone()[0]=='REVERSED'
        closed=state['closed_through']==str(d3)
        after=preflight(cur,d3)
        gap='ATTENDANCE_CELL_MISSING' in codes(after,[worker])
        filed=cur.execute("select count(*),coalesce(bool_and(readiness->>'status'='READY'),true) from erp.accounting_close_filings_v1").fetchone()
        conn.rollback()
    # Neither path takes the other's lock, so each commits on its own; afterwards the engine must reflect what committed.
    expect_closed=commit if first=='CLOSE' else outcome.get('ok',False)
    expect_reversed=commit if first=='REVERSE' else outcome.get('ok',False)
    ok=(ready_before=='READY' and closed==expect_closed and reversed_==expect_reversed and filed[0]==(1 if closed else 0)
        and filed[1] and gap==reversed_)
    return dict(status='PASS' if ok else 'FAIL',first=first,first_committed=commit,ready_before=ready_before,contention=contention,
                contender=outcome,closed=closed,reversed=reversed_,gap_visible_after=gap,filings=filed[0],filings_ready=filed[1],quiet=quiet,
                expected=dict(closed=expect_closed,reversed=expect_reversed,filings=1 if expect_closed else 0,gap_visible_after=expect_reversed))


def recost_race(admin,today,first,commit):
    """Backdated purchase (recost producer, FOR SHARE on the period row) versus close (FOR UPDATE), both orders."""
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        f,_=recost_fixture(cur,today,False)
        d=f['purchase_day']+timedelta(days=1)
        quiet=quiet_seed(cur,f['purchase_day'],d)
        pre=preflight(cur,d);conn.commit()
    if pre['status']!='READY':
        return dict(status='INCOMPLETE',reason='fixture not READY before the race',blockers=blockers_brief(pre),quiet=quiet)
    def do_purchase(cur):
        chain.prior.post_purchase(cur,f['material'],chain.production.at(f['purchase_day'],22),unit_price=12);api.admin(cur);return 'PURCHASED'
    def do_close(cur):
        api.ordinary(cur)
        try:
            cur.execute('savepoint c');cur.execute('select erp.close_accounting_through(%s,%s)',(d,'AW race close'));cur.execute('release savepoint c');r='CLOSED'
        except psycopg.Error as exc:
            cur.execute('rollback to savepoint c');r=(exc.diag.message_primary or '')[:400]
        api.admin(cur);return r
    ops=dict(PURCHASE=do_purchase,CLOSE=do_close);other='CLOSE' if first=='PURCHASE' else 'PURCHASE'
    held,contention,outcome=two_sessions(admin,ops[first],ops[other],commit)
    close_result=held if first=='CLOSE' else (outcome.get('result') if outcome.get('ok') else outcome.get('message'))
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        queue_rows=cur.execute("select count(*) from erp.cost_recalc_queue where entity_type='PO' and entity_id=%s and status in('PENDING','RUNNING','FAILED')",(f['po'],)).fetchone()[0]
        state=control(cur);after=preflight(cur,d);conn.rollback()
    closed=state['closed_through']==str(d)
    if first=='PURCHASE':
        # The close waits for the producer, then recomputes: committed purchase -> refused with RECOST_PENDING; aborted -> closes.
        expected=dict(contention='BLOCKED',close='CLOSE_BLOCKED with RECOST_PENDING' if commit else 'CLOSED')
        ok=contention['kind']=='BLOCKED' and (('RECOST_PENDING' in str(close_result)) if commit else close_result=='CLOSED')
    else:
        # The producer waits for the close; after it the queue row is a late change the engine shows for the closed date.
        expected=dict(contention='BLOCKED',closed=commit,late_change_visible='queue row -> RECOST_PENDING for D' )
        purchase_ok=outcome.get('ok',False)
        ok=(contention['kind']=='BLOCKED' and closed==commit and (queue_rows>0)==purchase_ok
            and (not purchase_ok or 'RECOST_PENDING' in codes(after,[f['po']])))
    return dict(status='PASS' if ok else 'FAIL',first=first,first_committed=commit,expected=expected,contention=contention,contender=outcome,
                close_result=close_result,queue_rows_after=queue_rows,state=state,after_codes_own=codes(after,[f['po']]),quiet=quiet)


def races(phase,verify):
    admin=boundary.ADMIN.rsplit('/',1)[0]+'/'+RACE_DB
    report=dict(status='INCOMPLETE',database=RACE_DB,schedules={},production_go=False,independent_acceptance=False,label=LABEL)
    r1.docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',RACE_DB)
    try:
        report['setup']=race_setup(admin,None,verify)
        with psycopg.connect(admin) as conn,conn.cursor() as cur:
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        if phase=='after':
            for kind,fn,firsts in (('ATTENDANCE',attendance_race,('CLOSE','REVERSE')),('RECOST',recost_race,('PURCHASE','CLOSE'))):
                for first in firsts:
                    for commit in (False,True):
                        key=f'{kind}_RACE:{first}_FIRST:'+('COMMIT' if commit else 'ABORT')
                        try:row=fn(admin,today,first,commit)
                        except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                        report['schedules'][key]=row;r1.save('RACES_'+phase.upper(),report)
                        print(json.dumps(dict(group='AW_RACES_'+phase.upper(),case=key,**row),default=str),flush=True)
    finally:
        r1.docker('dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',RACE_DB)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            report['race_database_remaining']=cur.execute('select count(*) from pg_database where datname=%s',(RACE_DB,)).fetchone()[0]
    report['counts']=dict(Counter(r['status'] for r in report['schedules'].values()))
    bad=report['counts'].get('INCOMPLETE') or report['counts'].get('FAIL') or report['race_database_remaining']
    report['status']='INCOMPLETE' if bad else 'PASS'
    r1.save('RACES_'+phase.upper(),report);return report


def cases(cur,today):
    return [('DISCOVERY:SEED',lambda:discovery(cur,today)),
            ('REGISTRY:NATIVE_NAMES',lambda:registry_native(cur,today)),
            ('P01:REVERSE_AFTER_CLOSE',lambda:p01_reverse_after_close(cur,today)),
            ('S06:RECOST_IN_PERIOD',lambda:recost_in_period(cur,today,True)),
            ('S06:RECOST_CONTROL_NO_BACKDATE',lambda:recost_in_period(cur,today,False)),
            ('P02:OWNER_ESTIMATE',lambda:p02_estimate(cur,today)),
            ('P04:FG_SAME_INSTANT_MINUS_FIRST',lambda:p04_fg_same_instant(cur,today,True)),
            ('P04:FG_SAME_INSTANT_PLUS_FIRST',lambda:p04_fg_same_instant(cur,today,False)),
            ('ACCESS:NON_OWNER_AND_FACADE',lambda:access(cur,today))]


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),installed_functions_patched_for_testing=False,
                production_go=False,independent_acceptance=False,release_evidence=False)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=av_runtime.change('install',boundary.PG,control_url)['status']
        verify=av_runtime.verified
        if phase=='after':
            report['aw_install']=install_aw();verify=aw_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(aw_probe_setup={k:report.get(k) for k in ('au_install','av_install','aw_install')}),default=str),flush=True)
        group=r1.group('AW_CASES_'+phase.upper(),cases,verify)
        report['aw_cases']={k:group[k] for k in ('status','counts')}
        race=races(phase,verify)
        report['aw_races']={k:race[k] for k in ('status','counts','race_database_remaining')}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and race['status']!='INCOMPLETE' else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(aw_probe_phase=phase,**report),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error','AW_PROBE_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
