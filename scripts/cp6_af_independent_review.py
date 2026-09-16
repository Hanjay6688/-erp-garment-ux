#!/usr/bin/env python3
"""Independent AF transaction checks on frozen source and synthetic local data."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import hashlib,json,os,subprocess,traceback,uuid,sys
# The harness lives beside the immutable candidate checkout in CI. Resolve all
# existing ERP modules from the candidate, including builders with cwd pins.
sys.path.insert(0,str(Path.cwd()/'scripts'))
import psycopg
import cp6_v2620af_runtime as runtime
import cp6_v2620af_family as prior_cases
import cp6_ae_independent_audit as prior_review
from cp6_v2620u_install_diagnostic import snapshot
from cp6_v2620n_rollback_guards import function_catalog

AF_HEAD='f46699865501b03f9fba3a8b188f3fd01eedf404'
AF_TREE='f4dad6a6bccfffa1ba01f542cac36ac1d100c63f'
URL='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ROOT=Path('cp6-proof/independent-af')
actors,base,prior=prior_cases.actors,prior_cases.base,prior_cases.prior

def save(name,value):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')

def ordinary(cur):
    actors.owner(cur)
    identity=cur.execute('select current_user,session_user,erp.current_app_role()').fetchone()
    assert identity==('authenticated','authenticated','OWNER'),identity
    return identity

def operation(cur,query,params=()):
    identity=ordinary(cur);cur.execute('savepoint reviewed_operation')
    error=None;rows=None;changed=0
    try:
        cur.execute(query,params);changed=cur.rowcount
        if cur.description:rows=cur.fetchall()
    except psycopg.Error as exc:
        error={'sqlstate':exc.sqlstate,'message':str(exc)}
        cur.execute('rollback to savepoint reviewed_operation')
    cur.execute('release savepoint reviewed_operation')
    return dict(identity=identity,refused=error is not None,error=error,rows=rows,changed=changed)

def fixture(cur,day):
    actors.admin(cur)
    tag=uuid.uuid4().hex[:12]
    products=[base.create_product(cur,'AF-PEER-'+tag+'-'+str(n)) for n in range(2)]
    customers=[base.create_customer(cur,'AF-PEER-'+tag+'-'+str(n)) for n in range(2)]
    second_location=str(uuid.uuid4())
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'Independent second FG location','FG_WAREHOUSE',true)",(second_location,'AF-PEER-'+tag))
    ordinary(cur)
    header=uuid.uuid4()
    cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status) values(%s,%s,%s,'DRAFT')",(header,'AF-PEER-'+tag,day-timedelta(days=2)))
    for product in products:
        cur.execute("""insert into erp.opening_balance_items
          (opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method)
          values(%s,'FINISHED_GOODS',%s,%s,10,1.25,'GRADE_A','MANUAL')""",(header,product,base.LOCATION))
    cur.execute('select erp.post_opening_balance(%s)',(header,))
    payload=dict(sale_number='AF-PEER-SALE-'+tag,customer_id=customers[0],source_location_id=base.LOCATION,
        sale_date=day.isoformat()+'T10:00:00+07:00',reason='Independent AF ordinary draft',
        items=[dict(product_id=products[0],qty_pcs=3,unit_price_snapshot='20',discount_amount=0)])
    request=uuid.uuid4()
    sale=base.one(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,null)',(json.dumps(payload),request))
    replay=base.one(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,null)',(json.dumps(payload),request))
    assert replay==sale
    item=base.one(cur,'select id from erp.sales_items where sale_id=%s',(sale['sale_id'],))
    result=dict(products=products,customers=customers,second_location=second_location,payload=payload,sale=sale,item=item)
    before=observe(cur,sale['sale_id'])
    assert before['items'][0]['qty_pcs']==3 and before['active_stock_qty']==3 and before['journal_count']==0
    assert not before['mismatches'],before
    assert confidence(cur,day)['data_confidence']['status']=='READY'
    return result

def observe(cur,sale_id):
    actors.admin(cur)
    state=base.one(cur,"""select jsonb_build_object('header',to_jsonb(h),
      'items',(select jsonb_agg(to_jsonb(i) order by i.id) from erp.sales_items i where i.sale_id=h.id),
      'movements',(select jsonb_agg(to_jsonb(m) order by m.id) from erp.fg_stock_movements m
        join erp.sales_items i on i.id=m.source_id where i.sale_id=h.id and m.source_type='SALE_ITEM'
        and m.movement_type in('SALE_RESERVE','SALE') and not exists(select 1 from erp.fg_stock_movements x where x.reversal_of_id=m.id)),
      'allocations',(select jsonb_agg(to_jsonb(a)||jsonb_build_object('lot_product_id',l.product_id) order by a.id)
        from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id join erp.fg_lots l on l.id=a.lot_id where i.sale_id=h.id),
      'active_stock_qty',(select coalesce(sum(-m.qty_signed),0) from erp.fg_stock_movements m
        join erp.sales_items i on i.id=m.source_id where i.sale_id=h.id and m.source_type='SALE_ITEM'
        and m.movement_type in('SALE_RESERVE','SALE') and not exists(select 1 from erp.fg_stock_movements x where x.reversal_of_id=m.id)),
      'journal_count',(select count(*) from erp.journal_entries e where e.source_type='SALE' and e.source_id=h.id),
      'journal',(select jsonb_agg(to_jsonb(e)) from erp.journal_entries e where e.source_type='SALE' and e.source_id=h.id),
      'stock',(select jsonb_agg(to_jsonb(b) order by b.product_id,b.location_id) from erp.fg_inventory_balances b))
      from erp.sales_headers h where h.id=%s""",(sale_id,))
    assert state is not None
    items={x['id']:x for x in state['items'] or []};bad=[]
    for m in state['movements'] or []:
        i=items[m['source_id']]
        for field,left,right in [('product',m['product_id'],i['product_id']),('location',m['location_id'],state['header']['source_location_id']),('customer',m['customer_id'],state['header']['customer_id']),('physical_at',m['physical_at'],state['header']['sale_date'])]:
            if left!=right:bad.append({'field':field,'movement':m['id'],'observed':left,'expected':right})
    for a in state['allocations'] or []:
        if a['lot_product_id']!=items[a['sale_item_id']]['product_id']:bad.append({'field':'allocation_product','allocation':a['id'],'observed':a['lot_product_id'],'expected':items[a['sale_item_id']]['product_id']})
        if a['location_id']!=state['header']['source_location_id']:bad.append({'field':'allocation_location','allocation':a['id'],'observed':a['location_id'],'expected':state['header']['source_location_id']})
    state['mismatches']=bad
    return state

def confidence(cur,day):
    ordinary(cur)
    return base.one(cur,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(day,day,day))

def sale_case(mode):
    def run(cur,day):
        f=fixture(cur,day);sale=f['sale']['sale_id'];before=observe(cur,sale)
        if mode.startswith('RPC_EDIT'):
            payload=dict(f['payload'],sale_id=sale,reason='Independent legitimate edit')
            line=dict(payload['items'][0])
            if mode=='RPC_EDIT_PRODUCT':line['product_id']=f['products'][1]
            else:line['qty_pcs']=2
            payload['items']=[line]
            mutation=operation(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)',(json.dumps(payload),uuid.uuid4(),f['sale']['row_version']))
        elif mode=='CANCEL':
            mutation=operation(cur,"select erp.cancel_sale_draft_v2(%s,'Independent cancellation',%s,%s)",(sale,uuid.uuid4(),f['sale']['row_version']))
            after=observe(cur,sale)
            assert not mutation['refused'] and after['header']['status']=='CANCELLED' and after['active_stock_qty']==0 and after['journal_count']==0,(mutation,after)
            return dict(status='CONTROL_PASS',operation=mutation,before=before,after=after)
        elif mode=='BASE_POST':mutation={'refused':False,'control':True}
        elif mode=='MOVE_DRAFT':
            target=uuid.uuid4();ordinary(cur)
            cur.execute("insert into erp.sales_headers(id,sale_number,customer_id,sale_date,source_location_id,status) values(%s,%s,%s,%s,%s,'DRAFT')",
              (target,'AF-PEER-MOVE-'+target.hex,f['customers'][1],(day+timedelta(days=1)).isoformat()+'T10:00:00+07:00',base.LOCATION))
            mutation=operation(cur,'update erp.sales_items set sale_id=%s where id=%s',(target,f['item']))
            if not mutation['refused']:sale=target
        else:
            sql,params={
              'PRODUCT':('update erp.sales_items set product_id=%s where id=%s',(f['products'][1],f['item'])),
              'QUANTITY':('update erp.sales_items set qty_pcs=2 where id=%s',(f['item'],)),
              'PRICE_ONLY':('update erp.sales_items set unit_price_snapshot=21 where id=%s',(f['item'],)),
              'LOCATION':('update erp.sales_headers set source_location_id=%s where id=%s',(f['second_location'],sale)),
              'CUSTOMER':('update erp.sales_headers set customer_id=%s where id=%s',(f['customers'][1],sale)),
              'DATE':('update erp.sales_headers set sale_date=%s where id=%s',((day+timedelta(days=1)).isoformat()+'T10:00:00+07:00',sale)),
              'NOTES':("update erp.sales_headers set notes='Independent harmless notes edit' where id=%s",(sale,)),
            }[mode]
            mutation=operation(cur,sql,params)
        if mutation['refused']:
            after=observe(cur,sale)
            assert after==before,(mutation,before,after)
            return dict(status='CONTROL_PASS',mutation=mutation,before=before,after=after)
        draft=observe(cur,sale);version=draft['header']['row_version']
        posted=operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(sale,uuid.uuid4(),version))
        after=observe(cur,sale)
        if posted['refused']:
            assert after==draft
            if mode in ('BASE_POST','RPC_EDIT_PRODUCT','RPC_EDIT_QUANTITY','PRICE_ONLY','NOTES'):
                raise AssertionError('NORMAL_TRANSACTION_REFUSED:'+json.dumps(posted,default=str))
            return dict(status='CONTROL_PASS',mutation=mutation,post=posted,before=before,draft=draft,after=after)
        assert after['header']['status']=='POSTED' and after['journal_count']==1
        state=confidence(cur,day+timedelta(days=1))
        mismatch=after['mismatches']
        return dict(status='BUG_PROVEN' if mismatch else 'CONTROL_PASS',mode=mode,mutation=mutation,post=posted,
            before=before,draft=draft,after=after,report=state,
            business_requirement='Posted sale item, reserved stock, warehouse, customer, and physical date must agree; edits must rebuild reservations or refuse atomically.',
            synthetic_detector_control=False,http_ui_reachability_proven=False)
    return run

def run():
    assert os.environ.get('PGURL')==URL and os.environ.get('CP6_AF_INDEPENDENT_CONFIRM')=='postgres'
    head,tree=runtime.verify_audit_source();assert (head,tree)==(AF_HEAD,AF_TREE)
    result=dict(format='CP6_AF_INDEPENDENT_REVIEW_V1',status='INCOMPLETE',candidate_head=head,candidate_tree=tree,
      harness_head=os.environ['CP6_AF_HARNESS_HEAD'],run_id=os.environ.get('GITHUB_RUN_ID'),cases={},
      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),production_go=False,
      hosted_database_used=False,http_ui_csv_reachability_proven=False)
    modes=('BASE_POST','RPC_EDIT_PRODUCT','RPC_EDIT_QUANTITY','CANCEL','PRODUCT','QUANTITY','LOCATION','CUSTOMER','DATE','MOVE_DRAFT','PRICE_ONLY','NOTES')
    cases=[('SALE_'+mode,sale_case(mode)) for mode in modes]
    for mode in ('SAME_PARENT_EDIT','DELETE','MOVE','MOVE_AND_EDIT','DRAFT_MOVE'):
        cases.append(('AF_OPENING_'+mode,lambda c,d,m=mode:prior_review.opening_change(c,d,m)))
    with psycopg.connect(URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur))==278
        unseeded=snapshot(cur);catalog=function_catalog(cur)
        usage=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        result['schema_usage_fixture_grant']=not usage
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
        base.load_fixture_foundation(cur);actors.admin(cur)
        day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        prior.set_open_period(cur,day-timedelta(days=4))
        for name,fn in cases:
            actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint independent_case')
            try:record=fn(cur,day)
            except Exception as exc:record=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint independent_case');actors.admin(cur);cur.execute('release savepoint independent_case')
            record['case_boundary_restored']=actors.boundary(cur)==before
            if not record['case_boundary_restored']:record['status']='INCOMPLETE'
            result['cases'][name]=record;save('RESULT',result)
            print(json.dumps(dict(case=name,status=record['status'],error=record.get('error'))),flush=True)
        actors.admin(cur);assert function_catalog(cur)==catalog
        conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
        result['entire_unseeded_boundary_exact']=snapshot(cur)==unseeded and function_catalog(cur)==catalog
        result['schema_usage_restored']=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage
        result['native_runtime_objects']=len(runtime.verified_successor(cur))
        result['auth_users'],result['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    result.update(expected_cases=len(cases),controls=sum(c['status']=='CONTROL_PASS' for c in result['cases'].values()),
      counterexamples=sum(c['status']=='BUG_PROVEN' for c in result['cases'].values()),incomplete=sum(c['status'] not in ('CONTROL_PASS','BUG_PROVEN') for c in result['cases'].values()))
    if result['entire_unseeded_boundary_exact'] and result['schema_usage_restored'] and result['auth_users']==result['app_users']==0 and result['incomplete']==0:
        result['status']='QUALIFIED_COUNTEREXAMPLE' if result['counterexamples'] else 'PASS_WITHIN_RECORDED_SCOPE'
    save('RESULT',result);return result

if __name__=='__main__':
    try:r=run()
    except Exception as exc:r=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False);save('RESULT',r)
    print(json.dumps({k:v for k,v in r.items() if k!='cases'},default=str))
    raise SystemExit(0 if r['status']=='PASS_WITHIN_RECORDED_SCOPE' else 1 if r['status']=='QUALIFIED_COUNTEREXAMPLE' else 2)
