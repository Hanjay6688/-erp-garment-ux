"""Link only the new positive-rate race work through Native payroll before READY."""
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import json,uuid
import cp6_aw_probe as aw

CONTRACTOR='a1000000-0000-0000-0000-000000000001'


def fingerprint(rows):
    return sha256(json.dumps(rows,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()


def complete(cur,as_of,completions):
    session_query="select current_user,session_user,coalesce(current_setting('request.jwt.claims',true),''),current_setting('TimeZone')"
    caller=cur.execute(session_query).fetchone()
    assert caller[:2]==('supabase_admin','supabase_admin'),'ORIGINAL_OBSERVER_IDENTITY_REQUIRED'
    aw.api.admin(cur)
    current=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    period=current-timedelta(days=3)
    assert period<=as_of<=current,'RACE_PAYROLL_MUST_PRECEDE_REPORT_AS_OF'
    rows=cur.execute("""select e.source_type,e.source_id::text,e.contractor_id::text,
        (e.eligible_at at time zone 'Asia/Jakarta')::date,e.remaining_qty,e.rate_snapshot,e.remaining_amount,
        w.completion_id::text,w.qty_payable,w.rate_snapshot,w.amount_payable,h.status
        from erp.v_payroll_eligible_work_lines e
        left join erp.work_completion_lines w on w.id=e.source_id and e.source_type='PRODUCTION'
        left join erp.work_completion_events h on h.id=w.completion_id
        where e.remaining_qty>0 order by e.source_id""").fetchall()
    assert len(rows)==1,('ONLY_ONE_NEW_RACE_WORK_LINE_EXPECTED',rows)
    kind,source,contractor,day,qty,rate,amount,completion,source_qty,source_rate,source_amount,status=rows[0]
    assert kind=='PRODUCTION'and contractor==CONTRACTOR and completion in {str(x)for x in completions},rows
    assert status=='POSTED'and day<=period and rate==source_rate==Decimal('1.25'),rows
    assert qty==source_qty and qty==9 and amount==source_amount==qty*rate and amount>0,rows
    overlap=cur.execute("select id::text,period_start,period_end,status from erp.payroll_settlements where contractor_id=%s and status<>'REVERSED'and period_start<=%s and period_end>=%s order by id",(contractor,period,period)).fetchall()
    assert not overlap,('EXPLICIT_RACE_PAYROLL_PERIOD_OCCUPIED',overlap)
    # Preserve all original work lineage, money, stock, HPP and payroll history.
    tables=('work_completion_events','work_completion_lines','po_work_component_snapshots',
        'journal_entries','journal_lines','fg_stock_movements','wip_stage_events','attendance_hpp_pools',
        'payroll_settlements','payroll_work_items','payroll_attendance_items','payroll_deductions','payroll_reimbursements')
    before={t:cur.execute('select id::text,to_jsonb(t)from erp.'+t+' t order by id').fetchall()for t in tables}
    cash=cur.execute('select id from erp.cash_accounts where is_active order by id limit 1').fetchone()[0]
    pid=uuid.uuid4()
    cur.execute("""insert into erp.payroll_settlements(id,payroll_number,contractor_id,
        period_start,period_end,status,payment_cash_account_id,payment_date,manual_adjustment,notes)
        values(%s,%s,%s,%s,%s,'DRAFT',%s,%s,0,'Explicit Native linkage of new work after committed race')""",
        (pid,'RACE9-'+pid.hex,contractor,period,period,cash,period))
    aw.chain.prior.as_owner(cur)
    populated=cur.execute('select erp.populate_payroll_draft(%s)',(pid,)).fetchone()[0]
    approved=cur.execute('select erp.approve_payroll(%s)',(pid,)).fetchone()[0]
    aw.api.admin(cur)
    header=cur.execute('select to_jsonb(p)from erp.payroll_settlements p where id=%s',(pid,)).fetchone()[0]
    assert header['status']=='APPROVED'and Decimal(str(header['net_payable']))==amount,header
    links=cur.execute('select to_jsonb(w)from erp.payroll_work_items w where payroll_id=%s order by id',(pid,)).fetchall()
    assert len(links)==1 and str(links[0][0]['source_id'])==source,links
    assert Decimal(str(links[0][0]['qty_payable']))==qty and Decimal(str(links[0][0]['rate_snapshot']))==rate,links
    assert cur.execute('select count(*)from erp.v_payroll_eligible_work_lines where remaining_qty>0').fetchone()==(0,)
    for table in tables:
        condition='where id<>%s'if table=='payroll_settlements'else'where payroll_id<>%s'if table.startswith('payroll_')else''
        after=cur.execute('select id::text,to_jsonb(t)from erp.'+table+' t '+condition+' order by id',(pid,)if condition else()).fetchall()
        assert after==before[table],('ORIGINAL_RACE_SOURCE_CHANGED_BY_PAYROLL_LINK',table)
    for table in('payroll_attendance_items','payroll_deductions','payroll_reimbursements'):
        assert cur.execute('select count(*)from erp.'+table+' where payroll_id=%s',(pid,)).fetchone()==(0,),table
    cur.execute("select set_config('request.jwt.claims',%s,true)",(caller[2],))
    assert cur.execute(session_query).fetchone()==caller,'RACE_OBSERVER_SESSION_CHANGED'
    return dict(caller_observer_identity_claims_timezone_restored=True,actual_eligible_source=rows,payroll_header=header,work_links=links,
        populate_receipt=populated,approve_receipt=approved,period_date=str(period),report_as_of=str(as_of),
        preserved_table_fingerprints={t:fingerprint(v)for t,v in before.items()},
        source_dates_quantities_rates_amounts_exact=True,all_original_work_lineage_rows_exact=True,
        all_GL_rows_and_stock_movements_exact=True,all_existing_payroll_and_HPP_pools_exact=True,
        no_payment_or_extra_cost_recognition=True,known_positive_source_rate_preserved=True,
        Native_period_overlap_guard_unchanged=True,UNKNOWN_never_zero=True)
