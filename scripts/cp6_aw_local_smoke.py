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
    for name,fn,expect in CASES:case(name,fn,expect)
    case('CLOSE_GATE',close_gate,dict(ready_status='READY',filed_through='2026-09-10',filed_status='READY',immutable=[True,True,True],
         blocked_status='RECALC_PENDING',refusal_code='CLOSE_BLOCKED',closed_through_after='2026-09-10',filings_after=1,before_lot_status='READY'))
    with psycopg.connect(ADMIN_URL+' dbname=postgres',autocommit=True) as c:
        ver=c.execute('show server_version').fetchone()[0];c.execute('drop database if exists '+DB)
    report=dict(label='LOCAL_PG16_SMOKE',native=False,server_version=ver,definitions_sha256=__import__('hashlib').sha256((ROOT/'scripts/cp6_aw_definitions.py').read_bytes()).hexdigest(),
                engine_sha256=__import__('hashlib').sha256((ROOT/'scripts/cp6_aw_engine.sql').read_bytes()).hexdigest(),
                stubs='run_v268/run_v267/run_integrity_checks, v_payroll_eligible_work_lines, v_material_grni_aging, account_id, require_owner_admin, refresh_material_cost_checkpoint and sync_finished_po_wip_residual are stubs',
                counts={s:sum(r['status']==s for r in results) for s in ('PASS','FAIL','ERROR')},cases=results)
    OUT.write_text(json.dumps(report,indent=1,default=str)+'\n')
    for r in results:print(r['status'],r['case'],'' if r['status']=='PASS' else json.dumps({k:r.get(k) for k in ('observed','error')},default=str)[:600])
    assert report['counts']['PASS']==len(results),report['counts']
