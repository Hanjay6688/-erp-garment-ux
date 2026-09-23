"""Local PG16 smoke of AV rev2 helper/guard/trigger on a synthetic catalog. NOT native qualification."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import psycopg
import cp6_av_definitions as d
# Disposable local server only; the script creates and drops its own database.
DB=os.environ.get('CP6_AV_SMOKE_DSN','host=/tmp port=55432 user=postgres dbname=postgres')
report=dict(scope='Local PostgreSQL 16 synthetic catalog; exact AV rev2 helper/guard/trigger text; NOT native Supabase',cases=[])
with psycopg.connect(DB,autocommit=True) as c:
    c.execute('drop database if exists av2smoke');c.execute('create database av2smoke')
with psycopg.connect(DB.replace('dbname=postgres','dbname=av2smoke')) as conn,conn.cursor() as cur:
    report['engine']=cur.execute('select version()').fetchone()[0]
    cur.execute("create role anon;create role authenticated;create role service_role;" if not cur.execute("select 1 from pg_roles where rolname='anon'").fetchone() else 'select 1')
    cur.execute("""create schema erp;
      create table erp.products(id uuid primary key,supersedes_product_id uuid references erp.products,identity_root_id uuid);
      create table erp.fg_lots(id uuid primary key default gen_random_uuid(),product_id uuid references erp.products,produced_at timestamptz,lot_origin text);
      create table erp.bs_cases(id uuid primary key default gen_random_uuid(),product_id uuid references erp.products,physical_at timestamptz,qc_item_id uuid,source_laundry_bs_allocation_id uuid,untracked_type text);
      create table erp.rework_orders(id uuid primary key default gen_random_uuid(),good_fg_lot_id uuid references erp.fg_lots);
      create table erp.product_identity_mutation_context_v1(product_id uuid);
      create function erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamptz,text) returns uuid language plpgsql as $$begin perform erp.latest_new_stock_physical_at_v1($1);return $1;end$$;
      create function erp.assert_product_identity_time(uuid,timestamptz,text default 'NEW_STOCK') returns void language sql as $$select$$;""")
    for key in d.REGISTRY:
        s,t,col=key.split('.')
        if t in ('bs_cases','fg_lots','product_identity_mutation_context_v1'):continue
        cur.execute(f"create table if not exists erp.{t}(id uuid default gen_random_uuid())")
        cur.execute(f"alter table erp.{t} add column {col} uuid references erp.products")
    cur.execute(d.SCHEMA,prepare=False)
    for text in d.NEW_FUNCTIONS.values():cur.execute(text,prepare=False)
    cur.execute(d.TRIGGERS,prepare=False)
    for ident,text in d.NEW_FUNCTIONS.items():
        canon=cur.execute('select pg_get_functiondef(%s::regprocedure)',(ident,)).fetchone()[0]
        report.setdefault('canonical_pg16_matches',{})[ident]=canon==text
    def guard():
        cur.execute('savepoint g')
        try:r=cur.execute('select erp.assert_new_stock_cutoff_coverage_v1()').fetchone()[0];cur.execute('release savepoint g');return r,None
        except psycopg.Error as e:cur.execute('rollback to savepoint g');return None,str(e).splitlines()[0]
    r,e=guard();report['baseline_guard']=dict(error=e,references=(r or {}).get('references'),facts=(r or {}).get('new_stock_fact_tables'))
    def variant(name,sql,expect):
        cur.execute('savepoint v')
        try:
            cur.execute(sql,prepare=False);r,e=guard()
            refused=e is not None
            report['cases'].append(dict(name=name,expected=expect,refused=refused,error=e,status='PASS' if (refused==(expect=='REFUSE') and (e is None or expect!='REFUSE' or any(x in e for x in ('UNCLASSIFIED','STALE','DRIFT')))) else 'FAIL'))
        finally:cur.execute('rollback to savepoint v')
    fact="create table erp.probe_physical_facts(product_id uuid references erp.products,physical_at timestamptz);"
    producer=lambda body,sp="set search_path=erp,pg_catalog":fact+f"create function erp.probe_producer(p uuid,m text) returns void language plpgsql {sp} as $f$begin {body} end$f$;"
    variant('GPT lowercase NEW_STOCK',producer("perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into erp.probe_physical_facts values(p,clock_timestamp());"),'REFUSE')
    variant('GPT uppercase PERFORM/INSERT',producer("PERFORM ERP.ASSERT_PRODUCT_IDENTITY_TIME(p,clock_timestamp(),'NEW_STOCK'); INSERT INTO erp.probe_physical_facts VALUES(p,clock_timestamp());"),'REFUSE')
    variant('GPT unqualified target under search_path',producer("perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into probe_physical_facts values(p,clock_timestamp());"),'REFUSE')
    variant('GPT quoted identifiers',producer("""perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into "erp"."probe_physical_facts" values(p,clock_timestamp());"""),'REFUSE')
    variant('comment inside qualified name',producer("perform erp.assert_product_identity_time(p,clock_timestamp()); insert into erp./*x*/probe_physical_facts values(p,clock_timestamp());"),'REFUSE')
    variant('MERGE instead of INSERT',producer("perform erp.assert_product_identity_time(p,clock_timestamp()); merge into erp.probe_physical_facts t using (select p pid) s on false when not matched then insert values(s.pid,clock_timestamp());"),'REFUSE')
    variant('dynamic EXECUTE',producer("perform erp.assert_product_identity_time(p,clock_timestamp()); execute format('insert into %I.%I values($1,$2)','erp','probe_physical_facts') using p,clock_timestamp();"),'REFUSE')
    variant('assert through wrapper function',"create function erp.probe_wrap(p uuid) returns void language sql as $f$select erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK')$f$;"+producer("perform erp.probe_wrap(p); insert into erp.probe_physical_facts values(p,clock_timestamp());"),'REFUSE')
    variant('no producer at all, only a new product FK table',fact,'REFUSE')
    variant('product_id uuid column without FK',"create table erp.probe_nofk(product_id uuid,physical_at timestamptz);",'REFUSE')
    variant('prefixed *_product_id column without FK in public',"create table public.probe_pub(target_product_id uuid);",'REFUSE')
    variant('renamed registered column (stale registry)',"alter table erp.sales_items rename column product_id to item_product_ref;",'REFUSE')
    variant('helper rewritten to drop BS source',"create or replace function erp.latest_new_stock_physical_at_v1(p_product_id uuid) returns timestamptz language sql stable set search_path to '' as $f$select max(l.produced_at) from erp.fg_lots l where l.product_id=p_product_id$f$;",'REFUSE')
    variant('consumer no longer calls helper',"create or replace function erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamptz,text) returns uuid language plpgsql as $f$begin return $1;end$f$;",'REFUSE')
    variant('CONTROL: new table without product reference',"create table erp.probe_unrelated(id uuid, physical_at timestamptz);",'ACCEPT')
    variant('LIMIT: NEW_STOCK producer writing into a classified non-fact table',"create function erp.probe_sales(p uuid) returns void language plpgsql as $f$begin perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into erp.sales_items(product_id) values(p);end$f$;",'ACCEPT')
    # helper semantics
    p='11111111-1111-4111-8111-111111111111'
    cur.execute('insert into erp.products(id) values(%s)',(p,))
    h=lambda:cur.execute('select erp.latest_new_stock_physical_at_v1(%s)::text',(p,)).fetchone()[0]
    sem={'empty':h()}
    cur.execute("insert into erp.bs_cases(product_id,physical_at,untracked_type) values(%s,'2026-09-23 10:00Z','OUT_OF_NOWHERE')",(p,));sem['manual_without_origin']=h()
    b=cur.execute("insert into erp.bs_cases(product_id,physical_at,untracked_type) values(%s,'2026-09-23 10:05Z','LEGACY') returning id",(p,)).fetchone()[0]
    cur.execute("insert into erp.bs_case_manual_origins_v1(bs_case_id,origin_type) values(%s,'LEGACY')",(b,));sem['legacy_origin']=h()
    cur.execute("insert into erp.bs_cases(product_id,physical_at,qc_item_id) values(%s,'2026-09-23 09:00Z',gen_random_uuid())",(p,));sem['qc_bs']=h()
    b=cur.execute("insert into erp.bs_cases(product_id,physical_at,untracked_type) values(%s,'2026-09-23 09:30Z','OUT_OF_NOWHERE') returning id",(p,)).fetchone()[0]
    cur.execute("insert into erp.bs_case_manual_origins_v1(bs_case_id,origin_type) values(%s,'OUT_OF_NOWHERE')",(b,));sem['out_of_nowhere_origin']=h()
    cur.execute("update erp.bs_cases set untracked_type=null where id=%s",(b,));sem['out_of_nowhere_after_classification_cleared_type']=h()
    lot=cur.execute("insert into erp.fg_lots(product_id,produced_at,lot_origin) values(%s,'2026-09-23 11:00Z','PRODUCTION') returning id",(p,)).fetchone()[0]
    cur.execute("insert into erp.rework_orders(good_fg_lot_id) values(%s)",(lot,));sem['rework_good_lot_only_newer']=h()
    cur.execute("insert into erp.fg_lots(product_id,produced_at,lot_origin) values(%s,'2026-09-23 09:45Z','PRODUCTION')",(p,));sem['qc_good_lot']=h()
    report['helper_semantics']=sem
    report['helper_expected']={'empty':None,'manual_without_origin':None,'legacy_origin':None,'qc_bs':'2026-09-23 09:00:00+00','out_of_nowhere_origin':'2026-09-23 09:30:00+00',
        'out_of_nowhere_after_classification_cleared_type':'2026-09-23 09:30:00+00','rework_good_lot_only_newer':'2026-09-23 09:30:00+00','qc_good_lot':'2026-09-23 09:45:00+00'}
    report['helper_status']='PASS' if sem==report['helper_expected'] else 'FAIL'
    imm={}
    for label,sql in (('update',"update erp.bs_case_manual_origins_v1 set origin_type='LEGACY'"),('delete','delete from erp.bs_case_manual_origins_v1'),('truncate','truncate erp.bs_case_manual_origins_v1')):
        cur.execute('savepoint i')
        try:cur.execute(sql);imm[label]='ACCEPTED'
        except psycopg.Error as e:imm[label]=str(e).splitlines()[0]
        cur.execute('rollback to savepoint i')
    report['origin_immutability']=imm
    report['origin_immutability_status']='PASS' if all('BS_MANUAL_ORIGIN_IMMUTABLE' in v for v in imm.values()) else 'FAIL'
    conn.rollback()
with psycopg.connect(DB,autocommit=True) as c:c.execute('drop database av2smoke')
report['summary']=dict(guard_cases=len(report['cases']),guard_pass=sum(x['status']=='PASS' for x in report['cases']))
print(json.dumps(report,indent=1,default=str))
