"""T2 regression for the combined CP6 candidate: AU + AV + AW (T1 install) + AX (T1 install).

Owner decision A+B: once every family passes its T1 probe, the whole existing regression runs once on the combined
candidate, then goes to independent audit. The case declarations, oracles and race schedules are the unchanged ones
the AV trial runs (AR 174, AT 16 / AU 15 with races, the original 326 plus AS 34); only the installed runtime differs.
Every case is compared with the AU recorded outcome per case id (H-01 comparator), so each moved case is listed for
disposition instead of being absorbed by a count. No oracle is edited and no historical HOLD is resolved here.

Label: T2_REGRESSION while the candidate is stable; T2_PRELIMINARY otherwise (set CP6_T2_LABEL).

CP6_T2_SEED=QUIETED (run 2): run 1 (35911656309) moved 145 regression and 7 AR cases, every one stopped by POLICY
blockers of the harness seed itself (4 seed workers without attendance, one seed payroll CALCULATED, seed contractor
work outside any payroll) under the recorded owner policy of AW (P-03: hold every date). Run 2 clears exactly those
seed items once per group, before any case, the way the owner would (awp.quiet_seed: attendance OFF through the
attendance RPCs, payroll approval, seed work into an approved payroll), inside the group transaction that is rolled
back afterwards. Oracles, cases and races are unchanged; a case that still moves is disposed of on its own.

Run 4 (independent review of 24 Sep): the quieting reads the closing date the group set instead of assuming it, clears
the seed items over the whole reopened range (not only the last 120 days), and requires the AW engine to answer READY
for that whole range before the closing date is put back; any refused step or a range that is not READY stops the group
(its cases are not run). The run-3 side channel is opt-in (CP6_T2_DIAG=1) and reads inside a savepoint that is rolled
back, so the case starts in the session state it had without it.

Run 5 (owner, 24 Sep): "lengkapi persiapan tes yang tidak sedang menguji payroll, perbaiki lima benturan absensi, lalu
jalankan ulang"; an approved payroll may still be a debt, so no test is made to pay, and tests about unpaid or partly
paid wages keep testing that. CP6_T2_FIXTURE=PAYROLL_APPROVED (default) therefore completes each case's own fixture
the way the owner policy asks, in the harness (the oracle files stay hash-pinned and unchanged): right before a case
reads readiness (owner report, preflight, close), every paid attendance day and payable work line that the case itself
created and no payroll has taken goes into a new payroll of that contractor, populated and APPROVED (cost recognised,
contractor payable; no payment), and the case's session is put back exactly. Items that existed before the case are not
touched. No case of the old sets tests uncovered work (they predate the policy); WORK_UNPAID has 0 payable pcs and
WORK_PARTIAL_PAY asserts 5 payable of 7 done before the report, so neither is changed by an approved, unpaid payroll.
The five CROSS:DAY:ATTENDANCE cases post PRESENT for the seed contractor on today-3 and today-2, days the quieting had
covered with OFF: those two days are now an OFF period of their own, reversed with the owner RPC inside the case's
savepoint only, so the case posts its own days and every other case keeps the full OFF cover.

Run 6: run 5 left 11 cases whose days fall inside a payroll of the same contractor that is approved but not paid (the
seed payroll ending 2026-02-01 and the quieting's seed work payrolls); the product allows one active payroll per day, so
the completion does what the owner would: cancel_unpaid_payroll on the overlapping unpaid payrolls and one approved,
unpaid payroll over the union (a PAID overlap is refused and recorded).
"""
from datetime import date,timedelta
from pathlib import Path
import argparse,json,os,re,sys,types

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_av_trial as avt
import cp6_av_runtime as av_runtime
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_regression_identity as identity

LABEL=os.environ.get('CP6_T2_LABEL','T2_PRELIMINARY')
SEED=os.environ.get('CP6_T2_SEED','AS_IS')
REOPEN=date(2026,1,1)
DIAG=os.environ.get('CP6_T2_DIAG')=='1'
FIXTURE=os.environ.get('CP6_T2_FIXTURE','PAYROLL_APPROVED')
assert FIXTURE in ('NONE','PAYROLL_APPROVED')
# cp6_successor_specs runs the business declarations with day=today-3; cp6_ac_independent_audit.attendance_case posts
# PRESENT for this seed contractor on day and day+1.
ATTENDANCE_OFFSET=3
ATTENDANCE_CONTRACTOR='a1000000-0000-0000-0000-000000000001'
avt.OUT=AUDITOR/'cp6-proof/t2'
assert SEED in ('AS_IS','QUIETED')


ORIGINAL_GROUP=avt.group


def group(name,factory):
    """Run 2 only: clear the seed's own open items in the group transaction before the cases are built."""
    if SEED!='QUIETED':return ORIGINAL_GROUP(name,factory)
    def quieted(cur,today):
        # group() has just closed the books (read here, not assumed). The seed payroll ends 2026-02-01 and the calendar
        # cases reopen up to three months back, so the seed items are cleared over the whole range from 2026-01-02 to
        # today with the books open, the AW engine must answer READY for every date of the reopened range, and only then
        # is the group's closing date put back (the same administrative helper group() uses).
        prior=avt.predecessor.historical.prior
        awp.api.admin(cur)
        found=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
        assert found is not None and REOPEN<found<today,('T2_UNEXPECTED_GROUP_CLOSE',found)
        prior.set_open_period(cur,REOPEN)
        case_days=(today-timedelta(days=ATTENDANCE_OFFSET),today-timedelta(days=ATTENDANCE_OFFSET-1))
        done=awp.quiet_seed(cur,REOPEN+timedelta(days=1),today,separate=[case_days])
        reopened=awp.preflight(cur,found)
        prior.set_open_period(cur,found)
        after=awp.preflight(cur,today)
        print(json.dumps(dict(group='T2_SEED_QUIETED',target=name,closed_through=found,window=[str(REOPEN+timedelta(days=1)),str(today)],
                              attendance=[dict(contractor=a['contractor'],periods=[(x['start'],x['end']) for x in a['periods']]) for a in done['attendance']],approved=done['approved'],work_payrolls=len(done['work_payrolls']),
                              refused=done['refused'],reopened_range=[str(REOPEN+timedelta(days=1)),str(found)],
                              reopened_status=reopened and reopened['status'],reopened_blockers=awp.blockers_brief(reopened),
                              after_status=after and after['status'],after_blockers=awp.blockers_brief(after)),default=str),flush=True)
        assert not done['refused'],('T2_SEED_QUIETING_REFUSED',done['refused'])
        assert reopened and reopened['status']=='READY',('T2_REOPENED_RANGE_NOT_READY',awp.blockers_brief(reopened))
        assert after and after['status']=='READY',('T2_QUIETED_SEED_NOT_READY',awp.blockers_brief(after))
        own=[x for a in done['attendance'] if a['contractor']==ATTENDANCE_CONTRACTOR for x in a['periods']
             if (x['start'],x['end'])==tuple(map(str,case_days))]
        assert len(own)==1,('T2_ATTENDANCE_CASE_DAYS_NOT_SEPARATE',own)
        return [(key,fixture(key,diagnosed(key,op,cur,today),cur,own[0])) for key,op in factory(cur,today)]
    return ORIGINAL_GROUP(name,quieted)


ELIGIBLE="select coalesce(array_agg(md5(e::text)),'{}') from erp.v_payroll_eligible_work_lines e where e.remaining_qty>0"
# What the AW engine counts as not taken by any payroll (PAYROLL_WORK_UNCOVERED, PAYROLL_ATTENDANCE_UNCOVERED).
UNCOVERED="""select 'W:'||md5(e::text),e.contractor_id,(e.eligible_at at time zone 'Asia/Jakarta')::date
 from erp.v_payroll_eligible_work_lines e where e.remaining_qty>0
union all
select 'A:'||ar.id::text,ar.contractor_id,ar.attendance_date from erp.attendance_records ar
 join erp.contractor_workers w on w.id=ar.worker_id join erp.contractors c on c.id=ar.contractor_id
 where coalesce(ar.record_lifecycle,'POSTED')='POSTED' and ar.paid_fraction>0 and w.pay_scheme in('DAILY','HYBRID') and c.attendance_required
  and not exists(select 1 from erp.payroll_attendance_items pai join erp.payroll_settlements ps on ps.id=pai.payroll_id
   where pai.attendance_record_id=ar.id and ps.status<>'REVERSED')"""
READINESS=re.compile(r'(get_owner_financial_snapshot|close_accounting_through|accounting_close_preflight|period_readiness|period_blockers)\w*\s*\(')
STATE=dict(conn=None,case=None,before=None,busy=False)
FIXTURES=[]


def session_state(cur):
    s=cur.execute("select session_user,current_user,coalesce(current_setting('request.jwt.claims',true),''),current_setting('TimeZone'),current_setting('search_path')").fetchone()
    return tuple(s)


def restore_session(cur,state):
    from psycopg import sql
    session,current,claims,zone,path=state
    awp.api.admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true),set_config('TimeZone',%s,true),set_config('search_path',%s,true)",(claims,zone,path))
    if session!=cur.execute('select session_user').fetchone()[0]:
        cur.execute(sql.SQL('set local session authorization {}').format(sql.Identifier(session)))
    if current!=session:cur.execute(sql.SQL('set local role {}').format(sql.Identifier(current)))
    assert session_state(cur)==state,('T2_FIXTURE_SESSION_NOT_RESTORED',session_state(cur),state)


def complete_payroll(cur):
    """Owner fixture completion: the case's own uncovered attendance and work into an APPROVED payroll (not paid)."""
    STATE['busy']=True
    state=session_state(cur);record=dict(case=STATE['case'],payrolls=[],refused=None)
    try:
        cur.execute('savepoint t2_fixture')
        try:
            awp.api.admin(cur)
            rows=[r for r in cur.execute(UNCOVERED).fetchall() if r[0] not in STATE['before']]
            by={}
            for key,contractor,day in rows:by.setdefault(contractor,[]).append((key,day))
            cash=cur.execute('select id from erp.cash_accounts where is_active order by cash_account_code limit 1').fetchone()[0]
            for contractor,items in sorted(by.items(),key=lambda x:str(x[0])):
                lo,hi=min(d for _,d in items),max(d for _,d in items)
                # One active payroll per contractor and day (product rule). When the case's days fall inside a payroll
                # that is approved but not paid, the owner cancels it (cancel_unpaid_payroll) and approves one payroll
                # over the union again: still a debt, nothing paid. A PAID overlap is refused and recorded.
                overlap=cur.execute("""select id,status,period_start,period_end from erp.payroll_settlements where contractor_id=%s
                    and status<>'REVERSED' and period_start<=%s and period_end>=%s order by period_start""",(contractor,hi,lo)).fetchall()
                assert all(o[1]!='PAID' for o in overlap),('T2_FIXTURE_OVERLAPS_PAID_PAYROLL',[str(o[0]) for o in overlap])
                if overlap:
                    awp.chain.prior.as_owner(cur)
                    for o in overlap:cur.execute('select erp.cancel_unpaid_payroll(%s,%s)',(o[0],'T2 fixture: late case work in this period; payroll redone unpaid'))
                    awp.api.admin(cur)
                    lo,hi=min([lo]+[o[2] for o in overlap]),max([hi]+[o[3] for o in overlap])
                pid=awp.uuid.uuid4()
                cur.execute("""insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_cash_account_id,payment_date,manual_adjustment,notes)
                    values(%s,%s,%s,%s,%s,'DRAFT',%s,%s,0,'T2 fixture completion: case work and attendance into an approved payroll (not paid)')""",
                    (pid,'T2-'+pid.hex[:12],contractor,lo,hi,cash,hi))
                awp.chain.prior.as_owner(cur)
                cur.execute('select erp.populate_payroll_draft(%s)',(pid,));cur.execute('select erp.approve_payroll(%s)',(pid,))
                awp.api.admin(cur)
                status=cur.execute('select status from erp.payroll_settlements where id=%s',(pid,)).fetchone()[0]
                assert status=='APPROVED',('T2_FIXTURE_PAYROLL_NOT_APPROVED',status)
                record['payrolls'].append(dict(contractor=str(contractor),start=str(lo),end=str(hi),status=status,
                    work_lines=sum(k.startswith('W:') for k,_ in items),attendance_days=sum(k.startswith('A:') for k,_ in items),
                    redone_unpaid=[dict(id=str(o[0]),status=o[1],start=str(o[2]),end=str(o[3])) for o in overlap]))
            cur.execute('release savepoint t2_fixture')
        except awp.psycopg.Error as exc:
            cur.execute('rollback to savepoint t2_fixture');record['refused']=exc.diag.message_primary
    finally:
        restore_session(cur,state);STATE['busy']=False
    if record['payrolls'] or record['refused']:
        FIXTURES.append(record);print(json.dumps(dict(group='T2_FIXTURE_PAYROLL',**record),default=str),flush=True)


EXECUTE=awp.psycopg.Cursor.execute


def execute(self,query,params=None,**kwargs):
    if STATE['conn'] is not None and self.connection is STATE['conn'] and not STATE['busy'] \
       and READINESS.search(query if isinstance(query,str) else str(query)):
        complete_payroll(self)
    return EXECUTE(self,query,params,**kwargs)


awp.psycopg.Cursor.execute=execute


def fixture(key,op,cur,case_period):
    """Arm the fixture completion for one case; the attendance cases get their two days back from the quieting."""
    if FIXTURE=='NONE':return op
    def run():
        cur.execute('savepoint t2_before')
        try:
            awp.api.admin(cur);before={r[0] for r in cur.execute(UNCOVERED).fetchall()}
        finally:
            cur.execute('rollback to savepoint t2_before');cur.execute('release savepoint t2_before')
        if key.startswith('CROSS:DAY:ATTENDANCE:'):awp.reverse_attendance(cur,case_period)
        STATE.update(conn=cur.connection,case=key,before=before)
        try:
            return op()
        finally:
            STATE.update(conn=None,case=None,before=None)
    return run


def diagnosed(key,op,cur,today):
    """Side channel only (CP6_T2_DIAG=1): when a case fails with a Python assertion (its transaction still usable), print
    the engine answer and how many payroll-eligible work lines the case itself created. The case outcome is re-raised
    unchanged. The reads happen inside savepoints that are rolled back, which also undoes their SET LOCAL/role changes."""
    if not DIAG:return op
    def read(query=None):
        cur.execute('savepoint t2_diag')
        try:
            if query is None:
                r=awp.preflight(cur,today);return r
            awp.api.admin(cur);return set(cur.execute(query).fetchone()[0])
        finally:
            cur.execute('rollback to savepoint t2_diag');cur.execute('release savepoint t2_diag')
    def run():
        try:before=read(ELIGIBLE)
        except awp.psycopg.Error:before=None
        try:
            return op()
        except Exception as exc:
            if not isinstance(exc,awp.psycopg.Error) and before is not None:
                try:
                    r=read();created=read(ELIGIBLE)-before
                    print(json.dumps(dict(group='T2_CASE_DIAG',case=key,engine_status=r and r['status'],blockers=awp.blockers_brief(r),
                                          uncovered_work_lines_created_by_case=len(created)),default=str),flush=True)
                except Exception as diag:
                    print(json.dumps(dict(group='T2_CASE_DIAG',case=key,diagnostic_error=str(diag)[:300])),flush=True)
            raise
    return run


avt.group=group


def change(kind,pg,control_url):
    """AV through its own closed-admission runtime, then the AW and AX T1 installs (development files)."""
    assert kind=='install'
    av=av_runtime.change('install',pg,control_url)
    aw=awp.install_aw();ax=axp.install_ax()
    return dict(status='PASS' if av['status']=='PASS' else 'FAIL',av=av['status'],aw=aw,ax=ax)


# The trial modules read `runtime`; point them at the combined candidate without touching their code.
avt.runtime=types.SimpleNamespace(change=change,verified=axp.ax_verified,pins=av_runtime.pins,
                                  qualify=None,refuse_post_use=None)


def ar_phase(report):
    """AR 174: the sequential group and the 28 races, on the combined candidate (no package cycles: that is T3)."""
    report['au_install']=avt.install_au()
    with avt.psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:avt.api.seed(cur)
    report['candidate_install']=change('install',avt.PG,avt.control())
    seq=avt.group('AR_SEQUENTIAL',avt.ar_sequential)
    report['sequential']={k:seq[k] for k in ('status','counts')}
    with avt.psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:
        axp.ax_verified(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    races=[]
    for kind in avt.inherited.KINDS:
        for winner in ('imported','legacy'):
            races.append(('CONCURRENT_'+kind+'_'+winner.upper()+'_FIRST',lambda k=kind,w=winner:avt.inherited.concurrency(today,k,w)))
    for winner in ('imported','legacy'):
        for same in (False,True):
            races.append((('SAME_HEADER_' if same else 'WINNER_ABORT_')+winner.upper(),lambda w=winner,s=same:avt.inherited.concurrency(today,'MATERIAL',w,commit=s,same_header=s)))
    for variant in ('REPLAY','PAYLOAD','ACTION'):
        races.append(('REQUEST_CONCURRENT_'+variant,lambda v=variant:avt.inherited.request_concurrency(today,v)))
    races.append(('STALE_SNAPSHOT_ISOLATION',lambda:avt.inherited.isolation_guard(today)))
    report['races']={}
    for name,operation in races:
        try:row=operation()
        except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc))
        report['races'][name]=row;avt.save('AR',report)
        print(json.dumps(dict(group='AR_CONCURRENCY',case=name,**row),default=str),flush=True)
    report['case_count']=len(seq['cases'])+len(report['races'])
    ok=report['case_count']==174 and seq['status']=='WRITER_PASS' and all(r['status']=='PASS' for r in report['races'].values())
    report['status']='WRITER_PASS' if ok else 'DISPOSITION_REQUIRED'


ORIGINAL_REGRESSION=avt.regression


def regression_phase(report):
    ORIGINAL_REGRESSION(report)
    # H-01: per-case identity against the AU recorded outcome, next to the old count summary.
    observed={}
    for name in ('business','imports','values'):
        path=avt.OUT/(name.upper()+'.json')
        observed[name.upper()]={k:r['status'] for k,r in json.loads(path.read_text())['cases'].items()}
    new=json.loads((avt.OUT/'NEW_CASES.json').read_text())
    observed['NEW_CASES']={k:r['status'] for k,r in new['cases'].items()}
    report['per_case_identity']=identity.compare(identity.load_expected(),observed)
    print(json.dumps(dict(group='T2_IDENTITY',**report['per_case_identity']),default=str),flush=True)
    if report['per_case_identity']['status']!='IDENTICAL_PER_CASE':report['status']='DISPOSITION_REQUIRED'


def run(phase):
    # Reuse the AV trial driver (writer checkout, clone lifecycle, primary check) with the combined candidate.
    if phase=='ar':avt.qualify=ar_phase
    if phase=='regression':avt.regression=regression_phase
    print(json.dumps(dict(t2_label=LABEL,phase=phase,seed=SEED)),flush=True)
    avt.run({'ar':'qualify','regression':'regression','temporal':'temporal'}[phase])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('ar','regression','temporal'),required=True)
    run(parser.parse_args().phase)
