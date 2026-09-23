"""AU-R1 probe: successor cutoff versus NEW_STOCK physical facts outside fg_lots.

Runs from the frozen AU writer checkout on a disposable clone of the exact AN
boundary. AS, AT and AU are installed by their own closed-admission runtimes;
no installed function is patched. Physical fixtures reuse the AL rework chain
already executed by the AU regression (work -> sewing -> laundry -> QC); only
the physical times are chosen here. Every business action, including the
owner successor edit, uses the ordinary authenticated session.

Phase 'before' observes frozen AU only. Phase 'after' additionally installs the
candidate successor from this auditor checkout and replays the same cases.
Expected outcomes come from the contract, never from observed behaviour:
a successor must not end a version before a NEW_STOCK fact already recorded on
it, and assert_product_identity_time refuses the same state in reverse order.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,TimeoutError as FutureTimeout
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
import argparse,hashlib,json,os,queue,re,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
FROZEN='ca7f09556397801c50a2277bdb65b1bf019f9a05'
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_au_trial as writer
import cp6_au_runtime as runtime
import cp6_au_cases as master
import cp6_at_cases as temporal
import cp6_at_probe as peer
import cp6_ao_ap_installed as api
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as boundary
from cp6_ao_ap_inventory import function_pins

OUT=AUDITOR/'cp6-proof/au-r1'
chain=boundary.historical
KEY_FUNCTIONS=('erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)',
               'erp.assert_product_identity_time(uuid,timestamp with time zone,text)',
               'erp.post_laundry_receipt(uuid)','erp.post_qc(uuid)','erp.post_product_conversion(uuid)',
               'erp.create_manual_bs_case_v2(jsonb,uuid)','erp.validate_product_identity_period()')


def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')


def now(cur):
    return cur.execute('select clock_timestamp()').fetchone()[0]


def family(cur):
    """Native catalog map: every identity-time caller and every product-referencing table."""
    callers=[]
    for schema,name,args,src in cur.execute(r"""select n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),p.prosrc
        from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        where n.nspname in('erp','public') and p.prosrc ~ 'assert_product_identity_time\s*\('
          and p.proname<>'assert_product_identity_time' order by 1,2,3""").fetchall():
        calls=[re.sub(r'\s+',' ',c).strip() for c in re.findall(r'assert_product_identity_time\s*\(([^;]*?)\)\s*;',src,re.S)]
        modes=['EXISTING_STOCK' if re.search(r"'EXISTING_STOCK'\s*$",c) else 'NEW_STOCK' if re.search(r"'NEW_STOCK'\s*$",c) or c.count(',')==1 else 'DYNAMIC' for c in calls]
        callers.append(dict(function=f'{schema}.{name}({args})',calls=calls,modes=modes,
                            inserts=sorted(set(re.findall(r'insert\s+into\s+erp\.([a-z0-9_]+)',src,re.I)))))
    references=cur.execute("""select c.relname,a.attname,fk.confdeltype::text,
        coalesce((select jsonb_agg(t.attname order by t.attnum) from pg_attribute t where t.attrelid=c.oid and t.attnum>0
          and not t.attisdropped and t.atttypid in('timestamptz'::regtype,'timestamp'::regtype,'date'::regtype)),'[]')
        from pg_constraint fk join pg_class c on c.oid=fk.conrelid join pg_namespace ns on ns.oid=c.relnamespace
        join pg_attribute a on a.attrelid=c.oid and a.attnum=any(fk.conkey)
        where fk.contype='f' and fk.confrelid='erp.products'::regclass and fk.conrelid<>'erp.products'::regclass
        order by 1,2""").fetchall()
    writers={}
    for table in ('fg_lots','bs_cases'):
        writers[table]=[f'{s}.{n}({a})' for s,n,a in cur.execute(r"""select n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace
            where n.nspname in('erp','public') and p.prosrc ~* ('insert\s+into\s+erp\.'||%s||'\M') order by 1,2,3""",(table,)).fetchall()]
    definitions={k:hashlib.sha256(cur.execute('select pg_get_functiondef(%s::regprocedure)',(k,)).fetchone()[0].encode()).hexdigest()
                 for k in KEY_FUNCTIONS}
    # Residual P0 review inputs (read-only catalog): product-like columns that no FK
    # protects, direct privileges/policies on erp.products, and cascade edges.
    unguarded=cur.execute("""select n.nspname,c.relname,a.attname,format_type(a.atttypid,a.atttypmod)
        from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
        where n.nspname in('erp','public') and c.relkind in('r','p') and a.attnum>0 and not a.attisdropped
          and a.attname ~ 'product' and a.atttypid in('uuid'::regtype,'uuid[]'::regtype,'text'::regtype,'jsonb'::regtype)
          and not exists(select 1 from pg_constraint fk where fk.contype='f' and fk.conrelid=c.oid and a.attnum=any(fk.conkey)
                         and fk.confrelid='erp.products'::regclass)
          and not (n.nspname='erp' and c.relname='products')
        order by 1,2,3""").fetchall()
    privileges={role:{p:cur.execute('select has_table_privilege(%s,%s,%s)',(role,'erp.products',p)).fetchone()[0] for p in ('SELECT','INSERT','UPDATE','DELETE')}
                for role in ('anon','authenticated','service_role')}
    policies=cur.execute("""select polname,polcmd::text,polpermissive,array(select case when x=0 then 'PUBLIC' else pg_get_userbyid(x) end from unnest(polroles)x order by 1),
        pg_get_expr(polqual,polrelid),pg_get_expr(polwithcheck,polrelid) from pg_policy where polrelid='erp.products'::regclass order by 1""").fetchall()
    rls=cur.execute("select relrowsecurity,relforcerowsecurity from pg_class where oid='erp.products'::regclass").fetchone()
    return dict(identity_time_callers=callers,product_references=[dict(table=t,column=c,on_delete=d,time_columns=tc) for t,c,d,tc in references],
                fact_writers=writers,key_function_definition_sha256=definitions,
                product_like_columns_without_fk=[dict(schema=s,table=t,column=c,type=ty) for s,t,c,ty in unguarded],
                products_table_privileges=privileges,products_rls=dict(enabled=rls[0],forced=rls[1]),
                products_policies=[dict(name=n,cmd=c,permissive=p,roles=r,using=u,check=w) for n,c,p,r,u,w in policies])


def production(cur,today):
    """AL rework chain up to a sent laundry delivery; all upstream facts are two days old."""
    f=chain.work.draft(cur,today,Decimal(0))
    chain.peer.ordinary(cur);cur.execute('select erp.post_work_completion(%s)',(f['completion'],))
    chain.production.owner(cur)
    cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',
        (json.dumps(dict(work_completion_id=str(f['completion']),qty_pcs=10,reason='AU-R1 ten original physical pieces')),uuid.uuid4()))
    chain.actors.admin(cur)
    day=cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date from erp.work_completion_events where id=%s",(f['completion'],)).fetchone()[0]
    assert chain.production.at(day,11)<now(cur)-timedelta(minutes=10),('AU_R1_FIXTURE_NOT_HISTORICAL',day)
    batch=cur.execute('select b.id from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%s',(f['group'],)).fetchone()[0]
    product=chain.base.create_product(cur,'AUR1-'+uuid.uuid4().hex[:12])
    f.update(batch=str(batch),group=str(f['group']),product=product,day=day)
    f['delivery']=chain.laundry_action(cur,'POST_DELIVERY',dict(distribution_batch_id=f['batch'],vendor_id=chain.base.VENDOR,
        wash_process_id=chain.base.BASE_PROCESS,target_dyeing_color='AUR1-NAVY',physical_at=chain.production.at(day,11).isoformat(),
        reason='AU-R1 ten physical pieces',lines=[dict(size_id=chain.base.SIZE,qty_sent_pcs=10)]),chain.base.group_version(cur,f['group']))['delivery_id']
    return f


def receipt(cur,f,at,bs):
    received=chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=f['delivery'],wash_process_id=chain.base.BASE_PROCESS,
        physical_at=at.isoformat(),reason='AU-R1 physical laundry return',
        lines=[dict(delivery_batch_size_line_id=chain.base.delivery_size_line(cur,f['delivery']),qty_good_received=10-bs,
                    qty_bs_laundry=bs,bs_product_id=str(f['product']) if bs else None)]),chain.base.delivery_version(cur,f['delivery']))
    chain.actors.admin(cur)
    return cur.execute('''select x.id,x.receipt_line_id from erp.laundry_receipt_batch_size_lines x
        join erp.laundry_receipt_lines l on l.id=x.receipt_line_id where l.receipt_id=%s''',(received['receipt_id'],)).fetchone()


def final(cur,f,source,at,good):
    rx,rl=source
    return chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=f['group'],destination_location_id=chain.base.LOCATION,
        physical_at=at.isoformat(),reason='AU-R1 exact Good/BS split',good_qty_pcs=good,completion_mode='ALL_READY',
        lines=[dict(final_product_id=str(f['product']),qty_good_pcs=good,qty_bs_pcs=10-good,
                    source_laundry_receipt_line_id=str(rl),source_laundry_receipt_batch_size_line_id=str(rx))]),chain.base.group_version(cur,f['group']))


def manual_bs(cur,f,at):
    return chain.bs_action(cur,'CREATE_MANUAL_BS',dict(untracked_type='OUT_OF_NOWHERE',legacy_reference='AU-R1-'+uuid.uuid4().hex[:10],
        change_reason='AU-R1 manual BS observation',physical_at=at.isoformat(),qty_pcs=1,product_id=str(f['product'])))


def edit(cur,product,effective):
    p=cur.execute('select id,sku,model_id,brand_id,size_id from erp.products where id=%s',(product,)).fetchone()
    api.ordinary(cur)
    return cur.execute('select erp.edit_product_identity_effective(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (p[0],p[1],p[2],p[3],'AUR1-'+uuid.uuid4().hex[:10],p[4],'AU-R1 corrected master',effective,'AU-R1 owner successor')).fetchone()[0]


def observe(cur,product):
    """Every version of the root plus every physical fact bound to the old version."""
    api.admin(cur)
    return cur.execute('''select jsonb_build_object(
      'versions',(select jsonb_agg(jsonb_build_object('id',p.id,'from',p.effective_from,'to',p.effective_to,'supersedes',p.supersedes_product_id) order by p.effective_from)
                  from erp.products p where p.identity_root_id=(select identity_root_id from erp.products where id=%s)),
      'bs_cases',(select jsonb_agg(jsonb_build_object('physical_at',b.physical_at,'qc_item_id',b.qc_item_id,'laundry_allocation_id',b.source_laundry_bs_allocation_id,
                  'untracked_type',b.untracked_type,'stage',b.detected_at_stage,'status',b.status,'qty',b.qty_pcs) order by b.physical_at) from erp.bs_cases b where b.product_id=%s),
      'fg_lots',(select jsonb_agg(jsonb_build_object('produced_at',l.produced_at,'origin',l.lot_origin,'qty',l.initial_qty_pcs) order by l.produced_at) from erp.fg_lots l where l.product_id=%s))''',
      (product,product,product)).fetchone()[0]


def cutoff_case(cur,today,variant):
    f=production(cur,today);product=f['product']
    start=now(cur)
    if variant in ('LAUNDRY_BS','BS_BEFORE_EFFECTIVE'):
        fact=start-timedelta(seconds=60);receipt(cur,f,fact,10)
    elif variant in ('QC_ALL_BS','QC_GOOD'):
        source=receipt(cur,f,start-timedelta(seconds=90),0)
        fact=start-timedelta(seconds=60);final(cur,f,source,fact,10 if variant=='QC_GOOD' else 0)
    elif variant=='MANUAL_BS':
        fact=start-timedelta(seconds=60);manual_bs(cur,f,fact)
    else:raise AssertionError(variant)
    effective=fact+timedelta(seconds=30) if variant=='BS_BEFORE_EFFECTIVE' else fact-timedelta(seconds=30)
    before=observe(cur,product)
    result,error=peer.attempt(cur,lambda:edit(cur,product,effective))
    after=observe(cur,product)
    ended=cur.execute('select effective_to from erp.products where id=%s',(product,)).fetchone()[0]
    cut=cur.execute('''select count(*) filter(where b.qc_item_id is not null or b.source_laundry_bs_allocation_id is not null),
          count(*) filter(where b.qc_item_id is null and b.source_laundry_bs_allocation_id is null)
        from erp.bs_cases b where b.product_id=%s and %s::timestamptz is not null and b.physical_at>=%s''',(product,ended,ended)).fetchone()
    lots=cur.execute('select count(*) from erp.fg_lots where product_id=%s and %s::timestamptz is not null and produced_at>=%s',(product,ended,ended)).fetchone()[0]
    row=dict(variant=variant,fact_physical_at=fact,requested_effective_from=effective,result=result,refusal=error,
             old_version_effective_to=ended,new_stock_bs_after_end=cut[0],untracked_bs_after_end=cut[1],fg_lots_after_end=lots,
             before=before,after=after,ordinary_authenticated_rpc=True)
    if variant in ('LAUNDRY_BS','QC_ALL_BS'):
        row['expected']='Refuse: successor would end the version before a recorded NEW_STOCK BS fact'
        row['status']='PASS' if error else 'COUNTEREXAMPLE'
    elif variant=='QC_GOOD':
        row['expected']='Refuse through the existing fg_lots cutoff'
        row['status']='CONTROL_PASS' if error else 'FAIL'
    elif variant=='BS_BEFORE_EFFECTIVE':
        row['expected']='Accept: the fact precedes the requested boundary'
        row['status']='CONTROL_PASS' if result and not error and not cut[0] else 'FAIL'
    else:
        row['expected']='Contract undecided (STATUS_DAN_TODO P0 physical cutoff); observation only'
        row['status']='HOLD_CONTRACT'
    return row


def reversed_case(cur,today,variant):
    """Edit first, then try to record the same NEW_STOCK fact on the ended version."""
    f=production(cur,today);product=f['product']
    start=now(cur)
    source=receipt(cur,f,start-timedelta(seconds=120),0) if variant=='QC_ALL_BS' else None
    effective=start-timedelta(seconds=90)
    successor=edit(cur,product,effective);api.admin(cur)
    fact=start-timedelta(seconds=60)
    if variant=='LAUNDRY_BS':operation=lambda:receipt(cur,f,fact,10)
    else:operation=lambda:final(cur,f,source,fact,0)
    result,error=peer.attempt(cur,operation)
    return dict(variant=variant,successor=successor,effective_from=effective,fact_physical_at=fact,result=result,refusal=error,
                expected='The ended version refuses a new NEW_STOCK fact atomically (identity assert or an earlier product-period guard)',
                status='CONTROL_PASS' if error else 'FAIL',ordinary_authenticated_rpc=True)


def coverage_case(cur,variant):
    """A future NEW_STOCK producer writing an uncovered product fact must fail the catalog guard."""
    if not cur.execute("select to_regprocedure('erp.assert_new_stock_cutoff_coverage_v1()') is not null").fetchone()[0]:
        return dict(status='NOT_APPLICABLE',reason='Coverage guard exists only on the candidate successor')
    api.admin(cur);cur.execute('set local role postgres')
    cur.execute('create table erp.cp6_au_r1_sample_facts(product_id uuid not null references erp.products,physical_at timestamptz not null)')
    mode={'NEW_STOCK':",'NEW_STOCK'",'DEFAULT':'','DYNAMIC':',p_mode','EXISTING_STOCK':",'EXISTING_STOCK'"}[variant]
    cur.execute(f'''create function erp.cp6_au_r1_sample_post(p_product_id uuid,p_mode text) returns void language plpgsql set search_path to '' as $f$
      begin perform erp.assert_product_identity_time(p_product_id,clock_timestamp(){mode});
      insert into erp.cp6_au_r1_sample_facts(product_id,physical_at) values(p_product_id,clock_timestamp());end$f$''')
    cur.execute('reset role')
    result,error=peer.attempt(cur,lambda:cur.execute('select erp.assert_new_stock_cutoff_coverage_v1()').fetchone()[0])
    expected_refusal=variant!='EXISTING_STOCK'
    ok=bool(error and 'NEW_STOCK_CUTOFF_COVERAGE_MISSING' in error['message'] and 'cp6_au_r1_sample_facts' in error['message']) if expected_refusal else bool(result and not error)
    return dict(variant=variant,result=result,refusal=error,expected='Refuse uncovered NEW_STOCK producer' if expected_refusal else 'EXISTING_STOCK producer is not a cutoff source',
                status='CONTROL_PASS' if ok else 'FAIL')


def r1_cases(cur,today):
    rows=[('CUTOFF:'+v,lambda v=v:cutoff_case(cur,today,v)) for v in ('LAUNDRY_BS','QC_ALL_BS','QC_GOOD','BS_BEFORE_EFFECTIVE','MANUAL_BS')]
    rows+=[('REVERSED:'+v,lambda v=v:reversed_case(cur,today,v)) for v in ('LAUNDRY_BS','QC_ALL_BS')]
    rows+=[('COVERAGE_GUARD:'+v,lambda v=v:coverage_case(cur,v)) for v in ('NEW_STOCK','DEFAULT','DYNAMIC','EXISTING_STOCK')]
    return rows


RACE_DB='cp6_au_r1_race'


def docker(*args):
    subprocess.run(['docker','exec','supabase_db_cp5-local',*args],check=True)


def race(admin,today,first,commit):
    """Two real sessions on committed disposable fixtures: NEW_STOCK BS versus successor edit."""
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        f=production(cur,today);base=now(cur)
    product=f['product'];fact=base-timedelta(seconds=60);effective=fact-timedelta(seconds=30)
    other='MASTER' if first=='BS' else 'BS'
    def act(cur,kind):
        if kind=='BS':return list(receipt(cur,f,fact,10))
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
        new_stock_bs=cur.execute('''select count(*) from erp.bs_cases where product_id=%s
            and (qc_item_id is not null or source_laundry_bs_allocation_id is not null)''',(product,)).fetchone()[0]
        cut=cur.execute('''select count(*) from erp.bs_cases where product_id=%s and %s::timestamptz is not null and physical_at>=%s
            and (qc_item_id is not null or source_laundry_bs_allocation_id is not null)''',(product,ended,ended)).fetchone()[0]
        authority=cur.execute('select count(*) from erp.product_identity_mutation_context_v1').fetchone()[0]
    bs_won=first=='BS' and commit or first=='MASTER' and not commit
    expected=dict(bs_recorded=bs_won,successor_created=not bs_won,contender_outcome_ok=not commit)
    observed=dict(bs_recorded=new_stock_bs>0,successor_created=successors>0,contender_outcome_ok=outcome['ok'])
    status='COUNTEREXAMPLE' if cut else 'PASS' if observed==expected and not authority else 'FAIL'
    return dict(status=status,first=first,first_committed=commit,fact_physical_at=fact,requested_effective_from=effective,
                held=held,contention=contention,contender_outcome=outcome,expected=expected,observed=observed,
                old_version_effective_to=ended,new_stock_bs_after_end=cut,unused_authority_rows=authority,
                actions='ordinary authenticated laundry public RPC and owner successor RPC',committed_fixture_isolated_in_race_copy=True)


def races(phase,verify):
    """Every schedule runs on a disposable copy of the clone; the clone itself never receives commits."""
    admin=boundary.ADMIN.rsplit('/',1)[0]+'/'+RACE_DB
    report=dict(status='INCOMPLETE',database=RACE_DB,schedules={},production_go=False,independent_acceptance=False)
    docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',RACE_DB)
    try:
        with psycopg.connect(admin) as conn,conn.cursor() as cur:
            report['runtime']=verify(cur);conn.rollback()
            cur.execute('grant usage on schema erp to authenticated')
            api.seed(cur);boundary.historical.prior.set_open_period(cur,date(2026,8,31))
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        for first in ('BS','MASTER'):
            for commit in (False,True):
                key='RACE:'+first+'_FIRST:'+('COMMIT' if commit else 'ABORT')
                try:row=race(admin,today,first,commit)
                except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                report['schedules'][key]=row;save('RACES_'+phase.upper(),report)
                print(json.dumps(dict(group='RACES_'+phase.upper(),case=key,**row),default=str),flush=True)
    finally:
        docker('dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',RACE_DB)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            report['race_database_remaining']=cur.execute('select count(*) from pg_database where datname=%s',(RACE_DB,)).fetchone()[0]
    report['counts']=dict(Counter(r['status'] for r in report['schedules'].values()))
    bad=report['counts'].get('INCOMPLETE') or report['counts'].get('FAIL') or report['race_database_remaining']
    report['status']='INCOMPLETE' if bad else 'COUNTEREXAMPLE' if report['counts'].get('COUNTEREXAMPLE') else 'PASS'
    save('RACES_'+phase.upper(),report);return report


def group(name,factory,verify):
    report=dict(status='INCOMPLETE',cases={},production_go=False,independent_acceptance=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        report['runtime_before']=verify(cur)
        initial=boundary.snapshot(cur);catalog=function_pins(cur)
        if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:cur.execute('grant usage on schema erp to authenticated')
        if not initial['erp']['app_users']['count']:api.seed(cur)
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        boundary.historical.prior.set_open_period(cur,date(2026,8,31))
        cases=factory(cur,today)
        report['planned_case_ids']=[k for k,_ in cases]
        for key,operation in cases:
            before=boundary.snapshot(cur)
            cur.execute('savepoint r1_case')
            try:row=operation()
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint r1_case');api.admin(cur);cur.execute('release savepoint r1_case')
            row['full_boundary_restored']=boundary.snapshot(cur)==before
            if not row['full_boundary_restored']:row['status']='INCOMPLETE'
            report['cases'][key]=row;save(name,report)
            print(json.dumps(dict(group=name,case=key,**row),default=str),flush=True)
        assert function_pins(cur)==catalog,'R1_CASE_FUNCTION_OR_ACL_MUTATION'
        conn.rollback();report['runtime_after']=verify(cur)
        report['complete_boundary_restored']=boundary.snapshot(cur)==initial
        conn.rollback()
    report['counts']=dict(Counter(r['status'] for r in report['cases'].values()))
    bad=report['counts'].get('INCOMPLETE') or report['counts'].get('FAIL') or not report['complete_boundary_restored']
    report['status']='INCOMPLETE' if bad else 'COUNTEREXAMPLE' if report['counts'].get('COUNTEREXAMPLE') else 'PASS'
    save(name,report);return report


def source():
    head=subprocess.check_output(['git','-C',str(AUDITOR),'rev-parse','HEAD'],text=True).strip()
    tree=subprocess.check_output(['git','-C',str(AUDITOR),'rev-parse','HEAD^{tree}'],text=True).strip()
    assert not subprocess.check_output(['git','-C',str(AUDITOR),'diff','HEAD','--name-only'],text=True).strip(),'AUDITOR_TRACKED_DIRTY'
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==FROZEN,'WRITER_NOT_FROZEN_AU'
    assert not subprocess.check_output(['git','diff','HEAD','--name-only'],text=True).strip(),'WRITER_TRACKED_DIRTY'
    changed=subprocess.check_output(['git','-C',str(AUDITOR),'diff','--name-only',FROZEN,head],text=True).splitlines()
    return dict(auditor_head=head,auditor_tree=tree,frozen_writer=FROZEN,changed_from_frozen=changed,
                sha256={p:hashlib.sha256((AUDITOR/p).read_bytes()).hexdigest() for p in changed if (AUDITOR/p).exists()})


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    report=dict(status='INCOMPLETE',phase=phase,source=source(),installed_functions_patched_for_testing=False,
                production_go=False,independent_acceptance=False)
    save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        writer.install_at()
        report['au_install']=runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        verify=runtime.verified
        with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
            report['au_runtime']=runtime.verified(cur);report['family']=family(cur);conn.rollback()
        save('FAMILY_'+phase.upper(),report['family'])
        print(json.dumps(dict(family_phase=phase,family=report['family']),default=str),flush=True)
        if phase=='after':
            import cp6_au_r1_candidate as candidate
            report['candidate_package']=candidate.qualify(boundary.PG,boundary.ADMIN)
            save('RESULT_'+phase.upper(),report)
            verify=candidate.verified
            with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
                report['candidate_family']=family(cur);conn.rollback()
            save('FAMILY_CANDIDATE',report['candidate_family'])
            print(json.dumps(dict(family_phase='candidate',package=report['candidate_package'],family=report['candidate_family']),default=str),flush=True)
        r1=group('R1_CASES_'+phase.upper(),r1_cases,verify)
        report['r1']={k:r1[k] for k in ('status','counts')}
        au=group('AU_MASTER_'+phase.upper(),master.cases,verify)
        report['au_master']={k:au[k] for k in ('status','counts')}
        at=group('AT_TEMPORAL_'+phase.upper(),temporal.cases,verify)
        report['at_temporal']={k:at[k] for k in ('status','counts')}
        rc=races(phase,verify)
        report['races']={k:rc[k] for k in ('status','counts','race_database_remaining')}
        if phase=='after':
            report['post_use_refusal']=candidate.refuse_post_use(boundary.PG,boundary.ADMIN)
            clean=r1['status']=='PASS' and au['status']=='PASS' and at['status']=='PASS' and rc['status']=='PASS'
            report['candidate_verdict']='CANDIDATE_WRITER_PASS' if clean else 'CANDIDATE_NOT_PASSING'
        complete=all(g['status']!='INCOMPLETE' for g in (r1,au,at,rc))
        report['status']='REVIEW_COMPLETE' if complete else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        save('RESULT_'+phase.upper(),report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('family','candidate_family')},default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error','R1_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
