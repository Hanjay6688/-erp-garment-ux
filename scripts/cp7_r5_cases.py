"""r5 fixes of the r4 audits (candidate 663f6fae), spliced into the CP17 harness after r4.

R5-01 (Sol SOL-R4-001, S1, r4 report audit/sol_cp17_r4): a valid FG_REPAIR Nota (two repair wages of 2 and 1 pcs at
2,000, saved and posted through the CP7 Nota route, 6,000) raised two CRITICAL `payroll_work_wrong_contractor` in
erp.run_v263a_payroll_integrity_checks(), because the checker resolved a line's contractor only through PRODUCTION and
REWORK sources (cp7_payroll_checks_bundle.py). Sol's case SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM
(audit/sol_cp17_r4/payroll_detector_dispute_cases.py) is used as written: the same fixture, the same resolved rows, the
same expected detector delta (none) and the same COUNTEREXAMPLE while the false alarm is there; the checker as it was
before R5-01 runs beside the installed one on the same books and must still count the two lines. Control: the checker
still counts a repair line whose wage belongs to another contractor and one whose wage is missing (the immutable-wage
guard is switched off only inside a rolled-back savepoint, labelled DETECTOR_CONTROL, like the CP17 legacy findings case).
"""
from decimal import Decimal
import cp6_bd_probe as bd
import cp7_nota_cases as nota
import cp7_nota_source_cases as sources
import cp7_payroll_checks_bundle as payroll_checks

NATIVE=['CP17_R5_01_VALID_FG_REPAIR_NOTA_ZERO_ALARM_SOL','CP17_R5_01_PAYROLL_CHECK_STILL_FINDS_WRONG_OR_MISSING_REPAIR']
RACES=[]
HTTP=[]
BROWSER=[]
FUNCTIONS=()
TARGET='run_v263a_payroll_integrity_checks:'+payroll_checks.CHECK
WAGE_GUARD='trg_guard_fg_unsourced_repair_wages_v1_immutable'


def detectors(cur):
    """Every Native detector identity and its count (cp6_bc_probe.DETECTORS, the set Sol counted: 167)."""
    out={}
    for function in bd.bcp.DETECTORS:
        bd.api.admin(cur);bd.chain.production.owner(cur)
        rows=cur.execute('select check_name,issue_count from erp.'+function+'()').fetchall()
        bd.api.admin(cur)
        for name,count in rows:
            key=function+':'+name;assert key not in out,('CP17_R5_DUPLICATE_DETECTOR',key);out[key]=int(count)
    return out


def delta(before,after):
    assert set(before)==set(after),('CP17_R5_DETECTOR_SET_CHANGED',sorted(set(before)^set(after)))
    return {k:after[k]-before[k] for k in before if after[k]!=before[k]}


def checker_before(cur):
    """Install, inside the caller's savepoint, the checker as it was before R5-01 under another name."""
    bd.api.admin(cur)
    installed=cur.execute('select pg_get_functiondef(%s::regprocedure)',(payroll_checks.SIGNATURE,)).fetchone()[0]
    old=payroll_checks.unpatched(installed)
    head='FUNCTION '+payroll_checks.SIGNATURE
    assert old.count(head)==1,'CP17_R5_01_CHECKER_HEAD_CHANGED'
    cur.execute('create schema cp17_r5_01')
    cur.execute(old.replace(head,'FUNCTION cp17_r5_01.checks_before()',1))
    def wrong():
        bd.api.admin(cur);bd.chain.production.owner(cur)
        n=cur.execute("select issue_count from cp17_r5_01.checks_before() where check_name=%s",(payroll_checks.CHECK,)).fetchone()[0]
        bd.api.admin(cur);return int(n)
    return wrong


def valid_nota(cur,today):
    """Sol's fixture: two Native repair wages (2 and 1 pcs at 2,000), then the public CP7 Nota SAVE and POST."""
    f=sources.repair(cur,today,qty=2)
    second=sources.ax.post(cur,sources.ax.repair_payload(f,1))
    bd.api.admin(cur)
    return f,second


def resolved_rows(cur,payroll_id):
    # Sol's resolution query, as written.
    return cur.execute("""select p.id::text,p.source_type,p.source_id::text,p.qty_payable::text,
      p.rate_snapshot::text,p.amount::text,ps.contractor_id::text,w.contractor_id::text,
      p.work_component_id::text,w.work_component_id::text,w.qty_pcs::text,w.rate_per_pcs::text,
      w.amount::text,w.status,r.status,w.receipt_id::text
      from erp.payroll_work_items p join erp.payroll_settlements ps on ps.id=p.payroll_id
      left join erp.fg_unsourced_repair_wages_v1 w on p.source_type='FG_REPAIR' and w.id=p.source_id
      left join erp.fg_unsourced_receipts_v1 r on r.id=w.receipt_id
      where p.payroll_id=%s order by w.qty_pcs,p.id""",(payroll_id,)).fetchall()


def cases(cur,today):

    # ---- R5-01: Sol's case, as written in audit/sol_cp17_r4/payroll_detector_dispute_cases.py (correct_repair).
    def sol_valid_repair_nota():
        o=dict(oracle_origin='SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM (PROMAX_INV_D02_HEALTHY_BOOK_ZERO)',
               fixture_origin='ACCEPTED_AX_NATIVE_REPAIR_QTY2_AND1_THEN_PUBLIC_CP7_NOTA_SAVE_POST',no_direct_fact_edit=True)
        before=detectors(cur)
        # The CP17 database carries the books of the cases before this one; Sol's oracle is the change this Nota makes.
        o['baseline_all_zero']=all(v==0 for v in before.values());o['detector_identities']=len(before)
        cur.execute('savepoint cp17_r5_01_sol')
        try:
            old=checker_before(cur);old_before=old()
            f,second=valid_nota(cur,today)
            o.update(contractor_id=str(f['contractor']),receipt_ids=[f['receipt'],second['receipt_id']])
            assert delta(before,detectors(cur))=={},'CP17_R5_01_REPAIR_SOURCES_RAISED_ALARMS'
            draft=nota.command(cur,'SAVE',nota.payload(cur,f,today))
            assert delta(before,detectors(cur))=={},'CP17_R5_01_DRAFT_RAISED_ALARMS'
            posted=nota.act(cur,'POST',draft);bd.api.admin(cur)
            header=cur.execute('select id::text,contractor_id::text,status,labor_total::text,net_payable::text from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()
            assert header[1]==str(f['contractor']) and header[2]=='CALCULATED' and Decimal(header[3])==Decimal(header[4])==6000,header
            rows=resolved_rows(cur,posted['payroll_id'])
            assert len(rows)==2 and [Decimal(r[3]) for r in rows]==[1,2],rows
            for row in rows:
                assert row[1]=='FG_REPAIR' and row[6]==row[7]==header[1]
                assert row[8]==row[9] and Decimal(row[3])==Decimal(row[10])
                assert Decimal(row[4])==Decimal(row[11])==2000
                assert Decimal(row[5])==Decimal(row[12])==Decimal(row[3])*2000
                assert row[13]==row[14]=='POSTED' and row[15] in o['receipt_ids']
            assert sum(Decimal(r[5]) for r in rows)==6000
            observed=delta(before,detectors(cur))
            old_after=old()
            o.update(payroll_header=header,observed_delta=observed,checker_before_r5_01=dict(before=old_before,after=old_after))
            # Before the fix the same books carry the two false alarms (Sol: 0 -> 2).
            assert old_after-old_before==2,('CP17_R5_01_OLD_CHECKER_DID_NOT_REPRODUCE',old_before,old_after)
            if observed=={}:
                o.update(status='PASS',false_alarm_reproduced=False,contract_satisfied=True)
            elif observed=={TARGET:2}:
                o.update(status='COUNTEREXAMPLE',false_alarm_reproduced=True,contract_satisfied=False)
            else:
                raise AssertionError(('CP17_R5_01_UNEXPECTED_ALARM_SET',observed))
        finally:
            cur.execute('rollback to savepoint cp17_r5_01_sol');cur.execute('release savepoint cp17_r5_01_sol');bd.api.admin(cur)
        assert detectors(cur)==before,'CP17_R5_01_DETECTORS_NOT_RESTORED'
        assert cur.execute("select count(*) from pg_namespace where nspname='cp17_r5_01'").fetchone()[0]==0
        o['full_restore']=True
        return o

    # ---- R5-01 control: real wrong-contractor and missing repair sources still count.
    def wrong_or_missing_still_found():
        cur.execute('savepoint cp17_r5_01_control')
        try:
            f,second=valid_nota(cur,today)
            posted=nota.act(cur,'POST',nota.command(cur,'SAVE',nota.payload(cur,f,today)));bd.api.admin(cur)
            wages=[r[2] for r in resolved_rows(cur,posted['payroll_id'])]
            assert len(wages)==2
            other=cur.execute('select id::text from erp.contractors where id<>%s order by id limit 1',(f['contractor'],)).fetchone()
            assert other,'CP17_R5_01_NO_OTHER_CONTRACTOR'
            valid=detectors(cur)
            def without_guard(sql,args):
                # DETECTOR_CONTROL: corrupt one immutable wage inside this savepoint only.
                bd.api.admin(cur);cur.execute('alter table erp.fg_unsourced_repair_wages_v1 disable trigger '+WAGE_GUARD)
                try:cur.execute(sql,args)
                finally:bd.api.admin(cur);cur.execute('alter table erp.fg_unsourced_repair_wages_v1 enable trigger '+WAGE_GUARD)
            without_guard('update erp.fg_unsourced_repair_wages_v1 set contractor_id=%s where id=%s',(other[0],wages[0]))
            moved=delta(valid,detectors(cur))
            without_guard('update erp.fg_unsourced_repair_wages_v1 set contractor_id=%s where id=%s',(f['contractor'],wages[0]))
            restored=delta(valid,detectors(cur))
            without_guard('delete from erp.fg_unsourced_repair_wages_v1 where id=%s',(wages[1],))
            missing=delta(valid,detectors(cur))
            # The target counts each corrupted line once; other detectors may notice the corruption too (recorded).
            assert moved.get(TARGET)==1 and restored=={} and missing.get(TARGET)==1,(moved,restored,missing)
            assert cur.execute("select tgenabled from pg_trigger where tgname=%s",(WAGE_GUARD,)).fetchone()[0]=='O'
        finally:
            cur.execute('rollback to savepoint cp17_r5_01_control');cur.execute('release savepoint cp17_r5_01_control');bd.api.admin(cur)
        return dict(status='PASS',wage_of_another_contractor_counted=moved,restored_wage_counts_nothing=True,
                    missing_wage_counted=missing,guard_switched_off_only_inside_rolled_back_savepoint=True)

    named=[sol_valid_repair_nota,wrong_or_missing_still_found]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):return []


def http_cases(http,today):return []
