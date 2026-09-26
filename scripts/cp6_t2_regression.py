"""T2 regression for the combined CP6 candidate: AU + AV + AW, AX, AY, AZ, BA, BB, BC and BD (T1 installs).

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

BD (25 Sep, owner: every CR in CP6): the candidate also includes BD, priced laundry deliveries, vendor invoices, the laundry
policy settings pending by default and ALL-W05 (scripts/cp6_bd_build.py).
BC (25 Sep, owner: every CR in CP6): the candidate also includes BC, the accessory service, return and inspection
workflow with its owner policy settings pending by default (scripts/cp6_bc_build.py).
BB (25 Sep, owner: every ALL state in CP6): the candidate also includes BB, the open cutover states of ALL (opening
settlement facade, credits and returns, open purchase orders, wages before and after cutover, cutting pickup, BS split and
open reworks of opening WIP; scripts/cp6_bb_build.py). BA (25 Sep): the candidate now includes BA, the independent audit's product fixes (A1 import identity, A3 dated WIP
remaining, A4 recost cents, A5 selectors, A6 single close filing, A9 dated advance capacity, A10 WIP product binding).
Cases that move against the recorded outcomes are listed for disposition as before; the frozen results stay recorded.

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

Owner decisions 24 Sep (AS oracle, quoted): "Saya setujui penyesuaian oracle hanya untuk delapan kasus AS tersebut:
event/jurnal HPP PO mengikuti 22 Sep pada fixture ini, karena barang jadi dan penjualan terjadi hari itu. Nominal, tanggal
invoice, dan revaluasi bahan tetap sesuai oracle lama." Then, asked about the conflict with the approved WIP principle
(the fixture cuts the material on 22 Sep), the owner chose "Ikut prinsip WIP": the material-to-WIP revaluation follows
the cutting day (22 Sep), the invoice journal stays on 21 Sep. The eight NEW_CASES ids DATE:False:<zone>:True:<cost> keep
the frozen AS oracle's own result (status unchanged); the harness adds approved_oracle_20260924, evaluated inside the
case savepoint from the database: the fixture's cutting, FG lots and sales must share one day L after the invoice date E;
every new PO HPP event and PO_HPP_GL_SYNC journal (economic and posting date), every new revaluation event and
MATERIAL_COST_REVALUATION journal must be on L; every other new journal (the supplier invoice) on E as the old oracle
requires; and the old oracle may have failed on its date checks only. No other case, nominal or check is touched. MATCH
is not called PASS until independently reviewed.
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
import cp6_ay_probe as ayp
import cp6_az_probe as azp
import cp6_ba_probe as bap
import cp6_bb_probe as bbp
import cp6_bc_probe as bcp
import cp6_bd_probe as bdp
import cp6_be_probe as bep
# BE final verification includes historical pocket receipt certainty (ordered DDL).
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
        cases=[(key,fixture(key,approved(key,diagnosed(key,op,cur,today),cur),cur,own[0])) for key,op in factory(cur,today)]
        if name=='NEW_CASES':
            assert sorted(k for k,_ in cases if k in APPROVED_AS_CASES)==sorted(APPROVED_AS_CASES),'T2_APPROVED_AS_CASES_NOT_FOUND'
        return cases
    return ORIGINAL_GROUP(name,quieted)


APPROVED_AS_CASES=tuple('DATE:False:%s:True:%s'%(z,c) for z in ('Asia/Jakarta','UTC','Etc/GMT+12','Pacific/Kiritimati') for c in ('20','20.003'))
APPROVED_DECISION=('Owner 24 Sep: event/jurnal HPP PO mengikuti 22 Sep pada fixture ini, karena barang jadi dan penjualan terjadi hari itu; '
                   'nominal dan tanggal invoice tetap sesuai oracle lama; revaluasi bahan ke WIP ikut prinsip WIP (hari potong, 22 Sep); '
                   'hanya delapan kasus AS ini.')


def approved_oracle(cur,row):
    """The owner-approved date oracle for the eight AS cases, read from the database before the case savepoint is undone."""
    obs=row.get('observations') or {}
    E=str(row.get('invoice_date'))
    hpp=obs.get('hpp_events') or [];reval=obs.get('revaluation_events') or [];journals=obs.get('journals') or []
    checks=dict(scope=row.get('closed') is False and row.get('partial') is True and str(row.get('recognition_date'))==E,
                replay_exact=row.get('replay_exact') is True,context_cleared=row.get('context_cleared') is True)
    awp.api.admin(cur)
    ids=[str(h[0]) for h in hpp]
    pos=[r[0] for r in cur.execute('select distinct po_id from erp.po_hpp_gl_events where id=any(%s::uuid[])',(ids,)).fetchall()]
    fixture=dict(po=pos)
    if len(pos)==1:
        fixture['lot_days']=sorted({str(r[0]) for r in cur.execute(
            "select erp._cp3_business_date(produced_at) from erp.fg_lots where po_id=%s and lot_origin in('PRODUCTION','CONVERSION') and initial_qty_pcs>0",(pos[0],))})
        fixture['sale_days']=sorted({str(r[0]) for r in cur.execute(
            """select erp._cp3_business_date(h.sale_date) from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
               join erp.sales_headers h on h.id=i.sale_id join erp.fg_lots l on l.id=a.lot_id
               where l.po_id=%s and h.status in('POSTED','PARTIAL_PAID','PAID')""",(pos[0],))})
        fixture['returns']=cur.execute("select count(*) from erp.sales_return_items ri join erp.fg_lots l on l.id=ri.lot_id where l.po_id=%s",(pos[0],)).fetchone()[0]
        fixture['cut_days']=sorted({str(r[0]) for r in cur.execute(
            """select erp._cp3_business_date(m.physical_at) from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
               where cg.po_id=%s and m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and m.reversal_of_id is null""",(pos[0],))})
        fixture['revaluation_journals']=sorted(str(r[0]) for r in cur.execute(
            'select journal_entry_id from erp.material_cost_revaluation_events where id=any(%s::uuid[])',([str(r[0]) for r in reval],)).fetchall())
        fixture['event_journals']=sorted(str(r[0]) for r in cur.execute('select journal_entry_id from erp.po_hpp_gl_events where id=any(%s::uuid[])',(ids,)).fetchall())
    applicable=len(pos)==1 and len(fixture.get('lot_days',[]))==1 and fixture.get('sale_days')==fixture.get('lot_days') \
               and fixture.get('cut_days')==fixture.get('lot_days') and fixture.get('returns')==0 and fixture['lot_days'][0]>E
    L=fixture['lot_days'][0] if applicable else None
    sync=[j for j in journals if j[1]=='PO_HPP_GL_SYNC'];recost=[j for j in journals if j[1]=='MATERIAL_COST_REVALUATION']
    other=[j for j in journals if j[1] not in ('PO_HPP_GL_SYNC','MATERIAL_COST_REVALUATION')]
    fixture['other_journals']=[[str(v) for v in j[1:4]] for j in other]
    checks.update(fixture_cut_goods_and_sale_one_day_after_invoice=applicable,
                  revaluation_events_on_cutting_day=bool(reval) and all(str(r[1])==L for r in reval),
                  revaluation_journals_on_cutting_day=bool(recost) and all(str(j[2])==L and str(j[3])==L for j in recost)
                      and sorted(str(j[0]) for j in recost)==fixture.get('revaluation_journals'),
                  hpp_events_on_goods_and_sale_day=bool(hpp) and all(str(h[1])==L for h in hpp),
                  hpp_journals_on_goods_and_sale_day=bool(sync) and all(str(j[2])==L and str(j[3])==L for j in sync)
                      and sorted(str(j[0]) for j in sync)==fixture.get('event_journals'),
                  other_journals_are_the_supplier_invoice_on_E=bool(other) and all(j[1]=='MATERIAL_SUPPLIER_INVOICE' and str(j[2])==E and str(j[3])==E for j in other))
    checks['old_oracle_failed_only_on_dates']=set((row.get('mismatches') or {}))<={'hpp_events','journal_posting_date','revaluation_events'}
    status='NOT_APPLICABLE' if not applicable else 'MATCH' if all(checks.values()) else 'MISMATCH'
    return dict(decision=APPROVED_DECISION,status=status,invoice_date=E,cut_goods_and_sale_day=L,checks=checks,fixture=fixture,
                old_oracle_status=row.get('status'),old_oracle_mismatch_keys=sorted((row.get('mismatches') or {})))


def approved(key,op,cur):
    if key not in APPROVED_AS_CASES:return op
    def run():
        row=op()
        # Own savepoint: an error here is recorded under the approved key and never changes the frozen oracle's status.
        cur.execute('savepoint t2_approved')
        try:
            result=approved_oracle(cur,row)
        except Exception as exc:
            cur.execute('rollback to savepoint t2_approved')
            result=dict(decision=APPROVED_DECISION,status='ERROR',error=str(exc)[:1000],old_oracle_status=row.get('status'))
        finally:
            cur.execute('release savepoint t2_approved')
        row['approved_oracle_20260924']=result;APPROVED_RESULTS[key]=result['status']
        print(json.dumps(dict(group='T2_APPROVED_ORACLE',case=key,**result),default=str),flush=True)
        return row
    return run


APPROVED_RESULTS={}


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


def fixture_summary(report):
    """Independent audit B5: every fixture completion of this run in one line (each is also printed as it happens,
    T2_FIXTURE_PAYROLL), so the auditor can check that no case testing an uncovered or unpaid readiness state was
    completed. The seed quieting is printed per group (T2_SEED_QUIETED)."""
    report['fixture_completions']=dict(mode=FIXTURE,seed=SEED,count=len(FIXTURES),cases=[r['case'] for r in FIXTURES],
        payrolls=sum(len(r['payrolls']) for r in FIXTURES),refused=[dict(case=r['case'],refused=r['refused']) for r in FIXTURES if r['refused']])
    print(json.dumps(dict(group='T2_FIXTURE_SUMMARY',**report['fixture_completions']),default=str),flush=True)


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
    """AV through its own closed-admission runtime, then the AW, AX, AY, AZ and BA T1 installs (development files; BA: the
    independent audit's product fixes, 25 Sep 2026)."""
    assert kind=='install'
    av=av_runtime.change('install',pg,control_url)
    aw=awp.install_aw();ax=axp.install_ax();ay=ayp.install_ay();az=azp.install_az();ba=bap.install_ba();bb=bbp.install_bb();bc=bcp.install_bc();bd=bdp.install_bd();be=bep.install_be()
    return dict(status='PASS' if av['status']=='PASS' else 'FAIL',av=av['status'],aw=aw,ax=ax,ay=ay,az=az,ba=ba,bb=bb,bc=bc,bd=bd,be=be)


# The trial modules read `runtime`; point them at the combined candidate without touching their code.
avt.runtime=types.SimpleNamespace(change=change,verified=bep.verified,pins=av_runtime.pins,
                                  qualify=None,refuse_post_use=None)


def superseding_cases(cur,today):
    """R12 handoff task 2: the replacement of AR_SEQUENTIAL ACCESSORY_CONNECTED_ZERO (a mandor note line priced 0.00 by hand
    posts), whose disposition is EXPECTED_CHANGE (ERP-DEC02, M:5023 B; auditors R12 §1). With BC the same line, built with the
    same fixture of the frozen harness, is refused BC_FREE_REQUIRES_POLICY (free goods only through the owner's Special line)
    and nothing changes (boundary and ledger). The old case keeps its recorded result (INCOMPLETE) and is marked superseded in
    docs/cp6-bc-case-table.md; the frozen harness file is not edited."""
    import cp6_ao_ap_installed as installed,cp6_accessory_issue_trial as accessories
    a=types.SimpleNamespace(**vars(installed))
    def zero_refused():
        f=accessories.fixture(a,cur,today,12);payload=f['payload'];payload['items'][0]['manual_price']='0.00'
        boundary=a.actors.boundary(cur);ledger=a.production.ledger(cur)
        result=a.inherited.refused(cur,lambda:accessories.call(a,cur,'POST',payload))
        ok=('BC_FREE_REQUIRES_POLICY' in (result.get('message') or '') and a.actors.boundary(cur)==boundary and a.production.ledger(cur)==ledger)
        return dict(status='PASS' if ok else 'FAIL',refusal=result,supersedes='AR_SEQUENTIAL:ACCESSORY_CONNECTED_ZERO',
                    disposition='EXPECTED_CHANGE (ERP-DEC02, M:5023 B)',boundary_unchanged=a.actors.boundary(cur)==boundary)
    return [('ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY',zero_refused)]


def ar_phase(report):
    """AR 174: the sequential group and the 28 races, on the combined candidate (no package cycles: that is T3)."""
    report['au_install']=avt.install_au()
    with avt.psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:avt.api.seed(cur)
    report['candidate_install']=change('install',avt.PG,avt.control())
    seq=avt.group('AR_SEQUENTIAL',avt.ar_sequential)
    report['sequential']={k:seq[k] for k in ('status','counts')}
    sup=avt.group('AR_SUPERSEDING',superseding_cases)
    report['superseding']=dict(status=sup['status'],counts=sup.get('counts'),cases={k:r['status'] for k,r in sup['cases'].items()})
    print(json.dumps(dict(group='AR_SUPERSEDING',**report['superseding']),default=str),flush=True)
    with avt.psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:
        bep.verified(cur)
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
    fixture_summary(report)


ORIGINAL_REGRESSION=avt.regression


def ao_trial_namespace():
    """The AO initial-import trial's own case functions from the frozen writer file, without its module-level runner
    (the file runs its whole trial on import); only its imports, its actors/base/production binding and its function
    definitions are taken, unchanged."""
    import ast
    source=(Path.cwd()/'scripts/cp6_initial_import_ao_trial.py').read_text()
    tree=ast.parse(source)
    skip={'cp6_v2620an_runtime','cp6_v2620ao_definitions','cp6_v2620n_rollback_guards'}
    keep=[]
    for node in tree.body:
        if isinstance(node,ast.Import) and not any(a.name in skip for a in node.names):keep.append(node)
        elif isinstance(node,ast.ImportFrom) and node.module not in skip:keep.append(node)
        elif isinstance(node,ast.Assign) and ast.unparse(node.targets[0]).strip('()')=='actors, base, production':keep.append(node)
        elif isinstance(node,ast.FunctionDef) and node.name in ('retail','invoice_date','direct_correction_reversal'):keep.append(node)
    names=sorted(n.name for n in keep if isinstance(n,ast.FunctionDef))
    assert names==['direct_correction_reversal','invoice_date','retail'],names
    AO_SOURCE['functions']={n.name:ast.get_source_segment(source,n) for n in keep if isinstance(n,ast.FunctionDef)}
    assert sum(isinstance(n,ast.Assign) for n in keep)==1,'AO_TRIAL_ACTORS_BINDING'
    namespace={'__name__':'cp6_initial_import_ao_trial_cases'}
    exec(compile(ast.Module(body=keep,type_ignores=[]),'cp6_initial_import_ao_trial.py','exec'),namespace)
    AO_SOURCE['namespace']=namespace
    return namespace,hashlib_sha(source)


def hashlib_sha(text):
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def ao_trial_cases(cur,today):
    """The AO trial's 12 cases (RETAIL, BAD_PRICE, FRACTIONAL_PCS, INVOICE x4, DIRECT_CORRECTION_REVERSAL x2) with the
    foundation its runner sets up. Added to T2 on 24 Sep: the AO trial exercises the invoice recost path that AY and AZ
    change and was not part of the T2 set. The period is opened from 2026-01-02 as on genuine AN; the closed variants
    close their own receipt day."""
    ns,sha=ao_trial_namespace()
    AO_SOURCE['sha256']=sha
    actors,base,production,foundation=ns['actors'],ns['base'],ns['production'],ns['foundation']
    avt.predecessor.historical.prior.set_open_period(cur,REOPEN)
    actors.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'))
    # The runner loads the CP3 seed and the CP6 laundry/QC seed on genuine AN; the T2 clone already carries the CP3 seed
    # (the AU seed), so only the laundry/QC seed is loaded, and only when its race PO is missing (T2 run 12 stopped on the
    # duplicate CP3 contractor).
    AO_SOURCE['foundation']='PRESENT'
    if not cur.execute("select count(*) from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()[0]:
        reader=getattr(base,'read_psql_seed',None) or __import__('cp6_v2620e_counterexample_regression').read_psql_seed
        cur.execute(reader(Path('supabase/tests/cp6_laundry_qc_concurrency_seed.sql')),prepare=False)
        AO_SOURCE['foundation']='LAUNDRY_QC_SEED_LOADED'
    actors.admin(cur)
    start=production.at(today-timedelta(days=1),0)
    model,contractor=cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
    foundation.OWNER=base.OPERATOR_AUTH
    foundation.MASTER=dict(model=model,contractor=contractor,start=start,
        supplier=cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0],
        pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT'").fetchone()[0],
        t0=start+timedelta(hours=1),t3=start+timedelta(hours=4))
    retail,invoice_date,reversal=ns['retail'],ns['invoice_date'],ns['direct_correction_reversal']
    cases=[('RETAIL:'+str(f),lambda f=f:retail(cur,today,f)) for f in (12,144)]
    cases+=[('BAD_PRICE:'+p,lambda p=p:retail(cur,today,12,p)) for p in ('-1','NaN','0.005')]
    cases+=[('FRACTIONAL_PCS',lambda:retail(cur,today,12,qty='7.0000001'))]
    cases+=[('INVOICE:'+z+':'+str(c),lambda z=z,c=c:invoice_date(cur,today,z,c)) for z in ('UTC','Pacific/Kiritimati') for c in (False,True)]
    cases+=[('DIRECT_CORRECTION_REVERSAL:'+str(c),lambda c=c:reversal(cur,today,c)) for c in (False,True)]
    return cases


AO_SOURCE={}


# ------------------------------------------------------------------ owner decision 24 Sep (second answer)
# The frozen oracles of 17 cases moved with AY/AZ (see frozen_oracle_moves). Owner, quoted: "Boleh untuk tiga kelompok; AS
# ADJUSTMENT_DATE jangan disahkan otomatis. ... lanjutkan pengecek otomatis dan perbarui tiga kelompok pertama sesuai aturan
# per kasus. Untuk ADJUSTMENT_DATE, telusuri pembaca effective_date dulu; bila aman, ubah oracle tanggalnya dengan bukti. Bila
# tidak, benahi model tanggalnya. Nominal dan ekspektasi lain tetap. Belum ada izin menyebut kasus yang masih INCOMPLETE
# sebagai PASS." The frozen oracles stay as they are and their results stand (INCOMPLETE/COUNTEREXAMPLE); the approved
# oracle of each case runs the same frozen case text with exactly the listed date substitutions (each asserted to occur
# once) and is reported under its own key, never as the frozen case's PASS.
APPROVED_B_DECISION={
    'CALENDAR':'Owner 24 Sep: 12 kalender HOLD - tanggal perpindahan nilai ke WIP mengikuti hari potong; status tetap HOLD.',
    'AO_OPEN':'Owner 24 Sep: AO periode terbuka - tanggal koreksi WIP/FG mengikuti hari barangnya berpindah tahap; jurnal invoice tetap pada tanggal invoice.',
    'AO_CLOSED':'Owner 24 Sep: AO periode tertutup - tanggal posting mengikuti hari pengakuan, tanggal ekonomi invoice tetap tersimpan (sejak AS).',
    'ADJUSTMENT':('Owner 24 Sep: ADJUSTMENT_DATE tidak disahkan otomatis; telusuri pembaca effective_date, bila aman ubah oracle tanggalnya '
                  'dengan bukti. Writer trace: readers are run_v267_financial_truth_checks V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER (fact '
                  'effective_date = its own journal economic_date; AZ sets both to the same date) and the pocket_period_recost trigger '
                  '(pocket recost journal date); no reader requires the invoice date. Proof in the case: those checks and the pocket checks '
                  'do not increase after the invoice and after its reversal.')}


def principle_truth(cur):
    """The product readers of material adjustment revaluation facts (issue counts): the fact/journal ledger check, the adjustment
    conservation check and the pocket checks (the pocket recost trigger reads the fact date)."""
    rows=cur.execute("""select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name like 'V2620T_MATERIAL_ADJUSTMENT%%'
      union all select check_name,issue_count from erp.pocket_fabric_checks_v1()
      union all select check_name,issue_count from erp.pocket_period_checks_v1()""").fetchall()
    return {r[0]:int(r[1]) for r in rows}


def principle_variant(name,source,namespace,subs):
    """The frozen function text with exactly the listed substitutions (each must occur once), compiled in its own globals."""
    import textwrap
    text=textwrap.dedent(source)
    for old,new in subs:
        assert text.count(old)==1,('T2_PRINCIPLE_SUBSTITUTION',name,old[:80])
        text=text.replace(old,new)
    scope=dict(namespace)
    exec(compile(text,'<principle:%s>'%name,'exec'),scope)
    return scope[name],hashlib_sha(text)


def principle_goods_day(cur,purchase):
    """The one business day on which the fixture of this purchase was cut, finished and sold (AA partial production)."""
    rows=cur.execute("""with po as(select distinct cg.po_id,cg.id from erp.cutting_groups cg
        join erp.material_stock_movements m on m.source_id=cg.id and m.source_type='CUTTING_GROUP' and m.reversal_of_id is null
        join erp.material_purchase_items i on i.material_id=m.material_id where i.purchase_id=%s)
      select 'CUT',erp._cp3_business_date(m.physical_at) from erp.material_stock_movements m join po on po.id=m.source_id
        where m.source_type='CUTTING_GROUP' and m.reversal_of_id is null
      union select 'LOT',erp._cp3_business_date(fl.produced_at) from erp.fg_lots fl join po on po.po_id=fl.po_id
        where fl.lot_origin in('PRODUCTION','CONVERSION') and fl.initial_qty_pcs>0
      union select 'SALE',erp._cp3_business_date(h.sale_date) from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id
        join erp.sales_headers h on h.id=si.sale_id join erp.fg_lots fl on fl.id=a.lot_id join po on po.po_id=fl.po_id
        where h.status in('POSTED','PARTIAL_PAID','PAID')""",(purchase,)).fetchall()
    days={d for _,d in rows}
    assert {k for k,_ in rows}=={'CUT','LOT','SALE'} and len(days)==1,('T2_PRINCIPLE_ONE_GOODS_DAY',rows)
    return days.pop()


AO_INVOICE_SUBS=[
    ("   fresh=[r for r in fresh if r[0] not in before]\n",
     "   fresh=[r for r in fresh if r[0] not in before]\n   principle_day[:]=[principle_goods_day(cursor,payload['purchase_id'])]\n"),
    ("assert all(r[2]==invoice and r[3]==(today if closed else invoice) for r in fresh),fresh",
     "assert all(r[2]==(invoice if closed or r[1]=='MATERIAL_SUPPLIER_INVOICE' else principle_day[0]) and "
     "r[3]==(today if closed else invoice if r[1]=='MATERIAL_SUPPLIER_INVOICE' else principle_day[0]) for r in fresh),fresh"),
    (" dated_journals=[]\n"," dated_journals=[]\n principle_day=[]\n"),
    ("all(r[1]==invoice for r in o['state']['revaluation_events'])",
     "all(r[1]==(today if closed else principle_day[0]) for r in o['state']['revaluation_events'])")]
AS_ADJUSTMENT_SUBS=[
    ("""    if closed:
        cur.execute('select erp.close_accounting_through(%s,%s)',(f['purchase_day'],'AS adjustment close'))""",
     """    api.admin(cur)
    adjustment_day=max(f['purchase_day'],cur.execute('select erp._cp3_business_date(physical_at) from erp.material_adjustments where id=%s',(adjustment,)).fetchone()[0])
    api.ordinary(cur)
    if closed:
        cur.execute('select erp.close_accounting_through(%s,%s)',(f['purchase_day'],'AS adjustment close'))"""),
    ("assert rows and all(r[1]==f['purchase_day'] for r in rows), rows",
     "assert rows and all(r[1]==(f['purchase_day'] if closed else adjustment_day) for r in rows), rows"),
    ("expected = today if closed else f['purchase_day']","expected = today if closed else adjustment_day"),
    ("errors = [r for r in rows if r[0]!=f['purchase_day'] or r[2]!=expected]",
     "errors = [r for r in rows if r[0]!=(f['purchase_day'] if closed else adjustment_day) or r[2]!=expected]"),
    # proof that no product reader of the fact date breaks: its readers' issue counts do not increase
    ("    version = cur.execute('select row_version from erp.material_purchase_headers where id=%s',(f['purchase'],)).fetchone()[0]\n",
     "    version = cur.execute('select row_version from erp.material_purchase_headers where id=%s',(f['purchase'],)).fetchone()[0]\n"
     "    truth_before=principle_truth(cur)\n"),
    ("    probe.invoice.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version)\n    api.admin(cur)\n",
     "    probe.invoice.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version)\n    api.admin(cur)\n"
     "    truth_after_invoice=principle_truth(cur)\n"),
    ("    api.receipts.rpc(api,cur,'reverse_material_supplier_invoice_v2',doc[0],'AS linked invoice inverse',uuid.uuid4(),doc[1])\n    api.admin(cur)\n",
     "    api.receipts.rpc(api,cur,'reverse_material_supplier_invoice_v2',doc[0],'AS linked invoice inverse',uuid.uuid4(),doc[1])\n    api.admin(cur)\n"
     "    truth_after_reversal=principle_truth(cur)\n"),
    ("    return dict(status='COUNTEREXAMPLE' if errors else 'PASS',closed=closed,",
     "    truth_ok=set(truth_before)>={'V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER','V2620T_MATERIAL_ADJUSTMENT_REVALUATION'} and \\\n"
     "        set(truth_after_invoice)==set(truth_before)==set(truth_after_reversal) and \\\n"
     "        all(truth_after_invoice[k]<=v and truth_after_reversal[k]<=v for k,v in truth_before.items())\n"
     "    return dict(status='COUNTEREXAMPLE' if errors or not truth_ok else 'PASS',adjustment_day=adjustment_day,truth_ok=truth_ok,\n"
     "                truth=dict(before=truth_before,after_invoice=truth_after_invoice,after_reversal=truth_after_reversal),closed=closed,")]
CALENDAR_SUBS=[
    ("if str(event[1])!=str(raw['purchase_date']):differences['material_event_date']=event",
     # the cutting day of the calendar fixture (AA partial production cuts, finishes and sells on purchase day + 1)
     "if str(event[1])!=str(date.fromisoformat(str(raw['purchase_date']))+timedelta(days=1)):differences['material_event_date']=event")]
PENDING={}


def pending_owner_cases(cur,today):
    """The approved oracles of the four AO INVOICE cases and of AS ADJUSTMENT_DATE:False (the calendar policy oracle is checked
    where it runs, see below)."""
    ao_trial_cases(cur,today)   # the AO trial's foundation for its invoice cases
    ns=AO_SOURCE['namespace']
    invoice_principle,sha_invoice=principle_variant('invoice_date',AO_SOURCE['functions']['invoice_date'],
                                                    dict(ns,principle_goods_day=principle_goods_day),AO_INVOICE_SUBS)
    import inspect
    adjustment_principle,sha_adjustment=principle_variant('adjustment_date',inspect.getsource(avt.independent.adjustment_date),
                                                          dict(vars(avt.independent),principle_truth=principle_truth),AS_ADJUSTMENT_SUBS)
    PENDING['sources']=dict(invoice_date=sha_invoice,adjustment_date=sha_adjustment)
    cases=[('AS:ADJUSTMENT_DATE:False',lambda:adjustment_principle(cur,today,False))]
    cases+=[('AO:INVOICE:%s:%s'%(z,c),lambda z=z,c=c:invoice_principle(cur,today,z,c)) for z in ('UTC','Pacific/Kiritimati') for c in (False,True)]
    return cases


ORIGINAL_CALENDAR_POLICY=avt.independent.calendar_policy


def calendar_policy_with_pending(raw):
    """The frozen calendar policy oracle, unchanged; the pending-decision variant is recorded next to it."""
    result=ORIGINAL_CALENDAR_POLICY(raw)
    try:
        variant,sha=principle_variant('calendar_policy',__import__('inspect').getsource(ORIGINAL_CALENDAR_POLICY),
                                      dict(vars(avt.independent),date=date,timedelta=timedelta),CALENDAR_SUBS)
        pending=variant(raw)
        result['approved_oracle_20260924b']=dict(decision=APPROVED_B_DECISION['CALENDAR'],status='MATCH' if pending['status']=='PASS' else pending['status'],
                                                 source_sha256=sha,mismatches=[o['mismatches'] for o in pending['observations']])
    except Exception as exc:
        result['approved_oracle_20260924b']=dict(decision=APPROVED_B_DECISION['CALENDAR'],status='ERROR',error=str(exc)[:1000])
    return result


avt.independent.calendar_policy=calendar_policy_with_pending


C0_ORACLES=Path(__file__).resolve().parent/'cp6_c0_oracles_auditor.py'
C0_ORACLES_SHA256='7c2c19b6e722d325ba902cfd9eb1ae2f98d4e2ec27245070ab485df0af9e66a7'
C0_ADJUSTMENT='G8C0:AS:ADJUSTMENT_DATE:False'


def c0_oracle_group():
    """Independent audit round 9, W2: the post-addendum C0 oracles as a routine T2 group, next to the frozen results.

    The oracle file is the auditor's audit/scenarios/c0_round8/gpt_c0_oracles.py (branch audit/cp6-final-20260924-gpt-a0bcadf),
    copied byte for byte and pinned by hash: 8 AS + 12 calendar + 4 AO + 1 adjustment, money in Decimal, dates by C0 D01.1-5
    (ratified e83d56e6; the adjustment's value part on max(E, adjustment day), D01.3). It runs in the auditor's own strict
    group (cp6_auditor_runner.strict_group, savepoint per case), not in the quieted T2 group, so neither the seed quieting
    nor the payroll completion touches it, as in the auditor's runs 36098555186 and 36099496005. The only addition is the
    auditor's transport correction of the adjustment case (gpt_http_and_adjustment.py, transport_rev2): the schema USAGE
    that the receipt helper revokes unconditionally is given back to the native runner before each read. The frozen
    assertions and results of the 25 old ids are not touched; this group reports under its own G8C0 ids."""
    import hashlib,importlib.util
    import cp6_auditor_runner as runner
    sha=hashlib.sha256(C0_ORACLES.read_bytes()).hexdigest()
    assert sha==C0_ORACLES_SHA256,('T2_C0_ORACLE_FILE_CHANGED',sha)
    spec=importlib.util.spec_from_file_location('cp6_c0_oracles_auditor',C0_ORACLES)
    c0=importlib.util.module_from_spec(spec);spec.loader.exec_module(c0)
    original=c0.observe

    def restored(cur,days):
        c0.api.admin(cur)
        if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:
            cur.execute('grant usage on schema erp to authenticated')
        return original(cur,days)

    def adjustment(op):
        def run():
            c0.observe=restored
            try:
                row=op()
                row['native_fixture_correction']=('restore only the runner grant removed by cp6_initial_import_receipt_trial.rpc '
                                                  '(auditor transport_rev2)')
                return row
            finally:
                c0.observe=original
        return run

    def cases(cur,today):
        return [(key,adjustment(op) if key==C0_ADJUSTMENT else op) for key,op in c0.cases(cur,today)]

    saved=runner.r1.OUT;runner.r1.OUT=avt.OUT   # the group's JSON goes with the T2 artifact
    try:
        group=runner.strict_group('T2_C0_ORACLE',cases,bep.verified)
    finally:
        runner.r1.OUT=saved
    return dict(status=group['status'],counts=group.get('counts'),final=group.get('final'),planned=len(group.get('planned_case_ids') or []),
                error=group.get('error'),source='audit/scenarios/c0_round8/gpt_c0_oracles.py',source_sha256=sha,
                oracle='C0 D01.1-5 (ratified e83d56e6), numbers and prefixes of the auditor file',
                note='New group; the frozen results of the 25 old ids stay as recorded.')


def regression_phase(report):
    ORIGINAL_REGRESSION(report)
    # The calendar policy oracle of the 12 historical HOLD cases (part of the regression's own verdict) is in the report
    # file only; print it so the log shows it too (it was not visible in runs 1-10).
    for key,policy in sorted((report.get('calendar_policy') or {}).items()):
        print(json.dumps(dict(group='T2_CALENDAR_POLICY',case=key,status=policy.get('status'),
                              mismatches=[o.get('mismatches') for o in policy.get('observations',[])]),default=str),flush=True)
    print(json.dumps(dict(group='T2_REGRESSION_VERDICT',status=report.get('status'),new_cases=report.get('new_cases'),
                          calendar_policy_count=len(report.get('calendar_policy') or {})),default=str),flush=True)
    # H-01: per-case identity against the AU recorded outcome, next to the old count summary.
    observed={}
    for name in ('business','imports','values'):
        path=avt.OUT/(name.upper()+'.json')
        observed[name.upper()]={k:r['status'] for k,r in json.loads(path.read_text())['cases'].items()}
    new=json.loads((avt.OUT/'NEW_CASES.json').read_text())
    observed['NEW_CASES']={k:r['status'] for k,r in new['cases'].items()}
    # AO trial (added coverage, 24 Sep): its recorded outcome at AO was 12 PASS (WRITER_TRIAL_PASS).
    try:
        ao=avt.group('AO_TRIAL',ao_trial_cases)
        report['ao_trial']=dict(status=ao['status'],counts=ao['counts'],source_sha256=AO_SOURCE.get('sha256'),foundation=AO_SOURCE.get('foundation'),
                                moved={k:r['status'] for k,r in ao['cases'].items() if r['status']!='PASS'})
    except Exception as exc:
        report['ao_trial']=dict(status='INCOMPLETE',error=str(exc)[:2000])
    print(json.dumps(dict(group='T2_AO_TRIAL',**report['ao_trial']),default=str),flush=True)
    # Owner decision 24 Sep (second answer): the approved oracles of the moved cases, reported under their own key.
    try:
        pending=avt.group('APPROVED_ORACLE_B',pending_owner_cases)
        cases={k:dict(approved_oracle='MATCH' if r['status']=='PASS' else r['status'],
                      decision=APPROVED_B_DECISION['ADJUSTMENT' if k.startswith('AS:') else 'AO_CLOSED' if k.endswith(':True') else 'AO_OPEN'])
               for k,r in pending['cases'].items()}
    except Exception as exc:
        pending,cases=dict(status='INCOMPLETE',counts={},error=str(exc)[:2000]),{}
    calendar={k:(v.get('approved_oracle_20260924b') or {}).get('status') for k,v in (report.get('calendar_policy') or {}).items()}
    report['approved_oracle_20260924b']=dict(status=pending['status'],counts=pending.get('counts'),cases=cases,error=pending.get('error'),
                                             sources=PENDING.get('sources'),calendar_policy=calendar,calendar_decision=APPROVED_B_DECISION['CALENDAR'],
                                             note='Frozen results stand (INCOMPLETE/COUNTEREXAMPLE/HOLD); MATCH is the approved oracle, not a frozen PASS.')
    print(json.dumps(dict(group='T2_APPROVED_ORACLE_B',**report['approved_oracle_20260924b']),default=str),flush=True)
    # The approved AS oracle: all eight evaluated (the wrapper is active only with the quieted seed).
    report['approved_oracle_20260924']=dict(results=APPROVED_RESULTS,match=sum(v=='MATCH' for v in APPROVED_RESULTS.values()),of=len(APPROVED_AS_CASES))
    print(json.dumps(dict(group='T2_APPROVED_ORACLE_SUMMARY',**report['approved_oracle_20260924'])),flush=True)
    try:
        report['c0_oracle']=c0_oracle_group()
    except Exception as exc:
        report['c0_oracle']=dict(status='INCOMPLETE',error=str(exc)[:2000])
    print(json.dumps(dict(group='T2_C0_ORACLE_SUMMARY',**report['c0_oracle']),default=str),flush=True)
    assert SEED!='QUIETED' or sorted(APPROVED_RESULTS)==sorted(APPROVED_AS_CASES),('T2_APPROVED_ORACLE_NOT_EVALUATED',sorted(APPROVED_RESULTS))
    report['per_case_identity']=identity.compare(identity.load_expected(),observed)
    print(json.dumps(dict(group='T2_IDENTITY',**report['per_case_identity']),default=str),flush=True)
    if report['per_case_identity']['status']!='IDENTICAL_PER_CASE':report['status']='DISPOSITION_REQUIRED'
    # The AO trial's recorded outcome is 12 PASS; any other result needs a disposition too (independent review 24 Sep).
    if report['ao_trial'].get('status')!='WRITER_PASS':report['status']='DISPOSITION_REQUIRED'
    # W2 (round 9): the C0 oracle group must pass 25/25 in full; anything else is listed for disposition.
    if report['c0_oracle'].get('status')!='PASS' or (report['c0_oracle'].get('counts') or {}).get('PASS')!=25:report['status']='DISPOSITION_REQUIRED'
    fixture_summary(report)


def run(phase):
    # Reuse the AV trial driver (writer checkout, clone lifecycle, primary check) with the combined candidate.
    if phase=='ar':avt.qualify=ar_phase
    if phase=='regression':avt.regression=regression_phase
    import cp6_run_identity as run_identity
    run_identity.announce(LABEL,phase=phase,seed=SEED)
    print(json.dumps(dict(t2_label=LABEL,phase=phase,seed=SEED)),flush=True)
    avt.run({'ar':'qualify','regression':'regression','temporal':'temporal'}[phase])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('ar','regression','temporal'),required=True)
    run(parser.parse_args().phase)
