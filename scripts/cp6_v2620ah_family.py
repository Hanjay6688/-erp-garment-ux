#!/usr/bin/env python3
"""AH return family: source-qualified original cases, legal paths and detectors."""
from pathlib import Path
from datetime import date,timedelta
import argparse,json,os,re,traceback,uuid
import psycopg
import cp6_ag_residual_review as original
import cp6_v2620ag_family as ag
import cp6_v2620ah_runtime as runtime
from cp6_v2620ah_build_sql import DIRTY_QUERY
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot
actors,base,prior=ag.actors,ag.base,ag.prior
peer=ag.peer
ROOT=Path('cp6-proof/writer-ah')
CHECK='V2620AH_RETURN_ALLOCATION_LINEAGE_MISMATCH'

def save(name,data):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2,default=str)+'\n')

def report(cur,day,blocked=False):
    result=peer.confidence(cur,day)
    check=cur.execute('select severity,issue_count from erp.run_v268_financial_report_checks() where check_name=%s',(CHECK,)).fetchone()
    assert result['data_confidence']['status']==('BLOCKED' if blocked else 'READY'),result
    assert check[0]=='CRITICAL' and (check[1]>0)==blocked,check
    actors.admin(cur)
    return dict(status='PASS',check=check,snapshot=result)

def install(cur):
    actors.admin(cur);cur.execute('set local role postgres')
    cur.execute(ag.sql_body(runtime.MIGRATION),prepare=False)
    cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]))
    assert len(runtime.verified_successor(cur))==690
    cur.execute('reset role')

def admission(mode):
    def case(cur,day):
        if mode=='CLEAN':
            before=function_catalog(cur);install(cur);actors.admin(cur)
            cur.execute(ag.sql_body(runtime.ROLLBACK),prepare=False)
            runtime.verify_predecessor(cur);assert function_catalog(cur)==before
            return dict(status='PASS',clean_install_restore=True)
        if mode=='VALID_OTHER_DRAFT':
            f=original.posted_fixture(cur,day);rid=original.create_return(cur,day,f,f['second_location'],'GRADE_A')
            install(cur)
            posted=peer.operation(cur,'select erp.post_sales_return(%s)',(rid,));original.success(posted)
            return dict(status='PASS',existing_valid_draft_posts=posted,report=report(cur,day))
        if mode in ('OVER_ALLOCATION','DRAFT_SOURCE'):
            proof=(original.allocation_case('TWO_DOCUMENTS') if mode=='OVER_ALLOCATION' else original.draft_source_case)(cur,day)
            assert proof['status']=='BUG_PROVEN',proof
            actors.admin(cur);cur.execute('set local role postgres')
            expected='AH_PREEXISTING_RETURN_ALLOCATION_REVIEW_REQUIRED' if mode=='OVER_ALLOCATION' else 'AH_PREEXISTING_DRAFT_RETURN_SOURCE_REVIEW_REQUIRED'
            error=ag.expected_refusal(cur,lambda:cur.execute(ag.sql_body(runtime.MIGRATION),prepare=False),expected)
            cur.execute('reset role')
            return dict(status='PASS',original_ag_counterexample=proof,refusal=error)
        mutations={
            'FUNCTION':("alter function erp.post_sales_return(uuid) set work_mem='64MB'",'AH_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
            'ACL':('grant execute on function erp.normalize_sales_return_item_from_allocation() to authenticated','AH_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
            'PLATFORM':("update supabase_migrations.schema_migrations set statements=array['wrong'] where name='erp_v2_6_20ag_cp6_sale_reservation_lineage'",'AH_REQUIRES_EXACT_AG_PLATFORM_CAPSULE'),
            'MARKER':("delete from erp.schema_migrations where version='v2.6.20ag'",'AH_REQUIRES_EXACT_AG_WITHOUT_AH_RESIDUE')}
        actors.admin(cur)
        if mode=='UNRELATED_FUNCTION_BINDING':
            cur.execute("alter function erp.post_sale_v2(uuid,uuid,bigint) set work_mem='64MB'")
            try:runtime.verify_predecessor(cur)
            except AssertionError as exc:
                assert 'AG_LIVE_FUNCTION_DRIFT' in str(exc),str(exc)
                return dict(status='PASS',preapply_full_catalog_refusal=str(exc))
            raise AssertionError('Unrelated source drift was accepted')
        query,expected=mutations[mode];cur.execute(query);cur.execute('set local role postgres')
        error=ag.expected_refusal(cur,lambda:cur.execute(ag.sql_body(runtime.MIGRATION),prepare=False),expected)
        cur.execute('reset role');return dict(status='PASS',refusal=error)
    return case

def retained(fn):
    def case(cur,day):
        result=fn(cur,day)
        assert result['status']=='CONTROL_PASS',result
        result['status']='PASS';result['original_ag_oracle_retained']=True
        return result
    return case

def ordinary_return(destination,grade):
    def case(cur,day):
        f=original.posted_fixture(cur,day);f['ordinary_draft_creation']=True
        actors.admin(cur)
        assert not base.one(cur,"select has_table_privilege('authenticated','erp.locations','SELECT')")
        assert not base.one(cur,"select has_function_privilege('authenticated','erp.normalize_sales_return_item_from_allocation()','EXECUTE')")
        dest=f['second_location'] if destination=='OTHER' else base.LOCATION
        rid=original.create_return(cur,day,f,dest,grade)
        identity=cur.execute('select current_user,session_user,erp.current_app_role()').fetchone()
        assert identity==('authenticated','authenticated','OWNER'),identity
        operation=peer.operation(cur,'select erp.post_sales_return(%s)',(rid,));original.success(operation)
        actors.admin(cur)
        movement=cur.execute("select m.location_id,m.quality_grade,m.qty_signed from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id where i.return_id=%s and m.movement_type='SALE_RETURN'",(rid,)).fetchall()
        assert movement==[(uuid.UUID(str(dest)),grade,1)],movement
        return dict(status='PASS',draft_caller=identity,posting=operation,movement=movement,reference_table_select_granted=False,normalizer_execute_granted=False,report=report(cur,day))
    return case

def split_destination(cur,day):
    f=original.posted_fixture(cur,day);f['ordinary_draft_creation']=True
    ids=[]
    for destination,grade in ((base.LOCATION,'GRADE_A'),(f['second_location'],'GRADE_B'),(f['second_location'],'HOLD')):
        rid=original.create_return(cur,day,f,destination,grade);ids.append(rid)
        original.success(peer.operation(cur,'select erp.post_sales_return(%s)',(rid,)))
    extra=original.create_return(cur,day,f,f['second_location'],'GRADE_A')
    refusal=original.refusal(cur,'select erp.post_sales_return(%s)',(extra,),'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION')
    original.success(peer.operation(cur,"select erp.reverse_sales_return(%s,'AH legitimate partial reversal')",(ids[0],)))
    # Rereceipt occurs after reversal; do not use an earlier physical instant.
    peer.ordinary(cur);cur.execute('update erp.sales_returns set physical_at=clock_timestamp() where id=%s',(extra,))
    original.success(peer.operation(cur,'select erp.post_sales_return(%s)',(extra,)))
    actors.admin(cur)
    active=base.one(cur,"select sum(i.qty_pcs) from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s and r.status='POSTED'",(f['sale']['sale_id'],))
    assert active==3
    today=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
    return dict(status='PASS',active_returned=active,original_allocation=3,over_limit_refusal=refusal,report=report(cur,today))

def allocation_limit(cur,day):
    f=peer.fixture(cur,day)
    payload=dict(f['payload'],sale_id=f['sale']['sale_id'],reason='AH two original sale lines',items=[dict(f['payload']['items'][0]),dict(f['payload']['items'][0])])
    saved=original.success(peer.operation(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)',(json.dumps(payload),uuid.uuid4(),f['sale']['row_version'])))
    original.success(peer.operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(saved['sale_id'],uuid.uuid4(),saved['row_version'])))
    actors.admin(cur)
    allocations=[str(row[0]) for row in cur.execute('select a.id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s order by a.id',(saved['sale_id'],))]
    assert len(allocations)==2
    f['allocation']=allocations[0];f['ordinary_draft_creation']=True
    first=original.create_return(cur,day,f,base.LOCATION,'GRADE_A',(2,))
    second=original.create_return(cur,day,f,f['second_location'],'GRADE_B',(2,))
    original.success(peer.operation(cur,'select erp.post_sales_return(%s)',(first,)))
    error=original.refusal(cur,'select erp.post_sales_return(%s)',(second,),'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION')
    # The other original allocation remains independently eligible.
    f['allocation']=allocations[1]
    other=original.create_return(cur,day,f,f['second_location'],'GRADE_A',(2,))
    original.success(peer.operation(cur,'select erp.post_sales_return(%s)',(other,)))
    return dict(status='PASS',selected_allocation_limit_preserved=True,other_allocation_remains_eligible=True,atomic_refusal=error,report=report(cur,day))

def source_state(mode):
    def case(cur,day):
        f=peer.fixture(cur,day) if mode=='DRAFT' else original.posted_fixture(cur,day)
        actors.admin(cur)
        f['allocation']=base.one(cur,'select id from erp.sale_stock_allocations where sale_item_id=%s',(f['item'],))
        if mode=='REVERSED':original.success(peer.operation(cur,"select erp.reverse_sale(%s,'AH source state control')",(f['sale']['sale_id'],)))
        f['ordinary_draft_creation']=True
        error=original.capture_draft_refusal(cur,lambda:original.create_return(cur,day,f,base.LOCATION,'GRADE_A'),'P0001','AH_RETURN_SOURCE_MUST_BE_ACTIVE_POSTED_SALE')
        if mode=='DRAFT':
            payload=dict(f['payload'],sale_id=f['sale']['sale_id'],reason='Draft remains editable',items=[dict(f['payload']['items'][0],product_id=f['products'][1])])
            original.success(peer.operation(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)',(json.dumps(payload),uuid.uuid4(),f['sale']['row_version'])))
        return dict(status='PASS',atomic_refusal=error,report=report(cur,day))
    return case

def source_rebind(cur,day):
    f=original.posted_fixture(cur,day);f['ordinary_draft_creation']=True
    rid=original.create_return(cur,day,f,base.LOCATION,'GRADE_A')
    payload=dict(f['payload'],sale_number='AH-OTHER-'+uuid.uuid4().hex,reason='Other legitimate sale')
    other=original.success(peer.operation(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,null)',(json.dumps(payload),uuid.uuid4())))
    original.success(peer.operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(other['sale_id'],uuid.uuid4(),other['row_version'])))
    original.success(peer.operation(cur,'update erp.sales_returns set sale_id=%s where id=%s',(other['sale_id'],rid)))
    error=original.refusal(cur,'select erp.post_sales_return(%s)',(rid,),'AH_RETURN_ALLOCATION_SOURCE_MISMATCH')
    return dict(status='PASS',atomic_refusal=error)

def anonymous_draft(cur,day):
    f=original.posted_fixture(cur,day);before=original.state(cur);cur.execute('savepoint ah_anon')
    try:
        cur.execute('set local session authorization anon')
        cur.execute("insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at) values(%s,%s,%s,%s)",('AH-ANON',f['sale']['sale_id'],f['customers'][0],day.isoformat()+'T12:00:00+07:00'))
    except psycopg.Error as exc:
        error=dict(sqlstate=exc.sqlstate,message=str(exc));assert exc.sqlstate=='42501',error
    else:raise AssertionError('Anonymous return creation accepted')
    finally:cur.execute('rollback to savepoint ah_anon;release savepoint ah_anon');actors.admin(cur)
    assert original.state(cur)==before
    return dict(status='PASS',atomic_refusal=error)

def reference_case(target,expect_fixed=False):
    """Same lawful DRAFT insert as existing business fixture, real OWNER caller.

    The original control retries the identical insert as fixture administrator
    only after rolling back the denied OWNER attempt. No posted history is forged.
    The complete established workflow must then succeed to qualify the input.
    """
    def case(cur,day):
        from datetime import date
        from decimal import Decimal
        import cp6_aa_invoice_partial_audit as aa
        import cp6_v2620f_final_runtime_regression as final
        observed=[]
        table='work_completion_lines' if target=='WORK' else 'vendor_invoice_items'
        class Probe:
            def __getattr__(self,name):return getattr(cur,name)
            def execute(self,query,params=None,**kwargs):
                if not re.search(r'insert\s+into\s+erp\.'+table+r'\b',str(query),re.I):
                    # Invoice posting is intentionally a private backend
                    # dependency. This probe changes only the permitted DRAFT
                    # row caller; preserve the original backend posting caller.
                    if 'select erp.post_vendor_invoice(' in str(query):actors.admin(cur)
                    return cur.execute(query,params,**kwargs)
                actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ah_reference_insert')
                identity=peer.ordinary(cur);error=None
                try:cur.execute(query,params,**kwargs)
                except psycopg.Error as exc:
                    error=dict(sqlstate=exc.sqlstate,message=str(exc))
                    cur.execute('rollback to savepoint ah_reference_insert');actors.admin(cur)
                    assert actors.boundary(cur)==before
                finally:cur.execute('release savepoint ah_reference_insert')
                if error:
                    if expect_fixed:raise AssertionError(error)
                    assert error['sqlstate']=='42501',error
                    expected='production_orders' if target=='WORK' else 'laundry_receipt_lines'
                    assert 'permission denied for table '+expected in error['message'],error
                    actors.admin(cur);cur.execute(query,params,**kwargs)
                observed.append(dict(table=table,identity=identity,ordinary_refusal=error,
                                     identical_fixture_admin_control=error is not None))
                return cur
        proxy=Probe()
        if target=='WORK':
            f=aa.estimated_receipt(cur,day);aa.partial_production(proxy,f)
        else:
            actors.admin(cur);prior.set_open_period(cur,date(2026,8,31))
            f=final.base.fresh(cur,'a')
            delivery=final.base.post_delivery(cur,f,final.base.BASE_PROCESS,'2026-09-01T11:00:00Z')
            _,_,receipt=final.base.post_receipt(cur,str(delivery['delivery_id']),final.base.BASE_PROCESS,'2026-09-02T11:00:00Z')
            final.finalize_laundry_invoice(proxy,receipt,Decimal('10'))
        assert len(observed)==1,observed
        actors.admin(cur);today=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
        state=peer.confidence(cur,today);assert state['data_confidence']['status']=='READY',state
        return dict(status='PASS',classification='CONTROL_PASS' if observed[0]['ordinary_refusal'] is None else 'BUG_PROVEN',
                    selected_path=target,observations=observed,complete_business_control=True,
                    invoice_posting_backend_only=target=='VENDOR',
                    synthetic_detector_control=False,report=state)
    return case

def detector(mode):
    def case(cur,day):
        f=original.posted_fixture(cur,day);f['ordinary_draft_creation']=True
        rid=original.create_return(cur,day,f,f['second_location'],'GRADE_A')
        original.success(peer.operation(cur,'select erp.post_sales_return(%s)',(rid,)))
        report(cur,day);actors.admin(cur)
        mid=base.one(cur,"select m.id from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id where i.return_id=%s and m.movement_type='SALE_RETURN'",(rid,))
        query,params={
            'PRODUCT':('update erp.fg_stock_movements set product_id=%s where id=%s',(f['products'][1],mid)),
            'LOCATION':('update erp.fg_stock_movements set location_id=%s where id=%s',(base.LOCATION,mid)),
            'GRADE':("update erp.fg_stock_movements set quality_grade='GRADE_B' where id=%s",(mid,)),
            'CUSTOMER':('update erp.fg_stock_movements set customer_id=%s where id=%s',(f['customers'][1],mid)),
            'DATE':("update erp.fg_stock_movements set physical_at=physical_at+interval '1 hour' where id=%s",(mid,)),
            'QUANTITY':('update erp.fg_stock_movements set qty_signed=2 where id=%s',(mid,)),
            'ORPHAN':('update erp.fg_stock_movements set source_id=%s where id=%s',(uuid.uuid4(),mid)),
            'MISSING':('delete from erp.fg_stock_movements where id=%s',(mid,)),
        }[mode]
        cur.execute(query,params)
        result=report(cur,day,True);result.update(synthetic_detector_control=True,not_a_new_business_counterexample=True)
        return result
    return case

def phase_cases(phase):
    if phase=='reference':return [('WORK',reference_case('WORK')),('VENDOR',reference_case('VENDOR'))]
    if phase=='admission':return [(m,admission(m)) for m in ('CLEAN','VALID_OTHER_DRAFT','OVER_ALLOCATION','DRAFT_SOURCE','FUNCTION','ACL','PLATFORM','MARKER','UNRELATED_FUNCTION_BINDING')]
    if phase=='focused':
        replaced={'RETURN_ALLOCATION_TWO_DOCUMENTS','RETURN_DRAFT_SOURCE','RETURN_ORDINARY_DRAFT_CREATE','RETURN_REBIND_SALE'}
        cases=[('AG_'+name,retained(fn)) for name,fn in original.cases() if name not in replaced]
        cases += [('ORDINARY_'+dest+'_'+grade,ordinary_return(dest,grade)) for dest in ('SAME','OTHER') for grade in ('GRADE_A','GRADE_B','HOLD')]
        cases += [('ALLOCATION_LIMIT',allocation_limit),('SPLIT_DESTINATION',split_destination),('SOURCE_DRAFT',source_state('DRAFT')),('SOURCE_REVERSED',source_state('REVERSED')),('SOURCE_REBIND',source_rebind),('ANONYMOUS_DRAFT',anonymous_draft)]
        return cases+[('AG_WRITER_'+name,fn) for name,fn in ag.phase_cases('focused')]
    if phase=='detector':return [(mode,detector(mode)) for mode in ('PRODUCT','LOCATION','GRADE','CUSTOMER','DATE','QUANTITY','ORPHAN','MISSING')]+[('AG_'+name,fn) for name,fn in ag.phase_cases('detector')]
    if phase=='crossflow':return ag.phase_cases('crossflow')
    raise AssertionError(phase)

def run(phase):
    head,tree=runtime.verify_audit_source()
    assert os.environ.get('PGURL')==peer.URL and os.environ.get('CP6_AH_CONFIRM')=='postgres'
    result=dict(status='INCOMPLETE',phase=phase,head=head,tree=tree,run_id=os.environ.get('GITHUB_RUN_ID'),cases={},production_go=False,http_ui_csv_reachability_proven=False,hosted_database_used=False)
    with psycopg.connect(peer.URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        untouched=actors.boundary(cur);catalog=function_catalog(cur)
        if phase in ('admission','reference'):
            runtime.verify_predecessor(cur)
            if phase=='admission':save('AG_COMPLETE_CATALOG',catalog);save('AG_COMPLETE_BOUNDARY',snapshot(cur))
        else:assert len(runtime.verified_successor(cur))==690
        usage=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')");result['schema_usage_fixture_grant']=not usage
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
        base.load_fixture_foundation(cur);actors.admin(cur)
        day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        prior.set_open_period(cur,date(2026,8,31) if phase=='crossflow' else day-timedelta(days=5))
        for name,case in phase_cases(phase):
            actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ah_case')
            try:record=case(cur,day)
            except Exception as exc:record=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc())
            finally:cur.execute('rollback to savepoint ah_case');actors.admin(cur);cur.execute('release savepoint ah_case')
            record['full_boundary_restored']=actors.boundary(cur)==before
            if not record['full_boundary_restored']:record['status']='FAIL'
            result['cases'][name]=record;save(phase,result)
            print(json.dumps(dict(phase=phase,case=name,status=record['status'],error=record.get('error'))),flush=True)
        actors.admin(cur);result['function_catalog_unchanged']=function_catalog(cur)==catalog
        conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
        result['unseeded_boundary_restored']=actors.boundary(cur)==untouched
        result['schema_usage_restored']=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage
        result['auth_users'],result['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    result.update(passed=sum(c['status']=='PASS' for c in result['cases'].values()),failed=sum(c['status']!='PASS' for c in result['cases'].values()))
    if result['function_catalog_unchanged'] and result['unseeded_boundary_restored'] and result['schema_usage_restored'] and result['auth_users']==result['app_users']==result['failed']==0:
        result['status']='PASS'
    save(phase,result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('reference','admission','focused','detector','crossflow'),required=True)
    phase=parser.parse_args().phase
    try:result=run(phase)
    except Exception as exc:result=dict(status='FAIL',phase=phase,error=str(exc),traceback=traceback.format_exc(),production_go=False);save(phase,result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}));raise SystemExit(0 if result['status']=='PASS' else 1)
