"""AW local smoke (PostgreSQL 16, not native PG17): the per-date close engine on the real table DDL.

Builds a scratch database from the table definitions in the repo catalog snapshot
(supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz), stubs the check functions and the two views
the engine reads, installs the AW definitions (engine, readiness, preflight, close, filing, laundry estimate,
facades) and runs the engine cases plus the close gate. Every case runs in a rolled-back transaction.
Usage: python3 scripts/cp6_aw_local_smoke.py "host=/tmp port=55432 user=postgres" OUT.json
"""
import gzip,json,re,sys,uuid
from datetime import date
from pathlib import Path
import psycopg

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cp6_aw_definitions as aw

ADMIN_URL=sys.argv[1];OUT=Path(sys.argv[2]);DB='cp6_aw_local_smoke'
DB_URL=ADMIN_URL+' dbname='+DB
TABLES=['cost_recalc_queue','material_stock_movements','cutting_groups','contractor_material_issue_items','contractor_material_issues',
 'fg_lots','journal_lines','journal_entries','production_orders','account_daily_balances','chart_accounts','fg_stock_movements',
 'contractors','contractor_workers','attendance_records','worker_employment_periods','payroll_settlements','payroll_attendance_items',
 'laundry_deliveries','laundry_delivery_lines','laundry_receipts','laundry_receipt_lines','accounting_period_control','audit_logs']
STUBS="create function erp._cp3_business_date(p timestamptz) returns date language sql immutable as $$select (p at time zone 'Asia/Jakarta')::date$$;\ncreate table erp._stub_accounts(mapping_key text primary key, account_id uuid not null);\ncreate function erp.account_id(p_mapping_key text) returns uuid language sql stable as $$select account_id from erp._stub_accounts where mapping_key=p_mapping_key$$;\ncreate table erp._stub_checks(src text, check_name text, severity text, issue_count bigint, details text);\ncreate function erp.run_v268_financial_report_checks() returns table(check_name text, severity text, issue_count bigint, details text) language sql as $$select check_name,severity,issue_count,details from erp._stub_checks where src='v268'$$;\ncreate function erp.run_v267_financial_truth_checks() returns table(check_name text, severity text, issue_count bigint, details text) language sql as $$select check_name,severity,issue_count,details from erp._stub_checks where src='v267'$$;\ncreate function erp.run_integrity_checks() returns table(check_name text, severity text, issue_count bigint, details text) language sql as $$select check_name,severity,issue_count,details from erp._stub_checks where src='integrity'$$;\ncreate table erp.v_payroll_eligible_work_lines(source_type text, source_id uuid, contractor_id uuid, po_id uuid, eligible_at timestamptz, remaining_qty numeric, remaining_amount numeric);\ncreate table erp.v_material_grni_aging(purchase_id uuid, physical_at timestamptz, grni_estimated_amount numeric);\ncreate table if not exists erp.materials(id uuid primary key default gen_random_uuid());\ncreate table if not exists erp._stub_checkpoint_calls(material_id uuid, through date);\ncreate or replace function erp.refresh_material_cost_checkpoint(p uuid, d date) returns void language sql as $$insert into erp._stub_checkpoint_calls values(p,d)$$;\ncreate or replace function erp.require_owner_admin() returns void language sql as $$select$$;\ncreate or replace function erp.current_app_user_id() returns uuid language sql as $$select null::uuid$$;\ncreate or replace function erp.sync_finished_po_wip_residual(uuid,date,text) returns void language sql as $$select$$;\n"


def build():
    boot=gzip.open(ROOT/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz','rt').read()
    ddl=['create schema erp;']
    ddl+=['create sequence %s;'%q for q in sorted(set(re.findall(r"nextval\('(erp\.[a-z_0-9]+)'",boot)))]
    for t in TABLES:
        m=re.search(r'create table "erp"\."%s" \((.*?)\n\);'%t,boot,re.S);assert m,t
        ddl.append('create table "erp"."%s" (%s\n);'%(t,m.group(1)))
        ddl+=re.findall(r'alter table only "erp"\."%s" add constraint "[^"]+" PRIMARY KEY \([^)]*\);'%t,boot)
    with psycopg.connect(ADMIN_URL+' dbname=postgres',autocommit=True) as c:
        c.execute('drop database if exists '+DB);c.execute('create database '+DB)
        for r in ('anon','authenticated','service_role'):
            if not c.execute('select 1 from pg_roles where rolname=%s',(r,)).fetchone():c.execute('create role '+r+' nologin')
    with psycopg.connect(DB_URL) as conn,conn.cursor() as cur:
        cur.execute('create extension if not exists pgcrypto')
        cur.execute('\n'.join(ddl),prepare=False)
        cur.execute(STUBS,prepare=False)
        cur.execute(aw.SCHEMA,prepare=False)
        for t in aw.NEW_FUNCTIONS.values():cur.execute(t,prepare=False)
        cur.execute(aw.FUNCTIONS[aw.CLOSE],prepare=False)
        for t in aw.PUBLIC_FUNCTIONS.values():cur.execute(t,prepare=False)
        cur.execute(aw.TRIGGERS,prepare=False)


URL=DB_URL
U=lambda:str(uuid.uuid4())
results=[]


def ready(cur,through,window_from=None):
    return cur.execute('select erp.period_readiness_v1(%s,%s)',(through,window_from)).fetchone()[0]


def codes(r):return sorted({b['code'] for b in r['blockers']})


def case(name,fn,expect):
    with psycopg.connect(URL) as conn,conn.cursor() as cur:
        try:
            observed=fn(cur)
            ok=all(observed.get(k)==v for k,v in expect.items())
            results.append(dict(case=name,status='PASS' if ok else 'FAIL',expected=expect,observed=observed))
        except Exception as exc:
            results.append(dict(case=name,status='ERROR',error=str(exc)))
        conn.rollback()


def accounts(cur):
    ids={k:U() for k in ('MATERIAL_INVENTORY','WIP','FG_INVENTORY')}
    for k,v in ids.items():cur.execute('insert into erp._stub_accounts values(%s,%s)',(k,v))
    return ids


def po(cur,number):
    pid=U();cur.execute('insert into erp.production_orders(id,po_number,model_id) values(%s,%s,%s)',(pid,number,U()));return pid


def lot(cur,po_id,at):
    cur.execute('insert into erp.fg_lots(lot_number,product_id,po_id,initial_qty_pcs,cached_qty_pcs,produced_at) values(%s,%s,%s,1,1,%s)',
                ('L'+U()[:8],U(),po_id,at))


def queue(cur,po_id,status='PENDING',attempts=0,recalc_from=None):
    cur.execute('insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason,status,attempt_count) values(%s,%s,%s,%s,%s,%s)',
                ('PO',po_id,recalc_from,'test',status,attempts))


D=date(2026,9,15)


def recost_in_period(cur):
    p=po(cur,'PO-IN');lot(cur,p,'2026-09-10 10:00+07');queue(cur,p,recalc_from='2026-09-20 10:00+07')
    r=ready(cur,D);b=r['blockers'][0]
    return dict(status=r['status'],codes=codes(r),facts=b['reference']['facts'],impact=b['impact_date'])


def recost_after_period(cur):
    p=po(cur,'PO-AFTER');lot(cur,p,'2026-09-20 10:00+07');queue(cur,p,recalc_from='2026-09-20 10:00+07')
    r=ready(cur,D);return dict(status=r['status'],codes=codes(r))


def recost_boundary(cur):
    # 23:30 Jakarta on D is inside D; 00:30 Jakarta on D+1 is outside.
    p=po(cur,'PO-EDGE');lot(cur,p,'2026-09-15 23:30+07');queue(cur,p)
    q=po(cur,'PO-EDGE2');lot(cur,q,'2026-09-16 00:30+07');queue(cur,q)
    r=ready(cur,D);return dict(status=r['status'],pos=sorted(b['reference']['po_number'] for b in r['blockers']))


def recost_exhausted(cur):
    p=po(cur,'PO-EX');lot(cur,p,'2026-09-10 10:00+07');queue(cur,p,'FAILED',3)
    r=ready(cur,D);return dict(status=r['status'],codes=codes(r),critical=r['critical_count'])


def integrity_current(cur):
    cur.execute("""insert into erp._stub_checks values('v268','V268_UNBALANCED_POSTED_JOURNAL','CRITICAL',1,'x'),
      ('v268','V268_COST_RECALC_EXHAUSTED','CRITICAL',1,'queue'),('v268','V268_COST_RECALC_PENDING','WARNING',2,'queue'),
      ('v267','V268_UNBALANCED_POSTED_JOURNAL','CRITICAL',1,'dup'),('integrity','STALE_RECOST_QUEUE','WARN',1,'q'),
      ('integrity','NEGATIVE_FG_BALANCE','ERROR',1,'neg'),('v267','AP_OPENING_RECEIPT_SOURCE_DRIFT','CRITICAL',0,'none')""")
    r=ready(cur,D);return dict(status=r['status'],codes=codes(r))


def gl_negative(cur,through):
    ids=accounts(cur)
    cur.execute('insert into erp.account_daily_balances(balance_date,account_id,debit_total,credit_total) values(%s,%s,0,50),(%s,%s,80,0)',
                ('2026-09-05',ids['WIP'],'2026-09-08',ids['WIP']))
    r=ready(cur,through);return dict(status=r['status'],codes=codes(r))


def fg_negative(cur,through):
    prod,loc=U(),U()
    cur.execute("""insert into erp.fg_stock_movements(product_id,location_id,movement_type,qty_signed,source_type,physical_at)
      values(%s,%s,'SALE',-5,'T','2026-09-05 10:00+07'),(%s,%s,'QC_IN',5,'T','2026-09-06 10:00+07'),
            (%s,%s,'QC_IN',3,'T','2026-09-07 10:00+07'),(%s,%s,'SALE',-3,'T','2026-09-07 10:00+07')""",(prod,loc)*4)
    r=ready(cur,through);return dict(status=r['status'],codes=codes(r))


def material_reversal(cur):
    mat,loc=U(),U();src=U()
    cur.execute("""insert into erp.material_stock_movements(id,material_id,location_id,movement_type,qty_signed,source_type,physical_at)
      values(%s,%s,%s,'ISSUE',-3,'T','2026-09-05 10:00+07')""",(src,mat,loc))
    cur.execute("""insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,physical_at,reversal_of_id)
      values(%s,%s,'ISSUE_REVERSAL',3,'T','2026-09-07 10:00+07',%s)""",(mat,loc,src))
    r1=ready(cur,D)
    cur.execute("""insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,physical_at)
      values(%s,%s,'ISSUE',-1,'T','2026-09-08 10:00+07')""",(mat,loc))
    r2=ready(cur,D);return dict(reversed_pair=r1['status'],real_negative=codes(r2))


def attendance(cur):
    c=U();w=U()
    cur.execute("insert into erp.contractors(id,contractor_code,contractor_name,attendance_required) values(%s,'C1','Mandor A',true)",(c,))
    cur.execute("insert into erp.contractor_workers(id,contractor_id,worker_name,pay_scheme) values(%s,%s,'Budi','DAILY')",(w,c))
    cur.execute("insert into erp.worker_employment_periods(worker_id,started_on,start_reason) values(%s,'2026-09-01','t')",(w,))
    for d,st,lc in (('2026-09-01','PRESENT',None),('2026-09-02','PRESENT','DRAFT'),('2026-09-03','OFF','POSTED')):
        cur.execute('insert into erp.attendance_records(contractor_id,worker_id,attendance_date,status,paid_fraction,record_lifecycle) values(%s,%s,%s,%s,%s,%s)',
                    (c,w,d,st,0 if st=='OFF' else 1,lc))
    r=ready(cur,date(2026,9,3),date(2026,9,1))
    b=[x for x in r['blockers'] if x['code']=='ATTENDANCE_CELL_MISSING']
    empty=ready(cur,date(2026,9,3),date(2026,9,4))  # empty window: X <= closed_through
    return dict(status=r['status'],missing=[x['reference']['sample_days'] for x in b],
                empty_window_attendance=[x['code'] for x in empty['blockers'] if x['family']=='ATTENDANCE'])


def payroll(cur):
    c=U();w=U()
    cur.execute("insert into erp.contractors(id,contractor_code,contractor_name,attendance_required) values(%s,'C2','Mandor B',true)",(c,))
    cur.execute("insert into erp.contractor_workers(id,contractor_id,worker_name,pay_scheme) values(%s,%s,'Sari','DAILY')",(w,c))
    due=U();straddle=U();rec1=U();rec2=U()
    cur.execute("insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status) values(%s,'PR-DUE',%s,'2026-09-01','2026-09-07','CALCULATED'),(%s,'PR-STRADDLE',%s,'2026-09-12','2026-09-18','DRAFT')",(due,c,straddle,c))
    cur.execute("insert into erp.attendance_records(id,contractor_id,worker_id,attendance_date,status,paid_fraction) values(%s,%s,%s,'2026-09-13','PRESENT',1),(%s,%s,%s,'2026-09-14','PRESENT',1)",(rec1,c,w,rec2,c,w))
    cur.execute("insert into erp.payroll_attendance_items(payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot) values(%s,%s,%s,1,100)",(straddle,w,rec1))
    cur.execute("insert into erp.v_payroll_eligible_work_lines(contractor_id,eligible_at,remaining_qty,remaining_amount) values(%s,'2026-09-10 10:00+07',5,50),(%s,'2026-09-20 10:00+07',7,70)",(c,c))
    r=ready(cur,D)
    by={}
    for b in r['blockers']:by.setdefault(b['code'],[]).append(b['reference'])
    return dict(status=r['status'],not_approved=[x['payroll_number'] for x in by.get('PAYROLL_NOT_APPROVED',[])],
                uncovered_attendance=[x['records'] for x in by.get('PAYROLL_ATTENDANCE_UNCOVERED',[])],
                uncovered_work=[x['remaining_qty'] for x in by.get('PAYROLL_WORK_UNCOVERED',[])])


def laundry(cur):
    p=po(cur,'PO-L');v=U()
    d1,d2,d3=U(),U(),U();l1,l2,l3=U(),U(),U()
    for d,st in ((d1,'SENT'),(d2,'SENT'),(d3,'DRAFT')):
        cur.execute("insert into erp.laundry_deliveries(id,delivery_number,po_id,vendor_id,target_dyeing_color,physical_at,status) values(%s,%s,%s,%s,'NAVY','2026-09-05 10:00+07',%s)",(d,'LD-'+d[:4],p,v,st))
    for l,d in ((l1,d1),(l2,d2),(l3,d3)):
        cur.execute('insert into erp.laundry_delivery_lines(id,delivery_id,cutting_group_id,qty_sent_pcs) values(%s,%s,%s,10)',(l,d,U()))
    r=U();cur.execute("insert into erp.laundry_receipts(id,receipt_number,delivery_id,physical_at,status) values(%s,'LR1',%s,'2026-09-06 10:00+07','POSTED')",(r,d1))
    cur.execute("insert into erp.laundry_receipt_lines(receipt_id,delivery_line_id,qty_good_received,qty_bs_laundry,actual_rate_snapshot,actual_cost_status,actual_cost) values(%s,%s,9,1,5,'ESTIMATED',50)",(r,l1))
    res=ready(cur,D)
    return dict(status=res['status'],unknown_lines=sorted(b['reference']['delivery_line_id']==l2 for b in res['blockers'] if b['code']=='LAUNDRY_PRICE_UNKNOWN'))


def grni_info(cur):
    cur.execute("insert into erp.v_material_grni_aging values(%s,'2026-09-05 10:00+07',120)",(U(),))
    r=ready(cur,D);return dict(status=r['status'],info=[b['code'] for b in r['info']])




# ---- GPT audit 757b79a regressions (P-01..P-04). Old cases above keep their expected values unchanged. ----

def fg_move(cur,prod,loc,qty,at,created,lot_id=None):
    cur.execute("""insert into erp.fg_stock_movements(product_id,lot_id,location_id,movement_type,qty_signed,source_type,physical_at,system_created_at)
      values(%s,%s,%s,%s,%s,'T',%s,%s)""",(prod,lot_id,loc,'IN' if qty>0 else 'OUT',qty,at,created))


def p04_fg_same_instant(cur,minus_first):
    prod,loc=U(),U()
    order=[(-1,'2026-09-05 10:00:01+07'),(1,'2026-09-05 10:00:02+07')] if minus_first else [(1,'2026-09-05 10:00:01+07'),(-1,'2026-09-05 10:00:02+07')]
    for q,created in order:fg_move(cur,prod,loc,q,'2026-09-05 10:00+07',created)
    r=ready(cur,D);return dict(status=r['status'],codes=codes(r))


def p04_fg_lot_level(cur):
    prod,loc,lot_a,lot_b=U(),U(),U(),U()
    fg_move(cur,prod,loc,5,'2026-09-05 10:00+07','2026-09-05 10:00+07',lot_b)
    fg_move(cur,prod,loc,-1,'2026-09-06 10:00+07','2026-09-06 10:00+07',lot_a)
    r=ready(cur,D);return dict(status=r['status'],levels=sorted(b['reference']['level'] for b in r['blockers']))


def p04_material_transfer_order(cur):
    """A transfer-in is ordered right after its transfer-out (cost engine rule), not by its own creation time."""
    mat,a,b,src=U(),U(),U(),U()
    rows=[(a,'OPENING',5,'OPENING_BALANCE_ITEM',U(),'2026-09-05 09:00+07','2026-09-05 09:00+07'),
          (a,'TRANSFER_OUT',-2,'MATERIAL_TRANSFER',src,'2026-09-05 10:00+07','2026-09-05 10:00:01+07'),
          (b,'ISSUE',-2,'T',U(),'2026-09-05 10:00+07','2026-09-05 10:00:02+07'),
          (b,'TRANSFER_IN',2,'MATERIAL_TRANSFER',src,'2026-09-05 10:00+07','2026-09-05 10:00:03+07')]
    for loc,mt,q,st,sid,at,created in rows:
        cur.execute("""insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,source_id,physical_at,system_created_at)
          values(%s,%s,%s,%s,%s,%s,%s,%s)""",(mat,loc,mt,q,st,sid,at,created))
    paired=ready(cur,D)
    cur.execute("delete from erp.material_stock_movements where movement_type='TRANSFER_IN'")
    cur.execute("""insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,source_id,physical_at,system_created_at)
      values(%s,%s,'ADJUST_IN',2,'T',%s,'2026-09-05 10:00+07','2026-09-05 10:00:03+07')""",(mat,b,U()))
    unpaired=ready(cur,D)
    return dict(paired=paired['status'],unpaired=codes(unpaired))


def p03_scoped(cur):
    """AW-04: an FG defect dated 20 September must not block 10 September; it blocks 20 September."""
    prod,loc=U(),U()
    fg_move(cur,prod,loc,-1,'2026-09-20 10:00+07','2026-09-20 10:00+07')
    cur.execute("insert into erp._stub_checks values('integrity','NEGATIVE_FG_BALANCE','ERROR',1,'neg')")
    early=ready(cur,date(2026,9,10));late=ready(cur,date(2026,9,20))
    info=[b for b in early['info'] if b['code']=='NEGATIVE_FG_BALANCE']
    return dict(early=early['status'],early_info_policy=[b['reference']['date_policy'] for b in info],
                late=late['status'],late_codes=codes(late))


def p03_unconfirmed_and_unknown(cur):
    cur.execute("insert into erp._stub_checks values('integrity','NEGATIVE_FG_BALANCE','ERROR',1,'neg'),('v268','V9999_NEW_CHECK','CRITICAL',2,'new')")
    r=ready(cur,date(2026,9,1))
    by={b['code']:b['reference'] for b in r['blockers']}
    return dict(status=r['status'],fg_class=by['NEGATIVE_FG_BALANCE']['class'],fg_confirmed=by['NEGATIVE_FG_BALANCE']['dated_detector_confirmed'],
                new_class=by['V9999_NEW_CHECK']['class'],new_policy=by['V9999_NEW_CHECK']['date_policy'])


def worker(cur,code,started):
    c=U();w=U()
    cur.execute("insert into erp.contractors(id,contractor_code,contractor_name,attendance_required) values(%s,%s,'Mandor',true)",(c,code))
    cur.execute("insert into erp.contractor_workers(id,contractor_id,worker_name,pay_scheme) values(%s,%s,'Budi','DAILY')",(w,c))
    cur.execute("insert into erp.worker_employment_periods(worker_id,started_on,start_reason) values(%s,%s,'t')",(w,started))
    return c,w


def off(cur,c,w,day,lifecycle='POSTED'):
    rid=U()
    cur.execute("insert into erp.attendance_records(id,contractor_id,worker_id,attendance_date,status,paid_fraction,record_lifecycle) values(%s,%s,%s,%s,'OFF',0,%s)",(rid,c,w,day,lifecycle))
    return rid


def completeness(cur,through):
    return cur.execute('select erp.period_readiness_v1(%s,erp.period_completeness_from_v1())',(through,)).fetchone()[0]


def p01_reverse_after_close(cur):
    """AW-01: OFF on 10 Sept, close 10 Sept, reverse it, then the report for 10 Sept and close 11 Sept must block."""
    cur.execute("insert into erp.accounting_period_control(singleton_id,closed_through) values(1,'2026-09-09')")
    c,w=worker(cur,'P01','2026-09-10')
    rid=off(cur,c,w,'2026-09-10')
    filed=cur.execute("select public.erp_close_accounting_through_v1('2026-09-10','p01')").fetchone()[0]
    cur.execute("update erp.attendance_records set record_lifecycle='REVERSED' where id=%s",(rid,))
    off(cur,c,w,'2026-09-11')
    report10=completeness(cur,date(2026,9,10))
    pre11=cur.execute("select erp.accounting_close_preflight_v1('2026-09-11')").fetchone()[0]
    cur.execute('savepoint g')
    try:cur.execute("select erp.close_accounting_through('2026-09-11','p01 blocked')");refusal=None
    except psycopg.Error as exc:refusal=str(exc).split(':')[0]
    cur.execute('rollback to savepoint g')
    off(cur,c,w,'2026-09-10')
    after_fix=cur.execute("select erp.accounting_close_preflight_v1('2026-09-11')->>'status'").fetchone()[0]
    filings=cur.execute('select count(*),min(readiness->>\'status\') from erp.accounting_close_filings_v1').fetchone()
    return dict(filed=filed['readiness']['status'],report10=report10['status'],
                report10_missing=[b['reference']['first_missing'] for b in report10['blockers'] if b['code']=='ATTENDANCE_CELL_MISSING'],
                pre11=pre11['status'],refusal=refusal,after_fix=after_fix,filings=[filings[0],filings[1]])


def p01_pre_engine_lost_cell(cur):
    """Before the engine's first date only a cell that lost its posted record is reported; never-recorded legacy days are not."""
    cur.execute("insert into erp.accounting_period_control(singleton_id,closed_through) values(1,'2026-09-09')")
    c,w=worker(cur,'P01B','2026-09-01')
    rid=off(cur,c,w,'2026-09-05','REVERSED')
    for d in range(10,16):off(cur,c,w,'2026-09-%02d'%d)
    lost=completeness(cur,D)
    off(cur,c,w,'2026-09-05')
    fixed=completeness(cur,D)
    return dict(lost=lost['status'],lost_codes=codes(lost),lost_days=[b['reference']['sample_days'] for b in lost['blockers']],fixed=fixed['status'])


def p01_completeness_from(cur):
    f=lambda:str(cur.execute('select erp.period_completeness_from_v1()').fetchone()[0])
    cur.execute("insert into erp.accounting_period_control(singleton_id,closed_through) values(1,null)")
    never=f()
    cur.execute("update erp.accounting_period_control set closed_through='2026-09-09'")
    no_filing=f()
    cur.execute("insert into erp.accounting_close_filings_v1(closed_through,previous_closed_through,reason,readiness,gl_balances) values('2026-09-15','2026-09-09','t','{\"status\":\"READY\"}','{}')")
    cur.execute("update erp.accounting_period_control set closed_through='2026-09-15'")
    engine=f()
    cur.execute("update erp.accounting_period_control set closed_through='2026-09-05'")
    reopened=f()
    return dict(never=never,no_filing=no_filing,engine=engine,reopened=reopened)


def p02_estimate_nonfinite(cur):
    p=po(cur,'PO-P02');d=U();l=U()
    cur.execute("insert into erp.laundry_deliveries(id,delivery_number,po_id,vendor_id,target_dyeing_color,physical_at,status) values(%s,'LD-P02',%s,%s,'NAVY','2026-09-05 10:00+07','SENT')",(d,p,U()))
    cur.execute('insert into erp.laundry_delivery_lines(id,delivery_id,cutting_group_id,qty_sent_pcs) values(%s,%s,%s,10)',(l,d,U()))
    refused={}
    for v in ('NaN','Infinity','-Infinity','-1','1.005','10000000000000000'):
        cur.execute('savepoint g')
        try:cur.execute('select erp.set_laundry_rate_owner_estimate_v1(%s,%s::numeric,%s)',(l,v,'t'));refused[v]='ACCEPTED'
        except psycopg.Error as exc:refused[v]='LAUNDRY_ESTIMATE_RATE_INVALID' in str(exc)
        cur.execute('rollback to savepoint g')
    residue=cur.execute('select (select count(*) from erp.laundry_rate_owner_estimates_v1),(select estimated_rate_snapshot from erp.laundry_delivery_lines where id=%s)',(l,)).fetchone()
    blocked=ready(cur,D)['status']
    cur.execute('savepoint g')
    try:cur.execute("insert into erp.laundry_rate_owner_estimates_v1(delivery_line_id,rate_per_pcs,reason) values(%s,'NaN','t')",(l,));table='ACCEPTED'
    except psycopg.Error as exc:table=type(exc).__name__
    cur.execute('rollback to savepoint g')
    cur.execute('select erp.set_laundry_rate_owner_estimate_v1(%s,12.50,%s)',(l,'owner estimate'))
    return dict(refused=refused,estimates=residue[0],rate=residue[1],blocked=blocked,table_nan=table,after_valid=ready(cur,D)['status'])


def p02_engine_rate_invalid(cur):
    p=po(cur,'PO-P02B');d=U()
    cur.execute("insert into erp.laundry_deliveries(id,delivery_number,po_id,vendor_id,target_dyeing_color,physical_at,status) values(%s,'LD-P02B',%s,%s,'NAVY','2026-09-05 10:00+07','SENT')",(d,p,U()))
    for rate in ('NaN','-1'):
        cur.execute('insert into erp.laundry_delivery_lines(delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot) values(%s,%s,10,%s::numeric)',(d,U(),rate))
    r=ready(cur,D)
    return dict(status=r['status'],invalid=sorted(b['reference']['rate'] for b in r['blockers'] if b['code']=='LAUNDRY_PRICE_INVALID'),
                unknown=[b for b in r['blockers'] if b['code']=='LAUNDRY_PRICE_UNKNOWN'])


def p03_material_per_key(cur):
    """A reversal that does not mirror its original leaves a negative total the effective history does not see:
    the current-state check must then block every date instead of being scoped (per-key confirmation)."""
    mat,loc,src=U(),U(),U()
    cur.execute("""insert into erp.material_stock_movements(id,material_id,location_id,movement_type,qty_signed,source_type,physical_at)
      values(%s,%s,%s,'ISSUE',-3,'T','2026-09-05 10:00+07')""",(src,mat,loc))
    cur.execute("""insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,physical_at,reversal_of_id)
      values(%s,%s,'ISSUE_REVERSAL',2,'T','2026-09-06 10:00+07',%s)""",(mat,loc,src))
    cur.execute("insert into erp._stub_checks values('integrity','NEGATIVE_MATERIAL_LOCATION_BALANCE','ERROR',1,'neg')")
    unmirrored=ready(cur,date(2026,9,1))
    b=[x for x in unmirrored['blockers'] if x['code']=='NEGATIVE_MATERIAL_LOCATION_BALANCE']
    return dict(status=unmirrored['status'],confirmed=[x['reference']['dated_detector_confirmed'] for x in b],
                policy=[x['reference']['date_policy'] for x in b])


def p03_material_scoped(cur):
    mat,loc=U(),U()
    cur.execute("""insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,physical_at)
      values(%s,%s,'ISSUE',-1,'T','2026-09-20 10:00+07')""",(mat,loc))
    cur.execute("insert into erp._stub_checks values('integrity','NEGATIVE_MATERIAL_LOCATION_BALANCE','ERROR',1,'neg')")
    early=ready(cur,date(2026,9,10));late=ready(cur,date(2026,9,20))
    return dict(early=early['status'],early_info=[b['code'] for b in early['info'] if b['family']=='INTEGRITY'],
                late=late['status'],late_codes=codes(late))


def recost_unscoped_po(cur):
    p=po(cur,'PO-NOFACT');queue(cur,p)
    r=ready(cur,date(2026,9,1));return dict(status=r['status'],codes=codes(r),scope=[b['scope'] for b in r['blockers']])


def registry_complete(cur):
    rows=cur.execute('select check_class,count(*) from erp.period_integrity_check_registry_v1() group by 1 order by 1').fetchall()
    return dict(classes={k:v for k,v in rows},total=sum(v for _,v in rows))


AUDIT_CASES=[
    ('P04_FG_SAME_INSTANT_MINUS_FIRST',lambda c:p04_fg_same_instant(c,True),dict(status='BLOCKED',codes=['FG_QTY_NEGATIVE_ASOF'])),
    ('P04_FG_SAME_INSTANT_PLUS_FIRST_CONTROL',lambda c:p04_fg_same_instant(c,False),dict(status='READY',codes=[])),
    ('P04_FG_LOT_LEVEL',p04_fg_lot_level,dict(status='BLOCKED',levels=['LOT'])),
    ('P04_MATERIAL_TRANSFER_ORDER',p04_material_transfer_order,dict(paired='READY',unpaired=['MATERIAL_QTY_NEGATIVE_ASOF'])),
    ('P03_DATED_EQUIVALENT_SCOPED',p03_scoped,dict(early='READY',early_info_policy=['SCOPED_BY_DATED_DETECTOR'],late='BLOCKED',late_codes=['FG_QTY_NEGATIVE_ASOF'])),
    ('P03_UNCONFIRMED_AND_UNKNOWN_BLOCK',p03_unconfirmed_and_unknown,dict(status='BLOCKED',fg_class='DATED_EQUIVALENT',fg_confirmed=False,new_class='UNCLASSIFIED',new_policy='BLOCKS_EVERY_DATE')),
    ('P01_REVERSE_AFTER_CLOSE',p01_reverse_after_close,dict(filed='READY',report10='BLOCKED',report10_missing=['2026-09-10'],pre11='BLOCKED',refusal='CLOSE_BLOCKED',after_fix='READY',filings=[1,'READY'])),
    ('P01_PRE_ENGINE_LOST_CELL',p01_pre_engine_lost_cell,dict(lost='BLOCKED',lost_codes=['ATTENDANCE_CELL_REVERSED_UNREPLACED'],lost_days=[['2026-09-05']],fixed='READY')),
    ('P01_COMPLETENESS_FROM',p01_completeness_from,dict(never='None',no_filing='2026-09-10',engine='2026-09-10',reopened='2026-09-06')),
    ('P02_ESTIMATE_NONFINITE',p02_estimate_nonfinite,dict(refused={'NaN':True,'Infinity':True,'-Infinity':True,'-1':True,'1.005':True,'10000000000000000':True},estimates=0,rate=None,blocked='BLOCKED',table_nan='CheckViolation',after_valid='READY')),
    ('P02_ENGINE_RATE_INVALID',p02_engine_rate_invalid,dict(status='BLOCKED',invalid=['-1.00','NaN'],unknown=[])),
    ('P03_MATERIAL_UNMIRRORED_REVERSAL_BLOCKS',p03_material_per_key,dict(status='BLOCKED',confirmed=[False],policy=['BLOCKS_EVERY_DATE'])),
    ('P03_MATERIAL_SCOPED',p03_material_scoped,dict(early='READY',early_info=['NEGATIVE_MATERIAL_LOCATION_BALANCE'],late='BLOCKED',late_codes=['MATERIAL_QTY_NEGATIVE_ASOF'])),
    ('RECOST_UNSCOPED_PO_BLOCKS_EVERY_DATE',recost_unscoped_po,dict(status='RECALC_PENDING',codes=['RECOST_UNSCOPED_ENTITY'],scope=['CURRENT_STATE'])),
    ('P03_REGISTRY_COMPLETE',registry_complete,dict(classes={'DATABLE':94,'DATED_EQUIVALENT':2,'QUEUE_FAMILY':1,'SYSTEMIC':9,'UNCERTAIN':2},total=108)),
]


CASES=[
    ('RECOST_IN_PERIOD',recost_in_period,dict(status='RECALC_PENDING',codes=['RECOST_PENDING'],facts=['FG_LOT'],impact='2026-09-10')),
    ('RECOST_AFTER_PERIOD',recost_after_period,dict(status='READY',codes=[])),
    ('RECOST_JAKARTA_BOUNDARY',recost_boundary,dict(status='RECALC_PENDING',pos=['PO-EDGE'])),
    ('RECOST_EXHAUSTED',recost_exhausted,dict(status='BLOCKED',codes=['RECOST_FAILED_EXHAUSTED'],critical=1)),
    ('INTEGRITY_CURRENT',integrity_current,dict(status='BLOCKED',codes=['NEGATIVE_FG_BALANCE','V268_UNBALANCED_POSTED_JOURNAL'])),
    ('GL_NEGATIVE_HISTORICAL_TODAY_CLEAN',lambda c:gl_negative(c,D),dict(status='BLOCKED',codes=['GL_INVENTORY_NEGATIVE_ASOF'])),
    ('GL_NEGATIVE_AFTER_DATE_CONTROL',lambda c:gl_negative(c,date(2026,9,4)),dict(status='READY',codes=[])),
    ('FG_NEGATIVE_HISTORICAL',lambda c:fg_negative(c,D),dict(status='BLOCKED',codes=['FG_QTY_NEGATIVE_ASOF'])),
    ('FG_NEGATIVE_AFTER_DATE_CONTROL',lambda c:fg_negative(c,date(2026,9,4)),dict(status='READY',codes=[])),
    ('MATERIAL_REVERSED_PAIR',material_reversal,dict(reversed_pair='READY',real_negative=['MATERIAL_QTY_NEGATIVE_ASOF'])),
    ('ATTENDANCE_CELLS',attendance,dict(status='BLOCKED',missing=[['2026-09-02']],empty_window_attendance=[])),
    ('PAYROLL_POLICY',payroll,dict(status='BLOCKED',not_approved=['PR-DUE'],uncovered_attendance=[1],uncovered_work=[5])),
    ('LAUNDRY_UNKNOWN',laundry,dict(status='BLOCKED',unknown_lines=[True])),
    ('GRNI_INFO_ONLY',grni_info,dict(status='READY',info=['GRNI_ESTIMATE_OPEN'])),
]


def close_gate(cur):
    """READY close through the facade files a snapshot; a period-touching recost refuses close atomically."""
    cur.execute("insert into erp.accounting_period_control(singleton_id,closed_through) values(1,'2026-08-31')")
    cur.execute('insert into erp.materials default values')
    ready_status=cur.execute("select erp.accounting_close_preflight_v1('2026-09-10')->>'status'").fetchone()[0]
    filed=cur.execute("select public.erp_close_accounting_through_v1('2026-09-10','smoke')").fetchone()[0]
    immutable=[]
    for sql in ("update erp.accounting_close_filings_v1 set reason='x'",'delete from erp.accounting_close_filings_v1','truncate erp.accounting_close_filings_v1'):
        cur.execute('savepoint g')
        try:cur.execute(sql);immutable.append('ACCEPTED')
        except psycopg.Error as exc:immutable.append('CLOSE_FILING_IMMUTABLE' in str(exc))
        cur.execute('rollback to savepoint g')
    p=po(cur,'PO-GATE');lot(cur,p,'2026-09-12 10:00+07');queue(cur,p)
    blocked_status=cur.execute("select erp.accounting_close_preflight_v1('2026-09-15')->>'status'").fetchone()[0]
    cur.execute('savepoint g')
    try:cur.execute("select erp.close_accounting_through('2026-09-15','smoke blocked')");refusal=None
    except psycopg.Error as exc:refusal=str(exc).split('\n')[0]
    cur.execute('rollback to savepoint g')
    after=cur.execute('select closed_through,(select count(*) from erp.accounting_close_filings_v1) from erp.accounting_period_control').fetchone()
    before_lot=cur.execute("select erp.accounting_close_preflight_v1('2026-09-11')->>'status'").fetchone()[0]
    return dict(ready_status=ready_status,filed_through=filed['closed_through'],filed_status=filed['readiness']['status'],
                immutable=immutable,blocked_status=blocked_status,refusal_code=(refusal or '').split(':')[0],
                closed_through_after=str(after[0]),filings_after=after[1],before_lot_status=before_lot)


if __name__=='__main__':
    build()
    for name,fn,expect in CASES+AUDIT_CASES:case(name,fn,expect)
    case('CLOSE_GATE',close_gate,dict(ready_status='READY',filed_through='2026-09-10',filed_status='READY',immutable=[True,True,True],
         blocked_status='RECALC_PENDING',refusal_code='CLOSE_BLOCKED',closed_through_after='2026-09-10',filings_after=1,before_lot_status='READY'))
    with psycopg.connect(ADMIN_URL+' dbname=postgres',autocommit=True) as c:
        ver=c.execute('show server_version').fetchone()[0];c.execute('drop database if exists '+DB)
    report=dict(label='LOCAL_PG16_SMOKE',native=False,server_version=ver,definitions_sha256=__import__('hashlib').sha256((ROOT/'scripts/cp6_aw_definitions.py').read_bytes()).hexdigest(),
                engine_sha256=__import__('hashlib').sha256((ROOT/'scripts/cp6_aw_engine.sql').read_bytes()).hexdigest(),
                registry_sha256=__import__('hashlib').sha256((ROOT/'scripts/cp6_aw_integrity_registry.sql').read_bytes()).hexdigest(),
                stubs='run_v268/run_v267/run_integrity_checks, v_payroll_eligible_work_lines, v_material_grni_aging, account_id, require_owner_admin, refresh_material_cost_checkpoint and sync_finished_po_wip_residual are stubs',
                counts={s:sum(r['status']==s for r in results) for s in ('PASS','FAIL','ERROR')},cases=results)
    OUT.write_text(json.dumps(report,indent=1,default=str)+'\n')
    for r in results:print(r['status'],r['case'],'' if r['status']=='PASS' else json.dumps({k:r.get(k) for k in ('observed','error')},default=str)[:600])
    assert report['counts']['PASS']==len(results),report['counts']
