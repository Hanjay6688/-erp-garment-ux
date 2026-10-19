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

R5-02 (owner D17-2, KNOWN-P19-DIRECT-LATENCY): in eleven STABLE report and check readers every literal
`erp.account_id('<KEY>')` became `(select erp.account_id('<KEY>'))`, evaluated once per query instead of once per journal
line (cp7_report_accounts_bundle.py). Native cases: each installed reader and the same reader without the change run side
by side on the CP17 books (every product, PO, pocket period, opening settlement and sale journal/PO pair the database
holds, and three report windows) and must give the same rows or the same refusal; the review fails for a reader whose
literal calls changed or that uses a key outside the listed core mappings; a core mapping cannot be deleted.
"""
from datetime import timedelta
from decimal import Decimal
import json
import psycopg
import cp6_bd_probe as bd
import cp7_nota_cases as nota
import cp7_nota_source_cases as sources
import cp7_payroll_checks_bundle as payroll_checks
import cp7_report_accounts_bundle as report_accounts

NATIVE=['CP17_R5_01_VALID_FG_REPAIR_NOTA_ZERO_ALARM_SOL','CP17_R5_01_PAYROLL_CHECK_STILL_FINDS_WRONG_OR_MISSING_REPAIR',
        'CP17_R5_02_REPORT_READERS_SAME_ANSWER','CP17_R5_02_REPORT_READERS_REVIEWED']
RACES=[]
HTTP=[]
BROWSER=[]
FUNCTIONS=()
TARGET='run_v263a_payroll_integrity_checks:'+payroll_checks.CHECK
OWNER_AUTH=str(bd.chain.production.base.OPERATOR_AUTH)
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
    # Called like the installed checker (owner context, role authenticated); the schema exists only inside the savepoint.
    cur.execute('grant usage on schema cp17_r5_01 to authenticated;grant execute on function cp17_r5_01.checks_before() to authenticated')
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

    # ---- R5-02: every changed reader against itself without the change, on the same books.
    def reader_inputs():
        bd.api.admin(cur)
        ids=lambda sql:[(r[0],) for r in cur.execute(sql).fetchall()]
        windows=[(today-timedelta(days=d),today,today) for d in (0,30,400)]
        return {
            'erp.bb_opening_credit_account_v1(uuid)':ids('select id from erp.opening_subledger_settlements order by id limit 300'),
            'erp.compute_non_po_product_hpp_book_v2620f(uuid)':ids('select id from erp.products order by id limit 300'),
            'erp.compute_po_hpp_gl_book_v2620e(uuid)':ids('select id from erp.production_orders order by id limit 300'),
            'erp.get_owner_financial_snapshot_v2(date,date,date)':windows,
            'erp.pocket_period_book_v1(uuid)':ids('select id from erp.pocket_periods order by id limit 300'),
            'erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)':[tuple(r) for r in cur.execute(
                "select distinct e.id,l.po_id from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id"
                " where e.source_type in('SALE','SALES_RETURN','JOURNAL_REVERSAL') and l.po_id is not null order by 1,2 limit 300").fetchall()]}
    def readers_same_answer():
        inputs=reader_inputs();report=report_accounts.verify(cur);compared={}
        cur.execute('savepoint cp17_r5_02_same')
        try:
            bd.api.admin(cur);cur.execute('create schema cp17_r5_02')
            for signature in report_accounts.READERS:
                name=signature.split('(')[0]
                installed=cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
                head='FUNCTION '+name+'('
                old=report_accounts.unwrap(signature,installed)
                assert old.count(head)==1,('CP17_R5_02_READER_HEAD_CHANGED',signature)
                cur.execute(old.replace(head,'FUNCTION cp17_r5_02.'+name.split('.')[1]+'(',1))
                args=inputs.get(signature,[()])
                def answer(fn,a):
                    # Both the installed reader and its copy run in one context: the database owner session (the
                    # internal readers are not granted to the browser role) with the owner's claims, so
                    # erp.require_owner_admin() and erp.require_internal() see the owner.
                    bd.api.admin(cur);cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=OWNER_AUTH,role='authenticated')),))
                    cur.execute('savepoint cp17_r5_02_call')
                    try:
                        rows=cur.execute('select to_jsonb(x)::text from '+fn+'('+','.join(['%s']*len(a))+') x',a).fetchall()
                        return ('ROWS',sorted(r[0] for r in rows))
                    except psycopg.Error as e:
                        cur.execute('rollback to savepoint cp17_r5_02_call');return ('ERR',e.sqlstate,str(e).split('\n')[0])
                    finally:
                        cur.execute('release savepoint cp17_r5_02_call');bd.api.admin(cur)
                differences=[]
                for a in args:
                    new,old_answer=answer(name,a),answer('cp17_r5_02.'+name.split('.')[1],a)
                    if new!=old_answer:differences.append((str(a),str(new)[:400],str(old_answer)[:400]))
                assert not differences,('CP17_R5_02_READER_ANSWER_CHANGED',signature,differences[:2])
                compared[signature]=len(args)
        finally:
            cur.execute('rollback to savepoint cp17_r5_02_same');cur.execute('release savepoint cp17_r5_02_same');bd.api.admin(cur)
        return dict(status='PASS',reviewed=report,inputs_compared=compared,same_rows_or_same_refusal=True)
    def readers_reviewed():
        bd.api.admin(cur);clean=report_accounts.verify(cur)
        signature='erp.run_v268_financial_report_checks()'
        installed=cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
        old=report_accounts.unwrap(signature,installed)
        refusals={}
        def refused(label,fn):
            try:fn()
            except AssertionError as e:refusals[label]=str(e.args[0][0] if isinstance(e.args[0],tuple) else e.args[0]);return
            raise AssertionError(('CP17_R5_02_REVIEW_ACCEPTED',label))
        # A reader that gained one more literal call, a key outside the core list, or text already wrapped is refused.
        refused('one_more_call',lambda:report_accounts.wrap(signature,old.replace("begin","begin perform erp.account_id('WIP');",1)))
        refused('unlisted_key',lambda:report_accounts.wrap(signature,old.replace("erp.account_id('WIP')","erp.account_id('LABOR_COST')",1)))
        refused('already_wrapped',lambda:report_accounts.wrap(signature,installed))
        # The install refuses a predecessor whose literal calls changed.
        cur.execute('savepoint cp17_r5_02_review')
        try:
            cur.execute(old.replace("begin","begin perform erp.account_id('WIP');",1))
            try:cur.execute(report_accounts.block(signature));raise AssertionError('CP17_R5_02_INSTALL_ACCEPTED_CHANGED_READER')
            except psycopg.errors.RaiseException as e:refusals['install_changed_reader']=str(e).split('\n')[0]
        finally:cur.execute('rollback to savepoint cp17_r5_02_review');cur.execute('release savepoint cp17_r5_02_review');bd.api.admin(cur)
        # Every key is a core mapping: deleting one is refused by the Native guard.
        cur.execute('savepoint cp17_r5_02_mapping')
        try:
            try:cur.execute("delete from erp.accounting_account_mappings where mapping_key='WIP'");raise AssertionError('CP17_R5_02_CORE_MAPPING_DELETED')
            except psycopg.errors.RaiseException as e:refusals['core_mapping_delete']=str(e).split('\n')[0]
        finally:cur.execute('rollback to savepoint cp17_r5_02_mapping');cur.execute('release savepoint cp17_r5_02_mapping');bd.api.admin(cur)
        assert len(refusals)==5,refusals
        return dict(status='PASS',reviewed=clean,refusals=refusals)

    named=[sol_valid_repair_nota,wrong_or_missing_still_found,readers_same_answer,readers_reviewed]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):return []


def http_cases(http,today):return []
