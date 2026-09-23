"""AV rev2 probe: AU-R1, owner decisions 1C/2A and the coverage registry, before and after.

Runs from the frozen AU writer checkout on a disposable clone of the exact AN
boundary, reusing the AU-R1 probe fixtures (AL chain: work -> sewing -> laundry
-> QC, and the AL BS rework route). Phase 'before' observes frozen AU; phase
'after' installs AV rev2 through its closed-admission runtime (two exact
pre-use cycles) and replays the same cases. Expected outcomes come from the
contract and the recorded owner decisions (handoff §14), never from observed
behaviour. Business actions use the ordinary authenticated RPCs; guard
negatives create catalog objects inside a rolled-back savepoint only.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,TimeoutError as FutureTimeout
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
import argparse,json,os,queue,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_au_r1_probe as r1
import cp6_au_runtime as runtime
import cp6_au_cases as master
import cp6_at_cases as temporal
import cp6_ao_ap_installed as api
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as boundary

OUT=AUDITOR/'cp6-proof/av'
r1.OUT=OUT
chain=r1.chain
peer=r1.peer
now,edit,observe,production,receipt,final=r1.now,r1.edit,r1.observe,r1.production,r1.receipt,r1.final


def installed(cur):
    return cur.execute("select to_regclass('erp.bs_case_manual_origins_v1') is not null").fetchone()[0]


def manual_fact(cur):
    """New-stock BS predicate; the origin table is referenced only where it exists (frozen AU has none)."""
    origin=" or b.id in (select bs_case_id from erp.bs_case_manual_origins_v1 where origin_type='OUT_OF_NOWHERE')" if installed(cur) else ''
    return f"(b.qc_item_id is not null or b.source_laundry_bs_allocation_id is not null or b.untracked_type='OUT_OF_NOWHERE'{origin})"


def manual(cur,product,kind,at,reference=None):
    return chain.bs_action(cur,'CREATE_MANUAL_BS',dict(untracked_type=kind,legacy_reference=reference or 'AV-'+uuid.uuid4().hex[:12],
        change_reason='AV rev2 manual BS '+kind,physical_at=at.isoformat(),qty_pcs=1,product_id=str(product)))


def used_product(cur,today):
    """A product already used by a historical fact, so an edit creates a successor."""
    f=production(cur,today)
    source=receipt(cur,f,now(cur)-timedelta(minutes=30),0)
    final(cur,f,source,now(cur)-timedelta(minutes=20),10)
    api.admin(cur)
    return f


def bound_after_end(cur,product):
    api.admin(cur)
    ended=cur.execute('select effective_to from erp.products where id=%s',(product,)).fetchone()[0]
    if ended is None:return ended,0
    count=cur.execute(f'select count(*) from erp.bs_cases b where b.product_id=%s and b.physical_at>=%s and {manual_fact(cur)}',(product,ended)).fetchone()[0]
    return ended,count


def manual_cutoff(cur,today,kind):
    f=used_product(cur,today);product=f['product']
    fact=now(cur)-timedelta(seconds=60);manual(cur,product,kind,fact)
    effective=fact-timedelta(seconds=30)
    result,error=peer.attempt(cur,lambda:edit(cur,product,effective))
    ended,cut=bound_after_end(cur,product)
    row=dict(kind=kind,fact_physical_at=fact,requested_effective_from=effective,result=result,refusal=error,
             old_version_effective_to=ended,found_bs_after_end=cut,after=observe(cur,product),ordinary_authenticated_rpc=True)
    if kind=='OUT_OF_NOWHERE':
        row['expected']='Owner 1C: a found BS is a NEW_STOCK fact; the successor must not end the version before it'
        row['status']='PASS' if error else 'COUNTEREXAMPLE'
    else:
        row['expected']='Owner 1C: LEGACY stays existing stock and does not bound the successor'
        row['status']='CONTROL_PASS' if result and not error else 'FAIL'
    return row


def manual_reversed(cur,today,kind):
    f=used_product(cur,today);product=f['product']
    start=now(cur);effective=start-timedelta(seconds=90)
    successor=edit(cur,product,effective);api.admin(cur)
    fact=start-timedelta(seconds=60)
    result,error=peer.attempt(cur,lambda:manual(cur,product,kind,fact))
    row=dict(kind=kind,successor=successor,effective_from=effective,fact_physical_at=fact,result=result,refusal=error,ordinary_authenticated_rpc=True)
    if kind=='OUT_OF_NOWHERE':
        row['expected']='Owner 1C: a found BS after the version end is refused (NEW_STOCK on the version active at physical time)'
        row['status']='PASS' if error else 'COUNTEREXAMPLE'
    else:
        row['expected']='Owner 1C: LEGACY is existing stock; recording it on the ended version stays accepted'
        row['status']='CONTROL_PASS' if result and not error else 'FAIL'
    return row


def manual_classified(cur,today):
    f=used_product(cur,today);product=f['product']
    fact=now(cur)-timedelta(seconds=60);made=manual(cur,product,'OUT_OF_NOWHERE',fact)
    case=made['result']['bs_case_id']
    chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=case,cause_source='LAUNDRY',responsible_vendor_id=str(chain.base.VENDOR),
        change_reason='AV rev2 cause found after creation'),chain.version(cur,'bs_cases',case))
    api.admin(cur)
    untracked=cur.execute('select untracked_type from erp.bs_cases where id=%s',(case,)).fetchone()[0]
    effective=fact-timedelta(seconds=30)
    result,error=peer.attempt(cur,lambda:edit(cur,product,effective))
    return dict(fact_physical_at=fact,untracked_type_after_classification=untracked,requested_effective_from=effective,result=result,refusal=error,
                expected='Owner 1C: classification clears untracked_type, but the found-BS origin still bounds the successor',
                status='PASS' if error else 'COUNTEREXAMPLE',ordinary_authenticated_rpc=True)


PREINSTALL={}


def preinstall_fixtures():
    """Committed before AV installs (both phases): manual BS cases classified on AU, so the creation-time
    untracked type survives only in the insert audit row. OUT_OF_NOWHERE must keep bounding; LEGACY is the control."""
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        catalog=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        granted=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if granted:cur.execute('grant usage on schema erp to authenticated')
        if not cur.execute('select count(*) from erp.app_users').fetchone()[0]:api.seed(cur)
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        boundary.historical.prior.set_open_period(cur,date(2026,8,31))
        for kind in ('OUT_OF_NOWHERE','LEGACY'):
            f=used_product(cur,today);product=f['product']
            fact=now(cur)-timedelta(seconds=60);case=manual(cur,product,kind,fact)['result']['bs_case_id']
            chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=case,cause_source='LAUNDRY',responsible_vendor_id=str(chain.base.VENDOR),
                change_reason='AV rev2 cause found before AV installs'),chain.version(cur,'bs_cases',case))
            api.admin(cur)
            PREINSTALL[kind]=dict(product=product,bs_case_id=case,fact_physical_at=fact,
                untracked_type_after_classification=cur.execute('select untracked_type from erp.bs_cases where id=%s',(case,)).fetchone()[0])
        if granted:
            # Only business data may be committed before AV installs. The session grant is
            # revoked and the schema ACL restored exactly (grant/revoke can materialize a
            # NULL ACL) on this disposable clone; any other catalog difference refuses.
            cur.execute('revoke usage on schema erp from authenticated')
            cur.execute("update pg_catalog.pg_namespace set nspacl=%s::aclitem[] where nspname='erp'",(acl,))
        after=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0]
        drift=sorted(k for k in set(catalog)|set(after) if catalog.get(k)!=after.get(k))
        assert not drift,'PREINSTALL_CATALOG_DRIFT '+json.dumps(drift[:10])
        conn.commit()
    return PREINSTALL


def preinstall_case(cur,kind):
    p=PREINSTALL.get(kind)
    if not p:return dict(status='INCOMPLETE',error='PREINSTALL_FIXTURE_MISSING')
    origin=cur.execute('select origin_type from erp.bs_case_manual_origins_v1 where bs_case_id=%s',(p['bs_case_id'],)).fetchone() if installed(cur) else None
    effective=p['fact_physical_at']-timedelta(seconds=30)
    result,error=peer.attempt(cur,lambda:edit(cur,p['product'],effective))
    row=dict(fixture=p,origin=origin[0] if origin else None,requested_effective_from=effective,result=result,refusal=error,ordinary_authenticated_rpc=True)
    if kind=='OUT_OF_NOWHERE':
        row['expected']=('Owner 1C: a found BS classified before AV installs keeps its origin (backfilled from the insert audit row) '
                         'and still bounds the successor')
        cutoff=bool(error) and 'memotong histori' in (error.get('message') or '')
        row['status']=('COUNTEREXAMPLE' if not error else 'PASS' if cutoff and (origin is None and not installed(cur) or origin==('OUT_OF_NOWHERE',)) else 'FAIL')
    else:
        row['expected']='Owner 1C: a LEGACY case classified before AV installs gets no origin row and does not bound the successor'
        row['status']='CONTROL_PASS' if result and not error and origin is None else 'FAIL'
    return row


def manual_inactive(cur,today):
    f=used_product(cur,today);product=f['product']
    api.admin(cur);cur.execute('update erp.products set is_active=false where id=%s',(product,))
    result,error=peer.attempt(cur,lambda:manual(cur,product,'OUT_OF_NOWHERE',now(cur)-timedelta(seconds=30)))
    return dict(result=result,refusal=error,administrative_fixture='erp.products.is_active=false',
                expected='Owner 1C consequence: NEW_STOCK refuses a found BS on an inactive SKU (LEGACY remains available)',
                status='PASS' if error else 'COUNTEREXAMPLE')


def origin_immutable(cur,today):
    if not installed(cur):return dict(status='NOT_APPLICABLE',reason='Origin table exists only on AV rev2')
    f=used_product(cur,today);product=f['product']
    made=manual(cur,product,'OUT_OF_NOWHERE',now(cur)-timedelta(seconds=30));case=made['result']['bs_case_id']
    api.admin(cur)
    origin=cur.execute('select origin_type from erp.bs_case_manual_origins_v1 where bs_case_id=%s',(case,)).fetchone()
    attempts={}
    for label,sql in (('update',"update erp.bs_case_manual_origins_v1 set origin_type='LEGACY' where bs_case_id=%s"),
                      ('delete','delete from erp.bs_case_manual_origins_v1 where bs_case_id=%s')):
        cur.execute('savepoint origin_try')
        try:cur.execute(sql,(case,));attempts[label]='ACCEPTED'
        except psycopg.Error as exc:attempts[label]=exc.diag.message_primary
        cur.execute('rollback to savepoint origin_try')
    api.ordinary(cur)
    cur.execute('savepoint origin_read')
    try:cur.execute('select count(*) from erp.bs_case_manual_origins_v1').fetchone();attempts['authenticated_select']='ACCEPTED'
    except psycopg.Error as exc:attempts['authenticated_select']=exc.sqlstate
    cur.execute('rollback to savepoint origin_read');api.admin(cur)
    ok=origin==('OUT_OF_NOWHERE',) and all('BS_MANUAL_ORIGIN_IMMUTABLE' in attempts[k] for k in ('update','delete')) and attempts['authenticated_select']=='42501'
    return dict(origin=origin,attempts=attempts,expected='Origin recorded once; owner update/delete refused; no direct access for authenticated',status='PASS' if ok else 'FAIL')


def rework_ready(cur,today):
    """AL rework route up to an open laundry rework order on a QC BS; all upstream facts are two days old."""
    f=chain.work.draft(cur,today,Decimal(0));po=f['po']
    chain.peer.ordinary(cur);cur.execute('select erp.post_work_completion(%s)',(f['completion'],))
    chain.production.owner(cur)
    cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',
        (json.dumps(dict(work_completion_id=str(f['completion']),qty_pcs=10,reason='AV rev2 ten original physical pieces')),uuid.uuid4()))
    chain.actors.admin(cur)
    day=cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date from erp.work_completion_events where id=%s",(f['completion'],)).fetchone()[0]
    batch=cur.execute('select b.id from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%s',(f['group'],)).fetchone()[0]
    product=chain.base.create_product(cur,'AVR-'+uuid.uuid4().hex[:12])
    sent=chain.laundry_action(cur,'POST_DELIVERY',dict(distribution_batch_id=str(batch),vendor_id=chain.base.VENDOR,wash_process_id=chain.base.BASE_PROCESS,
        target_dyeing_color='AVR-NAVY',physical_at=chain.production.at(day,11),reason='AV rev2 ten physical pieces',
        lines=[dict(size_id=chain.base.SIZE,qty_sent_pcs=10)]),chain.base.group_version(cur,str(f['group'])))['delivery_id']
    received=chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=sent,wash_process_id=chain.base.BASE_PROCESS,physical_at=chain.production.at(day,12),
        reason='AV rev2 ten receipts',lines=[dict(delivery_batch_size_line_id=chain.base.delivery_size_line(cur,sent),qty_good_received=10,qty_bs_laundry=0,bs_product_id=None)]),
        chain.base.delivery_version(cur,sent))
    rx,rl=cur.execute('select x.id,x.receipt_line_id from erp.laundry_receipt_batch_size_lines x join erp.laundry_receipt_lines l on l.id=x.receipt_line_id where l.receipt_id=%s',(received['receipt_id'],)).fetchone()
    chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=str(f['group']),destination_location_id=chain.base.LOCATION,physical_at=chain.production.at(day,13).isoformat(),
        reason='AV rev2 six Good four BS',good_qty_pcs=6,completion_mode='ALL_READY',
        lines=[dict(final_product_id=product,qty_good_pcs=6,qty_bs_pcs=4,source_laundry_receipt_line_id=str(rl),source_laundry_receipt_batch_size_line_id=str(rx))]),
        chain.base.group_version(cur,str(f['group'])))
    chain.actors.admin(cur)
    bs=cur.execute("select id from erp.bs_cases where po_id=%s and status='OPEN'",(po,)).fetchone()[0]
    chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=f['component'],completed_before_bs_qty=4)],
        change_reason='AV rev2 original component earned before BS'),chain.version(cur,'bs_cases',bs))
    chain.actors.admin(cur)
    bom=cur.execute('select id from erp.accessory_bom_versions where product_id=%s and is_active',(product,)).fetchone()[0]
    made=chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='AVR-'+uuid.uuid4().hex[:20],bs_case_id=bs,destination_type='LAUNDRY',contractor_id=None,
        vendor_id=chain.base.VENDOR,qty_sent=4,physical_sent_at=chain.production.at(day,14),status='IN_PROGRESS',return_fg_location_id=chain.base.LOCATION,
        accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='AV rev2 four pieces to laundry rework',components=[]))
    return dict(product=product,bs=bs,order=made['result']['rework_order_id'],day=day)


def complete_rework(cur,f,at):
    payload=dict(rework_order_id=f['order'],qty_good=2,qty_bs=2,completed_at=at,return_fg_location_id=chain.base.LOCATION,
                 change_reason='AV rev2 two of four recover to Good')
    return chain.bs_action(cur,'COMPLETE_REWORK',payload,chain.version(cur,'rework_orders',f['order']))


def rework_cutoff(cur,today):
    f=rework_ready(cur,today);product=f['product']
    start=now(cur);completed=start-timedelta(seconds=60)
    posted=complete_rework(cur,f,completed);api.admin(cur)
    effective=start-timedelta(seconds=120)
    result,error=peer.attempt(cur,lambda:edit(cur,product,effective))
    return dict(rework_completed_at=completed,rework_lot=posted['result'].get('good_fg_lot_id'),requested_effective_from=effective,result=result,refusal=error,
                after=observe(cur,product),expected='Owner 2A: GOOD from rework is existing stock of the BS version and does not bound a successor',
                status='PASS' if result and not error else 'COUNTEREXAMPLE',ordinary_authenticated_rpc=True)


def rework_after_successor(cur,today):
    f=rework_ready(cur,today);product=f['product']
    start=now(cur);effective=start-timedelta(seconds=120)
    successor=edit(cur,product,effective);api.admin(cur)
    result,error=peer.attempt(cur,lambda:complete_rework(cur,f,start-timedelta(seconds=60)))
    return dict(successor=successor,effective_from=effective,result=result,refusal=error,
                expected='Owner 2A: rework GOOD returns to the BS version as existing stock even after that version ended',
                status='CONTROL_PASS' if result and not error else 'FAIL',ordinary_authenticated_rpc=True)


FACT="create table erp.cp6_av_probe_facts(product_id uuid references erp.products,physical_at timestamptz);"


def producer(body,search_path="set search_path=erp,pg_catalog"):
    return FACT+f"create function erp.cp6_av_probe_producer(p uuid,m text) returns void language plpgsql {search_path} as $f$begin {body} end$f$;"


GUARD_VARIANTS=[
    ('LOWERCASE_NEW_STOCK',producer("perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into erp.cp6_av_probe_facts values(p,clock_timestamp());"),True),
    ('UPPERCASE_CALL',producer("PERFORM ERP.ASSERT_PRODUCT_IDENTITY_TIME(p,clock_timestamp(),'NEW_STOCK'); INSERT INTO erp.cp6_av_probe_facts VALUES(p,clock_timestamp());"),True),
    ('UNQUALIFIED_UNDER_SEARCH_PATH',producer("perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into cp6_av_probe_facts values(p,clock_timestamp());"),True),
    ('QUOTED_IDENTIFIERS',producer("""perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into "erp"."cp6_av_probe_facts" values(p,clock_timestamp());"""),True),
    ('COMMENT_INSIDE_NAME',producer("perform erp.assert_product_identity_time(p,clock_timestamp()); insert into erp./*x*/cp6_av_probe_facts values(p,clock_timestamp());"),True),
    ('MERGE',producer("perform erp.assert_product_identity_time(p,clock_timestamp()); merge into erp.cp6_av_probe_facts t using (select p pid) s on false when not matched then insert values(s.pid,clock_timestamp());"),True),
    ('DYNAMIC_EXECUTE',producer("perform erp.assert_product_identity_time(p,clock_timestamp()); execute format('insert into %I.%I values($1,$2)','erp','cp6_av_probe_facts') using p,clock_timestamp();"),True),
    ('WRAPPER_ASSERT',"create function erp.cp6_av_probe_wrap(p uuid) returns void language sql as $f$select erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK')$f$;"
        +producer("perform erp.cp6_av_probe_wrap(p); insert into erp.cp6_av_probe_facts values(p,clock_timestamp());"),True),
    ('TABLE_ONLY',FACT,True),
    ('NO_FK_PRODUCT_ID',"create table erp.cp6_av_probe_nofk(product_id uuid,physical_at timestamptz);",True),
    ('NO_FK_PREFIXED_PUBLIC',"create table public.cp6_av_probe_pub(target_product_id uuid);",True),
    ('RENAMED_REGISTERED_COLUMN',"alter table erp.sales_items rename column product_id to item_product_ref;",True),
    ('HELPER_DRIFT',"create or replace function erp.latest_new_stock_physical_at_v1(p_product_id uuid) returns timestamptz language sql stable set search_path to '' as $f$select max(l.produced_at) from erp.fg_lots l where l.product_id=p_product_id$f$;",True),
    ('CONSUMER_DRIFT',"create or replace function erp.edit_product_identity_effective(p_product_id uuid,p_sku text,p_model_id uuid,p_brand_id uuid,p_color_name text,p_size_id uuid,p_product_name text,p_effective_from timestamptz default clock_timestamp(),p_reason text default null) returns uuid language plpgsql security definer set search_path to '' as $f$begin return p_product_id;end$f$;",True),
    ('CONTROL_UNRELATED_TABLE',"create table erp.cp6_av_probe_unrelated(id uuid,physical_at timestamptz);",False),
    ('LIMIT_NON_FACT_TABLE_WRITE',"create function erp.cp6_av_probe_sales(p uuid) returns void language plpgsql as $f$begin perform erp.assert_product_identity_time(p,clock_timestamp(),'NEW_STOCK'); insert into erp.sales_items(product_id) values(p);end$f$;",False),
]


def guard_case(cur,variant):
    if not installed(cur):return dict(status='NOT_APPLICABLE',reason='Coverage registry exists only on AV rev2')
    name,sql,refuse=next(v for v in GUARD_VARIANTS if v[0]==variant)
    api.admin(cur);cur.execute('set local role postgres')
    cur.execute(sql,prepare=False)
    cur.execute('reset role')
    result,error=peer.attempt(cur,lambda:cur.execute('select erp.assert_new_stock_cutoff_coverage_v1()').fetchone()[0]['references'])
    message=(error or {}).get('message') or ''
    ok=bool(error and any(x in message for x in ('UNCLASSIFIED','STALE','DRIFT'))) if refuse else bool(result is not None and not error)
    label='Documented limit: a NEW_STOCK producer writing into an already classified non-fact table is not detected' if variant.startswith('LIMIT') else None
    return dict(variant=variant,expected='Refuse at catalog level' if refuse else 'Accept',result=result,refusal=error,limit=label,
                status=('CONTROL_PASS' if not refuse else 'PASS') if ok else 'FAIL')


def guard_baseline(cur):
    if not installed(cur):return dict(status='NOT_APPLICABLE',reason='Coverage registry exists only on AV rev2')
    result=cur.execute('select erp.assert_new_stock_cutoff_coverage_v1()').fetchone()[0]
    ok=result['references']==23 and result['new_stock_fact_tables']==['bs_cases','fg_lots']
    return dict(references=result['references'],facts=result['new_stock_fact_tables'],status='CONTROL_PASS' if ok else 'FAIL')


def cases(cur,today):
    rows=[('CUTOFF:'+v,lambda v=v:r1.cutoff_case(cur,today,v)) for v in ('LAUNDRY_BS','QC_ALL_BS','QC_GOOD','BS_BEFORE_EFFECTIVE')]
    rows+=[('REVERSED:'+v,lambda v=v:r1.reversed_case(cur,today,v)) for v in ('LAUNDRY_BS','QC_ALL_BS')]
    rows+=[('MANUAL_CUTOFF:'+k,lambda k=k:manual_cutoff(cur,today,k)) for k in ('OUT_OF_NOWHERE','LEGACY')]
    rows+=[('MANUAL_REVERSED:'+k,lambda k=k:manual_reversed(cur,today,k)) for k in ('OUT_OF_NOWHERE','LEGACY')]
    rows+=[('MANUAL:CLASSIFIED_OUT_OF_NOWHERE',lambda:manual_classified(cur,today)),('MANUAL:INACTIVE_SKU',lambda:manual_inactive(cur,today)),
           ('MANUAL:ORIGIN_IMMUTABLE',lambda:origin_immutable(cur,today))]
    rows+=[('MANUAL:PREINSTALL_CLASSIFIED_'+k,lambda k=k:preinstall_case(cur,k)) for k in ('OUT_OF_NOWHERE','LEGACY')]
    rows+=[('REWORK:GOOD_DOES_NOT_BOUND',lambda:rework_cutoff(cur,today)),('REWORK:AFTER_SUCCESSOR',lambda:rework_after_successor(cur,today))]
    rows+=[('GUARD:BASELINE',lambda:guard_baseline(cur))]
    rows+=[('GUARD:'+v[0],lambda v=v:guard_case(cur,v[0])) for v in GUARD_VARIANTS]
    return rows


def found_race(admin,today,first,commit):
    """Two real sessions: a found (OUT_OF_NOWHERE) BS versus the successor edit, on committed disposable fixtures."""
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        f=production(cur,today);product=f['product']
        manual(cur,product,'OUT_OF_NOWHERE',now(cur)-timedelta(minutes=10),'AV-USED-'+uuid.uuid4().hex[:8])
        base=now(cur)
    fact=base-timedelta(seconds=60);effective=fact-timedelta(seconds=30)
    other='MASTER' if first=='BS' else 'BS'
    def act(cur,kind):
        if kind=='BS':return manual(cur,product,'OUT_OF_NOWHERE',fact)['result']['bs_case_id']
        result=edit(cur,product,effective);api.admin(cur);return result
    ready=queue.Queue()
    def worker(kind):
        try:
            with psycopg.connect(admin) as conn,conn.cursor() as cur:
                cur.execute("set local lock_timeout='20s';set local statement_timeout='40s'")
                ready.put(cur.execute('select pg_backend_pid()').fetchone()[0])
                return dict(ok=True,result=act(cur,kind))
        except psycopg.Error as exc:return dict(ok=False,sqlstate=exc.sqlstate,message=exc.diag.message_primary)
    with psycopg.connect(admin) as holder,holder.cursor() as hcur,ThreadPoolExecutor(max_workers=1) as pool:
        hpid=hcur.execute('select pg_backend_pid()').fetchone()[0]
        held=act(hcur,first)
        future=pool.submit(worker,other);wpid=ready.get(timeout=15)
        try:first_try=future.result(timeout=6)
        except FutureTimeout:
            first_try=None
            contention=dict(kind='BLOCKED',holder_blocks_worker=hcur.execute('select %s=any(pg_blocking_pids(%s))',(hpid,wpid)).fetchone()[0])
        else:contention=dict(kind='FAIL_FAST' if not first_try['ok'] else 'NO_CONTENTION',first_try=first_try)
        (holder.commit if commit else holder.rollback)()
        if first_try is None:outcome=future.result(timeout=45)
        elif not first_try['ok'] and 'POCKET_PERIOD_BUSY' in (first_try.get('message') or ''):outcome=worker(other)
        else:outcome=first_try
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        ended=cur.execute('select effective_to from erp.products where id=%s',(product,)).fetchone()[0]
        successors=cur.execute('select count(*) from erp.products where supersedes_product_id=%s',(product,)).fetchone()[0]
        recorded=cur.execute('select count(*) from erp.bs_cases where product_id=%s and physical_at=%s',(product,fact)).fetchone()[0]
        cut=cur.execute(f'select count(*) from erp.bs_cases b where b.product_id=%s and %s::timestamptz is not null and b.physical_at>=%s and {manual_fact(cur)}',(product,ended,ended)).fetchone()[0]
        authority=cur.execute('select count(*) from erp.product_identity_mutation_context_v1').fetchone()[0]
    bs_won=first=='BS' and commit or first=='MASTER' and not commit
    expected=dict(bs_recorded=bs_won,successor_created=not bs_won,contender_outcome_ok=not commit)
    observed=dict(bs_recorded=recorded>0,successor_created=successors>0,contender_outcome_ok=outcome['ok'])
    status='COUNTEREXAMPLE' if cut else 'PASS' if observed==expected and not authority else 'FAIL'
    return dict(status=status,first=first,first_committed=commit,fact_physical_at=fact,requested_effective_from=effective,held=held,
                contention=contention,contender_outcome=outcome,expected=expected,observed=observed,old_version_effective_to=ended,
                found_bs_after_end=cut,unused_authority_rows=authority,committed_fixture_isolated_in_race_copy=True)


def found_races(phase,verify):
    admin=boundary.ADMIN.rsplit('/',1)[0]+'/'+r1.RACE_DB
    report=dict(status='INCOMPLETE',database=r1.RACE_DB,schedules={},production_go=False,independent_acceptance=False)
    r1.docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',r1.RACE_DB)
    try:
        with psycopg.connect(admin) as conn,conn.cursor() as cur:
            report['runtime']=verify(cur);conn.rollback()
            cur.execute('grant usage on schema erp to authenticated')
            api.seed(cur);boundary.historical.prior.set_open_period(cur,date(2026,8,31))
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        for first in ('BS','MASTER'):
            for commit in (False,True):
                key='FOUND_RACE:'+first+'_FIRST:'+('COMMIT' if commit else 'ABORT')
                try:row=found_race(admin,today,first,commit)
                except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                report['schedules'][key]=row;r1.save('FOUND_RACES_'+phase.upper(),report)
                print(json.dumps(dict(group='FOUND_RACES_'+phase.upper(),case=key,**row),default=str),flush=True)
    finally:
        r1.docker('dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',r1.RACE_DB)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            report['race_database_remaining']=cur.execute('select count(*) from pg_database where datname=%s',(r1.RACE_DB,)).fetchone()[0]
    report['counts']=dict(Counter(r['status'] for r in report['schedules'].values()))
    bad=report['counts'].get('INCOMPLETE') or report['counts'].get('FAIL') or report['race_database_remaining']
    report['status']='INCOMPLETE' if bad else 'COUNTEREXAMPLE' if report['counts'].get('COUNTEREXAMPLE') else 'PASS'
    r1.save('FOUND_RACES_'+phase.upper(),report);return report


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    report=dict(status='INCOMPLETE',phase=phase,source=r1.source(),installed_functions_patched_for_testing=False,production_go=False,independent_acceptance=False)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        report['au_install']=runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])['status']
        report['preinstall_fixtures']=preinstall_fixtures()
        verify=runtime.verified
        if phase=='after':
            import cp6_av_runtime as candidate
            report['av_package']=candidate.qualify(boundary.PG,boundary.ADMIN)
            r1.save('RESULT_'+phase.upper(),report)
            verify=candidate.verified
            print(json.dumps(dict(av_package=report['av_package']),default=str),flush=True)
        with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
            report['family']=r1.family(cur);conn.rollback()
        r1.save('FAMILY_'+phase.upper(),report['family'])
        av=r1.group('AV_CASES_'+phase.upper(),cases,verify)
        report['av_cases']={k:av[k] for k in ('status','counts')}
        au=r1.group('AU_MASTER_'+phase.upper(),master.cases,verify)
        report['au_master']={k:au[k] for k in ('status','counts')}
        at=r1.group('AT_TEMPORAL_'+phase.upper(),temporal.cases,verify)
        report['at_temporal']={k:at[k] for k in ('status','counts')}
        laundry=r1.races(phase,verify)
        report['laundry_races']={k:laundry[k] for k in ('status','counts','race_database_remaining')}
        found=found_races(phase,verify)
        report['found_races']={k:found[k] for k in ('status','counts','race_database_remaining')}
        if phase=='after':
            report['post_use_refusal']=candidate.refuse_post_use(boundary.PG,boundary.ADMIN)
            clean=all(g['status']=='PASS' for g in (av,au,at,laundry,found))
            report['candidate_verdict']='CANDIDATE_WRITER_PASS' if clean else 'CANDIDATE_NOT_PASSING'
        complete=all(g['status']!='INCOMPLETE' for g in (av,au,at,laundry,found))
        report['status']='REVIEW_COMPLETE' if complete else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(av_probe_phase=phase,**{k:v for k,v in report.items() if k!='family'}),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error','AV_PROBE_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
